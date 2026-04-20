# Accounts, Niche Management & 24/7 Topic Rotation — Design Spec

**Date:** 2026-04-20
**Status:** Approved

---

## 1. Accounts Table (Frontend)

### Page: `web/src/pages/Accounts.tsx`

- Lists all accounts from `GET /api/accounts`
- Columns: username, nickname, platform, niche, topics (as tags), video count, OAuth status
- Action: Edit niche + topics per account via modal/drawer
- No OAuth linking UI — credentials already linked to account ID=1

### API Endpoints: `api/routers/accounts.py`

- `GET /api/accounts` — returns all accounts including `topics` JSON array
- `PUT /api/accounts/{account_id}` — updates niche and/or topics list

---

## 2. Niche/Topic Management

### Database Changes: `src/db.py`

**Accounts table migration:**
```sql
ALTER TABLE accounts ADD COLUMN topics TEXT DEFAULT '[]';
```
`topics` stored as JSON array of niche strings. Falls back to `niche` (single string) if `topics` is empty.

### Suggested Topic List (10 total)

1. "unsolved mysteries & internet rabbit holes"
2. "deep sea anomalies & thalassophobia"
3. "glitches in the matrix & mandela effects"
4. "cosmic horror & space anomalies"
5. "dark psychology & behavioral facts"
6. "abandoned mega-projects & ghost towns"
7. "forbidden places you can't visit"
8. "survival facts & what to do if"
9. "mythology & ancient curses"
10. "dystopian tech & futurism"

### Account Configuration

| Account | Existing niche | Topics |
|---------|---------------|--------|
| `awoogle organism` | "cool animal and plant fact" | keep existing |
| `awoogle millenia` | "creepy real historical event" | keep existing |
| (any account) | — | add any of the 10 topics above |

---

## 3. Persist YouTube URL to DB

### Database Changes: `src/db.py`

```sql
ALTER TABLE videos ADD COLUMN youtube_url TEXT;
```

### New Function: `update_video_youtube_url(video_id, youtube_url)`

```python
def update_video_youtube_url(video_id: int, youtube_url: str) -> bool:
    """Update the youtube_url field for a video record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE videos SET youtube_url = ? WHERE id = ?",
        (youtube_url, video_id)
    )
    conn.commit()
    return cursor.rowcount > 0
```

### Backend: `api/routers/upload.py`

In `_do_upload_video()`, after upload succeeds:
```python
from src.db import update_video_youtube_url
update_video_youtube_url(video_id, result["url"])
```

### Frontend: `web/src/pages/Videos.tsx`

Table columns — add `youtube_url` column:
- If set: clickable link to YouTube video
- If not set: "Upload" button (triggers upload flow inline, or status badge)

---

## 4. 24/7 Script with Topic Rotation

### New Script: `scripts/run_24h.py`

**Purpose:** Continuous round-robin generator across all accounts and topics.

**Algorithm:**
1. Load accounts from `.mp/youtube.json`
2. For each account, read its `topics` list; fallback to `niche` if empty
3. Round-robin across (account, topic) pairs
4. After all topics exhausted, reshuffle and repeat
5. Log everything to timestamped file: `logs/run_24h_YYYYMMDD_HHMMSS.log`

**Core loop:**
```python
import random, logging
from datetime import datetime
from src.run_pipeline import run_pipeline
from src.db import update_video_youtube_url

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def run_account_topic(account: dict, topic: str) -> dict:
    """Run pipeline for a single account + topic combination."""
    log_file = LOG_DIR / f"run_24h_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(filename=log_file, level=logging.INFO)

    info(f"Account: {account['nickname']} | Topic: {topic}")
    result = run_pipeline(
        niche=topic,
        language=account.get("language", "English"),
        upload=True,
        headless=True,
        account_id=account["id"]
    )

    if result.get("video_id") and result.get("youtube_url"):
        update_video_youtube_url(result["video_id"], result["youtube_url"])

    info(f"Result: {result.get('status', 'unknown')}")
    return result

def main():
    # Load accounts
    config_path = Path(".mp/youtube.json")
    with open(config_path) as f:
        data = json.load(f)

    accounts = data.get("accounts", [])

    # Build (account, topic) pairs
    pairs = []
    for acc in accounts:
        topics = acc.get("topics") or [acc.get("niche", "general")]
        for t in topics:
            pairs.append((acc, t))

    index = 0
    while True:
        acc, topic = pairs[index % len(pairs)]
        try:
            run_account_topic(acc, topic)
        except Exception as e:
            error(f"Error: {e}")
        index += 1
        time.sleep(60)  # configurable interval
```

**Usage:**
```bash
python scripts/run_24h.py
```

### Shell Wrapper: `scripts/run_24h.sh`

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
python scripts/run_24h.py >> logs/run_24h_stdout.log 2>&1
```

Run via systemd timer or cron.

---

## File Map

| File | Action |
|------|--------|
| `src/db.py` | Add `topics` TEXT column to `accounts`, add `youtube_url` TEXT column to `videos`, add `update_video_youtube_url()`, add `get_accounts()` |
| `api/routers/accounts.py` | Add `topics` to GET/PUT accounts endpoints |
| `api/routers/upload.py` | Call `update_video_youtube_url()` after upload success |
| `web/src/pages/Accounts.tsx` | Create — account list + niche/topics editor |
| `web/src/pages/Videos.tsx` | Add `youtube_url` column, clickable link or upload button |
| `scripts/run_24h.py` | Create — 24/7 round-robin generator script |
| `scripts/run_24h.sh` | Create — shell wrapper |

---

## Migration Summary

```sql
-- accounts table: add topics as JSON array
ALTER TABLE accounts ADD COLUMN topics TEXT DEFAULT '[]';

-- videos table: add youtube_url
ALTER TABLE videos ADD COLUMN youtube_url TEXT;
```