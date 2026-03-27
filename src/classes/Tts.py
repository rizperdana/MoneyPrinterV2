import os

from config import ROOT_DIR, get_tts_voice

from .EdgeTts import EdgeTTS


class TTS:
    def __init__(self) -> None:
        self._voice = get_tts_voice()
        self._model = EdgeTTS(self._voice)

    def synthesize(self, text, output_file=os.path.join(ROOT_DIR, ".mp", "audio.wav")):
        return self._model.synthesize(text, output_file)
