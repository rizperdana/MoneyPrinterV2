from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from src.youtube_oauth import getAuthorizationUrl, exchangeCodeForTokens, startOAuthFlow, isTokenValid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/url")
async def getAuthUrl(account_id: str = Query(None)):
    """Get OAuth authorization URL."""
    url = getAuthorizationUrl(account_id)
    return {"url": url}


@router.get("/google/start")
async def startOAuth():
    """Start OAuth flow by opening browser."""
    url = startOAuthFlow()
    return {"url": url, "message": "Opened browser for OAuth authorization"}


@router.get("/google/callback")
async def oauthCallback(code: str = Query(...), state: str = Query(None)):
    """Handle OAuth callback."""
    account_id = state or "1"
    tokens = exchangeCodeForTokens(code, account_id)
    if tokens:
        return {"status": "authenticated"}
    return {"status": "error", "message": "Failed to exchange code"}


@router.get("/status")
async def authStatus():
    """Check authentication status."""
    return {
        "authenticated": isTokenValid("1"),
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