# Audience-Aware Pipeline + Prosody Implementation Plan

## 1. SUMMARY

This plan implements an audience-aware content generation system that tailors script complexity and language based on target audience level. The system adds a new `audience` parameter with four levels: `beginner`, `general`, `intermediate`, and `expert`, each with distinct language complexity guidelines.

### Key Changes:
- Adds `audience` field to accounts, videos, and all generation functions
- Updates YouTube.py to bypass `__new__` with audience assignment
- Rewrites script complexity instructions from "5 YEARS OLD" to audience-specific guidance
- Enhances EdgeTts.py to preserve prosody on valid SSML while maintaining fallback for malformed

### Files Modified:
- `src/db.py` - accounts table migration, add_account(), update_account()
- `src/classes/YouTube.py` - __init__, __new__ bypass, generate_script()
- `src/llm_generate.py` - 7 generation functions
- `src/classes/EdgeTts.py` - SSML fallback behavior
- `src/run_24_7.py` - run_single_video()
- `src/main.py` - CLI flag
- `api/models.py` - AccountCreate, AccountUpdate

---

## 2. AUDIENCE LEVELS

| Level | Description | Language Complexity | Analogy Usage |
|-------|------------|------------------|-------------|
| `beginner` | Children 5-10 years | Basic words only, short sentences | Everyday objects, toys, games |
| `general` | General adult audience | Accessible language, no jargon without explanation | Cross-domain analogies |
| `intermediate` | Some technical background | Moderate technical terms with explanations | Domain-specific comparisons |
| `expert` | Technical/specialist viewers | Full technical terminology | Mathematical, scientific precision |

### AUDIENCE_GUIDANCE Dictionary (YouTube.py lines ~815)

```python
AUDIEN_ GUIDANCE = {
    "beginner": """
CRITICAL RULE — EXPLAIN LIKE THE VIEWER IS 5 YEARS OLD:
- Use ONLY words a 5-year-old knows. No jargon. No technical terms unless you immediately explain them with a simple analogy.
- Every concept must be compared to something from daily life: "It's like when you blow up a balloon and it pops" or "Imagine stacking LEGO blocks really fast"
- Each sentence must paint a CLEAR picture. If a kid can't visualize it, rewrite it.
- BAD: "The load balancer distributes traffic" → GOOD: "Imagine a pizza shop with one door. A thousand people try to enter at once. So they open ten doors and split the crowd evenly"
- BAD: "Infrastructure handles millions of connections" → GOOD: "Picture a million people all talking on the phone at the same time — somehow nobody gets disconnected"
- Maximum 8 words per sentence. Maximum 50 words total.
""",
    "general": """
CRITICAL RULE — EXPLAIN FOR A GENERAL AUDIENCE:
- Use accessible language that any adult can understand
- Avoid jargon without explanation
- Use analogies for complex technical topics only when helpful
- If using a technical term, explain it briefly in the same sentence
- BAD: "The load balancer distributes traffic across servers" → GOOD: "Think of a traffic cop directing cars. When one road gets too busy, they redirect some cars to another road"
- BAD: "Infrastructure handles millions of concurrent connections" → GOOD: "Imagine a phone switchboard operator from the old movies, but handling a million calls at once"
- Keep sentences short and punchy, 12-15 words maximum
""",
    "intermediate": """
CRITICAL RULE — EXPLAIN FOR AN INTERMEDIATE AUDIENCE:
- Technical terms are OK if briefly explained in context
- Use domain-specific comparisons when helpful
- Assume viewer has basic technical literacy but may not know your specific field
- Can use jargon with brief parenthetical explanation
- Example: "The load balancer (which distributes incoming traffic across multiple servers) routes requests based on current server load"
- Maintain clarity, don't dumb down, but don't overcomplicate
""",
    "expert": """
CRITICAL RULE — EXPLAIN FOR AN EXPERT AUDIENCE:
- Use full technical terminology appropriate to the subject
- No need for basic explanations of common concepts
- Focus on nuanced, precise explanations
- Can use mathematical or scientific notation if appropriate
- Assume deep domain knowledge
- Crisp, precise language over verbose analogies
"""
}
```

