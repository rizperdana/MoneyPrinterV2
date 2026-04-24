import os

from config import ROOT_DIR, get_tts_voice

from .EdgeTts import EdgeTTS


class TTS:
    """
    Text-to-Speech wrapper with language-aware voice selection.

    Args:
        language: Language name (e.g., "Indonesian", "English"). Uses default if None.
    """

    def __init__(self, language: str = None) -> None:
        print(f"TTS: Getting voice for language: {language or 'default'}...")
        self._voice = get_tts_voice(language)
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
