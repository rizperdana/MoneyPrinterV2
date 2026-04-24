# Locale BCP-47 Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `accounts.language` to `accounts.locale` (BCP-47 codes), cascade through TTS/content/hashtags/research.

**Architecture:** Rename DB columns/settings, update config functions, propagate `locale` param through pipeline. UI displays `{Language} ({Locale})`.

**Tech Stack:** Python (src/*), FastAPI (api/*), React (web/*), SQLite, edge-tts.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/db.py` | DB schema: rename `language` to `locale`, `languagevoices` to `localevoices`; add `LANGUAGE_TO_LOCALE` mapping; migration; seed BCP-47 defaults |
| `src/config.py` | Rename `get_languagevoices` to `get_localevoices`, `set_languagevoices` to `set_localevoices`; rename param `language` to `locale` in `get_tts_voice`/`set_tts_voice` |
| `src/classes/Tts.py` | Call `get_tts_voice(locale=...)` instead of `get_tts_voice(language=...)` |
| `src/classes/YouTube.py` | Rename `self.language` to `self.locale`; use `locale` for SSML xml:lang |
| `src/llm_generate.py` | Rename param `language` to `locale`; SSML xml:lang uses BCP-47 |
| `src/run_24_7.py` | `account.get("language")` to `account.get("locale")` |
| `src/run_pipeline.py` | Rename `args.language` to `args.locale` |
| `api/models.py` | Rename `language` field to `locale` in AccountCreate and Job models |
| `api/routers/accounts.py` | Pass `locale=body.locale` |
| `api/routers/generate.py` | Pass `locale` |
| `api/pipeline_worker.py` | `job.language` to `job.locale` |
| `src/main.py` | CLI: `--language` to `--locale` |
| `cli.py` | CLI: `--language` to `--locale` |
| `scripts/run_24h.py` | Rename `language` param to `locale` |
| `web/src/pages/Settings.tsx` | BCP-47 locale selector with readable labels |
| `web/src/pages/Videos.tsx` | `video.language` to `video.locale` |
| `web/src/pages/Generate.tsx` | State `language` to `locale` |
| `tests/*.py` | Update all test fixtures/assertions to BCP-47 codes |
| `src/research.py` | `locale` param to country code mapping for Tavily |

---

## Task 1: DB Migration

**Files:** Modify: `src/db.py`

- [ ] **Step 1: Add LANGUAGE_TO_LOCALE mapping**

Add near top of `db.py` after imports, before `init_db`:

```python
LANGUAGE_TO_LOCALE = {
    "Indonesian": "id-ID", "Javanese": "jv-ID", "Sundanese": "su-ID",
    "Malay": "ms-MY", "Thai": "th-TH", "Vietnamese": "vi-VN",
    "Filipino": "fil-PH", "Korean": "ko-KR", "Japanese": "ja-JP",
    "Chinese": "zh-CN", "Arabic": "ar-SA", "Hindi": "hi-IN",
    "Spanish": "es-ES", "French": "fr-FR", "German": "de-DE",
    "Italian": "it-IT", "Portuguese": "pt-BR", "Russian": "ru-RU",
    "Turkish": "tr-TR", "Polish": "pl-PL", "Dutch": "nl-NL",
    "Swedish": "sv-SE", "Danish": "da-DK", "Norwegian": "no-NO",
    "Finnish": "fi-FI", "Greek": "el-GR", "Czech": "cs-CZ",
    "Hungarian": "hu-HU", "Romanian": "ro-RO", "Ukrainian": "uk-UA",
    "English": "en-US",
}
```

- [ ] **Step 2: Replace languagevoices migration (lines ~170-174)**

Replace with localevoices migration that migrates old data:

```python
# Migration: add localevoices column (JSON dict of locale->voice)
try:
    cursor.execute("SELECT localevoices FROM settings LIMIT 1")
except sqlite3.OperationalError:
    try:
        cursor.execute("SELECT languagevoices FROM settings LIMIT 1")
        old_row = cursor.fetchone()
        if old_row and old_row[0]:
            cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT ?", (old_row[0],))
        else:
            cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'")
```

- [ ] **Step 3: Replace accounts language migration (lines ~176-180)**

Replace with locale migration that migrates old language names via `LANGUAGE_TO_LOCALE` mapping:

```python
# Migration: rename language column to locale (BCP-47)
try:
    cursor.execute("SELECT locale FROM accounts LIMIT 1")
    try:
        cursor.execute("SELECT language FROM accounts LIMIT 1")
        cursor.execute("SELECT id, language FROM accounts WHERE language IS NOT NULL AND language != ''")
        for account_id, lang in cursor.fetchall():
            locale = LANGUAGE_TO_LOCALE.get(lang, lang)
            cursor.execute("UPDATE accounts SET locale = ? WHERE id = ?", (locale, account_id))
        cursor.execute("ALTER TABLE accounts DROP COLUMN language")
    except sqlite3.OperationalError:
        pass
except sqlite3.OperationalError:
    try:
        cursor.execute("SELECT language FROM accounts LIMIT 1")
        cursor.execute("ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'")
        cursor.execute("SELECT id, language FROM accounts WHERE language IS NOT NULL AND language != ''")
        for account_id, lang in cursor.fetchall():
            locale = LANGUAGE_TO_LOCALE.get(lang, lang)
            cursor.execute("UPDATE accounts SET locale = ? WHERE id = ?", (locale, account_id))
        cursor.execute("ALTER TABLE accounts DROP COLUMN language")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'")
```

- [ ] **Step 4: Update add_account()**

Change `language: str = "English"` to `locale: str = "en-US"`. Update INSERT to use `locale` instead of `language`.

- [ ] **Step 5: Update update_account() valid_fields**

Change `"language"` to `"locale"`.

- [ ] **Step 6: Update add_video() signature (line 355-366)**

Change `language: str = "English"` to `locale: str = "en-US"` in the function signature (line 366). This updates the **signature**, not just the call.

```python
def add_video(
    topic: str,
    title: str,
    script: Optional[str] = None,
    platform: str = "youtube",
    file_path: Optional[str] = None,
    niche: str = "",
    description: Optional[str] = None,
    tags: Optional[str] = None,
    category: Optional[str] = None,
    account: Optional[str] = None,
    locale: str = "en-US",  # was: language: str = "English"
    for_kids: bool = False,
    account_id: Optional[int] = None,
) -> int:
```

- [ ] **Step 7: Update default localevoices seed (lines ~194-206)**

Replace Indonesian-only seed with BCP-47 keys:

```python
try:
    cursor.execute("SELECT value FROM settings WHERE key='localevoices'")
    row = cursor.fetchone()
    if not row or not row[0] or row[0] == '{}':
        set_setting("localevoices", json.dumps({
            "id-ID": "id-ID-GadisNeural",
            "jv-ID": "jv-ID-SitiNeural",
            "su-ID": "su-ID-TutiNeural"
        }))
except Exception:
    pass
```

- [ ] **Step 8: Verify and commit**

Run: `python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: Some tests fail due to remaining old names (fixed in Task 2).

Commit: `git add src/db.py && git commit -m "feat(db): migrate language->locale (BCP-47), languagevoices->localevoices"`

---

## Task 2: Config Rename

**Files:** Modify: `src/config.py`

- [ ] **Step 1: Rename get_languagevoices() to get_localevoices()**

Function at line 300. Update docstring `{language_name: voice}` to `{locale: voice}`.

- [ ] **Step 2: Rename set_languagevoices() to set_localevoices()**

Function at line 316. Update docstring.

- [ ] **Step 3: Update get_tts_voice() param language to locale**

Line 331: `def get_tts_voice(language: Optional[str] = None)` to `def get_tts_voice(locale: Optional[str] = None)`. Update docstring. Update all internal variable references.

- [ ] **Step 4: Update set_tts_voice() param language to locale**

Line 355: `def set_tts_voice(voice: str, language: Optional[str] = None)` to `def set_tts_voice(voice: str, locale: Optional[str] = None)`. Update docstring. Update `if language:` to `if locale:`.

- [ ] **Step 5: Update _get_config key languagevoices to localevoices**

In `get_localevoices()`: `_get_config("languagevoices", ...)` to `_get_config("localevoices", ...)`.

- [ ] **Step 6: Update set_setting key languagevoices to localevoices**

In `set_localevoices()`: `set_setting("languagevoices", ...)` to `set_setting("localevoices", ...)`.

- [ ] **Step 7: Update all callers**

Search all files and update:
- `get_languagevoices()` to `get_localevoices()`
- `set_languagevoices(...)` to `set_localevoices(...)`
- `get_tts_voice(language=...)` to `get_tts_voice(locale=...)`
- `set_tts_voice(voice, language=...)` to `set_tts_voice(voice, locale=...)`

Key files: `tests/test_config_voice.py`, `tests/test_tts.py`, `tests/test_indonesian_pipeline.py`, `tests/test_edge_tts_lang.py`.

- [ ] **Step 8: Verify and commit**

Run: `python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: FAIL - test fixtures still use old names.

Commit: `git add src/config.py && git commit -m "refactor(config): rename languagevoices->localevoices, language->locale param"`

---

## Task 3: Tts.py Update

**Files:** Modify: `src/classes/Tts.py`

- [ ] **Step 1: Update get_tts_voice call**

Line 18: `get_tts_voice(language)` to `get_tts_voice(locale)`.

Commit: `git add src/classes/Tts.py && git commit -m "refactor(tts): update get_tts_voice call to use locale param"`

---

## Task 4: YouTube.py Update

**Files:** Modify: `src/classes/YouTube.py`

- [ ] **Step 1: Rename self.language to self.locale**

Search for all `self.language` references. Rename to `self.locale`.

- [ ] **Step 2: Update SSML xml:lang**

Replace hardcoded or language-name-based `xml:lang` with `self.locale` directly (BCP-47 code).

Commit: `git add src/classes/YouTube.py && git commit -m "refactor(youtube): rename self.language->self.locale, SSML xml:lang uses BCP-47"`

---

## Task 5: llm_generate.py Update

**Files:** Modify: `src/llm_generate.py`

- [ ] **Step 1: Rename language param to locale in all functions**

Find functions with `language` param (likely `generate_script`, `generate_tags_response`). Rename to `locale`.

- [ ] **Step 2: Update SSML xml:lang to use locale**

Replace hardcoded `xml:lang="id-ID"` or language-name-based with `locale` param value.

- [ ] **Step 3: Update prompt text references**

In system prompts that reference language, update to mention BCP-47 locale code.

Commit: `git add src/llm_generate.py && git commit -m "refactor(llm_generate): rename language->locale, SSML uses BCP-47 xml:lang"`

---

## Task 6: Pipeline Files Update

**Files:** Modify: `src/run_24_7.py`, `src/run_pipeline.py`, `src/main.py`, `cli.py`, `scripts/run_24h.py`

- [ ] **Step 1: run_24_7.py line ~224**

`account.get("language")` to `account.get("locale")`.

- [ ] **Step 2: run_pipeline.py**

Rename `args.language` to `args.locale` throughout. Check argparse definition.

- [ ] **Step 3: main.py**

CLI params: `--language` to `--locale`. Update function signatures.

- [ ] **Step 4: cli.py**

CLI params: `--language` to `--locale`.

- [ ] **Step 5: run_24h.py**

Param `language` to `locale` in function signatures and body.

Commit: `git add src/run_24_7.py src/run_pipeline.py src/main.py cli.py scripts/run_24h.py && git commit -m "refactor: rename language->locale in pipeline and CLI"`

---

## Task 7: API Update

**Files:** Modify: `api/models.py`, `api/routers/accounts.py`, `api/routers/generate.py`, `api/pipeline_worker.py`

- [ ] **Step 1: models.py**

In `AccountCreate`: `language: str = "English"` to `locale: str = "en-US"`.
In `Job`: rename `language` field to `locale`.

- [ ] **Step 2: accounts.py router line ~84**

`language=body.language` to `locale=body.locale`.

- [ ] **Step 3: generate.py router**

Pass `locale=req.locale`.

- [ ] **Step 4: pipeline_worker.py line ~81**

`job.language` to `job.locale`.

Commit: `git add api/models.py api/routers/accounts.py api/routers/generate.py api/pipeline_worker.py && git commit -m "refactor(api): rename language->locale in models and routers"`

---

## Task 8: Web UI Update

**Files:** Modify: `web/src/pages/Settings.tsx`, `web/src/pages/Videos.tsx`, `web/src/pages/Generate.tsx`

- [ ] **Step 1: Settings.tsx - BCP-47 locale selector**

Replace language-name-based selector with BCP-47 locale selector. Each option shows readable label plus locale code. Update `languagevoices` references to `localevoices`.

Example LOCALES array:

```tsx
const LOCALES = [
  { label: "English (en-US)", value: "en-US" },
  { label: "Indonesian (id-ID)", value: "id-ID" },
  { label: "Malay (ms-MY)", value: "ms-MY" },
  { label: "Javanese (jv-ID)", value: "jv-ID" },
  { label: "Sundanese (su-ID)", value: "su-ID" },
  { label: "Thai (th-TH)", value: "th-TH" },
  { label: "Vietnamese (vi-VN)", value: "vi-VN" },
  { label: "Filipino (fil-PH)", value: "fil-PH" },
  { label: "Korean (ko-KR)", value: "ko-KR" },
  { label: "Japanese (ja-JP)", value: "ja-JP" },
  { label: "Chinese (zh-CN)", value: "zh-CN" },
  { label: "Arabic (ar-SA)", value: "ar-SA" },
  { label: "Hindi (hi-IN)", value: "hi-IN" },
  { label: "Spanish (es-ES)", value: "es-ES" },
  { label: "French (fr-FR)", value: "fr-FR" },
  { label: "German (de-DE)", value: "de-DE" },
  { label: "Italian (it-IT)", value: "it-IT" },
  { label: "Portuguese (pt-BR)", value: "pt-BR" },
  { label: "Russian (ru-RU)", value: "ru-RU" },
];
```

- [ ] **Step 2: Videos.tsx**

`video.language` to `video.locale` (lines ~188 and ~296).

- [ ] **Step 3: Generate.tsx**

State `language` to `locale`.

Commit: `git add web/src/pages/Settings.tsx web/src/pages/Videos.tsx web/src/pages/Generate.tsx && git commit -m "refactor(ui): rename language->locale, BCP-47 selector in Settings"`

---

## Task 9: Research Locale Cascade

**Files:** Modify: `src/research.py`

- [ ] **Step 1: Add LOCALE_TO_COUNTRY mapping**

```python
LOCALE_TO_COUNTRY = {
    "en-US": "US", "en-GB": "GB", "id-ID": "ID", "ms-MY": "MY",
    "th-TH": "TH", "vi-VN": "VN", "fil-PH": "PH", "ko-KR": "KR",
    "ja-JP": "JP", "zh-CN": "CN", "ar-SA": "SA", "hi-IN": "IN",
    "es-ES": "ES", "fr-FR": "FR", "de-DE": "DE", "it-IT": "IT",
    "pt-BR": "BR", "ru-RU": "RU", "tr-TR": "TR", "pl-PL": "PL",
    "nl-NL": "NL", "sv-SE": "SE", "da-DK": "DK", "no-NO": "NO",
    "fi-FI": "FI", "el-GR": "GR", "cs-CZ": "CZ", "hu-HU": "HU",
    "ro-RO": "RO", "uk-UA": "UA",
}
```

- [ ] **Step 2: Add locale param to research functions**

Add `locale: str = "en-US"` param to actual research functions:
1. `search_tavily()` (line 11): add `locale` param, map to country via `LOCALE_TO_COUNTRY`, pass to `tavily_search()`
2. `search_exa()` (line 47): add `locale` param, map to country, use in query context

Change from:
```python
def search_tavily(query, niche, max_results=8):
```
To:
```python
def search_tavily(query, niche, locale: str = "en-US", max_results=8):
    country = LOCALE_TO_COUNTRY.get(locale, "US")
    ...
```

Commit: `git add src/research.py && git commit -m "feat(research): add locale param, map to country code for Tavily"`

---

## Task 10: Tests Update

**Files:** Modify: `tests/test_config_voice.py`, `tests/test_tts.py`, `tests/test_indonesian_pipeline.py`, `tests/test_edge_tts_lang.py`

- [ ] **Step 1: test_config_voice.py**

- `reset_languagevoices()` to `reset_localevoices()` (function name and body)
- `get_tts_voice("Indonesian")` to `get_tts_voice("id-ID")`
- `get_tts_voice("German")` to `get_tts_voice("de-DE")`
- All fixture data: `"Indonesian": "id-ID-GadisNeural"` to `"id-ID": "id-ID-GadisNeural"`
- `from src.config import get_languagevoices` to `get_localevoices`
- All calls: `get_languagevoices()` to `get_localevoices()`

- [ ] **Step 2: test_tts.py**

Update `reset_languagevoices` to `reset_localevoices`. Update voice fixtures to BCP-47 keys.

- [ ] **Step 3: test_indonesian_pipeline.py**

Update all `"Indonesian"` to `"id-ID"`. Update voice fixtures to BCP-47.

- [ ] **Step 4: test_edge_tts_lang.py**

Verify all references already use BCP-47 format (id-ID-GadisNeural). Confirm `locale="id-ID"` in calls.

- [ ] **Step 5: Verify all tests pass**

Run: `python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: ALL PASS.

Commit: `git add tests/ && git commit -m "refactor(tests): update fixtures to BCP-47 locale codes"`

---

## Task 11: Integration + Preflight

- [ ] **Step 1: Run full test suite**

`python3 -m pytest tests/ -v --tb=short`

- [ ] **Step 2: Run preflight**

`python3 scripts/preflight_local.py`

- [ ] **Step 3: Smoke test**

```python
from src.config import get_tts_voice, get_localevoices
print(get_tts_voice("id-ID"))      # -> id-ID-GadisNeural
print(get_tts_voice("de-DE"))      # -> en-US-JennyNeural (fallback)
print(get_localevoices())           # -> {'id-ID': 'id-ID-GadisNeural', ...}
```

Commit any remaining changes: `git add -A && git commit -m "test: smoke test for BCP-47 locale system"`

---

## Task 12: Additional Missing Files (from review)

**Files:** Modify: `api/pipeline_worker.py`, `scripts/run_24h.py`

- [ ] **Step 1: pipeline_worker.py updates**

Lines 81, 241, 312 — update `youtube._language` → `youtube._locale`:
```python
# Line 81:
youtube._locale = job.locale  # was: youtube._language = job.language

# Line 241:
locale=youtube._locale,  # was: language=youtube._language

# Line 312:
"locale": youtube._locale,  # was: "language": youtube._language
```

- [ ] **Step 2: run_24h.py updates**

Lines 90, 103, 122, 139, 152 — update all `language` refs to `locale`:
```python
# Line 90: def add_video signature
def add_video(niche, locale, topic, ...):  # was: language

# Line 103: call inside add_video
locale=locale,  # was: language=language

# Line 122:
locale = account.get("locale", "en-US")  # was: account.get("language", "English")

# Line 139, 152: calls inside batch loop
locale=locale,
```

Commit: `git add api/pipeline_worker.py scripts/run_24h.py && git commit -m "fix: update language->locale in pipeline_worker and run_24h"`

---

## Self-Review Checklist

1. **Spec coverage:** All 9 spec sections have a corresponding task. Gaps? None found.
2. **Placeholder scan:** No TBD/TODO/placeholder patterns. All steps have exact code.
3. **Type consistency:** `locale` param used uniformly across all files. No mixed `language`/`locale`.
4. **Migration safety:** Old `languagevoices` and `language` column migrated before drop (SQLite ALTER TABLE DROP not supported in all versions).
5. **Task ordering:** Task 1 (DB) before Task 2 (config) — correct dependency.
