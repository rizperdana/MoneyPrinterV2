# Dynamic Background Music Ducking — Design Spec

**Date:** 2026-04-23
**Type:** Audio Feature (Enhancement)
**Status:** Draft

---

## Goal

Lower background music volume during TTS speech segments, raise it during TTS silence (between sentences), using sentence-level timing from EdgeTTS `SentenceBoundary` metadata. Volume levels and fade duration configurable via settings.

---

## Architecture

### Overview

```
EdgeTTS.synthesize(text)
  ├── generates MP3 audio
  └── writes metadata .json with SentenceBoundary entries
       (offset in microseconds, duration in microseconds, text)

YouTube.combine()
  ├── reads TTS audio file
  ├── loads SentenceBoundary metadata
  ├── builds speech_windows[] = [(start, end), ...] from metadata
  ├── loads background song as AudioFileClip
  ├── attaches time-varying volume function to song clip
  │     └── volume_func(t):
  │           if t in any speech_window → MUSIC_VOLUME_SPEECH (quiet)
  │           else → MUSIC_VOLUME_SILENCE (louder)
  │           apply linear fade at boundaries using FADE_DURATION_MS
  └── CompositeAudioClip([tts_clip, song_clip])
```

### Key Design Decisions

1. **Sentence-level vs word-level:** Sentence boundaries are natural speech pauses (~300–500ms). EdgeTTS produces them at no extra cost. This is the right granularity — word-level adds complexity for marginal gain.
2. **Time-varying volume via MoviePy's `with_volume_scaled(func)`:** `func` maps `t → volume_multiplier`. MoviePy evaluates it per-frame, so ducking follows the exact speech windows automatically.
3. **Fade transitions:** Linear fade in/out at speech boundaries prevents audible clicks. Configurable fade duration.
4. **No VAD needed:** EdgeTTS metadata is the VAD signal — precise, zero-latency, no extra computation.
5. **Backwards compatible:** If metadata file is missing or malformed, fall back to constant `MUSIC_VOLUME_SILENCE` (original behavior).

---

## New Configuration Keys

Added to settings (stored in DB, configurable by user):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `music_volume_speech` | float | `0.08` | Music volume multiplier during TTS speech (0.0–1.0) |
| `music_volume_silence` | float | `0.35` | Music volume multiplier during TTS silence (0.0–1.0) |
| `music_fade_duration_ms` | int | `200` | Fade duration in ms at speech/silence transitions |

---

## File Changes

### Modify: `src/classes/EdgeTts.py`

**Change:** `synthesize()` currently saves only MP3 → WAV. Add optional `metadata_path` parameter.

```python
def synthesize(
    self,
    text: str,
    output_file: str = ...,
    metadata_path: str | None = None,
) -> str:
    # ... existing MP3→WAV logic ...
    # NEW: if metadata_path provided, write SentenceBoundary metadata
    if metadata_path:
        with open(metadata_path) as f:
            # write JSON lines
    return output_file
```

**Implementation detail:** Use `boundary="SentenceBoundary"` explicitly (default, but make it intentional). EdgeTTS `save()` accepts `metadata_fname` parameter directly — pass it to save both MP3 and metadata in one call:

```python
await communicate.save(output_path, metadata_path)  # audio at output_path, metadata at metadata_path
```

---

### Modify: `src/classes/Tts.py`

**Change:** `TTS.synthesize()` signature to accept and pass through `metadata_path`.

```python
def synthesize(
    self,
    text,
    output_file=...,
    metadata_path: str | None = None,
):
    return self._model.synthesize(text, output_file, metadata_path=metadata_path)
```

---

### Modify: `src/classes/YouTube.py`

**Changes to `combine()` (around lines 2242–2248):**

1. Generate metadata path alongside tts_path:
   ```python
   tts_path = self.tts_path  # already set
   metadata_path = tts_path.replace(".wav", "_sentences.json")
   ```

2. Pass metadata_path to TTS if not already synthesized:
   - The TTS synthesis happens earlier in the pipeline. Ensure `self.tts_path` is set and the metadata file exists at the same path with `_sentences.json` suffix.

3. Load speech windows from metadata:
   ```python
   def load_speech_windows(meta_path: str) -> list[tuple[float, float]]:
       windows = []
       if os.path.exists(meta_path):
           with open(meta_path) as f:
               for line in f:
                   entry = json.loads(line)
                   if entry["type"] == "SentenceBoundary":
                       start_us = entry["offset"]
                       dur_us = entry["duration"]
                       start_s = start_us / 1_000_000
                       end_s = (start_us + dur_us) / 1_000_000
                       windows.append((start_s, end_s))
       return windows
   ```

4. Config getters (new in config.py — see below):
   ```python
   vol_speech   = get_music_volume_speech()    # e.g. 0.08
   vol_silence  = get_music_volume_silence()   # e.g. 0.35
   fade_ms      = get_music_fade_duration_ms()  # e.g. 200
   fade_s       = fade_ms / 1000
   ```

