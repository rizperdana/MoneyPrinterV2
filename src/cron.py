# RUN THIS N AMOUNT OF TIMES
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env so CLIPROXY_API_KEY and other vars are available in subprocess
load_dotenv(Path(__file__).parent.parent / ".env")

from status import error, success, info, warning
from cache import get_accounts
from config import get_verbose
from classes.Twitter import Twitter
from classes.YouTube import YouTube
from src.youtube_oauth import get_access_token
from src.youtube_api import youtubeApiUpload
from llm_provider import select_model
from tracker import (
    record_attempt,
    record_uploading,
    record_success,
    record_failure,
    is_topic_used,
    get_recent_topics,
)

try:
    from classes.Tts import TTS

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    TTS = None


def main():
    """Main function to post content to Twitter or upload videos to YouTube.

    This function determines its operation based on command-line arguments:
    - If the purpose is "twitter", it initializes a Twitter account and posts a message.
    - If the purpose is "youtube", it initializes a YouTube account, generates a video with TTS, and uploads it.

    Command-line arguments:
        sys.argv[1]: A string indicating the purpose, either "twitter" or "youtube".
        sys.argv[2]: A string representing the account UUID.

    The function also handles verbose output based on user settings and reports success or errors as appropriate.

    Args:
        None. The function uses command-line arguments accessed via sys.argv.

    Returns:
        None. The function performs operations based on the purpose and account UUID and does not return any value."""
    purpose = str(sys.argv[1])
    account_id = str(sys.argv[2])
    model = str(sys.argv[3]) if len(sys.argv) > 3 else None

    if model:
        select_model(model)
    else:
        error("No LLM model specified. Pass model name as third argument.")
        sys.exit(1)

    verbose = get_verbose()

    if purpose == "twitter":
        accounts = get_accounts("twitter")

        if not account_id:
            error("Account UUID cannot be empty.")

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Initializing Twitter...")
                twitter = Twitter(
                    acc["id"], acc["nickname"], acc["firefox_profile"], acc["topic"]
                )
                twitter.post()
                if verbose:
                    success("Done posting.")
                break
    elif purpose == "youtube":
        if not TTS_AVAILABLE:
            error("TTS not available - install kittentts")
            sys.exit(1)

        tts = TTS()

        accounts = get_accounts("youtube")

        if not account_id:
            error("Account UUID cannot be empty.")

        for acc in accounts:
            if acc["id"] == account_id:
                if verbose:
                    info("Initializing YouTube...")
                youtube = YouTube(
                    acc["id"],
                    acc["nickname"],
                    acc["firefox_profile"],
                    acc["niche"],
                    locale=acc["locale"],
                )

                # Get recent topics for LLM dedup context
                recent_topics = get_recent_topics(acc["id"], limit=20)
                if recent_topics and verbose:
                    info(
                        f" => {len(recent_topics)} recent topics loaded for dedup context"
                    )

                # Generate the video (topic generation happens inside)
                youtube.generate_video(tts)

                # Check if the generated topic is a duplicate
                if hasattr(youtube, "subject") and is_topic_used(
                    acc["id"], youtube.subject
                ):
                    warning(
                        f"Generated topic is a duplicate: {youtube.subject[:60]}..."
                    )
                    warning("Skipping this run. Try again later.")
                    sys.exit(0)

                # Record attempt in tracker
                upload_id = record_attempt(
                    account_id=acc["id"],
                    account_name=acc["nickname"],
                    niche=acc["niche"],
                    topic=youtube.subject if hasattr(youtube, "subject") else "",
                    title=youtube.metadata.get("title", "")
                    if hasattr(youtube, "metadata")
                    else "",
                    description=youtube.metadata.get("description", "")
                    if hasattr(youtube, "metadata")
                    else "",
                    tags=youtube.metadata.get("tags", [])
                    if hasattr(youtube, "metadata")
                    else [],
                    video_path=youtube.video_path
                    if hasattr(youtube, "video_path")
                    else "",
                )

                # Mark as uploading
                record_uploading(upload_id)

                # Upload (OAuth-based)
                oauth_token = get_access_token(youtube._account_nickname)
                if not oauth_token:
                    upload_success = False
                    upload_result = "No OAuth token"
                else:
                    try:
                        upload_api_result = youtubeApiUpload(
                            video_path=youtube.video_path,
                            title=result.get("title", "Untitled") if result else "Untitled",
                            description=result.get("description", "") if result else "",
                            tags=result.get("tags", []) if result else [],
                            oauth_token=oauth_token,
                            account_id=youtube._account_nickname,
                            progress_callback=None,
                        )
                        upload_success = bool(upload_api_result and upload_api_result.get("url"))
                        upload_result = upload_api_result.get("url", "") if upload_api_result else ""
                    except Exception as e:
                        upload_success = False
                        upload_result = str(e)

                if upload_success:
                    # Record success
                    record_success(upload_id, upload_result)
                    if verbose:
                        success(f"Uploaded Short: {upload_result}")
                    maybe_crosspost_youtube_short(
                        video_path=youtube.video_path,
                        title=youtube.metadata.get("title", ""),
                        interactive=False,
                    )
                else:
                    # Record failure
                    record_failure(upload_id, upload_result)
                    warning(f"YouTube upload failed: {upload_result}")
                    warning("Skipping Post Bridge cross-post.")
                break
    else:
        error("Invalid Purpose, exiting...")
        sys.exit(1)


if __name__ == "__main__":
    main()
