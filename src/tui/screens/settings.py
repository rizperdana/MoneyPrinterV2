"""Settings Screen — Configuration management per DESIGN.md Section 5.4."""

import os

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Switch
from textual.containers import Horizontal


class SettingsScreen(Screen):
    """Settings and configuration screen."""

    API_KEYS = [
        "CLIPROXY_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "TAVILY_API_KEY",
        "EXA_API_KEY",
        "PIXABAY_API_KEY",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_config()

    def _load_config(self):
        """Load current config values."""
        try:
            from src.config import (
                get_tts_voice, get_language,
                get_script_sentence_length,
                get_firefox_profile_path, get_imagemagick_path,
            )
            self._tts_voice = get_tts_voice()
            self._language = get_language()
            self._sentence_length = str(get_script_sentence_length())
            self._firefox_profile = get_firefox_profile_path()
            self._imagemagick = get_imagemagick_path()
        except Exception:
            self._tts_voice = "en-US-JennyNeural"
            self._language = "English"
            self._sentence_length = "4"
            self._firefox_profile = ""
            self._imagemagick = "/usr/bin/convert"

    def compose(self) -> ComposeResult:
        yield Static("[bold #e2e8f0]SETTINGS[/]", classes="screen-title")

        # API Keys
        yield Static(
            "[#64748b]─── api keys ──────────────────────────────────────────[/]",
            classes="section-divider",
        )
        for key in self.API_KEYS:
            value = os.environ.get(key, "")
            display = "••••••••••••••••" if value else "[#f59e0b]not set[/]"
            with Horizontal(classes="form-row"):
                yield Static(key, classes="form-label")
                yield Static(display, id=f"apikey-{key.lower()}")

        # Generation defaults
        yield Static(
            "[#64748b]─── generation defaults ───────────────────────────────[/]",
            classes="section-divider",
        )
        with Horizontal(classes="form-row"):
            yield Static("tts voice", classes="form-label")
            yield Input(value=self._tts_voice, id="input-tts")

        with Horizontal(classes="form-row"):
            yield Static("language", classes="form-label")
            yield Input(value=self._language, id="input-lang")

        with Horizontal(classes="form-row"):
            yield Static("sentences/seg", classes="form-label")
            yield Input(value=self._sentence_length, id="input-sentences")

        with Horizontal(classes="form-row"):
            yield Static("headless", classes="form-label")
            yield Switch(id="switch-headless", value=True)

        # Paths
        yield Static(
            "[#64748b]─── paths ────────────────────────────────────────────[/]",
            classes="section-divider",
        )
        with Horizontal(classes="form-row"):
            yield Static("firefox profile", classes="form-label")
            yield Input(value=self._firefox_profile, id="input-firefox")

        with Horizontal(classes="form-row"):
            yield Static("imagemagick", classes="form-label")
            yield Input(value=self._imagemagick, id="input-imagemagick")

        # Actions
        with Horizontal(classes="button-row"):
            yield Button("save", id="btn-save", classes="action-primary")
            yield Button("reset to defaults", id="btn-reset")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-save":
            self.app.notify("Settings saved (stub)")
        elif bid == "btn-reset":
            self._load_config()
            self.app.notify("Reset to defaults")
