# Implementation Plan: Accounts, Niche Management & 24/7 Topic Rotation

**Date:** 2026-04-20
**Status:** Ready for Execution

---

## Part A: DB & Backend Foundation

### Task 1: DB — Add `topics` column to accounts, `youtube_url` to videos, new functions

**Files:** `src/db.py`

**Steps:**

1. In `init_db()`, after the `oauth_token` migration block (~line 58), add:

```python
# Migration: Add topics column to accounts if not exists
try:
    cursor.execute("SELECT topics FROM accounts LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE accounts ADD COLUMN topics TEXT DEFAULT '[]'")

# Migration: Add youtube_url column to videos if not exists
try:
    cursor.execute("SELECT youtube_url FROM videos LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE videos ADD COLUMN youtube_url TEXT")
```

2. Add `update_video_youtube_url()` function after `get_video_by_id()` (~line 180):

```python
def update_video_youtube_url(video_id: int, youtube_url: str) -> bool:
    """
    Update the youtube_url field for a video record.

    Args:
        video_id: The video database ID
        youtube_url: The YouTube video URL

    Returns:
        True if updated, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE videos SET youtube_url = ? WHERE id = ?",
        (youtube_url, video_id)
    )
    conn.commit()
    return cursor.rowcount > 0
```

3. Add `list_accounts_with_topics()` function after `get_accounts()` (~line 240):

```python
def list_accounts_with_topics() -> list[dict]:
    """
    Get all accounts with their topics array.
    Reads topics from cache JSON files and merges with DB.

    Returns:
        List of account dicts with topics field (list or string)
    """
    import json
    import os

    result = []

    # Read from .mp/youtube.json
    yt_path = os.path.join(ROOT_DIR, ".mp", "youtube.json")
    if os.path.exists(yt_path):
        with open(yt_path, "r") as f:
            yt_data = json.load(f)
            for acc in yt_data.get("accounts", []):
                result.append({
                    "id": acc.get("id", ""),
                    "platform": "youtube",
                    "username": acc.get("id", ""),
                    "nickname": acc.get("nickname", ""),
                    "profile_path": acc.get("firefox_profile", ""),
                    "topics": acc.get("topics", []),
                    "niche": acc.get("niche", ""),
                    "language": acc.get("language", "English"),
                })

    # Read from .mp/twitter.json
    tw_path = os.path.join(ROOT_DIR, ".mp", "twitter.json")
    if os.path.exists(tw_path):
        with open(tw_path, "r") as f:
            tw_data = json.load(f)
            for acc in tw_data.get("accounts", []):
                result.append({
                    "id": acc.get("id", ""),
                    "platform": "twitter",
                    "username": acc.get("id", ""),
                    "nickname": acc.get("nickname", ""),
                    "profile_path": acc.get("firefox_profile", ""),
                    "topics": acc.get("topics", []),
                    "niche": acc.get("niche", ""),
                    "language": acc.get("language", "English"),
                })

    # Merge with DB accounts (skip duplicates by username+platform)
    db_accounts = get_accounts()
    for acc in db_accounts:
        if not any(a["username"] == acc["username"] and a["platform"] == acc["platform"] for a in result):
            result.append({
                **acc,
                "topics": acc.get("topics", []),
            })

    return result
```

4. Update `update_account()` to support `topics` field — modify the `valid_fields` set (~line 248):

```python
valid_fields = {"platform", "username", "nickname", "profile_path", "topics"}
```

5. Test: `cd /home/anon/Projects/experiment/MoneyPrinterV2 && python -c "from src.db import init_db, update_video_youtube_url, list_accounts_with_topics; init_db(); print('OK')"`

---

### Task 2: Accounts API — Add topics to GET/PUT endpoints

**Files:** `api/routers/accounts.py`

**Steps:**

1. Modify `GET /api/accounts` endpoint (~line 18) — add `topics` and `niche` fields to each account dict:

In the YouTube accounts block (~line 28), change:
```python
result.append(
    {
        "id": account_id,
        "platform": "youtube",
        "username": account_id,
        "nickname": acc.get("nickname", ""),
        "profile_path": acc.get("firefox_profile", ""),
        "oauth_status": oauth_status,
        "oauth_updated": oauth_updated,
    }
)
```
to:
```python
result.append(
    {
        "id": account_id,
        "platform": "youtube",
        "username": account_id,
        "nickname": acc.get("nickname", ""),
        "profile_path": acc.get("firefox_profile", ""),
        "niche": acc.get("niche", ""),
        "topics": acc.get("topics", []),
        "language": acc.get("language", "English"),
        "oauth_status": oauth_status,
        "oauth_updated": oauth_updated,
    }
)
```

