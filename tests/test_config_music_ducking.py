import unittest.mock as mock

def test_get_music_volume_speech_default():
    from src.config import get_music_volume_speech
    val = get_music_volume_speech()
    assert 0.0 <= val <= 1.0, f"Expected 0.0-1.0, got {val}"

def test_get_music_volume_silence_default():
    from src.config import get_music_volume_silence
    val = get_music_volume_silence()
    assert 0.0 <= val <= 1.0, f"Expected 0.0-1.0, got {val}"

def test_get_music_fade_duration_ms_default():
    from src.config import get_music_fade_duration_ms
    val = get_music_fade_duration_ms()
    assert 0 <= val <= 2000, f"Expected 0-2000, got {val}"

def test_volume_clamping_high():
    with mock.patch('src.config._get_config', return_value=2.0):
        from src.config import get_music_volume_speech
        val = get_music_volume_speech()
        assert val == 1.0, f"Expected clamped 1.0, got {val}"

def test_volume_clamping_low():
    with mock.patch('src.config._get_config', return_value=-0.5):
        from src.config import get_music_volume_speech
        val = get_music_volume_speech()
        assert val == 0.0, f"Expected clamped 0.0, got {val}"

def test_fade_clamping_high():
    with mock.patch('src.config._get_config', return_value=5000):
        from src.config import get_music_fade_duration_ms
        val = get_music_fade_duration_ms()
        assert val == 2000, f"Expected clamped 2000, got {val}"
