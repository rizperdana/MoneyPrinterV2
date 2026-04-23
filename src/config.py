import os
import sys
import json
import srt_equalizer

from termcolor import colored

# Always use project root (parent of src folder)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# DB-based settings cache (lazy-loaded, avoids circular import with db.py)
_settings_cache: dict | None = None


def _load_settings() -> dict:
    """
    Load settings from database only.
    Falls back to empty dict if DB unavailable.
    """
    global _settings_cache

    if _settings_cache is None:
        try:
            from src.db import get_settings as _db_get_settings
            _settings_cache = _db_get_settings()
        except Exception:
            _settings_cache = {}

    return _settings_cache


def _get_config(key: str, default=None):
    """Get config value from cached settings or default."""
    settings = _load_settings()
    value = settings.get(key, default)

    # Handle string "true"/"false" to bool conversion
    if value == "true":
        return True
    if value == "false":
        return False

    # Handle numeric strings
    if isinstance(value, str) and value:
        try:
            if "." in value:
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            pass

    # Handle JSON-serialized arrays and dicts
    if isinstance(value, str):
        if value.startswith("[") or value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

    return value


def reload_config() -> None:
    """Force reload settings from database."""
    global _settings_cache
    _settings_cache = None


def assert_folder_structure() -> None:
    """
    Make sure that the nessecary folder structure is present.

    Returns:
        None
    """
    # Create the .mp folder
    if not os.path.exists(os.path.join(ROOT_DIR, ".mp")):
        if get_verbose():
            print(
                colored(
                    f"=> Creating .mp folder at {os.path.join(ROOT_DIR, '.mp')}",
                    "green",
                )
            )
        os.makedirs(os.path.join(ROOT_DIR, ".mp"))


def get_first_time_running() -> bool:
    """
    Checks if the program is running for the first time by checking if .mp folder exists.

    Returns:
        exists (bool): True if the program is running for the first time, False otherwise
    """
    return not os.path.exists(os.path.join(ROOT_DIR, ".mp"))


