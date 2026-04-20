# Upload Progress Visibility — Design Spec

## Goal

Replace blind upload with visible progress in web UI and structured logging. Remove dead TUI code.

## Problem

After clicking "Upload" in the web UI:
- Progress dialog shows spinner + "Starting upload..." + 0% forever
- Backend runs upload silently in background thread
- No WebSocket events emitted to frontend
- Errors only visible in FastAPI stdout logs

Frontend expects `upload_progress`, `upload_complete`, `upload_error` events on WebSocket — backend never sends them.

## Architecture

**Approach**: Wire up existing WebSocket infrastructure + add structured logging.

### Event Flow

```
youtubeApiUpload() [youtube_api.py]
  → calls internal _upload_with_progress() with callback
  → callback → logger.info() (structured log)
  → callback → job.events.put_nowait() [via loop.call_soon_threadsafe]
    → WebSocket /ws/jobs/{job_id}
      → Videos.tsx handles upload_progress/upload_complete/upload_error
```

### Upload Phases (quantifiable)

| Phase      | Step label      | Duration  | Trackable |
| ---------- | --------------- | -------- | --------- |
| Init       | `initializing`  | ~200ms   | Fast, show 5% |
| Chunking   | `uploading`     | Variable | bytes_sent / total_bytes (1-95%) |
| Metadata   | `metadata`      | ~200ms   | Fast, show 98% |
| Complete   | `complete`      | —        | Show 100% |

### Event Schema

```typescript
// Progress
{ type: "upload_progress", step: string, status: string, progress: number }

// Complete
{ type: "upload_complete", url: string, video_id: string }

// Error
{ type: "upload_error", error: string }
```

### Logging Format

JSON structured logs from `youtube_api.py`:

```json
{"level": "INFO", "event": "youtube_upload", "phase": "init", "video_id": "xxx", "detail": "Initializing upload..."}
{"level": "INFO", "event": "youtube_upload", "phase": "uploading", "progress": 45.2, "bytes_sent": 45123456, "total_bytes": 99876543}
{"level": "INFO", "event": "youtube_upload", "phase": "metadata", "detail": "Setting video metadata..."}
{"level": "INFO", "event": "youtube_upload", "phase": "complete", "video_id": "drcMqQEzepA", "url": "https://www.youtube.com/watch?v=drcMqQEzepA"}
{"level": "ERROR", "event": "youtube_upload", "phase": "error", "error": "401 Unauthorized"}
```

## Components

### 1. `src/youtube_api.py` — progress callback + logging

- Add `progress_callback` param to `youtubeApiUpload()`
- Callback signature: `Callable[[str, str, float], None]` → `(step, status, progress)`
- Internal upload loop calls callback with progress updates
- Log every phase at INFO level with structured JSON

### 2. `api/routers/upload.py` — emit WebSocket events

- `_do_upload_video()` already runs in `bg.add_task()` (sync thread)
- Pass a callback that emits to `job.events` via `asyncio.get_event_loop().call_soon_threadsafe()`
- Handle errors and emit `upload_error`
- Handle completion and emit `upload_complete`

### 3. `src/status.py` — remove TUI

- Delete file entirely
- Check all imports across codebase
- Replace with lightweight `src/logger.py` for structured logging if needed

### 4. Frontend (`Videos.tsx`) — already has handlers

- Already has `upload_progress`, `upload_complete`, `upload_error` handlers
- Already has progress bar, step labels, spinner
- No frontend changes needed if events arrive correctly

### 5. Progress bar UX

- Map step → label via `STEP_LABELS` in Videos.tsx (already exists)
- Map `progress` float → percentage for progress bar
- Update status text with current phase

## TUI Removal

Delete:
- `src/status.py` — `error()`, `success()`, `info()`, `warning()`, `question()` helpers
- Find all imports of `status` across `src/` and `api/`
- Replace with `logging.getLogger(__name__).info()` etc.

## Testing

1. Upload a short test video via frontend — verify progress bar moves
2. Check server logs — verify JSON structured logs appear
3. Verify WebSocket events arrive in browser devtools
4. Verify error path emits `upload_error` with message

## Constraints

- Backend runs in sync thread via `bg.add_task()` — use thread-safe event emission
- Progress bar in frontend shows 0-100% based on `progress` field
- No new dependencies — use existing `logging`, `asyncio`, `requests`
- Keep upload reliability — don't break the actual upload flow
