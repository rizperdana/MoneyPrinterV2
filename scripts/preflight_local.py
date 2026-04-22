#!/usr/bin/env python3
import os
import sys
from typing import Tuple

import requests

# Add project root to path for imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def check_url(url: str, timeout: int = 3) -> Tuple[bool, str]:
    try:
        response = requests.get(url, timeout=timeout)
        return True, f"HTTP {response.status_code}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    from src.config import (
        get_stt_provider,
        get_imagemagick_path,
        get_firefox_profile_path,
        get_llm_base_url,
    )

    stt_provider = get_stt_provider()
    imagemagick_path = get_imagemagick_path()
    firefox_profile = get_firefox_profile_path()
    llm_base_url = get_llm_base_url()

    failures = 0

    stt_provider = str(stt_provider).lower()

    ok(f"stt_provider={stt_provider}")

    if imagemagick_path and os.path.exists(imagemagick_path):
        ok(f"imagemagick_path exists: {imagemagick_path}")
    else:
        warn(
            "imagemagick_path is not set to a valid executable path. "
            "MoviePy subtitle rendering may fail."
        )

    if firefox_profile:
        if os.path.isdir(firefox_profile):
            ok(f"firefox_profile exists: {firefox_profile}")
        else:
            warn(f"firefox_profile does not exist: {firefox_profile}")
    else:
        warn("firefox_profile is empty. Twitter/YouTube automation requires this.")

    # cliproxyapi (LLM)
    cliproxy_base = str(llm_base_url).rstrip("/") if llm_base_url else "http://localhost:8317/v1"
    reachable, detail = check_url(f"{cliproxy_base}/models", timeout=5)
    if not reachable:
        fail(f"cliproxyapi is not reachable at {cliproxy_base}: {detail}")
        failures += 1
    else:
        ok(f"cliproxyapi reachable at {cliproxy_base}")
        try:
            import httpx

            headers = {}
            api_key = os.environ.get("CLIPROXY_API_KEY", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = requests.get(f"{cliproxy_base}/models", headers=headers, timeout=5)
            data = resp.json()
            models = [m.get("id") for m in data.get("data", [])]
            if models:
                ok(f"cliproxyapi models available: {', '.join(models[:10])}")
            else:
                warn("No models returned from cliproxyapi.")
        except Exception as exc:
            warn(f"Could not validate cliproxyapi model list: {exc}")

    if stt_provider == "local_whisper":
        try:
            import faster_whisper  # noqa: F401

            ok("faster-whisper is installed")
        except Exception as exc:
            fail(f"faster-whisper is not importable: {exc}")
            failures += 1

    if failures:
        print("")
        print(f"Preflight completed with {failures} blocking issue(s).")
        return 1

    print("")
    print("Preflight passed. Local setup looks ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
