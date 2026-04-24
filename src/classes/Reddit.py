import re
import os
import json
import time
import shutil
import tempfile
import requests
from typing import List, Optional, Dict
from datetime import datetime
from termcolor import colored
from uuid import uuid4

from src.cache import get_accounts, add_account
from src.config import get_firefox_profile_path
from src.status import error, success, info, warning
from src.llm_provider import generate_text


class Reddit:
    """
    Class for fetching trending posts from Reddit and downloading media.

    Features:
    - Fetch trending posts from specified subreddits
    - Download images/videos from Reddit posts
    - Filter by post score (upvotes) for quality content
    - Support multiple subreddits (r/memes, r/dankmemes, r/ProgrammerHumor)

    Uses PRAW when REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET env vars are set,
    otherwise falls back to raw HTTP requests against the public Reddit API.
    """

    def __init__(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 10,
        min_score: int = 100,
    ) -> None:
        self.subreddits = subreddits or ["memes", "dankmemes", "ProgrammerHumor"]
        self.limit = limit
        self.min_score = min_score
        self.posts: List[Dict] = []
        self.downloaded_media: List[str] = []

        self.temp_dir = tempfile.mkdtemp(prefix="mp2_reddit_")

        # --- PRAW initialisation (preferred) ---
        self.reddit = None  # type: ignore
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        user_agent = os.environ.get("REDDIT_USER_AGENT", "MoneyPrinterV2/1.0")

        if client_id and client_secret:
            try:
                import praw

                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                )
                if get_verbose():
                    info(" => Reddit: using PRAW (authenticated)")
            except Exception as e:
                if get_verbose():
                    warning(
                        f" => Reddit: PRAW init failed, falling back to raw requests: {e}"
                    )
        else:
            if get_verbose():
                info(" => Reddit: no credentials, using raw requests")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_headers(self) -> dict:
        """Get headers for Reddit API requests (raw-requests fallback)."""
        return {
            "User-Agent": "MoneyPrinterV2/1.0 (Reddit to Twitter Bot)",
            "Accept": "application/json",
        }

    def _post_info_from_praw(self, submission) -> Optional[Dict]:
        """Convert a PRAW Submission to the standard post dict."""
        if submission.score < self.min_score:
            return None
        if submission.is_self:
            return None

        media_url = None
        media_type = None

        # Check for video first
        if getattr(submission, "is_video", False):
            try:
                media_url = submission.media["reddit_video"]["fallback_url"]
                media_type = "video"
            except (KeyError, TypeError):
                pass

        # Check for crosspost
        if media_url is None and hasattr(submission, "crosspost_parent"):
            parent = submission.crosspost_parent
            if parent:
                if getattr(parent, "is_video", False):
                    try:
                        media_url = parent.media["reddit_video"]["fallback_url"]
                        media_type = "video"
                    except (KeyError, TypeError):
                        pass

        # Try preview images (fallback for images / thumbnails)
        if media_url is None:
            try:
                preview_url = submission.preview["images"][0]["source"]["url"]
                media_url = preview_url
                media_type = "image"
            except (KeyError, AttributeError, TypeError):
                pass

        if media_url is None:
            return None

        return {
            "id": submission.id,
            "subreddit": str(submission.subreddit),
            "title": submission.title,
            "author": str(submission.author),
            "score": submission.score,
            "url": f"https://reddit.com{submission.permalink}",
            "media_url": media_url,
            "media_type": media_type,
            "created_utc": int(submission.created_utc),
            "num_comments": submission.num_comments,
        }

    def _post_info_from_raw(self, post_data: Dict) -> Optional[Dict]:
        """Convert a raw JSON post dict to the standard post dict."""
        if post_data.get("score", 0) < self.min_score:
            return None
        if post_data.get("is_self", True):
            return None

        preview = post_data.get("preview", {})
        images = preview.get("images", [])

        media_url = None
        media_type = None

        if images:
            source = images[0].get("source", {})
            media_url = source.get("url")
            if media_url:
                media_type = "image"

        if post_data.get("is_video", False):
            media_url = (
                post_data.get("media", {}).get("reddit_video", {}).get("fallback_url")
            )
            if media_url:
                media_type = "video"
        elif post_data.get("crosspost_parent_list"):
            parent = post_data["crosspost_parent_list"][0]
            if parent.get("is_video", False):
                media_url = (
                    parent.get("media", {}).get("reddit_video", {}).get("fallback_url")
                )
                if media_url:
                    media_type = "video"
            else:
                parent_images = parent.get("preview", {}).get("images", [])
                if parent_images:
                    media_url = parent_images[0].get("source", {}).get("url")
                    if media_url:
                        media_type = "image"

        if not media_url:
            return None

        return {
            "id": post_data.get("id"),
            "subreddit": post_data.get("subreddit"),
            "title": post_data.get("title"),
            "author": post_data.get("author"),
            "score": post_data.get("score"),
            "url": f"https://reddit.com{post_data.get('permalink')}",
            "media_url": media_url,
            "media_type": media_type,
            "created_utc": post_data.get("created_utc"),
            "num_comments": post_data.get("num_comments"),
        }

    # ------------------------------------------------------------------
    # Public API — same surface as before
    # ------------------------------------------------------------------

    def fetch_hot_posts(self, subreddit: str) -> List[Dict]:
        """
        Fetches hot posts from a specific subreddit using Reddit API.

        Args:
            subreddit (str): The subreddit name (without r/)

        Returns:
            posts (List[dict]): List of post dictionaries
        """
        if self.reddit:
            return self._fetch_praw(subreddit)
        return self._fetch_raw(subreddit)

    def _fetch_praw(self, subreddit: str) -> List[Dict]:
        """Fetch hot posts via PRAW."""
        try:
            posts: List[Dict] = []
            for submission in self.reddit.subreddit(subreddit).hot(limit=self.limit):
                post_info = self._post_info_from_praw(submission)
                if post_info:
                    posts.append(post_info)

            if get_verbose():
                info(f" => Fetched {len(posts)} posts from r/{subreddit}")
            return posts
        except Exception as e:
            if get_verbose():
                warning(f"Failed to fetch posts from r/{subreddit}: {e}")
            return []

    def _fetch_raw(self, subreddit: str) -> List[Dict]:
        """Fetch hot posts via raw HTTP requests (legacy fallback)."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        params = {"limit": self.limit, "raw_json": 1}

        try:
            response = requests.get(
                url,
                params=params,
                headers=self._get_headers(),
                timeout=30,
                verify=True,
            )
            response.raise_for_status()
            data = response.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post_info = self._post_info_from_raw(child.get("data", {}))
                if post_info:
                    posts.append(post_info)

            if get_verbose():
                info(f" => Fetched {len(posts)} posts from r/{subreddit}")
            return posts

        except requests.exceptions.SSLError as e:
            if get_verbose():
                warning(
                    f"SSL error fetching r/{subreddit}, retrying without verify: {e}"
                )
            # Retry without SSL verification as fallback
            try:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(
                    url,
                    params=params,
                    headers=self._get_headers(),
                    timeout=30,
                    verify=False,
                )
                response.raise_for_status()
                data = response.json()

                posts = []
                for child in data.get("data", {}).get("children", []):
                    post_info = self._post_info_from_raw(child.get("data", {}))
                    if post_info:
                        posts.append(post_info)

                if get_verbose():
                    info(
                        f" => Fetched {len(posts)} posts from r/{subreddit} (no SSL verify)"
                    )
                return posts
            except Exception as e2:
                if get_verbose():
                    warning(f"Failed to fetch posts from r/{subreddit} (retry): {e2}")
                return []
        except Exception as e:
            if get_verbose():
                warning(f"Failed to fetch posts from r/{subreddit}: {e}")
            return []

    def fetch_trending_posts(self) -> List[Dict]:
        """
        Fetches trending posts from all configured subreddits.

        Returns:
            posts (List[dict]): Combined list of posts from all subreddits
        """
        all_posts = []

        for subreddit in self.subreddits:
            if get_verbose():
                info(f" => Fetching posts from r/{subreddit}...")

            posts = self.fetch_hot_posts(subreddit)
            all_posts.extend(posts)

            # Small delay between subreddit requests
            time.sleep(1)

        # Sort by score (highest first)
        all_posts.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Store posts
        self.posts = all_posts

        if get_verbose():
            success(f" => Total trending posts: {len(all_posts)}")

        return all_posts

    def download_media(self, post: Dict) -> Optional[str]:
        """
        Downloads media from a Reddit post to local storage.

        Args:
            post (dict): The post dictionary containing media_url

        Returns:
            path (str): Path to the downloaded file, or None on failure
        """
        media_url = post.get("media_url")
        media_type = post.get("media_type")

        if not media_url:
            return None

        # Determine file extension
        if media_type == "video":
            ext = ".mp4"
        elif "png" in media_url.lower():
            ext = ".png"
        else:
            ext = ".jpg"

        filename = f"{post['id']}_{post['subreddit']}{ext}"
        filepath = os.path.join(self.temp_dir, filename)

        try:
            # Handle i.redd.it URLs (Reddit's image CDN)
            if "i.redd.it" in media_url:
                # Add quality indicator for images
                if media_type == "image":
                    # Try to get the full resolution
                    media_url = media_url.replace("/preview/", "/")

            response = requests.get(
                media_url, timeout=60, headers=self._get_headers(), verify=True
            )
            response.raise_for_status()

            # Check content type if available
            content_type = response.headers.get("Content-Type", "")
            if "video" in content_type:
                ext = ".mp4"
                filepath = filepath.replace(".jpg", ".mp4").replace(".png", ".mp4")
            elif "image" in content_type:
                if "png" in content_type:
                    ext = ".png"
                    filepath = filepath.replace(".jpg", ".png")

            # Ensure correct extension
            if not filepath.endswith(ext):
                filepath = filepath.rsplit(".", 1)[0] + ext

            with open(filepath, "wb") as f:
                f.write(response.content)

            # Verify file was written and has content
            if os.path.getsize(filepath) > 1000:
                self.downloaded_media.append(filepath)

                if get_verbose():
                    info(f" => Downloaded media: {filepath}")

                return filepath
            else:
                if get_verbose():
                    warning(
                        f" => Downloaded file too small, likely corrupted: {filepath}"
                    )
                os.remove(filepath)
                return None

        except Exception as e:
            if get_verbose():
                warning(f"Failed to download media: {e}")
            return None

    def download_all_media(self, max_downloads: int = 5) -> List[str]:
        """
        Downloads media from all fetched posts.

        Args:
            max_downloads (int): Maximum number of media files to download

        Returns:
            paths (List[str]): List of paths to downloaded files
        """
        downloaded = []

        for post in self.posts[:max_downloads]:
            filepath = self.download_media(post)
            if filepath:
                downloaded.append(filepath)
            time.sleep(0.5)  # Rate limiting

        if get_verbose():
            success(f" => Downloaded {len(downloaded)} media files")

        return downloaded

    def get_post_caption(self, post: Dict, max_length: int = 280) -> str:
        """
        Generates a caption for a Reddit post suitable for Twitter.
        Uses LLM to create witty, engaging captions with relevant hashtags.

        Args:
            post (dict): The post dictionary
            max_length (int): Maximum caption length (Twitter limit)

        Returns:
            caption (str): Generated caption
        """
        # Try LLM-powered caption first, fall back to simple caption
        try:
            caption = self.generate_meme_caption(post)
            if caption and len(caption) <= max_length:
                return caption
        except Exception:
            pass  # Fall through to simple caption

        # Fallback: simple caption from title
        title = post.get("title", "")
        subreddit = post.get("subreddit", "")
        score = post.get("score", 0)

        # Clean up title (remove markdown, links)
        title = re.sub(r"\[.*?\]\(.*?\)", "", title)  # Remove markdown links
        title = re.sub(r"http\S+", "", title)  # Remove URLs
        title = title.strip()

        # Truncate if needed
        if len(title) > max_length - 50:
            title = title[: max_length - 53].rsplit(" ", 1)[0] + "..."

        # Generate hashtag from subreddit
        hashtag = f"#{subreddit}" if subreddit else "#memes"

        # Create caption
        caption = f"🔥 {title}\n\n"
        caption += f"r/{subreddit} • {score:,} upvotes\n"
        caption += f"{hashtag} #reddit #viral"

        # Final check and truncate
        if len(caption) > max_length:
            caption = caption[: max_length - 3] + "..."

        return caption

    def generate_meme_caption(self, post: Dict) -> str:
        """
        Uses LLM to generate a witty, meme-style caption for a Reddit post.

        Produces short, punchy, funny captions with relevant hashtags —
        not just a copy of the Reddit title.

        Args:
            post (dict): The post dictionary with 'title', 'subreddit', 'score'

        Returns:
            caption (str): LLM-generated meme caption (≤ 280 chars)
        """
        title = post.get("title", "")
        subreddit = post.get("subreddit", "memes")
        score = post.get("score", 0)

        # Subreddit-to-hashtag mapping for trending/relevant tags
        subreddit_hashtags = {
            "memes": "#memes #funny #lol #relatable",
            "dankmemes": "#dankmemes #dank #edgymemes #darkhumor",
            "ProgrammerHumor": "#ProgrammerHumor #coding #devlife #techmemes",
            "me_irl": "#meirl #relatable #mood #toomeirlformeirl",
            "wholesomememes": "#wholesome #wholesomememes #goodvibes #positivity",
            "funny": "#funny #humor #comedy #laughing",
            "MemeEconomy": "#MemeEconomy #stonks #invest #mememarket",
            "PrequelMemes": "#PrequelMemes #StarWars #prequelmemes",
            "HistoryMemes": "#HistoryMemes #history #educational",
            "gaming": "#gaming #gamer #videogames #gamermemes",
        }

        hashtags = subreddit_hashtags.get(subreddit, f"#{subreddit} #memes #viral")

        prompt = (
            f"You are a viral meme social media copywriter. "
            f"Given this Reddit post from r/{subreddit} with {score:,} upvotes:\n\n"
            f'Title: "{title}"\n\n'
            f"Write a short, punchy, funny Twitter caption (max 200 characters, NOT the title). "
            f"Make it witty, meme-style, and engaging. Use internet humor. "
            f"Do NOT just repeat the title — add your own spin or joke. "
            f"Do NOT include hashtags (they will be added separately). "
            f"Output ONLY the caption text, nothing else."
        )

        try:
            raw = generate_text(prompt)
            if not raw:
                return ""

            # Clean up LLM output
            caption_text = raw.strip().strip('"').strip("'")
            # Remove any markdown bold/italic markers
            caption_text = re.sub(r"\*{1,3}", "", caption_text)
            # Remove any hashtags the LLM might have added anyway
            caption_text = re.sub(r"#\w+", "", caption_text).strip()

            # Build final caption with hashtags
            # Reserve space for hashtags + newlines
            hashtag_block = f"\n\n{hashtags}"
            max_text_len = 280 - len(hashtag_block)

            if len(caption_text) > max_text_len:
                caption_text = (
                    caption_text[: max_text_len - 3].rsplit(" ", 1)[0] + "..."
                )

            final_caption = f"{caption_text}{hashtag_block}"

            # Absolute safety: enforce 280-char Twitter limit
            if len(final_caption) > 280:
                final_caption = final_caption[:277] + "..."

            return final_caption

        except Exception as e:
            if get_verbose():
                warning(f"LLM caption generation failed: {e}")
            return ""

    def select_post(self, index: int) -> Optional[Dict]:
        """
        Selects a post by index from the fetched posts.

        Args:
            index (int): The index of the post to select (1-based)

        Returns:
            post (dict): The selected post, or None if index is invalid
        """
        if 0 < index <= len(self.posts):
            return self.posts[index - 1]
        return None

    def display_posts(self) -> None:
        """Displays fetched posts in a formatted table."""
        if not self.posts:
            warning("No posts to display. Run fetch_trending_posts() first.")
            return

        from prettytable import PrettyTable

        table = PrettyTable()
        table.field_names = ["#", "Subreddit", "Title", "Score", "Type"]

        for idx, post in enumerate(self.posts, start=1):
            title = (
                post.get("title", "")[:40] + "..."
                if len(post.get("title", "")) > 40
                else post.get("title", "")
            )
            table.add_row(
                [
                    idx,
                    f"r/{post.get('subreddit')}",
                    title,
                    f"{post.get('score', 0):,}",
                    post.get("media_type", "unknown"),
                ]
            )

        print(table)

    def get_best_post(self) -> Optional[Dict]:
        """
        Returns the highest upvoted post with media from fetched posts.

        This is a convenience method that fetches trending posts and returns
        the top one by score.

        Returns:
            post (dict): The highest upvoted post with media, or None if no posts found
        """
        if not self.posts:
            # Fetch posts if not already fetched
            self.fetch_trending_posts()

        if not self.posts:
            if get_verbose():
                warning("No posts with media found")
            return None

        # Return the first post (highest score after sorting)
        best_post = self.posts[0]

        if get_verbose():
            info(f" => Best post: {best_post.get('title', '')[:50]}...")
            info(
                f"    Score: {best_post.get('score', 0):,} | r/{best_post.get('subreddit')}"
            )

        return best_post

    def cleanup(self) -> None:
        """Removes the temporary directory and all downloaded media."""
        if hasattr(self, "temp_dir") and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if get_verbose():
                info(" => Cleaned up Reddit temp directory")

    def __del__(self) -> None:
        self.cleanup()
