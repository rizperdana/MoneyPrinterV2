# MoneyPrinterV2: Complexity-Aware Script Generation

## Overview
Implement complexity tier scoring, dynamic scene count, duration validation, and story completion validation.

## Architecture

```
topic → analyze_complexity() → tier (SIMPLE|MODERATE|COMPLEX)
                              ↓
                   ┌──────────┴──────────┐
                   ↓                     ↓
         duration_range[tier]    n_scenes[tier]
                   ↓                     ↓
         validate_duration()      generate_image_prompts()
                   ↓
         validate_completion() ──→ retry if needed
```

---

## Gap Coverage

| Gap | Solution | Location |
|-----|----------|----------|
| 1. Complexity scorer missing | `analyze_complexity()` | `src/llm_generate.py` |
| 2. Duration validation contradiction | `validate_duration()` | `src/llm_generate.py` |
| 3. Image count static | `n_scenes = f(tier)` | `generate_image_prompts_response()` |
| 4. No completion validation | `validate_completion()` | `src/llm_generate.py` |
| 5. Dead params | Remove from prompt | `generate_script_response()` |
| 6. Narrative arc not enforced | Validate in completion | `validate_completion()` |
| 7. Integration undefined | Full flow in plan | `src/run_pipeline.py` |

---

## Research Findings (MUST Implement)

### 1. Complexity Scoring Weights

```python
COMPLEXITY_WEIGHTS = {
    "entities": 0.25,      # distinct nouns/actors
    "temporal": 0.20,      # time spans mentioned
    "causal": 0.20,        # cause-effect
    "abstract": 0.20,      # intangible concepts
    "technical": 0.15,     # domain-specific terms
}
COMPLEXITY_TIERS = {
    "SIMPLE": (0, 0.35),
    "MODERATE": (0.35, 0.60),
    "COMPLEX": (0.60, 1.0)
}
# Edge cases: single word → MODERATE, empty → SIMPLE
```

### 2. Dynamic Scene Count Formula

```
Simple (50-90sec): 25-30 sec/scene → 2-4 scenes
Moderate (90-180sec): 20-25 sec/scene → 4-8 scenes
Complex (180-240sec): 15-20 sec/scene → 9-16 scenes
n_scenes = ceil(duration_seconds / seconds_per_scene)
```

### 3. Duration Validation Thresholds

| Tier | Sweet Spot | Acceptable Range |
|------|------------|------------------|
| Simple | 50-70s | 40-90s |
| Moderate | 90-120s | 60-180s |
| Complex | 120-180s | 90-240s |

### 4. Story Completion Validation

