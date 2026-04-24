# Externalize Hardcoded Values Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all hardcoded prompts, model names, timeouts, retries, UI selectors, and magic numbers with settings lookups via `config.py`, enabling full user customization without code changes.

**Architecture:** Flat config accessor functions in `config.py` + one `SETTINGS_SPEC` dict defining all settings (name, type, default). No nested dicts, no runtime JSON validation — just typed accessors. LLM prompts live as constants in `llm_prompts.py` module, loaded via `get_prompt()` helper.

> **DB-Only Architecture Note:** All settings are stored in SQLite in-memory DB via `db.py`. `config.json` is **deprecated** — it is only read once during `import_config_to_db()` (one-time migration) and never again. All code reads settings through `config.py` → `db.py`. The **only exception** is `scripts/retry_pending_uploads.py` which still reads `config.json` directly for `firefox_profile` — this will be fixed in Task 11.

**Tech Stack:** Python 3.12, SQLite in-memory DB (`db.py`), existing `_get_config()` infrastructure.

---

## Current State: DB-Only Config

| Location | Status | Notes |
|---|---|---|
| `src/config.py` → `db.py` | ✓ DB-only | All settings via `_get_config()` |
| `src/` (all other modules) | ✓ DB-only | Read through `config.py` |
| `db.py::import_config_to_db()` | ✓ Migration only | Runs once when DB is empty |
| `scripts/preflight_local.py` | ✓ Uses `config.py` | No direct config.json read |
| `scripts/retry_pending_uploads.py` | ✗ Direct read | Reads `config.json` for `firefox_profile` |
| `scripts/migrate_config_to_db.py` | ✓ Migration only | One-time use, deprecated |

---

## File Structure

```
src/config.py          # ADD: all new getter functions, SETTINGS_SPEC dict
src/llm_prompts.py     # CREATE: all prompt templates as module constants
src/classes/YouTube.py  # MODIFY: replace hardcoded values with config.py calls
src/classes/Twitter.py  # MODIFY: replace hardcoded values with config.py calls
src/classes/Reddit.py   # MODIFY: replace hardcoded values with config.py calls
src/classes/Outreach.py # MODIFY: replace hardcoded values with config.py calls
src/classes/PostBridge.py # MODIFY: replace hardcoded values with config.py calls
src/llm_provider.py    # MODIFY: replace hardcoded MODEL_ROUTING, timeouts, retries
src/llm_generate.py    # MODIFY: replace hardcoded prompts with get_prompt()
src/constants.py       # MODIFY: replace hardcoded constants with config.py calls
scripts/retry_pending_uploads.py  # MODIFY: use config.py instead of direct config.json read
```

---

## Gap Analysis Before Tasks

### Gap 1: Prompt Library vs Scattered Constants
Currently prompts are inline strings in `llm_generate.py` and `YouTube.py`. If user wants to customize one phrase, they'd have to edit multi-line template strings. **Solution:** Extract all prompts to `src/llm_prompts.py` as named constants. Add `get_prompt(name, **kwargs)` function that handles interpolation.

### Gap 2: Model Routing Is List-of-Tuples
`MODEL_ROUTING` in `llm_provider.py` is a dict mapping job→priority→model. Hardcoded model names appear in 3 places: routing dict, ultimate fallback list, per-job timeout dict. **Solution:** Models become settings `llm.routing.{job}.{priority}` and `llm.fallbacks` list.

### Gap 3: YouTube Selectors in constants.py
CSS selectors and XPath expressions for YouTube upload form are hardcoded in `constants.py`. These break when YouTube changes their UI. **Solution:** Move to `youtube.selectors.*` settings.

### Gap 4: Pollinations/Cloudflare Image Params
Image generation params (zimage vs flux size, nologo flag, enhancement suffix) are buried in `YouTube.py` method bodies. **Solution:** Group into `image.pollinations.*` and `image.cloudflare.*` settings groups.

### Gap 5: Ken Burns Motion Params
Zoom ranges, pan ranges, twist ratios are inline math with magic numbers. **Solution:** `video.ken_burns.*` settings group.

### Gap 6: Subtitle Styling
Font size, color, stroke color, stroke width are hardcoded in video generation. **Solution:** `video.subtitle.*` settings group.

### Gap 7: No Default Settings Registry
There's no single place documenting all available settings, their types, and defaults. **Solution:** `SETTINGS_SPEC` dict in `config.py` as the authoritative registry.

### Gap 8: LLM Prompt Interpolation
Prompts have dynamic parts (target_audience, sentence_length, etc.) embedded directly in the template strings. **Solution:** `get_prompt()` helper accepts kwargs and formats templates with them.

---

## Tasks

### Task 1: Create `src/llm_prompts.py` — Prompt Centralization

