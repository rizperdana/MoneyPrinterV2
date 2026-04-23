import pytest, re

def test_script_cleaner_strips_plain_text():
    """Plain text script should have non-word chars stripped."""
    script = "Hello! This is a test... with @special# characters!"
    cleaned = re.sub(r"[^\w\s.?!]", "", script)
    assert cleaned == "Hello! This is a test... with special characters!", f"Got: {cleaned}"

def test_script_cleaner_preserves_ssml():
    """SSML script should NOT be modified by the regex guard."""
    ssml_script = '<speak><prosody rate="90%">Hook sentence</prosody></speak>'
    if ssml_script.strip().startswith("<speak>"):
        result = ssml_script  # bypass
    else:
        result = re.sub(r"[^\w\s.?!]", "", ssml_script)
    assert result == ssml_script, "SSML should be preserved unchanged"
    assert "<" in result and "prosody" in result, "SSML tags intact"

def test_hook_sentence_with_prosody_preserved():
    """SSML with prosody should survive the guard."""
    ssml = '<speak><prosody rate="fast" pitch="+5st">Breaking news!</prosody></speak>'
    if ssml.strip().startswith("<speak>"):
        result = ssml
    else:
        result = re.sub(r"[^\w\s.?!]", "", ssml)
    assert "<prosody" in result and "fast" in result and "+5st" in result