- **Pre-screen:** check for resolution phrases (the answer is, in conclusion, that's why, etc.)
- **Arc detection:** STASIS → DISRUPTION → ATTEMPT → RESOLUTION
- **On failure:** retry with "Complete this story" prompt (max 1 retry)
- **If still fails:** flag as incomplete

---

# Implementation Steps

## Step 1: Add Complexity Scoring Module

**File:** `src/llm_generate.py`  
**Insert:** After imports (lines 1-5)

### EVIDENCE_REQUIRED
- No complexity analysis function exists
- Must return tier based on subject text

### CHANGE

Add after imports:

```python
# ---------------------------------------------------------------------------
# Complexity Scoring (Reviewer Gap #1)
# ---------------------------------------------------------------------------

COMPLEXITY_WEIGHTS = {
    "entities": 0.25,
    "temporal": 0.20,
    "causal": 0.20,
    "abstract": 0.20,
    "technical": 0.15,
}

COMPLEXITY_TIERS = {
    "SIMPLE": (0, 0.35),
    "MODERATE": (0.35, 0.60),
    "COMPLEX": (0.60, 1.0),
}

DURATION_RANGES = {
    "SIMPLE": {"sweet": (50, 70), "range": (40, 90)},
    "MODERATE": {"sweet": (90, 120), "range": (60, 180)},
    "COMPLEX": {"sweet": (120, 180), "range": (90, 240)},
}

SCENE_SECONDS_PER_TIER = {
    "SIMPLE": (25, 30),   # (min, max) seconds per scene
    "MODERATE": (20, 25),
    "COMPLEX": (15, 20),
}


def _count_pattern(text: str, pattern: str) -> int:
    """Count regex pattern matches in text."""
    import re
    return len(re.findall(pattern, text, re.IGNORECASE))


def analyze_complexity(subject: str) -> str:
    """
    Analyze subject complexity and return tier.
    
    Args:
        subject (str): The topic/subject to analyze.
        
    Returns:
        str: "SIMPLE", "MODERATE", or "COMPLEX"
    """
    if not subject or not subject.strip():
        return "SIMPLE"
    
    text = subject.strip()
    if len(text.split()) == 1:
        return "MODERATE"  # Edge case: single word
    
    # Calculate scores
    scores = {}
    
    # Entities: distinct nouns (capitalized words, proper nouns)
    scores["entities"] = _count_pattern(text, r'\b[A-Z][a-z]+\b') / max(len(text.split()), 1)
    
    # Temporal: time references
    temporal_patterns = r'\b(years?|months?|days?|hours?|ago|before|after|since|when|during|century|decade|ancient|modern|present|past|future)\b'
    scores["temporal"] = _count_pattern(text, temporal_patterns) / max(len(text.split()), 1)
    
    # Causal: cause-effect language
    causal_patterns = r'\b(because|so|therefore|causes|leads to|results in|due to|effect|impact|原因|所以|因此)\b'
    scores["causal"] = _count_pattern(text, causal_patterns) / max(len(text.split()), 1)
    
    # Abstract: intangible concepts
    abstract_patterns = r'\b(concept|idea|theory|principle|belief|philosophy|justice|freedom|love|time|space|energy|quantum|gravity|emotion)\b'
    scores["abstract"] = _count_pattern(text, abstract_patterns) / max(len(text.split()), 1)
    
    # Technical: domain-specific terms
    technical_patterns = r'\b(\w+ology|\w+ics|based|meter|gram|volt|amp|watt|percentage|ratio|algorithm|protocol|interface|system)\b'
    scores["technical"] = _count_pattern(text, technical_patterns) / max(len(text.split()), 1)
    
    # Calculate weighted score
    total_score = sum(COMPLEXITY_WEIGHTS[k] * scores.get(k, 0) for k in COMPLEXITY_WEIGHTS)
    
    # Map to tier
    for tier, (low, high) in COMPLEXITY_TIERS.items():
        if low <= total_score < high:
            return tier
    
    return "MODERATE"  # Default
```

### VERIFICATION
Run: `ctx_search` for `def analyze_complexity`  
Expect: Function found in llm_generate.py

### RISK: med  
### CONF: high

---

## Step 2: Add Duration Validation Function

**File:** `src/llm_generate.py`  
**Insert:** After analyze_complexity()

### EVIDENCE_REQUIRED
- Current validation uses 30s threshold (contradicts research)
- Must use tier-specific ranges

### CHANGE

Add after analyze_complexity():

```python
def validate_duration(script_text: str, tier: str) -> dict:
    """
    Validate script duration against tier-specific ranges.
    
    Args:
        script_text (str): The generated script.
        tier (str): "SIMPLE", "MODERATE", or "COMPLEX"
        
    Returns:
        dict: {"valid": bool, "duration": int, "message": str}
    """
    import re
    
    if tier not in DURATION_RANGES:
        tier = "MODERATE"
    
    # Estimate duration from word count
    # Average speaking rate: 150 words/min = 2.5 words/sec
    words = len(script_text.split())
    estimated_duration = int(words / 2.5)
    
    sweet_min, sweet_max = DURATION_RANGES[tier]["sweet"]
    range_min, range_max = DURATION_RANGES[tier]["range"]
    
    valid = range_min <= estimated_duration <= range_max
    
    return {
        "valid": valid,
        "duration": estimated_duration,
        "tier": tier,
        "in_sweet_spot": sweet_min <= estimated_duration <= sweet_max,
        "message": f"Duration {estimated_duration}s ({'valid' if valid else 'invalid'}) for {tier}tier"
    }
```

### VERIFICATION
Run: `ctx_search` for `def validate_duration`  
Expect: Function found

### RISK: low  
### CONF: high

---

## Step 3: Add Story Completion Validation

**File:** `src/llm_generate.py`  
**Insert:** After validate_duration()

### EVIDENCE_REQUIRED
- No validation for story arc completion
- Need pre-screen and arc detection

### CHANGE

Add after validate_duration():

```python
# Resolution phrases indicating story completion
RESOLUTION_PHRASES = [
    r"that's (why|how|the answer|the reason)",
    r"in conclusion",
    r"the answer is",
    r"so (that\'s|there\'s|the) (reason|explanation)",
    r"and that\'s (the|why|how)",
    r"now you know",
    r"that\'s (it|the story)",
    r"the (next|final) step",
    r"the solution",
    r"the truth about",
    r"here\'s what (happens|we learned)",
]

# Arc stages for detection
ARC_STAGES = ["stasis", "disruption", "attempt", "resolution"]


def validate_completion(script_text: str) -> dict:
    """
    Validate story completion via resolution signals and arc detection.
    
    Args:
        script_text (str): The generated script.
        
    Returns:
        dict: {"complete": bool, "has_resolution": bool, "arc_detected": list, "message": str}
    """
    import re
    
    text = script_text.lower()
    
    # Pre-screen: resolution phrases
    has_resolution = False
    for phrase in RESOLUTION_PHRASES:
        if re.search(phrase, text):
            has_resolution = True
            break
    
    # Arc detection (stage keywords)
    arc_detected = []
    if re.search(r"\b(now|, so|but then|then)\b", text):
        arc_detected.append("disruption")
    if re.search(r"\b(tried|attempted|decided|started|began)\b", text):
        arc_detected.append("attempt")
    if re.search(r"\b(finally|in the end|as a result|eventually|so now)\b", text):
        arc_detected.append("resolution")
    if re.search(r"\b(once|traditionally|normally|usually|every)\b", text):
        arc_detected.append("stasis")
    
    complete = has_resolution or len(arc_detected) >= 2
    
    return {
        "complete": complete,
        "has_resolution": has_resolution,
        "arc_detected": arc_detected,
        "message": f"{'complete' if complete else 'incomplete'} - resolution:{has_resolution}, arc:{arc_detected}"
    }


def check_and_complete_script(script_text: str) -> tuple:
    """
    Check completion and retry with completion prompt if needed.
    
    Args:
        script_text (str): The generated script.
        
    Returns:
        tuple: (final_script, validation_result)
    """
    validation = validate_completion(script_text)
    
    if validation["complete"]:
        return script_text, validation
    
    # Retry once with completion prompt
    completion_prompt = get_prompt(
        "script_complete",
        original_script=script_text
    )
    retry_script = generate_response(completion_prompt, job="script")
    
    # Validate retry
    retry_validation = validate_completion(retry_script)
    
    if retry_validation["complete"]:
        return retry_script, retry_validation
    
    # Still incomplete - flag it
    return retry_script, {
        "complete": False,
        "has_resolution": retry_validation["has_resolution"],
        "arc_detected": retry_validation["arc_detected"],
        "message": "incomplete after retry - flagged"
    }
```

### VERIFICATION
Run: `ctx_search` for `def validate_completion`  
Expect: Function found

### RISK: med  
### CONF: high

---

## Step 4: Remove Dead Function Parameters

**File:** `src/llm_generate.py`  
**Target:** Lines 43-67 (generate_script_response)

### EVIDENCE_REQUIRED
- `max_words_per_sentence` and `max_total_words` passed to prompt but template doesn't use them
- Dead params per reviewer

### CHANGE

Replace generate_script_response (lines 43-67):

```python
def generate_script_response(subject: str, locale: str, sentence_length: int) -> str:
    """
    Generate script for subject.
    
    Args:
        subject (str): The subject for the script.
        locale (str): BCP-47 locale code (e.g., en-US, id-ID).
        sentence_length (int): Kept for API compatibility (ignored by new template).
        
    Returns:
        str: Raw script text.
    """
    # Remove dead params - template doesn't use them
    prompt = get_prompt(
        "script",
        subject=subject,
        language=locale,
        locale=locale,
    )

    completion = generate_response(prompt, job="script")
    completion = re.sub(r"\*", "", completion)
    return completion
```

### VERIFICATION
Run: `ctx_symbol` for `generate_script_response`  
Expect: No max_words in get_prompt call

### RISK: low  
### CONF: high

---

## Step 5: Update Prompt Template - Remove Dead Params

**File:** `src/llm_prompts.py`  
**Target:** Lines 62-119 (SCRIPT template)

### EVIDENCE_REQUIRED
- Template references `{max_words_per_sentence}` and `{max_total_words}` 
- These are never used - should be removed

### CHANGE

Replace SCRIPT template CONSTRAINTS section (lines ~96-100):

```python
CONSTRAINTS:
- Write naturally in {language}
- End when story is COMPLETE, not when sentence limit hit
- Minimum 4 sentences (story arc needs stasis → resolution)
- NO "welcome", NO "in this video", NO "subscribe"
- NO markdown, NO numbering, NO bullet points
```

Remove from template:
- `{max_words_per_sentence}` 
- `{max_total_words}`

### VERIFICATION
Run: `ctx_search` for `max_words_per_sentence` in llm_prompts.py  
Expect: NOT found

### RISK: low  
### CONF: high

---

## Step 6: Add Script Complete Prompt for Retry

**File:** `src/llm_prompts.py`  
**Insert:** After SCRIPT definition

### CHANGE

Add new prompt:

```python
SCRIPT_COMPLETE = """Complete this story by adding the resolution.
The story starts well but ends incompletely. Your task:
1. Read the existing script
2. Add 1-3 sentences that resolve the story arc
3. End with a clear resolution, answer, or payoff

EXISTING SCRIPT:
{original_script}

OUTPUT: Add ONLY the completion sentences (no labels, no "here's the ending")."""
```

Add to get_prompt prompt_map:

```python
"script_complete": SCRIPT_COMPLETE,
```

### VERIFICATION
Run: `ctx_search` for `SCRIPT_COMPLETE` in llm_prompts.py  
Expect: Found

### RISK: low  
### CONF: high

---

## Step 7: Add Dynamic Scene Count

**File:** `src/llm_generate.py`  
**Target:** generate_image_prompts_response() (lines ~147-192)

### EVIDENCE_REQUIRED
- n_scenes currently static (lines 171-172)
- Need dynamic based on tier

### CHANGE

Replace n_scenes calculation (lines 171-172):

```python
def generate_image_prompts_response(subject: str, script: str, tier: str = "MODERATE") -> list:
    """
    Generate image prompts from script.
    
    Args:
        subject (str): The subject.
        script (str): The script text.
        tier (str): Complexity tier for scene count (SIMPLE|MODERATE|COMPLEX).
        
    Returns:
        list: List of image prompts.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", script) if len(s.strip()) > 10]
    
    # Dynamic scene count per tier (Reviewer Gap #3)
    # Simple: 4-6 scenes, Moderate: 6-8 scenes, Complex: 8-12 scenes
    tier_scene_ranges = {
        "SIMPLE": (4, 6),
        "MODERATE": (6, 8),
        "COMPLEX": (8, 12),
    }
    min_scenes, max_scenes = tier_scene_ranges.get(tier, (6, 8))
    n_scenes = min(max(len(sentences), min_scenes), max_scenes)
```

### VERIFICATION
Run: `ctx_search` for `tier_scene_ranges` in llm_generate.py  
Expect: Found

### RISK: med  
### CONF: high

---

## Step 8: Add Integration to run_pipeline

**File:** `src/run_pipeline.py`  
**Insert:** In run_pipeline() function

### EVIDENCE_REQUIRED
- Pipeline doesn't call complexity analysis
- Integration undefined (Gap #7)

### CHANGE

Add to run_pipeline() after getting topic:

```python
# Add complexity analysis to pipeline
def run_pipeline(niche: str, locale: str = "en-US", upload: bool = False, headless: bool = True) -> dict:
    # ... existing code ...
    
    # After topic selected (around line 45):
    selected_topic = topics[0]  # or user selection
    
    # Analyze complexity (Gap #7 - Integration)
    tier = analyze_complexity(selected_topic)
    print(f"[🎯 Complexity] {selected_topic[:50]}... → {tier}")
    
    # Duration validation config based on tier
    duration_config = DURATION_RANGES[tier]
    
    # ... generate script ...
    script = generate_script_response(selected_topic, locale, 0)
    
    # Validate duration
    duration_result = validate_duration(script, tier)
    print(f"[⏱ Duration] {duration_result['duration']}s - {duration_result['message']}")
    
    # Validate completion
    completion_result = validate_completion(script)
    if not completion_result["complete"]:
        print(f"[⚠ Completion] Retrying story completion...")
        script, completion_result = check_and_complete_script(script)
    print(f"[✓ Completion] {completion_result['message']}")
    
    # Generate image prompts with tier-based scene count
    image_prompts = generate_image_prompts_response(selected_topic, script, tier)
    print(f"[🎬 Scenes] {len(image_prompts)} images for {tier} tier")
```

### VERIFICATION
Run: `ctx_search` for `analyze_complexity` in run_pipeline.py  
Expect: Found

### RISK: med  
### CONF: med

---

## Step 9: Fix Hard 8-Sentence Truncation in YouTube.py

**File:** `src/classes/YouTube.py`  
**Target:** `_validate_script_timing()` (lines 1047-1053)

### EVIDENCE_REQUIRED
- `YouTube.py:1048` has hard 8-sentence truncation
- Reviewer: "REMOVE hard 8-sentence limit, replace with story completion check"

### CHANGE

Replace the hard 8-sentence truncation block:

```python
# OLD (lines 1047-1053):
        # Validate sentence count (target 6-8)
        if sentence_count > 8:
            warning(f"Too many sentences: {sentence_count} (target 6-8). Truncating...")
            sentences = sentences[:8]
            script = ". ".join(sentences)
            if script and not script[-1] in ".!?":
                script += "."

# NEW:
        # Story completion check: enforce minimum sentences (4), no hard max truncation
        # Let the story complete naturally — validation handles quality
        if sentence_count < 4:
            warning(f"Too few sentences: {sentence_count} (minimum 4 for story arc)")
```

**Key change:** Remove `if sentence_count > 8:` truncation entirely. Stories should complete naturally without artificial sentence caps.

### VERIFICATION
Run: `ctx_search` for `sentence_count > 8` in YouTube.py  
Expect: NOT found

### RISK: med  
### CONF: high

---

## Step 10: Replace 30s Duration Warning with Tier-Appropriate Validation

**File:** `src/classes/YouTube.py`  
**Target:** `_validate_script_timing()` (lines 1055-1059)

### EVIDENCE_REQUIRED
- `YouTube.py:1056` has `if estimated_duration > 30:` warning threshold
- Reviewer: "contradicts 50sec minimum requirement"
- Should use tier-appropriate ranges from `DURATION_RANGES`

### CHANGE

Replace the 30s hardcoded warning:

```python
# OLD (lines 1055-1059):
        # Warn if duration exceeds target
        if estimated_duration > 30:
            warning(
                f"Script estimated duration: {estimated_duration:.0f}s (target 20-30s)"
            )

# NEW:
        # Warn using tier-appropriate ranges (imported from llm_generate or inline)
        # For YouTube Shorts context: use MODERATE tier as default (60-180s)
        # This replaces the incorrect 30s threshold
        tier = "MODERATE"
        if estimated_duration < 60:
            warning(
                f"Script too short: {estimated_duration:.0f}s (minimum 50s for Shorts)"
            )
        elif estimated_duration > 180:
            warning(
                f"Script too long: {estimated_duration:.0f}s (maximum 180s for Shorts)"
            )
        if get_verbose():
            info(
                f" => Timing: ~{word_count} words, {sentence_count} sentences, {estimated_duration:.0f}s TTS"
            )
```

**Key change:** Replace hard 30s threshold with tier-appropriate ranges. For Shorts, MODERATE (60-180s) aligns with the 50s minimum requirement.

### VERIFICATION
Run: `ctx_search` for `estimated_duration > 30` in YouTube.py  
Expect: NOT found  
Run: `ctx_search` for `estimated_duration < 60` in YouTube.py  
Expect: Found

### RISK: med  
### CONF: high

---

# Implementation Order

| Seq | Step | Dependencies | Files |
|-----|------|--------------|-------|
| 1 | Add complexity module | - | llm_generate.py |
| 2 | Add duration validation | 1 | llm_generate.py |
| 3 | Add completion validation | 1 | llm_generate.py |
| 4 | Remove dead params | - | llm_generate.py |
| 5 | Update prompt template | - | llm_prompts.py |
| 6 | Add completion prompt | 5 | llm_prompts.py |
| 7 | Dynamic scene count | 1, 3 | llm_generate.py |
| 8 | Pipeline integration | 1-7 | run_pipeline.py |
| 9 | Fix YouTube 8-sentence cap | - | YouTube.py |
| 10 | Fix YouTube 30s threshold | 2 | YouTube.py |

---

# Verification Commands

| Step | Command | Expected |
|------|---------|----------|
| 1 | `ctx_search` for `def analyze_complexity` | Found |
| 2 | `ctx_search` for `def validate_duration` | Found |
| 3 | `ctx_search` for `def validate_completion` | Found |
| 4 | `ctx_search` for `max_words_per_sentence` in generate.py | NOT found |
| 5 | `ctx_search` for `max_words_per_sentence` in prompts.py | NOT found |
| 6 | `ctx_search` for `SCRIPT_COMPLETE` | Found |
| 7 | `ctx_search` for `tier_scene_ranges` | Found |
| 8 | `ctx_search` for `analyze_complexity` in run_pipeline.py | Found |
| 9 | `ctx_search` for `sentence_count > 8` in YouTube.py | NOT found |
| 10 | `ctx_search` for `estimated_duration > 30` in YouTube.py | NOT found |

---

# Rollback Commands

| Step | Rollback Action |
|------|-----------------|
| 1 | `git checkout src/llm_generate.py` (restore) |
| 2 | Same |
| 3 | Same |
| 4 | Same |
| 5 | `git checkout src/llm_prompts.py` |
| 6 | Same |
| 7 | Restore function signature |
| 8 | Remove integration code |
| 9 | `git checkout src/classes/YouTube.py` (restore _validate_script_timing) |
| 10 | Same |