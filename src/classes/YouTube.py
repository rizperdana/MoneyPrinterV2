import re
import base64
import json
import time
import os
import random
import requests
import assemblyai as aai

from utils import *
from cache import *
from .Tts import TTS
from llm_provider import generate_text
from config import *
from status import *
from uuid import uuid4
from constants import *
from typing import List
from moviepy.editor import *
from termcolor import colored
from selenium_firefox import *
from selenium import webdriver
from moviepy.video.fx.all import crop
from moviepy.config import change_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from moviepy.video.tools.subtitles import SubtitlesClip
from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime

# Set ImageMagick Path
change_settings({"IMAGEMAGICK_BINARY": get_imagemagick_path()})


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

        # Initialize the Firefox profile
        self.options: Options = Options()

        # Set headless state of browser
        if get_headless():
            self.options.add_argument("--headless")

        if not os.path.isdir(self._fp_profile_path):
            raise ValueError(
                f"Firefox profile path does not exist or is not a directory: {self._fp_profile_path}"
            )

        self.options.add_argument("-profile")
        self.options.add_argument(self._fp_profile_path)

        # Set the service
        self.service: Service = Service(GeckoDriverManager().install())

        # Initialize the browser
        self.browser: webdriver.Firefox = webdriver.Firefox(
            service=self.service, options=self.options
        )

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
            resp = requests.get(wiki_url, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()

                # Today's news
                news = data.get("news", [])
                news_items = []
                for item in news[:8]:
                    story = re.sub(r'<[^>]+>', '', item.get("story", "")).strip()
                    links = item.get("links", [])
                    titles = [l.get("titles", {}).get("normalized", "") for l in links]
                    if story:
                        entry = story[:150]
                        if titles:
                            entry += f" ({', '.join(titles[:2])})"
                        news_items.append(entry)
                if news_items:
                    context_parts.append("Wikipedia Today's News:\n" +
                                         "\n".join(f"- {n}" for n in news_items))

                # Today's featured article
                tfa = data.get("tfa", {})
                if tfa:
                    title = tfa.get("titles", {}).get("normalized", "")
                    extract = tfa.get("extract", "")[:200]
                    if title and extract:
                        context_parts.append(f"Wikipedia Featured Article: {title}\n{extract}")

                # Most read articles
                most_read = data.get("mostread", {}).get("articles", [])
                if most_read:
                    top_titles = [a.get("titles", {}).get("normalized", "") 
                                  for a in most_read[:10] if a.get("titles")]
                    if top_titles:
                        context_parts.append("Wikipedia Most Read Today:\n" +
                                             "\n".join(f"- {t}" for t in top_titles if t))
        except Exception as e:
            if get_verbose():
                warning(f"Wikipedia API failed: {e}")

        # Method 2: Google Trends RSS
        try:
            for geo in ["US", ""]:
                trends_url = f"https://trends.google.com/trending/rss?geo={geo}"
                resp = requests.get(trends_url, timeout=10,
                                    headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    titles = re.findall(r'<title>(.*?)</title>', resp.text)
                    relevant = []
                    for t in titles[1:20]:
                        t_clean = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', t).strip()
                        if t_clean and len(t_clean) > 3:
                            relevant.append(t_clean)
                    if relevant:
                        label = f"Google Trends ({geo or 'Global'})"
                        context_parts.append(f"{label}:\n" +
                                             "\n".join(f"- {t}" for t in relevant[:15]))
                        break
        except Exception as e:
            if get_verbose():
                warning(f"Google Trends failed: {e}")

        # Method 3: DuckDuckGo for niche-specific topics
        try:
            search_query = f"{self.niche} latest news today"
            ddg_url = "https://api.duckduckgo.com/"
            params = {"q": search_query, "format": "json", "no_html": 1, "skip_disambig": 1}
            resp = requests.get(ddg_url, params=params, timeout=10,
                                headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                related = data.get("RelatedTopics", [])
                topics_found = []
                for item in related[:8]:
                    if isinstance(item, dict) and item.get("Text"):
                        topics_found.append(item["Text"][:120])
                if topics_found:
                    context_parts.append(f"DuckDuckGo {self.niche}:\n" +
                                         "\n".join(f"- {t}" for t in topics_found))
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
                info(f" => Research context ({len(research_context)} chars) gathered from web search")

            # Feed real research data into the LLM
            trend_prompt = f"""You are a YouTube content strategist. Based on the following REAL-TIME research data, pick the best trending topic for a YouTube Short in the niche: {self.niche}

=== RESEARCH DATA ===
{research_context}
=== END RESEARCH DATA ===

Based on the research above, generate 3 specific, engaging video topic ideas that:
1. Are related to what's ACTUALLY trending right now (from the data above)
2. Would perform well as YouTube Shorts (curiosity-driven, visual, surprising)
3. Are specific enough to make a 45-60 second video about

Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example:
1. Scientists just discovered a new species of glowing shark in the deep ocean
2. The James Webb telescope captured something that shouldn't exist
3. Why octopuses might be smarter than we thought - new study reveals shocking results"""
        else:
            # Fallback: no web research available, use LLM knowledge
            if get_verbose():
                warning("Web research unavailable. Using LLM knowledge for topic generation.")
            trend_prompt = f"""You are a YouTube content strategist. Think about what's trending RIGHT NOW in the niche: {self.niche}

Consider:
1. What topics are people searching for RIGHT NOW in this niche?
2. What recent discoveries, news, or viral moments relate to this niche?
3. What would make someone stop scrolling and watch?

Generate 3 specific, engaging video topic ideas that would perform well as YouTube Shorts right now.
Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example:
1. Scientists just discovered a new species of glowing shark in the deep ocean
2. The James Webb telescope captured something that shouldn't exist
3. Why octopuses might be smarter than we thought - new study reveals shocking results"""

        completion = str(self.generate_response(trend_prompt)).strip()

        # Parse numbered topics
        topics = []
        for line in completion.split('\n'):
            line = line.strip()
            match = re.match(r'^[\d]+[\.\)\-\s]+(.+)$', line)
            if match:
                topic = match.group(1).strip()
                if len(topic) > 20:
                    topics.append(topic)

        # Pick the best topic (first one, usually most engaging)
        if topics:
            selected = topics[0]
        else:
            # Fallback to simple generation
            selected = self.generate_response(
                f"Generate one specific, engaging video topic about: {self.niche}. One sentence only."
            )

        if not selected:
            error("Failed to generate Topic.")
            selected = f"Interesting facts about {self.niche}"

        self.subject = selected

        if get_verbose():
            info(f" => Trending topic selected: {selected[:80]}...")

        return selected

    def generate_script(self) -> str:
        """
        Generate a script for a video with clear Hook + Body + CTA structure.

        Structure:
        - Hook (first 1-2 sentences): Grab attention immediately with a bold claim or question
        - Body (3-4 key points): Main content with interesting facts/reasons
        - CTA (last 1-2 sentences): Call to action - subscribe, like, comment

        Returns:
            script (str): The script of the video.
        """
        sentence_length = get_script_sentence_length()
        prompt = f"""Write a YouTube Shorts script about: {self.subject}

The script MUST follow this exact structure:

SECTION 1 - HOOK (1-2 sentences):
Start with a shocking fact, bold claim, or intriguing question that grabs attention IMMEDIATELY.
Examples: "You won't believe what scientists just found..." or "This changes everything we know about..."

SECTION 2 - BODY ({sentence_length - 3} sentences):
Present 3-4 key points, facts, or reasons that support the hook.
Each sentence should build on the previous one. Keep it punchy and engaging.
Use transitions like "But here's the thing..." or "What's even crazier..."

SECTION 3 - CALL TO ACTION (1-2 sentences):
End with a compelling CTA. Ask viewers to like, subscribe, or comment.
Examples: "Follow for more mind-blowing facts!" or "Drop a comment if this blew your mind!"

RULES:
- Total: {sentence_length} SHORT sentences maximum
- NO markdown, NO formatting, NO titles, NO section labels
- NO "welcome to this video" or "in this video"
- NO narrator/voiceover indicators
- Write in {self.language}
- Get straight to the point
- Each sentence should be punchy (under 15 words when possible)

Subject: {self.subject}
Language: {self.language}

Return ONLY the raw script text. No labels, no formatting, just the spoken words."""

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
            sentences = [s.strip() for s in re.split(r'[.!?]+', completion) if len(s.strip()) > 5]
            info(f" => Script: {len(sentences)} sentences, {len(completion)} chars")

        return completion

    def generate_metadata(self) -> dict:
        """
        Generates Video metadata for the to-be-uploaded YouTube Short (Title, Description, Tags).

        Returns:
            metadata (dict): The generated metadata with keys: title, description, tags.
        """
        title = self.generate_response(
            f"Please generate a YouTube Video Title for the following subject, including hashtags: {self.subject}. Only return the title, nothing else. Limit the title under 100 characters."
        )

        if len(title) > 100:
            if get_verbose():
                warning("Generated Title is too long. Retrying...")
            return self.generate_metadata()

        description = self.generate_response(
            f"Please generate a YouTube Video Description for the following script: {self.script}. Only return the description, nothing else."
        )

        # Generate SEO tags
        tags_raw = self.generate_response(
            f"Generate a JSON array of 10-15 YouTube SEO tags (single words or short phrases) for a video about: {self.subject}. "
            f"Return ONLY a JSON array of strings, e.g. [\"tag1\", \"tag2\"]. No other text."
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
        sentences = [s.strip() for s in re.split(r'[.!?]+', self.script) if len(s.strip()) > 10]

        # Target 4-5 scenes, 1 image each = 4-5 total
        n_scenes = min(max(len(sentences), 3), 5)

        prompt = f"""You are a visual director creating a storyboard for a YouTube Short.

Subject: {self.subject}
Script sentences (in order):
{chr(10).join(str(i+1) + '. ' + s for i, s in enumerate(sentences[:n_scenes]))}

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
        lines = completion.split('\n')
        for line in lines:
            line = line.strip()
            # Match patterns like "1.", "2.", "3." etc.
            match = re.match(r'^[\d]+[\.\)\-\s]+(.+)$', line)
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
                    image_prompts = [p.strip() for p in parsed if isinstance(p, str) and len(p.strip()) > 10]
            except Exception:
                pass

        # Fallback: generate from script sentences directly (1 per scene)
        if not image_prompts:
            if get_verbose():
                warning("LLM prompt parsing failed. Generating from script sentences...")
            for sentence in sentences[:n_scenes]:
                visual = f"wide cinematic shot of {sentence.strip()[:60]}, photorealistic, dramatic lighting, no text, no hands"
                image_prompts.append(visual)

        # Ensure minimum of 4 images
        while len(image_prompts) < 4 and sentences:
            idx = len(image_prompts) // 2
            if idx < len(sentences):
                variant = "wide establishing shot" if len(image_prompts) % 2 == 0 else "close-up detail view"
                visual = f"{variant} of {sentences[idx].strip()[:60]}, cinematic, detailed"
                image_prompts.append(visual)
            else:
                break

        # Cap at 12 images max
        image_prompts = image_prompts[:12]

        self.image_prompts = image_prompts

        success(f"Generated {len(image_prompts)} Image Prompts ({len(image_prompts)//2} scenes x 2 angles).")

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
                    mime_type = inline_data.get("mimeType") or inline_data.get("mime_type", "")
                    if data and str(mime_type).startswith("image/"):
                        image_bytes = base64.b64decode(data)
                        return self._persist_image(image_bytes, "Nano Banana 2 API")

            if get_verbose():
                warning(f"Nano Banana 2 did not return an image payload. Response: {body}")
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

        enhanced_prompt = f"{prompt}, cinematic, vertical 9:16, photorealistic, high detail, no text, no letters, no words, no fingers"
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

        enhanced_prompt = f"{prompt}, cinematic, vertical 9:16, photorealistic, high detail, no text, no letters, no words, no fingers"
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
            if "quota" in err_str.lower() or "exceeded" in err_str.lower() or "429" in err_str:
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
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
            "that", "this", "these", "those", "it", "its", "showing", "depicting",
            "featuring", "beautiful", "stunning", "amazing", "incredible", "dramatic",
            "view", "scene", "image", "photo", "picture", "background",
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
        Generates an AI image using Cloudflare Workers AI (SDXL).
        Free tier: 100,000 calls/day. No rate limit issues.
        """
        worker_url = os.environ.get("CF_WORKER_URL", "")
        api_key = os.environ.get("CF_WORKER_API_KEY", "")
        if not worker_url or not api_key:
            if get_verbose():
                warning("CF_WORKER_URL or CF_WORKER_API_KEY not set. Skipping Cloudflare.")
            return None

        enhanced_prompt = f"{prompt}, cinematic, photorealistic, high detail, 4k, no text, no letters, no words, no writing, no fingers, no hands close-up"
        print(f"Generating AI image via Cloudflare Workers AI (SDXL): {prompt[:80]}...")

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

            if resp.status_code == 429:
                if get_verbose():
                    warning("Cloudflare Workers AI rate limited (429).")
                return None

            if resp.status_code in (401, 403):
                if get_verbose():
                    warning(f"Cloudflare Workers AI auth failed ({resp.status_code}).")
                return None

            resp.raise_for_status()

            if len(resp.content) < 1000:
                if get_verbose():
                    warning("Cloudflare image too small, likely an error.")
                return None

            return self._persist_image(resp.content, "Cloudflare Workers AI (SDXL)")

        except Exception as e:
            if get_verbose():
                warning(f"Cloudflare Workers AI failed: {e}")
            return None

    def generate_image(self, prompt: str, delay_between: int = 30) -> str:
        """
        Generates an AI Image based on the given prompt.
        Priority: Cloudflare (SDXL) -> Gemini -> Pollinations -> g4f -> Pixabay
        """
        # 1. Try Cloudflare Workers AI (SDXL) - free, 100K/day, no rate limits
        if get_verbose():
            info("Trying Cloudflare Workers AI (SDXL)...")
        result = self.generate_image_cloudflare(prompt)
        if result is not None:
            time.sleep(2)
            return result

        # 2. Try Gemini - best quality
        gemini_key = get_nanobanana2_api_key()
        if gemini_key:
            if get_verbose():
                info("Cloudflare failed. Trying Gemini image API...")
            result = self.generate_image_nanobanana2(prompt)
            if result is not None:
                time.sleep(delay_between)
                return result

        # 3. Try Pollinations with API key
        if get_verbose():
            info("Gemini failed. Trying Pollinations API...")
        result = self.generate_image_pollinations(prompt)
        if result is not None:
            time.sleep(delay_between)
            return result

        # 4. Try g4f (Pollinations free)
        if not getattr(self, '_g4f_quota_exhausted', False):
            if get_verbose():
                info("Pollinations failed. Trying g4f (free)...")
            result = self.generate_image_g4f(prompt)
            if result is not None:
                time.sleep(delay_between)
                return result
        elif get_verbose():
            info("g4f quota exhausted, skipping...")

        # 5. Try Pixabay - stock photos
        if get_verbose():
            info("All AI generation failed. Trying Pixabay stock photos...")
        result = self.generate_image_pixabay(prompt)
        if result is not None:
            time.sleep(5)
            return result

        # 5. All failed - caller will use placeholder
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

        clips = []
        tot_dur = 0
        # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
        while tot_dur < max_duration:
            for image_path in self.images:
                clip = ImageClip(image_path)
                clip.duration = req_dur
                clip = clip.set_fps(30)

                # Not all images are same size,
                # so we need to resize them
                if round((clip.w / clip.h), 4) < 0.5625:
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to 1080x1920")
                    clip = crop(
                        clip,
                        width=clip.w,
                        height=round(clip.w / 0.5625),
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                else:
                    if get_verbose():
                        info(f" => Resizing Image: {image_path} to 1920x1080")
                    clip = crop(
                        clip,
                        width=round(0.5625 * clip.h),
                        height=clip.h,
                        x_center=clip.w / 2,
                        y_center=clip.h / 2,
                    )
                clip = clip.resize((1080, 1920))

                # Ken Burns effect: slow zoom/pan over clip duration
                # Alternate between zoom-in and zoom-out for variety
                zoom_start = 1.0
                zoom_end = 1.15
                if len(clips) % 2 == 1:
                    zoom_start, zoom_end = zoom_end, zoom_start

                # Pre-scale to max zoom size, then crop a fixed-size window that moves
                target_w, target_h = 1080, 1920
                max_zoom = max(zoom_start, zoom_end)
                scaled_w = int(target_w * max_zoom)
                scaled_h = int(target_h * max_zoom)
                clip = clip.resize((scaled_w, scaled_h))

                # Time-based crop: fixed window (1080x1920) moves across the scaled image
                import numpy as np

                def ken_burns_crop(get_frame, t, dur=clip.duration, sw=scaled_w, sh=scaled_h,
                                   tw=target_w, th=target_h, zs=zoom_start, ze=zoom_end):
                    progress = t / dur if dur > 0 else 0
                    # Start/end crop offsets (from center)
                    max_ox = (sw - tw) // 2
                    max_oy = (sh - th) // 2
                    # Zoom direction: if ze > zs, we zoom in (crop tighter)
                    # so offset goes from 0 to max (moving from center to edge)
                    ox = int(max_ox * progress)
                    oy = int(max_oy * progress)
                    # Center the crop with offset
                    cx = (sw - tw) // 2 - ox // 2
                    cy = (sh - th) // 2 - oy // 2
                    cx = max(0, min(cx, sw - tw))
                    cy = max(0, min(cy, sh - th))
                    frame = get_frame(t)
                    return frame[cy:cy+th, cx:cx+tw]

                clip = clip.fl(ken_burns_crop)

                # Fade in/out for smooth transitions
                clip = clip.fadein(0.5)
                clip = clip.fadeout(0.5)

                clips.append(clip)
                tot_dur += clip.duration

        final_clip = concatenate_videoclips(clips)
        final_clip = final_clip.set_fps(30)
        random_song = choose_random_song()

        subtitles = None
        try:
            subtitles_path = self.generate_subtitles(self.tts_path)
            equalize_subtitles(subtitles_path, 10)
            subtitles = SubtitlesClip(subtitles_path, generator)
            subtitles.set_pos(("center", "center"))
        except Exception as e:
            warning(f"Failed to generate subtitles, continuing without subtitles: {e}")

        random_song_clip = AudioFileClip(random_song).set_fps(44100)

        # Turn down volume
        random_song_clip = random_song_clip.fx(afx.volumex, 0.1)
        comp_audio = CompositeAudioClip([tts_clip.set_fps(44100), random_song_clip])

        final_clip = final_clip.set_audio(comp_audio)
        final_clip = final_clip.set_duration(tts_clip.duration)

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
            self.generate_image(prompt)

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
        driver = self.browser
        driver.get("https://studio.youtube.com")
        time.sleep(2)
        channel_id = driver.current_url.split("/")[-1]
        self.channel_id = channel_id

        return channel_id

    def upload_video(self) -> bool:
        """
        Uploads the video to YouTube.

        Returns:
            success (bool): Whether the upload was successful or not.
        """
        try:
            self.get_channel_id()

            driver = self.browser
            verbose = get_verbose()

            # Go to youtube.com/upload
            driver.get("https://www.youtube.com/upload")

            # Set video file
            FILE_PICKER_TAG = "ytcp-uploads-file-picker"
            file_picker = driver.find_element(By.TAG_NAME, FILE_PICKER_TAG)
            INPUT_TAG = "input"
            file_input = file_picker.find_element(By.TAG_NAME, INPUT_TAG)
            file_input.send_keys(self.video_path)

            # Wait for upload to finish
            time.sleep(5)

            # Set title
            textboxes = driver.find_elements(By.ID, YOUTUBE_TEXTBOX_ID)

            title_el = textboxes[0]
            description_el = textboxes[-1]

            if verbose:
                info("\t=> Setting title...")

            title_el.click()
            time.sleep(1)
            title_el.clear()
            title_el.send_keys(self.metadata["title"])

            if verbose:
                info("\t=> Setting description...")

            # Set description
            time.sleep(10)
            description_el.click()
            time.sleep(0.5)
            description_el.clear()
            description_el.send_keys(self.metadata["description"])

            time.sleep(0.5)

            # Set `made for kids` option
            if verbose:
                info("\t=> Setting `made for kids` option...")

            is_for_kids_checkbox = driver.find_element(
                By.NAME, YOUTUBE_MADE_FOR_KIDS_NAME
            )
            is_not_for_kids_checkbox = driver.find_element(
                By.NAME, YOUTUBE_NOT_MADE_FOR_KIDS_NAME
            )

            if not get_is_for_kids():
                is_not_for_kids_checkbox.click()
            else:
                is_for_kids_checkbox.click()

            time.sleep(0.5)

            # Click next
            if verbose:
                info("\t=> Clicking next...")

            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            # Click next again
            if verbose:
                info("\t=> Clicking next again...")
            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            # Wait for 2 seconds
            time.sleep(2)

            # Click next again
            if verbose:
                info("\t=> Clicking next again...")
            next_button = driver.find_element(By.ID, YOUTUBE_NEXT_BUTTON_ID)
            next_button.click()

            # Set as unlisted
            if verbose:
                info("\t=> Setting as unlisted...")

            radio_button = driver.find_elements(By.XPATH, YOUTUBE_RADIO_BUTTON_XPATH)
            radio_button[2].click()

            if verbose:
                info("\t=> Clicking done button...")

            # Click done button
            done_button = driver.find_element(By.ID, YOUTUBE_DONE_BUTTON_ID)
            done_button.click()

            # Wait for 2 seconds
            time.sleep(2)

            # Get latest video
            if verbose:
                info("\t=> Getting video URL...")

            # Get the latest uploaded video URL
            driver.get(
                f"https://studio.youtube.com/channel/{self.channel_id}/videos/short"
            )
            time.sleep(2)
            videos = driver.find_elements(By.TAG_NAME, "ytcp-video-row")
            first_video = videos[0]
            anchor_tag = first_video.find_element(By.TAG_NAME, "a")
            href = anchor_tag.get_attribute("href")
            if verbose:
                info(f"\t=> Extracting video ID from URL: {href}")
            video_id = href.split("/")[-2]

            # Build URL
            url = build_url(video_id)

            self.uploaded_video_url = url

            if verbose:
                success(f" => Uploaded Video: {url}")

            # Add video to cache
            self.add_video(
                {
                    "title": self.metadata["title"],
                    "description": self.metadata["description"],
                    "url": url,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            # Close the browser
            driver.quit()

            return True
        except:
            self.browser.quit()
            return False

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
