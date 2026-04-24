# Dynamic Background Music Ducking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lower background music volume during TTS speech segments, raise it during TTS silence (between sentences), using sentence-level timing from EdgeTTS `SentenceBoundary` metadata. Volume levels and fade duration configurable via settings.

**Architecture:** EdgeTTS `save(audio_path, metadata_path)` writes sentence boundary metadata to a sidecar `.jsonl` file. `YouTube.combine()` reads those boundaries, builds speech windows, and attaches a time-varying `volume_func(t)` to the background song via MoviePy's `with_volume_scaled(func)`.

**Tech Stack:** edge_tts, soundfile, moviepy, config.py (getters), YouTube.py

---

## GAP ANALYSIS — Spec → Plan

Before writing tasks, here are the gaps/discrepancies found between the spec and what actually exists in the codebase:

| Gap | Detail |
|-----|--------|
| **Gap 1: TTS synthesize path** | `YouTube.py` calls TTS in `generate_voiceover()` or similar, not `combine()`. Must trace exact call site and add metadata_path there. |
| **Gap 2: EdgeTTS save() signature** | `communicate.save(mp3_path, metadata_path)` — metadata is 2nd positional arg, not keyword. Must pass correctly. |
| **Gap 3: Metadata path convention** | Need exact convention: e.g., TTS at `.mp/audio.wav`, metadata at `.mp/audio_sentences.json`. Must codify. |
| **Gap 4: Config getters location** | `config.py` is 440 lines. New getters must go after existing patterns (around line 350–440). |
| **Gap 5: Fallback test coverage** | Need tests for: missing metadata, malformed metadata, empty metadata, edge fade zones. |
| **Gap 6: Script sentence parsing** | EdgeTTS uses `SentenceBoundary` — not word-level. This matches the B choice. Spec updated accordingly. |
| **Gap 7: `volume_func` complexity** | The refined binary+fade volume_func is simpler than the first version. Use the refined version from spec. |
| **Gap 8: `combine()` refactor** | `tts_path` is set earlier in pipeline. Must ensure metadata_path is derived and accessible at `combine()` time. |
| **Gap 9: Config validation clamping** | Config getters must clamp values (0.0–1.0 for volumes, 0–2000ms for fade). |

---

## Task Breakdown

### Task 1: Config Getters

**Files:**
- Modify: `src/config.py` (add 3 getters at end of file, before any final exports)

**Context:**
- `config.py` uses `_get_config(key, default)` for all settings
- Default values per spec: `music_volume_speech=0.08`, `music_volume_silence=0.35`, `music_fade_duration_ms=200`
- Clamp values: volumes 0.0–1.0, fade 0–2000ms
- Follow existing getter naming: `get_music_volume_speech()`, `get_music_volume_silence()`, `get_music_fade_duration_ms()`

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_music_ducking.py
def test_get_music_volume_speech_default():
    from src.config import get_music_volume_speech
    val = get_music_volume_speech()
    assert 0.0 <= val <= 1.0

def test_get_music_volume_silence_default():
    from src.config import get_music_volume_silence
    val = get_music_volume_silence()
    assert 0.0 <= val <= 1.0

def test_get_music_fade_duration_ms_default():
    from src.config import get_music_fade_duration_ms
    val = get_music_fade_duration_ms()
    assert 0 <= val <= 2000

def test_volume_clamping():
    """Volumes outside 0-1 are clamped."""
    from src.config import get_music_volume_speech
    # When settings return out-of-range values, getter clamps them
    # This tests the clamping logic directly
    import unittest.mock as mock
    with mock.patch('src.config._get_config', return_value=2.0):
        val = get_music_volume_speech()
        assert val == 1.0
    with mock.patch('src.config._get_config', return_value=-0.5):
        val = get_music_volume_speech()
        assert val == 0.0
```

Run: `python -m pytest tests/test_config_music_ducking.py -v`
Expected: FAIL — functions not defined

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_config_music_ducking.py -v 2>&1 | head -30`
Expected: FAIL — functions not defined

