# Opus Enhancement Plan - COMPLETED

## Issues Fixed

1. **Web UI auto-upload broken** — `auto_upload` silently dropped (not in `GenerateRequest`)
2. **Thumbnail generation missing** — need thumbnail + 1st frame as hook image
3. **Database schema messy** — `videos.account` is TEXT not FK, no proper relations, cache vs DB writes
4. **Workflow streamlining** — ensure clean pipeline without removing necessary parts

---

## What Was Implemented

### 1. Auto-Upload Fix

**Files changed:**
- `api/models.py` — added `auto_upload: bool = False` to `GenerateRequest`
- `api/jobs.py` — added `auto_upload: bool = False` field to `Job` dataclass; updated `JobManager.create()` to pass it through
- `api/routers/generate.py` — passes `auto_upload=req.auto_upload` to `job_manager.create()`
- `api/pipeline_worker.py` — after thumbnail step, if `job.auto_upload` is True, calls `youtube.upload_video()`, stores `upload_url` on job, calls `update_video_youtube_url(video_id, url)` with the actual DB row ID

### 2. Thumbnail + First Frame Generation

**Files changed:**
- `src/classes/YouTube.py` — added `generate_thumbnail()` method (~line 1533):
  - Generates AI thumbnail image via Pollinations/Flux/Cloudflare (same flow as video images)
  - Creates hook frame: title text overlay on first video image (PIL, 1280x720, white text with shadow)
  - Stores paths in `self.thumbnail_path` and `self.hook_frame_path`
- `api/pipeline_worker.py` — added thumbnail step: `youtube.generate_thumbnail()` called after combine, paths stored in result dict

### 3. Database Schema Cleanup

**Files changed:**
- `src/db.py`:
  - `videos` table: added `account_id INTEGER FK REFERENCES accounts(id)` (nullable for backwards compat)
  - `topics.topic`: added UNIQUE constraint
  - `add_video()`: accepts `account_id` param; resolves account_id from account username if not provided; writes `account_id` to DB; returns the new video row ID
  - `update_video_youtube_url(video_id, url)`: updates `youtube_url` column for a video
  - `get_account_by_username()`: helper to look up account ID by username
  - `account_oauth_links`: now populated when adding OAuth credentials

### 4. Workflow Streamlining

**Pipeline flow (new):**
```
(topic) → (script) → (metadata) → (image_prompts) → (images) → (tts) → (combine) → (thumbnail) → (upload)
```
- Added `thumbnail` step in STEPS list
- Added `upload` step in STEPS list
- `add_video()` called BEFORE auto-upload (so we have a DB row ID to update with youtube_url)
- Video ID returned from `add_video()` used for `update_video_youtube_url()`
- YouTube class `add_video()` now writes to DB instead of `.mp/youtube_cache.json`

### 5. Additional Fixes

- `api/pipeline_worker.py`: Null checks on `youtube.script` and `youtube.metadata` before accessing
- `src/classes/YouTube.py`: `add_video()` now calls `db.add_video()` instead of writing to cache JSON

---

## Branch
- `opus-enhancement` — all changes on this branch

## Status
- [x] Database cleanup
- [x] Job/model updates
- [x] Pipeline worker fixes
- [x] YouTube class fixes (DB writes, thumbnail)
- [x] Auto-upload integration
- [x] Code review fixes applied
- [x] All code compiles
- [x] Preflight passes