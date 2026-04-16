"""
MoneyPrinterV2 TUI Application
Main entry point for the Textual-based Terminal User Interface.

Layout: Header + [Sidebar | Content Area] + JobTicker
Navigation: Dashboard uses switch_screen; all others use push_screen.
"""

import os
import sys

# Setup paths — app.py is in src/tui/, so go up 2 levels to get project root
_app_dir = os.path.dirname(os.path.abspath(__file__))  # src/tui
_project_root = os.path.dirname(os.path.dirname(_app_dir))  # project root
_src_dir = os.path.join(_project_root, "src")  # src/ directory

# Add both project root and src/ to path for legacy imports
for _path in [_project_root, _src_dir]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Absolute path for CSS
_css_path = os.path.join(_app_dir, "styles", "app.tcss")

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual import events
from typing import Optional

# Initialize database tables
from src.db import init_db

init_db()

# Import widgets
from src.tui.widgets.sidebar import Sidebar
from src.tui.widgets.job_ticker import JobTicker

# Import events
from src.tui.events import (
    StepStarted,
    StepProgressed,
    StepCompleted,
    StepFailed,
    LogLine,
    JobCompleted,
    JobFailed,
    LibraryChanged,
)


class MoneyPrinterApp(App):
    """MoneyPrinterV2 Terminal User Interface."""

    CSS_PATH = _css_path
    TITLE = "MONEYPRINTER"

    BINDINGS = [
        Binding("g d", "go_to('dashboard')", "Dashboard", show=False),
        Binding("g v", "go_to('video_gen')", "Video", show=False),
        Binding("g a", "go_to('accounts')", "Accounts", show=False),
        Binding("g t", "go_to('twitter')", "Twitter", show=False),
        Binding("g f", "go_to('afm')", "AFM", show=False),
        Binding("g o", "go_to('outreach')", "Outreach", show=False),
        Binding("g s", "go_to('settings')", "Settings", show=False),
        Binding("escape", "pop_screen_or_home", "Back", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]

    # Screen name → module path mapping (lazy loading)
    SCREEN_MODULES = {
        "dashboard": "src.tui.screens.dashboard",
        "video_gen": "src.tui.screens.video_gen",
        "accounts": "src.tui.screens.accounts",
        "twitter": "src.tui.screens.twitter",
        "afm": "src.tui.screens.afm",
        "outreach": "src.tui.screens.outreach",
        "settings": "src.tui.screens.settings",
        "video_detail": "src.tui.screens.video_detail",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_screen_name: str = "dashboard"
        self._pending_key: Optional[str] = None
        # Pre-load screen classes into SCREENS for Textual's lazy instantiation
        self._register_screens()

    def _register_screens(self) -> None:
        """Import all screen classes and register them with Textual."""
        for name, mod_path in self.SCREEN_MODULES.items():
            try:
                parts = mod_path.rsplit(".", 1)
                mod = __import__(
                    mod_path, fromlist=[parts[1] if len(parts) > 1 else ""]
                )
                expected_name = name.title().replace("_", "") + "Screen"
                screen_cls = getattr(mod, expected_name, None)
                if screen_cls is None:
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name, None)
                        if (
                            attr
                            and isinstance(attr, type)
                            and issubclass(attr, Screen)
                            and attr is not Screen
                        ):
                            screen_cls = attr
                            break
                if screen_cls:
                    self.install_screen(screen_cls, name)
            except Exception as e:
                pass  # Will fail to navigate but won't crash

    def compose(self) -> ComposeResult:
        """Create the main layout: Sidebar + Content Area + JobTicker."""
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")
        yield JobTicker(id="job-ticker")

    def on_mount(self) -> None:
        """Initialize the app — attach interceptor, push dashboard."""
        # Attach status interceptor to capture status.* calls
        try:
            from src.tui.wrappers import status_interceptor

            status_interceptor.attach(self)
        except Exception as e:
            self.log.error(f"Failed to attach status interceptor: {e}")

        # Push dashboard as initial screen
        try:
            self.push_screen("dashboard")
            self._update_sidebar("dashboard")
        except Exception as e:
            self.log.error(f"Failed to push dashboard: {e}")

    def on_unmount(self) -> None:
        """Cleanup — detach status interceptor."""
        try:
            from src.tui.wrappers import status_interceptor

            status_interceptor.detach()
        except Exception:
            pass

    def action_go_to(self, screen_name: str) -> None:
        """Navigate to a screen by name.

        Per DESIGN Section 4:
        - Dashboard: pop to root
        - All others: pop to root, then push
        """
        if screen_name not in self.SCREEN_MODULES:
            return

        try:
            if screen_name == "dashboard":
                # Pop back to root
                while len(self.screen_stack) > 1:
                    self.pop_screen()
            else:
                # Don't stack the same screen twice
                if (
                    len(self.screen_stack) > 1
                    and self._current_screen_name == screen_name
                ):
                    return
                # Pop to root first, then push
                while len(self.screen_stack) > 1:
                    self.pop_screen()
                self.push_screen(screen_name)

            self._current_screen_name = screen_name
            self._update_sidebar(screen_name)

        except Exception as e:
            self.log.error(f"Navigation error go_to({screen_name}): {e}")

    def action_pop_screen_or_home(self) -> None:
        """Pop current screen, or go to dashboard if at root."""
        try:
            if len(self.screen_stack) > 1:
                self.pop_screen()
                self._current_screen_name = "dashboard"
                self._update_sidebar("dashboard")
            else:
                self.action_go_to("dashboard")
        except Exception as e:
            self.log.error(f"Pop screen error: {e}")

    def _update_sidebar(self, screen_name: str) -> None:
        """Update sidebar active state."""
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.set_active(screen_name)
        except Exception:
            pass

    # --- Key handling ---

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard shortcuts including 'g' prefix navigation."""
        # Ctrl+C — stop pipeline
        if event.key == "ctrl+c":
            self._handle_ctrl_c()
            event.stop()
            return

        key_map = {
            "d": "dashboard",
            "v": "video_gen",
            "a": "accounts",
            "t": "twitter",
            "f": "afm",
            "o": "outreach",
            "s": "settings",
        }

        if event.key == "g":
            self._pending_key = "g"
            event.stop()
            return

        if self._pending_key == "g" and event.key in key_map:
            self.action_go_to(key_map[event.key])
            self._pending_key = None
            event.stop()
            return

        self._pending_key = None

    def _handle_ctrl_c(self) -> None:
        """Handle Ctrl+C — stop pipeline and return to dashboard."""
        try:
            current = self.screen
            if hasattr(current, "_wrapper") and current._wrapper:
                current._wrapper.cancel()
        except Exception:
            pass

    # --- Message handlers (route to job ticker) ---

    def on_step_started(self, message: StepStarted) -> None:
        """Route step events to job ticker."""
        try:
            ticker = self.query_one("#job-ticker", JobTicker)
            ticker.set_running(message.step, f"step {message.index + 1}/7")
        except Exception:
            pass

    def on_step_progressed(self, message: StepProgressed) -> None:
        """Route progress to job ticker."""
        try:
            ticker = self.query_one("#job-ticker", JobTicker)
            ticker.set_running(message.step, message.detail)
        except Exception:
            pass

    def on_job_completed(self, message: JobCompleted) -> None:
        """Route job completion to ticker."""
        try:
            ticker = self.query_one("#job-ticker", JobTicker)
            ticker.set_complete(
                os.path.basename(message.video_path),
                f"uploaded to YouTube" if message.upload_url else "local",
            )
        except Exception:
            pass

    def on_job_failed(self, message: JobFailed) -> None:
        """Route job failure to ticker."""
        try:
            ticker = self.query_one("#job-ticker", JobTicker)
            ticker.set_failed(message.step, message.error[:80])
        except Exception:
            pass


# Entry point
def main():
    """Launch the TUI application."""
    app = MoneyPrinterApp()
    app.run()


if __name__ == "__main__":
    main()
