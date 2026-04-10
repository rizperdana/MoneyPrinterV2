"""Settings Screen - Configuration management."""

import os
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label


class SettingsScreen(Screen):
    """Settings and configuration screen."""

    # Config keys - stored in .env, not editable here
    API_KEYS = [
        ("CLIPROXY_API_KEY", "sk-..."),
        ("TAVILY_API_KEY", "tvly-..."),
        ("EXA_API_KEY", "..."),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_config()

    def _load_config(self):
        """Load current config from config module."""
        # Import from config module to get current values
        try:
            from src.config import (
                get_tts_voice,
                get_language,
                get_script_sentence_length,
                get_firefox_profile_path,
                get_imagemagick_path,
            )

            self._tts_voice = get_tts_voice()
            self._language = get_language()
            self._sentence_length = get_script_sentence_length()
            self._firefox_profile = get_firefox_profile_path()
            self._imagemagick = get_imagemagick_path()
        except Exception:
            self._tts_voice = "en-US-JennyNeural"
            self._language = "English"
            self._sentence_length = "4"
            self._firefox_profile = ""
            self._imagemagick = "/usr/bin/convert"

    def compose(self):
        yield Static("Settings", classes="screen-header")

        # API Keys - read from .env
        yield Static("API Keys (set in .env)", classes="section-header")
        for key, placeholder in self.API_KEYS:
            value = os.environ.get(key, "")
            masked = "•••••••��" if value else "(not set)"
            yield Label(f"{key}:")
            yield Static(masked, id=f"display-{key.lower()}")

        yield Static("Defaults", classes="section-header")
        yield Label("TTS Voice:")
        yield Input(value=self._tts_voice, id="input-tts-voice")
        yield Label("Language:")
        yield Input(value=self._language, id="input-language")
        yield Label("Sentence Length:")
        yield Input(value=self._sentence_length, id="input-sentence-length")
        yield Static("Browser", classes="section-header")
        yield Label("Firefox Profile:")
        yield Input(value=self._firefox_profile, id="input-firefox")
        yield Label("ImageMagick:")
        yield Input(value=self._imagemagick, id="input-imagemagick")
        yield Static("", classes="spacer")
        yield Static("Edit config.json or .env to change values", classes="hint")
        yield Button("⟳ Reload", variant="primary", id="btn-reload")