---

## 3. BACKWARD COMPATIBILITY

### Default Behavior
- **ALL defaults are `audience: str = "general"`** - ensures existing code works without modification
- New CLI/API fields are optional - if not provided, defaults to "general"
- Database migration adds column with DEFAULT 'general' - no data loss

### Migration Strategy
- SQLite ALTER TABLE ADD COLUMN with DEFAULT handles existing rows
- All functions accept optional audience param with "general" default
- API accepts optional audience field - if missing, defaults to "general"

---

## 4. CODE CHANGES (by file)

### 4.1 db.py

#### Line 82: accounts table
**Current:**
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        username TEXT NOT NULL,
        nickname TEXT,
        profile_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

**Change:** Add AFTER the CREATE (around line 90), add migration:

```python
# Migration: add audience column to accounts
try:
    cursor.execute("SELECT audience FROM accounts LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE accounts ADD COLUMN audience TEXT DEFAULT 'general'")
```

---

#### Line 666: add_account()
**Current:**
```python
def add_account(
    platform: str,
    username: str,
    nickname: Optional[str] = None,
    topic: Optional[str] = None,
    topics: Optional[str] = None,
    locale: str = "en-US",
) -> int:
```

**Change:**
```python
def add_account(
    platform: str,
    username: str,
    nickname: Optional[str] = None,
    topic: Optional[str] = None,
    topics: Optional[str] = None,
    locale: str = "en-US",
    audience: str = "general",
) -> int:
```

**Also update INSERT (line ~694):**
```python
cursor.execute(
    "INSERT INTO accounts (platform, username, nickname, topic, locale, audience) VALUES (?, ?, ?, ?, ?, ?)",
    (platform, username, nickname or "", topic or "", locale, audience),
)
```

---

#### Line 759: valid_fields
**Current:**
```python
valid_fields = {"platform", "username", "nickname", "topic", "locale"}
```

**Change:**
```python
valid_fields = {"platform", "username", "nickname", "topic", "locale", "audience"}
```

---

### 4.2 src/classes/YouTube.py

#### Line 93: __init__ - ADD audience: str = "general"
**Current:**
```python
def __init__(
    self,
    account_uuid: str,
    account_nickname: str,
    fp_profile_path: str,
    niche: str,
    locale: str = "en-US",
) -> None:
```

**Change:**
```python
def __init__(
    self,
    account_uuid: str,
    account_nickname: str,
    fp_profile_path: str,
    niche: str,
    locale: str = "en-US",
    audience: str = "general",
) -> None:
```

---

#### Line 114-118: instance var - ADD self._audience

**After line 118 (self._locale = locale), ADD:**
```python
self._audience: str = audience
```

**Also need property getter after line ~237 (after locale property):**

```python
@property
def audience(self) -> str:
    """
    Getter Method for the audience level.

    Returns:
        audience (str): The audience level (beginner, general, intermediate, expert)
    """
    return self._audience
```

---

#### Line 79-91: run_pipeline BYPASS - ADD youtube._audience

**Current (lines 79-91 in run_pipeline.py):**
```python
# Initialize YouTube
youtube = YouTube.__new__(YouTube)
youtube._account_uuid = "auto-pipeline"
youtube._account_nickname = "Auto Pipeline"
youtube._niche = niche
youtube._locale = locale
youtube.images = []
# ... other assignments
```

**Change:** ADD after youtube._locale assignment:

```python
youtube._audience = "general"  # Default for non-interactive pipeline
```

---

#### Line 815: Replace with AUDIENCE_GUIDANCE dict

