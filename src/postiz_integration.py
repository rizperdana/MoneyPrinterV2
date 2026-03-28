"""
Postiz integration for MoneyPrinterV2.

Replaces post_bridge_integration.py with Postiz self-hosted publishing.
"""

import os
from typing import Callable, Optional

from classes.Postiz import Postiz, PostizClientError
from config import get_postiz_config
from status import info, question, success, warning


def resolve_postiz_integrations(
    client: Postiz,
    platforms: list[str],
    interactive: bool,
    prompt_fn: Optional[Callable[[str], str]] = None,
) -> dict[str, dict]:
    """
    Resolve Postiz integrations for the requested platforms.

    Args:
        client: Postiz client instance.
        platforms: Target platform names (e.g., ["youtube", "tiktok"]).
        interactive: Whether prompting is allowed.
        prompt_fn: Optional prompt function override for tests.

    Returns:
        Dict mapping platform -> integration dict.
    """
    integration_map = client.find_integrations(platforms)

    for platform in platforms:
        key = platform.strip().lower()
        if key not in integration_map:
            warning(f"No connected Postiz integration found for {platform}.")
        else:
            integration = integration_map[key]
            profile = integration.get("profile", "?")
            info(f"Found Postiz integration for {platform}: @{profile}")

    return integration_map


def maybe_publish_via_postiz(
    video_path: str,
    title: str,
    description: str = "",
    interactive: bool = False,
    prompt_fn: Optional[Callable[[str], str]] = None,
) -> Optional[bool]:
    """
    Publish a video to social platforms via Postiz.

    Args:
        video_path: Path to generated video file.
        title: Video title.
        description: Video description / caption.
        interactive: Whether prompting is allowed.
        prompt_fn: Optional prompt function override for tests.

    Returns:
        True when published, False when attempted and failed,
        None when skipped.
    """
    config = get_postiz_config()

    if not config["enabled"]:
        return None

    if not config["api_key"]:
        warning(
            "Postiz is enabled but no API key is configured. "
            "Set postiz.api_key or POSTIZ_API_KEY."
        )
        return None

    if not os.path.exists(video_path):
        warning(f"Cannot publish because the video file was not found: {video_path}")
        return False

    platforms = config["platforms"]
    if not platforms:
        warning("Postiz is enabled but no platforms are configured.")
        return None

    if prompt_fn is None:
        prompt_fn = question

    if interactive:
        should_publish = config["auto_publish"]
        if not should_publish:
            platform_label = ", ".join(platforms)
            response = prompt_fn(
                f"Publish this video to {platform_label} via Postiz? (Yes/No): "
            ).strip().lower()
            should_publish = response in {"y", "yes"}
    else:
        if not config["auto_publish"]:
            info(
                "Postiz is enabled, but auto_publish is disabled. "
                "Skipping publish in cron mode."
            )
            return None
        should_publish = True

    if not should_publish:
        return None

    caption = description.strip() or title.strip()
    if not caption:
        caption = os.path.splitext(os.path.basename(video_path))[0]

    client = Postiz(
        api_key=config["api_key"],
        api_url=config["api_url"],
    )

    try:
        # Verify integrations exist before uploading
        integration_map = resolve_postiz_integrations(
            client=client,
            platforms=platforms,
            interactive=interactive,
            prompt_fn=prompt_fn,
        )
        if not integration_map:
            warning("No Postiz integrations were resolved. Skipping publish.")
            return None

        result = client.publish_video(
            video_path=video_path,
            title=title,
            description=caption,
            platforms=list(integration_map.keys()),
        )

        post_id = result.get("post", {}).get("id", "unknown")
        skipped = result.get("skipped_platforms", [])
        success(f"Published via Postiz (post ID: {post_id}).")
        if skipped:
            warning(f"Skipped platforms (no integration): {', '.join(skipped)}")
        return True

    except PostizClientError as exc:
        warning(f"Postiz publish failed: {exc}")
        return False
