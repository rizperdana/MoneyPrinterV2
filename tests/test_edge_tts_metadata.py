import os, tempfile, json, pytest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from classes.EdgeTts import EdgeTTS

def test_synthesize_writes_metadata():
    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = os.path.join(tmpdir, "audio.mp3")
        meta_path = os.path.join(tmpdir, "audio_meta.jsonl")
        result = model.synthesize(
            "Hello world. This is a test.",
            mp3_path,
            metadata_path=meta_path
        )
        assert os.path.exists(meta_path), f"Metadata file not created at {meta_path}"
        with open(meta_path) as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) >= 2, f"Expected >=2 sentence boundaries, got {len(lines)}"
        assert all(e["type"] == "SentenceBoundary" for e in lines)
        assert all("offset" in e and "duration" in e for e in lines)

def test_metadata_offset_format():
    """Offsets are in microseconds, positive, duration > 0."""
    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = os.path.join(tmpdir, "meta.jsonl")
        model.synthesize(
            "Short sentence.",
            os.path.join(tmpdir, "audio.mp3"),
            metadata_path=meta_path
        )
        with open(meta_path) as f:
            entry = json.loads(f.readline())
        assert entry["offset"] >= 0, f"Offset should be >= 0, got {entry['offset']}"
        assert entry["duration"] > 0, f"Duration should be > 0, got {entry['duration']}"

def test_synthesize_returns_audio_path():
    """synthesize() still returns the audio output path as before."""
    model = EdgeTTS()
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = os.path.join(tmpdir, "audio.mp3")
        meta_path = os.path.join(tmpdir, "meta.jsonl")
        result = model.synthesize("Hello world.", mp3_path, metadata_path=meta_path)
        assert result == mp3_path