**Files:**
- Create: `src/llm_prompts.py`
- Test: `tests/test_llm_prompts.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_prompts.py
def test_get_prompt_topic_with_research():
    result = get_prompt("topic_with_research", research_summary="AI is growing")
    assert "AI is growing" in result
    assert "Elementary school" in result

def test_get_prompt_topic_no_research():
    result = get_prompt("topic_no_research")
    assert "Elementary school" in result

def test_get_prompt_script():
    result = get_prompt("script", sentence_length=12, max_words_per_sentence=12, max_total_words=100)
    assert "12" in result

def test_get_prompt_title():
    result = get_prompt("title_retry")
    assert "50 characters" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_prompts.py -v`
Expected: FAIL — `No module named 'src.llm_prompts'`

- [ ] **Step 3: Create `src/llm_prompts.py`** with all prompt constants:

```python
# src/llm_prompts.py
"""All LLM prompt templates centralized. Use get_prompt() to retrieve."""

TOPIC_WITH_RESEARCH = """I need you to act as a content researcher for a viral YouTube channel...
[full prompt from llm_generate.py:35-54]
"""

TOPIC_NO_RESEARCH = """Create a viral curiosity-driven YouTube topic about...
[full prompt from llm_generate.py:56-72]
"""

SCRIPT = """Create a short viral YouTube video script...
[full prompt from llm_generate.py:89-146]
"""

TITLE_RETRY = """Generate a YouTube title that is...
[full prompt from llm_generate.py:170-189]
"""

YOUTUBE_TOPIC_WITH_RESEARCH = """[full prompt from YouTube.py:562-597]
"""

YOUTUBE_TOPIC_NO_RESEARCH = """[full prompt from YouTube.py:604-630]
"""

SEO_KEYWORDS = """[full prompt from YouTube.py:1166]
"""

TWITTER_POST = """[full prompt from Twitter.py:215]
"""

# ... all other prompts extracted from their original locations
```

- [ ] **Step 4: Add `get_prompt()` helper**

```python
def get_prompt(prompt_name: str, **kwargs) -> str:
    """Retrieve prompt by name, formatting with kwargs if provided."""
    prompt_map = {
        "topic_with_research": TOPIC_WITH_RESEARCH,
        "topic_no_research": TOPIC_NO_RESEARCH,
        "script": SCRIPT,
        "title_retry": TITLE_RETRY,
        "youtube_topic_with_research": YOUTUBE_TOPIC_WITH_RESEARCH,
        "youtube_topic_no_research": YOUTUBE_TOPIC_NO_RESEARCH,
        "seo_keywords": SEO_KEYWORDS,
        "twitter_post": TWITTER_POST,
        # ... all others
    }
    template = prompt_map.get(prompt_name)
    if template is None:
        raise ValueError(f"Unknown prompt: {prompt_name}")
    return template.format(**kwargs) if kwargs else template
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_llm_prompts.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm_prompts.py tests/test_llm_prompts.py
git commit -m "feat: centralize all LLM prompts in llm_prompts.py"
```

---

### Task 2: Add `SETTINGS_SPEC` Registry to `config.py`

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_settings.py
def test_settings_spec_exists():
    from src.config import SETTINGS_SPEC
    assert isinstance(SETTINGS_SPEC, dict)
    assert len(SETTINGS_SPEC) > 100  # we have 200+ settings

def test_settings_spec_has_required_fields():
    from src.config import SETTINGS_SPEC
    for key, spec in SETTINGS_SPEC.items():
        assert "default" in spec, f"{key} missing 'default'"
        assert "type" in spec, f"{key} missing 'type'"
        assert spec["type"] in ("str", "int", "float", "bool", "list", "dict"), f"{key} unknown type"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_settings.py::test_settings_spec_exists -v`
Expected: FAIL — `SETTINGS_SPEC` not defined

- [ ] **Step 3: Add `SETTINGS_SPEC` to `config.py`**

```python
# src/config.py — ADD after imports

