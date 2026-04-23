import sys, os
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import llm_generate

def test_generate_script_response_returns_ssml():
    """generate_script_response should return SSML starting with <speak>."""
    mock_ssml = '<speak><prosody rate="90%">First sentence hook!</prosody><break time="500ms"/><prosody rate="100%">Second sentence body.</prosody></speak>'

    with patch("llm_generate.generate_response", return_value=mock_ssml):
        result = llm_generate.generate_script_response("mystery topic", "English", 3)

    assert result.strip().startswith("<speak>"), f"Output should start with <speak>, got: {result[:50]}"
    assert "</speak>" in result, "Output should close with </speak>"
    assert "<prosody" in result, "Output should contain prosody tags"

def test_ssml_contains_valid_prosody_attributes():
    """Generated SSML should contain rate/pitch/volume/break/emphasis tags."""
    mock_ssml = '''<speak>
    <prosody rate="85%" pitch="-2st">Mystery reveal line.</prosody>
    <break time="500ms"/>
    <emphasis level="strong">IMPORTANT</emphasis>
    </speak>'''

    with patch("llm_generate.generate_response", return_value=mock_ssml):
        result = llm_generate.generate_script_response("mystery", "English", 3)

    assert 'rate="' in result, "Should contain rate attribute"
    assert "<break" in result, "Should contain break tag"

def test_plain_text_backward_compat():
    """If LLM returns plain text (no SSML), it should pass through unchanged."""
    plain_text = "Just a regular script without any tags."

    with patch("llm_generate.generate_response", return_value=plain_text):
        result = llm_generate.generate_script_response("simple topic", "English", 3)

    assert "Just a regular script" in result