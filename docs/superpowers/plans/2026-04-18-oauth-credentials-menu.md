# OAuth Credentials Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated menu page to list all OAuth credentials stored in the `oauth_credentials` table, with API endpoint and frontend display.

**Architecture:** A new `/api/oauth/credentials` endpoint already exists. Need to: (1) enhance it to show linked accounts, (2) create new OAuthCredentials page with table, (3) add sidebar nav item.

**Tech Stack:** React (web/), FastAPI (api/), SQLite (db.py)

---

## File Structure

- `api/routers/accounts.py` - Enhance existing `/oauth/credentials` endpoint
- `api/routers/oauth.py` - Add DELETE endpoint for deleting credentials
- `web/src/pages/OAuthCredentials.tsx` - Create new page component
- `web/src/components/Sidebar.tsx` - Add nav item
- `web/src/lib/api.ts` - Add API method

---

### Task 1: Enhance OAuth Credentials API

**Files:**
- Modify: `api/routers/accounts.py:107-119`
- Modify: `api/routers/oauth.py`

- [ ] **Step 1: Read current endpoint**

Run: `grep -n "list_oauth_credentials" api/routers/accounts.py`
Show current implementation.

- [ ] **Step 2: Enhance `/oauth/credentials` to include linked accounts**

Modify endpoint to also return which accounts each credential is linked to:

```python
@router.get("/oauth/credentials")
async def list_oauth_credentials(platform: str = "youtube"):
    """List OAuth credentials for a platform with linked accounts."""
    from src.db import get_oauth_credentials, get_linked_oauth_ids
    
    creds = get_oauth_credentials(platform=platform)
    result = []
    for c in creds:
        linked_accounts = get_linked_oauth_ids(c["id"])
        result.append({
            "oauth_id": c["id"],
            "account_name": c["account_name"],
            "platform": c["platform"],
            "updated_at": c["updated_at"],
            "has_token": bool(c.get("token")),
            "linked_account_ids": linked_accounts
        })
    return result
```

- [ ] **Step 3: Add DELETE endpoint for OAuth credentials**

Add to `api/routers/oauth.py`:

```python
@router.delete("/credentials/{oauth_id}")
async def delete_oauth_credential(oauth_id: int):
    """Delete an OAuth credential."""
    from src.db import delete_oauth_credential
    deleted = delete_oauth_credential(oauth_id=oauth_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="OAuth credential not found")
    return {"deleted": True}
```

- [ ] **Step 4: Test the enhanced endpoint**

Run: `curl -s http://localhost:8000/api/oauth/credentials?platform=youtube | python -m json.tool`
Expected: JSON array with `oauth_id`, `account_name`, `platform`, `updated_at`, `has_token`, `linked_account_ids`

- [ ] **Step 5: Commit**

```bash
git add api/routers/accounts.py api/routers/oauth.py
git commit -m "feat: enhance OAuth credentials API with linked accounts"
```

---

### Task 2: Add API method for frontend

**Files:**
- Modify: `web/src/lib/api.ts`

- [ ] **Step 1: Read current api.ts**

Run: `grep -n "oauth" web/src/lib/api.ts`
Show current OAuth-related functions.

- [ ] **Step 2: Add fetchOAuthCredentials and deleteOAuthCredential**

Add after existing OAuth functions:

```typescript
export async function fetchOAuthCredentials(platform: string = 'youtube'): Promise<OAuthCredential[]> {
  const res = await fetch(`/api/oauth/credentials?platform=${platform}`)
  if (!res.ok) throw new Error('Failed to fetch OAuth credentials')
  return res.json()
}

export async function deleteOAuthCredential(oauthId: number): Promise<void> {
  const res = await fetch(`/api/auth/credentials/${oauthId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete OAuth credential')
}
```

- [ ] **Step 3: Add OAuthCredential type if missing**

Check if `OAuthCredential` type exists, add if not:

```typescript
export interface OAuthCredential {
  oauth_id: number
  account_name: string
  platform: string
  updated_at: string
  has_token: boolean
  linked_account_ids: number[]
}
```

- [ ] **Step 4: Commit**

```bash
cd web && git add src/lib/api.ts && git commit -m "feat: add OAuth credentials API methods"
```

---

### Task 3: Create OAuthCredentials page

**Files:**
- Create: `web/src/pages/OAuthCredentials.tsx`

- [ ] **Step 1: Read Accounts.tsx for reference**

Run: `wc -l web/src/pages/Accounts.tsx`
Get structure for similar page.

- [ ] **Step 2: Create OAuthCredentials.tsx**

```tsx
import { useEffect, useState } from 'react'
import { fetchOAuthCredentials, deleteOAuthCredential, OAuthCredential } from '../lib/api'

