import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from src.db import init_db, set_setting, reload_settings

@pytest.fixture(autouse=True)
def reset_languagevoices():
    """Reset languagevoices to default before each test."""
    from src.config import _settings_cache
    # Reset languagevoices to default
    set_setting("languagevoices", json.dumps({
        "Indonesian": "id-ID-ArdiNeural",
        "Javanese": "jv-ID-DimasNeural",
        "Sundanese": "su-ID-JajangNeural"
    }))
    reload_settings()
    # Also clear config's cache
    import src.config as config_module
    config_module._settings_cache = None
    yield


def test_get_tts_voice_returns_default():
    """get_tts_voice() with no args returns default (en-US-JennyNeural)."""
    from src.config import get_tts_voice
    voice = get_tts_voice()
    assert voice == "en-US-JennyNeural", f"Expected en-US-JennyNeural, got {voice}"

def test_get_tts_voice_returns_indonesian_voice():
    """get_tts_voice('Indonesian') returns id-ID-ArdiNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("Indonesian")
    assert voice == "id-ID-ArdiNeural", f"Expected id-ID-ArdiNeural, got {voice}"

def test_set_and_get_language_voice():
    """set_tts_voice('id-ID-GadisNeural', 'Indonesian') persists."""
    from src.config import set_tts_voice, get_tts_voice
    set_tts_voice("id-ID-GadisNeural", "Indonesian")
    voice = get_tts_voice("Indonesian")
    assert voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {voice}"

def test_unknown_language_falls_back_to_default():
    """get_tts_voice('German') falls back to en-US-JennyNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("German")
    assert voice == "en-US-JennyNeural", f"Expected fallback en-US-JennyNeural, got {voice}"

def test_get_languagevoices_returns_dict():
    """get_languagevoices() returns {language: voice} dict."""
    from src.config import get_languagevoices
    langvoices = get_languagevoices()
    assert isinstance(langvoices, dict), "Should return dict"
    assert "Indonesian" in langvoices, "Indonesian should be in mapping"
    assert langvoices["Indonesian"] == "id-ID-ArdiNeural", f"Indonesian voice mismatch"
