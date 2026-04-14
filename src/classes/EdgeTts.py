import asyncio
import os
import tempfile
import re

import edge_tts
import soundfile as sf

from config import ROOT_DIR


class EdgeTTS:
    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        print(f"EdgeTTS __init__: voice={voice}")
        self._voice = voice
        print("EdgeTTS __init__ completed")

    def synthesize(
        self, text: str, output_file: str = os.path.join(ROOT_DIR, ".mp", "audio.wav")
    ):
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Apply storytelling prosody unless already SSML wrapped
        if not text.strip().startswith("<speak>"):
            text = self._wrap_with_prosody(text)

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

    def _wrap_with_prosody(self, text: str) -> str:
        """Split script into sentences and apply storytelling prosody patterns.

        Per FIX_STORYTELLING.md Section 7: voice should 'pause before important words'.
        Add <break> tags before twist/emphasis keywords and before final sentence.
        """
        # Twist/emphasis keywords that signal important moments per FIX_STORYTELLING.md
        emphasis_keywords = [
            "but",
            "however",
            "actually",
            "surprise",
            "then",
            "what",
            "why",
            "yet",
            "unexpected",
        ]

        # Split into sentences (handles .!? followed by space/end)
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        ssml_parts = ["<speak>"]

        for idx, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()

            # Add pause before sentences with emphasis keywords (per FIX_STORYTELLING.md)
            has_emphasis = any(kw in sentence_lower for kw in emphasis_keywords)
            prefix_break = ""
            if has_emphasis:
                prefix_break = '<break time="300ms"/> '

            # Add longer pause before final sentence/ending
            is_final = idx == len(sentences) - 1
            if is_final:
                prefix_break = '<break time="500ms"/> '

            if idx == 0:
                # Hook: slower, deliberate
                ssml_parts.append(
                    f'  <prosody rate="90%">{prefix_break}{sentence}</prosody>'
                )
            elif is_final:
                # Twist/Ending: slower, lower pitch, longer break
                ssml_parts.append(
                    f'  <prosody rate="85%" pitch="-1st">{prefix_break}{sentence}</prosody>'
                )
            elif has_emphasis:
                # Emphasis sentence: add slight pause before
                ssml_parts.append(
                    f'  <prosody rate="95%">{prefix_break}{sentence}</prosody>'
                )
            else:
                # Middle: normal pace
                ssml_parts.append(f'  <prosody rate="100%">{sentence}</prosody>')

        ssml_parts.append("</speak>")
        return "\n".join(ssml_parts)

    async def _generate_mp3(self, text: str, output_path: str) -> None:
        print(f"EdgeTTS _generate_mp3: text={text[:100]}, voice={self._voice}")
        communicate = edge_tts.Communicate(text, self._voice)
        await communicate.save(output_path)
