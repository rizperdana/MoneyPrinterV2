# Upload Progress Visibility — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make YouTube OAuth upload show visible progress in web UI and structured logs. Remove dead TUI code.

**Architecture:** Create a Job for video uploads, emit WebSocket events (`upload_progress`, `upload_complete`, `upload_error`) from `_do_upload_video()` via the existing `job.events` queue. Add structured logging + progress callback to `youtubeApiUpload()`.

**Tech Stack:** Python asyncio, FastAPI BackgroundTasks, existing `api/jobs.py` JobManager, existing WebSocket infrastructure.

---

## File Map

| File | Change |
|------|--------|
| `api/jobs.py` | Add `upload_type` field to Job dataclass (optional) |
| `api/routers/upload.py` | Create job, pass job.events, emit upload events |
| `src/youtube_api.py` | Add progress_callback param, structured logging, chunk progress |
| `src/tui/` | DELETE entire directory (TUI removal) |
| `web/src/lib/api.ts` | Update response type to include `job_id` |

---

### Task 1: Add progress callback to `youtubeApiUpload()`

**Files:** Modify: `src/youtube_api.py`

- [ ] **Step 1: Read current youtube_api.py upload function**

Read the entire `youtubeApiUpload()` function. Identify:
- Where initialization happens (POST to YouTube)
- Where file upload happens (PUT to upload URL, chunked)
- Where metadata patching happens
- Where response parsing happens

- [ ] **Step 2: Add progress_callback parameter**

Add near the top of `youtubeApiUpload()` function signature:
```python
from typing import Callable, Optional

def youtubeApiUpload(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    oauth_token: str = None,
    account_id: str = None,
    privacy: str = "public",
    for_kids: bool = False,
    thumbnail_path: str = None,
    progress_callback: Optional[Callable[[str, str, float], None]] = None,
) -> dict:
```

- [ ] **Step 3: Add structured logging setup**

At top of function (after `logger = logging.getLogger(__name__)`):
```python
import json

def _log(event: str, **kwargs):
    logger.info(json.dumps({"event": event, **kwargs}))
```

- [ ] **Step 4: Emit init phase**

After token validation (~line 113):
```python
if progress_callback:
    progress_callback("initializing", "Starting upload...", 5.0)
_log("youtube_upload", phase="init", title=title, video_id=account_id)
```

- [ ] **Step 5: Emit chunk upload progress**

Find the chunk upload loop (likely using `requests.put` with chunked file reading). Replace with a version that reads chunks and calls callback:

```python
# After opening file, before upload loop:
file_size = os.path.getsize(video_path)
chunk_size = 10 * 1024 * 1024  # 10MB chunks

# Inside / after each chunk sent:
bytes_sent = offset
progress_pct = 5.0 + (bytes_sent / file_size) * 90.0  # 5-95%
if progress_callback:
    progress_callback("uploading", f"Uploading... {int(progress_pct)}%", progress_pct)
_log("youtube_upload", phase="uploading", progress=round(progress_pct, 1), bytes_sent=bytes_sent, total_bytes=file_size)
```

- [ ] **Step 6: Emit metadata phase**

Before the metadata PATCH request:
```python
if progress_callback:
    progress_callback("metadata", "Setting title, description, tags...", 97.0)
_log("youtube_upload", phase="metadata", title=title)
```

- [ ] **Step 7: Emit complete phase**

On successful upload (after video ID returned):
```python
if progress_callback:
    progress_callback("complete", "Upload complete!", 100.0)
_log("youtube_upload", phase="complete", video_id=result.get("video_id"), url=result.get("url"))
```

- [ ] **Step 8: Emit error phase**

In each except block, before the exception:
```python
if progress_callback:
    progress_callback("error", str(e), 0)
_log("youtube_upload", phase="error", error=str(e))
```

- [ ] **Step 9: Run preflight to verify no import errors**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from src.youtube_api import youtubeApiUpload; print('OK')"
```

Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add src/youtube_api.py && git commit -m "feat(upload): add progress callback and structured logging"
```

---

### Task 2: Wire WebSocket events in upload endpoint

**Files:** Modify: `api/routers/upload.py`

- [ ] **Step 1: Create Job for video-based upload**

In `upload_video_by_id()` endpoint, before `bg.add_task()`:

```python
from api.jobs import job_manager, JobStatus

# Create a job for this upload so we have job.events for WebSocket streaming
upload_job = job_manager.create(
    account=account.get("id", "unknown"),
    niche="",
    language="",
)
upload_job.status = JobStatus.running

# Emit initial progress
upload_job.events.put_nowait({
    "type": "upload_progress",
    "step": "initializing",
    "status": "Starting upload...",
    "progress": 5,
})
```

- [ ] **Step 2: Return job_id in response**

Modify the return statement:
```python
return {
    "status": "uploading",
    "video_id": video_id,
    "platform": platform,
    "account": account.get("id"),
    "job_id": upload_job.id,
}
```

- [ ] **Step 3: Pass job.events to _do_upload_video**

Update the `bg.add_task` call:
```python
bg.add_task(_do_upload_video, file_path, video, account, platform, oauth_token, upload_job)
```

- [ ] **Step 4: Update _do_upload_video signature**

