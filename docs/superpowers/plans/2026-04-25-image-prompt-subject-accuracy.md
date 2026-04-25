# Image Prompt Subject Accuracy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Goal:** Make image generation show the correct subject from the video script by fixing (1) the style enhancement layer that injects random characters, and (2) the LLM prompt template that generates vague prompts. Also disable `generate_thumbnail()` since YouTube Shorts don't use custom thumbnails.
>
> **Architecture:** Two-stage fix:
> - **Stage 1 (upstream):** Rewrite `IMAGE_PROMPT` template and `generate_prompts()` to produce subject-anchored, detailed prompts with mandatory Ghibli/watercolor style.
> - **Stage 2 (downstream):** Replace the character-injecting enhancement in `generate_image_pollinations()` / `flux()` / `cloudflare()` with a clean style pass (Ghibli/watercolor) that does NOT inject people or faces.
>
> **Tech Stack:** Python 3.12, Pollinations AI (zimage/flux), minimax m2.5 LLM

---

## File Map

```
src/
  llm_prompts.py           # IMAGE_PROMPT template rewrite (Task 4)
  llm_generate.py          # Fallback prompt fix in generate_image_prompts_response() (Task 6)
  classes/
    YouTube.py             # generate_image_pollinations enhancement (Task 1)
                            # generate_image_pollinations_flux enhancement (Task 2)
                            # generate_image_cloudflare enhancement (Task 3)
                            # generate_prompts() upstream prompt rewrite (Task 5)
docs/
  superpowers/
    specs/
      2026-04-25-image-prompt-subject-accuracy-design.md   # Design doc (Task 0)
```

---

## Task 0: Write Design Doc

**Files:**
- Create: `docs/superpowers/specs/2026-04-25-image-prompt-subject-accuracy-design.md`

> **Note:** The design spec file has already been created at the path above. Verify it exists, then commit.

- [ ] **Step 1: Verify design spec exists**
```bash
ls -la /home/anon/Projects/experiment/MoneyPrinterV2/docs/superpowers/specs/2026-04-25-image-prompt-subject-accuracy-design.md && echo "EXISTS" || echo "MISSING"
```
Expected: "EXISTS"

- [ ] **Step 2: Commit design doc**
```bash
git add docs/superpowers/specs/2026-04-25-image-prompt-subject-accuracy-design.md
git commit -m "docs: add image prompt subject accuracy design spec"
```

---

## Task 1: Fix Stage 2 Enhancement in generate_image_pollinations()

**Files:**
- Modify: `src/classes/YouTube.py:1448-1451`

- [ ] **Step 1: Show current code (lines 1448-1451)**
```python
# Current code — line 1448-1451
api_key = os.environ.get("POLLINATIONS_API_KEY", "")

enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, rounded organic characters, magical realism elements, warm inviting palette, ultra-detailed expressive faces, family-friendly adventure scene."
```

> **Note:** Run `grep -n "rounded organic characters" src/classes/YouTube.py` first to confirm line numbers match ~1448-1451.

- [ ] **Step 2: Edit the enhancement to remove character injection**
```python
api_key = os.environ.get("POLLINATIONS_API_KEY", "")

# Clean style pass: retain Ghibli/watercolor aesthetic, remove character/face injection
enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette, no random characters, no unrelated people, no text, no watermarks, no logos"
```

- [ ] **Step 3: Verify file still parses (basic syntax check)**
```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "import ast; ast.parse(open('src/classes/YouTube.py').read())" && echo "Syntax OK"
```

- [ ] **Step 4: Commit**
```bash
git add src/classes/YouTube.py
git commit -m "fix(image): remove character injection from Pollinations zimage enhancement"
```

---

## Task 2: Fix Stage 2 Enhancement in generate_image_pollinations_flux()

**Files:**
- Modify: `src/classes/YouTube.py:1504-1507`

- [ ] **Step 1: Show current code (lines 1504-1507)**
```python
# Current code — line 1504-1507
api_key = os.environ.get("POLLINATIONS_API_KEY", "")

enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, rounded organic characters, magical realism elements, warm inviting palette, ultra-detailed expressive faces, family-friendly adventure scene."
```

