# OAuth Credential Selection for Upload - Design Spec

## Problem Statement

User can see stored OAuth credentials in the accounts table, but:
1. Cannot actually SELECT one to use for upload
2. Upload API doesn't use OAuth credentials - just picks first account from cache

## Design Decision

**Many-to-Many Relationship:** Account ↔ OAuth via junction table.

## Data Model

### New Table: `account_oauth_links`

```sql
CREATE TABLE account_oauth_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    oauth_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, oauth_id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (oauth_id) REFERENCES oauth_credentials(id)
);
```

- One account can have multiple OAuth credentials (YouTube, FB, TikTok, Twitter)
- One OAuth credential can be linked to one account

### Functions to Add (db.py)

```python
def link_oauth_to_account(account_id: int, oauth_id: int) -> int:
    """Link an OAuth credential to an account. Returns link ID."""
    
def unlink_oauth_from_account(account_id: int, oauth_id: int) -> bool:
    """Remove link between account and OAuth credential."""
    
def get_linked_oauth_ids(account_id: int) -> list[int]:
    """Get all OAuth IDs linked to an account."""
    
def get_account_links_for_oauth(oauth_id: int) -> list[dict]:
    """Get all account links for an OAuth credential."""
```

## Fix Design

### 1. Accounts.tsx - Make OAuth Dropdown Functional

**Change:** On selection, create/remove link between account and OAuth.

**Implementation:**
- Fetch all available OAuth credentials from `/api/oauth/credentials?platform=youtube`
- Fetch currently linked OAuth IDs from `/api/accounts/{account_id}/oauth-links`
- On dropdown change, call API: `POST /accounts/{account_id}/link-oauth` with `oauth_id` or `DELETE` to unlink
- Show all available OAuth credentials in dropdown with checkmark on linked ones
- Click to toggle link on/off

**UI Flow:**
```
Account: mychannel | OAuth: [Dropdown ▼]
  ☑ raider_kickuuuu@gmail.com (YouTube)
  ☐ other_user@gmail.com (YouTube)
  ☐ No OAuth
```

### 2. accounts.py - New Endpoints

```
GET /accounts/{account_id}/oauth-links
    → Returns list of {oauth_id, platform, account_name, linked_at}

POST /accounts/{account_id}/link-oauth
    Body: {oauth_id: int}
    → Creates link, returns link_id

DELETE /accounts/{account_id}/link-oauth/{oauth_id}
    → Removes link
```

### 3. upload.py - Accept account_id and use linked OAuth

**Change:** Add `account_id` query parameter to upload endpoint.

**Implementation:**
- Add `account_id: int = None` parameter
- If provided, look up OAuth links for that account
- Get OAuth credentials for the platform
- Use the linked OAuth token for upload (or first linked one)

**Endpoint signature:**
```
POST /videos/{video_id}/upload?platform=youtube&account_id=123
```

**Logic:**
1. Get account_id from param or job.account
2. Query `account_oauth_links` for linked oauth_id
3. Query `oauth_credentials` for the token
4. Pass token to YouTube.py for upload

## Files to Change

| File | Change |
|------|--------|
| `src/db.py` | Add `account_oauth_links` table + link/unlink functions |
| `api/routers/accounts.py` | Add `/accounts/{id}/oauth-links` endpoints |
| `api/routers/upload.py` | Add `account_id` param, use OAuth token from linked cred |
| `web/src/pages/Accounts.tsx` | Make OAuth dropdown functional with link/unlink API |

## Testing

1. **DB Test:** Add link, verify link exists, delete link, verify gone
2. **API Test:** `POST /accounts/1/link-oauth` creates link
3. **UI Test:** Select OAuth from dropdown, verify selection persists after refresh
4. **Upload Test:** `POST /videos/123/upload?account_id=1` uses linked OAuth

## Constraints

- Keep browser-based upload working (YouTube.py uses Firefox profile)
- Don't break existing upload flow (backward compat)
- OAuth credentials are per-platform (YouTube creds for YouTube upload)