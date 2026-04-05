import os

from config import ROOT_DIR, get_tts_voice

from .EdgeTts import EdgeTTS


class TTS:
    def __init__(self) -> None:
        print("TTS: Getting voice...")
        self._voice = get_tts_voice()
        print(f"TTS: Voice selected: {self._voice}")
        print("TTS: Initializing EdgeTTS...")
        self._model = EdgeTTS(self._voice)
        print("TTS initialized")

    def synthesize(self, text, output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav")):
        return self._model.synthesize(text, output_file)
