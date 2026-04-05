import re
import base64
import json
import time
import os
import random
import shutil
import tempfile
import numpy as np
import requests
import assemblyai as aai
from PIL import Image

from utils import *
from cache import *
from .Tts import TTS
from llm_provider import generate_text
from config import *
from status import *
from uuid import uuid4
from constants import *
from typing import List
from moviepy import (
    VideoClip,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
)
from moviepy.video.tools.subtitles import SubtitlesClip
from moviepy import afx
from termcolor import colored
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


def _suppress_stderr():
    """Context manager to suppress stderr."""
    import contextlib, io

    return contextlib.redirect_stderr(io.StringIO())


class YouTube:
    """
    Class for YouTube Automation.

    Steps to create a YouTube Short:
    1. Generate a topic [DONE]
    2. Generate a script [DONE]
    3. Generate metadata (Title, Description, Tags) [DONE]
    4. Generate AI Image Prompts [DONE]
    4. Generate Images based on generated Prompts [DONE]
    5. Convert Text-to-Speech [DONE]
    6. Show images each for n seconds, n: Duration of TTS / Amount of images [DONE]
    7. Combine Concatenated Images with the Text-to-Speech [DONE]
    """

    def __init__(
        self,
        account_uuid: str,
        account_nickname: str,
        fp_profile_path: str,
        niche: str,
        language: str,
    ) -> None:
        """
        Constructor for YouTube Class.

        Args:
            account_uuid (str): The unique identifier for the YouTube account.
            account_nickname (str): The nickname for the YouTube account.
            fp_profile_path (str): Path to the firefox profile that is logged into the specificed YouTube Account.
            niche (str): The niche of the provided YouTube Channel.
            language (str): The language of the Automation.

        Returns:
            None
        """
        self._account_uuid: str = account_uuid
        self._account_nickname: str = account_nickname
        self._fp_profile_path: str = fp_profile_path
        self._niche: str = niche
        self._language: str = language

        self.images = []
        self._g4f_quota_exhausted = False

        if not os.path.isdir(self._fp_profile_path):
            raise ValueError(
                f"Firefox profile path does not exist or is not a directory: {self._fp_profile_path}"
            )

        self.options: Options = Options()
        if get_headless():
            self.options.add_argument("--headless")

        self.options.add_argument("-profile")
        self.options.add_argument(self._fp_profile_path)

        gecko_path = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0/geckodriver"
        service = Service(executable_path=gecko_path)

        self.browser: webdriver.Firefox = webdriver.Firefox(
            service=service, options=self.options
        )
        self.wait: WebDriverWait = WebDriverWait(self.browser, 30)
        self.page = self.browser

        self._temp_profile_dir = None

    def _ensure_browser(self):
        pass

    @property
    def niche(self) -> str:
        """
        Getter Method for the niche.

        Returns:
            niche (str): The niche
        """
        return self._niche

    @property
    def language(self) -> str:
        """
        Getter Method for the language to use.

        Returns:
            language (str): The language
        """
        return self._language

    def generate_response(self, prompt: str, model_name: str = None) -> str:
        """
        Generates an LLM Response based on a prompt and the user-provided model.

        Args:
            prompt (str): The prompt to use in the text generation.

        Returns:
            response (str): The generated AI Repsonse.
        """
        return generate_text(prompt, model_name=model_name)

    def _research_trending_topics(self) -> str:
        """
        Researches trending topics from Wikipedia API and Google Trends.
        Returns raw search context to feed into the LLM for topic selection.

        Returns:
            context (str): Research context with trending keywords and topics.
        """
        context_parts = []

        # Method 1: Wikipedia Featured Content API (today's news + trending)
        try:
            from datetime import datetime

            today = datetime.now().strftime("%Y/%m/%d")
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/feed/featured/{today}"
            resp = requests.get(
                wiki_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()

                # Today's news
                news = data.get("news", [])
                news_items = []
                for item in news[:8]:
                    story = re.sub(r"<[^>]+>", "", item.get("story", "")).strip()
                    links = item.get("links", [])
                    titles = [l.get("titles", {}).get("normalized", "") for l in links]
                    if story:
                        entry = story[:150]
                        if titles:
                            entry += f" ({', '.join(titles[:2])})"
                        news_items.append(entry)
                if news_items:
                    context_parts.append(
                        "Wikipedia Today's News:\n"
                        + "\n".join(f"- {n}" for n in news_items)
                    )

                # Today's featured article
                tfa = data.get("tfa", {})
                if tfa:
                    title = tfa.get("titles", {}).get("normalized", "")
                    extract = tfa.get("extract", "")[:200]
                    if title and extract:
                        context_parts.append(
                            f"Wikipedia Featured Article: {title}\n{extract}"
                        )

                # Most read articles
                most_read = data.get("mostread", {}).get("articles", [])
                if most_read:
                    top_titles = [
                        a.get("titles", {}).get("normalized", "")
                        for a in most_read[:10]
                        if a.get("titles")
                    ]
                    if top_titles:
                        context_parts.append(
                            "Wikipedia Most Read Today:\n"
                            + "\n".join(f"- {t}" for t in top_titles if t)
                        )
        except Exception as e:
            if get_verbose():
                warning(f"Wikipedia API failed: {e}")

        # Method 2: Google Trends RSS
        try:
            for geo in ["US", ""]:
                trends_url = f"https://trends.google.com/trending/rss?geo={geo}"
                resp = requests.get(
                    trends_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    titles = re.findall(r"<title>(.*?)</title>", resp.text)
                    relevant = []
                    for t in titles[1:20]:
                        t_clean = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t).strip()
                        if t_clean and len(t_clean) > 3:
                            relevant.append(t_clean)
                    if relevant:
                        label = f"Google Trends ({geo or 'Global'})"
                        context_parts.append(
                            f"{label}:\n" + "\n".join(f"- {t}" for t in relevant[:15])
                        )
                        break
        except Exception as e:
            if get_verbose():
                warning(f"Google Trends failed: {e}")

        # Method 3: DuckDuckGo for niche-specific topics
        try:
            search_query = f"{self.niche} latest news today"
            ddg_url = "https://api.duckduckgo.com/"
            params = {
                "q": search_query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            }
            resp = requests.get(
                ddg_url,
                params=params,
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0"},
                verify=False,
            )
            if resp.status_code == 200:
                data = resp.json()
                related = data.get("RelatedTopics", [])
                topics_found = []
                for item in related[:8]:
                    if isinstance(item, dict) and item.get("Text"):
                        topics_found.append(item["Text"][:120])
                if topics_found:
                    context_parts.append(
                        f"DuckDuckGo {self.niche}:\n"
                        + "\n".join(f"- {t}" for t in topics_found)
                    )
        except Exception as e:
            if get_verbose():
                warning(f"DuckDuckGo failed: {e}")

        if context_parts:
            return "\n\n".join(context_parts)
        return ""

    def generate_topic(self) -> str:
        """
        Generates a topic based on trending subjects in the niche.
        Uses web research to find real trending topics, then picks the best one.

        Returns:
            topic (str): The generated topic.
        """
        # Step 1: Research what's actually trending
        research_context = self._research_trending_topics()

        if research_context:
            if get_verbose():
                info(
                    f" => Research context ({len(research_context)} chars) gathered from web search"
                )

            # Feed real research data into the LLM
            trend_prompt = f"""You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {self.niche}

=== RESEARCH DATA (for inspiration only) ===
{research_context}
=== END RESEARCH DATA ===

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY about "{self.niche}". Do NOT pick general news, history, or unrelated trending topics. If the research data doesn't contain niche-relevant content, IGNORE it and generate topics from your own knowledge about "{self.niche}".

Generate 3 specific, engaging video topic ideas that:
1. Are STRICTLY and EXCLUSIVELY about: {self.niche}
2. Would perform well as YouTube Shorts (curiosity-driven, visual, surprising)
3. Are specific enough to make a 45-60 second video about

Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example (if niche is "cool animal facts"):
1. The mantis shrimp can punch so fast it boils the water around it
2. Tardigrades can survive in the vacuum of outer space
3. Octopuses have three hearts and blue blood"""
        else:
            # Fallback: no web research available, use LLM knowledge
            if get_verbose():
                warning(
                    "Web research unavailable. Using LLM knowledge for topic generation."
                )
            trend_prompt = f"""You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {self.niche}

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY and EXCLUSIVELY about "{self.niche}". Do NOT drift into general knowledge, history, or unrelated subjects.

Consider:
1. What surprising or little-known facts exist about {self.niche}?
2. What recent discoveries or viral moments relate to {self.niche}?
3. What would make someone stop scrolling and watch about {self.niche}?

Generate 3 specific, engaging video topic ideas that would perform well as YouTube Shorts.
Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example (if niche is "cool animal facts"):
1. The mantis shrimp can punch so fast it boils the water around it
2. Tardigrades can survive in the vacuum of outer space
3. Octopuses have three hearts and blue blood"""

        completion = str(self.generate_response(trend_prompt)).strip()

        # Parse numbered topics
        topics = []
        for line in completion.split("\n"):
            line = line.strip()
            match = re.match(r"^[\d]+[\.\)\-\s]+(.+)$", line)
            if match:
                topic = match.group(1).strip()
                if len(topic) > 20:
                    topics.append(topic)

        # Load previously used topics to avoid duplicates
        used_topics_file = os.path.join(ROOT_DIR, ".mp", "used_topics.json")
        used_topics = []
        try:
            if os.path.exists(used_topics_file):
                with open(used_topics_file, "r") as f:
                    used_data = json.load(f)
                    if isinstance(used_data, dict):
                        used_topics = list(used_data.keys())
                    elif isinstance(used_data, list):
                        used_topics = used_data
        except Exception:
            pass

        # Filter out topics that are too similar to already used ones
        def is_similar(new_topic, used_list, threshold=0.4):
            """Check if topic shares too many words with an existing topic."""
            new_words = set(new_topic.lower().split())
            for used in used_list:
                used_words = set(used.lower().split())
                if not new_words or not used_words:
                    continue
                overlap = len(new_words & used_words) / max(
                    len(new_words), len(used_words)
                )
                if overlap > threshold:
                    return True
            return False

        # Pick the best topic that hasn't been used
        selected = None
        for topic in topics:
            if not is_similar(topic, used_topics):
                selected = topic
                break

        if not selected:
            # All topics were duplicates, force a new one
            if get_verbose():
                warning("All generated topics were duplicates. Forcing unique topic...")
            avoid_list = (
                "\n".join(f"- {t}" for t in used_topics[-20:])
                if used_topics
                else "none"
            )
            selected = self.generate_response(
                f"Generate ONE specific, engaging video topic about: {self.niche}.\n"
                f"DO NOT repeat any of these already-used topics:\n{avoid_list}\n"
                f"One sentence only. Be creative and pick something completely different."
            )

        if not selected:
            error("Failed to generate Topic.")
            selected = f"Interesting facts about {self.niche}"

        # Save topic to used list
        try:
            existing = {}
            if os.path.exists(used_topics_file):
                with open(used_topics_file, "r") as f:
                    existing = json.load(f)
            if not isinstance(existing, dict):
                existing = {}
            existing[selected] = {
                "account": self.nickname,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(used_topics_file, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass

        self.subject = selected

        if get_verbose():
            info(f" => Trending topic selected: {selected[:80]}...")

        return selected

    def generate_script(self) -> str:
        """
        Generate a script following the GUIDE's high-retention video structure.

        Structure:
        - Hook (first sentence): Bold disruptive statement that grabs attention in 0-3 seconds.
        - Core Delivery (next sentences): High information density, no filler. Each sentence = one visual scene.
        - Climax/Payoff: The most impressive fact or visual.
        - Seamless Loop: Last sentence grammatically connects back to the first sentence.

        Returns:
            script (str): The script of the video.
        """
        sentence_length = get_script_sentence_length()
        prompt = f"""Write a YouTube Shorts script about: {self.subject}

CRITICAL RULE — EXPLAIN LIKE THE VIEWER IS 5 YEARS OLD:
- Use ONLY words a 5-year-old knows. No jargon. No technical terms unless you immediately explain them with a simple analogy.
- Every concept must be compared to something from daily life: "It's like when you blow up a balloon and it pops" or "Imagine stacking LEGO blocks really fast"
- If the topic is technical (software, engineering, science), translate EVERY concept into a physical, visual, everyday comparison.
- BAD: "The load balancer distributes traffic across servers" → GOOD: "Imagine a pizza shop with one door. A thousand people try to enter at once. So they open ten doors and split the crowd evenly"
- BAD: "The infrastructure handles millions of concurrent connections" → GOOD: "Picture a million people all talking on the phone at the same time — somehow nobody gets disconnected"
- Each sentence must paint a CLEAR picture in the viewer's mind. If a kid can't visualize it, rewrite it.

STRUCTURE (strict):
1. HOOK (sentence 1): A shocking or surprising statement that makes people stop scrolling. Example: "This shrimp punches so fast the water catches fire."
2. CORE DELIVERY (sentences 2-{sentence_length - 1}): Each sentence = one clear visual scene. Explain ONE thing per sentence. Use analogies. Be specific with numbers and comparisons.
3. CLIMAX/PAYOFF (sentence {sentence_length - 1} or {sentence_length}): The most mind-blowing fact, delivered simply.
4. SEAMLESS LOOP (last sentence): Must grammatically connect back to the first sentence so the video loops seamlessly.

RULES:
- Total: {sentence_length} sentences maximum
- 70-120 words total (short, punchy, no rambling)
- First sentence is a HOOK STATEMENT, NOT a title or label
- Each sentence describes a visual scene (what we SEE on screen)
- NO markdown, NO formatting, NO section labels
- NO "welcome to this video" or "in this video"
- NO call to action, NO "like and subscribe"
- Write in {self.language}
- Each sentence punchy (under 15 words)
- SPECIFIC over VAGUE: say "300 million years ago" not "a long time ago", say "as fast as a bullet" not "very fast"

Subject: {self.subject}
Language: {self.language}

Return ONLY the raw script text. No labels, no numbering."""

        completion = self.generate_response(prompt)

        # Apply regex to remove *
        completion = re.sub(r"\*", "", completion)

        if not completion:
            error("The generated script is empty.")
            return

        if len(completion) > 5000:
            if get_verbose():
                warning("Generated Script is too long. Retrying...")
            return self.generate_script()

        self.script = completion

        if get_verbose():
            # Count approximate sections
            sentences = [
                s.strip() for s in re.split(r"[.!?]+", completion) if len(s.strip()) > 5
            ]
            info(f" => Script: {len(sentences)} sentences, {len(completion)} chars")

        return completion

    def generate_metadata(self) -> dict:
        """
        Generates Video metadata for the to-be-uploaded YouTube Short (Title, Description, Tags).

        Returns:
            metadata (dict): The generated metadata with keys: title, description, tags.
        """
        title = self.generate_response(
            f"Generate a YouTube Shorts title for: {self.subject}. "
            f"Rules: Under 50 characters. Front-load the most important keywords. "
            f"No hashtags in the title. Return ONLY the title, nothing else."
        )

        if len(title) > 50:
            if get_verbose():
                warning("Generated Title is too long. Retrying...")
            return self.generate_metadata()

        description = self.generate_response(
            f"Generate a YouTube Shorts description for the following script: {self.script}. "
            f"Rules: Include 3-5 relevant hashtags. Add a brief, keyword-rich summary of the video content "
            f"to index properly in YouTube Search. Return ONLY the description, nothing else."
        )

        # Generate SEO tags
        tags_raw = self.generate_response(
            f"Generate a JSON array of 10-15 YouTube SEO tags (single words or short phrases) for a video about: {self.subject}. "
            f'Return ONLY a JSON array of strings, e.g. ["tag1", "tag2"]. No other text.'
        )

        tags = []
        try:
            cleaned = str(tags_raw).replace("```json", "").replace("```", "").strip()
            tags = json.loads(cleaned)
            if not isinstance(tags, list):
                tags = []
        except Exception:
            # Fallback: extract from subject
            if get_verbose():
                warning("Failed to parse tags JSON. Using subject words as fallback.")
            tags = [w for w in self.subject.split() if len(w) > 2][:10]

        self.metadata = {"title": title, "description": description, "tags": tags}

        if get_verbose():
            info(f" => Generated {len(tags)} SEO tags")

        return self.metadata

    def generate_prompts(self) -> List[str]:
        """
        Generates AI Image Prompts based on the provided Video Script.
        Each scene gets 2 sub-prompts (different angle/perspective) for visual variety.
        Target: 8-12 total images for a richer visual experience.

        Returns:
            image_prompts (List[str]): Generated List of image prompts.
        """
        # Split script into sentences for scene mapping
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", self.script) if len(s.strip()) > 10
        ]

        # Target 4-5 scenes, 1 image each = 4-5 total
        n_scenes = min(max(len(sentences), 3), 5)

        prompt = f"""You are a visual director creating a storyboard for a YouTube Short.

Subject: {self.subject}
Script sentences (in order):
{chr(10).join(str(i + 1) + ". " + s for i, s in enumerate(sentences[:n_scenes]))}

For EACH sentence above, write ONE visual scene description for AI image generation.

CRITICAL RULES:
- NO text, letters, words, numbers, signs, logos, or writing of ANY kind in the scene
- NO close-ups of hands, fingers, or human extremities
- Use WIDE shots, landscapes, environments, aerial views
- Show the main subject clearly from a distance
- Each scene: 15-25 words describing what we SEE
- Consistent cinematic style across ALL scenes
- Scenes flow like a visual story (beginning to middle to end)

Output format: Numbered 1 to {n_scenes}. One scene per line.
Do NOT use JSON. Do NOT use quotes. Just numbered lines.

Example:
1. vast blue ocean surface stretching to horizon under golden sunset light with distant waves
2. aerial drone view of colorful coral reef teeming with tropical fish from above
3. deep dark ocean trench with bioluminescent creatures glowing in the abyss"""

        completion = str(self.generate_response(prompt)).strip()

        image_prompts = []

        # Parse numbered lines (1, 2, 3 format)
        lines = completion.split("\n")
        for line in lines:
            line = line.strip()
            # Match patterns like "1.", "2.", "3." etc.
            match = re.match(r"^[\d]+[\.\)\-\s]+(.+)$", line)
            if match:
                scene = match.group(1).strip().strip('"').strip("'")
                if len(scene) > 10:
                    image_prompts.append(scene)

        # Fallback: try JSON parse
        if not image_prompts:
            cleaned = completion.replace("```json", "").replace("```", "").strip()
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    image_prompts = [
                        p.strip()
                        for p in parsed
                        if isinstance(p, str) and len(p.strip()) > 10
                    ]
            except Exception:
                pass

        # Fallback: generate from script sentences directly (1 per scene)
        if not image_prompts:
            if get_verbose():
                warning(
                    "LLM prompt parsing failed. Generating from script sentences..."
                )
            for sentence in sentences[:n_scenes]:
                visual = f"wide cinematic shot of {sentence.strip()[:60]}, photorealistic, dramatic lighting, no text, no hands"
                image_prompts.append(visual)

        # Ensure minimum of 4 images
        while len(image_prompts) < 4 and sentences:
            idx = len(image_prompts) // 2
            if idx < len(sentences):
                variant = (
                    "wide establishing shot"
                    if len(image_prompts) % 2 == 0
                    else "close-up detail view"
                )
                visual = (
                    f"{variant} of {sentences[idx].strip()[:60]}, cinematic, detailed"
                )
                image_prompts.append(visual)
            else:
                break

        # Cap at 12 images max
        image_prompts = image_prompts[:12]

        self.image_prompts = image_prompts

        success(
            f"Generated {len(image_prompts)} Image Prompts ({len(image_prompts) // 2} scenes x 2 angles)."
        )

        return image_prompts

    def _persist_image(self, image_bytes: bytes, provider_label: str) -> str:
        """
        Writes generated image bytes to a PNG file in .mp.

        Args:
            image_bytes (bytes): Image payload
            provider_label (str): Label for logging

        Returns:
            path (str): Absolute image path
        """
        image_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")

        with open(image_path, "wb") as image_file:
            image_file.write(image_bytes)

        if get_verbose():
            info(f' => Wrote image from {provider_label} to "{image_path}"')

        self.images.append(image_path)
        return image_path

    def generate_image_nanobanana2(self, prompt: str) -> str:
        """
        Generates an AI Image using Nano Banana 2 API (Gemini image API).

        Args:
            prompt (str): Prompt for image generation

        Returns:
            path (str): The path to the generated image.
        """
        print(f"Generating Image using Nano Banana 2 API: {prompt}")

        api_key = get_nanobanana2_api_key()
        if not api_key:
            error("nanobanana2_api_key is not configured.")
            return None

        base_url = get_nanobanana2_api_base_url().rstrip("/")
        model = get_nanobanana2_model()
        aspect_ratio = get_nanobanana2_aspect_ratio()

        endpoint = f"{base_url}/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": aspect_ratio},
            },
        }

        try:
            response = requests.post(
                endpoint,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            if response.status_code == 429:
                if get_verbose():
                    warning("Gemini image API rate limited (429). Falling back.")
                return None
            response.raise_for_status()
            body = response.json()

            candidates = body.get("candidates", [])
            for candidate in candidates:
                content = candidate.get("content", {})
                for part in content.get("parts", []):
                    inline_data = part.get("inlineData") or part.get("inline_data")
                    if not inline_data:
                        continue
                    data = inline_data.get("data")
                    mime_type = inline_data.get("mimeType") or inline_data.get(
                        "mime_type", ""
                    )
                    if data and str(mime_type).startswith("image/"):
                        image_bytes = base64.b64decode(data)
                        return self._persist_image(image_bytes, "Nano Banana 2 API")

            if get_verbose():
                warning(
                    f"Nano Banana 2 did not return an image payload. Response: {body}"
                )
            return None
        except Exception as e:
            if get_verbose():
                warning(f"Failed to generate image with Nano Banana 2 API: {str(e)}")
            return None

    def generate_image_pollinations(self, prompt: str) -> str:
        """
        Generates an AI image using Pollinations.ai GET endpoint with API key.
        Uses the simple GET /image/{prompt} endpoint which bypasses Cloudflare blocking.

        Args:
            prompt (str): Scene description for image generation

        Returns:
            path (str): The path to the generated image, or None on failure.
        """
        api_key = os.environ.get("POLLINATIONS_API_KEY", "")
        if not api_key:
            if get_verbose():
                warning("POLLINATIONS_API_KEY not set. Skipping Pollinations.")
            return None

        enhanced_prompt = f"{prompt}, Ghibli watercolor"
        print(f"Generating AI image via Pollinations API: {prompt[:80]}...")

        try:
            import urllib.parse

            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=flux&width=1080&height=1920&key={api_key}&nologo=true"

            resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})

            if resp.status_code == 429:
                if get_verbose():
                    warning("Pollinations API rate limited (429).")
                return None

            if resp.status_code == 401 or resp.status_code == 403:
                if get_verbose():
                    warning(f"Pollinations API auth failed ({resp.status_code}).")
                return None

            resp.raise_for_status()

            if len(resp.content) < 1000:
                if get_verbose():
                    warning("Pollinations image too small, likely an error.")
                return None

            return self._persist_image(resp.content, "Pollinations API")

        except Exception as e:
            if get_verbose():
                warning(f"Pollinations image generation failed: {e}")
            return None

    def generate_image_g4f(self, prompt: str) -> str:
        """
        Generates an AI image using gpt4free (Pollinations/Flux).
        Free, no API key needed. Primary image generator.

        Args:
            prompt (str): Scene description for image generation

        Returns:
            path (str): The path to the generated image, or None on failure.
        """
        try:
            from g4f.client import Client
        except ImportError:
            if get_verbose():
                warning("g4f not installed. Cannot use Pollinations/Flux.")
            return None

        enhanced_prompt = f"{prompt}, Ghibli watercolor"
        print(f"Generating AI image via g4f (Pollinations/Flux): {prompt[:80]}...")

        try:
            client = Client()
            response = client.images.generate(
                model="flux",
                prompt=enhanced_prompt,
                response_format="url",
            )

            if not response or not response.data or len(response.data) == 0:
                if get_verbose():
                    warning("g4f returned no image data.")
                return None

            image_url = response.data[0].url
            if not image_url:
                if get_verbose():
                    warning("g4f returned empty URL.")
                return None

            # Download the image
            img_resp = requests.get(image_url, timeout=120)
            img_resp.raise_for_status()

            if len(img_resp.content) < 1000:
                if get_verbose():
                    warning("g4f image too small, likely an error page.")
                return None

            return self._persist_image(img_resp.content, "g4f Pollinations/Flux")

        except Exception as e:
            err_str = str(e)
            if (
                "quota" in err_str.lower()
                or "exceeded" in err_str.lower()
                or "429" in err_str
            ):
                if get_verbose():
                    warning(f"g4f quota exhausted: {e}")
                self._g4f_quota_exhausted = True
            elif get_verbose():
                warning(f"g4f image generation failed: {e}")
            return None

    def _simplify_prompt_for_pixabay(self, prompt: str) -> str:
        """
        Simplifies a verbose image prompt to 2-3 key nouns for better Pixabay search results.

        Args:
            prompt (str): Full image prompt

        Returns:
            query (str): Simplified search query
        """
        # Remove common filler words and keep key nouns
        stop_words = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "and",
            "but",
            "or",
            "nor",
            "not",
            "so",
            "yet",
            "both",
            "either",
            "that",
            "this",
            "these",
            "those",
            "it",
            "its",
            "showing",
            "depicting",
            "featuring",
            "beautiful",
            "stunning",
            "amazing",
            "incredible",
            "dramatic",
            "view",
            "scene",
            "image",
            "photo",
            "picture",
            "background",
        }

        words = re.sub(r"[^a-zA-Z\s]", "", prompt).split()
        key_words = [w for w in words if w.lower() not in stop_words and len(w) > 2]

        # Take first 3-4 key nouns for best Pixabay results
        query = " ".join(key_words[:4])
        return query if query else prompt[:50]

    def generate_image_pixabay(self, prompt: str) -> str:
        """
        Downloads a stock photo from Pixabay matching the prompt.
        Used as fallback when AI image generation fails.

        Args:
            prompt (str): Search query for Pixabay

        Returns:
            path (str): The path to the downloaded image, or None on failure.
        """
        api_key = os.environ.get("PIXABAY_API_KEY", "")
        if not api_key:
            if get_verbose():
                warning("PIXABAY_API_KEY not set. Cannot use Pixabay fallback.")
            return None

        # Simplify prompt to key nouns for better Pixabay results
        search_query = self._simplify_prompt_for_pixabay(prompt)

        try:
            params = {
                "key": api_key,
                "q": search_query,
                "image_type": "photo",
                "orientation": "vertical",
                "per_page": 3,
                "safesearch": "true",
            }
            resp = requests.get(
                "https://pixabay.com/api/",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", [])
            if not hits:
                if get_verbose():
                    warning(f"Pixabay returned no results for: {search_query}")
                return None

            # Pick a random result for variety
            hit = random.choice(hits)
            image_url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not image_url:
                return None

            # Download the image
            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()

            return self._persist_image(img_resp.content, "Pixabay")

        except Exception as e:
            if get_verbose():
                warning(f"Pixabay fallback failed: {e}")
            return None

    def generate_image_cloudflare(self, prompt: str) -> str:
        """
        Generates an AI image using Cloudflare Workers AI.
        Model priority: Leonardo Phoenix > Flux Schnell > Flux Klein > Flux Dev > SDXL
        Free tier: 100,000 calls/day. No rate limit issues.
        """
        worker_url = os.environ.get("CF_WORKER_URL", "")
        api_key = os.environ.get("CF_WORKER_API_KEY", "")
        if not worker_url or not api_key:
            if get_verbose():
                warning(
                    "CF_WORKER_URL or CF_WORKER_API_KEY not set. Skipping Cloudflare."
                )
            return None

        enhanced_prompt = f"{prompt}, Ghibli watercolor, high quality, detailed"

        # Model fallback chain: Leonardo Phoenix > Flux Schnell > Flux Klein > Flux Dev > SDXL
        models = [
            ("phoenix-1.0", "Leonardo Phoenix 1.0"),
            ("flux-1-schnell", "FLUX.1 Schnell"),
            ("flux-2-klein-4b", "FLUX.2 Klein 4B"),
            ("flux-2-dev", "FLUX.2 Dev"),
            ("sdxl", "Stable Diffusion v1.5"),
        ]

        for model_id, model_label in models:
            print(
                f"Generating AI image via Cloudflare ({model_label}): {prompt[:80]}..."
            )
            try:
                resp = requests.post(
                    worker_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"prompt": enhanced_prompt, "model": model_id},
                    timeout=120,
                )

                if resp.status_code == 429:
                    if get_verbose():
                        warning(
                            f"Cloudflare {model_label} rate limited (429). Trying next model..."
                        )
                    continue

                if resp.status_code in (401, 403):
                    if get_verbose():
                        warning(f"Cloudflare auth failed ({resp.status_code}).")
                    return None

                if resp.status_code >= 500:
                    # Log the actual error body for debugging
                    try:
                        error_body = resp.json()
                    except Exception:
                        error_body = resp.text[:500]
                    if get_verbose():
                        warning(
                            f"Cloudflare {model_label} server error ({resp.status_code}): {error_body}"
                        )
                    continue

                if resp.status_code != 200:
                    try:
                        error_body = resp.json()
                    except Exception:
                        error_body = resp.text[:500]
                    if get_verbose():
                        warning(
                            f"Cloudflare {model_label} returned {resp.status_code}: {error_body}"
                        )
                    continue

                if len(resp.content) < 1000:
                    if get_verbose():
                        warning(
                            f"Cloudflare {model_label} returned too small response. Trying next..."
                        )
                    continue

                return self._persist_image(resp.content, f"Cloudflare ({model_label})")

            except Exception as e:
                if get_verbose():
                    warning(
                        f"Cloudflare {model_label} failed: {e}. Trying next model..."
                    )
                continue

        # All models with model param failed — try old worker (no model param, SDXL only)
        if get_verbose():
            info(
                "All models with model param failed. Trying legacy worker (SDXL, no model param)..."
            )
        try:
            resp = requests.post(
                worker_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"prompt": enhanced_prompt},
                timeout=120,
            )

            if resp.status_code == 200 and len(resp.content) >= 1000:
                return self._persist_image(resp.content, "Cloudflare (Legacy SDXL)")

            try:
                error_body = resp.json()
            except Exception:
                error_body = resp.text[:500]
            if get_verbose():
                warning(f"Legacy worker also failed ({resp.status_code}): {error_body}")
        except Exception as e:
            if get_verbose():
                warning(f"Legacy worker failed: {e}")

        if get_verbose():
            warning("All Cloudflare methods failed.")
        return None

    def generate_image(self, prompt: str, delay_between: int = 2) -> str:
        """
        Generates an AI Image based on the given prompt.
        Priority: Pollinations (paid) -> g4f (free) -> Cloudflare Workers AI -> Pixabay
        """
        # 1. Try Pollinations with API key (fastest, most reliable)
        if get_verbose():
            info("Trying Pollinations API...")
        result = self.generate_image_pollinations(prompt)
        if result is not None:
            time.sleep(delay_between)
            return result

        # 2. Try g4f (Pollinations free)
        if not getattr(self, "_g4f_quota_exhausted", False):
            if get_verbose():
                info("Pollinations failed. Trying g4f (free)...")
            result = self.generate_image_g4f(prompt)
            if result is not None:
                time.sleep(delay_between)
                return result
        elif get_verbose():
            info("g4f quota exhausted, skipping...")

        # 3. Try Cloudflare Workers AI (SDXL) - may be rate limited
        if get_verbose():
            info("Trying Cloudflare Workers AI (SDXL)...")
        result = self.generate_image_cloudflare(prompt)
        if result is not None:
            time.sleep(2)
            return result

        # 4. Try Pixabay - stock photos
        if get_verbose():
            info("All AI generation failed. Trying Pixabay stock photos...")
        result = self.generate_image_pixabay(prompt)
        if result is not None:
            time.sleep(5)
            return result

        # All failed - caller will use placeholder
        if get_verbose():
            warning("All image generation methods failed.")
        return None

    def generate_script_to_speech(self, tts_instance: TTS) -> str:
        """
        Converts the generated script into Speech using KittenTTS and returns the path to the wav file.

        Args:
            tts_instance (tts): Instance of TTS Class.

        Returns:
            path_to_wav (str): Path to generated audio (WAV Format).
        """
        path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".wav")

        # Clean script, remove every character that is not a word character, a space, a period, a question mark, or an exclamation mark.
        self.script = re.sub(r"[^\w\s.?!]", "", self.script)

        tts_instance.synthesize(self.script, path)

        self.tts_path = path

        if get_verbose():
            info(f' => Wrote TTS to "{path}"')

        return path

    def add_video(self, video: dict) -> None:
        """
        Adds a video to the cache.

        Args:
            video (dict): The video to add

        Returns:
            None
        """
        videos = self.get_videos()
        videos.append(video)

        cache = get_youtube_cache_path()

        with open(cache, "r") as file:
            previous_json = json.loads(file.read())

            # Find our account
            accounts = previous_json["accounts"]
            for account in accounts:
                if account["id"] == self._account_uuid:
                    account["videos"].append(video)

            # Commit changes
            with open(cache, "w") as f:
                f.write(json.dumps(previous_json))

    def generate_subtitles(self, audio_path: str) -> str:
        """
        Generates subtitles for the audio using the configured STT provider.

        Args:
            audio_path (str): The path to the audio file.

        Returns:
            path (str): The path to the generated SRT File.
        """
        provider = str(get_stt_provider() or "local_whisper").lower()

        if provider == "local_whisper":
            return self.generate_subtitles_local_whisper(audio_path)

        if provider == "third_party_assemblyai":
            return self.generate_subtitles_assemblyai(audio_path)

        warning(f"Unknown stt_provider '{provider}'. Falling back to local_whisper.")
        return self.generate_subtitles_local_whisper(audio_path)

    def generate_subtitles_assemblyai(self, audio_path: str) -> str:
        """
        Generates subtitles using AssemblyAI.

        Args:
            audio_path (str): Audio file path

        Returns:
            path (str): Path to SRT file
        """
        aai.settings.api_key = get_assemblyai_api_key()
        config = aai.TranscriptionConfig()
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)
        subtitles = transcript.export_subtitles_srt()

        srt_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".srt")

        with open(srt_path, "w") as file:
            file.write(subtitles)

        return srt_path

    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        Formats a timestamp in seconds to SRT format.

        Args:
            seconds (float): Seconds

        Returns:
            ts (str): HH:MM:SS,mmm
        """
        total_millis = max(0, int(round(seconds * 1000)))
        hours = total_millis // 3600000
        minutes = (total_millis % 3600000) // 60000
        secs = (total_millis % 60000) // 1000
        millis = total_millis % 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def generate_subtitles_local_whisper(self, audio_path: str) -> str:
        """
        Generates subtitles using local Whisper (faster-whisper).

        Args:
            audio_path (str): Audio file path

        Returns:
            path (str): Path to SRT file
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            error(
                "Local STT selected but 'faster-whisper' is not installed. "
                "Install it or switch stt_provider to third_party_assemblyai."
            )
            raise

        model = WhisperModel(
            get_whisper_model(),
            device=get_whisper_device(),
            compute_type=get_whisper_compute_type(),
        )
        segments, _ = model.transcribe(audio_path, vad_filter=True)

        lines = []
        for idx, segment in enumerate(segments, start=1):
            start = self._format_srt_timestamp(segment.start)
            end = self._format_srt_timestamp(segment.end)
            text = str(segment.text).strip()

            if not text:
                continue

            lines.append(str(idx))
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")

        subtitles = "\n".join(lines)
        srt_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".srt")
        with open(srt_path, "w", encoding="utf-8") as file:
            file.write(subtitles)

        return srt_path

    def combine(self) -> str:
        """
        Combines everything into the final video.

        Returns:
            path (str): The path to the generated MP4 File.
        """
        combined_image_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".mp4")
        threads = get_threads()
        tts_clip = AudioFileClip(self.tts_path)
        max_duration = tts_clip.duration
        req_dur = max_duration / len(self.images)

        # Make a generator that returns a TextClip when called with consecutive
        generator = lambda txt: TextClip(
            txt,
            font=os.path.join(get_fonts_dir(), get_font()),
            fontsize=100,
            color="#FFFF00",
            stroke_color="black",
            stroke_width=5,
            size=(1080, 1920),
            method="caption",
        )

        print(colored("[+] Combining images...", "blue"))

        # ── Ken Burns effect (pan + zoom) ──────────────────────────────────
        # Load images at higher resolution so zoom-out has pixels to work with.
        # We crop a 1080x1920 window from the larger source each frame.
        OUTPUT_W, OUTPUT_H = 1080, 1920
        # Source resolution: 25% larger than output so zoom-out stays sharp
        SRC_W = int(OUTPUT_W * 1.25)  # 1350
        SRC_H = int(OUTPUT_H * 1.25)  # 2400

        # Pre-load source images at the larger resolution
        source_images = [
            Image.open(p).convert("RGB").resize((SRC_W, SRC_H), Image.LANCZOS)
            for p in self.images
        ]

        # Build a list of (source_image_index, duration) for each segment
        segments = []  # (source_images index, duration)
        tot_dur = 0
        while tot_dur < max_duration:
            for img_idx in range(len(source_images)):
                segments.append((img_idx, req_dur))
                tot_dur += req_dur
                if tot_dur >= max_duration:
                    break

        num_segments = len(segments)
        total_dur = num_segments * req_dur

        # Pre-compute Ken Burns parameters for each segment.
        # Each segment gets a random zoom direction (in/out) and pan direction.
        # Zoom: start at 1.0x, end at 1.0 +/- 0.12x (12% change — subtle Ken Burns)
        # Pan: shift crop window by up to +/-8% of source dimensions.
        ken_burns_params = []
        for seg_idx in range(num_segments):
            zoom_start = 1.0
            # Random zoom: 88% to 112% of source (always within source bounds)
            zoom_end = random.uniform(0.88, 1.12)
            # Random pan offsets (fraction of source dimensions)
            pan_x_start = random.uniform(-0.05, 0.05)
            pan_y_start = random.uniform(-0.05, 0.05)
            pan_x_end = random.uniform(-0.08, 0.08)
            pan_y_end = random.uniform(-0.08, 0.08)
            ken_burns_params.append(
                {
                    "zoom_start": zoom_start,
                    "zoom_end": zoom_end,
                    "pan_x_start": pan_x_start,
                    "pan_y_start": pan_y_start,
                    "pan_x_end": pan_x_end,
                    "pan_y_end": pan_y_end,
                }
            )

        def make_frame(t):
            """Render a frame with Ken Burns pan+zoom effect."""
            # Determine which segment we're in
            seg_idx = max(0, min(int(t / req_dur), num_segments - 1))
            img_idx, seg_dur = segments[seg_idx]
            kb = ken_burns_params[seg_idx]

            # Local time within this segment [0, 1]
            seg_start = seg_idx * req_dur
            local_t = (t - seg_start) / seg_dur if seg_dur > 0 else 0
            local_t = max(0.0, min(1.0, local_t))

            # Interpolate zoom and pan
            zoom = kb["zoom_start"] + (kb["zoom_end"] - kb["zoom_start"]) * local_t
            pan_x = kb["pan_x_start"] + (kb["pan_x_end"] - kb["pan_x_start"]) * local_t
            pan_y = kb["pan_y_start"] + (kb["pan_y_end"] - kb["pan_y_start"]) * local_t

            # Crop window size (inverse of zoom: larger zoom = smaller crop)
            crop_w = int(SRC_W / zoom)
            crop_h = int(SRC_H / zoom)
            crop_w = min(crop_w, SRC_W)
            crop_h = min(crop_h, SRC_H)

            # Crop position: center + pan offset
            cx = (SRC_W - crop_w) // 2 + int(pan_x * SRC_W)
            cy = (SRC_H - crop_h) // 2 + int(pan_y * SRC_H)
            # Clamp to valid range
            cx = max(0, min(cx, SRC_W - crop_w))
            cy = max(0, min(cy, SRC_H - crop_h))

            # Crop from source, then resize to output resolution
            cropped = source_images[img_idx].crop((cx, cy, cx + crop_w, cy + crop_h))
            frame = cropped.resize((OUTPUT_W, OUTPUT_H), Image.LANCZOS)
            return np.array(frame)

        final_clip = VideoClip(make_frame, duration=total_dur)
        final_clip = final_clip.with_fps(30)
        random_song = choose_random_song()

        subtitles = None
        try:
            subtitles_path = self.generate_subtitles(self.tts_path)
            equalize_subtitles(subtitles_path, 10)
            subtitles = SubtitlesClip(subtitles_path, generator)
            subtitles = subtitles.with_position(("center", "center"))
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without subtitles: {e}")

        random_song_clip = AudioFileClip(random_song).with_fps(44100)

        # Turn down volume
        random_song_clip = random_song_clip.with_volume_scaled(0.1)
        comp_audio = CompositeAudioClip([tts_clip.with_fps(44100), random_song_clip])

        final_clip = final_clip.with_audio(comp_audio)
        # Use total_dur (matches frame buffer exactly) instead of tts_clip.duration
        # to avoid black frames when TTS is slightly longer than the frame coverage.
        final_clip = final_clip.with_duration(total_dur)

        if subtitles is not None:
            final_clip = CompositeVideoClip([final_clip, subtitles])

        final_clip.write_videofile(combined_image_path, threads=threads)

        success(f'Wrote Video to "{combined_image_path}"')

        return combined_image_path

    def generate_video(self, tts_instance: TTS) -> str:
        """
        Generates a YouTube Short based on the provided niche and language.

        Args:
            tts_instance (TTS): Instance of TTS Class.

        Returns:
            path (str): The path to the generated MP4 File.
        """
        # Generate the Topic
        self.generate_topic()

        # Generate the Script
        self.generate_script()

        # Generate the Metadata
        self.generate_metadata()

        # Generate the Image Prompts
        self.generate_prompts()

        # Generate the Images
        for prompt in self.image_prompts:
            result = self.generate_image(prompt)
            if result:
                self.images.append(result)

        # Generate the TTS
        self.generate_script_to_speech(tts_instance)

        # Combine everything
        path = self.combine()

        if get_verbose():
            info(f" => Generated Video: {path}")

        self.video_path = os.path.abspath(path)

        return path

    def get_channel_id(self) -> str:
        """
        Gets the Channel ID of the YouTube Account.

        Returns:
            channel_id (str): The Channel ID.
        """
        self.browser.get("https://studio.youtube.com")
        time.sleep(2)
        channel_id = self.browser.current_url.split("/")[-1]
        self.channel_id = channel_id
        return channel_id

    def upload_video(self, upload_id: int = None) -> tuple:
        """
        Uploads the video to YouTube using Selenium (synchronous).

        Args:
            upload_id (int, optional): Tracker upload ID for status updates.

        Returns:
            (success, result) (tuple[bool, str]): (True, youtube_url) on success,
                                                   (False, error_message) on failure.
        """
        from selenium.webdriver.common.action_chains import ActionChains

        self._ensure_browser()
        browser = self.browser

        try:
            # Generate metadata if not already done
            if not hasattr(self, "metadata") or not self.metadata:
                self.generate_topic()
                self.generate_script()
                self.generate_metadata()

            page = browser
            verbose = get_verbose()
            wait = self.wait

            # ── Step 1: Navigate to YouTube Studio ──
            if verbose:
                info("\t=> Navigating to YouTube Studio...")
            browser.get("https://studio.youtube.com")
            time.sleep(3)

            # ── Step 2: Click Create → Upload videos ──
            if verbose:
                info("\t=> Opening upload dialog...")
            try:
                create_btn = browser.find_element(
                    By.CSS_SELECTOR, '[aria-label="Create"]'
                )
                browser.execute_script("arguments[0].scrollIntoView();", create_btn)
                time.sleep(0.5)
                create_btn.click()
                time.sleep(2)

                # Click "Upload videos" from the dropdown
                upload_opt = browser.find_element(
                    By.XPATH, "//*[text()='Upload videos']"
                )
                upload_opt.click()
                time.sleep(3)
            except Exception as e:
                if verbose:
                    warning(f"Create/Upload click failed: {e}")
                # Fallback: use YouTube Studio upload URL
                browser.get("https://www.youtube.com/upload?redirect_to_login=1")
                time.sleep(5)

            # ── Step 3: Set video file using Selenium send_keys ──
            # Find ALL file inputs on page - use more robust selector
            if verbose:
                info("\t=> Setting video file...")

            time.sleep(3)

            # First try the specific selector, then fall back to any file input
            try:
                file_input = browser.find_element(
                    By.CSS_SELECTOR, "ytcp-uploads-file-picker input[type='file']"
                )
            except:
                # Fallback: find ANY file input on the page
                file_inputs = browser.find_elements(
                    By.CSS_SELECTOR, "input[type='file']"
                )
                if file_inputs:
                    file_input = file_inputs[0]
                else:
                    # Last resort: try to get all inputs via JS
                    file_input = browser.execute_script(
                        "return Array.from(document.querySelectorAll('input')).find(el => el.type === 'file');"
                    )
                    if not file_input:
                        return (False, "Could not find file input on upload page")

            file_input.send_keys(self.video_path)

            time.sleep(3)

            # Check for daily upload limit warning
            page_content = browser.page_source.lower()
            if (
                "daily upload limit" in page_content
                or "upload more videos daily" in page_content
            ):
                if verbose:
                    warning("\t=> Daily upload limit reached!")
                return (
                    False,
                    "Daily upload limit reached. Upload more videos daily after a one-time verification or wait 24 hours.",
                )

            try:
                error_elements = browser.find_elements(
                    By.CSS_SELECTOR,
                    "[class*='error'], [class*='warning'], [role='alert']",
                )
                for err in error_elements:
                    if err.text and (
                        "limit" in err.text.lower() or "quota" in err.text.lower()
                    ):
                        if verbose:
                            warning(f"\t=> Error detected: {err.text}")
                        return (False, f"Upload blocked: {err.text}")
            except Exception:
                pass

            # ── Step 4: Wait for upload form ──
            if verbose:
                info("\t=> Waiting for upload form...")
            try:
                wait.until(EC.presence_of_element_located((By.ID, YOUTUBE_TEXTBOX_ID)))
            except Exception:
                return (False, "Upload form textboxes not found after 120s.")

            time.sleep(3)

            try:
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.CSS_SELECTOR, ".dialog-scrim")
                    )
                )
                time.sleep(1)
            except Exception:
                pass

            # ── Step 5: Fill title ──
            if verbose:
                info("\t=> Setting title...")
            time.sleep(2)
            title_el = browser.find_element(By.ID, YOUTUBE_TEXTBOX_ID)

            browser.execute_script("arguments[0].scrollIntoView();", title_el)
            browser.execute_script("arguments[0].click();", title_el)
            time.sleep(0.5)

            # Select all and delete
            actions = ActionChains(browser)
            actions.move_to_element(title_el)
            actions.click()
            actions.key_down(Keys.CONTROL)
            actions.send_keys("a")
            actions.key_up(Keys.CONTROL)
            actions.perform()
            time.sleep(0.2)
            title_el.send_keys(self.metadata["title"])

            # ── Step 6: Fill description ──
            if verbose:
                info("\t=> Setting description...")
            time.sleep(2)
            # Press Escape to close any popups
            actions = ActionChains(browser)
            actions.send_keys(Keys.ESCAPE)
            actions.perform()
            time.sleep(0.5)

            all_textboxes = browser.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)
            description_el = (
                all_textboxes[-1] if len(all_textboxes) >= 2 else all_textboxes[0]
            )
            browser.execute_script("arguments[0].scrollIntoView();", description_el)
            browser.execute_script("arguments[0].click();", description_el)
            time.sleep(0.5)

            # Select all and delete
            actions = ActionChains(browser)
            actions.move_to_element(description_el)
            actions.click()
            actions.key_down(Keys.CONTROL)
            actions.send_keys("a")
            actions.key_up(Keys.CONTROL)
            actions.perform()
            time.sleep(0.2)
            description_el.send_keys(self.metadata["description"])

            time.sleep(0.5)

            # ── Step 7: Click "Show more" ──
            time.sleep(2)
            try:
                show_more = browser.find_element(By.ID, "toggle-button")
                if show_more.is_displayed():
                    browser.execute_script("arguments[0].scrollIntoView();", show_more)
                    time.sleep(0.5)
                    show_more.click()
                    time.sleep(2)
                    if verbose:
                        info("\t=> Clicked Show more")
            except Exception as e:
                if verbose:
                    warning(f"Show more click failed: {e}")

            # ── Step 8: Set tags ──
            try:
                tags = self.metadata.get("tags", [])
                if tags:
                    if verbose:
                        info(f"\t=> Setting {len(tags)} tags...")
                    time.sleep(1)
                    tags_input = browser.find_element(
                        By.CSS_SELECTOR, "input[aria-label='Tags']"
                    )
                    if tags_input.is_displayed():
                        browser.execute_script(
                            "arguments[0].scrollIntoView();", tags_input
                        )
                        time.sleep(0.5)
                        tags_input.click()
                        time.sleep(0.5)
                        tags_str = ", ".join(tags[:15])
                        tags_input.send_keys(tags_str)
                        time.sleep(1)
                        if verbose:
                            info("\t=> Tags set successfully")
            except Exception as e:
                if verbose:
                    warning(f"Could not set tags: {e}")

            # ── Step 9: Made for kids ──
            if verbose:
                info("\t=> Setting 'made for kids' option...")
            time.sleep(1)
            try:
                if not get_is_for_kids():
                    not_kids = browser.find_element(
                        By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME
                    )
                    browser.execute_script("arguments[0].scrollIntoView();", not_kids)
                    time.sleep(0.5)
                    not_kids.click()
                else:
                    kids = browser.find_element(By.NAME, YOUTUBE_MADE_FOR_KIDS_NAME)
                    browser.execute_script("arguments[0].scrollIntoView();", kids)
                    time.sleep(0.5)
                    kids.click()
                time.sleep(2)
            except Exception as e:
                if verbose:
                    warning(f"Made for kids click failed: {e}")

            time.sleep(1)

            # ── Step 10: Click Next 3 times ──
            if verbose:
                info("\t=> Clicking next...")
            for i in range(3):
                if verbose:
                    info(f"\t=> Next click {i + 1}/3...")
                try:
                    next_btn = browser.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
                    wait.until(EC.visibility_of(next_btn))
                    next_btn.click()
                    time.sleep(2)
                except Exception as e:
                    if verbose:
                        warning(f"Next button {i + 1} failed: {e}")

            # ── Step 11: Set visibility to Public ──
            time.sleep(2)
            if verbose:
                info("\t=> Setting as public...")

            public_selected = False

            # Multiple selector strategies for robustness
            def get_public_radio(strategy_idx):
                strategies = [
                    lambda: browser.find_element(
                        By.XPATH, "//tp-yt-paper-radio-button[.//span[text()='Public']]"
                    ),
                    lambda: browser.find_element(
                        By.CSS_SELECTOR, "tp-yt-paper-radio-button"
                    ),
                    lambda: browser.find_element(
                        By.CSS_SELECTOR, "input[type='radio']"
                    ),
                    lambda: browser.find_element(
                        By.XPATH, "//ytcp-video-visibility//input[@type='radio']"
                    ),
                ]
                if strategy_idx < len(strategies):
                    return strategies[strategy_idx]()
                return None

            for attempt in range(5):
                try:
                    # Try each selector strategy
                    for selector_idx in range(4):
                        try:
                            public_radio = get_public_radio(selector_idx)
                            if public_radio and public_radio.is_displayed():
                                browser.execute_script(
                                    "arguments[0].scrollIntoView();", public_radio
                                )
                                time.sleep(0.5)
                                public_radio.click()
                                # Explicit wait after clicking (2000ms+) before verification
                                time.sleep(2.5)
                                # Verify aria-checked="true" - loop until confirmed
                                for verify_attempt in range(3):
                                    is_checked = public_radio.get_attribute(
                                        "aria-checked"
                                    )
                                    if is_checked == "true":
                                        public_selected = True
                                        if verbose:
                                            info(
                                                f"\t=> Public selected (strategy {selector_idx + 1}, attempt {attempt + 1})"
                                            )
                                        break
                                    time.sleep(1)
                                if public_selected:
                                    break
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Strategy {selector_idx + 1} failed: {e}")
                            continue

                    if public_selected:
                        break
                except Exception as e:
                    if verbose:
                        warning(f"\t=> Public radio attempt {attempt + 1} failed: {e}")
                time.sleep(1.5)

            if not public_selected and verbose:
                error(
                    "\t=> CRITICAL: Could not set visibility during upload! Will fix via edit page."
                )

            # ── Step 12: Click Done ──
            if verbose:
                info("\t=> Clicking done button...")
            time.sleep(1)
            try:
                done_btn = browser.find_element(By.ID, YOUTUBE_DONE_BUTTON_ID)
                wait.until(EC.visibility_of(done_btn))
                done_btn.click()
                time.sleep(2)
            except Exception as e:
                if verbose:
                    warning(f"Done button click failed: {e}")

            # ── Step 13: Wait for upload to complete ──
            if verbose:
                info("\t=> Waiting for upload to complete...")

            upload_confirmed = False
            # Wait up to 5 minutes (150 * 2s = 300s) for large video uploads
            for wait_round in range(150):
                time.sleep(2)
                try:
                    page_content = browser.page_source
                    current_url = browser.current_url
                    if (
                        "Upload complete" in page_content
                        or "uploaded" in page_content.lower()
                    ):
                        upload_confirmed = True
                        if verbose:
                            info(f"\t=> Upload confirmed after {(wait_round + 1) * 2}s")
                        break
                    if "videos/short" in current_url:
                        upload_confirmed = True
                        if verbose:
                            info(
                                f"\t=> Redirected to videos page after {(wait_round + 1) * 2}s"
                            )
                        break
                    if "/video/" in current_url and "/edit" in current_url:
                        upload_confirmed = True
                        if verbose:
                            info(
                                f"\t=> On edit page, upload likely complete after {(wait_round + 1) * 2}s"
                            )
                        break
                    # Also check if URL contains video ID pattern (11 chars)
                    if "/video/" in current_url:
                        video_id_match = re.search(
                            r"/video/([a-zA-Z0-9_-]{11})", current_url
                        )
                        if video_id_match:
                            upload_confirmed = True
                            if verbose:
                                info(
                                    f"\t=> Found video ID in URL after {(wait_round + 1) * 2}s"
                                )
                            break
                except Exception:
                    pass

            if not upload_confirmed and verbose:
                warning(
                    "\t=> Upload not confirmed after 300s, checking videos page anyway..."
                )

            time.sleep(3)

            # ── Step 14: Get latest video from YouTube Studio ──
            if verbose:
                info("\t=> Getting video URL...")

            # First try to get video ID from current URL if we're on an upload result page
            video_id = None
            current_url = browser.current_url

            # Check for video ID in URL (various patterns)
            if "/video/" in current_url:
                try:
                    video_id_match = re.search(
                        r"/video/([a-zA-Z0-9_-]{11})", current_url
                    )
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        if verbose:
                            info(f"\t=> Got video ID from URL: {video_id}")
                except Exception:
                    pass

            # If no video ID from URL, try the videos page
            if not video_id:
                browser.get("https://studio.youtube.com/videos")
                time.sleep(5)

                # Try multiple selectors for video rows
                video_rows = []
                for selector in ["ytcp-video-row", "[class*='video-row']", "tbody tr"]:
                    try:
                        video_rows = browser.find_elements(By.CSS_SELECTOR, selector)
                        if video_rows:
                            if verbose:
                                info(
                                    f"\t=> Found {len(video_rows)} video rows using selector: {selector}"
                                )
                            break
                    except Exception:
                        continue

                if not video_rows:
                    # Last resort: try to find any table with links
                    try:
                        links = browser.find_elements(
                            By.CSS_SELECTOR, "a[href*='/video/']"
                        )
                        if links:
                            if verbose:
                                info(f"\t=> Found {len(links)} video links")
                            first_link = links[0]
                            href = first_link.get_attribute("href")
                            if href and "/video/" in href:
                                video_id = (
                                    href.split("/video/")[-1]
                                    .split("/")[0]
                                    .split("?")[0]
                                )
                    except Exception:
                        pass

                if video_rows and not video_id:
                    first_video = video_rows[0]
                    try:
                        video_id = first_video.get_attribute("video-id")
                    except Exception:
                        pass

            if not video_id:
                try:
                    content = browser.page_source
                    matches = re.findall(r'video-id="([a-zA-Z0-9_-]{11})"', content)
                    if matches:
                        video_id = matches[0]
                        if verbose:
                            info(f"\t=> Found video ID from page source: {video_id}")
                except Exception:
                    pass

            if not video_id:
                return (False, "Could not extract video ID from uploaded video")

            url = build_url(video_id)

            # Verify title
            try:
                title_el = first_video.find_element(By.CSS_SELECTOR, "#video-title")
                uploaded_title = title_el.text.strip()
                if verbose:
                    info(f"\t=> Verified video title: {uploaded_title[:60]}")
            except Exception:
                pass

            self.uploaded_video_url = url
            if verbose:
                success(f" => Uploaded Video: {url}")

            # ── Step 15: POST-UPLOAD — ALWAYS force visibility to Public via edit page ──
            if verbose:
                info("\t=> Forcing video visibility to Public via edit page...")

            visibility_fixed = False

            # Multiple visibility badge selectors
            visibility_badge_selectors = [
                "ytcp-video-visibility-badge",
                "ytcp-video-metadata-editor-basics ytcp-video-visibility-badge",
                "[aria-label*='visibility']",
                ".ytcp-video-visibility-badge",
                "ytcp-form-video-visibility",
            ]

            for fix_attempt in range(5):
                try:
                    browser.get(f"https://studio.youtube.com/video/{video_id}/edit")
                    time.sleep(5)

                    # Method 1: Try multiple visibility badge selectors
                    vis_badge = None
                    for badge_sel in visibility_badge_selectors:
                        try:
                            badge = browser.find_element(By.CSS_SELECTOR, badge_sel)
                            if badge.is_displayed():
                                vis_badge = badge
                                break
                        except Exception:
                            continue

                    if vis_badge:
                        browser.execute_script(
                            "arguments[0].scrollIntoView();", vis_badge
                        )
                        time.sleep(1)
                        vis_badge.click()
                        time.sleep(2.5)

                        # Try to find and click Public radio option
                        try:
                            public_opt = browser.find_element(
                                By.XPATH,
                                "//tp-yt-paper-radio-button[.//span[text()='Public']]",
                            )
                            if public_opt.is_displayed():
                                public_opt.click()
                                time.sleep(2.5)
                        except Exception:
                            pass

                        # Click Done button
                        try:
                            done_btn = browser.find_element(
                                By.CSS_SELECTOR, "ytcp-button#done-button, #done-button"
                            )
                            wait.until(EC.visibility_of(done_btn))
                            done_btn.click()
                            time.sleep(2.5)
                        except Exception:
                            pass

                        # Click Save button
                        try:
                            save_btn = browser.find_element(
                                By.CSS_SELECTOR, "ytcp-button#save-button, #save-button"
                            )
                            browser.execute_script(
                                "arguments[0].scrollIntoView();", save_btn
                            )
                            time.sleep(1)
                            save_btn.click()
                            time.sleep(3)
                        except Exception:
                            pass

                        # Verify visibility was set
                        try:
                            vis_badge_verify = browser.find_element(
                                By.CSS_SELECTOR, "ytcp-video-visibility-badge"
                            )
                            badge_text = vis_badge_verify.text
                            if "public" in badge_text.lower():
                                visibility_fixed = True
                                if verbose:
                                    info(
                                        f"\t=> Visibility set to Public (attempt {fix_attempt + 1})"
                                    )
                                break
                        except Exception:
                            pass

                    # Method 2: Direct URL navigation and form submission
                    if not visibility_fixed:
                        try:
                            browser.get(
                                f"https://studio.youtube.com/video/{video_id}/details"
                            )
                            time.sleep(4)

                            # Find and click visibility dropdown
                            vis_dropdown_selectors = [
                                "ytcp-video-visibility-select",
                                "[aria-label*='visibility']",
                                ".visibility-select",
                            ]
                            vis_dropdown = None
                            for sel in vis_dropdown_selectors:
                                try:
                                    vis_dropdown = browser.find_element(
                                        By.CSS_SELECTOR, sel
                                    )
                                    if vis_dropdown.is_displayed():
                                        break
                                except Exception:
                                    continue

                            if vis_dropdown and vis_dropdown.is_displayed():
                                vis_dropdown.click()
                                time.sleep(2)

                                public_option = browser.find_element(
                                    By.XPATH,
                                    "//tp-yt-paper-item[contains(., 'Public')] | //paper-item[contains(., 'Public')]",
                                )
                                public_option.click()
                                time.sleep(2)

                                # Save
                                save_btn = browser.find_element(
                                    By.CSS_SELECTOR, "ytcp-button#save-button"
                                )
                                save_btn.click()
                                time.sleep(3)

                                visibility_fixed = True
                                if verbose:
                                    info(
                                        f"\t=> Visibility set via dropdown (attempt {fix_attempt + 1})"
                                    )
                                break
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Dropdown method failed: {e}")

                    time.sleep(2)
                except Exception as e:
                    if verbose:
                        warning(
                            f"\t=> Visibility fix attempt {fix_attempt + 1} failed: {e}"
                        )
                    time.sleep(3)

            if not visibility_fixed:
                if verbose:
                    error(
                        "\t=> CRITICAL: Failed to set visibility to Public after 3 attempts!"
                    )
            else:
                if verbose:
                    info("\t=> Video visibility confirmed as Public")

            # Add video to cache
            self.add_video(
                {
                    "title": self.metadata["title"],
                    "description": self.metadata["description"],
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            return (True, url)

        except Exception as e:
            error(f"Upload failed: {e}")
            import traceback

            error(traceback.format_exc())
            return (False, str(e))

    def upload_to_facebook(self) -> tuple:
        """
        Uploads the video to Facebook Reels using Selenium.
        Uses the same Firefox profile context for authentication.

        Returns:
            tuple: (success, url_or_error_message)
        """
        self._ensure_browser()
        browser = self.browser
        wait = self.wait
        verbose = get_verbose()

        try:
            if verbose:
                info("\t=> Navigating to Facebook...")
            browser.get("https://www.facebook.com")
            time.sleep(5)

            # Try to find the Create Reel button or file upload
            if verbose:
                info("\t=> Looking for create/reel option...")

            # Try to find file input for video upload
            try:
                file_input = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[type="file"]')
                    )
                )
            except Exception:
                # Try alternative: look for "Create Reel" or upload button
                if verbose:
                    info("\t=> Looking for upload button...")
                try:
                    upload_btn = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, "//*[contains(text(), 'Create Reel')]")
                        )
                    )
                    upload_btn.click()
                    time.sleep(3)
                    file_input = wait.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, 'input[type="file"]')
                        )
                    )
                except Exception:
                    file_input = None

            if file_input:
                if verbose:
                    info("\t=> Setting video file...")
                file_input.send_keys(self.video_path)
                time.sleep(5)

                # Fill description/caption
                if verbose:
                    info("\t=> Setting description...")
                # Try common Facebook caption selectors
                caption_selectors = [
                    (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
                    (By.TAG_NAME, "textarea"),
                    (By.CSS_SELECTOR, 'input[aria-label*="description"]'),
                    (By.CSS_SELECTOR, 'input[aria-label*="caption"]'),
                ]
                caption_el = None
                for by, selector in caption_selectors:
                    try:
                        caption_el = wait.until(
                            EC.visibility_of_element_located((by, selector))
                        )
                        if caption_el:
                            caption_el.click()
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue

                if caption_el:
                    desc = self.metadata.get(
                        "description", self.metadata.get("title", "")
                    )
                    caption_el.clear()
                    caption_el.send_keys(desc[:2000])  # Facebook limit
                    if verbose:
                        info("\t=> Description set")

                time.sleep(2)

                # Click Share/Post button
                if verbose:
                    info("\t=> Clicking Share...")
                share_selectors = [
                    (By.CSS_SELECTOR, 'button[aria-label*="Share"]'),
                    (By.XPATH, "//button[contains(text(), 'Share')]"),
                    (By.XPATH, "//button[contains(text(), 'Post')]"),
                    (By.XPATH, "//button[contains(text(), 'Next')]"),
                ]
                for by, selector in share_selectors:
                    try:
                        share_btn = wait.until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        share_btn.click()
                        if verbose:
                            info("\t=> Share button clicked")
                        break
                    except Exception:
                        continue

                # Wait for upload confirmation
                fb_url = ""
                if verbose:
                    info("\t=> Waiting for Facebook upload...")
                for _ in range(30):
                    time.sleep(2)
                    content = browser.page_source
                    if "published" in content.lower() or "success" in content.lower():
                        if verbose:
                            success("\t=> Facebook upload confirmed")
                        try:
                            current_url = browser.current_url
                            if "/reel/" in current_url or "/video/" in current_url:
                                fb_url = current_url
                            elif "/post/" in current_url:
                                fb_url = current_url
                            else:
                                try:
                                    post_links = browser.find_elements(
                                        By.CSS_SELECTOR,
                                        'a[href*="/reel/"], a[href*="/video/"], a[href*="/posts/"]',
                                    )
                                    for link in post_links:
                                        href = link.get_attribute("href")
                                        if (
                                            href
                                            and "facebook.com" in href
                                            and ("/reel/" in href or "/video/" in href)
                                        ):
                                            fb_url = href
                                            break
                                except Exception:
                                    pass

                            if not fb_url:
                                fb_url = (
                                    current_url
                                    if current_url and "facebook.com" in current_url
                                    else "https://www.facebook.com"
                                )
                        except Exception:
                            fb_url = "https://www.facebook.com"
                        return (True, fb_url)
                    if "error" in content.lower() and "try again" in content.lower():
                        if verbose:
                            warning("\t=> Facebook upload reported an error")
                        return (False, "Facebook upload reported an error")

                if verbose:
                    warning("\t=> Facebook upload not confirmed after 60s")
                return (False, "Facebook upload not confirmed after 60s")

            return (False, "Could not find file input for upload")

        except Exception as e:
            error(f"Facebook upload failed: {e}")
            if verbose:
                import traceback

                error(traceback.format_exc())
            return (False, str(e))

    def upload_to_tiktok(self) -> tuple:
        """
        Uploads the video to TikTok using Selenium.
        Uses the same Firefox profile context for authentication.

        Returns:
            tuple: (success, url_or_error_message)
        """
        self._ensure_browser()
        browser = self.browser
        wait = self.wait
        verbose = get_verbose()

        try:
            if verbose:
                info("\t=> Navigating to TikTok upload...")
            browser.get("https://www.tiktok.com/tiktokstudio/upload?from=webapp")
            time.sleep(5)

            # Wait for upload area
            if verbose:
                info("\t=> Waiting for upload interface...")

            # TikTok uses a file input for upload
            try:
                file_input = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'input[type="file"]')
                    )
                )
            except Exception:
                if verbose:
                    warning(
                        "\t=> File input not visible, trying alternative selectors..."
                    )
                alt_selectors = [
                    (By.CSS_SELECTOR, 'input[data-e2e="upload-input"]'),
                    (By.CSS_SELECTOR, 'input[accept*="video"]'),
                ]
                file_input = None
                for by, sel in alt_selectors:
                    try:
                        file_input = wait.until(
                            EC.presence_of_element_located((by, sel))
                        )
                        if file_input:
                            break
                    except Exception:
                        continue

            if file_input:
                if verbose:
                    info("\t=> Setting video file...")
                file_input.send_keys(self.video_path)
                time.sleep(8)

                # Fill description/caption
                if verbose:
                    info("\t=> Setting caption...")
                caption_selectors = [
                    (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
                    (By.CSS_SELECTOR, 'textarea[placeholder*="caption"]'),
                    (By.CSS_SELECTOR, 'textarea[placeholder*="description"]'),
                    (By.CSS_SELECTOR, 'div[data-e2e="tiktok-caption"]'),
                ]
                caption_el = None
                for by, selector in caption_selectors:
                    try:
                        caption_el = wait.until(
                            EC.visibility_of_element_located((by, selector))
                        )
                        if caption_el:
                            caption_el.click()
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue

                if caption_el:
                    title = self.metadata.get("title", "")
                    caption_el.send_keys(title[:2200])  # TikTok caption limit
                    if verbose:
                        info("\t=> Caption set")

                time.sleep(3)

                # Click Post button
                tt_url = ""
                if verbose:
                    info("\t=> Clicking Post...")
                time.sleep(3)

                post_selectors = [
                    (By.CSS_SELECTOR, 'button[data-e2e="post-button"]'),
                    (By.XPATH, "//button[contains(text(), 'Post')]"),
                    (By.XPATH, "//button[contains(text(), 'Schedule')]"),
                    (By.CSS_SELECTOR, 'button[class*="postButton"]'),
                    (By.CSS_SELECTOR, 'button[class*="PostButton"]'),
                    (By.XPATH, "//button[.//span[contains(text(), 'Post')]]"),
                ]
                post_clicked = False
                for by, selector in post_selectors:
                    try:
                        post_btn = browser.find_element(by, selector)
                        if post_btn.is_displayed():
                            browser.execute_script(
                                "arguments[0].scrollIntoView();", post_btn
                            )
                            time.sleep(0.5)
                            browser.execute_script("arguments[0].click();", post_btn)
                            post_clicked = True
                            if verbose:
                                info(f"\t=> Post button clicked: {selector}")
                            break
                    except Exception:
                        continue

                # Last resort: try to find any button with "Post" text
                if not post_clicked:
                    try:
                        all_buttons = browser.find_elements(By.TAG_NAME, "button")
                        for btn in all_buttons:
                            if "post" in btn.text.lower() and btn.is_displayed():
                                browser.execute_script(
                                    "arguments[0].scrollIntoView();", btn
                                )
                                time.sleep(0.5)
                                browser.execute_script("arguments[0].click();", btn)
                                post_clicked = True
                                if verbose:
                                    info("\t=> Post button clicked (fallback)")
                                break
                    except Exception:
                        pass

                if not post_clicked:
                    if verbose:
                        warning("\t=> Post button not found, but file was uploaded")
                    return (True, "https://www.tiktok.com")

                # Wait for upload to complete and try to extract video URL
                if verbose:
                    info("\t=> Waiting for TikTok upload to complete...")

                # Wait for success message or redirect
                for wait_cycle in range(30):
                    time.sleep(2)
                    current_url = browser.current_url

                    # Check if redirected to video page
                    if "/video/" in current_url and "tiktok.com" in current_url:
                        tt_url = current_url
                        if verbose:
                            info(f"\t=> TikTok video URL extracted: {tt_url}")
                        return (True, tt_url)

                    # Check for success message in page
                    page_content = browser.page_source.lower()
                    if "posted" in page_content or "success" in page_content:
                        if verbose:
                            info("\t=> TikTok upload confirmed")

                        # Wait a bit more for page to stabilize
                        time.sleep(3)

                        # Try multiple strategies to find video URL
                        # Strategy 1: Look for canonical URL meta tag
                        try:
                            canonical = browser.find_element(
                                By.CSS_SELECTOR, 'link[rel="canonical"]'
                            )
                            canonical_href = canonical.get_attribute("href")
                            if canonical_href and "/video/" in canonical_href:
                                tt_url = canonical_href
                                if verbose:
                                    info(
                                        f"\t=> TikTok video URL from canonical: {tt_url}"
                                    )
                                return (True, tt_url)
                        except Exception:
                            pass

                        # Strategy 2: Look for og:url meta tag
                        try:
                            og_url = browser.find_element(
                                By.CSS_SELECTOR, 'meta[property="og:url"]'
                            )
                            og_url_value = og_url.get_attribute("content")
                            if og_url_value and "/video/" in og_url_value:
                                tt_url = og_url_value
                                if verbose:
                                    info(f"\t=> TikTok video URL from og:url: {tt_url}")
                                return (True, tt_url)
                        except Exception:
                            pass

                        # Strategy 3: Look for video links in page
                        try:
                            video_links = browser.find_elements(
                                By.CSS_SELECTOR, 'a[href*="/video/"]'
                            )
                            for link in video_links:
                                href = link.get_attribute("href")
                                if href and "tiktok.com" in href and "/video/" in href:
                                    tt_url = href
                                    if verbose:
                                        info(f"\t=> TikTok video URL found: {tt_url}")
                                    return (True, tt_url)
                        except Exception:
                            pass
                        break

                # If still no URL, try to navigate to profile to find latest video
                if not tt_url:
                    try:
                        if verbose:
                            info("\t=> Trying to extract URL from profile...")
                        # Navigate to TikTok homepage to find profile
                        browser.get("https://www.tiktok.com")
                        time.sleep(5)

                        # Look for profile link (usually contains @username)
                        try:
                            profile_links = browser.find_elements(
                                By.CSS_SELECTOR, 'a[href*="@"]'
                            )
                            if profile_links:
                                profile_links[0].click()
                                time.sleep(5)
                                # Now look for the first video on profile
                                video_links = browser.find_elements(
                                    By.CSS_SELECTOR, 'a[href*="/video/"]'
                                )
                                for link in video_links:
                                    href = link.get_attribute("href")
                                    if href and "/video/" in href:
                                        tt_url = href
                                        if verbose:
                                            info(
                                                f"\t=> TikTok video URL from profile: {tt_url}"
                                            )
                                        return (True, tt_url)
                        except Exception:
                            pass

                        # Fallback: look for any video link in the current page
                        all_links = browser.find_elements(By.TAG_NAME, "a")
                        for link in all_links:
                            href = link.get_attribute("href")
                            if href and "/video/" in href and "tiktok.com" in href:
                                tt_url = href
                                if verbose:
                                    info(f"\t=> TikTok video URL from page: {tt_url}")
                                return (True, tt_url)
                    except Exception:
                        pass

                if not tt_url:
                    tt_url = "https://www.tiktok.com"
                    if verbose:
                        warning("\t=> Could not extract TikTok video URL")
                return (True, tt_url)

            return (False, "Could not find file input for upload")

        except Exception as e:
            error(f"TikTok upload failed: {e}")
            if verbose:
                import traceback

                error(traceback.format_exc())
            return (False, str(e))

    def upload_to_all_platforms(self) -> dict:
        results = {}

        try:
            info("Uploading to TikTok...")
            tt_success, tt_result = self.upload_to_tiktok()
            results["tiktok"] = (tt_success, tt_result)

            info("Uploading to Facebook...")
            fb_success, fb_result = self.upload_to_facebook()
            results["facebook"] = (fb_success, fb_result)

            info("Uploading to YouTube...")
            yt_success, yt_result = self.upload_video()
            results["youtube"] = (yt_success, yt_result)
        finally:
            info("Cleaning up...")
            self.cleanup()
            self._cleanup_temp_files()

        return results

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary media files in .mp directory."""
        import shutil

        mp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".mp"
        )
        if not os.path.exists(mp_dir):
            return

        # Keep only cache files
        keep_files = {"used_topics.json", "youtube.json", "last_run.json"}
        try:
            for item in os.listdir(mp_dir):
                if item in keep_files:
                    continue
                item_path = os.path.join(mp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception:
                    pass
            info("Temp files cleaned up.")
        except Exception as e:
            warning(f"Cleanup failed: {e}")

    def get_videos(self) -> List[dict]:
        """
        Gets the uploaded videos from the YouTube Channel.

        Returns:
            videos (List[dict]): The uploaded videos.
        """
        if not os.path.exists(get_youtube_cache_path()):
            # Create the cache file
            with open(get_youtube_cache_path(), "w") as file:
                json.dump({"videos": []}, file, indent=4)
            return []

        videos = []
        # Read the cache file
        with open(get_youtube_cache_path(), "r") as file:
            previous_json = json.loads(file.read())
            # Find our account
            accounts = previous_json["accounts"]
            for account in accounts:
                if account["id"] == self._account_uuid:
                    videos = account["videos"]

        return videos

    def cleanup(self) -> None:
        """Closes the Selenium browser and cleans up temp profile."""
        try:
            if self.browser:
                self.browser.quit()
        except Exception:
            pass

        if hasattr(self, "_temp_profile_dir") and self._temp_profile_dir:
            try:
                import shutil

                shutil.rmtree(self._temp_profile_dir, ignore_errors=True)
            except Exception:
                pass

        try:
            import glob

            for pattern in ["/tmp/mp2_*", "/tmp/selenium_*", "/tmp/firefox_*"]:
                for tmp_file in glob.glob(pattern):
                    try:
                        if os.path.isfile(tmp_file):
                            os.remove(tmp_file)
                        elif os.path.isdir(tmp_file):
                            shutil.rmtree(tmp_file, ignore_errors=True)
                    except Exception:
                        pass
        except Exception:
            pass

        self.browser = None
        self.page = None

    def __del__(self) -> None:
        self.cleanup()
