import pytest, sys, os, tempfile

# Add project root and src/ to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

@pytest.fixture(autouse=True)
def reset_localevoices():
    """Reset localevoices and tts_voice to default before each test."""
    import json
    from src.config import _settings_cache
    from src.db import set_setting, reload_settings

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


def test_tts_default_voice():
    """TTS() with no locale uses default English voice."""
    from src.classes.Tts import TTS
    tts = TTS()
    assert tts.voice == "en-US-JennyNeural", f"Expected en-US-JennyNeural, got {tts.voice}"

def test_tts_indonesian_voice():
    """TTS(locale='id-ID') uses id-ID-GadisNeural."""
    from src.classes.Tts import TTS
    tts = TTS(locale="id-ID")
    assert tts.voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {tts.voice}"

def test_tts_synthesize_indonesian():
    """TTS with id-ID locale synthesizes SSML correctly."""
    from src.classes.Tts import TTS

    tts = TTS(locale="id-ID")
    ssml = '<speak><prosody rate="90%">Terdapat fakta menakjubkan tentang laut.</prosody></speak>'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(ssml, output)
        assert os.path.exists(result), "Indonesian TTS should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)
