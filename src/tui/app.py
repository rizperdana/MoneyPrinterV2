"""
MoneyPrinterV2 TUI Application
Main entry point for the Textual-based Terminal User Interface
"""

import os
import sys
import asyncio

# Setup paths - app.py is in src/tui/, so go up 2 levels to get project root
_app_dir = os.path.dirname(os.path.abspath(__file__))  # src/tui
_project_root = os.path.dirname(os.path.dirname(_app_dir))  # project root
_src_dir = os.path.join(_project_root, "src")  # src/ directory

# Add both project root and src/ to path for legacy imports (from config, from db, etc.)
for _path in [_project_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Get absolute path for CSS
_css_path = os.path.join(_app_dir, "styles/dark.tcss")

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Static, Button
from textual import events
from typing import Optional

# Initialize database tables
from src.db import init_db

init_db()


class SidebarItem(Button):
    """A single item in the sidebar navigation."""

    def __init__(self, label: str, target: str, **kwargs):
        super().__init__(label, **kwargs)
        self.target = target


class Sidebar(Static):
    """Navigation sidebar for the TUI."""

    NAV_ITEMS = [
        ("📊 Dashboard", "dashboard"),
        ("🎬 Video Gen", "video_gen"),
        ("👤 Accounts", "accounts"),
        ("🐦 Twitter", "twitter"),
        ("💰 AFM", "afm"),
        ("📧 Outreach", "outreach"),
        ("⚙️ Settings", "settings"),
    ]

    BINDINGS = [
        Binding("g", "navigate_first()", "Nav", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static("NAVIGATE", classes="sidebar-header")
        for label, target in self.NAV_ITEMS:
            yield SidebarItem(label, target, variant="default", classes="nav-item")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle nav clicks."""
        button = event.button
        if hasattr(button, "target"):
            self.app.action_go_to(button.target)


class MoneyPrinterApp(App):
    """MoneyPrinterV2 Terminal User Interface."""

    CSS_PATH = _css_path
    TITLE = "MoneyPrinterV2"

    # Title bar shortcuts
    BINDINGS = [
        # Navigation shortcuts
        Binding("g d", "go_to('dashboard')", "Dashboard", show=True),
        Binding("g v", "go_to('video_gen')", "Video", show=True),
        Binding("g a", "go_to('accounts')", "Accounts", show=True),
        Binding("g t", "go_to('twitter')", "Twitter", show=True),
        Binding("g f", "go_to('afm')", "AFM", show=True),
        Binding("g o", "go_to('outreach')", "Outreach", show=True),
        Binding("g s", "go_to('settings')", "Settings", show=True),
        # Navigation within screen stack
        Binding("escape", "pop_screen_or_home()", "Back", show=True),
        # Quit
        Binding("q", "quit", "Quit", show=True),
        # Ctrl+C to stop pipeline (handled in on_key)
    ]

    # Screen name → import path mapping
    SCREEN_MODULES = {
        "dashboard": "src.tui.screens.dashboard",
        "video_gen": "src.tui.screens.video_gen",
        "accounts": "src.tui.screens.accounts",
        "twitter": "src.tui.screens.twitter",
        "afm": "src.tui.screens.afm",
        "outreach": "src.tui.screens.outreach",
        "settings": "src.tui.screens.settings",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._screen_cache: dict = {}
        self._install_screens()

    def _install_screens(self) -> None:
        """Pre-install all screens so push_screen works reliably."""
        for name in self.SCREEN_MODULES:
            self._load_screen(name)

    def _load_screen(self, name: str):
        """Load and cache a screen by name."""
        if name in self._screen_cache:
            return self._screen_cache[name]

        try:
            mod_path = self.SCREEN_MODULES[name]
            parts = mod_path.rsplit(".", 1)
            mod = __import__(mod_path, fromlist=[parts[1] if len(parts) > 1 else ""])
            # Get the screen class - name like "dashboard" → "DashboardScreen"
            class_name = (
                "".join(word.capitalize() for word in name.split("_")) + "Screen"
            )
            screen_cls = getattr(mod, class_name, None)
            if screen_cls is None:
                # Try exact case-insensitive match: "settings" matches "SettingsScreen"
                for attr_name in dir(mod):
                    if attr_name.lower() == name.lower() + "screen":
                        screen_cls = getattr(mod, attr_name)
                        break
            if screen_cls is None:
                # Last resort: look for any Screen subclass in the module
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name, None)
                    if (
                        attr
                        and isinstance(attr, type)
                        and issubclass(attr, Screen)
                        and attr_name.endswith("Screen")
                    ):
                        screen_cls = attr
                        break
            if screen_cls:
                instance = screen_cls()
                self._screen_cache[name] = instance
                self.install_screen(instance, name)
                return instance
        except Exception as e:
            print(f"Error loading screen {name}: {e}", file=sys.stderr)
        return None

    def compose(self) -> ComposeResult:
        """Create the main layout with sidebar + content area."""
        yield Header()
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")
            with Container(id="content-area"):
                # Initial screen will be pushed here
                pass
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app - push dashboard."""
        try:
            self.push_screen("dashboard")
        except Exception as e:
            self._handle_error("on_mount", e)

    def action_go_to(self, screen_name: str) -> None:
        """Navigate to a screen by name."""
        try:
            if screen_name not in self.SCREEN_MODULES:
                return
            # Load screen if not cached
            self._load_screen(screen_name)
            self.push_screen(screen_name)
        except Exception as e:
            self._handle_error(f"go_to({screen_name})", e)

    def action_navigate_first(self) -> None:
        """After 'g', wait for second key. Show navigation hint."""
        pass

    def action_pop_screen_or_home(self) -> None:
        """Pop current screen, or go to dashboard if at root."""
        try:
            screens = self.screen_stack
            if len(screens) > 1:
                self.pop_screen()
            else:
                # Already at root - navigate to dashboard
                self.push_screen("dashboard")
        except Exception as e:
            self._handle_error("pop_screen_or_home", e)

    # Track multi-key shortcuts
    _pending_key: Optional[str] = None

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard shortcuts."""
        # Ctrl+C - request pipeline stop
        if event.key == "ctrl_c":
            self._handle_ctrl_c()
            return

        # Two-key shortcuts: 'g' prefix → go_to
        # g+d, g+v, g+a, g+t, g+f, g+o, g+s
        key_map = {
            "d": "dashboard",
            "v": "video_gen",
            "a": "accounts",
            "t": "twitter",
            "f": "afm",
            "o": "outreach",
            "s": "settings",
        }

        # Handle 'g' prefix for navigation
        if event.key == "g":
            self._pending_key = "g"
            return

        # If we have a pending 'g', check for second key
        if self._pending_key == "g" and event.key in key_map:
            self.action_go_to(key_map[event.key])
            self._pending_key = None
            return

        # Clear pending key if not a valid combo
        self._pending_key = None

    def _handle_ctrl_c(self) -> None:
        """Handle Ctrl+C - stop pipeline and return to dashboard."""
        try:
            # Try to find and cancel pipeline in current video_gen screen
            current = self.screen
            if hasattr(current, "_pipeline") and current._pipeline:
                current._pipeline.cancel()
            # Pop back to dashboard
            while len(self.screen_stack) > 1:
                self.pop_screen()
        except Exception:
            pass

    def _handle_error(self, context: str, error: Exception) -> None:
        """Log errors to the current screen's log viewer if available."""
        error_msg = f"[red][ERROR][/red] {context}: {str(error)}"
        # Try to find a LogViewer in current screen
        try:
            current = self.screen
            if hasattr(current, "query_one"):
                try:
                    log = current.query_one("#log-viewer LogViewer", None)
                    if log:
                        log.write_entry(f"{context}: {str(error)}", "ERROR")
                    else:
                        log = current.query_one("LogViewer", None)
                        if log:
                            log.write_entry(f"{context}: {str(error)}", "ERROR")
                except Exception:
                    pass
        except Exception:
            pass

    def on_screen_layout(self, event) -> None:
        """Handle screen layout changes with error handling."""
        try:
            pass  # Layout updates handled by Textual
        except Exception as e:
            self._handle_error("screen_layout", e)


# Entry point
def main():
    """Launch the TUI application."""
    app = MoneyPrinterApp()
    app.run()


if __name__ == "__main__":
    main()