**Current (lines 815-821):**
```python
CRITICAL RULE — EXPLAIN LIKE THE VIEWER IS 5 YEARS OLD:
- Use ONLY words a 5-year-old knows. No jargon. No technical terms unless you immediately explain them with a simple analogy.
- Every concept must be compared to something from daily life: "It's like when you blow up a balloon and it pops" or "Imagine stacking LEGO blocks really fast"
- If the topic is technical (software, engineering, science), translate EVERY concept into a physical, visual, everyday comparison.
- BAD: "The load balancer distributes traffic across servers" → GOOD: "Imagine a pizza shop with one door. A thousand people try to enter at once. So they open ten doors and split the crowd evenly"
- BAD: "The infrastructure handles millions of concurrent connections" → GOOD: "Picture a million people all talking on the phone at the same time — somehow nobody gets disconnected"
- Each sentence must paint a CLEAR picture in the viewer's mind. If a kid can't visualize it, rewrite it.
```

**Change:** Replace with DYNAMIC audience instruction:

```python
# Get audience-specific guidance
audience_guidance = AUDIENCE_GUIDANCE.get(self._audience, AUDIENCE_GUIDANCE["general"])

CRITICAL RULE — {audience_guidance}
```

**Add AUDIENCE_GUIDANCE dict at top of YouTube class (around line 78, before class definition):**

```python
AUDIEN_ GUIDANCE = {
    "beginner": """
EXPLAIN LIKE THE VIEWER IS 5 YEARS OLD:
- Use ONLY words a 5-year-old knows. No jargon. No technical terms unless you immediately explain them with a simple analogy.
- Every concept must be compared to something from daily life: "It's like when you blow up a balloon and it pops" or "Imagine stacking LEGO blocks really fast"
- Each sentence must paint a CLEAR picture. If a kid can't visualize it, rewrite it.
- BAD: "The load balancer distributes traffic" → GOOD: "Imagine a pizza shop with one door. A thousand people try to enter at once. So they open ten doors and split the crowd evenly"
- BAD: "Infrastructure handles millions of connections" → GOOD: "Picture a million people all talking on the phone at the same time — somehow nobody gets disconnected"
- Maximum 8 words per sentence. Maximum 50 words total.
""",
    "general": """
EXPLAIN FOR A GENERAL AUDIENCE:
- Use accessible language that any adult can understand
- Avoid jargon without explanation
- Use analogies for complex technical topics only when helpful
- If using a technical term, explain it briefly in the same sentence
- BAD: "The load balancer distributes traffic across servers" → GOOD: "Think of a traffic cop directing cars. When one road gets too busy, they redirect some cars to another road"
- BAD: "Infrastructure handles millions of concurrent connections" → GOOD: "Imagine a phone switchboard operator from the old movies, but handling a million calls at once"
- Keep sentences short and punchy, 12-15 words maximum
""",
    "intermediate": """
EXPLAIN FOR AN INTERMEDIATE AUDIENCE:
- Technical terms are OK if briefly explained in context
- Use domain-specific comparisons when helpful
- Assume viewer has basic technical literacy but may not know your specific field
- Can use jargon with brief parenthetical explanation
- Example: "The load balancer (which distributes incoming traffic across multiple servers) routes requests based on current server load"
- Maintain clarity, don't dumb down, but don't overcomplicate
""",
    "expert": """
EXPLAIN FOR AN EXPERT AUDIENCE:
- Use full technical terminology appropriate to the subject
- No need for basic explanations of common concepts
- Focus on nuanced, precise explanations
- Can use mathematical or scientific notation if appropriate
- Assume deep domain knowledge
- Crisp, precise language over verbose analogies
"""
}
```

---

### 4.3 src/llm_generate.py

For EACH of 7 functions, add `audience: str = "general"` parameter:

#### Line 28: analyze_complexity
**Current:**
```python
def analyze_complexity(subject: str) -> str:
```

**Change:**
```python
def analyze_complexity(subject: str, audience: str = "general") -> str:
```

---

