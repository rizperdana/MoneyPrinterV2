"""
MoneyPrinterV2 - Main Entry Point

Launches the Terminal User Interface (TUI) for managing YouTube Shorts,
Twitter bots, Affiliate Marketing, and Outreach tasks.

Usage:
    python src/main.py          # Launch TUI
    python -m src.tui.app       # Alternative TUI launch
"""

import os
import sys

# Ensure project root and src/ are in path for imports
_app_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_app_dir)
_src_dir = _app_dir

for _path in [_project_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)


def main():
    """Launch the MoneyPrinterV2 TUI application."""
    # Import and run the TUI
    from src.tui.app import MoneyPrinterApp

    app = MoneyPrinterApp()
    app.run()


if __name__ == "__main__":
    main()
