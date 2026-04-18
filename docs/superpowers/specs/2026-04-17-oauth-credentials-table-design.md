# OAuth Credentials Table Design

## Overview

Store OAuth tokens for multiple platforms (YouTube, Facebook, TikTok, Twitter) linked to accounts. One account can have OAuth for multiple platforms (many-to-many relationship).

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS oauth_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    token TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_name, platform)
)
```

### Columns

| Column | Type | Description |
|--------|------|------------|
| id | INTEGER | Primary key, auto-increment |
| account_name | TEXT | Username (links to accounts.username) |
| platform | TEXT | youtube, facebook, tiktok, twitter |
| token | TEXT | access_token |
| payload | TEXT | Full JSON: refresh_token, expires_at, scope, etc |
| created_at | TIMESTAMP | Row creation time |
| updated_at | TIMESTAMP | Last update time |

### Constraints

- UNIQUE(account_name, platform): One OAuth credential per platform per account
- account_name references accounts.username at query time (no FK constraint)

## Functions

### add_oauth_credential(account_name, platform, token, payload_json) -> int

Insert new OAuth credential. Uses INSERT OR REPLACE to handle re-auth.

```python
def add_oauth_credential(account_name: str, platform: str, token: str, payload_json: str) -> int:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO oauth_credentials (account_name, platform, token, payload, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(account_name, platform) DO UPDATE SET
            token = excluded.token,
            payload = excluded.payload,
            updated_at = CURRENT_TIMESTAMP
        """,
        (account_name, platform, token, payload_json),
    )
    conn.commit()
    return cursor.lastrowid
```

### get_oauth_credentials(account_name: Optional[str] = None, platform: Optional[str] = None) -> list[dict]

Get OAuth credentials, optionally filtered.

```python
def get_oauth_credentials(account_name: Optional[str] = None, platform: Optional[str] = None) -> list[dict]:
    conn = _get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM oauth_credentials"
    params = []
    conditions = []
    
    if account_name:
        conditions.append("account_name = ?")
        params.append(account_name)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY updated_at DESC"
    
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

### delete_oauth_credential(account_name: str, platform: str) -> bool

Delete OAuth credential.

```python
def delete_oauth_credential(account_name: str, platform: str) -> bool:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM oauth_credentials WHERE account_name = ? AND platform = ?",
        (account_name, platform),
    )
    conn.commit()
    return cursor.rowcount > 0
```

### update_oauth_credential(account_name: str, platform: str, token: str, payload_json: str) -> bool

Update existing credential (alias for add with same logic).

## Account Menu Integration

### OAuth Connect Flow

1. Account menu shows "Connect [Platform] OAuth" option
2. Opens OAuth authorization URL in browser (platform-specific)
3. User authenticates on platform
4. Platform redirects to callback with tokens in URL/hash
5. Parse tokens from callback
6. Prompt for account_name to associate
7. Store in oauth_credentials table
8. Show success message

### Account Menu Display

Show connected OAuths per account:

```
Account: mychannel
  [YouTube] Connected (expires: 2026-05-01)
  [Facebook] Not connected
  [TikTok] Not connected
  [Twitter] Not connected
```

Options per platform: "Connect", "Refresh", "Disconnect"

## Platforms Supported

1. **youtube** - Google OAuth 2.0
2. **facebook** - Facebook Login
3. **tiktok** - TikTok Login Kit
4. **twitter** - X OAuth 2.0

## Implementation Order

1. Add oauth_credentials table to db.py init_db()
2. Add CRUD functions to db.py
3. Test functions independently (unit tests)
4. Integrate with account menu
5. Test full OAuth flow with new video

## Error Handling

- Invalid JSON in payload -> return error, don't store
- Duplicate account_name + platform -> upsert (update)
- Missing required fields -> validate before insert

## Testing

1. Add credential for YouTube
2. Add credential for same account, different platform (TikTok)
3. Update existing credential
4. Get credentials filtered by account_name
5. Get credentials filtered by platform
6. Delete credential
7. Test OAuth flow end-to-end (generate video)