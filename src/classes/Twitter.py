import re
import sys
import time
import os
import json
import shutil
import tempfile

from cache import get_accounts, add_account, remove_account
from config import get_firefox_profile_path, get_headless, ROOT_DIR
from status import error, success, info, warning
from llm_provider import generate_text
from typing import List, Optional
from datetime import datetime
from termcolor import colored
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote


class Twitter:
    """
    Class for the Bot, that grows a Twitter account.
    """

    def __init__(
        self, account_uuid: str, account_nickname: str, fp_profile_path: str, topic: str
    ) -> None:
        """
        Initializes the Twitter Bot.

        Args:
            account_uuid (str): The account UUID
            account_nickname (str): The account nickname
            fp_profile_path (str): The path to the Firefox profile

        Returns:
            None
        """
        self.account_uuid: str = account_uuid
        self.account_nickname: str = account_nickname
        self.fp_profile_path: str = fp_profile_path
        self.topic: str = topic

        # Initialize the Firefox profile
        self.options: Options = Options()

        # Set headless state of browser
        if get_headless():
            self.options.add_argument("--headless")

        if not os.path.isdir(fp_profile_path):
            raise ValueError(
                f"Firefox profile path does not exist or is not a directory: {fp_profile_path}"
            )

        # Copy profile to temp dir so we don't conflict with a running Firefox
        self._temp_profile_dir = tempfile.mkdtemp(prefix="mp2_ff_tw_")

        def _ignore_locks(dir, files):
            return [f for f in files if f in (".parentlock", "parent.lock", "lock")]

        temp_profile = os.path.join(self._temp_profile_dir, "profile")
        shutil.copytree(fp_profile_path, temp_profile, ignore=_ignore_locks)

        self.options.add_argument("-profile")
        self.options.add_argument(temp_profile)

        # Set the service
        self.service: Service = Service(GeckoDriverManager().install())

        # Initialize the browser
        self.browser: webdriver.Firefox = webdriver.Firefox(
            service=self.service, options=self.options
        )
        self.wait: WebDriverWait = WebDriverWait(self.browser, 30)

    def post(self, text: Optional[str] = None) -> None:
        """
        Starts the Twitter Bot.

        Args:
            text (str): The text to post

        Returns:
            None
        """
        bot: webdriver.Firefox = self.browser
        verbose: bool = get_verbose()

        bot.get("https://x.com/compose/post")

        post_content: str = text if text is not None else self.generate_post()
        now: datetime = datetime.now()

        print(colored(" => Posting to Twitter:", "blue"), post_content[:30] + "...")
        body = post_content

        text_box = None
        text_box_selectors = [
            (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0'][role='textbox']"),
            (By.XPATH, "//div[@data-testid='tweetTextarea_0']//div[@role='textbox']"),
            (By.XPATH, "//div[@role='textbox']"),
        ]

        for selector in text_box_selectors:
            try:
                text_box = self.wait.until(EC.element_to_be_clickable(selector))
                text_box.click()
                text_box.send_keys(body)
                break
            except Exception:
                continue

        if text_box is None:
            raise RuntimeError(
                "Could not find tweet text box. Ensure you are logged into X in this Firefox profile."
            )

        post_button = None
        post_button_selectors = [
            (By.XPATH, "//button[@data-testid='tweetButtonInline']"),
            (By.XPATH, "//button[@data-testid='tweetButton']"),
            (By.XPATH, "//span[text()='Post']/ancestor::button"),
        ]

        for selector in post_button_selectors:
            try:
                post_button = self.wait.until(EC.element_to_be_clickable(selector))
                post_button.click()
                break
            except Exception:
                continue

        if post_button is None:
            raise RuntimeError("Could not find the Post button on X compose screen.")

        if verbose:
            print(colored(" => Pressed [ENTER] Button on Twitter..", "blue"))
        time.sleep(2)

        # Add the post to the cache
        self.add_post({"content": body, "date": now.strftime("%m/%d/%Y, %H:%M:%S")})

        success("Posted to Twitter successfully!")

    def get_posts(self) -> List[dict]:
        """
        Gets the posts from the cache.

        Returns:
            posts (List[dict]): The posts
        """
        if not os.path.exists(get_twitter_cache_path()):
            # Create the cache file
            with open(get_twitter_cache_path(), "w") as file:
                json.dump({"accounts": []}, file, indent=4)

        with open(get_twitter_cache_path(), "r") as file:
            parsed = json.load(file)

            # Find our account
            accounts = parsed["accounts"]
            for account in accounts:
                if account["id"] == self.account_uuid:
                    posts = account["posts"]

                    if posts is None:
                        return []

                    # Return the posts
                    return posts

        return []

    def add_post(self, post: dict) -> None:
        """
        Adds a post to the cache.

        Args:
            post (dict): The post to add

        Returns:
            None
        """
        posts = self.get_posts()
        posts.append(post)

        with open(get_twitter_cache_path(), "r") as file:
            previous_json = json.loads(file.read())

            # Find our account
            accounts = previous_json["accounts"]
            for account in accounts:
                if account["id"] == self.account_uuid:
                    account["posts"].append(post)

            # Commit changes
            with open(get_twitter_cache_path(), "w") as f:
                f.write(json.dumps(previous_json))

    def generate_post(self) -> str:
        """
        Generates a post for the Twitter account based on the topic.

        Returns:
            post (str): The post
        """
        completion = generate_text(
            f"Generate a Twitter post about: {self.topic} in {get_twitter_language()}. "
            "The Limit is 2 sentences. Choose a specific sub-topic of the provided topic."
        )

        if get_verbose():
            info("Generating a post...")

        if completion is None:
            error("Failed to generate a post. Please try again.")
            sys.exit(1)

        # Apply Regex to remove all *
        completion = re.sub(r"\*", "", completion).replace('"', "")

        if get_verbose():
            info(f"Length of post: {len(completion)}")
        if len(completion) >= 260:
            return completion[:257].rsplit(" ", 1)[0] + "..."

        return completion

    def post_with_media(self, text: str, media_path: str = None) -> bool:
        """
        Posts a tweet with optional media (image/video) attachment.

        This method handles cross-posting Reddit content to Twitter with
        images or videos and a caption.

        Args:
            text (str): The tweet text/caption
            media_path (str): Optional path to image/video file to attach

        Returns:
            success (bool): Whether the post was successful
        """
        bot: webdriver.Firefox = self.browser
        verbose: bool = get_verbose()

        try:
            # Navigate to X compose page
            bot.get("https://x.com/compose/post")
            time.sleep(2)

            print(
                colored(" => Posting to Twitter with media:", "blue"), text[:50] + "..."
            )

            # Fill in the text first
            text_box = None
            text_box_selectors = [
                (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0'][role='textbox']"),
                (
                    By.XPATH,
                    "//div[@data-testid='tweetTextarea_0']//div[@role='textbox']",
                ),
                (By.XPATH, "//div[@role='textbox']"),
            ]

            for selector in text_box_selectors:
                try:
                    text_box = self.wait.until(EC.element_to_be_clickable(selector))
                    text_box.click()
                    text_box.send_keys(text)
                    break
                except Exception:
                    continue

            if text_box is None:
                raise RuntimeError(
                    "Could not find tweet text box. Ensure you are logged into X in this Firefox profile."
                )

            # Upload media if provided
            if media_path and os.path.isfile(media_path):
                if verbose:
                    info(f" => Uploading media: {media_path}")

                # Find the media upload button
                media_button_selectors = [
                    (By.XPATH, "//input[@type='file']"),
                    (By.CSS_SELECTOR, "input[type='file']"),
                    (By.XPATH, "//button[@data-testid='addFileButton']"),
                    (By.XPATH, "//button[contains(@aria-label, 'Add media')]"),
                ]

                media_input = None
                for selector in media_button_selectors:
                    try:
                        media_input = bot.find_element(*selector)
                        if media_input:
                            break
                    except Exception:
                        continue

                if media_input:
                    # Send the file path to the input
                    media_input.send_keys(media_path)

                    # Wait for media to upload
                    time.sleep(3)

                    if verbose:
                        info(" => Media uploaded successfully")
                else:
                    if verbose:
                        warning("Could not find media upload button, posting text only")

            # Click the post button
            post_button = None
            post_button_selectors = [
                (By.XPATH, "//button[@data-testid='tweetButtonInline']"),
                (By.XPATH, "//button[@data-testid='tweetButton']"),
                (By.XPATH, "//span[text()='Post']/ancestor::button"),
            ]

            for selector in post_button_selectors:
                try:
                    post_button = self.wait.until(EC.element_to_be_clickable(selector))
                    post_button.click()
                    break
                except Exception:
                    continue

            if post_button is None:
                raise RuntimeError(
                    "Could not find the Post button on X compose screen."
                )

            if verbose:
                print(colored(" => Pressed Post Button on Twitter..", "blue"))

            time.sleep(2)

            # Add the post to the cache
            now = datetime.now()
            self.add_post(
                {
                    "content": text,
                    "media_path": media_path,
                    "date": now.strftime("%m/%d/%Y, %H:%M:%S"),
                }
            )

            success("Posted to Twitter with media successfully!")
            return True

        except Exception as e:
            error(f"Failed to post with media: {e}")
            return False

    def post_reddit_content(self, reddit_post: dict, media_path: str = None) -> bool:
        """
        Posts Reddit content to Twitter with automatic caption generation.

        Convenience method that takes a Reddit post dict and optional media path,
        then posts to Twitter.

        Args:
            reddit_post (dict): The Reddit post dictionary (from Reddit.py)
            media_path (str): Optional path to downloaded media file

        Returns:
            success (bool): Whether the post was successful
        """
        # Generate caption from Reddit post
        caption = self._generate_reddit_caption(reddit_post)

        return self.post_with_media(caption, media_path)

    def _generate_reddit_caption(self, reddit_post: dict, max_length: int = 280) -> str:
        """
        Generates a Twitter caption from a Reddit post.
        Uses LLM for witty, engaging copy with trending hashtags.

        Args:
            reddit_post (dict): The Reddit post dictionary
            max_length (int): Maximum caption length

        Returns:
            caption (str): Generated caption
        """
        # Try LLM-powered caption first
        try:
            caption = self.generate_caption_from_reddit(reddit_post)
            if caption and len(caption) <= max_length:
                return caption
        except Exception:
            pass

        # Fallback: simple caption from title
        title = reddit_post.get("title", "")
        subreddit = reddit_post.get("subreddit", "")
        score = reddit_post.get("score", 0)
        url = reddit_post.get("url", "")

        # Clean up title
        title = re.sub(r"\[.*?\]\(.*?\)", "", title)
        title = re.sub(r"http\S+", "", title)
        title = title.strip()

        # Trending hashtag sets by subreddit
        trending_tags = {
            "memes": "#memes #viral #trending #lol",
            "dankmemes": "#dankmemes #dank #viral #edgy",
            "ProgrammerHumor": "#ProgrammerHumor #coding #devlife #tech",
            "me_irl": "#meirl #relatable #mood #viral",
            "wholesomememes": "#wholesome #goodvibes #positive #love",
            "funny": "#funny #humor #comedy #viral",
            "gaming": "#gaming #gamer #videogames #esports",
        }
        hashtags = trending_tags.get(subreddit, f"#{subreddit} #reddit #viral")

        # Build caption
        caption = f"🔥 {title}\n\n"
        caption += f"r/{subreddit} • {score:,} upvotes\n"
        caption += hashtags

        # Add URL if there's room
        if len(caption) + len(url) + 2 <= max_length:
            caption += f"\n{url}"
        elif len(caption) > max_length:
            caption = caption[: max_length - 3] + "..."

        return caption

    def generate_caption_from_reddit(self, reddit_post: dict) -> str:
        """
        Generates a witty, LLM-powered Twitter caption from a Reddit post.

        Uses the configured LLM to create short, punchy, meme-style captions
        with trending hashtags. Falls back to a simple title-based caption
        if the LLM is unavailable.

        Args:
            reddit_post (dict): The Reddit post dictionary containing at least
                                'title', 'subreddit', 'score', and 'url' keys

        Returns:
            caption (str): Generated Twitter-ready caption (≤ 280 chars)
        """
        title = reddit_post.get("title", "")
        subreddit = reddit_post.get("subreddit", "memes")
        score = reddit_post.get("score", 0)

        # Subreddit → trending hashtag mapping
        subreddit_hashtags = {
            "memes": "#memes #funny #lol #viral #trending",
            "dankmemes": "#dankmemes #dank #edgymemes #darkhumor #viral",
            "ProgrammerHumor": "#ProgrammerHumor #coding #devlife #techmemes #geek",
            "me_irl": "#meirl #relatable #mood #toomeirlformeirl",
            "wholesomememes": "#wholesome #wholesomememes #goodvibes #positivity",
            "funny": "#funny #humor #comedy #laughing #viral",
            "MemeEconomy": "#MemeEconomy #stonks #invest #mememarket",
            "gaming": "#gaming #gamer #videogames #gamermemes #esports",
            "HistoryMemes": "#HistoryMemes #history #educational #memes",
            "PrequelMemes": "#PrequelMemes #StarWars #prequelmemes",
        }

        hashtags = subreddit_hashtags.get(
            subreddit, f"#{subreddit} #memes #reddit #viral"
        )

        prompt = (
            f"You are a viral social media copywriter specializing in meme content. "
            f"Given this Reddit post from r/{subreddit} with {score:,} upvotes:\n\n"
            f'Title: "{title}"\n\n'
            f"Write a short, punchy, funny Twitter caption (max 200 characters). "
            f"Make it witty, meme-style, and engaging — NOT a copy of the title. "
            f"Add your own joke, spin, or hot take. Use internet humor. "
            f"Do NOT include hashtags (added separately). "
            f"Do NOT use quotes around the output. "
            f"Output ONLY the caption text."
        )

        try:
            raw = generate_text(prompt)
            if not raw:
                return self._generate_reddit_caption(reddit_post)

            # Clean up LLM output
            caption_text = raw.strip().strip('"').strip("'")
            caption_text = re.sub(r"\*{1,3}", "", caption_text)
            # Strip any hashtags the LLM may have added
            caption_text = re.sub(r"#\w+", "", caption_text).strip()

            # Build final caption: text + hashtags
            hashtag_block = f"\n\n{hashtags}"
            max_text_len = 280 - len(hashtag_block)

            if len(caption_text) > max_text_len:
                caption_text = (
                    caption_text[: max_text_len - 3].rsplit(" ", 1)[0] + "..."
                )

            final_caption = f"{caption_text}{hashtag_block}"

            # Enforce Twitter's 280-char hard limit
            if len(final_caption) > 280:
                final_caption = final_caption[:277] + "..."

            return final_caption

        except Exception as e:
            if get_verbose():
                warning(f"LLM caption generation failed, using fallback: {e}")
            return self._generate_reddit_caption(reddit_post)
