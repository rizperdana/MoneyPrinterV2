# YouTube OAuth Upload Refactor - Design Spec

## Problem
- Current upload tries OAuth API first, falls back to Firefox/Selenium browser automation on error
- Firefox/Selenium is unreliable (profile issues, version mismatches, headless mode problems)
- User wants to REMOVE browser automation entirely and use pure OAuth API upload

## Goal
Replace Firefox/Selenium browser automation with reliable YouTube Data API v3 OAuth upload.

## Architecture

### Current Flow (to be removed)
```
POST /videos/{video_id}/upload → try OAuth API → fallback to browser automation → Firefox/Selenium
```

### New Flow
```
POST /videos/{video_id}/upload → OAuth API → YouTube Data API v3 upload (no browser)
```

## Key Changes

### 1. YouTube API Upload (`src/youtube_api.py`)
- Already exists with resumable upload
- Needs improvement: better error handling, video ID extraction, status polling
- Remove fallback to browser code

### 2. Token Management (`src/youtube_oauth.py`)
- Already exists: `get_access_token()`, `refresh_token()`, `save_tokens()`
- Ensure automatic refresh works correctly
- Validate token has correct scope: `https://www.googleapis.com/auth/youtube.upload`

### 3. Upload Endpoint (`api/routers/upload.py`)
- Remove browser fallback logic
- If OAuth fails, return clear error (no fallback to browser)
- Require valid OAuth token linked to account

### 4. Remove Browser Dependency
- Delete or deprecate `src/classes/YouTube.py` (browser automation)
- Remove selenium/geckodriver dependencies (optional - keep for other uses)
- Clean up related code

## Data Flow
1. User selects account in UI
2. Account has linked OAuth credential (stored in `oauth_credentials` table)
3. `oauth_token` retrieved from `account_oauth_links` join
4. `youtubeApiUpload()` called with valid `oauth_token`
5. YouTube Data API v3 handles upload via resumable protocol
6. Returns video URL on success

## Success Criteria
- Upload works WITHOUT Firefox browser
- Uses YouTube Data API v3 OAuth authentication
- Clear error messages when OAuth fails
- No automatic fallback to browser automation

## Files to Modify
- `src/youtube_api.py` - improve error handling
- `api/routers/upload.py` - remove browser fallback
- Optionally: `src/classes/YouTube.py` - deprecate (keep for reference)