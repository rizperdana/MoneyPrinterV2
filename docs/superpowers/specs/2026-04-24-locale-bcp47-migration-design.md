# Locale BCP-47 Migration — Precision Specification

## Overview

Two distinct data concepts, kept separate:

| Concept | Stored In | Type | Purpose |
|---------|-----------|------|---------|
| `locale` | `accounts.locale` | `TEXT` scalar per account | Identifies the language+region for an account |
| `localevoices` | `settings` table, key=`localevoices` | `TEXT` (JSON dict) | Maps locale → TTS voice shortname globally |

---

## 1. Data Models

### 1a. `accounts` Table — `locale` Column

**SQL schema after migration:**

```sql
CREATE TABLE accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    platform         TEXT NOT NULL,
    username         TEXT NOT NULL,
    nickname         TEXT,
    profile_path     TEXT,
    oauth_token      TEXT,
    topics           TEXT DEFAULT '[]',   -- JSON array
    topic            TEXT DEFAULT '',
    locale           TEXT DEFAULT 'en-US', -- BCP-47 locale code
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**`locale` column values — BCP-47 format:**

| Value | Meaning |
|-------|---------|
| `en-US` | English (United States) — default |
| `en-GB` | English (United Kingdom) |
| `id-ID` | Indonesian (Indonesia) |
| `ms-MY` | Malay (Malaysia) |
| `jv-ID` | Javanese (Indonesia) |
| `su-ID` | Sundanese (Indonesia) |
| `th-TH` | Thai (Thailand) |
| `vi-VN` | Vietnamese (Vietnam) |
| `fil-PH` | Filipino (Philippines) |
| `ko-KR` | Korean (South Korea) |
| `ja-JP` | Japanese (Japan) |
| `zh-CN` | Chinese Simplified (China) |
| `ar-SA` | Arabic (Saudi Arabia) |
| `hi-IN` | Hindi (India) |
| `es-ES` | Spanish (Spain) |
| `fr-FR` | French (France) |
| `de-DE` | German (Germany) |
| `it-IT` | Italian (Italy) |
| `pt-BR` | Portuguese (Brazil) |
| `ru-RU` | Russian (Russia) |
| `tr-TR` | Turkish (Turkey) |
| `pl-PL` | Polish (Poland) |
| `nl-NL` | Dutch (Netherlands) |
| `sv-SE` | Swedish (Sweden) |
| `da-DK` | Danish (Denmark) |
| `no-NO` | Norwegian Bokmal (Norway) |
| `fi-FI` | Finnish (Finland) |
| `el-GR` | Greek (Greece) |
| `cs-CZ` | Czech (Czech Republic) |
| `hu-HU` | Hungarian (Hungary) |
| `ro-RO` | Romanian (Romania) |
| `uk-UA` | Ukrainian (Ukraine) |

**Migration from bare language names:**

```python
LANGUAGE_TO_LOCALE = {
    "Indonesian":  "id-ID",
    "Javanese":   "jv-ID",
    "Sundanese":   "su-ID",
    "Malay":      "ms-MY",
    "Thai":       "th-TH",
    "Vietnamese":  "vi-VN",
    "Filipino":   "fil-PH",
    "Korean":     "ko-KR",
    "Japanese":   "ja-JP",
    "Chinese":    "zh-CN",
    "Arabic":     "ar-SA",
    "Hindi":      "hi-IN",
    "Spanish":    "es-ES",
    "French":     "fr-FR",
    "German":     "de-DE",
    "Italian":    "it-IT",
    "Portuguese": "pt-BR",
    "Russian":    "ru-RU",
    "Turkish":    "tr-TR",
    "Polish":     "pl-PL",
    "Dutch":      "nl-NL",
    "Swedish":    "sv-SE",
    "Danish":     "da-DK",
    "Norwegian":  "no-NO",
    "Finnish":    "fi-FI",
    "Greek":      "el-GR",
    "Czech":      "cs-CZ",
    "Hungarian":  "hu-HU",
    "Romanian":   "ro-RO",
    "Ukrainian":  "uk-UA",
    "English":    "en-US",   # default fallback
}
```

---

### 1b. `settings` Table — `localevoices` Key

**SQL schema:**

```sql
CREATE TABLE settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
```

**`localevoices` entry:**

| key | value (TEXT, JSON) |
|-----|-------------------|
| `localevoices` | `{"id-ID": "id-ID-GadisNeural", "jv-ID": "jv-ID-SitiNeural", "su-ID": "su-ID-TutiNeural", ...}` |

**Default value on fresh seed:**

```json
{
  "id-ID": "id-ID-GadisNeural",
  "jv-ID": "jv-ID-SitiNeural",
  "su-ID": "su-ID-TutiNeural"
}
```

**`localevoices` — Full default voice map (female neural, BCP-47 keys):**

```json
{
  "en-US": "en-US-JennyNeural",
  "en-GB": "en-GB-AbbiNeural",
  "id-ID": "id-ID-GadisNeural",
  "ms-MY": "ms-MY-YasminNeural",
  "jv-ID": "jv-ID-SitiNeural",
  "su-ID": "su-ID-TutiNeural",
  "th-TH": "th-TH-PremwadeeNeural",
  "vi-VN": "vi-VN-HoaiMyNeural",
  "fil-PH": "fil-PH-BlessicaNeural",
  "ko-KR": "ko-KR-SunHiNeural",
  "ja-JP": "ja-JP-NanamiNeural",
  "zh-CN": "zh-CN-XiaoxiaoNeural",
  "ar-SA": "ar-SA-ZariyahNeural",
  "hi-IN": "hi-IN-SwaraNeural",
  "es-ES": "es-ES-ElviraNeural",
  "fr-FR": "fr-FR-BrigitteNeural",
  "de-DE": "de-DE-AmalaNeural",
  "it-IT": "it-IT-ElsaNeural",
  "pt-BR": "pt-BR-FranciscaNeural",
  "ru-RU": "ru-RU-SvetlanaNeural",
  "tr-TR": "tr-TR-EmelNeural",
  "pl-PL": "pl-PL-AgnieszkaNeural",
  "nl-NL": "nl-NL-FennaNeural",
  "sv-SE": "sv-SE-SofieNeural",
  "da-DK": "da-DK-ChristelNeural",
  "no-NO": "nb-NO-PernilleNeural",
  "fi-FI": "fi-FI-SelmaNeural",
  "el-GR": "el-GR-AthinaNeural",
  "cs-CZ": "cs-CZ-VlastaNeural",
  "hu-HU": "hu-HU-NoemiNeural",
  "ro-RO": "ro-RO-AlinaNeural",
  "uk-UA": "uk-UA-PolinaNeural"
}
```

---

## 2. Function Signatures

### 2a. Config Functions (`src/config.py`)

```python
def get_default_tts_voice() -> str:
    """Returns the default TTS voice (en-US-JennyNeural)."""
    return _get_config("tts_voice", "en-US-JennyNeural")


