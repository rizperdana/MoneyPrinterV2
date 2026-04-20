#!/usr/bin/env python3
"""
Test script to verify oauth_token refresh fix in youtubeApiUpload.

Simulates the exact upload flow where:
1. API endpoint passes oauth_token from DB
2. If token is expired, it should be refreshed
3. If token is valid, it should be used as-is
"""

import sys
import time
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root and src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test data
TEST_ACCOUNT_ID = "test_account_123"
VALID_TOKEN = "valid_access_token_12345"
EXPIRED_TOKEN = "expired_access_token_67890"


def create_mock_tokens(access_token: str, expired: bool = False):
    """Create mock token data."""
    saved_at = time.time() - 7200 if expired else time.time()
    return {
        "access_token": access_token,
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600,
        "saved_at": saved_at,
    }


class MockCredentials:
    """Mock credential object."""
    def __init__(self, token: str, payload: str):
        self.token = token
        self.payload = payload


@patch("src.youtube_api.requests.post")
@patch("src.youtube_oauth.load_tokens")
@patch("src.youtube_oauth.save_tokens")
def test_expired_token_gets_refreshed(mock_save, mock_load_tokens, mock_post):
    """Test: When passed oauth_token is expired, it should be refreshed."""
    print("\n" + "=" * 60)
    print("TEST: Expired oauth_token should trigger refresh")
    print("=" * 60)
    
    # Setup: DB has expired token, API passes it
    mock_load_tokens.return_value = create_mock_tokens(EXPIRED_TOKEN, expired=True)
    
    # Mock successful refresh
    refreshed_tokens = create_mock_tokens("refreshed_access_token_xyz", expired=False)
    mock_save.return_value = None
    
    # Mock API response (401 from original expired token)
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": {"errors": [{"message": "Token expired"}]}}
    mock_response.text = "Token expired"
    mock_post.return_value = mock_response
    
    from src.youtube_api import youtubeApiUpload
    
    # We expect an exception because we're mocking only the token refresh,
    # not the full upload flow. The key assertion is that get_access_token
    # was called to refresh.
    
    call_count = [0]
    original_get_access_token = None
    
    def mock_get_access_token(account_id):
        call_count[0] += 1
        tokens = mock_load_tokens(account_id)
        if tokens:
            return "refreshed_access_token_xyz"
        return None
    
    with patch("src.youtube_api.get_access_token", mock_get_access_token):
        with patch("src.youtube_api.is_token_valid_for_token") as mock_is_valid:
            # Simulate: passed token is expired
            mock_is_valid.return_value = False
            
            try:
                # This will fail at upload but we just want to verify refresh was called
                with patch("src.youtube_api.os.path.exists", return_value=True):
                    with patch("src.youtube_api.Path") as mock_path:
                        mock_path_instance = MagicMock()
                        mock_path_instance.stat.return_value.st_size = 1000
                        mock_path.return_value = mock_path_instance
                        
                        youtubeApiUpload(
                            video_path="/fake/video.mp4",
                            title="Test",
                            account_id=TEST_ACCOUNT_ID,
                            oauth_token=EXPIRED_TOKEN,
                        )
            except Exception as e:
                # Expected - we're testing token logic, not full upload
                pass
    
    # Verify: is_token_valid_for_token was called with the expired token
    mock_is_valid.assert_called_once_with(EXPIRED_TOKEN, TEST_ACCOUNT_ID)
    print(f"✓ is_token_valid_for_token called with: {EXPIRED_TOKEN[:20]}...")
    
    # Verify: get_access_token was called to refresh
    assert call_count[0] > 0, "get_access_token should have been called to refresh token"
    print(f"✓ get_access_token called {call_count[0]} time(s) to refresh token")
    
    print("\n✅ TEST PASSED: Expired token triggers refresh")


