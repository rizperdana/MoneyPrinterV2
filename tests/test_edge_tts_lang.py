import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_synthesize_indonesian_ssml():
    """Indonesian SSML with id-ID-ArdiNeural should produce audio."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    ssml = '''<speak version="1.0" xml:lang="id-ID">
        <prosody rate="90%">Terdapat creature yang boleh punch begitu keras ia membuat air mendidih!</prosody>
        <break time="300ms"/>
        <prosody rate="90%">Ini adalah fakta yang menakjubkan tentang laut.</prosody>
    </speak>'''

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(ssml, output)
        assert os.path.exists(result), "Indonesian SSML should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_fallback_on_malformed_ssml():
    """Malformed SSML falls back to stripped plain text."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    malformed = "<speak><prosody rate=broken>Text with bad attr</prosody></speak>"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(malformed, output)
        assert os.path.exists(result), "Fallback should still produce audio"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_plain_indonesian_text():
    """Plain Indonesian text (no SSML) should synthesize correctly."""
    from src.classes.EdgeTts import EdgeTTS

    tts = EdgeTTS(voice="id-ID-ArdiNeural")
    plain = "Ini adalah ujian untuk suara Indonesia."

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name

    try:
        result = tts.synthesize(plain, output)
        assert os.path.exists(result), "Plain text should produce audio"
        assert os.path.getsize(result) > 0, "Audio should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)