- [ ] **Step 3: Write minimal implementation**

Add to end of `config.py`:

```python
def get_music_volume_speech() -> float:
    """Music volume (0.0–1.0) during TTS speech segments."""
    val = _get_config("music_volume_speech", 0.08)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.08
    return max(0.0, min(1.0, val))

def get_music_volume_silence() -> float:
    """Music volume (0.0–1.0) during TTS silence (between sentences)."""
    val = _get_config("music_volume_silence", 0.35)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.35
    return max(0.0, min(1.0, val))

def get_music_fade_duration_ms() -> int:
    """Fade duration in ms at speech/silence transitions."""
    val = _get_config("music_fade_duration_ms", 200)
    try:
        val = int(val)
    except (TypeError, ValueError):
        val = 200
    return max(0, min(2000, val))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_config_music_ducking.py -v 2>&1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config_music_ducking.py
git commit -m "feat(config): add music ducking volume getters with clamping"
```

---

### Task 2: EdgeTTS Metadata Generation

**Files:**
- Modify: `src/classes/EdgeTts.py` — add `metadata_path` parameter to `synthesize()`
- Modify: `src/classes/Tts.py` — pass through `metadata_path`
- Create: `tests/test_edge_tts_metadata.py`

**Context:**
- Current `EdgeTts.synthesize(text, output_file)` → writes MP3 → converts to WAV → returns path
- Need: also write sentence metadata alongside the MP3
- EdgeTTS `communicate.save(audio_path, metadata_path)` writes metadata directly
- We need: metadata_path derived from output_file, e.g., `output_file.replace(".mp3", "_sentences.jsonl")` OR pass explicitly
- The metadata file is JSONL (one JSON object per line)

**Important detail:** The MP3 file is temporary (deleted after WAV conversion). Metadata must be written based on the original MP3 generation, not after. So modify `_generate_mp3` or the synthesize body to capture metadata while MP3 still exists.

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_edge_tts_metadata.py
import os, tempfile, pytest
from src.classes.EdgeTts import EdgeTTS

def test_synthesize_writes_metadata():
    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = os.path.join(tmpdir, "audio.mp3")
        meta_path = os.path.join(tmpdir, "audio_meta.jsonl")
        result = model.synthesize("Hello world. This is a test.", mp3_path, metadata_path=meta_path)
        assert os.path.exists(meta_path), "Metadata file not created"
        with open(meta_path) as f:
            lines = f.readlines()
        assert len(lines) >= 2, "Should have at least 2 sentence boundaries"
        import json
        entries = [json.loads(l) for l in lines]
        assert all(e["type"] == "SentenceBoundary" for e in entries)
        assert all("offset" in e and "duration" in e for e in entries)

def test_metadata_offset_format():
    """Offsets are in microseconds."""
    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = os.path.join(tmpdir, "meta.jsonl")
        model.synthesize("Short sentence.", os.path.join(tmpdir, "audio.mp3"), metadata_path=meta_path)
        with open(meta_path) as f:
            entry = json.loads(f.readline())
        assert entry["offset"] >= 0
        assert entry["duration"] > 0
```

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_edge_tts_metadata.py -v`
Expected: FAIL — `metadata_path` parameter not supported

- [ ] **Step 2: Run test to verify it fails** (already above)

- [ ] **Step 3: Write minimal implementation**

In `EdgeTts.py`, rewrite `synthesize()` to:

```python
def synthesize(
    self,
    text: str,
    output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav"),
    metadata_path: str | None = None,
):
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    text = text.strip()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
        tmp_mp3_path = tmp_mp3.name

    try:
        asyncio.run(self._generate_mp3(text, tmp_mp3_path, metadata_path))
        audio, sample_rate = sf.read(tmp_mp3_path)
        sf.write(output_file, audio, sample_rate)
    finally:
        if os.path.exists(tmp_mp3_path):
            os.unlink(tmp_mp3_path)

    return output_file

async def _generate_mp3(self, text: str, output_path: str, metadata_path: str | None = None) -> None:
    try:
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path, metadata_path)
    except Exception as e:
        # If SSML was passed but rejected, strip tags and retry once
        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r'\b(rate|pitch|volume)="[^"]+"', "", clean_text)
        clean_text = clean_text.strip()
        if clean_text:
            communicate = edge_tts.Communicate(clean_text, self._voice)
            await communicate.save(output_path, metadata_path)
        else:
            raise ValueError("Empty text after SSML cleanup") from e
```

Update `Tts.py` to pass through `metadata_path`:

```python
def synthesize(self, text, output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav"), metadata_path: str | None = None):
    return self._model.synthesize(text, output_file, metadata_path=metadata_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_edge_tts_metadata.py -v 2>&1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/classes/EdgeTts.py src/classes/Tts.py tests/test_edge_tts_metadata.py
git commit -m "feat(tts): synthesize writes SentenceBoundary metadata alongside audio"
```

---

### Task 3: Speech Windows Loader + Volume Function

**Files:**
- Create: `src/utils_audio.py` — helper functions for audio ducking
- Create: `tests/test_utils_audio.py`

**Context:**
- `load_speech_windows(meta_path) → list[tuple[float, float]]`
- `make_volume_func(windows, vol_speech, vol_silence, fade_s) → Callable[[float], float]`
- These are pure functions, no side effects — easy to test exhaustively

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_utils_audio.py
import json, tempfile, os, pytest
from src.utils_audio import load_speech_windows, make_volume_func

def test_load_speech_windows_basic():
    """Parse SentenceBoundary entries into (start_s, end_s) tuples."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 0, "duration": 1000000, "text": "Hello."}) + "\n")
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 1100000, "duration": 1000000, "text": "World."}) + "\n")
        path = f.name
    try:
        windows = load_speech_windows(path)
        assert windows == [(0.0, 1.0), (1.1, 2.1)], f"Got {windows}"
    finally:
        os.unlink(path)

def test_load_speech_windows_malformed():
    """Malformed lines are skipped."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 0, "duration": 1000000, "text": "Hello."}) + "\n")
        f.write("NOT JSON\n")
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 2000000, "duration": 1000000, "text": "World."}) + "\n")
        path = f.name
    try:
        windows = load_speech_windows(path)
        assert len(windows) == 2
    finally:
        os.unlink(path)

def test_load_speech_windows_missing_file():
    """Missing file returns empty list."""
    windows = load_speech_windows("/nonexistent/path.jsonl")
    assert windows == []

def test_volume_func_inside_speech_window():
    """Inside speech: returns vol_speech."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    assert abs(vol_func(2.0) - 0.08) < 1e-9

def test_volume_func_outside_speech_window():
    """Outside all speech windows: returns vol_silence."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    assert abs(vol_func(0.0) - 0.35) < 1e-9
    assert abs(vol_func(5.0) - 0.35) < 1e-9

def test_volume_func_fade_in_zone():
    """Before speech start (within fade): linear interpolation toward vol_speech."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    # At t=0.85 (0.15s into 0.2s fade-in): ratio = 0.15/0.2 = 0.75
    # expected = 0.35 + 0.75*(0.08-0.35) = 0.35 - 0.2025 = 0.1475
    val = vol_func(0.85)
    expected = 0.35 + 0.75 * (0.08 - 0.35)
    assert abs(val - expected) < 1e-9

def test_volume_func_fade_out_zone():
    """After speech end (within fade): linear interpolation toward vol_silence."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    # At t=3.15 (0.15s into fade-out from 3.0): ratio = 0.15/0.2 = 0.75
    # expected = 0.08 + 0.75*(0.35-0.08) = 0.08 + 0.2025 = 0.2825
    val = vol_func(3.15)
    expected = 0.08 + 0.75 * (0.35 - 0.08)
    assert abs(val - expected) < 1e-9