SETTINGS_SPEC: dict[str, dict] = {
    # ── LLM Provider ──────────────────────────────────────────────
    "llm.cliproxy_api_key":         {"type": "str",  "default": ""},
    "llm.base_url":                {"type": "str",  "default": "http://localhost:8317/v1"},
    "llm.default_timeout":         {"type": "float","default": 180.0},
    "llm.list_models_timeout":     {"type": "float","default": 30.0},
    "llm.max_retries":             {"type": "int",   "default": 2},
    "llm.retry_delay":             {"type": "float","default": 3.0},
    "llm.fallback_model":          {"type": "str",  "default": "kilo-auto/free"},
    "llm.ultimate_fallbacks":      {"type": "list", "default": ["kilo-auto/free", "gpt-4o-free", "gpt-4.1-free"]},
    # Job-specific timeouts
    "llm.job_timeouts.image_prompts": {"type": "float", "default": 60.0},
    # Model routing
    "llm.routing.topic.1":          {"type": "str",  "default": "bytedance-seed/dola-seed-2.0-pro:free"},
    "llm.routing.topic.2":          {"type": "str",  "default": "qwen/qwen3-next-80b-a3b-instruct:free"},
    "llm.routing.topic.3":          {"type": "str",  "default": "arcee-ai/trinity-large-thinking:free"},
    "llm.routing.script.1":         {"type": "str",  "default": "qwen/qwen3-next-80b-a3b-instruct:free"},
    "llm.routing.image_prompts.0":  {"type": "str",  "default": "gpt-4o-free"},
    # Spinner
    "llm.spinner_chars":            {"type": "list", "default": ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]},
    # ── LLM Generate / Prompts ───────────────────────────────────
    "llm.prompts.topic_with_research":    {"type": "str", "default": ""},  # loaded from llm_prompts.py
    "llm.prompts.topic_no_research":       {"type": "str", "default": ""},
    "llm.prompts.script":                 {"type": "str", "default": ""},
    "llm.prompts.title_rules":            {"type": "str", "default": "Under 50 characters. MUST be 3-8 words"},
    "llm.prompts.title_retry":             {"type": "str", "default": ""},
    "llm.prompts.description_hashtag_count": {"type": "str", "default": "3-5"},
    "llm.prompts.tags_count":              {"type": "str", "default": "10-15"},
    "llm.script.target_audience":         {"type": "str", "default": "Elementary school children (ages 6-10)"},
    "llm.script.max_words_per_sentence":   {"type": "int", "default": 12},
    "llm.script.max_total_words":          {"type": "int", "default": 100},
    # Image prompts
    "llm.prompts.image.gen_model":         {"type": "str", "default": "Z-Image Turbo (pollinations.ai zimage model)"},
    "llm.prompts.image.params":            {"type": "str", "default": "num_inference_steps=12, acceleration=high, image_size=landscape_16_9"},
    "llm.prompts.image.num_scenes":        {"type": "str", "default": "1 to {n_scenes}"},
    "llm.prompts.image.target_length":     {"type": "str", "default": "80-250"},
    "llm.prompts.image.max_prompts":       {"type": "int", "default": 12},
    "llm.topic.min_length":               {"type": "int", "default": 20},
    # YouTube-specific prompts
    "llm.prompts.youtube_topic_with_research": {"type": "str", "default": ""},
    "llm.prompts.youtube_topic_no_research":   {"type": "str", "default": ""},
    "llm.prompts.mystery_tone":            {"type": "str", "default": "I found something strange..."},
    "llm.prompts.seo_keywords":            {"type": "str", "default": ""},
    "llm.prompts.seo_example":              {"type": "str", "default": ""},
    # Twitter
    "llm.prompts.twitter_post":             {"type": "str", "default": ""},
    # ── YouTube / Browser ─────────────────────────────────────────
    "browser.geckodriver_path":            {"type": "str",  "default": "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0/geckodriver"},
    "browser.selenium_timeout":            {"type": "int",   "default": 30},
    # ── YouTube / Search ───────────────────────────────────────────
    "search.tavily.api_key":               {"type": "str",  "default": ""},
    "search.tavily.max_results":           {"type": "int",   "default": 8},
    "search.exa.api_key":                  {"type": "str",  "default": ""},
    "search.exa.max_results":              {"type": "int",   "default": 8},
    "search.ddgs.max_results":            {"type": "int",   "default": 8},
    "search.wikipedia.api_url":           {"type": "str",  "default": "https://en.wikipedia.org/api/rest_v1/feed/featured"},
    "search.request_timeout":              {"type": "float","default": 5.0},
    "search.google_trends.url":            {"type": "str",  "default": "https://trends.google.com/trends/rss"},
    "search.firecrawl.api_key":            {"type": "str",  "default": ""},
    "search.firecrawl.max_results":        {"type": "int",   "default": 8},
    # ── YouTube / Video ────────────────────────────────────────────
    "video.target_duration_sec":          {"type": "str",  "default": "20-30"},
    "video.max_words":                    {"type": "int",   "default": 120},
    "video.max_sentences":                {"type": "int",   "default": 8},
    "video.images_per_video":             {"type": "int",   "default": 8},
    "video.target_sentences":             {"type": "str",  "default": "6-8"},
    "video.words_per_second":              {"type": "float","default": 2.5},
    "video.title.min_chars":              {"type": "int",   "default": 60},
    "video.title.max_chars":              {"type": "int",   "default": 125},
    "video.title.starters":               {"type": "list", "default": ["This","Why","How","What","Scientists Found","Hidden"]},
    "video.title.padding_suffix":        {"type": "str",  "default": " — Strange But True"},
    "video.description.paragraphs":      {"type": "str",  "default": "1-3"},
    "video.max_tags":                     {"type": "int",   "default": 15},
    "video.image_prompt.max_words":      {"type": "str",  "default": "15-25"},
    "video.fps":                          {"type": "int",   "default": 30},
    "video.music_volume":                 {"type": "float","default": 0.1},
    "video.audio.mix":                    {"type": "str",  "default": "tts+music"},
    # ── YouTube / Image Generation ────────────────────────────────
    "image.pollinations.api_key":         {"type": "str",  "default": ""},
    "image.pollinations.zimage_cost":    {"type": "str",  "default": "0.002"},
    "image.pollinations.zimage_size":    {"type": "str",  "default": "1080x1920"},
    "image.pollinations.nologo":         {"type": "bool", "default": True},
    "image.pollinations.flux_size":       {"type": "str",  "default": "1080x1920"},
    "image.enhancement_suffix":          {"type": "str",  "default": "Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting..."},
    "image.request_timeout":             {"type": "int",   "default": 120},
    "image.min_size_bytes":              {"type": "int",   "default": 1000},
    "image.delay_between_requests":       {"type": "int",   "default": 2},
    "image.cloudflare.worker_url":       {"type": "str",  "default": ""},
    "image.cloudflare.api_key":          {"type": "str",  "default": ""},
    "image.cloudflare.model_chain":      {"type": "list", "default": [["phoenix-1.0","Leonardo Phoenix 1.0"],["flux-1-schnell","FLUX.1 Schnell"]]},
    "image.cloudflare.request_timeout":  {"type": "int",   "default": 120},
    # ── YouTube / Thumbnail ────────────────────────────────────────
    "video.thumbnail.font_size_ratio":    {"type": "float","default": 0.06},
    "video.thumbnail.shadow_offset":      {"type": "int",   "default": 3},
    # ── YouTube / Ken Burns ────────────────────────────────────────
    "video.ken_burns.zoom_range":         {"type": "float","default": 0.12},
    "video.ken_burns.twist_start_ratio":  {"type": "float","default": 0.67},
    "video.ken_burns.twist_zoom_range":   {"type": "list", "default": [0.80, 1.20]},
    "video.ken_burns.twist_pan_range":     {"type": "float","default": 0.12},
    "video.ken_burns.normal_zoom_range":  {"type": "list", "default": [0.88, 1.12]},
    "video.ken_burns.normal_pan_range":    {"type": "float","default": 0.08},
    "video.source_scale_factor":          {"type": "float","default": 1.25},
    "video.resolution":                   {"type": "str",  "default": "1080x1920"},
    # ── YouTube / Subtitle ────────────────────────────────────────
    "video.subtitle.font_size":           {"type": "int",   "default": 100},
    "video.subtitle.color":               {"type": "str",  "default": "#FFFF00"},
    "video.subtitle.stroke_color":        {"type": "str",  "default": "black"},
    "video.subtitle.stroke_width":        {"type": "int",   "default": 5},
    "video.subtitle.font_size_small":     {"type": "int",   "default": 80},
    "video.output_pattern":               {"type": "str",  "default": ".mp/{uuid}.mp4"},
    "video.encoding.threads":             {"type": "int",   "default": 2},
    # ── YouTube / STT ──────────────────────────────────────────────
    "stt.assemblyai.config":              {"type": "dict", "default": {}},
    "stt.whisper.device":                 {"type": "str",  "default": "cpu"},
    "stt.whisper.compute_type":           {"type": "str",  "default": "int8"},
    "stt.whisper.transcribe_options":     {"type": "dict", "default": {"vad_filter": True, "word_timestamps": True}},
    # ── Twitter ───────────────────────────────────────────────────
    "twitter.selectors.text_box":         {"type": "list", "default": ["div[data-offset-key]"]},  # TODO: actual selectors
    "twitter.selectors.post_button":     {"type": "list", "default": ["div[data-testid]"]},      # TODO: actual selectors
    "twitter.delays.after_post":         {"type": "int",   "default": 2},
    "twitter.delays.after_nav":           {"type": "int",   "default": 2},
    "twitter.delays.after_media_upload": {"type": "int",   "default": 3},
    "twitter.delays.after_post_media":   {"type": "int",   "default": 2},
    "twitter.max_post_length":            {"type": "int",   "default": 260},
    "twitter.truncate_suffix":           {"type": "str",  "default": "..."},
    "twitter.subreddit_hashtags":        {"type": "dict", "default": {}},  # TODO: actual defaults
    "twitter.reddit_hashtags":           {"type": "dict", "default": {}},
    "twitter.caption.max_length_llm":     {"type": "int",   "default": 200},
    "twitter.caption.max_text_len":      {"type": "int",   "default": 280},
    "twitter.caption.hard_limit":        {"type": "int",   "default": 280},
    # ── Reddit ─────────────────────────────────────────────────────
    "reddit.min_score":                   {"type": "int",   "default": 100},
    "reddit.default_subreddits":         {"type": "list", "default": ["memes","dankmemes","ProgrammerHumor"]},
    "reddit.user_agent":                  {"type": "str",  "default": "MoneyPrinterV2/1.0"},
    "reddit.headers.User-Agent":         {"type": "str",  "default": "MoneyPrinterV2/1.0 (Reddit to Twitter Bot)"},
    "reddit.fetch_limit":                {"type": "int",   "default": 10},
    "reddit.request_timeout":            {"type": "int",   "default": 30},
    "reddit.delays.between_requests":    {"type": "int",   "default": 1},
    "reddit.media_download_timeout":     {"type": "int",   "default": 60},
    "reddit.min_download_size":          {"type": "int",   "default": 1000},
    "reddit.max_downloads":             {"type": "int",   "default": 5},
    "reddit.delays.between_downloads":    {"type": "int",   "default": 1},
    "reddit.caption_hashtags":           {"type": "dict", "default": {}},
    "reddit.caption.max_length_llm":     {"type": "int",   "default": 200},
    "reddit.caption.max_text_len":      {"type": "int",   "default": 280},
    "reddit.caption.hard_limit":        {"type": "int",   "default": 280},
    # ── Outreach ───────────────────────────────────────────────────
    "outreach.scraper.binary_name":      {"type": "str",  "default": "google-maps-scraper"},  # platform-dependent
    "outreach.scraper.timeout":          {"type": "int",   "default": 300},
    "outreach.delays.after_scrape":      {"type": "int",   "default": 2},
    # ── PostBridge ─────────────────────────────────────────────────
    "postbridge.api_base":               {"type": "str",  "default": "https://api.post-bridge.com/v1"},
    "postbridge.retryable_codes":        {"type": "set",  "default": {429, 500, 502, 503, 504}},
    "postbridge.max_retries":            {"type": "int",   "default": 3},
    "postbridge.timeout.media_upload":   {"type": "int",   "default": 600},
    "postbridge.timeout.default":         {"type": "int",   "default": 60},
    "postbridge.retry_delay_factor":     {"type": "float","default": 0.5},
    # ── Constants / Selectors ─────────────────────────────────────
    "youtube.constants.textbox_id":      {"type": "str",  "default": "textbox"},
    "youtube.constants.made_for_kids":  {"type": "str",  "default": "VIDEO_MADE_FOR_KIDS_MFK"},
    "youtube.constants.not_made_for_kids": {"type": "str", "default": "VIDEO_MADE_FOR_KIDS_NOT_MFK"},
    "youtube.constants.next_button_id":  {"type": "str",  "default": "next-button"},
    "youtube.constants.done_button_id":  {"type": "str",  "default": "done-button"},
    "youtube.constants.radio_button_xpath": {"type": "str", "default": ""},
    "tiktok.constants.upload_button":    {"type": "str",  "default": ""},
    "tiktok.constants.textbox_id":       {"type": "str",  "default": ""},
    "tiktok.constants.next_button":      {"type": "str",  "default": ""},
    "tiktok.constants.done_button":       {"type": "str",  "default": ""},
    "tiktok.constants.title_input":      {"type": "str",  "default": ""},
    "tiktok.constants.description":      {"type": "str",  "default": ""},
    "tiktok.constants.hashtags":         {"type": "str",  "default": ""},
    "amazon.constants.product_title_id":  {"type": "str",  "default": "productTitle"},
    "amazon.constants.feature_bullets_id": {"type": "str", "default": "feature-bullets"},
    "twitter.constants.textarea_class":   {"type": "str",  "default": "public-DraftStyleDefault-block public-DraftStyleDefault-ltr"},
    "twitter.constants.post_button_xpath": {"type": "str", "default": ""},
}
```

Also add a helper:

```python
def get_setting_spec(key: str) -> dict | None:
    """Return the spec for a setting key, or None if not found."""
    return SETTINGS_SPEC.get(key)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config_settings.py