def get_localevoices() -> dict:
    """
    Gets the per-locale TTS voice mapping.

    Returns:
        dict: {locale: voice_shortname, ...}
          e.g. {"id-ID": "id-ID-GadisNeural", "de-DE": "de-DE-KlarissaNeural"}
    """
    raw = _get_config("localevoices", "{}")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def set_localevoices(mapping: dict) -> None:
    """
    Sets the per-locale TTS voice mapping.

    Args:
        mapping: {locale: voice_shortname, ...}
    """
    from src.db import set_setting, reload_settings
    try:
        set_setting("localevoices", json.dumps(mapping))
        global _settings_cache
        _settings_cache = None
        reload_settings()
    except Exception as e:
        from status import error
        error(f"Failed to save localevoices: {e}")


def get_tts_voice(locale: Optional[str] = None) -> str:
    """
    Gets the TTS voice for a given locale.

    Args:
        locale: BCP-47 locale code (e.g. "id-ID", "de-DE"). None returns default.

    Returns:
        str: TTS voice shortname for the locale, or default if not found.
             e.g. "id-ID-GadisNeural" for locale="id-ID"
                  "en-US-JennyNeural" for locale=None (default fallback)
    """
    if locale:
        localevoices = get_localevoices()
        voice = localevoices.get(locale)
        if voice:
            return voice
    return get_default_tts_voice()


def set_tts_voice(voice: str, locale: Optional[str] = None) -> None:
    """
    Sets the TTS voice. If locale is None, sets the default voice.
    If locale is provided, sets the voice for that locale.

    Args:
        voice: TTS voice shortname (e.g. "id-ID-GadisNeural")
        locale: BCP-47 locale code (e.g. "id-ID"). None = default.
    """
    if locale:
        localevoices = get_localevoices()
        localevoices[locale] = voice
        set_localevoices(localevoices)
    else:
        from src.db import set_setting
        try:
            set_setting("tts_voice", voice)
        except Exception as e:
            from status import error
            error(f"Failed to save default TTS voice: {e}")
        global _settings_cache
        _settings_cache = None
```

---

### 2b. DB Functions (`src/db.py`)

```python
def add_account(
    platform: str,
    username: str,
    topic: str = "",
    oauth_token: str = None,
    profile_path: str = None,
    locale: str = "en-US"
) -> int:
    """Insert account, return id."""
    # INSERT INTO accounts (platform, username, nickname, topic, locale)
    # VALUES (?, ?, ?, ?, ?)


def update_account(account_id: int, **fields) -> bool:
    """valid_fields includes 'locale'."""


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
    """Insert video record."""
