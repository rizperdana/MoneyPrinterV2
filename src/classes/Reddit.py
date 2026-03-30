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

from cache import *
from config import *
from status import *
from llm_provider import generate_text
from constants import *


class Reddit:
    """
    Class for fetching trending posts from Reddit and downloading media.
    
    Features:
    - Fetch trending posts from specified subreddits
    - Download images/videos from Reddit posts
    - Filter by post score (upvotes) for quality content
    - Support multiple subreddits (r/memes, r/dankmemes, r/ProgrammerHumor)
    """

    def __init__(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 10,
        min_score: int = 100,
    ) -> None:
        """
        Initializes the Reddit bot.

        Args:
            subreddits (List[str]): List of subreddit names to fetch from (without 'r/')
            limit (int): Maximum number of posts to fetch per subreddit
            min_score (int): Minimum post score to consider

        Returns:
            None
        """
        self.subreddits = subreddits or ["memes", "dankmemes", "ProgrammerHumor"]
        self.limit = limit
        self.min_score = min_score
        self.posts: List[Dict] = []
        self.downloaded_media: List[str] = []
        
        # Create temp directory for downloads
        self.temp_dir = tempfile.mkdtemp(prefix="mp2_reddit_")

    def _get_headers(self) -> dict:
        """Get headers for Reddit API requests."""
        return {
            "User-Agent": "MoneyPrinterV2/1.0 (Reddit to Twitter Bot)",
            "Accept": "application/json",
        }

    def fetch_hot_posts(self, subreddit: str) -> List[Dict]:
        """
        Fetches hot posts from a specific subreddit using Reddit API.

        Args:
            subreddit (str): The subreddit name (without r/)

        Returns:
            posts (List[dict]): List of post dictionaries
        """
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        params = {"limit": self.limit, "raw_json": 1}
        
        try:
            response = requests.get(
                url, 
                params=params, 
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            posts = []
            children = data.get("data", {}).get("children", [])
            
            for child in children:
                post_data = child.get("data", {})
                
                # Filter by minimum score
                if post_data.get("score", 0) < self.min_score:
                    continue
                
                # Skip self posts (text only)
                if post_data.get("is_self", True):
                    continue
                
                # Get media URL
                preview = post_data.get("preview", {})
                images = preview.get("images", [])
                
                media_url = None
                media_type = None
                
                # Try to get media from preview images
                if images:
                    source = images[0].get("source", {})
                    media_url = source.get("url")
                    if media_url:
                        media_type = "image"
                
                # Check for video/gallery
                if post_data.get("is_video", False):
                    media_url = post_data.get("media", {}).get("reddit_video", {}).get("fallback_url")
                    if media_url:
                        media_type = "video"
                elif post_data.get("crosspost_parent_list"):
                    # Handle crossposts
                    parent = post_data["crosspost_parent_list"][0]
                    if parent.get("is_video", False):
                        media_url = parent.get("media", {}).get("reddit_video", {}).get("fallback_url")
                        if media_url:
                            media_type = "video"
                    else:
                        images = parent.get("preview", {}).get("images", [])
                        if images:
                            media_url = images[0].get("source", {}).get("url")
                            if media_url:
                                media_type = "image"
                
                # Skip if no media found
                if not media_url:
                    continue
                
                post_info = {
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
                posts.append(post_info)
            
            if get_verbose():
                info(f" => Fetched {len(posts)} posts from r/{subreddit}")
            
            return posts
            
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
            
            response = requests.get(media_url, timeout=60, headers=self._get_headers())
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
                    warning(f" => Downloaded file too small, likely corrupted: {filepath}")
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

        Args:
            post (dict): The post dictionary
            max_length (int): Maximum caption length (Twitter limit)

        Returns:
            caption (str): Generated caption
        """
        title = post.get("title", "")
        subreddit = post.get("subreddit", "")
        score = post.get("score", 0)
        
        # Clean up title (remove markdown, links)
        title = re.sub(r"\[.*?\]\(.*?\)", "", title)  # Remove markdown links
        title = re.sub(r"http\S+", "", title)  # Remove URLs
        title = title.strip()
        
        # Truncate if needed
        if len(title) > max_length - 50:
            title = title[:max_length - 53].rsplit(" ", 1)[0] + "..."
        
        # Create caption
        caption = f"🔥 {title}\n\n"
        caption += f"r/{subreddit} • {score:,} upvotes\n"
        caption += f"{post.get('url', '')}"
        
        # Final check and truncate
        if len(caption) > max_length:
            caption = caption[:max_length - 3] + "..."
        
        return caption

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
            title = post.get("title", "")[:40] + "..." if len(post.get("title", "")) > 40 else post.get("title", "")
            table.add_row([
                idx,
                f"r/{post.get('subreddit')}",
                title,
                f"{post.get('score', 0):,}",
                post.get("media_type", "unknown")
            ])
        
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
            info(f"    Score: {best_post.get('score', 0):,} | r/{best_post.get('subreddit')}")
        
        return best_post

    def cleanup(self) -> None:
        """Removes the temporary directory and all downloaded media."""
        if hasattr(self, 'temp_dir') and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            if get_verbose():
                info(" => Cleaned up Reddit temp directory")

    def __del__(self) -> None:
        self.cleanup()
