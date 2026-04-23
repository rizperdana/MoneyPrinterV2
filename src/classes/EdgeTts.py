import asyncio
import os
import tempfile
import re

import edge_tts
import soundfile as sf

from config import ROOT_DIR


class EdgeTTS:
    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        self._voice = voice

    def synthesize(
        self, text: str, output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav")
    ):
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        text = text.strip()

        # DO NOT strip SSML — Communicate handles both SSML and plain text
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            tmp_mp3_path = tmp_mp3.name

        try:
            asyncio.run(self._generate_mp3(text, tmp_mp3_path))
            audio, sample_rate = sf.read(tmp_mp3_path)
            sf.write(output_file, audio, sample_rate)
        finally:
            if os.path.exists(tmp_mp3_path):
                os.unlink(tmp_mp3_path)

        return output_file

    async def _generate_mp3(self, text: str, output_path: str) -> None:
        try:
            communicate = edge_tts.Communicate(text, self._voice)
            await communicate.save(output_path)
        except Exception as e:
            # If SSML was passed but rejected, strip tags and retry once
            clean_text = re.sub(r"<[^>]+>", "", text)
            clean_text = re.sub(r'\b(rate|pitch|volume)="[^"]+"', "", clean_text)
            clean_text = clean_text.strip()
            if clean_text:
                communicate = edge_tts.Communicate(clean_text, self._voice)
                await communicate.save(output_path)
            else:
                raise ValueError("Empty text after SSML cleanup") from e
