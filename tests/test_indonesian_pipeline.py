import pytest
import sys
import os
import tempfile

# Add project root to path
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



def test_indonesian_tts_voice_selection():
    """When locale=id-ID, TTS uses id-ID-GadisNeural."""
    from src.classes.Tts import TTS
    tts = TTS(locale="id-ID")
    assert tts.voice == "id-ID-GadisNeural", f"Expected id-ID-GadisNeural, got {tts.voice}"


def test_indonesian_ssml_script_generation():
    """generate_script_response with id-ID locale outputs SSML."""
    from unittest.mock import patch

    mock_ssml = '''<speak>
        <prosody rate="100%" pitch="+1st">Terdapat fakta menakjubkan tentang lautan.</prosody>
        <break time="300ms"/>
        <prosody rate="100%">Kehidupan marin yang menakjubkan bisa hidup di tempat yang sangat dalam.</prosody>
    </speak>'''

    with patch("src.llm_generate.generate_response", return_value=mock_ssml):
        from src.llm_generate import generate_script_response
        result = generate_script_response("fakta laut", "id-ID", 3)

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


def test_localevoices_config_round_trip():
    """localevoices JSON round-trips through config."""
    from src.config import set_localevoices, get_localevoices

    test_mapping = {
        "id-ID": "id-ID-GadisNeural",
        "ms-MY": "ms-MY-YasminNeural",
    }
    set_localevoices(test_mapping)
    retrieved = get_localevoices()

    assert retrieved["id-ID"] == "id-ID-GadisNeural"
    assert retrieved["ms-MY"] == "ms-MY-YasminNeural"
