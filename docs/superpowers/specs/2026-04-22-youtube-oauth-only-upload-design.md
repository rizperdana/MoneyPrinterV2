# YouTube OAuth-Only Upload — Remove All Selenium Browser Usage

**Date:** 2026-04-22
**Status:** Draft
**Owner:** MoneyPrinterV2

## Context

YouTube uploads currently use two methods:
1. **OAuth API** (`youtubeApiUpload` in `src/youtube_api.py`) — correct, browser-less
2. **Selenium browser** (`YouTube.upload_video()` in `src/classes/YouTube.py`) — fragile, breaks when YouTube UI changes

The auto-upload feature in the UI pipeline (`api/pipeline_worker.py`) incorrectly calls Selenium-based `youtube.upload_video()` instead of `youtubeApiUpload()` with OAuth. This causes the `[aria-label="Create"]` selector failure reported by the user.

**Goal:** Remove all Selenium-based YouTube upload paths. All YouTube uploads must go through OAuth API.

---

## Current State

### Upload Paths (Callers of `YouTube.upload_video()`)

| File | Line | Context | OAuth? |
|------|------|---------|--------|
| `api/pipeline_worker.py` | 247 | `youtube.upload_video()` | ❌ No — **BUG** |
| `api/routers/upload.py` | 58 | `_do_upload()` — `/upload/{job_id}` endpoint | ❌ No |
| `src/main.py` | 106 | CLI `upload` command | ❌ No |
| `src/batch_run.py` | 90 | Batch upload | ❌ No |
| `src/cron.py` | 150 | Cron upload | ❌ No |

### Reference: Correct OAuth Implementation

`api/routers/upload.py` lines 76-293 (`POST /videos/{video_id}/upload`) uses OAuth correctly:
```python
# Get OAuth credentials (lines 144-166)
oauth_token = ...
# Call API upload (lines 225-233)
youtubeApiUpload(video_path=file_path, oauth_token=oauth_token, ...)
```

`src/run_pipeline.py` lines 172-197 also uses OAuth correctly.

---

## Files to Change

### 1. `api/pipeline_worker.py` (line 247)

**Change:** Replace `youtube.upload_video()` with OAuth API call.

**Current (line 243-252):**
```python
if job.auto_upload:
    on_progress("upload", "running")
    success, url = youtube.upload_video()  # ← SELENIUM — BUG
    if success and url:
        job.upload_url = url
        upload_url = url
        update_video_youtube_url(video_id, url)
    on_progress("upload", "done", detail=url if success else "failed")
```

**New:** Get OAuth credentials → call `youtubeApiUpload()` with progress callback.

**Gap to fill:** `pipeline_worker.py` doesn't currently get OAuth credentials. Must add same credential-fetching logic used in `api/routers/upload.py` lines 144-166:
```python
from src.db import get_linked_oauth_ids, get_oauth_credentials_by_ids, get_oauth_credentials
oauth_ids = get_linked_oauth_ids(job.account)
oauth_creds = get_oauth_credentials_by_ids(oauth_ids)
oauth_creds = [c for c in oauth_creds if c["platform"] == "youtube"]
oauth_token = oauth_creds[0]["token"] if oauth_creds else None
```

**Error handling:** If no OAuth token, emit error event with message "No OAuth token — please link YouTube account".

### 2. `api/routers/upload.py` — Remove Old Endpoint

**Change:** Delete `POST /upload/{job_id}` endpoint (lines 21-74) and `_do_upload()` function (lines 37-73).

**Rationale:**
- It uses Selenium-based `yt.upload_video()`
- It's redundant — `POST /videos/{video_id}/upload` covers the same use case with OAuth
- It doesn't support OAuth tokens, so it can't be fixed without a rewrite

**Dependency:** Check if any frontend code calls `/upload/{job_id}`. If so, redirect to use `/videos/{video_id}/upload` instead.

### 3. `src/main.py` (line 106)

**Change:** CLI upload command should use OAuth.

**Current:**
```python
success_flag, result = yt.upload_video()
```

**New:** Get OAuth token → call `youtubeApiUpload()`.

**Gap:** CLI doesn't have `account_id` concept in the same way. Default to `"default"` account or add `--account` flag.

### 4. `src/batch_run.py` (line 90)

**Change:** Use OAuth upload instead of Selenium.

**Current:**
```python
yt_success, yt_url = youtube.upload_video()
```

**New:** Get OAuth token from account → call `youtubeApiUpload()`.

### 5. `src/cron.py` (line 150)

**Change:** Use OAuth upload instead of Selenium.

**Current:**
```python
upload_success, upload_result = youtube.upload_video(upload_id=upload_id)
```

**New:** OAuth-based upload with same pattern.

### 6. `src/classes/YouTube.py`

**Change:** Mark `upload_video()` as deprecated or redirect to OAuth internally.