5. Volume function with fade:
   ```python
   def make_volume_func(windows, vol_speech, vol_silence, fade_s):
       def volume_func(t):
           for start, end in windows:
               # Check if t is within speech window (with fade buffer)
               if start - fade_s <= t <= end + fade_s:
                   # Inside speech window
                   # Fade in at start, fade out at end
                   if t < start:
                       # Pre-speech: ramp up to silence volume
                       return vol_silence
                   elif t > end:
                       # Post-speech: ramp down to silence volume
                       return vol_silence
                   else:
                       # Inside speech window
                       dist_to_start = t - (start - fade_s)
                       dist_to_end = (end + fade_s) - t
                       if dist_to_start < fade_s:
                           # Fade-in zone
                           ratio = dist_to_start / fade_s
                           return vol_speech + ratio * (vol_silence - vol_speech)
                       elif dist_to_end < fade_s:
                           # Fade-out zone
                           ratio = dist_to_end / fade_s
                           return vol_speech + ratio * (vol_silence - vol_speech)
                       else:
                           return vol_speech
           # Outside all speech windows: full silence volume
           return vol_silence
       return volume_func
   ```

   **Refinement (simpler):** Instead of the above, use a direct binary approach with pre/post fade:
   ```python
   def volume_func(t):
       for start, end in windows:
           if start - fade_s <= t <= end + fade_s:
               # Inside or near speech window
               if start <= t <= end:
                   return vol_speech
               elif t < start:
                   # Fade in from vol_silence → vol_speech
                   return vol_silence + (vol_speech - vol_silence) * ((t - (start - fade_s)) / fade_s)
               else:  # t > end
                   # Fade out from vol_speech → vol_silence
                   return vol_speech + (vol_silence - vol_speech) * ((t - end) / fade_s)
       return vol_silence
   ```

6. Apply to song clip:
   ```python
   speech_windows = load_speech_windows(metadata_path)
   if speech_windows:
       vol_func = make_volume_func(speech_windows, vol_speech, vol_silence, fade_s)
       random_song_clip = random_song_clip.with_volume_scaled(vol_func)
   else:
       # Fallback: constant silence volume (original behavior)
       random_song_clip = random_song_clip.with_volume_scaled(vol_silence)
   ```

---

### Modify: `src/config.py`

**Add new getter functions (after existing getters):**

```python
def get_music_volume_speech() -> float:
    """Music volume (0.0–1.0) during TTS speech segments."""
    val = _get_config("music_volume_speech", 0.08)
    return float(max(0.0, min(1.0, val)))

def get_music_volume_silence() -> float:
    """Music volume (0.0–1.0) during TTS silence (between sentences)."""
    val = _get_config("music_volume_silence", 0.35)
    return float(max(0.0, min(1.0, val)))

def get_music_fade_duration_ms() -> int:
    """Fade duration in ms at speech/silence transitions."""
    val = _get_config("music_fade_duration_ms", 200)
    return int(max(0, min(2000, val)))  # clamp 0–2000ms
```

---

## Error Handling & Edge Cases

| Scenario | Behavior |
|----------|----------|
| Metadata file missing | Fall back to constant `vol_silence` (original behavior) |
| Metadata file malformed (invalid JSON) | Log warning, fall back to constant `vol_silence` |
| Metadata file empty | Fall back to constant `vol_silence` |
| `vol_speech` > `vol_silence` | Clamp both to valid range in config getters |
| Song file missing | Skip music, TTS only (existing behavior) |
| Fade duration = 0 | No fade, hard transition |
| TTS is shorter than music | Music fades naturally to silence after TTS ends |

---

## Default Behavior (No Config Changes)

| Parameter | Default | Effect |
|-----------|---------|--------|
| `music_volume_speech` | 0.08 | Music at 8% during TTS speech |
| `music_volume_silence` | 0.35 | Music at 35% during silence gaps |
| `music_fade_duration_ms` | 200 | 200ms linear fade between states |

**Comparison with current behavior:**
Current: constant `0.1` (10%) at all times.
New: `0.08` during speech, `0.35` during gaps — noticeable ducking effect that respects natural pauses.

---

## UI/Config Integration

Settings stored in database via existing `get_settings()`/`save_settings()` pattern. User-facing config UI (if exists) should expose three sliders:

1. **Music Vol (Speech):** 0–100% → stored as `music_volume_speech` (0.0–1.0)
2. **Music Vol (Silence):** 0–100% → stored as `music_volume_silence` (0.0–1.0)
3. **Duck Fade Duration:** 0–500ms → stored as `music_fade_duration_ms`

---

## Testing

| Test | What it verifies |
|------|-----------------|
| EdgeTTS metadata file created | `synthesize(..., metadata_path=...)` writes valid JSON lines |
| Speech windows parsed correctly | `load_speech_windows()` returns list of (start_s, end_s) tuples |
| Volume func returns speech vol inside window | `volume_func(midpoint_of_window)` == `vol_speech` (±epsilon) |
| Volume func returns silence vol outside windows | `volume_func(far_from_windows)` == `vol_silence` |
| Fade zones transition correctly | Linear interpolation in fade zones |
| Fallback when metadata missing | No metadata → constant `vol_silence` used |
| End-to-end video with ducking | Video plays with audible ducking effect |

---

## Scope Boundaries

**In scope:**
- Sentence-level ducking via EdgeTTS metadata
- Configurable volume levels and fade duration
- Backwards-compatible fallback

**Out of scope:**
- Word-level ducking (future upgrade, no architectural change needed)
- Ducking for non-EdgeTTS TTS providers (would require VAD)
- Real-time ducking during live streaming
