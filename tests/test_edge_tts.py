import pytest, tempfile, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from classes.EdgeTts import EdgeTTS

def test_synthesize_passes_ssml_through():
    """SSML input should reach Communicate without modification."""
    tts = EdgeTTS(voice="en-US-JennyNeural")
    ssml_input = '<speak><prosody rate="90%">Hook sentence</prosody><break time="500ms"/><prosody rate="100%">Body text</prosody></speak>'
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name
    try:
        result = tts.synthesize(ssml_input, output)
        assert os.path.exists(result), "SSML should produce audio file"
        assert os.path.getsize(result) > 0, "Audio file should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)

def test_synthesize_plain_text_still_works():
    """Plain text input (no SSML) should still synthesize correctly."""
    tts = EdgeTTS(voice="en-US-JennyNeural")
    plain_input = "This is a plain text test sentence."
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output = f.name
    try:
        result = tts.synthesize(plain_input, output)
        assert os.path.exists(result), "Plain text should produce audio file"
        assert os.path.getsize(result) > 0, "Audio file should not be empty"
    finally:
        if os.path.exists(output):
            os.unlink(output)