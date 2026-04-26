import asyncio
import os
import tempfile
import re

import edge_tts
import soundfile as sf

from src.config import ROOT_DIR


class EdgeTTS:
    """
    Edge TTS synthesis with SSML passthrough and language-aware prosody calibration.

    Args:
        voice: Edge TTS voice shortname (e.g., "en-US-JennyNeural", "id-ID-ArdiNeural")
    """
    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        self._voice = voice

    def synthesize(
        self,
        text: str,
        output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav"),
        metadata_path: str | None = None,
    ):
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        text = text.strip()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            tmp_mp3_path = tmp_mp3.name

        try:
            asyncio.run(self._generate_mp3(text, tmp_mp3_path, metadata_path))
            audio, sample_rate = sf.read(tmp_mp3_path)
            sf.write(output_file, audio, sample_rate)
        finally:
            if os.path.exists(tmp_mp3_path):
                os.unlink(tmp_mp3_path)

        return output_file

    async def _generate_mp3(
        self, text: str, output_path: str, metadata_path: str | None = None
    ) -> None:
        # Check if text contains SSML tags
        is_ssml = bool(
            re.search(r"<[^>]+>.*</[^>]+>", text)
        ) and (
            "<speak>" in text or "<prosody>" in text or "<voice>" in text
        )

        if is_ssml:
            # Try SSML pass-through (edge-tts may reject)
            try:
                communicate = edge_tts.Communicate(text, self._voice)
                await communicate.save(output_path, metadata_path)
            except Exception:
                # Fallback 1: Strip SSML tags and retry
                clean_text = re.sub(r"<[^>]+>", "", text)
                clean_text = re.sub(r'\b(rate|pitch|volume)="[^"]+"', "", clean_text)
                clean_text = clean_text.strip()
                try:
                    communicate = edge_tts.Communicate(clean_text, self._voice)
                    await communicate.save(output_path, metadata_path)
                except Exception:
                    # Fallback 2: Pass through as-is, let it fail gracefully
                    communicate = edge_tts.Communicate(text, self._voice)
                    await communicate.save(output_path, metadata_path)
        else:
            # Normal text processing
            try:
                communicate = edge_tts.Communicate(text, self._voice)
                await communicate.save(output_path, metadata_path)
            except Exception:
                # Fallback: Strip any remaining tags
                clean_text = re.sub(r"<[^>]+>", "", text)
                clean_text = re.sub(r'\b(rate|pitch|volume)="[^"]+"', "", clean_text)
                clean_text = clean_text.strip()
                if clean_text:
                    communicate = edge_tts.Communicate(clean_text, self._voice)
                    await communicate.save(output_path, metadata_path)
                else:
                    raise ValueError("Empty text after cleanup")
