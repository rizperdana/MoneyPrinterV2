import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

def test_generate_indonesian_script_returns_ssml():
    """generate_script_response for Indonesian should return SSML."""
    from unittest.mock import patch

    mock_ssml = '''<speak version="1.0" xml:lang="id-ID">
        <prosody rate="90%" pitch="-1st">Terdapat fakta menakjubkan yang kamu perlu tahu tentang lautan.</prosody>
        <break time="300ms"/>
        <prosody rate="90%">Kehidupan marin yang menakjubkan ini boleh hidup di tempat yang sangat dalam.</prosody>
    </speak>'''

    with patch("llm_generate.generate_response", return_value=mock_ssml):
        from llm_generate import generate_script_response
        result = generate_script_response("fakta laut", "Indonesian", 3)

    assert result.strip().startswith("<speak"), f"Should start with <speak>, got: {result[:50]}"
    assert "<prosody" in result, "Should contain prosody tags"
    assert "rate=" in result, "Should contain rate attribute"
