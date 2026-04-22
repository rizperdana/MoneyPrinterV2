# SSML Prosody Voiceover — Design Spec

**Date:** 2026-04-22
**Project:** MoneyPrinterV2 — Humane/Hooking Voiceover via Edge TTS SSML Prosody
**Status:** Draft

---

## 1. Context and Motivation

The project generates YouTube Shorts from scripts. The current Edge TTS pipeline produces flat, robotic voice output with no delivery variation. This works for simple topics but fails for content that needs emotional range — mysteries, news, motivational, science explainers, etc.

Goal: Let the LLM model decide the best delivery strategy per-script and embed prosody control directly in the generated script using SSML. Edge TTS will render the SSML natively.

---

## 2. Root Cause Analysis — Why Prosody Never Worked

Three independent failure points destroy prosody before it reaches Edge TTS:

### 2.1 YouTube.py line 1765 — Script Cleaner

```python
self.script = re.sub(r"[^\w\s.?!]", "", self.script)
tts_instance.synthesize(self.script, path)
```

**What it does:** Removes every character that is not a word, space, period, question mark, or exclamation mark.

**Effect on SSML:** Strips `<`, `>`, `/` characters. An SSML string like `<speak><prosody rate="90%">...</prosody></speak>` becomes `speakprosody rate90...prosgodyendspeak`. Completely destroyed.

**This runs right before `synthesize()`** — so even if the LLM generates perfect SSML, it dies here.

### 2.2 EdgeTts.py line 28 — `_strip_ssml()` in synthesize

```python
try:
    text = self._strip_ssml(text)
except Exception:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
```

```python
def _strip_ssml(self, text: str) -> str:
    if "<speak" in text.lower():
        text = re.sub(r"<speak[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"</speak>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)  # kills ALL XML including <prosody>
    text = re.sub(r'\b(rate|pitch)="[^"]+"', "", text)
    return text.strip()
```

**Effect:** Even if SSML somehow survived YouTube.py's regex, this method strips all XML tags including valid `<prosody>`, `<break>`, `<emphasis>` tags.

**Origin:** Commits labeled "fix bug on edge tts" (e.g., `26de378`, `f7141c8`) — the "fix" broke prosody.

### 2.3 llm_generate.py — Prompt Generates Plain Text Only

The `generate_script_response()` prompt instructs the LLM to output plain text:

```
Return ONLY the raw script text. No labels, no numbering.
```

No SSML, no delivery instructions, no prosody annotations.

**Effect:** Even if we fix the pipeline, the LLM never generates SSML.

---

### Summary: Pipeline currently looks like this

```
LLM → Plain script text (no prosody)
  ↓
YouTube.py line 1765 strips < > / → still plain text
  ↓
EdgeTts.synthesize() calls _strip_ssml() → still plain text
  ↓
edge_tts.Communicate(plain_text) → robotic audio, no prosody
```

---

## 3. Proposed Fix

### Option B: LLM Generates SSML Directly (Selected)

The LLM generates SSML with embedded prosody. EdgeTts passes SSML directly to Edge TTS. No prosody is stripped at any point.

### Data Flow (After Fix)

```
LLM → SSML script (e.g., <speak><prosody rate="fast">...</prosody></speak>)
  ↓
YouTube.generate_tts() → bypasses [^\w\s.?!] regex when input starts with "<speak>"
  ↓
EdgeTts.synthesize() → passes SSML directly to edge_tts.Communicate(ssml, voice)
  ↓
Edge TTS renders audio with prosody control
```

---

## 4. Edge TTS SSML Support (Verified)

`edge_tts.Communicate` accepts SSML strings natively. No special configuration needed.

### Supported SSML Tags

| Tag | Attributes | Notes |
|-----|-----------|-------|
| `<prosody>` | `rate`, `pitch`, `volume` | Core prosody control |
| `<break>` | `time` | Explicit pauses |
| `<emphasis>` | `level` | Word-level stress |
| `<say-as>` | `interpret-as` | "whispered", "characters" etc. |

### Prosody Value Formats

| Attribute | Format | Example |
|-----------|--------|---------|
| `rate` | percentage or keyword | `"85%"`, `"fast"`, `"medium"`, `"slow"` |
| `pitch` | semitones or keyword | `"+10st"`, `"-5st"`, `"high"`, `"low"` |
| `volume` | percentage or keyword | `"+3dB"`, `"medium"`, `"loud"`, `"soft"` |

### Constraints
- Rate range: ~20%-200% (outside this may be clamped)
- Pitch: semitone shifts limited to roughly ±50st
- Edge TTS may silently clamp values outside range

