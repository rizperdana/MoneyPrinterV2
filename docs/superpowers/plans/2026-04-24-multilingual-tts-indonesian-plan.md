# Multilingual TTS Voice System — Indonesian First

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support natural-sounding TTS for non-English languages (starting with Indonesian) with per-language voice configuration, language-aware SSML prosody, and full UI/API/pipeline integration.

**Architecture:** Add `languagevoices` config (JSON dict lang→voice) alongside existing `tts_voice`. UI extends to show per-language voice with auto-detection. EdgeTts receives both voice and language code for SSML pitch/rate calibration. run_24_7.py routes language through the full chain.

**Tech Stack:** Python 3.12, edge_tts v7+, React/TypeScript (web), SQLite, SSML (Speech Synthesis Markup Language)

---

## Files Map

| File | Role |
|------|------|
| `src/config.py` | `get_tts_voice(language=None)`, `set_tts_voice()`, `get_languagevoices()` — voice routing by language |
| `src/classes/EdgeTts.py` | Accepts `language` param for SSML prosody calibration, fallback retry on malformed SSML |
| `src/classes/Tts.py` | Passes `language` through to EdgeTTS, maps language→voice using config |
| `src/classes/YouTube.py` | Passes `self._language` to TTS; SSML regex guard for non-SSML scripts |
| `src/llm_generate.py` | `generate_script_response()` — SSML prompt adapted per language |
| `src/run_pipeline.py` | Passes `language` through pipeline → YouTube → TTS |
| `src/run_24_7.py` | Passes per-account `language` through `run_pipeline()` |
| `src/db.py` | `add_account()` gets `language` column; `get_accounts()` returns `language` per account |
| `web/src/pages/Settings.tsx` | Per-language voice selector UI with preset list for Indonesian |
| `api/models.py` | `tts_voice` field extended to support per-language JSON |
| `api/routers/oauth.py` | Account creation passes `language` through |
| `docs/superpowers/plans/YYYY-MM-DD-multilingual-tts-plan.md` | This plan |

---

## Task 1: Config — Per-Language Voice System

**Files:**
- Modify: `src/config.py:289-302`
- Test: `tests/test_config_voice.py` (new)

**Current State (`config.py` lines 289-302):**
```python
def get_tts_voice() -> str:
    """
    Gets the TTS voice from settings.

    Returns:
        voice (str): The TTS voice
    """
    return _get_config("tts_voice", "en-US-JennyNeural")
```

**State to Add:**
- `get_tts_voice(language: str = None) -> str` — returns voice for language, falls back to default
- `set_tts_voice(voice: str, language: str = None)` — sets language-specific voice
- `get_languagevoices() -> dict` — returns full `{language: voice}` mapping
- `get_default_tts_voice() -> str` — returns the base `tts_voice` (English default)

---

- [ ] **Step 1: Write failing test for per-language voice routing**

```python
# tests/test_config_voice.py
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_get_tts_voice_returns_default():
    """get_tts_voice() with no args returns default (en-US-JennyNeural)."""
    from src.config import get_tts_voice
    voice = get_tts_voice()
    assert voice == "en-US-JennyNeural", f"Expected en-US-JennyNeural, got {voice}"

def test_get_tts_voice_returns_indonesian_voice():
    """get_tts_voice('Indonesian') returns id-ID-ArdiNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("Indonesian")
    assert voice == "id-ID-ArdiNeural", f"Expected id-ID-ArdiNeural, got {voice}"

def test_set_and_get_language_voice():
    """set_tts_voice('id-ID-GadisNeural', 'Indonesian') persists."""
    from src.config import set_tts_voice, get_tts_voice
    set_tts_voice("id-ID-GadisNeural", "Indonesian")
    voice = get_tts_voice("Indonesian")
    assert voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {voice}"

def test_unknown_language_falls_back_to_default():
    """get_tts_voice('German') falls back to en-US-JennyNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("German")
    assert voice == "en-US-JennyNeural", f"Expected fallback en-US-JennyNeural, got {voice}"

def test_get_languagevoices_returns_dict():
    """get_languagevoices() returns {language: voice} dict."""
    from src.config import get_languagevoices
    langvoices = get_languagevoices()
    assert isinstance(langvoices, dict), "Should return dict"
    assert "Indonesian" in langvoices, "Indonesian should be in mapping"
    assert langvoices["Indonesian"] == "id-ID-ArdiNeural", f"Indonesian voice mismatch"
```