def test_volume_func_zero_fade():
    """Fade duration = 0: hard transition."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.0)
    assert abs(vol_func(1.0) - 0.08) < 1e-9
    assert abs(vol_func(0.999) - 0.35) < 1e-9
    assert abs(vol_func(3.0) - 0.08) < 1e-9
    assert abs(vol_func(3.001) - 0.35) < 1e-9

def test_volume_func_multiple_windows():
    """Multiple speech windows: each handled independently."""
    windows = [(0.5, 1.5), (3.0, 4.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.1)
    assert abs(vol_func(1.0) - 0.08) < 1e-9   # inside first window
    assert abs(vol_func(3.5) - 0.08) < 1e-9   # inside second window
    assert abs(vol_func(2.0) - 0.35) < 1e-9   # between windows
```

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_utils_audio.py -v`
Expected: FAIL — module not found

- [ ] **Step 2: Run test to verify it fails** (already above)

- [ ] **Step 3: Write minimal implementation**

Create `src/utils_audio.py`:

```python
"""Audio ducking helpers — speech window parsing and volume functions."""
import json
import os
from typing import Callable


def load_speech_windows(meta_path: str) -> list[tuple[float, float]]:
    """Load speech windows from EdgeTTS SentenceBoundary metadata file.

    Args:
        meta_path: Path to JSONL metadata file.

    Returns:
        List of (start_seconds, end_seconds) tuples for each sentence.
    """
    if not os.path.exists(meta_path):
        return []

    windows = []
    with open(meta_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "SentenceBoundary":
                continue

            offset_us = entry.get("offset", 0)
            dur_us = entry.get("duration", 0)
            start_s = offset_us / 1_000_000
            end_s = (offset_us + dur_us) / 1_000_000
            windows.append((start_s, end_s))

    return windows


def make_volume_func(
    windows: list[tuple[float, float]],
    vol_speech: float,
    vol_silence: float,
    fade_s: float,
) -> Callable[[float], float]:
    """Build a time-varying volume function for dynamic music ducking.

    Args:
        windows: List of (start, end) speech windows in seconds.
        vol_speech: Volume multiplier during TTS speech.
        vol_silence: Volume multiplier during TTS silence (between sentences).
        fade_s: Fade duration in seconds at speech/silence transitions.

    Returns:
        A function t -> volume_multiplier.
    """
    def volume_func(t: float) -> float:
        for start, end in windows:
            fade_start = start - fade_s
            fade_end = end + fade_s

            if fade_start <= t <= fade_end:
                if start <= t <= end:
                    # Inside speech window: quiet
                    return vol_speech
                elif t < start:
                    # Fade-in zone: interpolate from vol_silence to vol_speech
                    dist = t - fade_start
                    if fade_s > 0:
                        ratio = dist / fade_s
                    else:
                        ratio = 1.0
                    return vol_silence + ratio * (vol_speech - vol_silence)
                else:  # t > end
                    # Fade-out zone: interpolate from vol_speech to vol_silence
                    dist = t - end
                    if fade_s > 0:
                        ratio = dist / fade_s
                    else:
                        ratio = 1.0
                    return vol_speech + ratio * (vol_silence - vol_speech)

        # Outside all speech windows: full silence volume
        return vol_silence

    return volume_func
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_utils_audio.py -v 2>&1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/utils_audio.py tests/test_utils_audio.py
git commit -m "feat(audio): add speech window loader and dynamic volume function"
```

---

### Task 4: YouTube.combine() Integration

**Files:**
- Modify: `src/classes/YouTube.py` — integrate ducking in `combine()` method

**Context:**
- `YouTube.combine()` currently at lines ~2240–2259
- TTS path: `self.tts_path` (set earlier in pipeline by TTS synthesis call)
- Metadata path convention: `self.tts_path.replace(".wav", "_sentences.jsonl")`
- Import new helpers: `from utils_audio import load_speech_windows, make_volume_func`
- Import config getters: `from config import get_music_volume_speech, get_music_volume_silence, get_music_fade_duration_ms`
- Fallback: if `speech_windows` is empty (metadata missing/empty), use constant `vol_silence`

**Steps:**

- [ ] **Step 1: Write the failing test**

```python
# tests/test_youtube_combine_music_ducking.py
import os, tempfile, pytest
from unittest import mock

def test_combine_uses_dynamic_ducking():
    """When metadata exists, song clip gets dynamic volume func."""
    # This test is tricky because combine() is a long method.
    # Test the ducking logic in isolation: given speech windows,
    # volume_func produces the right values.
    from src.utils_audio import make_volume_func, load_speech_windows
    windows = [(0.0, 2.0), (3.0, 5.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    # Inside speech: 0.08
    assert abs(vol_func(1.0) - 0.08) < 1e-9
    # Between windows: 0.35
    assert abs(vol_func(2.5) - 0.35) < 1e-9
    # Fade zone at end of window
    assert vol_func(2.15) > 0.08  # transitioning back toward silence
    assert vol_func(2.15) < 0.35

def test_combine_fallback_no_metadata():
    """When metadata is missing, constant vol_silence is used."""
    from src.utils_audio import load_speech_windows
    windows = load_speech_windows("/nonexistent/file.jsonl")
    assert windows == []
    # The combine() method should fall back gracefully
```

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_youtube_combine_music_ducking.py -v`
Expected: PASS (these are logic-only tests, no combine() execution needed)

- [ ] **Step 2: Run test to verify it passes** (already above — logic tests)

- [ ] **Step 3: Modify combine() method**

Locate the section in `combine()` around lines 2242–2248:

```python
# CURRENT (constant volume):
random_song = choose_random_song()
random_song_clip = AudioFileClip(random_song).with_fps(44100)
random_song_clip = random_song_clip.with_volume_scaled(0.1)
comp_audio = CompositeAudioClip([tts_clip.with_fps(44100), random_song_clip])
```

REPLACE with:

```python
# Dynamic music ducking: lower volume during TTS speech, raise during silence
random_song = choose_random_song()
random_song_clip = AudioFileClip(random_song).with_fps(44100)

metadata_path = self.tts_path.replace(".wav", "_sentences.jsonl")
speech_windows = load_speech_windows(metadata_path)

if speech_windows:
    vol_speech = get_music_volume_speech()
    vol_silence = get_music_volume_silence()
    fade_ms = get_music_fade_duration_ms()
    fade_s = fade_ms / 1000.0
    vol_func = make_volume_func(speech_windows, vol_speech, vol_silence, fade_s)
    random_song_clip = random_song_clip.with_volume_scaled(vol_func)
else:
    # Fallback: constant silence volume (original default 0.1, but configurable)
    vol_silence = get_music_volume_silence()
    random_song_clip = random_song_clip.with_volume_scaled(vol_silence)

comp_audio = CompositeAudioClip([tts_clip.with_fps(44100), random_song_clip])
```

Add imports at top of YouTube.py (check existing imports section):
```python
from utils_audio import load_speech_windows, make_volume_func
```

**Important:** You also need to ensure the metadata file was actually written during TTS synthesis. Check where `self.tts_path` is set in the pipeline — that call must also pass `metadata_path`. See Task 5.

- [ ] **Step 4: Verify code is syntactically correct**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -c "from src.classes.YouTube import YouTube; print('import OK')" 2>&1`
Expected: No import errors

- [ ] **Step 5: Commit**

```bash
git add src/classes/YouTube.py
git commit -m "feat(youtube): integrate dynamic music ducking in combine()"
```

---

### Task 5: Wire TTS Metadata Path in Pipeline

**Files:**
- Modify: `src/classes/YouTube.py` — find where TTS is called and pass metadata_path

**Context:**
- Need to trace the full pipeline: where does `self.tts_path` get set?
- Search for `.synthesize(` calls in `YouTube.py` and find where TTS output path is assigned
- At that call site, also compute `metadata_path` and pass it to the synthesize call

**Steps:**

- [ ] **Step 1: Find all synthesize() call sites in YouTube.py**

Run: `grep -n "synthesize\|tts_path\|TTS\|\.synthesize" /home/anon/Projects/experiment/MoneyPrinterV2/src/classes/YouTube.py | head -40`

Report back the exact lines where TTS is called and where `self.tts_path` is assigned.

- [ ] **Step 2: At each call site, pass metadata_path**

For each call site found:
```python
# Before synthesize call, compute metadata_path:
metadata_path = tts_output_path.replace(".mp", "/.sentences.jsonl")  # or similar
# Actually the synthesize receives output_file, so:
# metadata_path = output_file.replace(".mp3", "_sentences.jsonl").replace(".wav", "_sentences.jsonl")
# Simplify: use a helper or just pass it alongside
```

The `Tts.synthesize(text, output_file, metadata_path=metadata_path)` now accepts metadata_path (Task 2).

- [ ] **Step 3: Verify pipeline end-to-end**

Run a smoke test (if possible without browser):
```python
# Pseudo-test: verify synthesize writes metadata, combine() reads it
```

- [ ] **Step 4: Commit**

```bash
git add src/classes/YouTube.py
git commit -m "feat(youtube): wire metadata_path into TTS synthesize calls"
```

---

### Task 6: Preflight / Smoke Test

**Files:**
- Modify: `scripts/preflight_local.py` (optional — add music ducking config check)
- Create: `tests/test_e2e_music_ducking.py` (end-to-end)

**Context:**
- After all changes, verify the full pipeline works
- Test: generate a short script, run TTS with metadata, assemble video with ducking

**Steps:**

- [ ] **Step 1: Run preflight**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python scripts/preflight_local.py 2>&1 | head -30`
Expected: All checks pass

- [ ] **Step 2: Run existing tests**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_e2e_music_ducking.py 2>&1 | tail -20`
Expected: All existing tests still pass (no regression)

- [ ] **Step 3: Write and run E2E ducking smoke test**

```python
# tests/test_e2e_music_ducking.py
"""E2E smoke test: synthesize with metadata + verify ducking logic."""
import os, tempfile

def test_e2e_ducking_logic():
    from src.classes.EdgeTts import EdgeTTS
    from src.utils_audio import load_speech_windows, make_volume_func

    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3 = os.path.join(tmpdir, "audio.mp3")
        meta = os.path.join(tmpdir, "sentences.jsonl")
        model.synthesize("Hello. World.", mp3, metadata_path=meta)

        windows = load_speech_windows(meta)
        assert len(windows) == 2, f"Expected 2 sentences, got {windows}"

        vol_func = make_volume_func(windows, 0.08, 0.35, 0.2)
        # Check inside vs outside windows
        assert abs(vol_func(windows[0][0] + 0.1) - 0.08) < 1e-3  # inside speech
        assert abs(vol_func(windows[1][1] + 0.5) - 0.35) < 1e-3  # outside
```

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python -m pytest tests/test_e2e_music_ducking.py -v 2>&1`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e_music_ducking.py
git commit -m "test: add E2E smoke test for music ducking pipeline"
```

---

## Final Verification

After all tasks:
1. All new tests pass
2. `python scripts/preflight_local.py` passes
3. No regressions in existing tests
4. `git log --oneline` shows 6 commits

## Task Summary

| # | Task | Files | Key Action |
|---|------|-------|------------|
| 1 | Config getters | `config.py` | 3 getters with clamping |
| 2 | EdgeTTS metadata | `EdgeTts.py`, `Tts.py` | Pass `metadata_path` to `save()` |
| 3 | Ducking helpers | `utils_audio.py` | `load_speech_windows` + `make_volume_func` |
| 4 | combine() integration | `YouTube.py` | Attach `volume_func` to song clip |
| 5 | Wire TTS call sites | `YouTube.py` | Pass `metadata_path` at synthesize calls |
| 6 | Verification | preflight + tests | Smoke test |
