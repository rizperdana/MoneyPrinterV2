# OAuth Credential Selection for Upload - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to SELECT an OAuth credential from UI and have it used during video upload via API.

**Architecture:** Add junction table `account_oauth_links` for many-to-many relationship between accounts and OAuth credentials. UI allows linking/unlinking. Upload API uses linked OAuth.

**Tech Stack:** Python (db.py, api), TypeScript (React frontend)

---

## Task 1: Add account_oauth_links table and functions to db.py

**Files:**
- Modify: `src/db.py` (add table in init_db, add link/unlink functions after delete_oauth_credential)

- [ ] **Step 1: Add account_oauth_links table to init_db()**

Find `init_db()` function and add after oauth_credentials table creation (around line 88):

```python
    # Account-OAuth link table (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_oauth_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            oauth_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, oauth_id),
            FOREIGN KEY (account_id) REFERENCES accounts(id),
            FOREIGN KEY (oauth_id) REFERENCES oauth_credentials(id)
        )
    """)
```

- [ ] **Step 2: Add link_oauth_to_account() function**

Add after `delete_oauth_credential()` function (around line 540):

```python
def link_oauth_to_account(account_id: int, oauth_id: int) -> int:
    """
    Link an OAuth credential to an account.

    Args:
        account_id: The account ID
        oauth_id: The OAuth credential ID

    Returns:
        The row ID of the inserted link
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO account_oauth_links (account_id, oauth_id, created_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(account_id, oauth_id) DO NOTHING
        """,
        (account_id, oauth_id),
    )
    conn.commit()
    return cursor.lastrowid
```

- [ ] **Step 3: Add unlink_oauth_from_account() function**

```python
def unlink_oauth_from_account(account_id: int, oauth_id: int) -> bool:
    """
    Remove link between account and OAuth credential.

    Args:
        account_id: The account ID
        oauth_id: The OAuth credential ID

    Returns:
        True if deleted, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM account_oauth_links WHERE account_id = ? AND oauth_id = ?",
        (account_id, oauth_id),
    )
    conn.commit()
    return cursor.rowcount > 0
```

- [ ] **Step 4: Add get_linked_oauth_ids() function**

```python
def get_linked_oauth_ids(account_id: int) -> list[int]:
    """
    Get all OAuth IDs linked to an account.

    Args:
        account_id: The account ID

    Returns:
        List of OAuth credential IDs
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT oauth_id FROM account_oauth_links WHERE account_id = ?",
        (account_id,),
    )
    return [row["oauth_id"] for row in cursor.fetchall()]
```

- [ ] **Step 5: Add get_oauth_credentials_by_ids() function**

```python
def get_oauth_credentials_by_ids(oauth_ids: list[int]) -> list[dict]:
    """
    Get OAuth credentials by their IDs.

    Args:
        oauth_ids: List of OAuth credential IDs

    Returns:
        List of OAuth credential dicts
    """
    if not oauth_ids:
        return []
    conn = _get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(oauth_ids))
    cursor.execute(
        f"SELECT * FROM oauth_credentials WHERE id IN ({placeholders})",
        oauth_ids,
    )
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 6: Test the new functions**

Run:
```python
python3 -c "
from db import init_db, link_oauth_to_account, unlink_oauth_from_account, get_linked_oauth_ids, get_oauth_credentials_by_ids
init_db()

# First get an oauth_id from existing credentials
from db import get_oauth_credentials
creds = get_oauth_credentials()
if creds:
    oauth_id = creds[0]['id']
    # Link it to account_id 1
    link_id = link_oauth_to_account(1, oauth_id)
    print(f'Linked, returned: {link_id}')
    
    # Get linked
    linked = get_linked_oauth_ids(1)
    print(f'Linked OAuth IDs for account 1: {linked}')
    
    # Get full creds
    full_creds = get_oauth_credentials_by_ids(linked)
    print(f'Full creds: {len(full_creds)}')
    
    # Unlink
    deleted = unlink_oauth_from_account(1, oauth_id)
    print(f'Unlinked: {deleted}')