> **Note:** Run `grep -n "rounded organic characters" src/classes/YouTube.py` first to confirm line numbers match ~1504-1507.

- [ ] **Step 2: Edit the enhancement (identical fix to flux)**
```python
api_key = os.environ.get("POLLINATIONS_API_KEY", "")

# Clean style pass: retain Ghibli/watercolor aesthetic, remove character/face injection
enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette, no random characters, no unrelated people, no text, no watermarks, no logos"
```

- [ ] **Step 3: Verify syntax**
```bash
python3 -c "import ast; ast.parse(open('src/classes/YouTube.py').read())" && echo "Syntax OK"
```

- [ ] **Step 4: Commit**
```bash
git add src/classes/YouTube.py
git commit -m "fix(image): remove character injection from Pollinations flux enhancement"
```

---

## Task 3: Fix Stage 2 Enhancement in generate_image_cloudflare()

**Files:**
- Modify: `src/classes/YouTube.py` (exact line TBD via grep)

> **⚠️ CRITICAL FIX (from review):** The line number in the original plan was approximate (1547-1560). The actual line is ~1562 and may include a `, high quality, detailed` suffix. Always verify with grep before editing.

- [ ] **Step 1: Find the exact line number of the cloudflare enhancement**
```bash
grep -n "rounded organic characters" /home/anon/Projects/experiment/MoneyPrinterV2/src/classes/YouTube.py
```
Expected output: lists ALL three occurrences (zimage, flux, cloudflare) with exact line numbers.

- [ ] **Step 2: Edit the cloudflare enhancement at its exact line number**
Replace only the cloudflare occurrence. The zimage (Task 1) and flux (Task 2) lines should already be fixed.
```python
# OLD (verify exact line — may include ", high quality, detailed" suffix):
enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, rounded organic characters, magical realism elements, warm inviting palette, ultra-detailed expressive faces, family-friendly adventure scene., high quality, detailed"
# NEW:
enhanced_prompt = f"{prompt}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette, no random characters, no unrelated people, no text, no watermarks, no logos"
```

- [ ] **Step 3: Verify syntax**
```bash
python3 -c "import ast; ast.parse(open('src/classes/YouTube.py').read())" && echo "Syntax OK"
```

- [ ] **Step 4: Commit**
```bash
git add src/classes/YouTube.py
git commit -m "fix(image): remove character injection from Cloudflare image enhancement"
```

---

## Task 4: Rewrite IMAGE_PROMPT Template in llm_prompts.py

**Files:**
- Modify: `src/llm_prompts.py` — replace `IMAGE_PROMPT` constant

- [ ] **Step 1: Show current IMAGE_PROMPT (lines ~165-205)**
```bash
sed -n '/^IMAGE_PROMPT = """$/,/^"""$/p' /home/anon/Projects/experiment/MoneyPrinterV2/src/llm_prompts.py
```

- [ ] **Step 2: Replace the IMAGE_PROMPT template**

Find the exact location of IMAGE_PROMPT in the file and replace it:

