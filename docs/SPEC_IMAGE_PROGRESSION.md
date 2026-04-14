# Image Progression Specification

## Overview

Modify `generate_prompts()` in `YouTube.py` to create visual storyboard with explicit narrative phases (Hook → Context → Detail → Twist → Ending) matching FIX_STORYTELLING.md Section 4.

## Current State

- `generate_prompts()` maps script sentences 1:1 to image prompts
- No narrative progression
- Generic "cinematic" style prompts

## Target State

Each image has explicit story role with phase-specific guidance:

| Phase | Role | Goal | Prompt Keywords |
|------|------|------|-----------------|
| 1 | Hook | Grab attention, most shocking | "most shocking", "terrifying", "incredible", "impossible" |
| 2 | Context | Ground the story, setting | "location", "environment", "documentary", "habitat" |
| 3 | Detail | Build curiosity, close-up | "close-up", "extreme detail", "macro", "scientific" |
| 4 | Twist | Peak tension, deepen mystery | "unexpected", "twist", "shocking", "contradiction" |
| 5 | Ending | Loop-ready, unresolved | "staring at camera", "unresolved", "haunting", "mysterious" |

## Implementation

### File: `src/classes/YouTube.py`

Modified function: `generate_prompts()` (around line 770)

### Change Type
Replace existing prompt construction with phase-guided prompt that explicitly maps sentences to story phases.

### New Prompt Template

```python
prompt = f"""You are a visual storyboard director creating a {n_scenes}-frame sequence for: {self.subject}

Script: {script_summary}

Create ONE visual prompt per phase:

PHASES:
1. HOOK - Most shocking/unusual visual. Grab attention immediately.
2. CONTEXT - Where/when it exists. Ground the story.
3. DETAIL - Close-up of strange feature. Build curiosity.
4. TWIST - Something that deepens mystery. Peak tension.
5. ENDING - Unresolved, memorable frame. Loops with opening.

RULES:
- NO text, letters, words, numbers in any frame
- NO close-ups of hands, fingers, extremities
- Wide shots, environments, aerial views preferred
- Consistent cinematic lighting across all frames
- Each frame tells visual story progressing to next

For each phase, output: "PhaseName: prompt (15-25 words)"
"""
```

### Output Format
Parse lines matching pattern: `X. PHASE: prompt` where X is 1-5.

### Fallback
If prompt parsing fails, generate from script sentences with phase keywords appended.

## Testing

Run video generation and verify:
1. 4-5 distinct images generated
2. Each image matches its phase (not generic)
3. Story flows: shocking → setting → detail → twist → ending

## Acceptance Criteria

- [ ] `generate_prompts()` outputs 4-5 prompts
- [ ] Each prompt clearly matches phase role
- [ ] No text/words in generated images
- [ ] Visual story progression observable