**Options:**
- **Option A:** Keep `upload_video()` as-is but add a deprecation warning — it still serves as fallback for non-OAuth scenarios (e.g., if user truly wants browser-based for some reason)
- **Option B:** Have `upload_video()` automatically use OAuth internally if credentials available, fall back to Selenium only if explicitly requested with a flag

**Recommendation:** Option B — refactor `upload_video()` to:
```python
def upload_video(self, use_oauth_fallback=True, upload_id=None):
    """Upload video - prefers OAuth, falls back to browser if use_oauth_fallback=False."""
    if use_oauth_fallback:
        oauth_token = get_access_token(self._account_nickname)
        if oauth_token:
            return self._upload_via_oauth(oauth_token)  # New internal method
    # Browser fallback (existing code)
    ...
```

This preserves backward compatibility for any external callers while fixing the internal flows.

### 7. `api/routers/upload.py` — Fix OAuth Token Refresh in `_do_upload_video`

**Gap:** In `youtubeApiUpload()` (youtube_api.py line 84-89), token refresh is handled but if refresh fails, the upload fails without a useful message. Ensure `_do_upload_video` catches auth errors and surfaces actionable guidance.

---

## Edge Cases & Gaps

### 1. Missing OAuth Credentials
- **When:** User toggles auto-upload but has no OAuth token stored
- **Handling:** Emit error event with message "No OAuth token found. Please link your YouTube account in Settings." Don't fail silently.
- **UI:** Frontend should disable auto-upload toggle if no OAuth credentials available.

### 2. Expired OAuth Token (Auto-Refresh)
- **When:** Token expires during upload
- **Handling:** `youtubeApiUpload()` already calls `get_access_token()` which refreshes if needed (youtube_api.py lines 84-89). If refresh fails, raise exception with clear message.
- **Verify:** Ensure `get_access_token()` in `youtube_oauth.py` properly refreshes tokens.

### 3. Upload Failures (API Errors)
- **When:** Quota exceeded, network error, API rejection
- **Handling:** `youtubeApiUpload()` returns error dict or raises exception. Pipeline worker catches exceptions and emits error events.
- **Gap:** Error messages may not be user-friendly. Improve error messages in `youtube_api.py` `_handle_api_error()` for common cases (quota, token expired, not verified).

### 4. TikTok Upload
- **Current:** TikTok uses Selenium in `upload_to_tiktok()` — no OAuth implementation
- **Scope:** Out of scope for this fix (user asked about YouTube only)
- **Future:** TikTok OAuth upload would need separate implementation

### 5. Facebook Upload
- **Current:** Facebook uses Selenium in `upload_to_facebook()` — no OAuth implementation
- **Scope:** Out of scope for this fix
- **Future:** Facebook OAuth upload would need separate implementation

### 6. `get_channel_id()` and `get_videos()` in YouTube.py
- These use Selenium to scrape YouTube Studio
- Not related to upload, but use browser
- **Decision:** Leave as-is for now — user asked to remove Selenium from upload only

### 7. `src/cron.py` — Multiple Accounts
- Cron may process videos for different accounts
- Need to ensure `get_access_token()` accepts account identifier
- Verify `youtube_oauth.py` `get_access_token()` can handle multiple account names

### 8. Browser Profile Path
- `YouTube.__init__` takes `fp_profile_path` — needed for Selenium-based methods
- OAuth upload doesn't need browser profile
- When using OAuth, we shouldn't require Firefox profile to be configured
- **Fix:** `api/pipeline_worker.py` should not fail if `fp_profile` is missing when using OAuth upload

---

## Success Criteria

1. Auto-upload from UI pipeline uses `youtubeApiUpload()` with OAuth — no Selenium involved
2. All YouTube upload paths (`main.py`, `batch_run.py`, `cron.py`) use OAuth
3. `/upload/{job_id}` endpoint removed (redundant Selenium path)
4. Clear error messages when OAuth credentials missing/expired
5. No regression — videos still upload successfully via OAuth API
6. Firefox browser still needed for non-upload tasks (channel ID, video listing) — those remain unchanged

---

## Rollback Plan

If OAuth upload fails catastrophically:
1. Revert `api/pipeline_worker.py` to call `youtube.upload_video()` (Selenium)
2. Keep `/upload/{job_id}` endpoint until OAuth is proven stable
3. User can disable auto-upload and manually trigger via `/videos/{video_id}/upload`

---

## Testing Checklist

1. **Auto-upload via UI pipeline** — generates video, auto-uploads via OAuth API
2. **Manual upload via UI** — `/videos/{video_id}/upload` with OAuth
3. **CLI upload** — `python src/main.py --upload ...` uses OAuth
4. **Batch upload** — all videos upload via OAuth
5. **Expired token** — upload fails with clear error, not silent skip
6. **Missing token** — error message guides user to link account
7. **No Firefox profile** — OAuth uploads work without any browser profile configured