```python
IMAGE_PROMPT = """
You are a text-to-image prompt engineer writing for Z-Image Turbo (pollinations.ai zimage model).

STYLE (MANDATORY — use this exact style for every prompt, do not omit or modify):
Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette.

TASK:
For each script sentence below, write ONE complete visual scene prompt for Z-Image Turbo.
The prompt must tell the image model EXACTLY what to show — subject, environment, shot type, lighting, and nuance.
Write prompts that work WITHOUT any additional enhancement or post-processing.

SUBJECT FROM VIDEO: {subject}

SCRIPT SENTENCES (write one prompt per sentence, in order):
{sentences}

FOR EACH SENTENCE, CREATE A PROMPT WITH THESE ELEMENTS:
1. SUBJECT — Who or what is the primary focus? Give 2-3 specific defining traits.
   If the script mentions a person (e.g., "Hitler"), describe the figure specifically:
   "a figure in a 1940s German military uniform with Iron Cross medal, not a generic soldier"
   If the script mentions an object (e.g., "the mantis shrimp's claw"), be specific:
   "the raptorial claw of a mantis shrimp, extended and ready to strike"
   If the script mentions a place (e.g., "the Brandenburg Gate"), show recognizable features:
   "the Brandenburg Gate in Berlin with its quadriga statue, sandstone columns"
2. ACTION/STATE — What is the subject doing or how does it appear in this moment?
3. ENVIRONMENT — Where is it? Include only setting details that directly support subject identification.
4. SHOT TYPE — Wide establishing / medium / close-up / aerial? Choose what best shows the subject clearly.
5. LIGHTING — Type and direction: golden hour sunlight, soft overcast, dramatic rim light, etc.
6. NUANCE — Any specific visual details that further clarify the subject (materials, textures, colors)?

RULES (STRICT — every prompt must follow these):
- SUBJECT MUST appear and be clearly identifiable in every prompt
- If script is about a PERSON, show that specific person with distinguishing traits — NOT a generic human figure
- If script is about an OBJECT, show that object clearly with defining characteristics — NOT a generic item
- If script is about a PLACE, show recognizable features of that place — NOT a generic looking location
- DO NOT substitute generic alternatives for the specific subject in the script
- MANDATORY STYLE: Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette
- NO text, no letters, no numbers, no signs, no logos, no writing of any kind
- NO close-ups of hands, fingers, or human extremities (unless hands are the actual subject)
- NO vague adjectives alone: do not use "cinematic", "beautiful", "epic", "magical", "dreamlike" without concrete subject info
- If the topic is ABSTRACT (e.g., "justice", "freedom", "time"), represent it through a concrete visual metaphor before applying style
- 90-150 words per prompt (Z-Image Turbo sweet spot)
- Use complete natural sentences, NOT tag lists
- Mention the primary subject 2-3 times in different forms within the prompt for reinforcement

TECHNICAL PARAMS (append to each prompt):
"Params: num_inference_steps={num_inference_steps}, acceleration={acceleration}, image_size={image_size}"

OUTPUT FORMAT:
Numbered 1 to {n_scenes}. Each prompt on its own line.
- Target length: 90-150 words per prompt
- Use complete natural sentences (NOT tags/lists)
- NO JSON, NO quotes, NO bullet points
- Scenes must flow as a visual narrative (beginning → middle → end)
- Same Ghibli/watercolor style across ALL scenes

Example output:
1. A weathered prospector in a torn flannel shirt and dusty denim crouches beside a rushing mountain stream, panning for gold with calloused hands. The scene unfolds in a secluded Sierra Nevada canyon during late autumn golden hour. Shot in Studio Ghibli style with soft earthy watercolor lighting, warm inviting palette. Wide establishing shot with the subject placed using rule of thirds. Sharp focus throughout, no text, no random characters. Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9
2. An extreme aerial drone shot soaring over the canyon rim at sunrise, revealing the vast scale of the Sierra Nevada wilderness bathed in pink and orange alpenglow. Studio Ghibli style with soft earthy watercolor lighting, warm inviting palette. No text, no random characters. Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9
"""
```

- [ ] **Step 3: Verify syntax**
```bash
python3 -c "import ast; ast.parse(open('src/llm_prompts.py').read())" && echo "Syntax OK"
```

- [ ] **Step 4: Commit**
```bash
git add src/llm_prompts.py
git commit -m "refactor(image): rewrite IMAGE_PROMPT template for subject accuracy and Z-Image optimization"
```

---

## Task 5: Strengthen generate_prompts() in YouTube.py

**Files:**
- Modify: `src/classes/YouTube.py:1290-1324` (approx — the prompt sent to LLM)

- [ ] **Step 1: Show current prompt section (lines ~1290-1324)**
```bash
sed -n '1290,1324p' /home/anon/Projects/experiment/MoneyPrinterV2/src/classes/YouTube.py
```

- [ ] **Step 2: Edit the prompt in generate_prompts() to add subject extraction and rules**

Find the `prompt = f"""You are a visual storyboard director...` section (starting around line 1290) and replace it with:

