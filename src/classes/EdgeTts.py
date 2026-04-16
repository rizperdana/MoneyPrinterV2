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

        # Pass raw text directly - no SSML wrapping
        text = text.strip()

        # Safeguard: strip any accidental SSML-like content that could break audio
        try:
            text = self._strip_ssml(text)
        except Exception:
            # If sanitize fails, strip common XML-like patterns
            text = re.sub(r"<[^>]+>", "", text)
            text = text.strip()

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

    def _strip_ssml(self, text: str) -> str:
        """Strip SSML/XML tags to prevent accidental SSML interpretation."""
        if "<speak" in text.lower():
            # Remove entire <speak> wrapper and all internal tags
            text = re.sub(r"<speak[^>]*>", "", text, flags=re.IGNORECASE)
            text = re.sub(r"</speak>", "", text, flags=re.IGNORECASE)
        # Remove any remaining XML-like tags
        text = re.sub(r"<[^>]+>", "", text)
        # Clean up orphaned rate/pitch attributes
        text = re.sub(r'\b(rate|pitch)="[^"]+"', "", text)
        return text.strip()

    async def _generate_mp3(self, text: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path)
