"""E2E smoke test: synthesize with metadata + verify ducking logic end-to-end."""
import os, tempfile

def test_e2e_ducking_logic():
    """Full pipeline: synthesize → load windows → verify volume func behaves correctly."""
    from src.classes.EdgeTts import EdgeTTS
    from src.utils_audio import load_speech_windows, make_volume_func

    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3 = os.path.join(tmpdir, "audio.mp3")
        meta = os.path.join(tmpdir, "sentences.jsonl")
        model.synthesize("Hello. World.", mp3, metadata_path=meta)

        windows = load_speech_windows(meta)
        assert len(windows) >= 2, f"Expected >=2 sentences, got {len(windows)}: {windows}"

        vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
        # Inside first sentence window
        mid0 = (windows[0][0] + windows[0][1]) / 2
        assert abs(vol_func(mid0) - 0.08) < 1e-3, f"Inside speech should be ~0.08, got {vol_func(mid0)}"
        # Outside all windows (far after last sentence)
        far_after = windows[-1][1] + 1.0
        assert abs(vol_func(far_after) - 0.35) < 1e-3, f"Outside should be ~0.35, got {vol_func(far_after)}"