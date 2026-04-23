# YouTube OAuth-Only Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all Selenium browser usage from YouTube uploads. All uploads go through `youtubeApiUpload()` with OAuth tokens.

**Architecture:** Replace all `YouTube.upload_video()` calls (Selenium-based) with `youtubeApiUpload()` calls (OAuth API). The `upload_video()` method in `YouTube` class will be refactored to internally use OAuth or remain as browser fallback with a deprecation path.

**Tech Stack:** Python, `src/youtube_api.py` (OAuth API), `src/youtube_oauth.py` (token mgmt), `src/db.py` (OAuth credentials)

---

## File Changes Overview

| File | Action | Purpose |
|------|--------|---------|
| `api/pipeline_worker.py` | Modify | Fix auto_upload to use OAuth |
| `api/routers/upload.py` | Modify | Remove old `/upload/{job_id}` Selenium endpoint |
| `src/main.py` | Modify | CLI upload uses OAuth |
| `src/batch_run.py` | Modify | Batch upload uses OAuth |
| `src/cron.py` | Modify | Cron upload uses OAuth |
| `src/classes/YouTube.py` | Modify | Deprecate `upload_video()` or add OAuth path |
| `src/youtube_oauth.py` | Read | `get_access_token()` for token refresh |
| `src/db.py` | Read | OAuth credential functions |

---

## Task 1: Fix `api/pipeline_worker.py` — Auto-Upload Uses OAuth

**Files:**
- Modify: `api/pipeline_worker.py:243-252`
- Read: `api/routers/upload.py:144-166` (OAuth credential fetching pattern)

- [ ] **Step 1: Read current auto_upload section**

Read `api/pipeline_worker.py` lines 240-260 to see exact context around line 247.

- [ ] **Step 2: Add OAuth credential imports**

Add near the imports at top of `_run_sync()` function (after line 105):
```python
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload
```

- [ ] **Step 3: Replace `youtube.upload_video()` with OAuth call**

Replace lines 243-252:
```python
# OLD (Selenium-based — BUG):
if job.auto_upload:
    on_progress("upload", "running")
    success, url = youtube.upload_video()
    if success and url:
        job.upload_url = url
        upload_url = url
        update_video_youtube_url(video_id, url)
    on_progress("upload", "done", detail=url if success else "failed")
```

With:
```python
# NEW (OAuth API):
if job.auto_upload:
    on_progress("upload", "running")
    try:
        oauth_token = get_access_token(job.account or "default")
        if not oauth_token:
            on_progress("upload", "done", detail="No OAuth token — link YouTube account")
            on_progress("upload", "error", error="No OAuth token — please link your YouTube account in Settings")
        else:
            upload_result = youtubeApiUpload(
                video_path=youtube.video_path,
                title=metadata.get("title", "Untitled") if metadata else "Untitled",
                description=metadata.get("description", "") if metadata else "",
                tags=tags_list if tags_list else [],
                oauth_token=oauth_token,
                account_id=job.account or "default",
                progress_callback=lambda step, status, pct: on_progress("upload", step, detail=status) if step != "uploading" else None,
            )
            if upload_result and upload_result.get("url"):
                url = upload_result["url"]
                job.upload_url = url
                upload_url = url
                update_video_youtube_url(video_id, url)
                on_progress("upload", "done", detail=url)
            else:
                on_progress("upload", "done", detail="Upload failed")
    except Exception as e:
        on_progress("upload", "done", detail=f"Error: {str(e)}")
        on_progress("upload", "error", error=str(e))
```

Note: `metadata` and `tags_list` are already defined earlier in `_run_sync()` (lines 148-241). Verify they're in scope.

- [ ] **Step 4: Verify `metadata` and `tags_list` are in scope**

Check that `metadata` (line 218) and `tags_list` (lines 219-223) are accessible at line 243. They are — they're defined before the auto_upload block in `_run_sync()`.

- [ ] **Step 5: Test import**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from api.pipeline_worker import _run_sync; print('import OK')"`
Expected: `import OK`

- [ ] **Step 6: Commit**

```bash
git add api/pipeline_worker.py
git commit -m "fix(pipeline): auto_upload uses OAuth API instead of Selenium"
```

---

## Task 2: Remove Old `/upload/{job_id}` Endpoint (Selenium-Based)

