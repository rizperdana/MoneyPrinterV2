import pytest
import sys
import os
import tempfile

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))


@pytest.fixture(autouse=True)
def reset_languagevoices():
    """Reset languagevoices and tts_voice to default before each test."""
    import json
    from src.config import _settings_cache
    from src.db import set_setting, reload_settings

    # Reset languagevoices to default
    set_setting("languagevoices", json.dumps({
        "Indonesian": "id-ID-GadisNeural",
        "Javanese": "jv-ID-DimasNeural",
        "Sundanese": "su-ID-JajangNeural"
    }))
    # Reset default tts_voice to en-US-JennyNeural
    set_setting("tts_voice", "en-US-JennyNeural")
    reload_settings()
    # Also clear config's cache
    import src.config as config_module
    config_module._settings_cache = None
    yield



def test_indonesian_tts_voice_selection():
    """When language=Indonesian, TTS uses id-ID-GadisNeural."""
    from src.classes.Tts import TTS
    tts = TTS(language="Indonesian")
    assert tts.voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {tts.voice}"


def test_indonesian_ssml_script_generation():
    """generate_script_response with Indonesian language outputs SSML."""
    from unittest.mock import patch

    mock_ssml = '''<speak>
        <prosody rate="100%" pitch="+1st">Terdapat fakta menakjubkan tentang lautan.</prosody>
        <break time="300ms"/>
        <prosody rate="100%">Kehidupan marin yang menakjubkan bisa hidup di tempat yang sangat dalam.</prosody>
    </speak>'''

    with patch("src.llm_generate.generate_response", return_value=mock_ssml):
        from src.llm_generate import generate_script_response
        result = generate_script_response("fakta laut", "Indonesian", 3)

    assert result.strip().startswith("<speak>")
    assert "rate=" in result
    assert "<break" in result


def test_indonesian_edge_tts_synthesis():
    """EdgeTTS with id-ID-GadisNeural synthesizes Indonesian text."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-GadisNeural")
    indonesian_ssml = '<speak version="1.0" xml:lang="id-ID"><prosody rate="90%">Lautan menyimpan banyak misteri yang menakjubkan.</prosody></speak>'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(indonesian_ssml, output)
        assert os.path.exists(result), "Indonesian EdgeTTS should produce audio"
        assert os.path.getsize(result) > 1000, "Audio file should have content"
    finally:
        if os.path.exists(output):
            os.unlink(output)


def test_languagevoices_config_round_trip():
    """languagevoices JSON round-trips through config."""
    from src.config import set_languagevoices, get_languagevoices

    test_mapping = {
        "Indonesian": "id-ID-GadisNeural",
        "Malay": "ms-MY-YasminNeural",
    }
    set_languagevoices(test_mapping)
    retrieved = get_languagevoices()

    assert retrieved["Indonesian"] == "id-ID-GadisNeural"
    assert retrieved["Malay"] == "ms-MY-YasminNeural"
