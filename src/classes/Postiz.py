"""
Postiz API client for multi-platform social media publishing.

Replaces PostBridge with a self-hosted Postiz instance.
Docs: https://docs.postiz.com/public-api/introduction
"""

import mimetypes
import os
import time
from datetime import datetime
from typing import Optional, Sequence

import requests


class PostizClientError(RuntimeError):
    """Raised when a Postiz API request fails."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class Postiz:
    """
    Thin client for the Postiz public API.

    Docs: https://docs.postiz.com/public-api/introduction
    """

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.postiz.com",
        session: Optional[requests.Session] = None,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the Postiz client.

        Args:
            api_key: API key from Postiz Settings > Developers > Public API.
            api_url: Base URL of the Postiz instance (cloud or self-hosted).
            session: Optional requests session for connection pooling.
            max_retries: Max retry attempts for transient failures.
        """
        self._base_url = f"{api_url.rstrip('/')}/public/v1"
        self._session = session or requests.Session()
        self._headers = {
            "Authorization": api_key,
        }
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_integrations(self) -> list[dict]:
        """
        Fetch connected social media integrations (channels).

        Returns:
            List of integration dicts with keys: id, name, identifier,
            picture, disabled, profile, customer.
        """
        return self._request_json("GET", f"{self._base_url}/integrations")

    def upload_file(self, file_path: str) -> dict:
        """
        Upload a local media file to Postiz.

        Args:
            file_path: Absolute path to the media file (image or video).

        Returns:
            Dict with keys: id, path (URL to the uploaded file).
        """
        if not os.path.exists(file_path):
            raise PostizClientError(f"File does not exist: {file_path}")

        mime_type = self._guess_mime_type(file_path)
        file_name = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            response = self._request(
                "POST",
                f"{self._base_url}/upload",
                files={"file": (file_name, f, mime_type)},
                timeout=600,
                expected_statuses={200, 201},
            )

        try:
            return response.json()
        except ValueError as exc:
            raise PostizClientError(
                "Postiz returned a non-JSON response for upload.",
                status_code=response.status_code,
            ) from exc

    def create_post(
        self,
        posts: list[dict],
        post_type: str = "now",
        scheduled_date: Optional[str] = None,
        short_link: bool = False,
        tags: Optional[list] = None,
    ) -> dict:
        """
        Create or schedule a post across one or more integrations.

        Args:
            posts: List of post payloads, each containing:
                - integration: {"id": "integration-id"}
                - value: [{"content": "...", "image": [...]}]
                - settings: {"__type": "youtube", "title": "...", ...}
            post_type: "now" to publish immediately, "schedule" to schedule.
            scheduled_date: ISO8601 datetime string (required when post_type="schedule").
            short_link: Whether to shorten links.
            tags: Optional list of tags.

        Returns:
            API response dict.
        """
        payload = {
            "type": post_type,
            "date": scheduled_date or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "shortLink": short_link,
            "tags": tags or [],
            "posts": posts,
        }

        return self._request_json(
            "POST",
            f"{self._base_url}/posts",
            json=payload,
        )

    def delete_post(self, post_id: str) -> dict:
        """
        Delete a post by ID.

        Args:
            post_id: The post ID to delete.

        Returns:
            API response dict.
        """
        return self._request_json(
            "DELETE",
            f"{self._base_url}/posts/{post_id}",
        )

    def get_posts(self, limit: int = 10) -> list[dict]:
        """
        Get a list of recent posts.

        Args:
            limit: Maximum number of posts to return.

        Returns:
            List of post dicts.
        """
        return self._request_json(
            "GET",
            f"{self._base_url}/posts",
            params={"limit": limit},
        )

    # ------------------------------------------------------------------
    # Convenience methods for MoneyPrinterV2
    # ------------------------------------------------------------------

    def find_integration(self, platform: str) -> Optional[dict]:
        """
        Find the first integration matching a platform identifier.

        Args:
            platform: Platform identifier (e.g., "youtube", "tiktok").

        Returns:
            Integration dict or None if not found.
        """
        integrations = self.list_integrations()
        for integration in integrations:
            if integration.get("identifier", "").lower() == platform.lower():
                return integration
        return None

    def find_integrations(self, platforms: Sequence[str]) -> dict[str, dict]:
        """
        Find integrations for multiple platforms.

        Args:
            platforms: Platform identifiers to look up.

        Returns:
            Dict mapping platform name -> integration dict (skips missing).
        """
        integrations = self.list_integrations()
        by_identifier = {}
        for integration in integrations:
            identifier = integration.get("identifier", "").lower()
            by_identifier[identifier] = integration

        result = {}
        for platform in platforms:
            key = platform.strip().lower()
            if key in by_identifier:
                result[key] = by_identifier[key]
        return result

    def publish_video(
        self,
        video_path: str,
        title: str,
        description: str,
        platforms: Sequence[str],
        scheduled_date: Optional[str] = None,
        youtube_settings: Optional[dict] = None,
        tiktok_settings: Optional[dict] = None,
    ) -> dict:
        """
        High-level method: upload a video and publish to specified platforms.

        Args:
            video_path: Path to the local video file.
            title: Post/video title.
            description: Post/video description (used as caption).
            platforms: Target platforms, e.g. ["youtube", "tiktok"].
            scheduled_date: Optional ISO8601 datetime for scheduling.
            youtube_settings: Optional YouTube-specific overrides.
            tiktok_settings: Optional TikTok-specific overrides.

        Returns:
            Dict with keys: upload (upload response), post (post response),
            skipped_platforms (list of platforms without integrations).
        """
        # 1. Upload the video
        upload_result = self.upload_file(video_path)
        video_id = upload_result.get("id")
        video_url = upload_result.get("path", "")
        if not video_id:
            raise PostizClientError(
                f"Postiz upload did not return a file ID: {upload_result}"
            )

        # 2. Find integrations for requested platforms
        integration_map = self.find_integrations(platforms)
        skipped = [p for p in platforms if p.lower() not in integration_map]

        if not integration_map:
            raise PostizClientError(
                f"No Postiz integrations found for: {', '.join(platforms)}. "
                "Connect accounts in Postiz first."
            )

        # 3. Build post payloads per platform
        posts = []
        for platform, integration in integration_map.items():
            settings = self._build_platform_settings(
                platform, title, youtube_settings, tiktok_settings
            )
            posts.append({
                "integration": {"id": integration["id"]},
                "value": [
                    {
                        "content": description,
                        "image": [
                            {"id": video_id, "path": video_url}
                        ],
                    }
                ],
                "settings": settings,
            })

        # 4. Determine post type
        post_type = "schedule" if scheduled_date else "now"

        # 5. Create the post
        post_result = self.create_post(
            posts=posts,
            post_type=post_type,
            scheduled_date=scheduled_date,
        )

        return {
            "upload": upload_result,
            "post": post_result,
            "skipped_platforms": skipped,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_platform_settings(
        self,
        platform: str,
        title: str,
        youtube_overrides: Optional[dict] = None,
        tiktok_overrides: Optional[dict] = None,
    ) -> dict:
        """Build platform-specific settings dict."""
        platform = platform.strip().lower()

        if platform == "youtube":
            settings = {
                "__type": "youtube",
                "title": title,
                "type": "SHORTS",
                "selfDeclaredMadeForKids": False,
            }
            if youtube_overrides:
                settings.update(youtube_overrides)
            return settings

        if platform == "tiktok":
            settings = {
                "__type": "tiktok",
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "duet": False,
                "stitch": False,
                "comment": True,
                "autoAddMusic": False,
                "brand_content_toggle": False,
                "brand_organic_toggle": False,
                "content_posting_method": "UPLOAD",
            }
            if tiktok_overrides:
                settings.update(tiktok_overrides)
            return settings

        # Generic fallback
        return {"__type": platform}

    def _guess_mime_type(self, file_path: str) -> str:
        """Guess MIME type for a file, defaulting to video/mp4."""
        guessed_type = mimetypes.guess_type(file_path)[0]
        if guessed_type in {
            "image/png", "image/jpeg", "image/gif", "image/webp",
            "video/mp4", "video/quicktime", "video/webm",
        }:
            return guessed_type
        return "video/mp4"

    def _request_json(self, method: str, url: str, **kwargs) -> dict:
        """Make a request and parse JSON response."""
        response = self._request(method, url, **kwargs)

        try:
            response_json = response.json()
        except ValueError as exc:
            raise PostizClientError(
                "Postiz returned a non-JSON response.",
                status_code=response.status_code,
            ) from exc

        if not isinstance(response_json, dict):
            return {"data": response_json}

        return response_json

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[dict] = None,
        timeout: int = 60,
        expected_statuses: Optional[set[int]] = None,
        **kwargs,
    ) -> requests.Response:
        """Make an HTTP request with retry logic."""
        if expected_statuses is None:
            expected_statuses = {200}

        merged_headers = dict(self._headers)
        if headers:
            merged_headers.update(headers)

        last_exception = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=merged_headers,
                    timeout=timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_exception = exc
                if attempt == self._max_retries:
                    break
                time.sleep(0.5 * attempt)
                continue

            if response.status_code in expected_statuses:
                return response

            if (
                response.status_code in self.RETRYABLE_STATUS_CODES
                and attempt < self._max_retries
            ):
                time.sleep(0.5 * attempt)
                continue

            raise PostizClientError(
                self._build_http_error(response),
                status_code=response.status_code,
            )

        raise PostizClientError(
            f"Request to Postiz failed: {last_exception}",
        ) from last_exception

    def _build_http_error(self, response: requests.Response) -> str:
        """Build a human-readable error message from a failed response."""
        try:
            response_json = response.json()
        except ValueError:
            response_json = None

        details = None

        if isinstance(response_json, dict):
            if isinstance(response_json.get("error"), list):
                details = "; ".join(str(item) for item in response_json["error"])
            elif response_json.get("error"):
                details = str(response_json["error"])
            elif response_json.get("message"):
                details = str(response_json["message"])

        if details is None:
            body = response.text.strip()
            details = body or "No response body."

        return f"Postiz API returned HTTP {response.status_code}: {details}"