```

---

### 2c. TTS Class (`src/classes/Tts.py`)

```python
class Tts:
    def __init__(self, locale: Optional[str] = None) -> None:
        self._voice = get_tts_voice(locale=locale)  # was: get_tts_voice(language=...)
```

---

### 2d. YouTube Class (`src/classes/YouTube.py`)

```python
class YouTube:
    def __init__(self, ..., locale: str = "en-US") -> None:
        self.locale = locale          # was: self.language
        self._voice = get_tts_voice(locale=locale)  # locale cascades here
        # ...
```

**SSML xml:lang uses `self.locale` directly:**

```python
# When generating SSML-wrapped script:
if not self.script.strip().startswith("<speak>"):
    self.script = f'<speak version="1.0" xml:lang="{self.locale}">...' + self.script + '</speak>'
```

---

### 2e. LLM Generate (`src/llm_generate.py`)

Functions that take `language` param → rename to `locale: str = "en-US"`.

Expected function signatures:

```python
def generate_script_response(topic: str, niche: str, locale: str = "en-US",
                            for_kids: bool = False, extra: str = "") -> str:
    # Prompt includes: Write the script in {locale} (BCP-47).
    # SSML wrapper uses xml:lang="{locale}" directly.


def generate_tags_response(topic: str, niche: str, locale: str = "en-US",
                          num_tags: int = 10) -> list[str]:
    # Prompt includes: Generate hashtags appropriate for locale={locale}.
    # LLM researches/adjusts based on locale context (no hardcoded hashtags).
```

---

### 2f. Pipeline (`src/run_pipeline.py`)

```python
def run_pipeline(
    niche: str,
    output_dir: str,
    logger,
    upload: bool = False,
    locale: str = "en-US",   # was: language="English"
) -> dict:
    youtube = YouTube(..., locale=locale)
    tts = Tts(locale=locale)
    # ...
```

---

### 2g. 24/7 Runner (`src/run_24_7.py`)

```python
# Around line 224
locale = account.get("locale") or default_locale  # was: account.get("language")
run_pipeline(..., locale=locale)
```

---

### 2h. Research (`src/research.py`)

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

# Add locale param to search_tavily (line 11)
def search_tavily(
    query: str,
    niche: str,
    locale: str = "en-US",
    max_results: int = 8,
) -> str:
    # Map locale -> country code for Tavily
    country = LOCALE_TO_COUNTRY.get(locale, "US")
    # tavily_search(query=query, niche=niche, country=country, max_results=max_results)

    ...

# Add locale param to search_exa (line 47)
def search_exa(
    query: str,
    niche: str,
    locale: str = "en-US",
    num_results: int = 8,
) -> str:
    country = LOCALE_TO_COUNTRY.get(locale, "US")
    # exa_search_exa(query=query, includeDomains=...)
    ...
```

---

### 2i. API Models (`api/models.py`)

```python
class AccountCreate(BaseModel):
    platform: str
    username: str
    nickname: Optional[str] = None
    topic: str = ""
    locale: str = "en-US"   # was: language="English"


class Job(BaseModel):
    account: str
    niche: str
    locale: str = "en-US"   # was: language
    for_kids: bool = False
    auto_upload: bool = False
```

---

## 3. DB Migrations

### 3a. Migration: `localevoices` (settings table)

```python
# Migration: add localevoices column (JSON dict of locale->voice)
# Check if new column exists first (covers fresh installs)
try:
    cursor.execute("SELECT localevoices FROM settings LIMIT 1")
except sqlite3.OperationalError:
    # New column doesn't exist — create it
    try:
        # Check if old languagevoices column exists and migrate it
        cursor.execute("SELECT languagevoices FROM settings LIMIT 1")
        old_row = cursor.fetchone()
        if old_row and old_row[0]:
            cursor.execute(
                "ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT ?",
                (old_row[0],)
            )
        else:
            cursor.execute(
                "ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'"
            )
    except sqlite3.OperationalError:
        cursor.execute(
            "ALTER TABLE settings ADD COLUMN localevoices TEXT DEFAULT '{}'"
        )
```

### 3b. Migration: `locale` (accounts table)

