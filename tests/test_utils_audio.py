import json, tempfile, os, pytest
from src.utils_audio import load_speech_windows, make_volume_func

def test_load_speech_windows_basic():
    """Parse SentenceBoundary entries into (start_s, end_s) tuples."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 0, "duration": 1000000, "text": "Hello."}) + "\n")
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 1100000, "duration": 1000000, "text": "World."}) + "\n")
        path = f.name
    try:
        windows = load_speech_windows(path)
        assert windows == [(0.0, 1.0), (1.1, 2.1)], f"Got {windows}"
    finally:
        os.unlink(path)

def test_load_speech_windows_malformed():
    """Malformed lines are skipped."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 0, "duration": 1000000, "text": "Hello."}) + "\n")
        f.write("NOT JSON\n")
        f.write(json.dumps({"type": "SentenceBoundary", "offset": 2000000, "duration": 1000000, "text": "World."}) + "\n")
        path = f.name
    try:
        windows = load_speech_windows(path)
        assert len(windows) == 2, f"Expected 2 windows, got {len(windows)}"
    finally:
        os.unlink(path)

def test_load_speech_windows_missing_file():
    """Missing file returns empty list."""
    windows = load_speech_windows("/nonexistent/path.jsonl")
    assert windows == [], f"Got {windows}"

def test_volume_func_inside_speech_window():
    """Inside speech: returns vol_speech."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    val = vol_func(2.0)
    assert abs(val - 0.08) < 1e-9, f"Expected 0.08, got {val}"

def test_volume_func_outside_speech_window():
    """Outside all speech windows: returns vol_silence."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    assert abs(vol_func(0.0) - 0.35) < 1e-9
    assert abs(vol_func(5.0) - 0.35) < 1e-9

def test_volume_func_fade_in_zone():
    """Before speech start (within fade): linear interpolation toward vol_speech."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    # At t=0.95 (0.15s into 0.2s fade-in): ratio = 0.15/0.2 = 0.75
    # expected = 0.35 + 0.75*(0.08-0.35) = 0.1475
    val = vol_func(0.95)
    expected = 0.35 + 0.75 * (0.08 - 0.35)
    assert abs(val - expected) < 1e-9, f"Expected {expected}, got {val}"

def test_volume_func_fade_out_zone():
    """After speech end (within fade): linear interpolation toward vol_silence."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.2)
    # At t=3.15 (0.15s into fade-out from 3.0): ratio = 0.15/0.2 = 0.75
    # expected = 0.08 + 0.75*(0.35-0.08) = 0.2825
    val = vol_func(3.15)
    expected = 0.08 + 0.75 * (0.35 - 0.08)
    assert abs(val - expected) < 1e-9, f"Expected {expected}, got {val}"

def test_volume_func_zero_fade():
    """Fade duration = 0: hard transition."""
    windows = [(1.0, 3.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.0)
    assert abs(vol_func(1.0) - 0.08) < 1e-9
    assert abs(vol_func(0.999) - 0.35) < 1e-9
    assert abs(vol_func(3.0) - 0.08) < 1e-9
    assert abs(vol_func(3.001) - 0.35) < 1e-9

def test_volume_func_multiple_windows():
    """Multiple speech windows: each handled independently."""
    windows = [(0.5, 1.5), (3.0, 4.0)]
    vol_func = make_volume_func(windows, vol_speech=0.08, vol_silence=0.35, fade_s=0.1)
    assert abs(vol_func(1.0) - 0.08) < 1e-9
    assert abs(vol_func(3.5) - 0.08) < 1e-9
    assert abs(vol_func(2.0) - 0.35) < 1e-9