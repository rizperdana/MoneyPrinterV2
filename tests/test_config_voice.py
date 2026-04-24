import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from src.db import init_db, set_setting, reload_settings

@pytest.fixture(autouse=True)
def reset_localevoices():
    """Reset localevoices and tts_voice to default before each test."""
    from src.config import _settings_cache
    # Reset localevoices to default
    set_setting("localevoices", json.dumps({
        "id-ID": "id-ID-GadisNeural",
        "jv-ID": "jv-ID-SitiNeural",
        "su-ID": "su-ID-TutiNeural"
    }))
    # Reset default tts_voice to en-US-JennyNeural
    set_setting("tts_voice", "en-US-JennyNeural")
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
    """get_tts_voice('id-ID') returns id-ID-GadisNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("id-ID")
    assert voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {voice}"

def test_set_and_get_locale_voice():
    """set_tts_voice('id-ID-GadisNeural', 'id-ID') persists."""
    from src.config import set_tts_voice, get_tts_voice
    set_tts_voice("id-ID-GadisNeural", "id-ID")
    voice = get_tts_voice("id-ID")
    assert voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {voice}"

def test_unknown_locale_falls_back_to_default():
    """get_tts_voice('de-DE') falls back to en-US-JennyNeural."""
    from src.config import get_tts_voice
    voice = get_tts_voice("de-DE")
    assert voice == "en-US-JennyNeural", f"Expected fallback en-US-JennyNeural, got {voice}"

def test_get_localevoices_returns_dict():
    """get_localevoices() returns {locale: voice} dict."""
    from src.config import get_localevoices
    localevoices = get_localevoices()
    assert isinstance(localevoices, dict), "Should return dict"
    assert "id-ID" in localevoices, "id-ID should be in mapping"
    assert localevoices["id-ID"] == "id-ID-GadisNeural", f"id-ID voice mismatch"

def test_set_tts_voice_default_no_locale():
    """set_tts_voice(voice) with no locale sets the default TTS voice."""
    from src.config import set_tts_voice, get_tts_voice
    # Set default voice
    set_tts_voice("en-US-GuyNeural")
    # Verify by calling get_tts_voice() with no args (returns default)
    voice = get_tts_voice()
    assert voice == "en-US-GuyNeural", f"Expected en-US-GuyNeural, got {voice}"

def test_get_localevoices_invalid_json_returns_empty():
    """get_localevoices() with invalid JSON in DB returns empty dict."""
    from src.config import get_localevoices
    # Inject malformed JSON directly into DB
    set_setting("localevoices", "not valid json here")
    reload_settings()
    # Also clear config cache
    import src.config as config_module
    config_module._settings_cache = None
    # Should return empty dict, not raise
    localevoices = get_localevoices()
    assert localevoices == {}, f"Expected empty dict, got {localevoices}"