git commit -m "feat: add SETTINGS_SPEC registry to config.py"
```

---

### Task 3: Add Config Accessor Functions for New Settings

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config_accessors.py`

- [ ] **Step 1: Write failing tests for each new accessor**

```python
# tests/test_config_accessors.py
def test_get_llm_routing():
    from src.config import get_llm_routing
    routing = get_llm_routing("topic")
    assert isinstance(routing, dict)
    assert 1 in routing

def test_get_llm_job_timeout():
    from src.config import get_llm_job_timeout
    assert get_llm_job_timeout("image_prompts") == 60.0
    assert get_llm_job_timeout("unknown_job") == 180.0

def test_get_browser_geckodriver_path():
    from src.config import get_browser_geckodriver_path
    path = get_browser_geckodriver_path()
    assert isinstance(path, str)

# ... similar tests for each new accessor
```

- [ ] **Step 2: Add accessor functions to `config.py`**

Grouped by concern:

```python
# ── LLM Routing ──────────────────────────────────────────────────
def get_llm_routing(job: str) -> dict[int, str]:
    """Get model routing for a job type. Returns dict of priority -> model."""
    routing = {
        "topic": {
            1: _get_config("llm.routing.topic.1", "bytedance-seed/dola-seed-2.0-pro:free"),
            2: _get_config("llm.routing.topic.2", "qwen/qwen3-next-80b-a3b-instruct:free"),
            3: _get_config("llm.routing.topic.3", "arcee-ai/trinity-large-thinking:free"),
        },
        "script": {
            1: _get_config("llm.routing.script.1", "qwen/qwen3-next-80b-a3b-instruct:free"),
        },
        "image_prompts": {
            0: _get_config("llm.routing.image_prompts.0", "gpt-4o-free"),
        },
    }
    return routing.get(job, {})

def get_llm_ultimate_fallbacks() -> list[str]:
    val = _get_config("llm.ultimate_fallbacks")
    if isinstance(val, list):
        return val
    return ["kilo-auto/free", "gpt-4o-free", "gpt-4.1-free"]

def get_llm_job_timeout(job: str) -> float:
    defaults = {
        "image_prompts": 60.0,
    }
    return _get_config(f"llm.job_timeouts.{job}", defaults.get(job, 180.0))

def get_llm_default_timeout() -> float:
    return float(_get_config("llm.default_timeout", 180.0))

def get_llm_max_retries() -> int:
    return int(_get_config("llm.max_retries", 2))

def get_llm_retry_delay() -> float:
    return float(_get_config("llm.retry_delay", 3.0))

def get_llm_spinner_chars() -> list[str]:
    val = _get_config("llm.spinner_chars")
    if isinstance(val, list):
        return val
    return ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

def get_llm_base_url() -> str:
    return _get_config("llm.base_url", "http://localhost:8317/v1")

def get_llm_fallback_model() -> str:
    return _get_config("llm.fallback_model", "kilo-auto/free")

# ... continue for all other settings groups
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_config_accessors.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/config.py tests/test_config_accessors.py
git commit -m "feat: add config accessors for all hardcoded values"
```