Do the same for Twitter accounts block (~line 48).

2. Modify `PUT /api/accounts/{account_id}` endpoint (~line 120) — update `AccountUpdate` model in `api/models.py` to include `topics`:

Add to `AccountUpdate` class:
```python
topics: list[str] | None = None
niche: str | None = None
language: str | None = None
```

3. Verify GET/PUT: `curl http://127.0.0.1:8000/api/accounts` — each account should show `topics` and `niche` fields.

---

### Task 3: Upload — Persist YouTube URL to DB

**Files:** `api/routers/upload.py`

**Steps:**

1. In `_do_upload_video()` function, after successful upload result is available (line ~140):

Find where `result.get("url")` is available after the `youtubeApiUpload` call succeeds. After the block:
```python
if result:
    logging.info(f"API upload successful: {result.get('url')}")
return result
```

Add `video_id` to the result dict so the caller can persist it. The `video_id` is the `video["id"]` parameter passed to `_do_upload_video`. After the result is obtained (around line ~145), add:

```python
# Persist YouTube URL to database
from src.db import update_video_youtube_url
if video_id and result and result.get("url"):
    update_video_youtube_url(video_id, result["url"])
```

2. Test import: `python -c "from api.routers.upload import router; print('OK')"`

---

## Part B: Frontend — Accounts Page

### Task 4: Modify `web/src/pages/Accounts.tsx` — Add niche/topics editor

**Files:** `web/src/pages/Accounts.tsx` (already exists — modify it)

**Steps:**

1. Add `topics` and `niche` columns to the accounts table header (~line 127):

In `<TableHeader>` row, add after `<TableHead>Nickname</TableHead>`:
```tsx
<TableHead>Niche</TableHead>
<TableHead>Topics</TableHead>
```

2. Add `video_count` (count videos per account) and display cells (~line 140):

In each `<TableRow>`, after the nickname cell, add:
```tsx
<TableCell className="text-muted-foreground text-xs max-w-32 truncate">
  {a.niche || "—"}
</TableCell>
<TableCell>
  {a.topics && Array.isArray(a.topics) && a.topics.length > 0 ? (
    <div className="flex flex-wrap gap-1">
      {a.topics.slice(0, 3).map((t: string, i: number) => (
        <span key={i} className="inline-block px-1.5 py-0.5 rounded bg-muted text-xs">
          {t}
        </span>
      ))}
      {a.topics.length > 3 && (
        <span className="text-xs text-muted-foreground">+{a.topics.length - 3}</span>
      )}
    </div>
  ) : (
    <span className="text-muted-foreground text-xs">—</span>
  )}
</TableCell>
```

3. Change the `Edit` dropdown menu item to open an edit dialog:

Add state for the edit dialog after existing state (~line 20):
```tsx
const [editAccount, setEditAccount] = useState<AccountData | null>(null)
const [editTopics, setEditTopics] = useState<string>("")
const [editNiche, setEditNiche] = useState<string>("")
```

Add edit dialog component after the Add Account Dialog (~before line 230):
```tsx
{/* Edit Account Dialog */}
<Dialog open={!!editAccount} onOpenChange={(open) => !open && setEditAccount(null)}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Edit Account: {editAccount?.nickname || editAccount?.username}</DialogTitle>
    </DialogHeader>
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Niche</Label>
        <Input
          value={editNiche}
          onChange={(e) => setEditNiche(e.target.value)}
          placeholder="e.g., cool animal and plant fact"
        />
      </div>
      <div className="space-y-2">
        <Label>Topics (JSON array, one of the 10 dark niches)</Label>
        <textarea
          className="w-full h-32 px-3 py-2 rounded-md border border-input bg-background text-sm font-mono"
          value={editTopics}
          onChange={(e) => setEditTopics(e.target.value)}
          placeholder='["unsolved mysteries & internet rabbit holes", "deep sea anomalies & thalassophobia"]'
        />
        <p className="text-xs text-muted-foreground">
          Available topics: unsolved mysteries & internet rabbit holes, deep sea anomalies & thalassophobia, glitches in the matrix & mandela effects, cosmic horror & space anomalies, dark psychology & behavioral facts, abandoned mega-projects & ghost towns, forbidden places you can't visit, survival facts & what to do if, mythology & ancient curses, dystopian tech & futurism
        </p>
      </div>
    </div>
    <DialogFooter>
      <Button variant="outline" onClick={() => setEditAccount(null)}>Cancel</Button>
      <Button onClick={async () => {
        if (!editAccount) return
        let topics = editTopics
        try { topics = JSON.parse(editTopics) } catch {}
        await api.accounts.update(editAccount.id, { niche: editNiche, topics })
        setEditAccount(null)
        load()
      }}>
        Save
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

4. Change the `Edit` dropdown item to trigger the edit dialog (~line 205):

Change:
```tsx
<DropdownMenuItem disabled>Edit</DropdownMenuItem>
```
to:
```tsx
<DropdownMenuItem onClick={() => {
  setEditNiche(a.niche || "")
  setEditTopics(a.topics && Array.isArray(a.topics) ? JSON.stringify(a.topics, null, 2) : "[]")
  setEditAccount(a)
}}>
  Edit
