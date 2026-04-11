"""
MoneyPrinterV2 — CLI Entry Point

Usage:
    python cli.py generate --account "channel123" --niche "space mysteries" --language en
    python cli.py serve --open
    python cli.py accounts list
"""

import os
import sys
import json

# Ensure src/ and project root are on the path
_project_root = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_project_root, "src")
for _p in [_project_root, _src_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

import click


@click.group()
def cli():
    """MoneyPrinterV2 — Automated YouTube Shorts pipeline."""
    pass


@cli.command()
@click.option("--account", required=True, help="Account nickname or UUID")
@click.option("--niche", required=True, help="Video topic niche")
@click.option("--language", default="English", help="Content language")
@click.option("--upload", is_flag=True, default=False, help="Upload after generation")
def generate(account, niche, language, upload):
    """Generate a video from a niche prompt."""
    from run_pipeline import run_pipeline

    result = run_pipeline(niche=niche, language=language, upload=upload)
    if result.get("video_path"):
        click.echo(f"✅ Video: {result['video_path']}")
    else:
        click.echo(f"❌ Failed: {result.get('error', 'Unknown error')}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--account", required=True, help="Account nickname or UUID")
@click.option("--file", "filepath", required=True, type=click.Path(exists=True), help="Video file path")
def upload(account, filepath):
    """Upload an existing video to YouTube."""
    from config import get_firefox_profile_path
    from classes.YouTube import YouTube

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
        success_flag, result = yt.upload_video()
        if success_flag:
            click.echo(f"✅ Uploaded: {result}")
        else:
            click.echo(f"❌ Upload failed: {result}", err=True)
            sys.exit(1)
    finally:
        if hasattr(yt, "_browser") and yt._browser:
            yt._browser.quit()


@cli.command()
@click.option("--account", required=True, help="Account nickname or UUID")
@click.option("--niche", required=True, help="Video topic niche")
@click.option("--interval", default=3600, help="Seconds between runs")
def run247(account, niche, interval):
    """Run 24/7 generation loop."""
    import time
    from run_pipeline import run_pipeline

    click.echo(f"🔄 Starting 24/7 mode. Niche: {niche}, Interval: {interval}s")
    while True:
        try:
            result = run_pipeline(niche=niche, language="English", upload=True)
            if result.get("video_path"):
                click.echo(f"✅ Generated: {result['video_path']}")
            else:
                click.echo(f"⚠️ Run failed: {result.get('error')}", err=True)
        except Exception as e:
            click.echo(f"❌ Error: {e}", err=True)
        click.echo(f"⏳ Sleeping {interval}s...")
        time.sleep(interval)


@cli.command()
@click.option("--account", required=True, help="Account nickname or UUID")
@click.option("--niches-file", required=True, type=click.Path(exists=True), help="File with niches (one per line)")
@click.option("--count", default=1, help="Videos per niche")
def batch(account, niches_file, count):
    """Batch generate videos from a niches file."""
    from run_pipeline import run_pipeline

    with open(niches_file) as f:
        niches = [line.strip() for line in f if line.strip()]

    click.echo(f"📦 Batch: {len(niches)} niches × {count} each = {len(niches) * count} videos")

    for niche in niches:
        for i in range(count):
            click.echo(f"\n{'='*50}\n🎬 Niche: {niche} ({i+1}/{count})")
            result = run_pipeline(niche=niche, language="English")
            if result.get("video_path"):
                click.echo(f"✅ {result['video_path']}")
            else:
                click.echo(f"❌ {result.get('error')}", err=True)


@cli.group()
def accounts():
    """Manage accounts."""
    pass


@accounts.command("list")
def accounts_list():
    """List all accounts."""
    from db import init_db, get_accounts

    init_db()
    accts = get_accounts()
    if not accts:
        click.echo("No accounts found.")
        return
    for a in accts:
        click.echo(f"  [{a['id']}] {a['platform']} — {a['username']}")


cli.add_command(accounts)


@cli.command()
@click.option("--port", default=8000, help="Server port")
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open browser on start")
def serve(port, host, open_browser):
    """Start the web UI."""
    import uvicorn
    import webbrowser
    import threading

    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    click.echo(f"🚀 Starting MoneyPrinterV2 on http://{host}:{port}")
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    cli()
