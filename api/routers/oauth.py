from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from src.youtube_oauth import (
    get_authorization_url,
    exchange_code_for_tokens,
    start_oauth_flow,
    is_token_valid,
)

router = APIRouter(tags=["auth"])

# Separate router for Google redirect (no prefix)
google_redirect_router = APIRouter(tags=["auth"])


@google_redirect_router.get("/google/redirect")
async def googleRedirect(
    code: str = Query(...), state: str = Query(None), scope: str = Query(None)
):
    """Handle Google OAuth redirect callback."""
    account_id = state or "default"
    try:
        tokens = exchange_code_for_tokens(code, account_id)
        if tokens:
            return RedirectResponse(url="/accounts?oauth=success", status_code=302)
    except Exception as e:
        print(f"OAuth error: {e}")
    return RedirectResponse(url="/accounts?oauth=error", status_code=302)


@router.get("/google/url")
async def getAuthUrl(account_id: str = Query(None)):
    """Get OAuth authorization URL."""
    url = get_authorization_url(account_id)
    return {"url": url}


@router.get("/google/start")
async def startOAuth():
    """Start OAuth flow by opening browser."""
    url = start_oauth_flow()
    return {"url": url, "message": "Opened browser for OAuth authorization"}


@router.get("/google/callback")
async def oauthCallback(code: str = Query(...), state: str = Query(None)):
    """Handle OAuth callback."""
    account_id = state or "1"
    tokens = exchange_code_for_tokens(code, account_id)
    if tokens:
        return {"status": "authenticated"}
    return {"status": "error", "message": "Failed to exchange code"}


@router.get("/status")
async def authStatus():
    """Check authentication status."""
    return {
        "authenticated": is_token_valid("1"),
        "has_refresh_token": False,
    }


@router.post("/logout")
async def logout():
    """Logout by clearing tokens."""
    from pathlib import Path

    _project_root = Path(__file__).parent.parent.parent
    tokens_file = _project_root / ".mp" / "youtube_tokens.json"
    if tokens_file.exists():
        tokens_file.unlink()
    return {"status": "logged_out"}


@router.delete("/credentials/{oauth_id}")
async def delete_oauth_credential(oauth_id: int):
    """Delete an OAuth credential."""
    from db import delete_oauth_credential_by_id

    deleted = delete_oauth_credential_by_id(oauth_id=oauth_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="OAuth credential not found")
    return {"deleted": True}