#### Line ~60: generate_response
**Current:**
```python
def generate_response(prompt: str, job: str = None) -> str:
```

**Change:**
```python
def generate_response(prompt: str, job: str = None, audience: str = "general") -> str:
```

---

#### ~generate_topic_response
**Current:**
```python
def generate_topic_response(niche: str, research_context: str = None) -> str:
```

**Change:**
```python
def generate_topic_response(niche: str, research_context: str = None, audience: str = "general") -> str:
```

---

#### ~generate_script_response
**Current:**
```python
def generate_script_response(subject: str, locale: str, sentence_length: int) -> str:
```

**Change:**
```python
def generate_script_response(subject: str, locale: str, sentence_length: int, audience: str = "general") -> str:
```

---

#### ~generate_title_response
**Current:**
```python
def generate_title_response(subject: str) -> str:
```

**Change:**
```python
def generate_title_response(subject: str, audience: str = "general") -> str:
```

---

#### ~generate_description_response
**Current:**
```python
def generate_description_response(script: str) -> str:
```

**Change:**
```python
def generate_description_response(script: str, audience: str = "general") -> str:
```

---

#### ~generate_tags_response
**Current:**
```python
def generate_tags_response(subject: str) -> list:
```

**Change:**
```python
def generate_tags_response(subject: str, audience: str = "general") -> list:
```

---

#### ~generate_image_prompts_response
**Current:**
```python
def generate_image_prompts_response(subject: str, script: str) -> list:
```

**Change:**
```python
def generate_image_prompts_response(subject: str, script: str, audience: str = "general") -> list:
```

---

### 4.4 src/classes/EdgeTts.py

#### Lines 47-62: Keep fallback, enable SSML

**Current behavior:** Strips ALL prosody on ANY exception

**Current code:**
```python
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

**Analysis:** The current implementation already has fallback for malformed SSML. The issue is it strips prosody even when SSML is valid but rejected for OTHER reasons (e.g., unsupported voice).

**Enhancement:** Add better detection to preserve prosody when it's valid SSML being rejected:

```python
async def _generate_mp3(
    self, text: str, output_path: str, metadata_path: str | None = None
) -> None:
    # Check if input contains SSML tags
    has_ssml = text.strip().startswith("<speak>") or "<prosody" in text or "<w" in text
    
    try:
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path, metadata_path)
    except Exception as e:
        error_msg = str(e).lower()
        
        # If SSML was rejected due to malformed syntax, strip and retry
        if has_ssml and any(err in error_msg for err in ["ssml", "invalid", "malformed", "syntax"]):
            # Strip ALL tags on malformed SSML error
            clean_text = re.sub(r"<[^>]+>", "", text)
            clean_text = clean_text.strip()
            if clean_text:
                communicate = edge_tts.Communicate(clean_text, self._voice)
                await communicate.save(output_path, metadata_path)
            else:
                raise ValueError("Empty text after SSML cleanup") from e
        elif has_ssml:
            # SSML is valid but voice doesn't support it - strip prosody only, keep text
            # Try removing prosody tags but keeping text structure
            text_without_prosody = re.sub(r"<prosety[^>]*>[^<]*</prosody>", "", text, flags=re.IGNORECASE)
            if text_without_prosody != text:
                try:
                    communicate = edge_tts.Communicate(text_without_prosody, self._voice)
                    await communicate.save(output_path, metadata_path)
                    return
                except:
                    pass
            # If still fails, strip all and retry
            clean_text = re.sub(r"<[^>]+>", "", text)
            clean_text = clean_text.strip()
            if clean_text:
                communicate = edge_tts.Communicate(clean_text, self._voice)
                await communicate.save(output_path, metadata_path)
            else:
                raise ValueError("Empty text after SSML cleanup") from e
        else:
            # No SSML, re-raise
            raise
