# Locale BCP-47 Migration Design

## Goal

Rename `accounts.language` (bare language name, e.g. `"Indonesian"`) → `accounts.locale` (BCP-47 code, e.g. `"id-ID"`). Cascade BCP-47 locale through the entire pipeline: TTS voice lookup, content generation, research filtering, hashtag generation.

---

## 1. BCP-47 Locale Standard

BCP-47 format: `{ISO-639-1}-{ISO-3166-1-alpha-2}`
- Lowercase language code + uppercase region code, hyphen separated
- Examples: `en-US`, `id-ID`, `ms-MY`, `jv-ID`, `su-ID`, `ko-KR`, `ja-JP`, `zh-CN`, `ar-SA`, `hi-IN`, `es-ES`, `fr-FR`, `de-DE`, `it-IT`, `pt-BR`, `vi-VN`, `th-TH`, `fil-PH`, `ru-RU`, `tr-TR`, `pl-PL`, `nl-NL`, `sv-SE`, `da-DK`, `no-NO`, `fi-FI`, `el-GR`, `cs-CZ`, `hu-HU`, `ro-RO`, `uk-UA`

Azure Neural TTS uses BCP-47 locale codes as voice prefixes (e.g. `id-ID-GadisNeural`).

---

## 2. Data Model Changes

### DB Migration: `accounts.language` → `accounts.locale`

SQL (wrapped in `try/except sqlite3.OperationalError`):

```sql
-- Drop old language column if it exists, add new locale column
-- Strategy: add locale column, migrate data, drop language column

ALTER TABLE accounts ADD COLUMN locale TEXT DEFAULT 'en-US';
-- Migrate: "Indonesian" → "id-ID", "English" → "en-US", "Javanese" → "jv-ID", "Sundanese" → "su-ID", etc.

UPDATE accounts SET locale = 'id-ID' WHERE language = 'Indonesian';
UPDATE accounts SET locale = 'en-US' WHERE language = 'English';
UPDATE accounts SET locale = 'jv-ID' WHERE language = 'Javanese';
UPDATE accounts SET locale = 'su-ID' WHERE language = 'Sundanese';

ALTER TABLE accounts DROP COLUMN language;
```

### Config: `languagevoices` → `localevoices`

Rename DB setting key `languagevoices` → `localevoices`. Keys become BCP-47 codes.

Default on fresh seed:

```python
"localevoices": {
    "id-ID": "id-ID-GadisNeural",
    "jv-ID": "jv-ID-SitiNeural",
    "su-ID": "su-ID-TutiNeural"
}
```

Rename functions:
- `get_languagevoices()` → `get_localevoices()`
- `set_languagevoices()` → `set_localevoices()`

### Config API changes

- `get_tts_voice(language=...)` → `get_tts_voice(locale=...)`
- `set_tts_voice(voice, language=...)` → `set_tts_voice(voice, locale=...)`
- `get_tts_voice()` with no arg → still returns default (`en-US-JennyNeural`)

---

## 3. Locale-to-Voice Mapping Table

Default female-voice mapping (pre-populated):

| Locale | Language | Female Voice |
|--------|----------|-------------|
| `en-US` | English (US) | `en-US-JennyNeural` |
| `en-GB` | English (UK) | `en-GB-AbbiNeural` |
| `id-ID` | Indonesian | `id-ID-GadisNeural` |
| `ms-MY` | Malay (MY) | `ms-MY-YasminNeural` |
| `jv-ID` | Javanese | `jv-ID-SitiNeural` |
| `su-ID` | Sundanese | `su-ID-TutiNeural` |
| `th-TH` | Thai | `th-TH-PremwadeeNeural` |
| `vi-VN` | Vietnamese | `vi-VN-HoaiMyNeural` |
| `fil-PH` | Filipino | `fil-PH-BlessicaNeural` |
| `ko-KR` | Korean | `ko-KR-SunHiNeural` |
| `ja-JP` | Japanese | `ja-JP-NanamiNeural` |
| `zh-CN` | Chinese (Simplified) | `zh-CN-XiaoxiaoNeural` |
| `ar-SA` | Arabic (SA) | `ar-SA-ZariyahNeural` |
| `hi-IN` | Hindi | `hi-IN-SwaraNeural` |
| `es-ES` | Spanish (ES) | `es-ES-ElviraNeural` |
| `fr-FR` | French (FR) | `fr-FR-BrigitteNeural` |
| `de-DE` | German (DE) | `de-DE-AmalaNeural` |
| `it-IT` | Italian | `it-IT-ElsaNeural` |
| `pt-BR` | Portuguese (BR) | `pt-BR-FranciscaNeural` |
| `ru-RU` | Russian | `ru-RU-SvetlanaNeural` |
| `tr-TR` | Turkish | `tr-TR-EmelNeural` |
| `pl-PL` | Polish | `pl-PL-AgnieszkaNeural` |
| `nl-NL` | Dutch | `nl-NL-FennaNeural` |
| `sv-SE` | Swedish | `sv-SE-SofieNeural` |
| `da-DK` | Danish | `da-DK-ChristelNeural` |
| `no-NO` | Norwegian | `nb-NO-PernilleNeural` |
| `fi-FI` | Finnish | `fi-FI-SelmaNeural` |
| `el-GR` | Greek | `el-GR-AthinaNeural` |
| `cs-CZ` | Czech | `cs-CZ-VlastaNeural` |
| `hu-HU` | Hungarian | `hu-HU-NoemiNeural` |
| `ro-RO` | Romanian | `ro-RO-AlinaNeural` |
| `uk-UA` | Ukrainian | `uk-UA-PolinaNeural` |

