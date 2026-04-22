"""
MoneyPrinterV2 — Unified CLI Entry Point

Usage:
    python src/main.py --help                    # Show all commands
    python src/main.py serve                      # Start web UI
    python src/main.py serve --open               # Start web UI and open browser
    python src/main.py generate --niche "topic"   # Generate video
    python src/main.py accounts list              # List accounts
"""

import os
import sys
import click

# Ensure project root and src/ are in path for imports
_app_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_app_dir)
_src_dir = _app_dir

for _path in [_project_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from dotenv import load_dotenv

load_dotenv(os.path.join(_project_root, ".env"))


@click.group()
def cli():
    """MoneyPrinterV2 — Automated video creation and social media publishing."""
    pass


# === Web Server ===


@cli.command("serve")
@click.option("--port", default=8701, help="Server port")
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option(
    "--open", "open_browser", is_flag=True, default=False, help="Open browser on start"
)
def serve(port, host, open_browser):
    """Start the web UI."""
    import uvicorn
    import webbrowser
    import threading

    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    click.echo(f"🚀 Starting MoneyPrinterV2 on http://{host}:{port}")
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


# === Generate ===


@cli.command("generate")
@click.option("--account", default="auto", help="Account nickname/UUID or 'auto'")
@click.option("--niche", required=True, help="Video topic niche")
@click.option("--language", default="English", help="Content language")
@click.option("--upload", is_flag=True, default=False, help="Upload after generation")
@click.option("--for-kids", is_flag=True, default=False, help="Content for kids")
def generate(account, niche, language, upload, for_kids):
    """Generate a video from a niche prompt."""
    from src.run_pipeline import run_pipeline

    click.echo(f"🎬 Generating: {niche} (language: {language})")
    result = run_pipeline(niche=niche, language=language, upload=upload)
    if result.get("video_path"):
        click.echo(f"✅ Video: {result['video_path']}")
    else:
        click.echo(f"❌ Failed: {result.get('error', 'Unknown error')}", err=True)
        sys.exit(1)


# === Upload ===


@cli.command("upload")
@click.option("--account", required=True, help="Account nickname or UUID")
@click.option(
    "--file",
    "filepath",
    required=True,
    type=click.Path(exists=True),
    help="Video file path",
)
def upload(account, filepath):
    """Upload an existing video to YouTube."""
    from src.config import get_firefox_profile_path
    from src.classes.YouTube import YouTube

    fp_profile = get_firefox_profile_path()
    yt = YouTube(
        account_uuid=account,
        account_nickname=account,
        fp_profile_path=fp_profile,
        niche="",
        language="English",
    )
    yt.video_path = os.path.abspath(filepath)
    try:
        from src.youtube_oauth import get_access_token
        from src.youtube_api import youtubeApiUpload

        oauth_token = get_access_token("default")
        if not oauth_token:
            click.echo("Error: No OAuth token. Link YouTube account first.")
            return
        try:
            upload_result = youtubeApiUpload(
                video_path=os.path.abspath(filepath),
                title="Untitled",  # CLI doesn't have metadata
                description="",
                tags=[],
                oauth_token=oauth_token,
                account_id="default",
                progress_callback=None,
            )
            if upload_result and upload_result.get("url"):
                success_flag = True
                result = upload_result["url"]
            else:
                success_flag = False
                result = "Upload returned no URL"
        except Exception as e:
            success_flag = False
            result = str(e)

        if success_flag:
            click.echo(f"✅ Uploaded: {result}")
        else:
            click.echo(f"❌ Upload failed: {result}", err=True)
            sys.exit(1)
    finally:
        if hasattr(yt, "_browser") and yt._browser:
            yt._browser.quit()


# === 24/7 ===


@cli.command("run247")
@click.option("--account", default="auto", help="Account nickname or UUID or 'auto'")
@click.option("--niche", required=True, help="Video topic niche")
@click.option("--language", default="English", help="Content language")
@click.option("--interval", default=3600, help="Seconds between runs")
@click.option("--upload", is_flag=True, default=True, help="Upload after generation")
def run247(account, niche, language, interval, upload):
    """Run 24/7 generation loop."""
    import time
    from src.run_pipeline import run_pipeline

    click.echo(f"🔄 Starting 24/7 mode. Niche: {niche}, Interval: {interval}s")
    while True:
        try:
            result = run_pipeline(niche=niche, language=language, upload=upload)
            if result.get("video_path"):
                click.echo(f"✅ Generated: {result['video_path']}")
            else:
                click.echo(f"⚠️ Run failed: {result.get('error')}", err=True)
        except Exception as e:
            click.echo(f"❌ Error: {e}", err=True)
        click.echo(f"⏳ Sleeping {interval}s...")
        time.sleep(interval)


# === Batch ===


@cli.command("batch")
@click.option("--account", default="auto", help="Account nickname or UUID or 'auto'")
@click.option(
    "--niches-file",
    required=True,
    type=click.Path(exists=True),
    help="File with niches (one per line)",
)
@click.option("--count", default=1, help="Videos per niche")
@click.option("--language", default="English", help="Content language")
def batch(account, niches_file, count, language):
    """Batch generate videos from a niches file."""
    from src.run_pipeline import run_pipeline

    with open(niches_file) as f:
        niches = [line.strip() for line in f if line.strip()]

    click.echo(
        f"📦 Batch: {len(niches)} niches × {count} each = {len(niches) * count} videos"
    )

    for niche in niches:
        for i in range(count):
            click.echo(f"\n{'=' * 50}\n🎬 Niche: {niche} ({i + 1}/{count})")
            result = run_pipeline(niche=niche, language=language)
            if result.get("video_path"):
                click.echo(f"✅ {result['video_path']}")
            else:
                click.echo(f"❌ {result.get('error')}", err=True)


# === Accounts ===


@cli.group("accounts")
def accounts():
    """Manage accounts."""
    pass


@accounts.command("list")
def accounts_list():
    """List all accounts."""
    from src.db import init_db, get_accounts
    from src.cache import get_accounts as get_cache_accounts
    import json

    init_db()

    # Get from DB
    db_accounts = get_accounts()

    # Get from cache files
    yt_accounts = get_cache_accounts("youtube")
    tw_accounts = get_cache_accounts("twitter")

    if not db_accounts and not yt_accounts and not tw_accounts:
        click.echo("No accounts found.")
        return

    click.echo("📋 Accounts:")

    for a in yt_accounts:
        click.echo(f"  • youtube: {a.get('nickname', a.get('id', 'unknown'))}")
    for a in tw_accounts:
        click.echo(f"  • twitter: {a.get('nickname', a.get('id', 'unknown'))}")
    for a in db_accounts:
        click.echo(f"  • {a['platform']}: {a['username']}")


if __name__ == "__main__":
    cli()
