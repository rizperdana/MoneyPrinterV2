# Thumbnail LLM Prompt Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded thumbnail generation with LLM-generated custom prompts that create engaging, clickbait-style vertical thumbnails for YouTube Shorts.

**Architecture:** Add LLM function for thumbnail prompt generation, new job type for model routing, update thumbnail generation to use LLM-generated prompts instead of fixed template.

**Tech Stack:** Python, OpenAI-compatible LLM API, Pollinations AI image generation, PIL for image processing.

---

## Task 1: Add thumbnail_prompt job type to llm_provider.py

**Files:**
- Modify: `src/llm_provider.py:208-239` (MODEL_ROUTING dict)
- Modify: `src/llm_provider.py:200-206` (JOBS dict)

- [ ] **Step 1: Add thumbnail_prompt to JOBS dict**

```python
JOBS = {
    "topic": "Topic Generation", 
    "script": "Script Writing",
    "seo_tags": "SEO Tags",
    "image_prompts": "Image Prompts", 
    "title_desc": "Title/Description",
    "thumbnail_prompt": "Thumbnail Prompt Generation",
}
```

- [ ] **Step 2: Add thumbnail_prompt routing in MODEL_ROUTING**

```python
MODEL_ROUTING = {
    # ... existing jobs ...
    "thumbnail_prompt": [
        "kilo-auto/free",
        "qwen/qwen3-next-80b-a3b-instruct:free", 
        "bytedance-seed/dola-seed-2.0-pro:free",
        "arcee-ai/trinity-large-thinking:free",
    ],
}
```

- [ ] **Step 3: Run test to verify routing works**

Run: `python3 -c "from llm_provider import get_model_for_job; print(get_model_for_job('thumbnail_prompt'))"`
Expected: kilo-auto/free or first available model

## Task 2: Add generate_thumbnail_prompt function to llm_generate.py

**Files:**
- Modify: `src/llm_generate.py` (add new function after existing functions)

- [ ] **Step 1: Add import for thumbnail_prompt job**

Add to imports: `from llm_provider import generate_text, get_model_for_job`

- [ ] **Step 2: Add generate_thumbnail_prompt function**

```python
def generate_thumbnail_prompt_response(subject: str, script: str, title: str) -> str:
    """
    Generate engaging thumbnail prompt from video content.
    
    Args:
        subject (str): Video topic/subject
        script (str): Full video script text
        title (str): Video title
        
    Returns:
        str: Custom thumbnail prompt optimized for clickbait vertical format
    """
    prompt = f"""Create a compelling thumbnail prompt for this YouTube Short:

TITLE: {title}
SUBJECT: {subject}
SCRIPT: {script[:500]}...

⚠️ REQUIREMENTS:
- Vertical 9:16 format (1080x1920)
- Clickbait/attention-grabbing style
- Mysterious, intriguing atmosphere
- High contrast, vibrant colors
- Cinematic lighting
- Must hook viewers to click
- NO TEXT in the image (text added later via overlay)

⚠️ VISUAL STYLE:
- Epic, dramatic composition
- Mysterious atmosphere that matches the video's mystery tone
- Bold, striking visuals that stop scrolling
- Professional, high-quality look

Generate ONE detailed prompt (50-100 words) that captures the essence of this video in a visually striking way.

Return ONLY the prompt text, no quotes or labels."""

    return generate_response(prompt, job="thumbnail_prompt")
```

- [ ] **Step 3: Test function import**

Run: `python3 -c "from llm_generate import generate_thumbnail_prompt_response; print('Import successful')"`
Expected: Import successful

## Task 3: Update generate_thumbnail in YouTube.py

**Files:**
- Modify: `src/classes/YouTube.py:1718-1786` (generate_thumbnail method)

- [ ] **Step 1: Add import for new LLM function**

Add to imports: `from llm_generate import generate_thumbnail_prompt_response`

- [ ] **Step 2: Replace hardcoded prompt generation with LLM call**

