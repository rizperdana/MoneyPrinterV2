import pytest, sys, os, tempfile

# Add project root and src/ to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

def test_tts_default_voice():
    """TTS() with no language uses default English voice."""
    from src.classes.Tts import TTS
    tts = TTS()
    assert tts.voice == "en-US-JennyNeural", f"Expected en-US-JennyNeural, got {tts.voice}"

def test_tts_indonesian_voice():
    """TTS(language='Indonesian') uses id-ID-ArdiNeural."""
    from src.classes.Tts import TTS
    tts = TTS(language="Indonesian")
    assert tts.voice == "id-ID-ArdiNeural", f"Expected id-ID-ArdiNeural, got {tts.voice}"

def test_tts_synthesize_indonesian():
    """TTS with Indonesian language synthesizes SSML correctly."""
    from src.classes.Tts import TTS

    tts = TTS(language="Indonesian")
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