**Files:**
- Modify: `api/routers/upload.py:21-74`
- Check: Any frontend code calling `/upload/{job_id}`

- [ ] **Step 1: Search for callers of `/upload/{job_id}`**

Run: `grep -r "upload/{job_id}\|/upload/" --include="*.py" --include="*.tsx" --include="*.ts" --include="*.js" | grep -v "videos/{video_id}/upload"`
Expected: Should show only the endpoint definition itself

- [ ] **Step 2: Also check API client calls**

Run: `grep -r "upload.*job_id\|job_id.*upload" --include="*.py" --include="*.tsx" --include="*.ts" -n api/ web/src/`
Expected: Check if any frontend calls the old endpoint

- [ ] **Step 3: Remove `_do_upload()` function and old endpoint**

Delete from `api/routers/upload.py`:
- Lines 21-34: `@router.post("/upload/{job_id}")` endpoint
- Lines 37-73: `async def _do_upload(job):` function

Keep everything else (the OAuth-based `upload_video_by_id` and `_do_upload_video` remain intact).

- [ ] **Step 4: Verify file still imports correctly**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from api.routers.upload import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add api/routers/upload.py
git commit -m "chore(upload): remove old Selenium-based /upload/{job_id} endpoint"
```

---

## Task 3: Fix `src/main.py` — CLI Upload Uses OAuth

**Files:**
- Modify: `src/main.py:95-115`
- Read: `src/run_pipeline.py:172-197` (reference OAuth pattern)

- [ ] **Step 1: Read current CLI upload section**

Read `src/main.py` lines 95-120 to see exact context.

- [ ] **Step 2: Add OAuth imports**

Add after line 12 (or near existing imports):
```python
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload
```

- [ ] **Step 3: Replace `yt.upload_video()` with OAuth call**

Find the block around line 106 that does `success_flag, result = yt.upload_video()`. Replace with:
```python
oauth_token = get_access_token("default")
if not oauth_token:
    click.echo("Error: No OAuth token. Link YouTube account first.")
    return
try:
    upload_result = youtubeApiUpload(
        video_path=os.path.abspath(filepath),
        title="Untitled",  # CLI doesn't have metadata, using default
        description="",
        tags=[],
        oauth_token=oauth_token,
        account_id="default",
        progress_callback=None,
    )
    if upload_result and upload_result.get("url"):
        success_flag = True
        result = upload_result["url"]
    else:
        success_flag = False
        result = "Upload returned no URL"
except Exception as e:
    success_flag = False
    result = str(e)
```

- [ ] **Step 4: Test import**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from src.main import cli; print('import OK')"`
Expected: `import OK`

- [ ] **Step 5: Commit**

```bash
git add src/main.py
git commit -m "fix(cli): upload command uses OAuth API instead of Selenium"
```

---

## Task 4: Fix `src/batch_run.py` — Batch Upload Uses OAuth

**Files:**
- Modify: `src/batch_run.py:80-95`
- Read: `src/run_pipeline.py:172-197` (reference)

- [ ] **Step 1: Read batch_run upload section**

Read `src/batch_run.py` lines 80-100.

- [ ] **Step 2: Add OAuth imports**

Add after line 15:
```python
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload
```

- [ ] **Step 3: Replace `youtube.upload_video()` with OAuth call**

Replace around line 90:
```python
# OLD:
yt_success, yt_url = youtube.upload_video()
results["youtube"] = {"success": yt_success, "url": yt_url if yt_success else None}
print(f"YouTube: {yt_success} - {yt_url}")

# NEW:
oauth_token = get_access_token("default")
if not oauth_token:
    yt_success = False
    yt_url = "No OAuth token"
else:
    try:
        upload_result = youtubeApiUpload(
            video_path=youtube.video_path,
            title=result.get("title", "Untitled") if result else "Untitled",
            description=result.get("description", "") if result else "",
            tags=result.get("tags", []) if result else [],
            oauth_token=oauth_token,
            account_id="default",
            progress_callback=None,
        )
        yt_success = bool(upload_result and upload_result.get("url"))
        yt_url = upload_result.get("url", "") if upload_result else ""
    except Exception as e:
        yt_success = False
        yt_url = str(e)
results["youtube"] = {"success": yt_success, "url": yt_url}
print(f"YouTube: {yt_success} - {yt_url}")
```