---

## 5. Component Changes

### 5.1 llm_generate.py — `generate_script_response()`

**Change:** Add SSML generation instructions to the script prompt.

**New Prompt Structure:**

```
You are generating a YouTube Shorts script with voice delivery prosody.

OUTPUT FORMAT: SSML (Speech Synthesis Markup Language) wrapped in <speak> tags.
Do NOT output plain text. Output valid SSML.

SSML TAGS YOU MAY USE:
- <prosody rate="X%" pitch="±Yst" volume="Z">text</prosody>
  rate: 20%-200% (fast=150%, medium=100%, slow=75%)
  pitch: +5st (higher), -5st (lower)
  volume: +3dB (louder), -3dB (quieter)
- <break time="500ms"/> — pause
- <emphasis level="strong">word</emphasis> — stress
- <say-as interpret-as="whispered">text</say-as> — whisper effect

PROSODY DECISION RULES (model decides per script):
- Hook/first sentence: energetic rate, pause after
- Mystery/tension topics: slower rate, lower pitch, deliberate pacing
- News/urgent topics: faster rate, higher pitch, clipped sentences
- Motivational: building energy, emphasis on key words, pauses before punchlines
- Science/explainer: moderate pace, clear diction, occasional emphasis
- Questions: raised pitch on question word, pause before answer

CONTENT CONSTRAINTS (unchanged):
- Total: {sentence_length} sentences
- Language: {language}
- Target: 60-100 words
- No "welcome", "in this video", "subscribe"
- No markdown, no numbering, plain sentences inside SSML
```

**Return:** Raw SSML string starting with `<speak>`.

**Parsing:** `generate_script_response` returns the raw completion (SSML text). No post-processing of SSML tags — the LLM output is passed through verbatim.

### 5.2 EdgeTts.py — `synthesize()`

**Change:** Remove `_strip_ssml()` and its call. Pass text directly to `edge_tts.Communicate`.

```python
def synthesize(
    self, text: str, output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav")
):
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    text = text.strip()

    # DO NOT strip SSML — Communicate handles both SSML and plain text
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
        tmp_mp3_path = tmp_mp3.name

    try:
        asyncio.run(self._generate_mp3(text, tmp_mp3_path))
        audio, sample_rate = sf.read(tmp_mp3_path)
        sf.write(output_file, audio, sample_rate)
    finally:
        if os.path.exists(tmp_mp3_path):
            os.unlink(tmp_mp3_path)

    return output_file
```

**`_strip_ssml()` method:** Remove entirely.

**Fallback handling:** If Communicate raises an exception (malformed SSML), catch it and retry with plain text. To do this, add:

```python
async def _generate_mp3(self, text: str, output_path: str) -> None:
    try:
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path)
    except Exception as e:
        # If SSML was passed but rejected, try plain text
        # Strip any remaining XML and retry once
        clean_text = re.sub(r"<[^>]+>", "", text)
        clean_text = re.sub(r'\b(rate|pitch|volume)="[^"]+"', "", clean_text)
        communicate = edge_tts.Communicate(clean_text, self._voice)
        await communicate.save(output_path)
```

### 5.3 YouTube.py — `generate_tts()`

**Change:** Guard the `[^\w\s.?!]` regex so it skips SSML inputs.

```python
def generate_tts(self, tts_instance) -> str:
    path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".wav")

    # Only strip non-word chars if text is NOT SSML
    # SSML scripts start with <speak> and must be preserved
    if not self.script.strip().startswith("<speak>"):
        self.script = re.sub(r"[^\w\s.?!]", "", self.script)

    tts_instance.synthesize(self.script, path)
    self.tts_path = path
    return path
```

**Rationale:** If the LLM generates SSML, we need the `<speak>` tag intact. If it's plain text (existing scripts in DB, or non-SSML content), the regex still applies.

---

## 6. SSML Prompt Engineering Guidelines

### 6.1 When to Use Each Prosody Element

| Element | Use Case | Example |
|---------|----------|---------|
| `<prosody rate="fast">` | Excited, news, urgency | `"Breaking news! NASA just announced..."` |
| `<prosody rate="85%">` | Mystery, tension, dramatic reveal | `"But what they found underneath was..."` |
| `<prosody pitch="+5st">` | Questions, excitement, disbelief | `"Did you know that sharks can...?"` |
| `<prosody pitch="-3st">` | Authority, calm explanation | `"The answer lies in quantum physics"` |
| `<break time="500ms"/>` | Scene change, dramatic pause | After hook or before twist |
| `<emphasis level="strong">` | Key terms, punchline words | `"This is the MOST important part"` |
| `<say-as interpret-as="whispered">` | Secrets, suspense, intimate moments | `"But there's one more thing they never told you"` |