@patch("src.youtube_api.is_token_valid_for_token")
@patch("src.youtube_api.get_access_token")
def test_valid_token_used_directly(mock_get_access, mock_is_valid):
    """Test: When passed oauth_token is valid, it should be used directly."""
    print("\n" + "=" * 60)
    print("TEST: Valid oauth_token should be used directly")
    print("=" * 60)
    
    # Setup: token is valid
    mock_is_valid.return_value = True
    mock_get_access.return_value = VALID_TOKEN  # Should NOT be called
    
    from src.youtube_api import youtubeApiUpload
    
    access_token_used = [None]
    
    def capture_get_access_token(account_id):
        # Should not be called for valid token
        return "should_not_be_used"
    
    mock_get_access.side_effect = capture_get_access_token
    
    with patch("src.youtube_api.os.path.exists", return_value=True):
        with patch("src.youtube_api.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.stat.return_value.st_size = 1000
            mock_path.return_value = mock_path_instance
            
            try:
                youtubeApiUpload(
                    video_path="/fake/video.mp4",
                    title="Test",
                    account_id=TEST_ACCOUNT_ID,
                    oauth_token=VALID_TOKEN,
                )
            except Exception as e:
                pass
    
    # Verify: is_token_valid_for_token was called
    mock_is_valid.assert_called_once_with(VALID_TOKEN, TEST_ACCOUNT_ID)
    print(f"✓ is_token_valid_for_token called with valid token")
    
    # Verify: get_access_token was NOT called (token is valid)
    assert mock_get_access.call_count == 0, "get_access_token should NOT be called for valid token"
    print(f"✓ get_access_token NOT called (token is valid)")
    
    print("\n✅ TEST PASSED: Valid token used directly without refresh")


@patch("src.youtube_api.get_access_token")
def test_no_token_falls_back_to_get_access(mock_get_access):
    """Test: When no oauth_token passed, falls back to get_access_token."""
    print("\n" + "=" * 60)
    print("TEST: No oauth_token falls back to get_access_token")
    print("=" * 60)
    
    mock_get_access.return_value = VALID_TOKEN
    
    from src.youtube_api import youtubeApiUpload
    
    with patch("src.youtube_api.os.path.exists", return_value=True):
        with patch("src.youtube_api.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.stat.return_value.st_size = 1000
            mock_path.return_value = mock_path_instance
            
            try:
                youtubeApiUpload(
                    video_path="/fake/video.mp4",
                    title="Test",
                    account_id=TEST_ACCOUNT_ID,
                    oauth_token=None,  # No token passed
                )
            except Exception as e:
                pass
    
    # Verify: get_access_token was called
    mock_get_access.assert_called_once_with(TEST_ACCOUNT_ID)
    print(f"✓ get_access_token called with account_id: {TEST_ACCOUNT_ID}")
    
    print("\n✅ TEST PASSED: No token falls back correctly")


def test_is_token_valid_for_token_function():
    """Test the is_token_valid_for_token function directly."""
    print("\n" + "=" * 60)
    print("TEST: is_token_valid_for_token function")
    print("=" * 60)
    
    from src.youtube_oauth import is_token_valid_for_token
    
    with patch("src.youtube_oauth.load_tokens") as mock_load:
        # Test 1: Valid token
        mock_load.return_value = create_mock_tokens(VALID_TOKEN, expired=False)
        result = is_token_valid_for_token(VALID_TOKEN, TEST_ACCOUNT_ID)
        assert result == True, "Valid token should return True"
        print(f"✓ Valid token returns True")
        
        # Test 2: Expired token
        mock_load.return_value = create_mock_tokens(VALID_TOKEN, expired=True)
        result = is_token_valid_for_token(VALID_TOKEN, TEST_ACCOUNT_ID)
        assert result == False, "Expired token should return False"
        print(f"✓ Expired token returns False")
        
        # Test 3: Token mismatch (passed token different from DB)
        mock_load.return_value = create_mock_tokens("different_token", expired=False)
        result = is_token_valid_for_token(VALID_TOKEN, TEST_ACCOUNT_ID)
        assert result == False, "Token mismatch should return False"
        print(f"✓ Token mismatch returns False")
        
        # Test 4: No tokens in DB
        mock_load.return_value = None
        result = is_token_valid_for_token(VALID_TOKEN, TEST_ACCOUNT_ID)
        assert result == False, "No tokens should return False"
        print(f"✓ No tokens returns False")
    
    print("\n✅ TEST PASSED: is_token_valid_for_token works correctly")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("YOUTUBE API TOKEN REFRESH FIX - TEST SUITE")
    print("=" * 60)
    
    try:
        test_is_token_valid_for_token_function()
        test_valid_token_used_directly()
        test_expired_token_gets_refreshed()
        test_no_token_falls_back_to_get_access()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)
        print("\nFix verified:")
        print("1. Valid oauth_token → used directly (no unnecessary refresh)")
        print("2. Expired oauth_token → refreshed via get_access_token()")
        print("3. No oauth_token → falls back to get_access_token()")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
