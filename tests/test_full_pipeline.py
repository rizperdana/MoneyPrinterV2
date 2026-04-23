import pytest, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from classes.EdgeTts import EdgeTTS

def test_full_ssml_pipeline():
    """Simulate the full pipeline: SSML script → EdgeTts → audio file."""
    tts = EdgeTTS(voice="en-US-JennyNeural")

    # This is what the LLM would generate for a mystery topic
    ssml_script = '''<speak>
    <prosody rate="80%" pitch="-3st">There's a place where shadows never move.</prosody>
    <break time="500ms"/>
    <prosody rate="85%">And the secrets buried there... are older than time.</prosody>
    <break time="300ms"/>
    <emphasis level="strong">No one has ever come back.</emphasis>
    </speak>'''

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        output_path = f.name

    try:
        result = tts.synthesize(ssml_script, output_path)
        assert os.path.exists(result), "SSML pipeline should produce audio"
        assert os.path.getsize(result) > 1000, "Audio should have content (not empty)"
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

def test_prosody_elements_in_final_audio():
    """Verify different prosody settings produce different audio files."""
    tts = EdgeTTS(voice="en-US-JennyNeural")

    # Two SSML inputs with different prosody (different duration expectations)
    ssml_fast = '<speak><prosody rate="fast">Quick delivery. This is fast.</prosody></speak>'
    ssml_slow = '<speak><prosody rate="slow">Slow delivery. This takes time.</prosody></speak>'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f1:
        path1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f2:
        path2 = f2.name

    try:
        tts.synthesize(ssml_fast, path1)
        tts.synthesize(ssml_slow, path2)

        # Different prosody = different file sizes (rough proxy for different audio)
        size1 = os.path.getsize(path1)
        size2 = os.path.getsize(path2)

        assert size1 != size2, "Fast and slow prosody should produce different audio files"
    finally:
        for p in [path1, path2]:
            if os.path.exists(p):
                os.unlink(p)