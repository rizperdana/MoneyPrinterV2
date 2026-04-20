"""Accounts router — CRUD endpoints wrapping src/db.py."""

import os
import sys

_project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, HTTPException, Request

from api.models import AccountCreate, AccountUpdate

router = APIRouter()


@router.get("/accounts")
async def list_accounts():
    """List all accounts from .mp cache files and DB."""
    from db import get_accounts, get_oauth_credentials

    result = []

    # Read youtube accounts directly from .mp/youtube.json
    yt_path = os.path.join(_project_root, ".mp", "youtube.json")
    if os.path.exists(yt_path):
        import json

        with open(yt_path, "r") as f:
            yt_data = json.load(f)
            for acc in yt_data.get("accounts", []):
                account_id = acc.get("id", "")
                # Check OAuth status
                oauth_creds = get_oauth_credentials(
                    platform="youtube", account_name=account_id
                )
                oauth_status = "connected" if oauth_creds else "not_connected"
                oauth_updated = (
                    oauth_creds[0].get("updated_at") if oauth_creds else None
                )
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

    # Read twitter accounts directly from .mp/twitter.json
    tw_path = os.path.join(_project_root, ".mp", "twitter.json")
    if os.path.exists(tw_path):
        import json

        with open(tw_path, "r") as f:
            tw_data = json.load(f)
            for acc in tw_data.get("accounts", []):
                account_id = acc.get("id", "")
                # Check OAuth status
                oauth_creds = get_oauth_credentials(
                    platform="twitter", account_name=account_id
                )
                oauth_status = "connected" if oauth_creds else "not_connected"
                oauth_updated = (
                    oauth_creds[0].get("updated_at") if oauth_creds else None
                )
                result.append(
                    {
                        "id": account_id,
                        "platform": "twitter",
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

    # Also get accounts from database
    db_accounts = get_accounts()
    for acc in db_accounts:
        # Avoid duplicates by checking username+platform
        if not any(
            a["username"] == acc["username"] and a["platform"] == acc["platform"]
            for a in result
        ):
            # Check OAuth status
            oauth_creds = get_oauth_credentials(
                platform=acc.get("platform"), account_name=acc.get("username")
            )
            oauth_status = "connected" if oauth_creds else "not_connected"
            oauth_updated = oauth_creds[0].get("updated_at") if oauth_creds else None
            acc["oauth_status"] = oauth_status
            acc["oauth_updated"] = oauth_updated
            result.append(acc)

    return result


@router.get("/oauth/credentials")
async def list_oauth_credentials(platform: str = "youtube"):
    """List OAuth credentials for a platform."""
    from db import get_oauth_credentials, get_linked_account_ids

    creds = get_oauth_credentials(platform=platform)
    return [
        {
            "oauth_id": c["id"],
            "account_name": c["account_name"],
            "platform": c["platform"],
            "updated_at": c["updated_at"],
            "has_token": bool(c.get("token")),
            "linked_account_ids": get_linked_account_ids(c["id"]),
        }
        for c in creds
    ]


@router.get("/accounts/{username}/last-topic")
async def get_last_topic(username: str):
    """Get the niche for an account from youtube.json."""
    import json

    # Read from .mp/youtube.json
    yt_path = os.path.join(_project_root, ".mp", "youtube.json")
    if os.path.exists(yt_path):
        with open(yt_path, "r") as f:
            yt_data = json.load(f)
            for acc in yt_data.get("accounts", []):
                if acc.get("id") == username:
                    return {
                        "topic": acc.get("niche", ""),
                        "niche": acc.get("niche", ""),
                    }

    return {"topic": None, "niche": None}


@router.post("/accounts")
async def create_account(body: AccountCreate):
    """Create a new account."""
    from db import add_account

    account_id = add_account(
        platform=body.platform,
        username=body.username,
        nickname=body.nickname,
        profile_path=body.profile_path,
    )
    return {"id": account_id, "status": "created"}


@router.put("/accounts/{account_id}")
async def update_account_endpoint(account_id: int, body: AccountUpdate):
    """Update an existing account."""
    from db import update_account

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = update_account(account_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "updated"}


@router.delete("/accounts/{account_id}")
async def delete_account_endpoint(account_id: int):
    """Delete an account."""
    from db import delete_account

    success = delete_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "deleted"}


@router.get("/accounts/{account_id}/oauth-links")
async def get_account_oauth_links(account_id: str):
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
            "linked": True,
        }
        for c in creds
    ]


@router.post("/accounts/{account_id}/link-oauth")
async def link_oauth_to_account_endpoint(account_id: str, request: Request):
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

    # Handle both "id" from DB and "oauth_id" from API response
    actual_oauth_id = oauth_id
    if isinstance(oauth_id, str) and not isinstance(oauth_id, int):
        # Try to find matching credential
        for c in creds:
            if str(c["id"]) == str(oauth_id):
                actual_oauth_id = c["id"]
                break

    link_id = link_oauth_to_account(account_id, actual_oauth_id)
    return {"link_id": link_id, "account_id": account_id, "oauth_id": oauth_id}


@router.delete("/accounts/{account_id}/unlink-oauth/{oauth_id}")
async def unlink_oauth(account_id: str, oauth_id: int):
    """Unlink an OAuth credential from an account."""
    from db import unlink_oauth_from_account

    deleted = unlink_oauth_from_account(account_id, oauth_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"deleted": True}
