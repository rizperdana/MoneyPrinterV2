"""
MoneyPrinterV2 - Non-Interactive Pipeline Runner
Runs the full YouTube Shorts pipeline end-to-end without user input.

Usage:
    python src/run_pipeline.py [--niche "science facts"] [--language English] [--upload]
    python src/run_pipeline.py [--niche "science facts"] [--postiz] [--postiz-url URL] [--postiz-key KEY]

Environment:
    CLIPROXY_API_KEY  - Required for LLM text generation
    GEMINI_API_KEY    - Required for AI image generation (optional, falls back to placeholders)
    POSTIZ_API_KEY    - Postiz API key (alternative to --postiz-key)
    POSTIZ_API_URL    - Postiz instance URL (alternative to --postiz-url)
"""

import os
import sys
import json
import argparse
import time

# Load .env before other imports
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *
from status import *
from llm_provider import select_model
from config import get_ollama_model
from classes.YouTube import YouTube
from classes.Tts import TTS


def run_pipeline(
    niche: str,
    language: str,
    upload: bool = False,
    headless: bool = True,
    postiz_enabled: bool = False,
    postiz_url: str = "",
    postiz_key: str = "",
    postiz_platforms: list = None,
) -> dict:
    """
    Run the full video generation pipeline non-interactively.

    Args:
        niche: Video topic niche (e.g., "interesting science facts")
        language: Content language (e.g., "English")
        upload: Whether to upload to YouTube after generation
        headless: Run Firefox in headless mode
        postiz_url: Postiz instance URL (overrides config)
        postiz_key: Postiz API key (overrides config)
        postiz_platforms: Target platforms for Postiz (overrides config)

    Returns:
        dict with keys: topic, title, description, video_path, uploaded, postiz
    """
    result = {
        "topic": None,
        "title": None,
        "description": None,
        "video_path": None,
        "uploaded": False,
        "postiz": None,
        "error": None,
    }

    try:
        # Select LLM model
        model = get_ollama_model()
        if model:
            select_model(model)
            info(f"Using LLM model: {model}")

        # Initialize TTS
        tts = TTS()

        # Initialize YouTube (skip browser if not uploading)
        fp_profile = get_firefox_profile_path()

        if upload and fp_profile and os.path.isdir(fp_profile):
            info("Initializing YouTube with Firefox profile for upload...")
            youtube = YouTube(
                account_uuid="auto-pipeline",
                account_nickname="Auto Pipeline",
                fp_profile_path=fp_profile,
                niche=niche,
                language=language,
            )
        else:
            if upload:
                warning("No valid Firefox profile configured. Skipping upload.")
                upload = False

            # Create YouTube instance without browser
            youtube = YouTube.__new__(YouTube)
            youtube._account_uuid = "auto-pipeline"
            youtube._account_nickname = "Auto Pipeline"
            youtube._niche = niche
            youtube._language = language
            youtube.images = []
            youtube.subject = None
            youtube.script = None
            youtube.metadata = None
            youtube.image_prompts = None
            youtube.tts_path = None
            youtube.video_path = None

        # Step 1: Generate Topic
        info("Step 1/7: Generating topic...")
        topic = youtube.generate_topic()
        result["topic"] = topic
        success(f"Topic: {topic}")

        # Step 2: Generate Script
        info("Step 2/7: Generating script...")
        script = youtube.generate_script()
        success(f"Script: {len(script)} chars")

        # Step 3: Generate Metadata
        info("Step 3/7: Generating metadata...")
        metadata = youtube.generate_metadata()
        result["title"] = metadata["title"]
        result["description"] = metadata["description"]
        result["tags"] = metadata.get("tags", [])
        success(f"Title: {metadata['title']}")
        success(f"Tags: {len(result['tags'])} SEO tags")

        # Step 4: Generate Image Prompts
        info("Step 4/7: Generating image prompts...")
        prompts = youtube.generate_prompts()
        success(f"Generated {len(prompts)} image prompts")

        # Step 5: Generate Images
        info("Step 5/7: Generating images...")
        for i, prompt in enumerate(prompts):
            img_path = youtube.generate_image(prompt, delay_between=30)
            if img_path:
                success(f"Image {i+1}/{len(prompts)}: {os.path.basename(img_path)}")
            else:
                warning(f"Image {i+1}/{len(prompts)}: FAILED (will use placeholder)")
            # 30s delay is handled inside generate_image() after each success

        # Fill remaining slots with placeholders if any images failed
        if len(youtube.images) < len(prompts):
            missing = len(prompts) - len(youtube.images)
            warning(f"{missing} images failed. Generating {missing} placeholders.")
            _generate_placeholder_images(youtube, missing, offset=len(youtube.images))

        if len(youtube.images) == 0:
            error("No images generated. Cannot create video.")
            result["error"] = "No images generated"
            return result

        success(f"Total images: {len(youtube.images)}")

        # Step 6: TTS
        info("Step 6/7: Generating text-to-speech...")
        youtube.generate_script_to_speech(tts)
        success(f"TTS: {youtube.tts_path}")

        # Step 7: Combine
        info("Step 7/7: Combining video...")
        path = youtube.combine()
        youtube.video_path = os.path.abspath(path)
        result["video_path"] = youtube.video_path
        size_mb = os.path.getsize(youtube.video_path) / 1024 / 1024
        success(f"Video: {youtube.video_path} ({size_mb:.1f} MB)")

        # Upload (optional)
        if upload:
            info("Uploading to YouTube...")
            try:
                youtube.upload_video()
                result["uploaded"] = True
                result["youtube_url"] = getattr(youtube, "uploaded_video_url", None)
                success(f"Video uploaded successfully! {result.get('youtube_url', '')}")
            except Exception as e:
                error(f"Upload failed: {e}")
                result["error"] = f"Upload failed: {e}"

        # Postiz publishing (optional, triggered by --postiz flag or --postiz-key)
        postiz_enabled = bool(postiz_key) or bool(os.environ.get("POSTIZ_API_KEY", ""))
        if postiz_enabled:
            info("Publishing via Postiz...")
            try:
                from classes.Postiz import Postiz, PostizClientError

                url = postiz_url or os.environ.get("POSTIZ_API_URL", "https://api.postiz.com")
                key = postiz_key or os.environ.get("POSTIZ_API_KEY", "")
                platforms = postiz_platforms or ["youtube", "tiktok"]

                client = Postiz(api_key=key, api_url=url)

                # Verify integrations
                integration_map = client.find_integrations(platforms)
                if not integration_map:
                    warning(f"No Postiz integrations found for: {', '.join(platforms)}")
                    result["postiz"] = {"status": "skipped", "reason": "no integrations"}
                else:
                    for p, integ in integration_map.items():
                        info(f"Postiz integration: {p} -> @{integ.get('profile', '?')}")

                    desc = result.get("description") or result.get("title") or ""
                    postiz_result = client.publish_video(
                        video_path=youtube.video_path,
                        title=result["title"] or "Untitled",
                        description=desc,
                        platforms=list(integration_map.keys()),
                    )
                    post_id = postiz_result.get("post", {}).get("id", "unknown")
                    success(f"Published via Postiz (post ID: {post_id})")
                    result["postiz"] = {
                        "status": "published",
                        "post_id": post_id,
                        "platforms": list(integration_map.keys()),
                        "skipped": postiz_result.get("skipped_platforms", []),
                    }
            except PostizClientError as e:
                warning(f"Postiz publish failed: {e}")
                result["postiz"] = {"status": "failed", "error": str(e)}
            except Exception as e:
                warning(f"Postiz publish error: {e}")
                result["postiz"] = {"status": "failed", "error": str(e)}

    except Exception as e:
        error(f"Pipeline failed: {e}")
        result["error"] = str(e)
        import traceback
        traceback.print_exc()

    return result