---

### Task 4: Update `llm_provider.py` to Use Config Accessors

**Files:**
- Modify: `src/llm_provider.py`
- Test: `tests/test_llm_provider.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_llm_provider.py
def test_generate_text_uses_config_timeout():
    # Patch config to return a specific timeout, verify it's used
    pass

def test_model_routing_comes_from_config():
    # Patch config, verify routing picks up new values
    pass
```

- [ ] **Step 2: Update `llm_provider.py` imports and MODEL_ROUTING**

Replace hardcoded `MODEL_ROUTING` dict at line ~210 with:

```python
from src.config import (
    get_llm_routing,
    get_llm_ultimate_fallbacks,
    get_llm_default_timeout,
    get_llm_job_timeout,
    get_llm_max_retries,
    get_llm_retry_delay,
    get_llm_spinner_chars,
    get_llm_base_url,
    get_llm_fallback_model,
)

MODEL_ROUTING = {
    "topic": {},
    "script": {},
    "seo_tags": {},
    "image_prompts": {},
    "title_desc": {},
}

# Populate from config (lazy — done on first call)
def _get_model_routing() -> dict:
    for job in MODEL_ROUTING:
        MODEL_ROUTING[job] = get_llm_routing(job)
    return MODEL_ROUTING
```

Replace all `timeout=180.0` etc. with `timeout=get_llm_default_timeout()`.