"
```

- [ ] **Step 7: Commit**

```bash
git add src/db.py && git commit -m "feat: add account_oauth_links table with link/unlink functions"
```

---

## Task 2: Add link/unlink endpoints to accounts.py

**Files:**
- Modify: `api/routers/accounts.py` (add new endpoints for linking)

- [ ] **Step 1: Add GET /accounts/{account_id}/oauth-links endpoint**

Add after existing endpoints (around line 130):

```python
@router.get("/accounts/{account_id}/oauth-links")
async def get_account_oauth_links(account_id: int):
    """Get all OAuth links for an account."""
    from db import get_linked_oauth_ids, get_oauth_credentials_by_ids
    
    oauth_ids = get_linked_oauth_ids(account_id)
    if not oauth_ids:
        return []
    
    creds = get_oauth_credentials_by_ids(oauth_ids)
    return [
        {
            "oauth_id": c["id"],
            "platform": c["platform"],
            "account_name": c["account_name"],
            "linked": True
        }
        for c in creds
    ]
```

- [ ] **Step 2: Add POST /accounts/{account_id}/link-oauth endpoint**

```python
@router.post("/accounts/{account_id}/link-oauth")
async def link_oauth_to_account(account_id: int, request: Request):
    """Link an OAuth credential to an account."""
    from db import link_oauth_to_account, get_oauth_credentials
    
    body = await request.json()
    oauth_id = body.get("oauth_id")
    
    if not oauth_id:
        raise HTTPException(status_code=400, detail="oauth_id required")
    
    # Verify oauth_id exists
    creds = get_oauth_credentials()
    if not any(c["id"] == oauth_id for c in creds):
        raise HTTPException(status_code=404, detail="OAuth credential not found")
    
    link_id = link_oauth_to_account(account_id, oauth_id)
    return {"link_id": link_id, "account_id": account_id, "oauth_id": oauth_id}
```

- [ ] **Step 3: Add DELETE /accounts/{account_id}/unlink-oauth/{oauth_id} endpoint**

```python
@router.delete("/accounts/{account_id}/unlink-oauth/{oauth_id}")
async def unlink_oauth(account_id: int, oauth_id: int):
    """Unlink an OAuth credential from an account."""
    from db import unlink_oauth_from_account
    
    deleted = unlink_oauth_from_account(account_id, oauth_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"deleted": True}
```

- [ ] **Step 4: Test the endpoints**

```bash
curl -s http://localhost:8000/api/accounts/1/oauth-links | python3 -m json.tool
```

- [ ] **Step 5: Commit**

```bash
git add api/routers/accounts.py && git commit -m "feat: add oauth link/unlink endpoints to accounts API"
```

---

## Task 3: Update upload.py to use linked OAuth

**Files:**
- Modify: `api/routers/upload.py` (add account_id param, use OAuth from linked cred)

- [ ] **Step 1: Add account_id parameter to upload endpoint**

Find the `upload_video_by_id()` function and add `account_id: int = None` parameter:

```python
@router.post("/videos/{video_id}/upload")
async def upload_video_by_id(
    video_id: int,
    background_tasks: BackgroundTasks,
    platform: str = "youtube",
    account_id: int = None,  # ADD THIS
):
```

- [ ] **Step 2: Get OAuth credentials when account_id is provided**

Add after the existing account lookup (around line 100):

```python
    oauth_creds = []
    if account_id:
        from db import get_linked_oauth_ids, get_oauth_credentials_by_ids
        oauth_ids = get_linked_oauth_ids(account_id)
        if oauth_ids:
            oauth_creds = get_oauth_credentials_by_ids(oauth_ids)
            # Filter by platform
            oauth_creds = [c for c in oauth_creds if c["platform"] == platform]
```

- [ ] **Step 3: Pass OAuth token to upload**

Modify the upload call to pass OAuth credentials:

```python
    # Add to the background task or upload call
    # If we have OAuth creds, pass the first one
    oauth_token = oauth_creds[0]["token"] if oauth_creds else None
    
    background_tasks.add_task(
        do_upload,
        job_id=job_id,
        platform=platform,
        account_uuid=account.get("id") if account else None,
        oauth_token=oauth_token,  # ADD THIS
    )