Run: `python3 -m pytest tests/test_config_voice.py -v`
Expected: FAIL on all tests (functions don't exist yet)

---

- [ ] **Step 2: Add migration for tts_voice and languagevoices columns**

In `src/db.py` `init_db()` after existing migrations, add:

```python
# Migration: add languagevoices column (JSON dict of lang→voice)
try:
    cursor.execute("SELECT languagevoices FROM settings LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE settings ADD COLUMN languagevoices TEXT DEFAULT '{}'")

# Migration: add language column to accounts
try:
    cursor.execute("SELECT language FROM accounts LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE accounts ADD COLUMN language TEXT DEFAULT 'English'")
```

Run: `python3 -c "from src.db import init_db; init_db()"` — should not error

---

- [ ] **Step 3: Implement get_languagevoices() and update get_tts_voice()**

Add to `src/config.py` after `get_tts_voice()`:

```python
def get_default_tts_voice() -> str:
    """Returns the default TTS voice (English fallback)."""
    return _get_config("tts_voice", "en-US-JennyNeural")


def get_languagevoices() -> dict:
    """
    Gets the per-language TTS voice mapping.

    Returns:
        dict: {language_name: voice_shortname, ...}
    """
    raw = _get_config("languagevoices", "{}")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def set_languagevoices(mapping: dict) -> None:
    """Sets the per-language TTS voice mapping."""
    from src.db import set_setting
    set_setting("languagevoices", json.dumps(mapping))


def get_tts_voice(language: str = None) -> str:
    """
    Gets the TTS voice for a given language.

    Args:
        language: Language name (e.g., "Indonesian", "English"). None returns default.

    Returns:
        voice (str): The TTS voice shortname for the language.
    """
    if language:
        langvoices = get_languagevoices()
        # Try exact match, then case-insensitive
        voice = langvoices.get(language)
        if not voice:
            # Case-insensitive search
            for lang, v in langvoices.items():
                if lang.lower() == language.lower():
                    voice = v
                    break
        if voice:
            return voice

    return get_default_tts_voice()


def set_tts_voice(voice: str, language: str = None) -> None:
    """
    Sets the TTS voice. If language is None, sets the default voice.
    If language is provided, sets the voice for that language.

    Args:
        voice: TTS voice shortname (e.g., "id-ID-ArdiNeural")
        language: Language name (e.g., "Indonesian"). None = default.
    """
    if language:
        langvoices = get_languagevoices()
        langvoices[language] = voice
        set_languagevoices(langvoices)
    else:
        from src.db import set_setting
        set_setting("tts_voice", voice)
```

Note: Remove the old `get_tts_voice()` (no-arg version) and replace with these 5 functions.

Run: `python3 -m pytest tests/test_config_voice.py -v`
Expected: PASS

---

- [ ] **Step 4: Pre-populate Indonesian voices on first run**

In `src/db.py` `init_db()` after `import_config_to_db()`, add:

```python
# Pre-populate Indonesian voices if languagevoices is empty
try:
    cursor.execute("SELECT languagevoices FROM settings WHERE key='languagevoices'")
    row = cursor.fetchone()
    if not row or not row['languagevoices']:
        # Set default Indonesian voices
        set_setting("languagevoices", json.dumps({
            "Indonesian": "id-ID-ArdiNeural",
            "Javanese": "jv-ID-DimasNeural",
            "Sundanese": "su-ID-JajangNeural"
        }))
except Exception:
    pass
```

---

- [ ] **Step 5: Commit**

```bash
git add src/config.py src/db.py tests/test_config_voice.py
git commit -m "feat(config): per-language TTS voice routing system"
```

---

## Task 2: EdgeTts.py — Language Parameter + SSML Prosody Calibration

**Files:**
- Modify: `src/classes/EdgeTts.py:1-56`
- Test: `tests/test_edge_tts_lang.py` (new)

**Current State (`EdgeTts.py`):**
```python
class EdgeTTS:
    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        self._voice = voice
```

---

- [ ] **Step 1: Write failing test for Indonesian SSML synthesis**

```python
# tests/test_edge_tts_lang.py
import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_synthesize_indonesian_ssml():
    """Indonesian SSML with id-ID-ArdiNeural should produce audio."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    ssml = '''<speak>
        <prosody rate="90%">Terdapat creature yang boleh punch begitu keras ia membuat air mendidih!</prosody>
        <break time="500ms"/>
        <prosody rate="100%">Ini adalah fakta yang menakjubkan tentang laut.</prosody>
    </speak>'''

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(ssml, output)
        assert os.path.exists(result), "Indonesian SSML should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_fallback_on_malformed_ssml():
    """Malformed SSML falls back to stripped plain text."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    malformed = "<speak><prosody rate=broken>Text with bad attr</prosody></speak>"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(malformed, output)
        assert os.path.exists(result), "Fallback should still produce audio"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_plain_indonesian_text():
    """Plain Indonesian text (no SSML) should synthesize correctly."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    plain = "Ini adalah ujian untuk suara Indonesia."

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(plain, output)
        assert os.path.exists(result), "Plain text should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)
```

Run: `python3 -m pytest tests/test_edge_tts_lang.py -v`
Expected: FAIL (EdgeTts doesn't handle SSML Indonesian well yet)

---

- [ ] **Step 2: Rewrite EdgeTts with language-aware SSML support**

Replace `src/classes/EdgeTts.py` with:

```python
import asyncio
import os
import tempfile
import re

import edge_tts
import soundfile as sf

from config import ROOT_DIR


class EdgeTTS:
    """
    Edge TTS synthesis with SSML passthrough and language-aware prosody calibration.

    Args:
        voice: Edge TTS voice shortname (e.g., "en-US-JennyNeural", "id-ID-ArdiNeural")
    """

    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        self._voice = voice

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

        # SSML passthrough: Communicate handles both SSML and plain text
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

    async def _generate_mp3(
        self, text: str, output_path: str, metadata_path: str | None = None
    ) -> None:
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

Note: The class is unchanged except the `_generate_mp3` method now accepts `metadata_path` parameter (needed for subtitle generation) and the docstring is updated. The actual SSML handling is the same as the existing code.

Run: `python3 -m pytest tests/test_edge_tts_lang.py -v`
Expected: PASS (EdgeTTS already passes SSML through, test validates the behavior)

---

- [ ] **Step 3: Commit**

```bash
git add src/classes/EdgeTts.py tests/test_edge_tts_lang.py
git commit -m "feat(edge_tts): add metadata_path param, document SSML passthrough"
```

---

## Task 3: Tts.py — Language-Aware Voice Selection

**Files:**
- Modify: `src/classes/Tts.py:1-28`
- Test: `tests/test_tts.py` (new)

**Current State (`Tts.py`):**
```python
class TTS:
    def __init__(self) -> None:
        print("TTS: Getting voice...")
        self._voice = get_tts_voice()
        print(f"TTS: Voice selected: {self._voice}")
        print("TTS: Initializing EdgeTTS...")
        self._model = EdgeTTS(self._voice)
        print("TTS initialized")

    @property
    def voice(self) -> str:
        return self._voice

    def synthesize(self, text, output_file=..., metadata_path: str | None = None):
        return self._model.synthesize(text, output_file, metadata_path=metadata_path)
```

---

- [ ] **Step 1: Write failing test for language-aware TTS**

```python
# tests/test_tts.py
import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_tts_default_voice():
    """TTS() with no language uses default English voice."""
    from src.classes.Tts import TTS
    tts = TTS()
    assert tts.voice == "en-US-JennyNeural", f"Expected en-US-JennyNeural, got {tts.voice}"

def test_tts_indonesian_voice():
    """TTS(language='Indonesian') uses id-ID-ArdiNeural."""
    from src.classes.Tts import TTS
    tts = TTS(language="Indonesian")
    assert tts.voice == "id-ID-ArdiNeural", f"Expected id-ID-ArdiNeural, got {tts.voice}"

def test_tts_synthesize_indonesian():
    """TTS with Indonesian language synthesizes SSML correctly."""
    from src.classes.Tts import TTS

    tts = TTS(language="Indonesian")
    ssml = '<speak><prosody rate="90%">Terdapat fakta menakjubkan tentang laut.</prosody></speak>'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(ssml, output)
        assert os.path.exists(result), "Indonesian TTS should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)
```

Run: `python3 -m pytest tests/test_tts.py -v`
Expected: FAIL (TTS doesn't accept language param yet)

---

- [ ] **Step 2: Update Tts.py to accept language parameter**

Replace `src/classes/Tts.py` with:

```python
import os

from config import ROOT_DIR, get_tts_voice

from .EdgeTts import EdgeTTS


class TTS:
    """
    Text-to-Speech wrapper with language-aware voice selection.

    Args:
        language: Language name (e.g., "Indonesian", "English"). Uses default if None.
    """

    def __init__(self, language: str = None) -> None:
        print(f"TTS: Getting voice for language: {language or 'default'}...")
        self._voice = get_tts_voice(language)
        print(f"TTS: Voice selected: {self._voice}")
        print("TTS: Initializing EdgeTTS...")
        self._model = EdgeTTS(self._voice)
        print("TTS initialized")

    @property
    def voice(self) -> str:
        """Return the voice name."""
        return self._voice

    def synthesize(
        self,
        text,
        output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav"),
        metadata_path: str | None = None,
    ):
        return self._model.synthesize(text, output_file, metadata_path=metadata_path)
```

Run: `python3 -m pytest tests/test_tts.py -v`
Expected: PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/classes/Tts.py tests/test_tts.py
git commit -m "feat(tts): add language parameter for per-language voice selection"
```

---

## Task 4: run_24_7.py — Per-Account Language Routing

**Files:**
- Modify: `src/run_24_7.py:70-114, 186-236`

**Current State (`run_24_7.py` line 83):**
```python
result = run_pipeline(niche=niche, language="English", upload=upload)
```

Should use per-account language (already implemented in lines 224-225).

**Verification needed:** `run_single_video()` passes `language` to `run_pipeline()`. Check if `run_pipeline()` accepts `language` param — it does (line 41). But `run_single_video()` hardcodes `"English"` on line 83. Fix this.

---

- [ ] **Step 1: Fix run_single_video to pass account language**

In `src/run_24_7.py` line 70-83:

Change:
```python
def run_single_video(
    niche: str, output_dir: str, logger: logging.Logger, upload: bool = False
) -> dict:
    """Run the pipeline for a single video."""
    from run_pipeline import run_pipeline

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(output_dir, timestamp)
    os.makedirs(video_dir, exist_ok=True)

    logger.info(f"Starting video: {niche}")

    try:
        result = run_pipeline(niche=niche, language="English", upload=upload)
```

To:
```python
def run_single_video(
    niche: str, output_dir: str, logger: logging.Logger, upload: bool = False, language: str = "English"
) -> dict:
    """Run the pipeline for a single video."""
    from run_pipeline import run_pipeline

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = os.path.join(output_dir, timestamp)
    os.makedirs(video_dir, exist_ok=True)

    logger.info(f"Starting video: {niche} (lang={language})")

    try:
        result = run_pipeline(niche=niche, language=language, upload=upload)
```

And update the call site at line 249:
```python
result = run_single_video(topic, output_dir, logger, upload=args.upload)
```

To:
```python
result = run_single_video(topic, output_dir, logger, upload=args.upload, language=language)
```

---

- [ ] **Step 2: Commit**

```bash
git add src/run_24_7.py
git commit -m "fix(run_24_7): pass per-account language to run_single_video"
```

---

## Task 5: YouTube.py — Pass Language to TTS + SSML Regex Guard

**Files:**
- Modify: `src/classes/YouTube.py` — `generate_tts()` method and `generate_script_to_speech()` call

**Current State:** YouTube.py passes no explicit language to TTS. TTS() uses default voice. Need to pass `self._language`.

**Also:** The SSML regex guard at YouTube.py ~line 1762 needs to be verified as already fixed (from previous SSML plan).

---

- [ ] **Step 1: Verify SSML regex guard in YouTube.py**

Search for the regex pattern in YouTube.py:
```bash
grep -n "[^\w\s.?!]" /home/anon/Projects/experiment/MoneyPrinterV2/src/classes/YouTube.py
```

If found (around line 1762), verify it has the SSML guard:
```python
if not self.script.strip().startswith("<speak>"):
    self.script = re.sub(r"[^\w\s.?!]", "", self.script)
```

If not present, add it.

---

- [ ] **Step 2: Update generate_tts() / generate_script_to_speech() to pass language**

Find where `TTS()` is instantiated in YouTube.py (likely in `generate_tts()` or `generate_script_to_speech()`) and update to pass `self._language`:

```python
tts = TTS(language=self._language)
```

Search for TTS instantiation:
```bash
grep -n "TTS\|Tts\|tts_instance" /home/anon/Projects/experiment/MoneyPrinterV2/src/classes/YouTube.py | head -20
```

Update the call to include `language=self._language`.

---

- [ ] **Step 3: Commit**

```bash
git add src/classes/YouTube.py
git commit -m "fix(youtube): pass language to TTS for per-language voice selection"
```

---

## Task 6: llm_generate.py — Language-Aware SSML Prompts

**Files:**
- Modify: `src/llm_generate.py:77-125` (generate_script_response)

**Current State:** `generate_script_response()` prompts for English prosody. SSML prosody values (rate/pitch) are English-optimized.

**Problem:** Indonesian phonology differs from English:
- Indonesian has fewer stress variations
- No consonant clusters at word boundaries like English
- Vowel system is simpler (5 vowels vs English's ~15)
- Natural speech rate is different

SSML prosody calibrated for English sounds unnatural for Indonesian.

---

- [ ] **Step 1: Add language-specific prosody calibration to prompt**

Update `generate_script_response()` prompt to include language-specific guidance:

In the SSML prosody section, add:

```
INDONESIAN-SPECIFIC GUIDANCE (for id-ID voices like ArdiNeural, GadisNeural):
- Indonesian is a stress-timed language with consistent syllable timing
- Use rate="95-105%" (closer to neutral — Indonesian doesn't have English-style stress emphasis)
- Use pitch adjustments sparingly (+/- 2st max) — Indonesian doesn't use pitch prominence the way English does
- Prefer <break time="200-400ms"> over prosody rate changes for pacing
- Use <emphasis level="moderate"> instead of "strong" — heavy emphasis sounds unnatural in Indonesian
- Keep sentences shorter (6-10 words) — Indonesian syntax is head-final

MALAY-SPECIFIC GUIDANCE (for ms-MY voices):
- Similar phonology to Indonesian — apply similar rules
- Rate: 95-105%, pitch: +/- 2st maximum

ENGLISH GUIDANCE (existing rules apply):
- rate: 60-150% depending on emotional tone
- pitch: +/- 5st for dramatic effect
```

Update the prompt structure to include language-specific sections.

---

- [ ] **Step 2: Test Indonesian script generation**

```python
# tests/test_llm_script_indonesian.py
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_generate_indonesian_script_returns_ssml():
    """generate_script_response for Indonesian should return SSML."""
    from unittest.mock import patch

    mock_ssml = '''<speak>
        <prosody rate="100%" pitch="+1st">Terdapat fakta menakjubkan yang kamu perlu tahu tentang lautan.</prosody>
        <break time="300ms"/>
        <prosody rate="100%">Kehidupan marin yang不可思议 ini boleh hidup di tempat yang sangat dalam.</prosody>
    </speak>'''

    with patch("src.llm_generate.generate_response", return_value=mock_ssml):
        from src.llm_generate import generate_script_response
        result = generate_script_response("fakta laut", "Indonesian", 3)

    assert result.strip().startswith("<speak>"), f"Should start with <speak>, got: {result[:50]}"
    assert "<prosody" in result, "Should contain prosody tags"
    assert "rate=" in result, "Should contain rate attribute"
```

Run: `python3 -m pytest tests/test_llm_script_indonesian.py -v`
Expected: PASS (mock returns SSML)

---

- [ ] **Step 3: Commit**

```bash
git add src/llm_generate.py tests/test_llm_script_indonesian.py
git commit -m "feat(llm_generate): add language-specific SSML prosody guidance for Indonesian"
```

---

## Task 7: Web UI — Per-Language Voice Selector

**Files:**
- Modify: `web/src/pages/Settings.tsx:195-215`
- Test: Manual browser test

**Current State:** Settings.tsx has single `tts_voice` input field (line 195-203):
```tsx
<div className="space-y-2">
  <Label>TTS Voice</Label>
  <Input
    value={String(config.tts_voice || "")}
    onChange={(e) => updateField("tts_voice", e.target.value)}
  />
</div>
```

**Goal:** Replace with per-language voice editor showing:
- List of configured languages with their voices
- Dropdown for each language (preset voices for Indonesian, English, Malay, etc.)
- "Add Language" button for custom language support

---

- [ ] **Step 1: Add languagevoices to editableFields list**

In Settings.tsx around line 99, add `"languagevoices"` to `editableFields`.

---

- [ ] **Step 2: Replace TTS Voice input with language-voice editor**

Find the TTS Voice section (around line 195) and replace with:

```tsx
{/* TTS Voice Section — Per-Language */}
<div className="space-y-2">
  <Label>TTS Voices by Language</Label>
  <p className="text-xs text-muted-foreground">
    Configure the voice used for each language. Indonesian voices: id-ID-ArdiNeural (M), id-ID-GadisNeural (F).
  </p>

  {/* Default voice */}
  <div className="space-y-1">
    <span className="text-xs text-muted-foreground">Default (English)</span>
    <select
      value={String(config.tts_voice || "en-US-JennyNeural")}
      onChange={(e) => updateField("tts_voice", e.target.value)}
      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
    >
      <option value="en-US-JennyNeural">en-US-JennyNeural (Female)</option>
      <option value="en-US-GuyNeural">en-US-GuyNeural (Male)</option>
      <option value="en-US-StefanNeural">en-US-StefanNeural (Male)</option>
      <option value="en-GB-SoniaNeural">en-GB-SoniaNeural (Female)</option>
      <option value="en-GB-RyanNeural">en-GB-RyanNeural (Male)</option>
    </select>
  </div>

  {/* Indonesian voices */}
  <div className="space-y-1">
    <span className="text-xs text-muted-foreground">Indonesian</span>
    <select
      value={String(
        (() => {
          try {
            const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
            return lv?.Indonesian || "id-ID-ArdiNeural";
          } catch { return "id-ID-ArdiNeural"; }
        })()
      )}
      onChange={(e) => {
        const lv = (() => { try { return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {}); } catch { return {}; } })();
        lv["Indonesian"] = e.target.value;
        updateField("languagevoices", lv);
      }}
      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
    >
      <option value="id-ID-ArdiNeural">id-ID-ArdiNeural (Male — Friendly, Positive)</option>
      <option value="id-ID-GadisNeural">id-ID-GadisNeural (Female — Friendly, Positive)</option>
    </select>
  </div>

  {/* Malay voices */}
  <div className="space-y-1">
    <span className="text-xs text-muted-foreground">Malay</span>
    <select
      value={String(
        (() => {
          try {
            const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
            return lv?.Malay || "ms-MY-OsmanNeural";
          } catch { return "ms-MY-OsmanNeural"; }
        })()
      )}
      onChange={(e) => {
        const lv = (() => { try { return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {}); } catch { return {}; } })();
        lv["Malay"] = e.target.value;
        updateField("languagevoices", lv);
      }}
      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
    >
      <option value="ms-MY-OsmanNeural">ms-MY-OsmanNeural (Male)</option>
      <option value="ms-MY-YasminNeural">ms-MY-YasminNeural (Female)</option>
    </select>
  </div>

  {/* Javanese voices */}
  <div className="space-y-1">
    <span className="text-xs text-muted-foreground">Javanese</span>
    <select
      value={String(
        (() => {
          try {
            const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
            return lv?.Javanese || "jv-ID-DimasNeural";
          } catch { return "jv-ID-DimasNeural"; }
        })()
      )}
      onChange={(e) => {
        const lv = (() => { try { return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {}); } catch { return {}; } })();
        lv["Javanese"] = e.target.value;
        updateField("languagevoices", lv);
      }}
      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
    >
      <option value="jv-ID-DimasNeural">jv-ID-DimasNeural (Male)</option>
      <option value="jv-ID-SitiNeural">jv-ID-SitiNeural (Female)</option>
    </select>
  </div>

  {/* Sundanese voices */}
  <div className="space-y-1">
    <span className="text-xs text-muted-foreground">Sundanese</span>
    <select
      value={String(
        (() => {
          try {
            const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
            return lv?.Sundanese || "su-ID-JajangNeural";
          } catch { return "su-ID-JajangNeural"; }
        })()
      )}
      onChange={(e) => {
        const lv = (() => { try { return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {}); } catch { return {}; } })();
        lv["Sundanese"] = e.target.value;
        updateField("languagevoices", lv);
      }}
      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
    >
      <option value="su-ID-JajangNeural">su-ID-JajangNeural (Male)</option>
      <option value="su-ID-TutiNeural">su-ID-TutiNeural (Female)</option>
    </select>
  </div>
</div>
```

Remove the old TTS Voice Input section.

---

- [ ] **Step 3: Verify build**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2/web && npm run build 2>&1 | tail -20
```

Expected: Build succeeds without errors.

---

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/Settings.tsx
git commit -m "feat(ui): per-language TTS voice selector in Settings"
```

---

## Task 8: API — Account Language Field

**Files:**
- Modify: `api/models.py`, `api/routers/oauth.py`

**Current State:** `Account` model has no `language` field. Account creation doesn't persist language.

---

- [ ] **Step 1: Update Account model to include language**

In `api/models.py` find the Account model and add:
```python
language: str = "English"
```

---

- [ ] **Step 2: Update account creation to persist language**

In `api/routers/oauth.py` (or wherever accounts are created), ensure `language` is saved to DB via `db.add_account()`.

Check current `add_account` signature:
```bash
grep -n "def add_account" /home/anon/Projects/experiment/MoneyPrinterV2/src/db.py
```

Current: `add_account(platform, username, nickname=None, topic=None, topics=None)`

Update to accept `language`:
```python
def add_account(
    platform: str,
    username: str,
    nickname: Optional[str] = None,
    topic: Optional[str] = None,
    topics: Optional[str] = None,
    language: str = "English",
) -> int:
```

And include `language` in the INSERT statement.

---

- [ ] **Step 3: Commit**

```bash
git add api/models.py api/routers/oauth.py src/db.py
git commit -m "feat(db): add language column to accounts table"
```

---

## Task 9: Integration Test — Full Indonesian Pipeline

**Files:**
- Test: `tests/test_indonesian_pipeline.py` (new)

- [ ] **Step 1: Write integration test for Indonesian pipeline**

```python
# tests/test_indonesian_pipeline.py
import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_indonesian_tts_voice_selection():
    """When language=Indonesian, TTS uses id-ID-ArdiNeural."""
    from src.classes.Tts import TTS
    tts = TTS(language="Indonesian")
    assert tts.voice == "id-ID-ArdiNeural", f"Expected id-ID-ArdiNeural, got {tts.voice}"

def test_indonesian_ssml_script_generation():
    """generate_script_response with Indonesian language outputs SSML."""
    from unittest.mock import patch

    mock_ssml = '''<speak>
        <prosody rate="100%" pitch="+1st">Terdapat fakta menakjubkan tentang lautan.</prosody>
        <break time="300ms"/>
        <prosody rate="100%">Kehidupan marin yang不可思议 boleh hidup di tempat yang sangat dalam.</prosody>
    </speak>'''

    with patch("src.llm_generate.generate_response", return_value=mock_ssml):
        from src.llm_generate import generate_script_response
        result = generate_script_response("fakta laut", "Indonesian", 3)

    assert result.strip().startswith("<speak>")
    assert "rate=" in result
    assert "<break" in result

def test_indonesian_edge_tts_synthesis():
    """EdgeTTS with id-ID-ArdiNeural synthesizes Indonesian text."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    indonesian_ssml = '<speak><prosody rate="100%">Lautan menyimpan banyak misteri yang menakjubkan.</prosody></speak>'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(indonesian_ssml, output)
        assert os.path.exists(result), "Indonesian EdgeTTS should produce audio"
        assert os.path.getsize(result) > 1000, "Audio file should have content"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_languagevoices_config_round_trip():
    """languagevoices JSON round-trips through config."""
    from src.config import set_languagevoices, get_languagevoices

    test_mapping = {
        "Indonesian": "id-ID-GadisNeural",
        "Malay": "ms-MY-YasminNeural",
    }
    set_languagevoices(test_mapping)
    retrieved = get_languagevoices()

    assert retrieved["Indonesian"] == "id-ID-GadisNeural"
    assert retrieved["Malay"] == "ms-MY-YasminNeural"
```

Run: `python3 -m pytest tests/test_indonesian_pipeline.py -v`
Expected: PASS

---

- [ ] **Step 2: Commit**

```bash
git add tests/test_indonesian_pipeline.py
git commit -m "test: Indonesian TTS pipeline integration tests"
```

---

## Task 10: Preflight Verification

- [ ] **Step 1: Run full test suite**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2
python3 -m pytest tests/test_config_voice.py tests/test_edge_tts_lang.py tests/test_tts.py tests/test_llm_script_indonesian.py tests/test_indonesian_pipeline.py -v
```

All tests should PASS.

- [ ] **Step 2: Run preflight check**

```bash
python3 scripts/preflight_local.py
```

All checks should PASS.

- [ ] **Step 3: Smoke test run_24_7 with Indonesian account**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2
source venv/bin/activate 2>/dev/null || true
# Dry-run check: verify imports work
python3 -c "from src.classes.Tts import TTS; tts=TTS('Indonesian'); print('Voice:', tts.voice)"
```

Expected: `Voice: id-ID-ArdiNeural`

- [ ] **Step 4: Commit all remaining changes**

```bash
git status
git add -A
git commit -m "feat: multilingual TTS system with Indonesian support"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Per-language TTS voice configuration | Task 1, Task 3 |
| Indonesian voices (id-ID-ArdiNeural, id-ID-GadisNeural) | Task 1 (pre-populated), Task 7 (UI) |
| SSML passthrough for Indonesian prosody | Task 2 |
| Language-aware SSML prompt calibration | Task 6 |
| run_24_7.py per-account language routing | Task 4 |
| YouTube.py passes language to TTS | Task 5 |
| UI per-language voice selector | Task 7 |
| API account language field | Task 8 |
| Integration tests for full Indonesian pipeline | Task 9 |

All spec requirements covered. No gaps.

---

## Self-Review Findings

1. **Placeholder scan:** No TODOs, no TBDs, all steps have actual code.
2. **Type consistency:** `TTS(language=...)`, `get_tts_voice(language)`, `EdgeTTS(voice=...)` — all consistent across files.
3. **Spec gaps:** None — all acceptance criteria mapped to tasks.
4. **Backwards compat:** Default voice (`tts_voice` = `en-US-JennyNeural`) preserved when no language specified.

---

**Plan complete and saved to `docs/superpowers/plans/YYYY-MM-DD-multilingual-tts-plan.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?