"""Audio ducking helpers — speech window parsing and volume functions."""
import json
import os
from typing import Callable


def load_speech_windows(meta_path: str) -> list[tuple[float, float]]:
    """Load speech windows from EdgeTTS SentenceBoundary metadata file.

    Args:
        meta_path: Path to JSONL metadata file.

    Returns:
        List of (start_seconds, end_seconds) tuples for each sentence.
    """
    if not os.path.exists(meta_path):
        return []

    windows = []
    with open(meta_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("type") != "SentenceBoundary":
                continue

            offset_us = entry.get("offset", 0)
            dur_us = entry.get("duration", 0)
            start_s = offset_us / 1_000_000
            end_s = (offset_us + dur_us) / 1_000_000
            windows.append((start_s, end_s))

    return windows


def make_volume_func(
    windows: list[tuple[float, float]],
    vol_speech: float,
    vol_silence: float,
    fade_s: float,
) -> Callable[[float], float]:
    """Build a time-varying volume function for dynamic music ducking.

    Args:
        windows: List of (start, end) speech windows in seconds.
        vol_speech: Volume multiplier during TTS speech.
        vol_silence: Volume multiplier during TTS silence (between sentences).
        fade_s: Fade duration in seconds at speech/silence transitions.

    Returns:
        A function t -> volume_multiplier.
    """
    def volume_func(t: float) -> float:
        for start, end in windows:
            fade_start = start - fade_s
            fade_end = end + fade_s

            if fade_start <= t <= fade_end:
                if start <= t <= end:
                    return vol_speech
                elif t < start:
                    dist = t - fade_start
                    ratio = dist / fade_s if fade_s > 0 else 1.0
                    return vol_silence + ratio * (vol_speech - vol_silence)
                else:
                    dist = t - end
                    ratio = dist / fade_s if fade_s > 0 else 1.0
                    return vol_speech + ratio * (vol_silence - vol_speech)

        return vol_silence

    return volume_func