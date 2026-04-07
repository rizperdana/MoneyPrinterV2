"""
Unit test for YouTube class utilities.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from classes.YouTube import YouTube


class TestYouTubeUtils(unittest.TestCase):
    """Test YouTube class utility methods."""

    def test_simplify_prompt_for_pixabay(self):
        """Test prompt simplification for Pixabay search."""
        # Create minimal YouTube instance
        yt = YouTube(
            account_uuid="test-id",
            account_nickname="test",
            fp_profile_path="/tmp/fake",
            niche="science",
            language="English",
        )

        # Test simplification
        result = yt._simplify_prompt_for_pixabay(
            "A beautiful wide cinematic shot of a vast blue ocean surface stretching to horizon"
        )
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_format_srt_timestamp(self):
        """Test SRT timestamp formatting."""
        yt = YouTube(
            account_uuid="test-id",
            account_nickname="test",
            fp_profile_path="/tmp/fake",
            niche="science",
            language="English",
        )

        # Test various timestamps
        self.assertEqual(yt._format_srt_timestamp(0), "00:00:00,000")
        self.assertEqual(yt._format_srt_timestamp(1.5), "00:00:01,500")
        self.assertEqual(yt._format_srt_timestamp(61), "00:01:01,000")
        self.assertEqual(yt._format_srt_timestamp(3661), "01:01:01,000")


if __name__ == "__main__":
    unittest.main()
