# Image Prompt Subject Accuracy — Design Spec

> **Status:** APPROVED for implementation

## Problem Statement
When generating images for YouTube Shorts videos, the system produces images with irrelevant characters/people instead of the actual subject matter from the script. Example: Script about "Hitler in WWII bunker" generates images of random places instead of a figure in a bunker setting.

## Root Causes

### Stage 2 — Enhancement Layer (YouTube.py)
The `generate_image_pollinations()` / `flux()` / `cloudflare()` methods append this to every prompt:
```
Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting,
rounded organic characters, magical realism elements, ultra-detailed expressive
faces, family-friendly adventure scene.
```

The phrases `rounded organic characters`, `ultra-detailed expressive faces`, and `family-friendly adventure scene` are **character injection triggers**. They cause the image model to add random people even when the script is about an object, place, or concept.

### Stage 1 — LLM Prompt Template (llm_prompts.py + YouTube.py)
The old `IMAGE_PROMPT` template was generating 15-25 word prompts that were:
- Too short for Z-Image to work well (needs 90-150 words)
- Vague — "cinematic style" instead of specific subject traits
- Missing subject reinforcement (the subject is mentioned once and not anchored)
- Not aware that Stage 2 will inject characters (so LLM doesn't compensate)

## Solution

### Stage 2 — Clean Style Pass (no character injection)
Replace the enhancement with:
```
Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting,
warm inviting palette, no random characters, no unrelated people
```
**Removed:** `rounded organic characters`, `ultra-detailed expressive faces`, `magical realism elements`, `family-friendly adventure scene`
**Kept:** `Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette`

### Stage 1 — Self-Sufficient Prompt Template
Rewrite `IMAGE_PROMPT` in `llm_prompts.py` to:
1. Fix the style mandate: "Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette" — this is the ONLY style, no negotiation
2. Enforce 90-150 word prompts (Z-Image sweet spot — updated from 80-150 per review)
3. Subject-first: Lead every prompt with specific subject + 2-3 defining traits
4. Subject reinforcement: Mention the main subject 2-3 times in different forms
5. No vague terms: "cinematic" alone is banned; use concrete photography descriptors
6. No substitution rule: If script says "Hitler", show a figure with 1940s military traits — not a generic person
7. Abstract topic handling: If topic is abstract, use concrete visual metaphor

Update `generate_prompts()` in YouTube.py to:
1. Inject `extracted_facts` (topic_identifier, person_names, locations) as mandatory visual anchors
2. Remove 15-25 word cap — let prompts be 90-150 words
3. Add "no substitution" rule explicitly
4. Tell LLM that no additional style enhancement will be added (it must include style in the prompt)
5. Add null safety: if `extracted_facts` is None/empty, use `self.subject` as fallback

## Out of Scope

### generate_thumbnail() — Never Called
`generate_thumbnail()` at YouTube.py line 1707 is **never called** in the video generation pipeline. YouTube Shorts use auto-generated thumbnails. The method exists but is not invoked in `generate_video()`. No changes needed.

## Web Research Requirement

**Web research MUST run before image prompt generation.** The `extracted_facts` dictionary is the primary mechanism for subject anchoring. If web research fails or returns empty facts:
- `self.extracted_facts` will be `None` or `{}`
- The prompt must fall back to using `self.subject` directly
- The no-substitution rule still applies — if `self.subject` says "Hitler in bunker", the prompt must use those exact words

**Implementation:** Ensure `_research_trending_topics()` is always called before `generate_prompts()`. If research returns no facts, still pass `extracted_facts={}` (not None) so the template can use `if self.extracted_facts` checks.

## Files to Modify

| File | Change |
|------|--------|
| `src/classes/YouTube.py:1448-1451` | Replace enhancement in `generate_image_pollinations()` |
| `src/classes/YouTube.py:1504-1507` | Replace enhancement in `generate_image_pollinations_flux()` |
| `src/classes/YouTube.py:~1562` | Replace enhancement in `generate_image_cloudflare()` (verify with grep) |
| `src/classes/YouTube.py:1290-1324` | Rewrite `generate_prompts()` prompt with subject extraction and rules |
| `src/llm_prompts.py` IMAGE_PROMPT | Full template rewrite |
| `src/llm_generate.py` fallback | Use Ghibli style in fallback prompts |

## Word Count Target
- **Target:** 90-150 words per prompt
- **No retry mechanism** — if LLM outputs outside range, accept it (guideline, not hard requirement)
- The 90-150 range was chosen based on Z-Image Turbo's 512 token limit (~600-1000 words) and sweet spot for subject coherence

## Testing
- Generate a video about a specific historical figure/location
- Verify generated image prompts mention the specific subject with traits
- Verify images produced match the script subject, not random characters
- Test fallback path by corrupting LLM output and checking fallback prompts
- Verify `generate_thumbnail()` is never called in the pipeline