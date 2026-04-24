import os

from config import ROOT_DIR, get_tts_voice

from src.classes.EdgeTts import EdgeTTS


class TTS:
    """
    Text-to-Speech wrapper with locale-aware voice selection.

    Args:
        locale: BCP-47 locale code (e.g., "id-ID", "en-US"). Uses default if None.
    """

    def __init__(self, locale: str = None) -> None:
        print(f"TTS: Getting voice for locale: {locale or 'default'}...")
        self._voice = get_tts_voice(locale)
        print(f"TTS: Voice selected: {self._voice}")
        print("TTS: Initializing EdgeTTS...")
        self._model = EdgeTTS(self._voice)
        print("TTS initialized")

    @property
    def voice(self) -> str:
        """Return the voice name."""
        return self._voice

    def synthesize(
        self,
        text,
        output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav"),
        metadata_path: str | None = None,
    ):
        return self._model.synthesize(text, output_file, metadata_path=metadata_path)