export default function OAuthCredentials() {
  const [credentials, setCredentials] = useState<OAuthCredential[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadCredentials()
  }, [])

  async function loadCredentials() {
    try {
      setLoading(true)
      const data = await fetchOAuthCredentials('youtube')
      setCredentials(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(oauthId: number) {
    if (!confirm('Delete this OAuth credential?')) return
    try {
      await deleteOAuthCredential(oauthId)
      await loadCredentials()
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  if (loading) return <div className="p-4">Loading...</div>
  if (error) return <div className="p-4 text-red-500">{error}</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">OAuth Credentials</h1>
      
      {credentials.length === 0 ? (
        <p className="text-gray-500">No OAuth credentials stored.</p>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-2">Account Name</th>
              <th className="text-left py-2">Platform</th>
              <th className="text-left py-2">Updated</th>
              <th className="text-left py-2">Status</th>
              <th className="text-left py-2">Linked Accounts</th>
              <th className="text-left py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {credentials.map((cred) => (
              <tr key={cred.oauth_id} className="border-b border-gray-100">
                <td className="py-3">{cred.account_name}</td>
                <td className="py-3">{cred.platform}</td>
                <td className="py-3">{new Date(cred.updated_at).toLocaleDateString()}</td>
                <td className="py-3">
                  {cred.has_token ? (
                    <span className="text-green-600">Connected</span>
                  ) : (
                    <span className="text-gray-400">No Token</span>
                  )}
                </td>
                <td className="py-3">
                  {cred.linked_account_ids.length > 0 ? (
                    <span>{cred.linked_account_ids.length} linked</span>
                  ) : (
                    <span className="text-gray-400">None</span>
                  )}
                </td>
                <td className="py-3">
                  <button
                    onClick={() => handleDelete(cred.oauth_id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
cd web && git add src/pages/OAuthCredentials.tsx && git commit -m "feat: add OAuth credentials page"
```

---

### Task 4: Add Sidebar nav item

**Files:**
- Modify: `web/src/components/Sidebar.tsx`

- [ ] **Step 1: Find nav items array**

Run: `grep -n "Dashboard\|Generate\|Videos\|Accounts" web/src/components/Sidebar.tsx`
Show where nav items are defined.

- [ ] **Step 2: Add OAuth Credentials nav item**

Add `{ name: 'OAuth Credentials', path: '/oauth-credentials' }` to navItems array.

- [ ] **Step 3: Commit**

```bash
cd web && git add src/components/Sidebar.tsx && git commit -m "feat: add OAuth Credentials nav item"
```

---

### Task 5: Register route in App

**Files:**
- Modify: `web/src/App.tsx` (or wherever routes are defined)

- [ ] **Step 1: Find route registration**

Run: `grep -n "Accounts\|Route" web/src/App.tsx | head -20`
Show how routes are set up.

- [ ] **Step 2: Add OAuthCredentials route**

Add route for `/oauth-credentials` pointing to OAuthCredentials component.

- [ ] **Step 3: Commit**

```bash
cd web && git add src/App.tsx && git commit -m "feat: register OAuth Credentials route"
```

---

### Task 6: Verify full flow

- [ ] **Step 1: Check API server running**

Run: `curl -s http://localhost:8000/api/oauth/credentials?platform=youtube | python -m json.tool`
Expected: Array of credentials

- [ ] **Step 2: Verify all files exist**

```bash
ls -la web/src/pages/OAuthCredentials.tsx
ls -la web/src/components/Sidebar.tsx
```

- [ ] **Step 3: Final commit**

No code changes, just summarize if all works.

---

## Self-Review Checklist

1. **Spec coverage:** All requirements covered (list credentials, show linked accounts, delete functionality, sidebar nav)
2. **Placeholder scan:** No TBD/TODO - all code shown is complete
3. **Type consistency:** `oauth_id` used consistently (int type matches DB)

## Execution Options

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints