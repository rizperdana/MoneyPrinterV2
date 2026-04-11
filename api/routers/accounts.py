"""Accounts router — CRUD endpoints wrapping src/db.py."""

import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import APIRouter, HTTPException

from api.models import AccountCreate, AccountUpdate

router = APIRouter()


@router.get("/accounts")
async def list_accounts():
    """List all accounts."""
    from db import get_accounts
    return get_accounts()


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