Replace `range(2)` with `range(get_llm_max_retries())`.

Replace `_time.sleep(3)` with `_time.sleep(get_llm_retry_delay())`.

Replace spinner list with `get_llm_spinner_chars()`.

Replace fallback list with `get_llm_ultimate_fallbacks()`.

Replace base URL with `get_llm_base_url()`.

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_llm_provider.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/llm_provider.py tests/test_llm_provider.py
git commit -m "refactor: llm_provider reads all hardcoded values from config"
```

---

### Task 5: Update `llm_generate.py` to Use `get_prompt()`

**Files:**
- Modify: `src/llm_generate.py`
- Test: `tests/test_llm_generate.py`

- [ ] **Step 1: Write failing test**

```python
def test_generate_topic_with_research_uses_prompt_module():
    # Verify prompts come from llm_prompts.py, not inline strings
    pass
```

- [ ] **Step 2: Replace inline prompts with `get_prompt()` calls**

Replace:
```python
trend_prompt = TOPIC_WITH_RESEARCH_PROMPT  # inline string
```
With:
```python
from src.llm_prompts import get_prompt
trend_prompt = get_prompt("topic_with_research", research_summary=...)
```

Replace hardcoded values with config accessors:
```python
target_audience = _get_config("llm.script.target_audience", "Elementary school children (ages 6-10)")
max_words_per_sentence = _get_config("llm.script.max_words_per_sentence", 12)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_llm_generate.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/llm_generate.py tests/test_llm_generate.py
git commit -m "refactor: llm_generate uses get_prompt() from llm_prompts.py"
```

---

### Task 6: Update `classes/YouTube.py` — 100+ Replacements

**Files:**
- Modify: `src/classes/YouTube.py`
- Test: `tests/test_youtube_config.py`

This is the largest task. Group changes by concern:

**6a. Browser/Selenium** (lines ~161-168):
```python
# BEFORE
self._browser = webdriver.Firefox(executable_path="/home/anon/.cache/selenium/geckodriver/linux64/0.36.0/geckodriver")
WebDriverWait(self._browser, 30)

# AFTER
from src.config import get_browser_geckodriver_path, get_browser_selenium_timeout
geckodriver_path = get_browser_geckodriver_path()
self._browser = webdriver.Firefox(executable_path=geckodriver_path)
WebDriverWait(self._browser, get_browser_selenium_timeout())
```

**6b. Search providers** (lines ~301-476):
```python
# BEFORE
os.environ.get("TAVILY_API_KEY", "")
max_results=8

# AFTER
from src.config import get_tavily_api_key, get_tavily_max_results
api_key = get_tavily_api_key()
max_results = get_tavily_max_results()
```

**6c. Video params** (lines ~761-1065):
Extract all `video.target_duration_sec`, `video.max_words`, etc. to config accessors.

**6d. Image generation** (lines ~1463-1599):
```python
# BEFORE
os.environ.get("POLLINATIONS_API_KEY", "")
"0.002 pts/image"
width=1080&height=1920
&nologo=true
timeout=120

# AFTER
from src.config import get_pollinations_api_key, get_image_params...
api_key = get_pollinations_api_key()
params = get_image_pollinations_params()  # returns dict with zimage_cost, size, nologo, timeout
```

**6e. Ken Burns** (lines ~2120-2143):
```python
# BEFORE
zoom: start at 1.0x, end at 1.0 +/- 0.12x

# AFTER
from src.config import get_ken_burns_zoom_range
zoom_range = get_ken_burns_zoom_range()
zoom_end = random.uniform(1.0 - zoom_range, 1.0 + zoom_range)
```

**6f. Subtitle styling** (lines ~2066-2073):
```python
# BEFORE
fontsize=100
color="#FFFF00"
stroke_color="black"
stroke_width=5

# AFTER
from src.config import get_subtitle_config
cfg = get_subtitle_config()  # returns dict with font_size, color, stroke_color, stroke_width
fontsize = cfg["font_size"]
```

**6g. Thumbnail** (lines ~1759-1772):
```python
# BEFORE
font_size = max(48, int(720 * 0.06))
shadow_offset = 3

# AFTER
from src.config import get_thumbnail_config
cfg = get_thumbnail_config()
font_size = max(48, int(720 * cfg["font_size_ratio"]))
shadow_offset = cfg["shadow_offset"]
```

**6h. Cloudflare model chain** (lines ~1581-1599):
```python
# BEFORE
("phoenix-1.0", "Leonardo Phoenix 1.0")
("flux-1-schnell", "FLUX.1 Schnell")

# AFTER
from src.config import get_cloudflare_model_chain
model_chain = get_cloudflare_model_chain()
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_youtube_config.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/classes/YouTube.py tests/test_youtube_config.py
git commit -m "refactor: YouTube.py externalizes 100+ hardcoded values to config"
```

---

### Task 7: Update `classes/Twitter.py`

**Files:**
- Modify: `src/classes/Twitter.py`
- Test: `tests/test_twitter_config.py`

- [ ] Replace selectors (lines ~106-129) with `get_twitter_selector("text_box")`, `get_twitter_selector("post_button")`
- [ ] Replace delays with `get_twitter_delay("after_post")`, etc.
- [ ] Replace max_post_length, truncate_suffix, caption limits
- [ ] Replace hashtag dicts
- [ ] Replace prompt with `get_prompt("twitter_post", topic=..., language=...)`

```python
# BEFORE
time.sleep(2)  # after_post
f"Generate a Twitter post about: {self.topic} in {get_twitter_language()}..."

# AFTER
from src.config import get_twitter_delay, get_twitter_max_post_length
time.sleep(get_twitter_delay("after_post"))
from src.llm_prompts import get_prompt
prompt = get_prompt("twitter_post", topic=self.topic, language=get_twitter_language())
```

---

### Task 8: Update `classes/Reddit.py`

**Files:**
- Modify: `src/classes/Reddit.py`
- Test: `tests/test_reddit_config.py`

- [ ] Replace min_score, default_subreddits, user_agent, headers
- [ ] Replace timeouts and delays
- [ ] Replace download limits and size thresholds
- [ ] Replace caption limits

---

### Task 9: Update `classes/Outreach.py`

**Files:**
- Modify: `src/classes/Outreach.py`
- Test: `tests/test_outreach_config.py`

- [ ] Replace binary_name, timeout, delays

---

### Task 10: Update `classes/PostBridge.py`

**Files:**
- Modify: `src/classes/PostBridge.py`
- Test: `tests/test_postbridge_config.py`

- [ ] Replace API_BASE, RETRYABLE_STATUS_CODES, max_retries, timeouts, retry_delay_factor

---

### Task 11: Update `constants.py`

**Files:**
- Modify: `src/constants.py`
- Test: `tests/test_constants_config.py`

- [ ] Replace all `_*_CLASS`, `_*_XPATH`, `_*_ID` constants with config lookups:

```python
# BEFORE
TWITTER_TEXTAREA_CLASS = "public-DraftStyleDefault-block..."
YOUTUBE_TEXTBOX_ID = "textbox"