```python
# Migration: rename language column to locale (BCP-47)
# SQLite does not support ALTER TABLE RENAME COLUMN directly,
# so we use add -> migrate data -> drop old column pattern.
try:
    # Check if new locale column exists
    cursor.execute("SELECT locale FROM accounts LIMIT 1")
    # locale column exists — check if we need to migrate from old language column
    try:
        cursor.execute("SELECT language FROM accounts LIMIT 1")
        # Both exist — migrate old language values to new locale
        cursor.execute(
            "SELECT id, language FROM accounts "
            "WHERE language IS NOT NULL AND language != ''"
        )
        for account_id, lang in cursor.fetchall():
            locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)  # map or keep original
            cursor.execute(
                "UPDATE accounts SET locale = ? WHERE id = ?",
                (locale_val, account_id)
            )
        cursor.execute("ALTER TABLE accounts DROP COLUMN language")
    except sqlite3.OperationalError:
        pass  # No old language column, locale column is clean
except sqlite3.OperationalError:
    # locale column doesn't exist
    try:
        cursor.execute("SELECT language FROM accounts LIMIT 1")
        # Old language column exists — add locale, migrate, drop
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'"
        )
        cursor.execute(
            "SELECT id, language FROM accounts "
            "WHERE language IS NOT NULL AND language != ''"
        )
        for account_id, lang in cursor.fetchall():
            locale_val = LANGUAGE_TO_LOCALE.get(lang, lang)
            cursor.execute(
                "UPDATE accounts SET locale = ? WHERE id = ?",
                (locale_val, account_id)
            )
        cursor.execute("ALTER TABLE accounts DROP COLUMN language")
    except sqlite3.OperationalError:
        # Neither exists — add new locale column (fresh install)
        cursor.execute(
            "ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US'"
        )
```

---

## 4. Data Flow

```
Account created
    locale="id-ID" stored in accounts table

Pipeline starts (run_pipeline with locale="id-ID")
    │
    ├─► research_topic(..., locale="id-ID")
    │       └─► LOCALE_TO_COUNTRY["id-ID"] = "ID"
    │           └─► tavily_search(..., country="ID")
    │
    ├─► generate_script_response(..., locale="id-ID")
    │       └─► Prompt: "Write in id-ID locale"
    │       └─► SSML: xml:lang="id-ID"
    │
    ├─► generate_tags_response(..., locale="id-ID")
    │       └─► Prompt: "Generate id-ID-appropriate hashtags"
    │
    ├─► YouTube(..., locale="id-ID")
    │       └─► self.locale = "id-ID"
    │       └─► self._voice = get_tts_voice(locale="id-ID")
    │       └─► SSML xml:lang="{self.locale}"
    │
    └─► Tts(locale="id-ID")
            └─► get_tts_voice("id-ID")
                    └─► get_localevoices()["id-ID"]
                            └─► "id-ID-GadisNeural"
```

---

## 5. UI Labels

The UI displays `{Language Name} ({BCP-47 Code})` for readability:

| Display Label | Value (BCP-47) |
|--------------|----------------|
| English (en-US) | `en-US` |
| Indonesian (id-ID) | `id-ID` |
| Malay (ms-MY) | `ms-MY` |
| Javanese (jv-ID) | `jv-ID` |
| Sundanese (su-ID) | `su-ID` |
| Thai (th-TH) | `th-TH` |
| Vietnamese (vi-VN) | `vi-VN` |
| Filipino (fil-PH) | `fil-PH` |
| Korean (ko-KR) | `ko-KR` |
| Japanese (ja-JP) | `ja-JP` |
| Chinese (zh-CN) | `zh-CN` |
| Arabic (ar-SA) | `ar-SA` |
| Hindi (hi-IN) | `hi-IN` |
| Spanish (es-ES) | `es-ES` |
| French (fr-FR) | `fr-FR` |
| German (de-DE) | `de-DE` |
| Italian (it-IT) | `it-IT` |
| Portuguese (pt-BR) | `pt-BR` |
| Russian (ru-RU) | `ru-RU` |

---

## 6. What Gets Deleted

After migration is complete:

| Old | Removed |
|-----|---------|
| `accounts.language` column | Dropped after data migrated |
| `settings.languagevoices` key | Superseded by `settings.localevoices` |
| `get_languagevoices()` function | Renamed to `get_localevoices()` |
| `set_languagevoices()` function | Renamed to `set_localevoices()` |
| `get_tts_voice(language=...)` param | Renamed to `locale=...` |
| `set_tts_voice(voice, language=...)` param | Renamed to `locale=...` |
| Bare language name strings in code | All replaced with BCP-47 codes |

---

## 7. Test Fixtures (expected values)

All tests use BCP-47 locale codes as keys and arguments:

```python
# config test
get_tts_voice("id-ID")        # → "id-ID-GadisNeural"
get_tts_voice("de-DE")        # → "en-US-JennyNeural" (fallback)
get_tts_voice("jv-ID")        # → "jv-ID-SitiNeural"
get_tts_voice()               # → "en-US-JennyNeural" (default)

# localevoices dict
{"id-ID": "id-ID-GadisNeural", "jv-ID": "jv-ID-SitiNeural"}

# add_account
add_account(platform="youtube", username="test", locale="id-ID")

# SSML
'<speak version="1.0" xml:lang="id-ID">' in ssml_output
```