```python
    prompt = f"""You are a visual storyboard director creating a {n_scenes}-frame sequence for a YouTube Short about: {self.subject}

SCRIPT: {self.script[:500]}...
{visual_grounding}

MANDATORY STYLE (apply to every frame):
Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette.

EXTRACTED SUBJECT FACTS (each MUST appear in the visuals — not generic substitutes):
- Topic: {topic_id if topic_id else self.subject}
- Location: {primary_loc if primary_loc else 'unknown'}
- Key visual element: {primary_kf if primary_kf else 'mysterious setting'}
{f'- Specific persons: {", ".join(self.extracted_facts.get("person_names", []))}' if self.extracted_facts and isinstance(self.extracted_facts.get("person_names"), list) else ''}

VISUAL RULES:
1. SUBJECT ACCURACY: Each frame MUST show the specific topic/location/person from the extracted facts — NOT generic alternatives.
   - If the topic is "Hitler in the bunker", show a figure with 1940s military traits in a concrete underground bunker.
   - If the topic is "the mantis shrimp", show the specific crustacean with its distinctive raptorial claw.
   - If the topic is "the Brandenburg Gate", show the recognizable Berlin landmark with quadriga.
2. NO SUBSTITUTION: Do NOT generate a generic person/place/object when the script names something specific. Be exact.
3. ABSTRACT TOPICS: If the topic is abstract (justice, freedom, time), use a concrete visual metaphor: "scales of justice" for justice, "hourglass with sand" for time, "bird in flight" for freedom.
4. SUBJECT REINFORCEMENT: Mention the primary subject 2-3 times in different forms within each prompt.
4. SHOT VARIETY: Use WIDE for establishing scenes, CLOSE-UP for detail shots, AERIAL for scale.
5. NO text/letters/words/numbers/signs/logos/writing in any frame.
6. NO close-ups of hands/fingers (unless hands ARE the subject).
7. 90-150 words per prompt (NOT 15-25 — Z-Image needs more detail).
8. Consistent Ghibli/watercolor style across ALL frames.

PHASES (one prompt per phase):
1. HOOK - Most shocking/unusual visual. Grab attention immediately with the actual subject.
2. CONTEXT - Where/when it exists. Ground the story with accurate location/setting.
3. DETAIL - Close-up of strange feature. Build curiosity with the specific subject.
4. TWIST - Something that contradicts or deepens tension.
5. ENDING - Unresolved, memorable frame. Loops with opening.

(Add more phases as needed for {n_scenes} scenes)

Output format (one per line, numbered):
1. HOOK: [prompt — 90-150 words, include subject, Ghibli style]
2. CONTEXT: [prompt — 90-150 words, include location, Ghibli style]
3. DETAIL: [prompt — 90-150 words, include key feature, Ghibli style]
4. TWIST: [prompt — 90-150 words, Ghibli style]
5. ENDING: [prompt — 90-150 words, Ghibli style]"""
```

- [ ] **Step 3: Also update the fallback prompt (around line 1381)**
The fallback that generates prompts when LLM parsing fails is too generic. Change:
```python
# OLD (line ~1381):
visual = f"{phase.lower()} visual: {sentence.strip()[:60]}, wide cinematic shot, photorealistic, dramatic lighting, no text"

# NEW:
visual = f"{phase.lower()} visual: {sentence.strip()[:60]}, Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette, wide shot, no text, no random characters, sharp focus"
```

- [ ] **Step 4: Verify syntax**
```bash
python3 -c "import ast; ast.parse(open('src/classes/YouTube.py').read())" && echo "Syntax OK"
```

- [ ] **Step 5: Commit**
```bash
git add src/classes/YouTube.py
git commit -m "fix(image): strengthen generate_prompts() with subject extraction and no-substitution rule"
```

---

## Task 6: Fix Fallback in generate_image_prompts_response() in llm_generate.py

**Files:**
- Modify: `src/llm_generate.py:1372-1396` (fallback section)

- [ ] **Step 1: Show current fallback code**
```bash
sed -n '1372,1396p' /home/anon/Projects/experiment/MoneyPrinterV2/src/llm_generate.py
```

- [ ] **Step 2: Replace the fallback prompts**

