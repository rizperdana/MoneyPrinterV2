"""
MoneyPrinterV2 - Non-Interactive Pipeline Runner
Runs the full YouTube Shorts pipeline end-to-end without user input.

Usage:
    python src/run_pipeline.py [--niche "science facts"] [--locale en-US] [--upload]

Environment:
    CLIPROXY_API_KEY  - Required for LLM text generation
    GEMINI_API_KEY    - Optional for AI image generation (falls back to placeholders)
"""

import os
import sys
import json
import argparse

from dotenv import load_dotenv

# Add project root and src to path (same pattern as api/main.py)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.dirname(os.path.abspath(__file__))
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Load .env before other imports that need env vars
load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)

from src.config import ROOT_DIR, get_default_model
from src.status import error, success, info, warning
from src.llm_provider import select_model
from src.classes.YouTube import YouTube
from src.classes.Tts import TTS
from src.db import get_existing_videos_for_niche
from src.research import extract_facts


def run_pipeline(
    niche: str,
    locale: str = "en-US",
    upload: bool = False,
    headless: bool = True,
    audience: str = "general",
) -> dict:
    """
    Run the full video generation pipeline non-interactively.

    Args:
        niche: Video topic niche (e.g., "interesting science facts")
        locale: BCP-47 locale code (e.g., "en-US", "id-ID")
        upload: Whether to upload to YouTube after generation
        headless: Run Firefox in headless mode
        audience: Target audience level (beginner, general, intermediate, expert)

    Returns:
        dict with keys: topic, title, description, video_path, uploaded, error
    """
    result = {
        "topic": None,
        "title": None,
        "description": None,
        "video_path": None,
        "uploaded": False,
        "error": None,
    }

    try:
        # Select LLM model
        model = get_default_model()
        if model:
            select_model(model)
            info(f"Using LLM model: {model}")

        # Initialize TTS
        tts = TTS(locale=locale)

        # Initialize YouTube
        youtube = YouTube.__new__(YouTube)
        youtube._account_uuid = "auto-pipeline"
        youtube._account_nickname = "Auto Pipeline"
        youtube._niche = niche
        youtube._locale = locale
        youtube._audience = audience
        youtube.images = []
        youtube.subject = None
        youtube.script = None
        youtube.metadata = None
        youtube.image_prompts = None
        youtube.tts_path = None
        youtube.video_path = None
        youtube.extracted_facts = None

        # Query existing videos for this niche (to avoid duplicates)
        existing_videos = []
        try:
            existing_videos = get_existing_videos_for_niche(niche, limit=50)
            if existing_videos:
                info(f" => Loaded {len(existing_videos)} existing videos for dedup context")
        except Exception as e:
            warning(f"Could not load existing videos: {e}")

        # Step 1: Generate Topic
        info("Step 1/7: Generating topic...")

        # Research first, then extract facts before topic generation
        research_text = youtube._research_trending_topics()
        youtube.extracted_facts = extract_facts(research_text, niche)
        info(f" => Extracted facts: {youtube.extracted_facts.get('extraction_note', 'none')}")

        topic = youtube.generate_topic(
            existing_videos=existing_videos if existing_videos else None,
            extracted_facts=youtube.extracted_facts,
        )
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
                success(f"Image {i + 1}/{len(prompts)}: {os.path.basename(img_path)}")
            else:
                warning(f"Image {i + 1}/{len(prompts)}: FAILED (will use placeholder)")
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

        if upload:
            info("Uploading to YouTube...")
            try:
                from src.youtube_oauth import get_access_token
                from src.youtube_api import youtubeApiUpload

                oauth_token = get_access_token("default")
                if oauth_token:
                    upload_result = youtubeApiUpload(
                        video_path=youtube.video_path,
                        title=result.get("title", "Untitled"),
                        description=result.get("description", ""),
                        tags=result.get("tags", []),
                        oauth_token=oauth_token,
                        account_id="default",
                        progress_callback=None,
                    )
                    result["uploaded"] = True
                    result["youtube_url"] = upload_result.get("url")
                    success(f"Uploaded: {result['youtube_url']}")
                else:
                    result["uploaded"] = False
                    warning("No OAuth token available. Skipping upload.")
            except Exception as e:
                error(f"Upload failed: {e}")
                result["error"] = f"Upload failed: {e}"

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
        (30, 60, 114),
        (42, 82, 152),
        (50, 100, 180),
        (60, 120, 200),
        (70, 140, 220),
        (80, 160, 240),
        (90, 180, 250),
        (100, 200, 255),
    ]
    labels = [
        "Scene 1",
        "Scene 2",
        "Scene 3",
        "Scene 4",
        "Scene 5",
        "Scene 6",
        "Scene 7",
        "Scene 8",
    ]

    for i in range(min(count, len(colors))):
        idx = offset + i
        img = Image.new("RGB", (1080, 1920), colors[i % len(colors)])
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60
            )
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
    parser = argparse.ArgumentParser(
        description="MoneyPrinterV2 Non-Interactive Pipeline"
    )
    parser.add_argument(
        "--niche", default="interesting science facts", help="Video niche/topic"
    )
    parser.add_argument("--locale", default="en-US", help="BCP-47 locale code (e.g., en-US, id-ID)")
    parser.add_argument(
        "--upload", action="store_true", help="Upload to YouTube after generation"
    )
    parser.add_argument(
        "--no-headless", action="store_true", help="Show Firefox browser"
    )
    args = parser.parse_args()

    info("=" * 50)
    info("MoneyPrinterV2 - Automated Pipeline")
    info("=" * 50)

    result = run_pipeline(
        niche=args.niche,
        locale=args.locale,
        upload=args.upload,
        headless=not args.no_headless,
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