- [ ] **Step 4: Test import**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from src.batch_run import process_video; print('import OK')"`
Expected: `import OK`

- [ ] **Step 5: Commit**

```bash
git add src/batch_run.py
git commit -m "fix(batch): upload uses OAuth API instead of Selenium"
```

---

## Task 5: Fix `src/cron.py` — Cron Upload Uses OAuth

**Files:**
- Modify: `src/cron.py:140-160`
- Read: `src/run_pipeline.py:172-197` (reference)

- [ ] **Step 1: Read cron upload section**

Read `src/cron.py` lines 140-165.

- [ ] **Step 2: Add OAuth imports**

Check existing imports at top of file. Add:
```python
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload
```

- [ ] **Step 3: Replace `youtube.upload_video()` with OAuth call**

Replace around line 150:
```python
# OLD:
upload_success, upload_result = youtube.upload_video(upload_id=upload_id)

# NEW:
oauth_token = get_access_token(youtube._account_nickname)
if not oauth_token:
    upload_success = False
    upload_result = "No OAuth token"
else:
    try:
        upload_api_result = youtubeApiUpload(
            video_path=youtube.video_path,
            title=result.get("title", "Untitled") if result else "Untitled",
            description=result.get("description", "") if result else "",
            tags=result.get("tags", []) if result else [],
            oauth_token=oauth_token,
            account_id=youtube._account_nickname,
            progress_callback=None,
        )
        upload_success = bool(upload_api_result and upload_api_result.get("url"))
        upload_result = upload_api_result.get("url", "") if upload_api_result else ""
    except Exception as e:
        upload_success = False
        upload_result = str(e)
```

Note: `youtube._account_nickname` is set earlier in cron.py (line 73).

- [ ] **Step 4: Test import**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from src.cron import upload_pending; print('import OK')"`
Expected: `import OK`

- [ ] **Step 5: Commit**

```bash
git add src/cron.py
git commit -m "fix(cron): upload uses OAuth API instead of Selenium"
```

---

## Task 6: Deprecate `YouTube.upload_video()` or Add OAuth Path

**Files:**
- Modify: `src/classes/YouTube.py:2574-2595`
- Read: `src/youtube_api.py:53-95` (youtubeApiUpload signature)

- [ ] **Step 1: Read upload_video method signature**

Read `src/classes/YouTube.py` lines 2574-2600 to see the method signature and docstring.

- [ ] **Step 2: Add internal OAuth helper method to YouTube class**

Add near the top of the `YouTube` class (after line ~175, near other helper methods):

```python
def _upload_via_oauth(self, oauth_token: str = None) -> tuple:
    """Upload video via OAuth API.

    Args:
        oauth_token: OAuth token. If None, gets from get_access_token().

    Returns:
        (success, result_or_url) tuple
    """
    from src.youtube_oauth import get_access_token
    from src.youtube_api import youtubeApiUpload

    if not oauth_token:
        oauth_token = get_access_token(self._account_nickname)

    if not oauth_token:
        return (False, "No OAuth token — please link YouTube account")

    try:
        result = youtubeApiUpload(
            video_path=self.video_path,
            title=self.metadata.get("title", "Untitled") if self.metadata else "Untitled",
            description=self.metadata.get("description", "") if self.metadata else "",
            tags=self.metadata.get("tags", []) if self.metadata else [],
            oauth_token=oauth_token,
            account_id=self._account_nickname,
            progress_callback=None,
        )
        if result and result.get("url"):
            self.uploaded_video_url = result["url"]
            return (True, result["url"])
        return (False, "Upload returned no URL")
    except Exception as e:
        return (False, str(e))
```

- [ ] **Step 3: Update upload_video() docstring to mark as deprecated**

Read current docstring at line 2575. Prepend deprecation notice:
```python
def upload_video(self, upload_id: int = None) -> tuple:
    """
    DEPRECATED: Use _upload_via_oauth() or youtubeApiUpload() directly.
    This method uses Selenium browser automation which breaks when YouTube UI changes.
    Uploads the video to YouTube using OAuth API.

    Args:
        upload_id (int, optional): Tracker upload ID for status updates.

    Returns:
        (success, result) (tuple[bool, str]): (True, youtube_url) on success,
                                               (False, error_message) on failure.
    """
```

