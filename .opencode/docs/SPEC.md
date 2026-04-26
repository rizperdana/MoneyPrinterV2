# MoneyPrinterV2: Complexity-Aware Script Generation Spec

## Gap Coverage (Updated)

| Gap | Solution | Location |
|-----|----------|----------|
| 1. Complexity scorer missing | `analyze_complexity()` | `src/llm_generate.py` |
| 2. Duration validation contradiction | `validate_duration()` | `src/llm_generate.py` |
| 3. Image count static | `n_scenes = f(tier)` | `generate_image_prompts_response()` |
| 4. No completion validation | `validate_completion()` | `src/llm_generate.py` |
| 5. Dead params | Remove from prompt | `generate_script_response()` |
| 6. Narrative arc not enforced | Validate in completion | `validate_completion()` |
| 7. Integration undefined | Full flow in plan | `src/run_pipeline.py` |
| 8. YouTube.py 8-sentence hard cap | Remove truncation | `YouTube.py._validate_script_timing()` |
| 9. YouTube.py 30s threshold | Replace with tier ranges | `YouTube.py._validate_script_timing()` |

## Solution Architecture

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

## Component Specifications

### 1. Complexity Scorer (Gap #1)

**Function:** `analyze_complexity(subject: str) -> str`

**Weights:**
| Factor | Weight | Description |
|--------|--------|-------------|
| entities | 0.25 | distinct nouns/actors |
| temporal | 0.20 | time spans mentioned |
| causal | 0.20 | cause-effect language |
| abstract | 0.20 | intangible concepts |
| technical | 0.15 | domain-specific terms |

**Tiers:**
| Tier | Score Range |
|------|------------|
| SIMPLE | 0.00 - 0.35 |
| MODERATE | 0.35 - 0.60 |
| COMPLEX | 0.60 - 1.00 |

**Edge Cases:**
- Empty subject → SIMPLE
- Single word → MODERATE

### 2. Duration Validation (Gap #2)

**Function:** `validate_duration(script_text: str, tier: str) -> dict`

**Thresholds:**
| Tier | Sweet Spot | Acceptable Range |
|------|------------|------------------|
| Simple | 50-70s | 40-90s |
| Moderate | 90-120s | 60-180s |
| Complex | 120-180s | 90-240s |

**Estimation:** words / 2.5 = seconds (150 wpm speaking rate)

### 3. Dynamic Scene Count (Gap #3)

**Function:** `generate_image_prompts_response(subject, script, tier)`

**Scenes per Tier:**
| Tier | Min Scenes | Max Scenes |
|------|-----------|------------|
| Simple | 4 | 6 |
| Moderate | 6 | 8 |
| Complex | 8 | 12 |

### 4. Story Completion Validation (Gap #4, #6)

**Function:** `validate_completion(script_text: str) -> dict`

**Resolution Phrases:**
- "that's why/how/the answer"
- "in conclusion"
- "the answer is"
- "now you know"
- "and that's the reason"
- "the solution"

**Arc Detection:** STASIS → DISRUPTION → ATTEMPT → RESOLUTION

**Retry Logic:** Max 1 retry with "Complete this story" prompt

### 5. Dead Param Removal (Gap #5)

**Files:** 
- `src/llm_generate.py` - remove from generate_script_response()
- `src/llm_prompts.py` - remove from SCRIPT template

**Removed:** `{max_words_per_sentence}`, `{max_total_words}`

### 6. Pipeline Integration (Gap #7)

**Flow in run_pipeline():**

1. Get topic
2. `tier = analyze_complexity(topic)`
3. `duration_config = DURATION_RANGES[tier]`
4. Generate script
5. `duration_result = validate_duration(script, tier)`
6. `completion_result = validate_completion(script)`
7. If incomplete: `script = check_and_complete_script(script)`
8. `image_prompts = generate_image_prompts_response(..., tier)`

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `src/llm_generate.py` | Add complex/mod | After imports |
| `src/llm_generate.py` | Add validate_duration | After complex |
| `src/llm_generate.py` | Add validate_completion | After validate |
| `src/llm_generate.py` | Update generate_script | Lines 43-67 |
| `src/llm_generate.py` | Update image prompts | Add tier param |
| `src/llm_prompts.py` | Clean SCRIPT template | Lines 96-100 |
| `src/llm_prompts.py` | Add SCRIPT_COMPLETE | After SCRIPT |
| `src/run_pipeline.py` | Add integration | In run_pipeline() |
| `src/classes/YouTube.py` | Remove 8-sentence cap | _validate_script_timing() |
| `src/classes/YouTube.py` | Replace 30s threshold | _validate_script_timing() |

## Success Criteria

1. `analyze_complexity("quantum physics")` returns "COMPLEX"
2. `analyze_complexity("cat facts")` returns "SIMPLE"
3. `validate_duration(script, "MODERATE")` respects 60-180s
4. `validate_completion()` detects resolution phrases
5. No `max_words_per_sentence` in generate.py or prompts.py
6. Scene count varies by tier

## Test Scenarios

| Test | Input | Expected |
|------|-------|----------|
| Complex scorer | "quantum entanglement physics" | COMPLEX |
| Simple scorer | "cat photos" | SIMPLE |
| Edge single | "AI" | MODERATE |
| Duration valid | 70s script, MODERATE | valid |
| Duration invalid | 30s script, MODERATE | invalid |
| Completion | Script with "that's why" | complete |
| Scenes simple | 5 sentences, SIMPLE | 4-6 scenes |
| Scenes complex | 10 sentences, COMPLEX | 8-12 scenes |