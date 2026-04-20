# YouTube OAuth Upload Implementation Plan

> **For agentic workers:** Use subagent-driven-development to implement task-by-task.

**Goal:** Replace browser automation with pure OAuth API for YouTube upload

**Architecture:** YouTube Data API v3 with OAuth 2.0 Bearer token, resumable upload protocol

**Tech Stack:** Python requests library, YouTube Data API v3, OAuth 2.0

---

### Task 1: Enhance youtube_api.py with proper error handling

**Files:**
- Modify: `src/youtube_api.py`

- [ ] Step 1: Read current youtube_api.py to understand implementation
- [ ] Step 2: Add better error handling for HTTP errors (401, 403, 500)
- [ ] Step 3: Add video ID extraction from API response
- [ ] Step 4: Add polling for video processing status
- [ ] Step 5: Test with curl command to verify API works
- [ ] Step 6: Commit

### Task 2: Update upload endpoint to remove browser fallback

**Files:**
- Modify: `api/routers/upload.py`

- [ ] Step 1: Read current upload.py to find browser fallback logic
- [ ] Step 2: Remove fallback to `classes/YouTube.py`
- [ ] Step 3: Return clear error if OAuth token invalid
- [ ] Step 4: Test upload with OAuth token
- [ ] Step 5: Commit

### Task 3: Verify OAuth token has correct scope

**Files:**
- Modify: `src/youtube_oauth.py`

- [ ] Step 1: Check what scopes are stored with OAuth tokens
- [ ] Step 2: Ensure `youtube.upload` scope is requested during OAuth flow
- [ ] Step 3: Add scope validation before upload
- [ ] Step 4: Test OAuth flow end-to-end
- [ ] Step 5: Commit

### Task 4: End-to-end test

**Files:**
- Test with actual video upload

- [ ] Step 1: Get fresh OAuth token
- [ ] Step 2: Call upload endpoint with selected account
- [ ] Step 3: Verify video appears on YouTube channel
- [ ] Step 4: Commit any final fixes