- [ ] **Step 4: Add OAuth-first logic to upload_video()**

Replace the opening of `upload_video()` (lines 2585-2610) with:

```python
def upload_video(self, upload_id: int = None) -> tuple:
    """
    DEPRECATED: Use _upload_via_oauth() instead.
    ...
    """
    # Try OAuth first (preferred path)
    oauth_result = self._upload_via_oauth()
    if oauth_result[0]:  # Success
        return oauth_result

    # OAuth failed — log warning and fall back to browser
    import logging
    logging.warning(f"OAuth upload failed ({oauth_result[1]}), falling back to browser automation")
    warning(f"OAuth upload failed, using browser fallback: {oauth_result[1]}")

    # ... rest of existing Selenium code continues from line 2585 onwards
    # (the _ensure_browser() call and browser-based upload)
```

Note: This preserves full backward compatibility. If OAuth succeeds, browser is never launched. If OAuth fails, old Selenium path runs.

- [ ] **Step 5: Test imports**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from classes.YouTube import YouTube; print('import OK')"`
Expected: `import OK`

- [ ] **Step 6: Commit**

```bash
git add src/classes/YouTube.py
git commit -m "feat(YouTube): add _upload_via_oauth() and deprecate browser-based upload"
```

---

## Task 7: Verify All Changes — Integration Test

- [ ] **Step 1: Check all upload paths use OAuth**

Run: `grep -n "upload_video()\|youtubeApiUpload\|yt.upload_video" --include="*.py" src/ api/ scripts/`
Expected output should show:
- `youtubeApiUpload` calls in all upload paths
- `upload_video()` calls only in deprecated code path or for backward compat

- [ ] **Step 2: Run preflight check**

Run: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 scripts/preflight_local.py`
Expected: All checks pass (OAuth credentials, etc.)

- [ ] **Step 3: Check imports work correctly**

Run each:
```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && \
python3 -c "from api.pipeline_worker import _run_sync; print('pipeline_worker OK')" && \
python3 -c "from api.routers.upload import router; print('upload router OK')" && \
python3 -c "from src.main import cli; print('main OK')" && \
python3 -c "from src.batch_run import process_video; print('batch_run OK')" && \
python3 -c "from src.cron import upload_pending; print('cron OK')" && \
python3 -c "from src.classes.YouTube import YouTube; print('YouTube OK')"
```

- [ ] **Step 4: Final commit (if all tasks passed)**

```bash
git add -A && git commit -m "feat: remove Selenium from YouTube uploads — all use OAuth API

- pipeline_worker: auto_upload now uses youtubeApiUpload()
- Removed old /upload/{job_id} Selenium endpoint
- main.py: CLI upload uses OAuth
- batch_run.py: batch upload uses OAuth
- cron.py: cron upload uses OAuth
- YouTube.upload_video() deprecated, _upload_via_oauth() added"
```

---

## Spec Coverage Checklist

| Spec Requirement | Task |
|------------------|------|
| Auto-upload uses OAuth (not Selenium) | Task 1 |
| `/upload/{job_id}` endpoint removed | Task 2 |
| CLI upload uses OAuth | Task 3 |
| Batch upload uses OAuth | Task 4 |
| Cron upload uses OAuth | Task 5 |
| `upload_video()` deprecated with OAuth path | Task 6 |
| Clear error when OAuth missing | Tasks 1,3,4,5 |
| Token refresh handled | `youtubeApiUpload()` already handles (line 84-89) |
| Firefox profile not required for OAuth | Verified — OAuth doesn't use browser |
| TikTok/Facebook unchanged | Not touched (out of scope) |

---

## Rollback Plan

If OAuth upload fails in production:
1. Revert `api/pipeline_worker.py` — change back to `youtube.upload_video()`
2. Re-add `api/routers/upload.py` old endpoint from git
3. Revert `src/main.py`, `src/batch_run.py`, `src/cron.py`
4. Keep `YouTube.upload_video()` as active (remove deprecation)

```bash
# Rollback individual files
git checkout HEAD~1 -- api/pipeline_worker.py api/routers/upload.py src/main.py src/batch_run.py src/cron.py
```
