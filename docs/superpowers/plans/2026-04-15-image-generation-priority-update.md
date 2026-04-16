# Image Generation Priority Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder image generation priority in YouTube.py from Cloudflare-first to Pollinations-first with proper fallbacks.

**Architecture:** Modify `generate_image()` method to try Pollinations providers first (zimage then flux), then fallback to Cloudflare as backup. This keeps all existing provider implementations unchanged.

**Tech Stack:** Python (YouTube.py), existing image provider methods

---

## Current State

### Current Priority (lines 1475-1508)
```python
def generate_image(self, prompt: str, delay_between: int = 2) -> str:
    # 1. Try Cloudflare Image API FIRST
    result = self.generate_image_cloudflare(prompt)
    # 2. Try Pollinations zimage
    result = self.generate_image_pollinations(prompt)
    # 3. Fallback to Pollinations flux
    result = self.generate_image_pollinations_flux(prompt)
```

### Existing Provider Methods
| Method | Lines | Provider | Model | Cost |
|--------|-------|----------|-------|------|
| `generate_image_pollinations()` | 1240-1294 | Pollinations.ai | zimage | 0.002 pts/image |
| `generate_image_pollinations_flux()` | 1296-1348 | Pollinations.ai | flux | 0.001 pts/image |
| `generate_image_cloudflare()` | 1350-1473 | Cloudflare Workers AI | phoenix/schnell/klein/dev/sdxl | Free (100k/day) |

---

## Files

- Modify: `src/classes/YouTube.py:1475-1508` (the `generate_image` method)

---

### Task 1: Update Image Generation Priority

**Files:**
- Modify: `src/classes/YouTube.py:1475-1508`

- [ ] **Step 1: Update generate_image() method priority order**

Replace the entire `generate_image()` method (lines 1475-1508):

```python
def generate_image(self, prompt: str, delay_between: int = 2) -> str:
    """
    Generates an AI Image based on the given prompt.
    Priority: Pollinations zimage -> Pollinations flux -> Cloudflare
    """
    # 1. Try Pollinations zimage FIRST (primary)
    if get_verbose():
        info("Trying Pollinations zimage...")
    result = self.generate_image_pollinations(prompt)
    if result is not None:
        time.sleep(delay_between)
        return result

    # 2. Fallback to Pollinations flux (if zimage unavailable/failed)
    if get_verbose():
        info("zimage failed. Trying Pollinations flux...")
    result = self.generate_image_pollinations_flux(prompt)
    if result is not None:
        time.sleep(delay_between)
        return result

    # 3. Final fallback to Cloudflare (if Pollinations exhausted)
    if get_verbose():
        info("Pollinations exhausted. Trying Cloudflare...")
    result = self.generate_image_cloudflare(prompt)
    if result is not None:
        time.sleep(delay_between)
        return result

    # All failed - show proper warning
    warning(
        "ALL IMAGE GENERATION METHODS FAILED. No image generated for this prompt."
    )
    return None
```

- [ ] **Step 2: Run preflight to verify no syntax errors**

Run: `python3 scripts/preflight_local.py`

Expected: PASS (no import/syntax errors)

- [ ] **Step 3: Commit the change**

```bash
git add src/classes/YouTube.py
git commit -m "refactor: reorder image generation priority to Pollinations-first"
```

---

## Summary

| Step | Action | Risk |
|------|--------|------|
| 1 | Update `generate_image()` method priority | LOW - only reorders existing methods |
| 2 | Run preflight | LOW - verifies syntax |
| 3 | Commit | LOW - version control |

**Verification:** After change, image generation should attempt Pollinations providers before Cloudflare, matching desired priority chain.