```

- [ ] **Step 4: Update do_upload to accept and use oauth_token**

Find `do_upload()` function and add `oauth_token` parameter:

```python
def do_upload(job_id: int, platform: str, account_uuid: str = None, oauth_token: str = None):
```

Use oauth_token if provided (for API-based upload):

```python
    if oauth_token and platform == "youtube":
        # Use YouTube API with OAuth token instead of browser
        from src.youtube_api import youtube_api_upload
        youtube_api_upload(
            video_path=file_path,
            title=title,
            description=description,
            oauth_token=oauth_token,
        )
        return
```

- [ ] **Step 5: Commit**

```bash
git add api/routers/upload.py && git commit -m "feat: upload endpoint accepts account_id and uses linked OAuth"
```

---

## Task 4: Fix Accounts.tsx dropdown to link/unlink OAuth

**Files:**
- Modify: `web/src/pages/Accounts.tsx` (make dropdown functional)

- [ ] **Step 1: Update OAuth dropdown to show all available creds with link toggle**

Find the OAuth dropdown section (around lines 95-115) and replace with:

```tsx
<select
  className="h-6 text-xs px-1 rounded border"
  value={linkedOauthIds.includes(a.id) ? String(a.id) : ""}
  onChange={async (e) => {
    const oauthId = parseInt(e.target.value);
    if (oauthId && !linkedOauthIds.includes(a.id)) {
      // Link OAuth to account
      await fetch(`/api/accounts/${a.id}/link-oauth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oauth_id: oauthId })
      });
      setRefresh(r => r + 1);
    }
  }}
>
  <option value="">No OAuth</option>
  {oauthCreds
    .filter(c => c.platform === 'youtube')
    .map(cred => (
      <option 
        key={cred.oauth_id} 
        value={cred.oauth_id}
        disabled={linkedOauthIds.includes(cred.oauth_id) && cred.oauth_id !== a.id}
      >
        {cred.account_name} {linkedOauthIds.includes(cred.oauth_id) ? '(linked)' : ''}
      </option>
    ))}
</select>
```

- [ ] **Step 2: Fetch all OAuth credentials and linked status**

Add to the component's useEffect:

```tsx
const [oauthCreds, setOauthCreds] = useState<any[]>([]);
const [linkedOauthIds, setLinkedOauthIds] = useState<number[]>([]);

useEffect(() => {
  // Fetch available OAuth credentials
  fetch('/api/oauth/credentials?platform=youtube')
    .then(r => r.json())
    .then(data => setOauthCreds(data));
  
  // Fetch linked status for all accounts
  Promise.all(accounts.map(a => 
    fetch(`/api/accounts/${a.id}/oauth-links`).then(r => r.json())
  )).then(results => {
    const allLinked = results.flat().map(l => l.oauth_id);
    setLinkedOauthIds([...new Set(allLinked)]);
  });
}, [accounts, refresh]);
```

- [ ] **Step 3: Commit**

```bash
cd web && git add src/pages/Accounts.tsx && git commit -m "fix: make OAuth dropdown functional with link/unlink"
```

---

## Task 5: Test full OAuth selection flow

**Files:**
- Test: Manual API and UI testing

- [ ] **Step 1: Test database functions**

```bash
python3 -c "
from db import init_db, get_oauth_credentials, link_oauth_to_account, get_linked_oauth_ids, unlink_oauth_from_account
init_db()
creds = get_oauth_credentials()
print(f'Total OAuth creds: {len(creds)}')
if creds:
    oauth_id = creds[0]['id']
    print(f'Testing with oauth_id: {oauth_id}')
    link_id = link_oauth_to_account(1, oauth_id)
    print(f'Link result: {link_id}')
    linked = get_linked_oauth_ids(1)
    print(f'Linked IDs: {linked}')
"
```

- [ ] **Step 2: Test API endpoints**

```bash
# Get OAuth links for account 1
curl -s http://localhost:8000/api/accounts/1/oauth-links | python3 -m json.tool

# Link OAuth
curl -s -X POST http://localhost:8000/api/accounts/1/link-oauth \
  -H "Content-Type: application/json" \
  -d '{"oauth_id": 1}' | python3 -m json.tool
```

- [ ] **Step 3: Test upload with account_id**

```bash
# Test upload endpoint accepts account_id
curl -s -X POST "http://localhost:8000/api/videos/1/upload?platform=youtube&account_id=1" | python3 -m json.tool
```

- [ ] **Step 4: Commit test results**

```bash
git add -A && git commit -m "test: verify oauth selection and upload flow"
```

---