</DropdownMenuItem>
```

5. Add the `api.accounts.update()` method to `web/src/lib/api.ts`:

Find the `accounts` object in `api.ts` and add `update` method:
```typescript
update: (id: string, data: { niche?: string; topics?: string[] }) =>
  fetch(`/api/accounts/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then(r => r.json()),
```

6. Verify: load `/accounts` page — table should show niche, topics tags, Edit should open dialog with pre-filled topics JSON.

---

### Task 5: Wire Accounts in sidebar navigation

**Files:** `web/src/App.tsx`, `web/src/components/Sidebar.tsx`

**Status:** Already done. Route `/accounts` exists in App.tsx line 23. NavLink exists in Sidebar.tsx line 17 (`{ label: "Accounts", path: "/accounts", icon: Users }`). No changes needed.

---

## Part C: Frontend — Videos Table

### Task 6: Add youtube_url column + inline progress to Videos table

**Files:** `web/src/pages/Videos.tsx`

**Steps:**

1. In the video card inside the `.map()` (around line 137), add a `youtube_url` status badge after the platform line:

Find:
```tsx
<p className="text-sm text-muted-foreground">
  Niche: {video.niche || "?"} | Platform: {video.platform} | Lang: {video.language || "?"}
</p>
```

Replace with:
```tsx
<p className="text-sm text-muted-foreground">
  Niche: {video.niche || "?"} | Platform: {video.platform} | Lang: {video.language || "?"}
  {video.youtube_url && (
    <span className="ml-2">
      <a href={video.youtube_url} target="_blank" rel="noopener noreferrer" className="text-green-600 underline text-xs">
        YouTube ↗
      </a>
    </span>
  )}
</p>
```

2. For the upload button (line 156): keep existing `handleUpload(video)` flow — it already shows the progress dialog. The only change is that after upload completes, `video.youtube_url` will be set in the database, so on page refresh the link will appear.

3. To show inline upload status without requiring a modal: modify the button section of each video card to show a status indicator:

Find (line 152-165):
```tsx
<Button
  variant="outline"
  size="sm"
  onClick={() => handleUpload(video)}
>
  <Upload className="w-4 h-4 mr-1" />
  Upload
</Button>
```

Replace with:
```tsx
{video.youtube_url ? (
  <span className="inline-flex items-center gap-1 text-green-600 text-xs">
    <Check className="w-3 h-3" />
    Uploaded
  </span>
) : (
  <Button
    variant="outline"
    size="sm"
    onClick={() => handleUpload(video)}
  >
    <Upload className="w-4 h-4 mr-1" />
    Upload
  </Button>
)}
```

Add `Check` to the import from `lucide-react` (line 4).

4. After successful upload in `handleConfirmUpload()`, refresh the videos list so the YouTube link appears:

In the `ws.onmessage` handler for `upload_complete` event (~line 80), add after setting `setUploadResult`:
```tsx
// Refresh videos to show youtube_url
api.videos().then(d => setVideos(d.videos || [])).catch(() => {})
```

5. Verify: upload a video, after completion the video card should show "Uploaded" badge with green check instead of Upload button. The YouTube URL link should appear next to the platform info.

---

## Part D: 24/7 Script

### Task 7: Create `scripts/run_24h.py`

**Files:** Create `scripts/run_24h.py`

**Steps:**

1. Read `src/run_pipeline.py` to understand `run_pipeline()` signature (already done — see above). Key: `run_pipeline(niche=str, language=str, upload=bool, headless=bool)` returns dict with keys: `topic`, `title`, `description`, `video_path`, `uploaded`, `error`, and optionally `youtube_url` after successful upload.

2. Create the script:

```python
#!/usr/bin/env python3
"""
scripts/run_24h.py
24/7 round-robin video generator + uploader.

Usage:
    python scripts/run_24h.py

Environment:
    CLIPROXY_API_KEY, GEMINI_API_KEY, FIREFOX_PROFILE_PATH

State:
    ~/.mp/24h_state.json tracks (account_index, topic_index) per run.
"""

import os
import sys
import json
import time
import logging
import random
from datetime import datetime
from pathlib import Path

# Add project root and src to path
_project_root = Path(__file__).parent.parent.resolve()
_src_dir = _project_root / "src"
for _p in [str(_project_root), str(_src_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

from config import ROOT_DIR, get_firefox_profile_path
from status import info, success, error
from run_pipeline import run_pipeline
from db import update_video_youtube_url, add_video

# State file
STATE_FILE = Path.home() / ".mp" / "24h_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Suggested dark niche topics (from spec)
DARK_NICHES = [
    "unsolved mysteries & internet rabbit holes",
    "deep sea anomalies & thalassophobia",
    "glitches in the matrix & mandela effects",
    "cosmic horror & space anomalies",
    "dark psychology & behavioral facts",
    "abandoned mega-projects & ghost towns",
    "forbidden places you can't visit",
    "survival facts & what to do if",
    "mythology & ancient curses",
    "dystopian tech & futurism",
]

# Logging setup
LOG_DIR = _project_root / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging() -> logging.Logger:
    log_file = LOG_DIR / f"run_24h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("run_24h")
    return logger


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "index": 0,
        "last_run": None,
    }


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_accounts() -> list[dict]:
    """Load accounts from .mp/youtube.json."""
    yt_path = _project_root / ".mp" / "youtube.json"
    if not yt_path.exists():
        raise FileNotFoundError(f"Account config not found: {yt_path}")

    with open(yt_path, "r") as f:
        data = json.load(f)

    accounts = data.get("accounts", [])
    if not accounts:
        raise ValueError("No accounts found in .mp/youtube.json")

    return accounts


def build_pairs(accounts: list[dict]) -> list[tuple[dict, str]]:
    """Build (account, topic) pairs. Topics from account or fallback to dark niches."""
    pairs = []
    for acc in accounts:
        topics = acc.get("topics")
        if not topics:
            niche = acc.get("niche", "")
            topics = [niche] if niche else DARK_NICHES
        for t in topics:
            pairs.append((acc, t))
    return pairs


def run_account_topic(acc: dict, topic: str, logger: logging.Logger) -> dict:
    """Run pipeline for one account + topic. Persist result to DB."""
    logger.info(f"Account: {acc.get('nickname')} | Topic: {topic}")

    result = run_pipeline(
        niche=topic,
        language=acc.get("language", "English"),
        upload=True,
        headless=True,
    )

    youtube_url = result.get("youtube_url")

    # Persist video to DB if we have a file_path
    video_path = result.get("video_path")
    video_id = None
    if video_path:
        try:
            video_id = add_video(
                topic=result.get("topic", topic),
                title=result.get("title", "Untitled"),
                platform="youtube",
                file_path=video_path,
                niche=topic,
                description=result.get("description", ""),
                tags=",".join(result.get("tags", [])) if result.get("tags") else None,
                account=acc.get("id"),
                language=acc.get("language", "English"),
            )
            logger.info(f"Saved video to DB: id={video_id}")
        except Exception as e:
            logger.error(f"Failed to save video to DB: {e}")

    # Persist YouTube URL
    if video_id and youtube_url:
        update_video_youtube_url(video_id, youtube_url)
        logger.info(f"Persisted youtube_url: {youtube_url}")

    status = "ok" if result.get("uploaded") else "failed"
    logger.info(f"Result: {status} | URL: {youtube_url or 'N/A'}")

    return result


def main():
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("24/7 Runner starting")

    try:
        accounts = load_accounts()
    except FileNotFoundError as e:
        logger.error(e)
        print(f"Error: {e}")
        return

    pairs = build_pairs(accounts)
    if not pairs:
        logger.error("No (account, topic) pairs built")
        return

    logger.info(f"Loaded {len(accounts)} accounts, {len(pairs)} pairs")

    state = load_state()
    index = state.get("index", 0) % len(pairs)

    acc, topic = pairs[index]
    state["last_run"] = datetime.now().isoformat()

    try:
        result = run_account_topic(acc, topic, logger)
        state["last_result"] = "ok" if result.get("uploaded") else "failed"
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        state["last_result"] = "error"

    state["index"] = (index + 1) % len(pairs)
    save_state(state)

    logger.info(f"Next index: {state['index']} | State saved to {STATE_FILE}")


if __name__ == "__main__":
    main()
```

3. Run once to verify: `python scripts/run_24h.py`. Expected: generates a video with the first account/pair, logs to `logs/run_24h_*.log`, state saved to `~/.mp/24h_state.json`.

---

### Task 8: Create shell wrapper + systemd timer

**Files:** Create `scripts/run_24h.sh`, `scripts/moneyprinter-24h.service`, `scripts/moneyprinter-24h.timer`

**Steps:**

1. Create `scripts/run_24h.sh`:

```bash
#!/bin/bash
# scripts/run_24h.sh
# Shell wrapper for the 24/7 runner.
# Run via: bash scripts/run_24h.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate venv if it exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

exec python scripts/run_24h.py >> logs/run_24h_stdout.log 2>&1
```

Make executable: `chmod +x scripts/run_24h.sh`

2. Create `scripts/moneyprinter-24h.service`:

```ini
[Unit]
Description=MoneyPrinterV2 24/7 Generator
After=network.target

[Service]
Type=oneshot
ExecStart=/home/anon/Projects/experiment/MoneyPrinterV2/scripts/run_24h.sh
WorkingDirectory=/home/anon/Projects/experiment/MoneyPrinterV2
User=anon
StandardOutput=append:/home/anon/Projects/experiment/MoneyPrinterV2/logs/run_24h_stdout.log
StandardError=append:/home/anon/Projects/experiment/MoneyPrinterV2/logs/run_24h_stderr.log

[Install]
WantedBy=multi-user.target
```

3. Create `scripts/moneyprinter-24h.timer`:

```ini
[Unit]
Description=MoneyPrinterV2 24/7 Periodic Runner (every 60 min)

[Timer]
OnBootSec=5min
OnUnitActiveSec=60min
Unit=moneyprinter-24h.service

[Install]
WantedBy=timers.target
```

4. Enable the timer:

```bash
# Copy service/timer to user systemd directory
mkdir -p ~/.config/systemd/user
cp scripts/moneyprinter-24h.service ~/.config/systemd/user/
cp scripts/moneyprinter-24h.timer ~/.config/systemd/user/

# Reload systemd, enable and start timer
systemctl --user daemon-reload
systemctl --user enable moneyprinter-24h.timer
systemctl --user start moneyprinter-24h.timer

# Check status
systemctl --user list-timers
```

---

## Task Checklist

| # | Task | File | Status |
|---|------|------|--------|
| 1 | DB migrations + functions | `src/db.py` | Pending |
| 2 | Accounts API topics | `api/routers/accounts.py`, `api/models.py` | Pending |
| 3 | Persist YouTube URL | `api/routers/upload.py` | Pending |
| 4 | Accounts page edit | `web/src/pages/Accounts.tsx`, `web/src/lib/api.ts` | Pending |
| 5 | Sidebar nav | — | Already done |
| 6 | Videos youtube_url | `web/src/pages/Videos.tsx` | Pending |
| 7 | 24h script | `scripts/run_24h.py` | Pending |
| 8 | Shell + systemd | `scripts/run_24h.sh`, `scripts/moneyprinter-24h.service`, `scripts/moneyprinter-24h.timer` | Pending |

---

## Function Name Cross-Reference

All function names used consistently across tasks:

| Function | Defined In | Used In |
|----------|-----------|---------|
| `update_video_youtube_url(video_id, youtube_url)` | Task 1 | Task 3 |
| `list_accounts_with_topics()` | Task 1 | (available for future use) |
| `add_video(...)` | `src/db.py` (existing) | Task 7 |
| `run_pipeline(niche, language, upload, headless)` | `src/run_pipeline.py` (existing) | Task 7 |
| `get_firefox_profile_path()` | `src/config.py` (existing) | Task 7 |
