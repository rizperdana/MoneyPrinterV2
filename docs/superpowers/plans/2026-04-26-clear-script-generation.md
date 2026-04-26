# Clear Script Generation - Implementation Plan

**Goal:** Rewrite SCRIPT prompt with 4-step structure, fix audience mismatch, clean up unused parameters.

**Approved Design (from user):**
```
STEP 1 - SETUP (1 sentence): Hook with ONE surprising fact about the topic.
STEP 2 - DISCOVERY (2-3 sentences): What happened / What is it / The facts. Be specific.
STEP 3 - EXPLANATION (2-3 sentences): WHY this matters / WHY it works. Use simple analogy.
STEP 4 - TAKEAWAY (1-2 sentences): MUST answer "so what?" or "why should I care?"

Rules:
1. ONE topic only
2. NEW info every sentence
3. Simple words (general audience 12+)
4. MUST end with takeaway
```

## Current State (from research)

| File | Line | Issue |
|------|------|-------|
| `src/llm_prompts.py` | 62-120 | SCRIPT constant - elementary audience (6-10), SSML complexity, no 4-step structure |
| `src/llm_generate.py` | 177-201 | generate_script_response() - passes unused params to prompt |
| `src/llm_generate.py` | 28-73 | analyze_complexity() exists but never called |
| `src/llm_generate.py` | 116-127 | validate_completion() exists but never used |

## Tasks

### Task 1: Rewrite SCRIPT Prompt (src/llm_prompts.py:62)
**Duration:** 3-5 min  
**Risk:** med  
**Confidence:** high

**What:** Replace SCRIPT constant with 4-step structure

**Changes:**
- Audience: "Elementary school children (ages 6-10)" → "General audience (ages 12+)"
- Structure: Apply 4-step template (SETUP → DISCOVERY → EXPLANATION → TAKEAWAY)
- Remove SSML complexity - output plain text instead
- Add subject reinforcement requirement
- Keep simple words rule but adjust for 12+ audience (not 2-syllable max)

**Verify:** New prompt contains STEP 1-4 sections, outputs plain text (no SSML tags)

---

### Task 2: Clean Up generate_script_response() (src/llm_generate.py:177)
**Duration:** 2-3 min  
**Risk:** low  
**Confidence:** high

**What:** Remove unused parameters from prompt construction

**Changes:**
- Remove `sentence_length`, `max_words_per_sentence`, `max_total_words` from get_prompt() call
- Keep only `subject` and `language` (or `locale`) as they're used
- Simple change - just delete the unused kwargs

**Before:**
```python
prompt = get_prompt(
    "script",
    subject=subject,
    language=locale,
    locale=locale,
    sentence_length=sentence_length,
    max_words_per_sentence=12,
    max_total_words=100
)
```

**After:**
```python
prompt = get_prompt(
    "script",
    subject=subject,
    language=locale
)
```

**Verify:** Function still works, only 2 kwargs passed

---

### Task 3: Integrate analyze_complexity() - Optional (src/llm_generate.py:177)
**Duration:** 3-5 min  
**Risk:** med  
**Confidence:** medium

**What:** Use analyze_complexity() to adapt prompt based on subject complexity

**Changes:**
- Add complexity tier detection before generating script
- Pass tier to prompt (SIMPLE/MODERATE/COMPLEX)
- Adjust word count/sentence count based on tier in prompt

**Skip if:** Not needed for MVP - prompt works for all complexities

**Verify:** Complexity tier appears in prompt output

---

### Task 4: Add Completion Validation - Optional (src/llm_generate.py:199)
**Duration:** 2-3 min  
**Risk:** low  
**Confidence:** medium

**What:** Use validate_completion() to check script before returning

**Changes:**
- Call validate_completion() on generated script
- If incomplete, retry once or append completion

**Skip if:** LLM produces complete scripts reliably

**Verify:** validate_completion() called on output

---

## Verification Commands

```bash
# Run preflight to check for errors
python3 scripts/preflight_local.py

# Smoke test - try generating a script
python3 -c "
from src.llm_generate import generate_script_response
result = generate_script_response('sharks have six senses', 'en-US', 4)
print(result)
"
```

## Success Criteria

- [ ] SCRIPT prompt uses 4-step structure (SETUP/DISCOVERY/EXPLANATION/TAKEAWAY)
- [ ] Audience changed to "general audience (12+)"
- [ ] Output is plain text (no SSML tags required)
- [ ] Unused parameters removed from generate_script_response()
- [ ] Script generation works without errors