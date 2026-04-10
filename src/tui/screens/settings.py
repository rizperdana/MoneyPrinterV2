"""Settings Screen - Configuration management."""

from textual.screen import Screen
from textual.widgets import Static, Button, Input, Label


class SettingsScreen(Screen):
    """Settings and configuration screen."""

    def compose(self):
        yield Static("Settings", classes="screen-header")
        yield Static("API Keys", classes="section-header")
        yield Label("CLIPROXY_API_KEY:")
        yield Input(placeholder="sk-...", id="input-cliproxy", password=True)
        yield Label("TAVILY_API_KEY:")
        yield Input(placeholder="tvly-...", id="input-tavily", password=True)
        yield Label("EXA_API_KEY:")
        yield Input(placeholder="...", id="input-exa", password=True)
        yield Static("Defaults", classes="section-header")
        yield Label("TTS Voice:")
        yield Input(value="en-US-JennyNeural", id="input-tts-voice")
        yield Label("Language:")
        yield Input(value="English", id="input-language")
        yield Label("Sentence Length:")
        yield Input(value="4", id="input-sentence-length")
        yield Static("Browser", classes="section-header")
        yield Label("Firefox Profile:")
        yield Input(placeholder="/path/to/profile", id="input-firefox")
        yield Label("ImageMagick:")
        yield Input(value="/usr/bin/convert", id="input-imagemagick")
        yield Button("Save Settings", variant="primary", id="btn-save")
        yield Button("Reset to Defaults", id="btn-reset")