def _generate_placeholder_images(youtube, count: int, offset: int = 0):
    """Generate colored placeholder images when AI image gen is unavailable."""
    from PIL import Image, ImageDraw, ImageFont

    colors = [
        (30, 60, 114), (42, 82, 152), (50, 100, 180),
        (60, 120, 200), (70, 140, 220), (80, 160, 240),
        (90, 180, 250), (100, 200, 255),
    ]
    labels = [
        "Scene 1", "Scene 2", "Scene 3", "Scene 4",
        "Scene 5", "Scene 6", "Scene 7", "Scene 8",
    ]

    for i in range(min(count, len(colors))):
        idx = offset + i
        img = Image.new("RGB", (1080, 1920), colors[i % len(colors)])
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except Exception:
            font = ImageFont.load_default()

        label = labels[i % len(labels)]
        bbox = draw.textbbox((0, 0), label, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((1080 - w) // 2, (1920 - h) // 2), label, fill="white", font=font)

        path = os.path.join(ROOT_DIR, ".mp", f"placeholder_{idx}.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path)
        youtube.images.append(path)


def main():
    parser = argparse.ArgumentParser(description="MoneyPrinterV2 Non-Interactive Pipeline")
    parser.add_argument("--niche", default="interesting science facts", help="Video niche/topic")
    parser.add_argument("--language", default="English", help="Content language")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube after generation")
    parser.add_argument("--no-headless", action="store_true", help="Show Firefox browser")
    parser.add_argument("--postiz", action="store_true", help="Publish via Postiz after generation")
    parser.add_argument("--postiz-url", default="", help="Postiz instance URL (default: https://api.postiz.com)")
    parser.add_argument("--postiz-key", default="", help="Postiz API key (or set POSTIZ_API_KEY env var)")
    parser.add_argument("--postiz-platforms", default="", help="Comma-separated platforms (default: youtube,tiktok)")
    args = parser.parse_args()

    # Parse Postiz platforms
    postiz_platforms = None
    if args.postiz_platforms:
        postiz_platforms = [p.strip() for p in args.postiz_platforms.split(",") if p.strip()]

    info("=" * 50)
    info("MoneyPrinterV2 - Automated Pipeline")
    info("=" * 50)

    result = run_pipeline(
        niche=args.niche,
        language=args.language,
        upload=args.upload,
        headless=not args.no_headless,
        postiz_url=args.postiz_url,
        postiz_key=args.postiz_key,
        postiz_platforms=postiz_platforms,
    )

    print("\n" + "=" * 50)
    if result["video_path"]:
        success(f"Done! Video: {result['video_path']}")
    else:
        error(f"Failed: {result.get('error', 'Unknown error')}")

    # Save result metadata
    meta_path = os.path.join(ROOT_DIR, ".mp", "last_run.json")
    with open(meta_path, "w") as f:
        json.dump(result, f, indent=2)
    info(f"Metadata saved to: {meta_path}")


if __name__ == "__main__":
    main()
