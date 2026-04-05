import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

fake_kittentts = types.ModuleType("kittentts")
fake_kittentts.KittenTTS = object
sys.modules.setdefault("kittentts", fake_kittentts)

fake_ollama = types.ModuleType("ollama")
fake_ollama.Client = object
sys.modules.setdefault("ollama", fake_ollama)

fake_llm_provider = types.ModuleType("llm_provider")
fake_llm_provider.select_model = lambda model: None
sys.modules.setdefault("llm_provider", fake_llm_provider)

fake_tts_module = types.ModuleType("classes.Tts")
fake_tts_module.TTS = object
sys.modules.setdefault("classes.Tts", fake_tts_module)

fake_twitter_module = types.ModuleType("classes.Twitter")
fake_twitter_module.Twitter = object
sys.modules.setdefault("classes.Twitter", fake_twitter_module)

fake_youtube_module = types.ModuleType("classes.YouTube")
fake_youtube_module.YouTube = object
sys.modules.setdefault("classes.YouTube", fake_youtube_module)

import cron


class CronPostBridgeTests(unittest.TestCase):
    @patch("cron.maybe_crosspost_youtube_short")
    @patch("cron.YouTube")
    @patch("cron.TTS")
    @patch("cron.get_accounts")
    @patch("cron.select_model")
    @patch("cron.get_verbose")
    def test_crosspost_does_not_run_when_youtube_upload_fails(
        self,
        get_verbose_mock,
        select_model_mock,
        get_accounts_mock,
        tts_cls_mock,
        youtube_cls_mock,
        crosspost_mock,
    ) -> None:
        get_verbose_mock.return_value = False
        get_accounts_mock.return_value = [
            {
                "id": "yt-1",
                "nickname": "Channel",
                "firefox_profile": "/tmp/profile",
                "niche": "finance",
                "language": "English",
            }
        ]
        youtube_instance = youtube_cls_mock.return_value
        youtube_instance.upload_video.return_value = (False, "Upload failed")
        youtube_instance.video_path = "/tmp/video.mp4"
        youtube_instance.metadata = {"title": "Title"}
        youtube_instance.subject = "Test Topic"
        from tracker import is_topic_used

        is_topic_used_mock = Mock(return_value=False)
        with patch("cron.is_topic_used", is_topic_used_mock):
            with patch.object(
                sys,
                "argv",
                ["cron.py", "youtube", "yt-1", "llama3.2:3b"],
            ):
                cron.main()

        select_model_mock.assert_called_once_with("llama3.2:3b")
        tts_cls_mock.assert_called_once()
        youtube_cls_mock.return_value.generate_video.assert_called_once()
        youtube_cls_mock.return_value.upload_video.assert_called_once()
        crosspost_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