```

---

### 4.5 src/run_24_7.py

#### Line 69: Add audience param

**Current:**
```python
def run_single_video(
    niche: str, output_dir: str, logger: logging.Logger, upload: bool = False, locale: str = "en-US"
) -> dict:
```

**Change:**
```python
def run_single_video(
    niche: str, output_dir: str, logger: logging.Logger, upload: bool = False, locale: str = "en-US", audience: str = "general"
) -> dict:
```

**Also update calling code (around line 248):**
```python
result = run_single_video(topic, output_dir, logger, upload=args.upload, locale=locale, audience=account.get("audience", "general"))
```

**Add to account loading (around line 222):**
```python
audience = account.get("audience") or "general"
logger.info(f"Audience: {audience}")
```

---

### 4.6 src/main.py

**Add --audience flag to CLI:**

```python
parser.add_argument(
    "--audience",
    type=str,
    default="general",
    choices=["beginner", "general", "intermediate", "expert"],
    help="Target audience level (default: general)",
)
```

---

### 4.7 api/models.py

#### AccountCreate: audience field
**Current:**
```python
class AccountCreate(BaseModel):
    platform: str
    username: str
    nickname: str | None = None
    topic: str | None = None
    locale: str = "en-US"
```

**Change:**
```python
class AccountCreate(BaseModel):
    platform: str
    username: str
    nickname: str | None = None
    topic: str | None = None
    locale: str = "en-US"
    audience: str = "general"
```

---

#### AccountUpdate: audience field
**Current:**
```python
class AccountUpdate(BaseModel):
    platform: str | None = None
    username: str | None = None
    nickname: str | None = None
    topic: str | None = None
    locale: str | None = None
```

**Change:**
```python
class AccountUpdate(BaseModel):
    platform: str | None = None
    username: str | None = None
    nickname: str | None = None
    topic: str | None = None
    locale: str | None = None
    audience: str | None = None
```

---

## 5. TASKS (numbered, each with steps)

### Task 1: Database Changes
**Steps:**
1. Read db.py to find exact line numbers
2. Add audience column migration after accounts table CREATE (line ~90)
3. Update add_account() signature with audience param
4. Update add_account() INSERT statement
5. Update valid_fields set

**Verification:**
```bash
python3 -c "from src.db import init_db, get_accounts; init_db(); print([a.get('audience') for a in get_accounts()[:3]])"
```

---

### Task 2: YouTube.py Class Changes
**Steps:**
1. Read YouTube.py to find exact line numbers
2. Add AUDIENCE_GUIDANCE dict before class definition
3. Update __init__ signature with audience param
4. Add self._audience instance variable
5. Add audience property getter
6. Update generate_script() to use dynamic guidance

**Verification:**
```bash
python3 -c "from src.classes.YouTube import YouTube, AUDIENCE_GUIDANCE; print(list(AUDIENCE_GUIDANCE.keys()))"
```

---

### Task 3: run_pipeline.py BYPASS
**Steps:**
1. Read run_pipeline.py to find exact line numbers
2. Add youtube._audience = "general" after youtube._locale assignment

**Verification:**
```bash
python3 -c "from src.run_pipeline import run_pipeline; import inspect; print('audience' in str(inspect.signature(run_pipeline)))"
```

---

### Task 4: llm_generate.py Changes
**Steps:**
1. Read llm_generate.py to find all 7 functions
2. Add audience param to each function signature
3. Use audience in prompt construction where applicable

**Verification:**
```bash
python3 -c "from src.llm_generate import generate_script_response; import inspect; sig = inspect.signature(generate_script_response); print('audience' in sig)"
```

---

### Task 5: EdgeTts.py Enhancement
**Steps:**
1. Read EdgeTts.py to find exact line numbers
2. Enhance _generate_mp3 with better SSML detection
3. Preserve prosody when SSML is valid but rejected

**Verification:**
```bash
python3 -c "from src.classes.EdgeTTS import EdgeTTS; tts = EdgeTTS(); print('Enhanced SSML handling')"
```

---

### Task 6: run_24_7.py Changes
**Steps:**
1. Read run_24_7.py to find exact line numbers
2. Add audience param to run_single_video
3. Update account loading to include audience
4. Pass audience to run_pipeline

**Verification:**
```bash
python3 -c "from src.run_24_7 import run_single_video; import inspect; sig = inspect.signature(run_single_video); print('audience' in sig)"
```

---

### Task 7: main.py CLI
**Steps:**
1. Read main.py to find CLI argument parser location
2. Add --audience flag with choices

**Verification:**
```bash
python3 src/main.py --help | grep audience
```

---

### Task 8: api/models.py Changes
**Steps:**
1. Read api/models.py to find model locations
2. Add audience to AccountCreate
3. Add audience to AccountUpdate

**Verification:**
```bash
python3 -c "from api.models import AccountCreate, AccountUpdate; print(AccountCreate.model_fields); print(AccountUpdate.model_fields)"
```

---

## 6. VERIFICATION COMMANDS

### After all changes, run:

```bash
# 1. Database migration check
python3 -c "
from src.db import init_db, get_accounts
init_db()
accounts = get_accounts()
print('Accounts with audience:', len([a for a in accounts if a.get('audience')]))
print('Sample:', [a.get('audience') for a in accounts[:2]])
"