def get_email_credentials() -> dict:
    """
    Gets the email credentials from settings.

    Returns:
        credentials (dict): The email credentials
    """
    email_json = _get_config("email")
    if isinstance(email_json, dict):
        return email_json
    if email_json:
        try:
            return json.loads(email_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return {}


def get_oauth_credentials() -> dict:
    """
    Gets the OAuth credentials from settings.

    Returns:
        credentials (dict): The OAuth credentials
    """
    oauth_json = _get_config("google_oauth")
    if isinstance(oauth_json, dict):
        return oauth_json
    if oauth_json:
        try:
            import json as _json
            return _json.loads(oauth_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return {}


def get_verbose() -> bool:
    """
    Gets the verbose flag from settings.

    Returns:
        verbose (bool): The verbose flag
    """
    value = _get_config("verbose", False)
    return bool(value) if value else False


def get_firefox_profile_path() -> str:
    """
    Gets the path to the Firefox profile.

    Returns:
        path (str): The path to the Firefox profile
    """
    return _get_config("firefox_profile", "")


def get_headless() -> bool:
    """
    Gets the headless flag from settings.

    Returns:
        headless (bool): The headless flag
    """
    value = _get_config("headless", True)
    return bool(value) if value else True


def get_llm_base_url() -> str:
    """
    Gets the LLM API base URL.

    Returns:
        url (str): The LLM API base URL
    """
    return _get_config("llm_base_url", "http://localhost:8317/v1")


def get_default_model() -> str:
    """
    Gets the default LLM model name from settings.

    Returns:
        model (str): The model name, or empty string if not set.
    """
    return _get_config("llm_model", "")


def get_twitter_language() -> str:
    """
    Gets the Twitter language from settings.

    Returns:
        language (str): The Twitter language
    """
    return _get_config("twitter_language", "English")


def get_tiktok_username() -> str:
    """
    Gets the TikTok username from config.

    Returns:
        username (str): The TikTok username
    """
    return _get_config("tiktok_username", "")


def get_threads() -> int:
    """
    Gets the amount of threads to use for example when writing to a file with MoviePy.

    Returns:
        threads (int): Amount of threads
    """
    return int(_get_config("threads", 2))


def get_zip_url() -> str:
    """
    Gets the URL to the zip file containing the songs.

    Returns:
        url (str): The URL to the zip file
    """
    return _get_config("zip_url", "")


def get_is_for_kids() -> bool:
    """
    Gets the is for kids flag from settings.

    Returns:
        is_for_kids (bool): The is for kids flag
    """
    value = _get_config("is_for_kids", False)
    return bool(value) if value else False


def get_google_maps_scraper_zip_url() -> str:
    """
    Gets the URL to the zip file containing the Google Maps scraper.

    Returns:
        url (str): The URL to the zip file
    """
    return _get_config("google_maps_scraper", "")


def get_google_maps_scraper_niche() -> str:
    """
    Gets the niche for the Google Maps scraper.

    Returns:
        niche (str): The niche
    """
    return _get_config("google_maps_scraper_niche", "")


def get_scraper_timeout() -> int:
    """
    Gets the timeout for the scraper.

    Returns:
        timeout (int): The timeout
    """
    return int(_get_config("scraper_timeout", 300))


def get_outreach_message_subject() -> str:
    """
    Gets the outreach message subject.

    Returns:
        subject (str): The outreach message subject
    """
    return _get_config("outreach_message_subject", "")


def get_outreach_message_body_file() -> str:
    """
    Gets the outreach message body file.

    Returns:
        file (str): The outreach message body file
    """
    return _get_config("outreach_message_body_file", "outreach_message.html")


def get_tts_voice() -> str:
    """
    Gets the TTS voice from settings.

    Returns:
        voice (str): The TTS voice
    """
    return _get_config("tts_voice", "en-US-JennyNeural")


def get_assemblyai_api_key() -> str:
    """
    Gets the AssemblyAI API key.

    Returns:
        key (str): The AssemblyAI API key
    """
    return _get_config("assembly_ai_api_key", "")


def get_stt_provider() -> str:
    """
    Gets the configured STT provider.

    Returns:
        provider (str): The STT provider
    """
    return _get_config("stt_provider", "local_whisper")


def get_whisper_model() -> str:
    """
    Gets the local Whisper model name.

    Returns:
        model (str): Whisper model name
    """
    return _get_config("whisper_model", "base")


def get_whisper_device() -> str:
    """
    Gets the target device for Whisper inference.

    Returns:
        device (str): Whisper device
    """
    return _get_config("whisper_device", "auto")


def get_whisper_compute_type() -> str:
    """
    Gets the compute type for Whisper inference.

    Returns:
        compute_type (str): Whisper compute type
    """
    return _get_config("whisper_compute_type", "int8")


def equalize_subtitles(srt_path: str, max_chars: int = 10) -> None:
    """
    Equalizes the subtitles in a SRT file.

    Args:
        srt_path (str): The path to the SRT file
        max_chars (int): The maximum amount of characters in a subtitle

    Returns:
        None
    """
    srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)


def get_font() -> str:
    """
    Gets the font from settings.

    Returns:
        font (str): The font
    """
    return _get_config("font", "bold_font.ttf")


def get_fonts_dir() -> str:
    """
    Gets the fonts directory.

    Returns:
        dir (str): The fonts directory
    """
    return os.path.join(ROOT_DIR, "fonts")


def get_imagemagick_path() -> str:
    """
    Gets the path to ImageMagick.

    Returns:
        path (str): The path to ImageMagick
    """
    return _get_config("imagemagick_path", "/usr/bin/convert")


def get_script_sentence_length() -> int:
    """
    Gets the forced script's sentence length.
    In case there is no sentence length in config, returns 4 when none

    Returns:
        length (int): Length of script's sentence
    """
    value = _get_config("script_sentence_length")
    if value is not None:
        return int(value)
    return 4


def get_images_per_video() -> int:
    """
    Gets the number of images to generate per video from settings.
    Default is 8 images per video.

    Returns:
        count (int): Number of images per video
    """
    return int(_get_config("images_per_video", 8))


# ─── Schedule Time Defaults ────────────────────────────────────────────────────

DEFAULT_YOUTUBE_SCHEDULE_TIMES = ["06:00", "12:00", "18:00"]
DEFAULT_TWITTER_SCHEDULE_TIMES = ["09:00", "15:00", "21:00"]


def get_youtube_schedule_times() -> list:
    """
    Gets the YouTube upload schedule times.

    Returns:
        list: List of time strings, e.g. ["06:00", "12:00", "18:00"]
    """
    return _get_config("youtube_schedule_times", DEFAULT_YOUTUBE_SCHEDULE_TIMES)


def get_twitter_schedule_times() -> list:
    """
    Gets the Twitter posting schedule times.

    Returns:
        list: List of time strings, e.g. ["09:00", "15:00", "21:00"]
    """
    return _get_config("twitter_schedule_times", DEFAULT_TWITTER_SCHEDULE_TIMES)


def get_music_volume_speech() -> float:
    """Music volume (0.0–1.0) during TTS speech segments."""
    val = _get_config("music_volume_speech", 0.08)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.08
    return max(0.0, min(1.0, val))


def get_music_volume_silence() -> float:
    """Music volume (0.0–1.0) during TTS silence (between sentences)."""
    val = _get_config("music_volume_silence", 0.35)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = 0.35
    return max(0.0, min(1.0, val))


def get_music_fade_duration_ms() -> int:
    """Fade duration in ms at speech/silence transitions."""
    val = _get_config("music_fade_duration_ms", 200)
    try:
        val = int(val)
    except (TypeError, ValueError):
        val = 200
    return max(0, min(2000, val))