# AFTER
from src.config import get_youtube_selector, get_twitter_selector
YOUTUBE_TEXTBOX_ID = get_youtube_selector("textbox_id")
TWITTER_TEXTAREA_CLASS = get_twitter_selector("textarea_class")
```

Note: Some constants (like XPath expressions) may be too fragile for runtime config. Mark those as `readonly` in SETTINGS_SPEC and document that they require code changes if YouTube/Twitter updates their UI.

---

### Task 12: Fix `scripts/retry_pending_uploads.py` — Remove Direct `config.json` Read

**Files:**
- Modify: `scripts/retry_pending_uploads.py`

**Why:** This script is the only remaining direct reader of `config.json` in the codebase (outside of migration). It reads `firefox_profile` directly instead of using `config.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_retry_pending_uploads.py
def test_no_direct_config_json_read(monkeypatch):
    """Verify the script imports config from config.py, not config.json directly."""
    import subprocess
    result = subprocess.run(
        ["grep", "-n", "config.json", "scripts/retry_pending_uploads.py"],
        capture_output=True, text=True
    )
    assert result.returncode != 0, f"Still reading config.json directly: {result.stdout}"
```

- [ ] **Step 2: Verify test fails**

Run: `grep -n "config.json" scripts/retry_pending_uploads.py`
Expected: Line with `config_path = os.path.join(ROOT, "config.json")`

- [ ] **Step 3: Replace direct config.json read with config.py**

```python
# BEFORE (lines 14-18)
config_path = os.path.join(ROOT, "config.json")
import json
with open(config_path) as f:
    config = json.load(f)
fp = config.get("firefox_profile", "")

# AFTER
from src.config import get_firefox_profile_path
fp = get_firefox_profile_path()
```

Also remove the now-unused `import json`.

- [ ] **Step 4: Verify test passes**

Run: `grep -n "config.json" scripts/retry_pending_uploads.py`
Expected: no output (config.json no longer referenced)

- [ ] **Step 5: Commit**

```bash
git add scripts/retry_pending_uploads.py tests/test_retry_pending_uploads.py
git commit -m "fix(retry_pending_uploads): use config.py instead of direct config.json read"
```

---

### Task 13: Delete `config.json` — Final Cleanup

**Files:**
- Delete: `config.json`

**Why:** After all 12 tasks above, all settings live in the SQLite DB. `config.json` is no longer read by any code path (migration only runs once on fresh DB). Delete it to prevent accidental future use.

- [ ] **Step 1: Verify DB is populated and all settings are readable**

Run: `python3 -c "from src.db import get_settings; s = get_settings(); print(f'DB has {len(s)} settings'); print('llm_base_url:', s.get('llm_base_url', 'NOT FOUND'))"`
Expected: DB has many settings, `llm_base_url` is readable

- [ ] **Step 2: Verify no code reads config.json**

Run: `grep -rn "config.json" src/ scripts/ --include="*.py" | grep -v "migrate_config_to_db\|config.json is deprecated\|# deprecated\|Migration\|deprecated\|one-time"`
Expected: only `scripts/migrate_config_to_db.py` references (for the migration logic itself)

- [ ] **Step 3: Delete config.json**

```bash
git rm config.json
git commit -m "chore: remove deprecated config.json — all settings now in DB"
```

- [ ] **Step 4: Update .gitignore if config.json is tracked**

If `config.json` appears in `.gitignore`, remove the entry (it should already be ignored, but verify).

---

## Self-Review Checklist

After completing all tasks:

1. **Spec coverage:** Every hardcoded value from the explorer report now has a corresponding entry in `SETTINGS_SPEC` and a config accessor function.
2. **No placeholders:** All steps have actual code, file paths, and expected outputs.
3. **Type consistency:** All `_get_config()` calls use the correct type casting (`int()`, `float()`, `bool()`, `list()`, `dict()`) matching the spec type.
4. **Circular import avoidance:** `config.py` does NOT import from `llm_prompts.py` — prompts are loaded via a lazy import inside `get_prompt()`.
5. **Backward compatibility:** Existing `config.json` values for old keys (e.g., `llm_model`, `llm_base_url`) still work via `_get_config()` falling back to old keys while new dot-notation keys are added.
6. **Test coverage:** Each task includes a test that verifies the value comes from config, not hardcoded.

---

## Execution Options

**Plan complete.** Two execution approaches:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task (Tasks 1-13), review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