---

## 4. File Changes

| File | Change |
|------|--------|
| `src/db.py` | Rename `languagevoices` → `localevoices`; rename `language` → `locale` in accounts table; add migration; update `add_account()`, `update_account()`, seed defaults with BCP-47 |
| `src/config.py` | Rename `get_languagevoices()` → `get_localevoices()`, `set_languagevoices()` → `set_localevoices()`; rename param `language` → `locale` in `get_tts_voice()`/`set_tts_voice()`; update docstrings |
| `src/classes/Tts.py` | Update `get_tts_voice(language=...)` → `get_tts_voice(locale=...)` |
| `src/run_24_7.py` | `account.get("language")` → `account.get("locale")` |
| `src/run_pipeline.py` | `args.language` → `args.locale` |
| `src/classes/YouTube.py` | `self.language` → `self.locale`; update SSML `xml:lang` injection; update prompt references |
| `src/llm_generate.py` | Param `language` → `locale` in function signatures; update SSML `xml:lang` to use locale; update prompt text references |
| `api/models.py` | `language` field → `locale` field |
| `api/routers/accounts.py` | `language=body.language` → `locale=body.locale` |
| `api/routers/generate.py` | Pass `locale` |
| `api/pipeline_worker.py` | `job.language` → `job.locale` |
| `src/main.py` | CLI params `language` → `locale` |
| `cli.py` | CLI params `language` → `locale` |
| `scripts/run_24h.py` | `language` → `locale` |
| `web/src/pages/Settings.tsx` | Language selector → locale selector with BCP-47 labels; `languagevoices` → `localevoices` |
| `web/src/pages/Videos.tsx` | `video.language` → `video.locale` |
| `web/src/pages/Generate.tsx` | State `language` → `locale` |
| `tests/*.py` | All test files: rename fixtures, function calls, expected values from language names to BCP-47 codes |

---

## 5. SSML Changes

`xml:lang` attribute uses BCP-47 locale directly:

```xml
<speak version="1.0" xml:lang="id-ID">
    <prosody rate="90%" pitch="-1st" volume="medium">
        [INDONESIAN TEXT]
    </prosody>
</speak>
```

---

## 6. Research / Hashtag Cascade

Locale cascades to:
1. **TTS voice**: `get_tts_voice(locale)` → BCP-47 voice shortname
2. **Content generation**: LLM prompt receives `locale` (e.g. `"id-ID"`) for language-appropriate output
3. **Hashtags**: `generate_tags_response()` already uses LLM — inject locale context so LLM generates region-appropriate hashtags
4. **Research filtering**: `research.py` functions accept `locale` → map to country code for Tavily `country=` param

### Research Country Code Mapping

| Locale | Country Code |
|--------|-------------|
| `en-US` | `US` |
| `en-GB` | `GB` |
| `id-ID` | `ID` |
| `ms-MY` | `MY` |
| `th-TH` | `TH` |
| `vi-VN` | `VN` |
| `fil-PH` | `PH` |
| `ko-KR` | `KR` |
| `ja-JP` | `JP` |
| `zh-CN` | `CN` |
| `ar-SA` | `SA` |
| `hi-IN` | `IN` |
| `es-ES` | `ES` |
| `fr-FR` | `FR` |
| `de-DE` | `DE` |
| `it-IT` | `IT` |
| `pt-BR` | `BR` |
| `ru-RU` | `RU` |
| Others | `US` (default fallback) |

---

## 7. Backward Compatibility

- Old accounts with `language="Indonesian"` etc. get migrated to `locale="id-ID"` etc. on first DB init
- `get_tts_voice("Indonesian")` (old bare name) should still work by treating it as a locale lookup — if not found in `localevoices`, check if it's a valid BCP-47 code, otherwise try to map bare names to locales
- Migration in `db.py init_db()`: for each existing account row with bare language name, map to BCP-47 and update

### Language Name → Locale Mapping

```python
LANGUAGE_TO_LOCALE = {
    "Indonesian": "id-ID",
    "Javanese": "jv-ID",
    "Sundanese": "su-ID",
    "Malay": "ms-MY",
    "Thai": "th-TH",
    "Vietnamese": "vi-VN",
    "Filipino": "fil-PH",
    "Korean": "ko-KR",
    "Japanese": "ja-JP",
    "Chinese": "zh-CN",
    "Arabic": "ar-SA",
    "Hindi": "hi-IN",
    "Spanish": "es-ES",
    "French": "fr-FR",
    "German": "de-DE",
    "Italian": "it-IT",
    "Portuguese": "pt-BR",
    "Russian": "ru-RU",
    "Turkish": "tr-TR",
    "English": "en-US",  # default
}
```

---

## 8. Scope Boundaries

**In scope:** BCP-47 rename, cascade through TTS/content/hashtags/research, DB migration, UI/API updates.

**Out of scope:**
- Adding new TTS providers (Edge TTS only for now)
- Changing video resolution, format, or metadata schema
- Multi-lingual video output (single locale per video)
- Currency conversion or locale-specific formatting

---

## 9. Risks

| Risk | Mitigation |
|------|-----------|
| Old bare language names in DB not migrated | Migration script in `init_db()` with explicit mapping |
| UI displays raw BCP-47 codes (e.g. "id-ID") instead of readable labels | UI shows `{Language} ({Locale})` e.g. "Indonesian (id-ID)" |
| SSML `xml:lang` not supported by voice | EdgeTTS guard: fallback to bare `<speak>` if synthesis fails |
| Tests use old language names and break | Update all test fixtures and assertions |