Replace lines 1728-1730:
```python
# OLD: Hardcoded prompt
title = self.metadata.get("title", self.subject) if hasattr(self, "metadata") and self.metadata else (self.subject or "")
thumbnail_prompt = f"Epic clickbait thumbnail for: {title} - mysterious atmosphere, high contrast, cinematic lighting, vibrant colors, must grab attention, no text"

# NEW: LLM-generated prompt
title = self.metadata.get("title", self.subject) if hasattr(self, "metadata") and self.metadata else (self.subject or "")
script = getattr(self, 'script', '')  # Get script if available
if script:
    thumbnail_prompt = generate_thumbnail_prompt_response(self.subject, script, title)
else:
    # Fallback if no script available
    thumbnail_prompt = f"Epic clickbait thumbnail for: {title} - mysterious atmosphere, high contrast, cinematic lighting, vibrant colors, must grab attention, no text"
```

- [ ] **Step 3: Add verbose logging for new prompt**

Add after prompt generation:
```python
if get_verbose():
    info(f" => Thumbnail prompt: {thumbnail_prompt[:100]}...")
```

- [ ] **Step 4: Verify hook_frame creation unchanged**

Ensure the hook_frame creation (lines 1740-1786) remains exactly the same - only the thumbnail_prompt changes.

## Task 4: Test end-to-end thumbnail generation

**Files:**
- Test: Manual testing via `src/main.py` or direct script

- [ ] **Step 1: Create test script to verify thumbnail generation**

Create `test_thumbnail.py`:
```python
#!/usr/bin/env python3
"""Test thumbnail LLM prompt generation"""

from classes.YouTube import YouTube
from config import get_verbose

# Test data
test_title = "Scientists Found Something Impossible in the Ocean"
test_subject = "deep sea mysteries"
test_script = "Did you know there's a place in the ocean deeper than Mount Everest is tall? Scientists recently discovered something impossible down there..."

def test_thumbnail_prompt():
    # Create YouTube instance
    yt = YouTube("test_uuid", "test_nickname", None, "ocean mysteries", "en")
    yt.subject = test_subject
    yt.script = test_script
    yt.metadata = {"title": test_title}
    
    # Generate thumbnail
    yt.generate_thumbnail()
    
    # Check results
    if hasattr(yt, 'thumbnail_path') and yt.thumbnail_path:
        print(f"✅ Thumbnail generated: {yt.thumbnail_path}")
        return True
    else:
        print("❌ Thumbnail generation failed")
        return False

if __name__ == "__main__":
    test_thumbnail_prompt()
```

- [ ] **Step 2: Run test script**

Run: `python3 test_thumbnail.py`
Expected: Thumbnail generated successfully with LLM prompt

- [ ] **Step 3: Verify LLM prompt quality**

Check that generated prompt is more specific and engaging than the old hardcoded one.

- [ ] **Step 4: Clean up test file**

Run: `rm test_thumbnail.py`

## Task 5: Sample LLM prompt for documentation

**Files:**
- Create: `docs/superpowers/plans/2026-04-22-thumbnail-llm-prompts-plan.md` (this file)

- [ ] **Step 1: Add sample prompt to plan**

Add this sample LLM prompt that would generate engaging thumbnail prompts:

**Sample LLM Prompt for Thumbnail Generation:**
```
Create a compelling thumbnail prompt for this YouTube Short:

TITLE: Scientists Found Something Impossible in the Ocean
SUBJECT: deep sea mysteries  
SCRIPT: Did you know there's a place in the ocean deeper than Mount Everest is tall? Scientists recently discovered something impossible down there...

⚠️ REQUIREMENTS:
- Vertical 9:16 format (1080x1920)
- Clickbait/attention-grabbing style
- Mysterious, intriguing atmosphere
- High contrast, vibrant colors
- Cinematic lighting
- Must hook viewers to click
- NO TEXT in the image (text added later via overlay)

⚠️ VISUAL STYLE:
- Epic, dramatic composition
- Mysterious atmosphere that matches the video's mystery tone
- Bold, striking visuals that stop scrolling
- Professional, high-quality look

Generate ONE detailed prompt (50-100 words) that captures the essence of this video in a visually striking way.

Return ONLY the prompt text, no quotes or labels.
```

**Expected LLM Output:**
"A mysterious deep-sea scene showing bioluminescent creatures around an ancient sunken temple, with dramatic lighting casting eerie shadows on strange underwater artifacts, creating an atmosphere of impossible discovery and hidden secrets in the ocean depths."

- [ ] **Step 2: Commit final plan**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && git add docs/superpowers/plans/2026-04-22-thumbnail-llm-prompts-plan.md && git commit -m "docs: add thumbnail LLM prompts implementation plan"`