# 2. YouTube class check  
python3 -c "
from src.classes.YouTube import YouTube, AUDIENCE_GUIDANCE
print('AUDIEN_ GUIDANCE levels:', list(AUDIENCE_GUIDANCE.keys()))
"

# 3. Function signatures check
python3 -c "
import inspect
from src.llm_generate import generate_script_response
sig = inspect.signature(generate_script_response)
print('generate_script_response audience:', 'audience' in sig)
"

# 4. run_24_7 check
python3 -c "
import inspect
from src.run_24_7 import run_single_video
sig = inspect.signature(run_single_video)
print('run_single_video audience:', 'audience' in sig)
"

# 5. API models check
python3 -c "
from api.models import AccountCreate, AccountUpdate
print('AccountCreate audience:', 'audience' in AccountCreate.model_fields)
print('AccountUpdate audience:', 'audience' in AccountUpdate.model_fields)
"

# 6. Integration test
python3 src/run_pipeline.py --niche "test" --locale en-US --audience beginner
echo "Audience parameter passed!"
```

---

## 7. ROLLBACK

### If issues occur:

```bash
# Revert db.py - remove migration and parameter
sed -i 's/cursor.execute("ALTER TABLE accounts ADD COLUMN audience TEXT DEFAULT .general.")/# REMOVED: audience migration/g' src/db.py
sed -i 's/audience: str = "general"//g' src/db.py

# Revert YouTube.py
git checkout src/classes/YouTube.py

# Revert llm_generate.py
git checkout src/llm_generate.py

# Revert api/models.py
git checkout api/models.py

# Revert EdgeTts.py
git checkout src/classes/EdgeTts.py

# Revert run_24_7.py
git checkout src/run_24_7.py
```

### Rollback command:
```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2
git stash  # If changes staged
git checkout -- .  # Revert all changes
```

---

## 8. DEPENDENCIES

No new dependencies required. All changes use existing:
- SQLite (already in use)
- Pydantic BaseModel (already in use)
- Standard re module (already in use)

---

## 9. TESTING

### Manual test scenarios:

1. **Default behavior**: Generate video without audience flag → should use "general"
2. **Beginner**: `--audience beginner` → verify simple language in script
3. **Expert**: `--audience expert` → verify technical terminology in script
4. **Database migration**: Existing accounts should have audience="general" after migration
5. **API**: Create account with audience → verify it saves to DB

### Test scripts to create:

```python
# test_audience.py
from src.llm_generate import analyze_complexity

# Test each audience level
for level in ["beginner", "general", "intermediate", "expert"]:
    result = analyze_complexity("quantum computing", audience=level)
    print(f"{level}: {result[:100]}")
```