### 6.2 Topic-Based Prosody Strategies

The LLM should decide dynamically based on content:

**Mystery:** Slower base rate (85-90%), lower pitch, deliberate pauses, emphasis on reveal words.

**News/Informational:** Medium-faster rate (110-130%), steady pacing, minimal breaks, clear diction.

**Motivational:** Building energy curve — slower opening, faster middle, slower emphatic finish, strategic pauses before punchlines.

**Science/Explainer:** Medium rate (100%), slightly lower pitch for authority, occasional emphasis on technical terms.

**Humor/Witty:** Faster rate with pitch variation, natural breaks at punchline timing.

### 6.3 SSML Quality Guidelines for LLM

- Always wrap in `<speak>...</speak>`
- Nest prosody inside speak, not overlapping
- Use `ms` or `s` for break time (e.g., `500ms`, `1s`)
- Avoid pitch values beyond ±30st
- Rate values outside 50%-200% may be clamped silently
- Test with Edge TTS to verify rendering

---

## 7. Error Handling Strategy

### 7.1 Malformed SSML

If Edge TTS throws an exception on SSML input:
1. Catch the exception
2. Strip remaining XML tags from the input
3. Retry with clean plain text
4. Log warning: "SSML rejected, falling back to plain text"

### 7.2 Empty/Invalid Prosody Values

LLM may generate out-of-range values. Edge TTS clamps silently.
- No pre-validation in Python (trust LLM)
- If output sounds wrong, adjust LLM prompt

### 7.3 Plain Text Input (Backward Compatibility)

If `synthesize()` receives plain text (no `<speak>` tag):
- Pass directly to `Communicate`
- Works as before — no regression

### 7.4 Large SSML Inputs

LLM might generate very long SSML strings. Edge TTS handles large inputs fine. No chunking needed at synthesis layer.

---

## 8. Testing Plan

### 8.1 Unit Tests

| Test | File | What to verify |
|------|------|----------------|
| SSML passthrough | `EdgeTts` | SSML input reaches Communicate unchanged |
| Plain text fallback | `EdgeTts` | Plain text input still works |
| SSML rejection fallback | `EdgeTts` | Invalid SSML falls back to plain text |
| Regex guard | `YouTube` | SSML bypasses regex, plain text doesn't |
| Script generation | `llm_generate` | LLM outputs valid SSML starting with `<speak>` |

### 8.2 Integration Tests

| Test | What to verify |
|------|----------------|
| Full pipeline | Script → SSML → Edge TTS → audio file renders correctly |
| Hook prosody | Audio has slower first sentence, strategic pause after |
| Topic variety | Mystery, news, motivational scripts all render with distinct delivery |

### 8.3 Manual Verification

Run `python3 src/main.py` with a mystery topic and a motivational topic. Compare audio output quality — should hear:
- Mystery: slower, deliberate, pauses before reveals
- Motivational: energy building, emphasis on key words

---

## 9. Files to Modify

| File | Change |
|------|--------|
| `src/llm_generate.py` | Update `generate_script_response()` prompt to output SSML |
| `src/classes/EdgeTts.py` | Remove `_strip_ssml()`, remove strip call, add fallback in `_generate_mp3()` |
| `src/classes/YouTube.py` | Guard regex with `startswith("<speak>")` check |

No changes to `Tts.py`, `run_pipeline.py`, or database schema.

---

## 10. Rollback Plan

If issues arise:
1. Revert `YouTube.py` regex change → SSML stripped again (old behavior)
2. Revert `EdgeTts.py` → re-enable `_strip_ssml()` (old behavior)
3. Revert `llm_generate.py` prompt → plain text output (old behavior)

All three changes are self-contained and independently revertable.

---

## 11. Open Questions

None — all clarified during brainstorming.

---

## 12. Acceptance Criteria

1. LLM generates scripts with embedded SSML prosody tags
2. Scripts starting with `<speak>` bypass the `[^\w\s.?!]` regex in YouTube.py
3. EdgeTts passes SSML directly to `edge_tts.Communicate` without stripping
4. Edge TTS renders audio with dynamic rate, pitch, volume, pauses, and emphasis
5. Plain text scripts (no SSML) continue to work without modification
6. Malformed SSML falls back gracefully to plain text
7. Audio output is noticeably more engaging across mystery, news, motivational, and science topics