```python
async def _do_upload_video(
    file_path: str,
    video: dict,
    account: dict,
    platform: str = "youtube",
    oauth_token: str = None,
    job=None,
):
```

- [ ] **Step 5: Create progress callback that emits to job.events**

In `_do_upload_video()`, inside `_sync_upload()` before the upload code:

```python
def _emit(step, status_msg, progress):
    """Emit upload progress event to WebSocket via thread-safe bridge."""
    import asyncio
    event = {"type": "upload_progress", "step": step, "status": status_msg, "progress": progress}
    if job:
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(job.events.put_nowait, event)
        except RuntimeError:
            pass  # No event loop in this thread

progress_callback = _emit
```

- [ ] **Step 6: Pass progress_callback to youtubeApiUpload**

```python
result = youtubeApiUpload(
    video_path=file_path,
    title=video.get("title", "Untitled"),
    description=video.get("description", ""),
    tags=video.get("tags", "").split(",") if video.get("tags") else [],
    oauth_token=oauth_token,
    progress_callback=progress_callback,
)
```

- [ ] **Step 7: Emit completion event**

After successful upload (after logging line):
```python
if job:
    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(job.events.put_nowait, {
            "type": "upload_complete",
            "url": result.get("url", ""),
            "video_id": result.get("video_id", ""),
        })
        # Mark job done
        job.status = JobStatus.done
        job.upload_url = result.get("url", "")
    except RuntimeError:
        pass
```

- [ ] **Step 8: Emit error event**

In the except block, after `logging.error`:
```python
if job:
    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(job.events.put_nowait, {
            "type": "upload_error",
            "error": str(e),
        })
        job.status = JobStatus.failed
        job.error = str(e)
    except RuntimeError:
        pass
```

- [ ] **Step 9: Test imports**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && python3 -c "from api.routers.upload import upload_video_by_id, _do_upload_video; print('OK')"
```

Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add api/routers/upload.py && git commit -m "feat(upload): emit WebSocket events for upload progress"
```

---

### Task 3: Update frontend API type

**Files:** Modify: `web/src/lib/api.ts`

- [ ] **Step 1: Read api.ts uploadByVideoId function**

Find `uploadByVideoId` in `web/src/lib/api.ts`.

- [ ] **Step 2: Update response type**

Change the response type to include `job_id`:
```typescript
uploadByVideoId: (videoId: number, platform: string, accountId?: string) =>
  fetch(`/api/videos/${videoId}/upload?platform=${platform}${accountId ? `&account_name=${accountId}` : ''}`).then(r =>
    json<{ status: string; video_id: number; platform: string; account: string; job_id: string }>(r)
  ),
```

- [ ] **Step 3: Commit**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2/web && git add src/lib/api.ts && git commit -m "feat(api): add job_id to uploadByVideoId response"
```

---

### Task 4: Connect frontend to job WebSocket

**Files:** Modify: `web/src/pages/Videos.tsx`

- [ ] **Step 1: Read current Videos.tsx upload handling**

Find where `uploadByVideoId` is called and how the WebSocket is opened.

- [ ] **Step 2: Extract job_id from response and connect to WebSocket**

Currently the code likely opens a WebSocket without knowing the job_id. Update the upload handler:

```typescript
// After uploadByVideoId call succeeds:
const uploadResponse = await uploadByVideoId(video.id, "youtube", selectedAccountId);
if (uploadResponse.job_id) {
  setJobId(uploadResponse.job_id);
  connectToJob(uploadResponse.job_id);
}
```

The existing `useJobSocket` hook or WebSocket connection code should already handle `upload_progress`, `upload_complete`, `upload_error` events. The key change is that now the frontend HAS the `job_id` from the upload response.

- [ ] **Step 3: Commit**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2/web && git add src/pages/Videos.tsx && git commit -m "feat(ui): connect upload dialog to job WebSocket for progress"
```

---

### Task 5: Remove TUI

**Files:** DELETE: `src/tui/` (entire directory)

- [ ] **Step 1: Verify no imports of tui outside src/tui**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && rg "from src.tui|import.*tui" --type py | grep -v "src/tui/"
```

Expected: no results (except worktree refs if any)

- [ ] **Step 2: Delete src/tui directory**

```bash
rm -rf /home/anon/Projects/experiment/MoneyPrinterV2/src/tui
```

- [ ] **Step 3: Verify main.py still imports**

```bash
python3 -c "from src.main import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: remove TUI (web UI only)"
```

---

### Task 6: End-to-end test

**Files:** Run manual test

- [ ] **Step 1: Start server**

```bash
cd /home/anon/Projects/experiment/MoneyPrinterV2 && source venv/bin/activate && python3 src/main.py serve
```

- [ ] **Step 2: Upload a video via web UI**

Open http://127.0.0.1:8000, go to Videos page, click upload on a video.

- [ ] **Step 3: Verify progress updates**

Watch the progress bar move from 5% → uploading → metadata → complete. The spinner should disappear and the YouTube URL should appear.

- [ ] **Step 4: Check structured logs**

```bash
grep "youtube_upload" /home/anon/Projects/experiment/MoneyPrinterV2/logs/*.log
```

Or check stdout for JSON log lines.

- [ ] **Step 5: Report results**