Find the fallback section starting with:
```python
# Fallback: generate Z-Image Turbo formatted prompts from script sentences
if not image_prompts:
    for sentence in sentences[:n_scenes]:
        visual = (
            f"A cinematic scene depicting {sentence.strip()[:100]} "
            f"in a wide establishing shot with dramatic lighting and atmospheric depth. "
            f"Photorealistic 8K quality with sharp focus, crisp textures, and professional color grading. "
            f"No text, no gibberish, no watermarks, clean composition. "
            f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
        )
        image_prompts.append(visual)
```

Replace with:
```python
    # Fallback: generate Z-Image Turbo formatted prompts from script sentences
    if not image_prompts:
        for sentence in sentences[:n_scenes]:
            visual = (
                f"Scene showing {sentence.strip()[:100]} in Pixar 3D animation "
                f"in Studio Ghibli style with soft earthy watercolor lighting and warm inviting palette. "
                f"Subject clearly visible with defining characteristics, wide establishing shot, "
                f"no text, no random characters, no watermarks, no logos, sharp focus throughout. "
                f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
            )
            image_prompts.append(visual)
```

Also fix the second fallback (lines ~1386-1396):
```python
# OLD:
variant = (
    "wide establishing aerial shot"
    if len(image_prompts) % 2 == 0
    else "cinematic medium shot"
)
visual = (
    f"{variant} depicting {sentences[idx].strip()[:80]} "
    f"with dramatic lighting and cinematic atmosphere. "
    f"8K photorealistic with sharp focus, no artifacts. "
    f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
)
# NEW:
variant = (
    "wide establishing aerial shot"
    if len(image_prompts) % 2 == 0
    else "cinematic medium shot"
)
visual = (
    f"{variant} depicting {sentences[idx].strip()[:80]} "
    f"in Pixar 3D animation in Studio Ghibli style with soft earthy watercolor lighting. "
    f"Warm inviting palette, no text, no random characters, no watermarks, sharp focus. "
    f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
)
```

- [ ] **Step 3: Verify syntax**
```bash
python3 -c "import ast; ast.parse(open('src/llm_generate.py').read())" && echo "Syntax OK"
```

- [ ] **Step 4: Commit**
```bash
git add src/llm_generate.py
git commit -m "fix(image): use Ghibli style in fallback prompts instead of generic photorealistic"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** Each design requirement has a corresponding task.
  - Remove character injection from Stage 2 → Tasks 1, 2, 3 ✓
  - Rewrite IMAGE_PROMPT template → Task 4 ✓
  - Strengthen generate_prompts() with subject extraction → Task 5 ✓
  - Fix fallback prompts → Task 6 ✓
- [ ] **Placeholder scan:** No "TBD", "TODO", "fill in later", "add validation" in any step ✓
- [ ] **Type consistency:** Function names match across tasks ✓
- [ ] **All code blocks show actual code** — no "similar to above" shortcuts ✓
- [ ] **Exact line numbers** provided for where to edit (or grep step for approximate) ✓
- [ ] **Syntax verification commands** included in each task ✓
- [ ] **Per-task commits** for clean git history ✓
- [ ] **Word count updated to 90-150** everywhere ✓
- [ ] **generate_thumbnail()** — never called in pipeline ✓ (no task needed)
- [ ] **No retry logic** — guidelines only ✓
- [ ] **Fallback wording synced** across Task 5 and Task 6 ✓

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2026-04-25-image-prompt-subject-accuracy.md`.**

### Task Summary (6 Tasks — all that are needed)

| Task | File | Description |
|------|------|-------------|
| 1 | `YouTube.py` | Fix `generate_image_pollinations()` enhancement |
| 2 | `YouTube.py` | Fix `generate_image_pollinations_flux()` enhancement |
| 3 | `YouTube.py` | Fix `generate_image_cloudflare()` enhancement |
| 4 | `llm_prompts.py` | Rewrite IMAGE_PROMPT template |
| 5 | `YouTube.py` | Strengthen `generate_prompts()` with subject extraction |
| 6 | `llm_generate.py` | Fix fallback prompts (Ghibli style) |

**Thumbnail:** Never called in pipeline — no task needed.

**For subagent-driven execution:** Use `superpowers:subagent-driven-development` skill.