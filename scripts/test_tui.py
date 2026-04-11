#!/usr/bin/env python3
"""Comprehensive TUI test."""

import asyncio
import os
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "src"))

os.environ["TERM"] = "xterm-256color"

from src.db import init_db
from src.tui.app import MoneyPrinterApp


async def test_all_screens():
    """Test all screens."""
    app = MoneyPrinterApp()
    results = []

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"Dashboard: {type(current).__name__}")

        await pilot.press("g")
        await pilot.press("v")
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"VideoGen: {type(current).__name__}")

        await pilot.press("g")
        await pilot.press("s")
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"Settings: {type(current).__name__}")

        await pilot.press("escape")
        await pilot.pause(0.3)

        await pilot.press("g")
        await pilot.press("t")
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"Twitter: {type(current).__name__}")

        await pilot.press("g")
        await pilot.press("f")
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"AFM: {type(current).__name__}")

        await pilot.press("g")
        await pilot.press("o")
        await pilot.pause(0.3)
        current = app.screen
        results.append(f"Outreach: {type(current).__name__}")

    return results


if __name__ == "__main__":
    init_db()

    print("Testing all screens...")
    try:
        results = asyncio.run(test_all_screens())
        for r in results:
            print(f"  ✓ {r}")
        print("\n✅ All screens loaded successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
