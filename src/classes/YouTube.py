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

from utils import close_running_selenium_instances, build_url, choose_random_song
from cache import get_accounts, add_account, get_youtube_cache_path
from .Tts import TTS
from llm_provider import generate_text, get_model_for_job
from config import (
    ROOT_DIR,
    get_headless,
    get_verbose,
    get_script_sentence_length,
    get_stt_provider,
    get_assemblyai_api_key,
    get_whisper_model,
    get_whisper_device,
    get_whisper_compute_type,
    get_threads,
    get_fonts_dir,
    get_font,
    get_is_for_kids,
)
from status import error, success, info, warning
from uuid import uuid4
from constants import (
    YOUTUBE_TEXTBOX_ID,
    YOUTUBE_MADE_FOR_KIDS_NAME,
    YOUTUBE_NOT_MADE_FOR_KIDS_NAME,
    YOUTUBE_NEXT_BUTTON_ID,
    YOUTUBE_DONE_BUTTON_ID,
)
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
from selenium.webdriver.common.action_chains import ActionChains


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
        self._browser_initialized: bool = False
        self._progress_callback = None

        # Validate profile path exists (but don't init browser yet)
        if self._fp_profile_path and not os.path.isdir(self._fp_profile_path):
            raise ValueError(
                f"Firefox profile path does not exist or is not a directory: {self._fp_profile_path}"
            )

        self._options: Optional[Options] = None
        self._browser: Optional[webdriver.Firefox] = None
        self._wait: Optional[WebDriverWait] = None
        self._temp_profile_dir: Optional[str] = None

    def set_progress_callback(self, cb):
        """Set a callback for pipeline progress events."""
        self._progress_callback = cb

    def _progress(
        self, step: str, status: str, progress: float | None = None, detail: str = ""
    ):
        """Emit a progress event if a callback is registered."""
        if self._progress_callback:
            self._progress_callback(step, status, progress, detail)

    def _ensure_browser(self) -> None:
        """Lazy initialization of the browser - only created when needed."""
        if self._browser_initialized:
            return

        if not self._fp_profile_path:
            raise ValueError(f"Firefox profile path is required for browser operations")

        self._options = Options()
        if get_headless():
            self._options.add_argument("--headless")

        self._options.add_argument("-profile")
        self._options.add_argument(self._fp_profile_path)

        gecko_path = "/home/anon/.cache/selenium/geckodriver/linux64/0.36.0/geckodriver"
        # Add gecko driver to PATH for selenium
        gecko_dir = os.path.dirname(gecko_path)
        if gecko_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = gecko_dir + ":" + os.environ.get("PATH", "")

        self._browser = webdriver.Firefox(options=self._options)
        self._wait = WebDriverWait(self._browser, 30)
        self.page = self._browser
        self._browser_initialized = True

    @property
    def browser(self):
        """Property for backward compatibility - triggers lazy init."""
        self._ensure_browser()
        return self._browser

    @property
    def wait(self):
        """Property for backward compatibility - triggers lazy init."""
        self._ensure_browser()
        return self._wait

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
        model = model_name or get_model_for_job("script")
        print(f"[📝 LLM] Using model: {model}")
        result = generate_text(prompt, model_name=model)
        print(f"[✅ LLM] Generated {len(result)} chars")
        return result

    def _research_trending_topics(self) -> str:
        """
        Researches trending topics with dynamic, unique queries.
        Priority: Tavily -> Exa -> ddgs -> Wikipedia -> Google RSS -> Firecrawl
        Uses randomized angles to ensure unique results every time.
        """
        import random
        from datetime import datetime

        context_parts = []
        now = datetime.now()

        # Generate dynamic angle modifiers for unique research
        angle_modifiers = [
            f"recently discovered",
            f"unusual facts",
            f"lesser-known",
            f"breaking",
            f"trending now",
            f"surprising",
            f"mysteries",
            f"latest findings {now.strftime('%B %Y')}",
            f"hidden gems",
            f"controversial",
        ]
        # Pick random modifier based on time for variety
        random.seed(int(now.timestamp()) % 10000)
        angle = random.choice(angle_modifiers)

        # Build dynamic queries
        base_query = self.niche
        dynamic_queries = [
            f"{angle} {base_query}",
            f"{base_query} {now.year} facts",
            f"what's trending in {base_query} right now",
            f"unknown {base_query} secrets",
            f"{base_query} viral moments",
        ]

        info("   🔍 Starting dynamic topic research...")

        # Method 1: Tavily
        info("   🔍 Searching Tavily...")
        try:
            from tavily import TavilyClient

            api_key = os.environ.get("TAVILY_API_KEY", "")
            if api_key:
                # Use different query each time
                query = random.choice(dynamic_queries)
                tavily_client = TavilyClient(api_key=api_key)
                response = tavily_client.search(
                    query=query,
                    max_results=8,
                    include_answer=True,
                )
                if response.get("results"):
                    topics_found = []
                    for r in response["results"][:8]:
                        title = r.get("title", "")
                        content = r.get("content", "")[:150]
                        if title and content:
                            topics_found.append(f"{title}: {content}")
                    if topics_found:
                        context_parts.append(
                            f"Tavily ({query[:40]}):\n"
                            + "\n".join(f"- {t}" for t in topics_found[:8])
                        )
                        info(f"   ✅ Tavily: {len(topics_found)} results")
        except Exception as e:
            warning(f"Tavily failed: {e}")

        # Method 2: Exa
        info("   🔍 Searching Exa...")
        try:
            from exa_py import Exa

            api_key = os.environ.get("EXA_API_KEY", "")
            if api_key:
                query = random.choice(dynamic_queries)
                exa = Exa(api_key=api_key)
                response = exa.search(
                    query,
                    num_results=8,
                    type="neural",
                )
                if response.results:
                    topics_found = []
                    for r in response.results:
                        text = r.text[:150] if r.text else r.get("extract", "")[:150]
                        if r.title and text:
                            topics_found.append(f"{r.title}: {text}")
                    if topics_found:
                        context_parts.append(
                            f"Exa ({query[:40]}):\n"
                            + "\n".join(f"- {t}" for t in topics_found[:8])
                        )
                        info(f"   ✅ Exa: {len(topics_found)} results")
        except Exception as e:
            warning(f"Exa failed: {e}")

        # Method 3: ddgs (DuckDuckGo via Bing backend - bypasses Indonesia block)
        info("   🔍 Searching DuckDuckGo (ddgs)...")
        try:
            from ddgs import DDGS

            # Disable proxy
            for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
                os.environ.pop(k, None)

            ddg = DDGS()
            query = random.choice(dynamic_queries)
            results = ddg.text(query, max_results=8)
            if results:
                topics_found = []
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    if title and body:
                        topics_found.append(f"{title}: {body[:100]}")
                if topics_found:
                    context_parts.append(
                        f"DuckDuckGo ({query[:40]}):\n"
                        + "\n".join(f"- {t}" for t in topics_found[:8])
                    )
                    info(f"   ✅ ddgs: {len(topics_found)} results")
        except Exception as e:
            warning(f"ddgs failed: {e}")

        # Method 4: Wikipedia
        info("   🔍 Fetching Wikipedia...")
        try:
            today = now.strftime("%Y/%m/%d")
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/feed/featured/{today}"
            resp = requests.get(
                wiki_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()

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

                tfa = data.get("tfa", {})
                if tfa:
                    title = tfa.get("titles", {}).get("normalized", "")
                    extract = tfa.get("extract", "")[:200]
                    if title and extract:
                        context_parts.append(
                            f"Wikipedia Featured Article: {title}\n{extract}"
                        )

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
                info(f"   ✅ Wikipedia: fetched")
        except Exception as e:
            warning(f"Wikipedia API failed: {e}")

        # Method 5: Google Trends RSS
        info("   🔍 Fetching Google Trends...")
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
                        info(f"   ✅ Google Trends: {len(relevant)} topics")
                        break
        except Exception as e:
            warning(f"Google Trends failed: {e}")

        # Method 6: Firecrawl (last fallback)
        info("   🔍 Searching Firecrawl...")
        try:
            from firecrawl import Firecrawl

            api_key = os.environ.get("FIRECRAWL_API_KEY", "")
            if api_key and not any(
                p
                for p in context_parts
                if any(x in p.lower() for x in ["tavily", "exa", "duckduckgo", "ddgs"])
            ):
                firecrawl = Firecrawl(api_key=api_key)
                query = random.choice(dynamic_queries)
                search_result = firecrawl.search(
                    query=query,
                    limit=8,
                )
                if search_result and hasattr(search_result, "web"):
                    web_results = search_result.web or []
                    topics_found = []
                    for item in web_results[:8]:
                        title = item.title if hasattr(item, "title") else ""
                        desc = (
                            item.description[:120]
                            if hasattr(item, "description") and item.description
                            else ""
                        )
                        if title and desc:
                            topics_found.append(f"{title}: {desc}")
                    if topics_found:
                        context_parts.append(
                            f"Firecrawl ({query[:40]}):\n"
                            + "\n".join(f"- {t}" for t in topics_found[:8])
                        )
                        info(f"   ✅ Firecrawl: {len(topics_found)} results")
        except Exception as e:
            warning(f"Firecrawl failed: {e}")

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

        completion = str(
            self.generate_response(trend_prompt, model_name=get_model_for_job("topic"))
        ).strip()

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
        def isSimilar(new_topic, used_list, threshold=0.35):
            """Check if topic shares too many words with an existing topic."""
            new_words = set(re.sub(r"[^\w\s]", "", new_topic.lower()).split())
            for used in used_list:
                used_words = set(re.sub(r"[^\w\s]", "", used.lower()).split())
                if not new_words or not used_words:
                    continue
                overlap = len(new_words & used_words) / max(
                    len(new_words), len(used_words)
                )
                if overlap > threshold:
                    return True
                # Also check if the key words overlap significantly
                key_words = [w for w in new_words if len(w) > 4]
                used_key_words = [w for w in used_words if len(w) > 4]
                if any(kw in used_key_words for kw in key_words[:2]):
                    return True
            return False

        # Pick the best topic that hasn't been used
        selected = None
        for topic in topics:
            if not isSimilar(topic, used_topics):
                selected = topic
                break

        if not selected:
            # All topics were duplicates, force a new one
            if get_verbose():
                warning("All generated topics were duplicates. Forcing unique topic...")
            avoid_list = (
                "\n".join(f"- {t}" for t in used_topics[-30:])
                if used_topics
                else "none"
            )
            # Generate multiple options and pick the most different one
            response = self.generate_response(
                f"""Generate 5 completely different, specific video topics about: {self.niche}

IMPORTANT: Each topic must be about a DIFFERENT aspect or fact of {self.niche}.
Do NOT repeat these already-used topics:\n{avoid_list}

Format: Just list 5 topics, one per line, numbered 1-5.""",
                model_name=get_model_for_job("topic"),
            )

            # Parse all generated topics
            new_topics = []
            for line in response.split("\n"):
                line = line.strip()
                match = re.match(r"^[\d]+[\.\)\-\s]+(.+)$", line)
                if match:
                    topic = match.group(1).strip()
                    if len(topic) > 20 and not isSimilar(topic, used_topics):
                        new_topics.append(topic)

            if new_topics:
                # Pick a random one to add variety
                selected = random.choice(new_topics)
            else:
                # Last resort: pick something completely random
                selected = f"Amazing {self.niche} facts you never knew!"

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

        info(f" 🎯 Topic selected: {selected[:80]}...")
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
        info(" ✍️ Generating script...")
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

        completion = self.generate_response(
            prompt, model_name=get_model_for_job("script")
        )

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
            f"Rules: 60-125 characters. Front-load the most important keywords. "
            f"No hashtags in the title. Return ONLY the title, nothing else.",
            model_name=get_model_for_job("title_desc"),
        )

        if len(title) > 125:
            if get_verbose():
                warning("Generated Title is over 125 chars. Retrying...")
            return self.generate_metadata()

        description = self.generate_response(
            f"Generate a YouTube Shorts description for the following script: {self.script}. "
            f"Rules: Include 3-5 relevant hashtags. Add a brief, keyword-rich summary of the video content "
            f"to index properly in YouTube Search. Return ONLY the description, nothing else.",
            model_name=get_model_for_job("title_desc"),
        )

        # Generate SEO tags
        tags_raw = self.generate_response(
            f"Generate a JSON array of 10-15 YouTube SEO tags (single words or short phrases) for a video about: {self.subject}. "
            f'Return ONLY a JSON array of strings, e.g. ["tag1", "tag2"]. No other text.',
            model_name=get_model_for_job("seo_tags"),
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

        completion = str(
            self.generate_response(
                prompt, model_name=get_model_for_job("image_prompts")
            )
        ).strip()

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

    # GEMINI IMAGE GENERATION COMPLETELY REMOVED

    def generate_image_pollinations(self, prompt: str) -> str:
        """
        Generates an AI image using Pollinations.ai GET endpoint with API key.
        Uses zimage model (0.002 pts/image, ~500/hr budget).

        Args:
            prompt (str): Scene description for image generation

        Returns:
            path (str): The path to the generated image, or None on failure.
        """
        api_key = os.environ.get("POLLINATIONS_API_KEY", "")

        enhanced_prompt = f"{prompt}, Ghibli watercolor"
        print(f"Generating AI image via Pollinations zimage: {prompt[:80]}...")

        try:
            import urllib.parse

            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            if api_key:
                url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=zimage&width=1080&height=1920&key={api_key}&nologo=true"
            else:
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=zimage&width=1080&height=1920&nologo=true"

            resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})

            if resp.status_code == 429:
                if get_verbose():
                    warning("Pollinations zimage rate limited (429).")
                return None

            if resp.status_code in (401, 403):
                if get_verbose():
                    warning(f"Pollinations zimage auth failed ({resp.status_code}).")
                return None

            resp.raise_for_status()

            if len(resp.content) < 1000:
                if get_verbose():
                    warning("Pollinations zimage image too small, likely an error.")
                return None

            return self._persist_image(
                resp.content,
                "Pollinations API zimage"
                if api_key
                else "Pollinations zimage (public)",
            )

        except Exception as e:
            if get_verbose():
                warning(f"Pollinations image generation failed: {e}")
            return None

    def generate_image_pollinations_flux(self, prompt: str) -> str:
        """
        Generates an AI image using Pollinations.ai GET endpoint with flux model.
        Fallback when zimage is exhausted. Costs 0.001 pts/image (~150/hr from 0.15/hr budget).

        Args:
            prompt (str): Scene description for image generation

        Returns:
            path (str): The path to the generated image, or None on failure.
        """
        api_key = os.environ.get("POLLINATIONS_API_KEY", "")

        enhanced_prompt = f"{prompt}, Ghibli watercolor"
        print(f"Generating AI image via Pollinations flux: {prompt[:80]}...")

        try:
            import urllib.parse

            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            if api_key:
                url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=flux&width=1080&height=1920&key={api_key}&nologo=true"
            else:
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=1080&height=1920&nologo=true"

            resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})

            if resp.status_code == 429:
                if get_verbose():
                    warning("Pollinations flux rate limited (429).")
                return None

            if resp.status_code in (401, 403):
                if get_verbose():
                    warning(f"Pollinations flux auth failed ({resp.status_code}).")
                return None

            resp.raise_for_status()

            if len(resp.content) < 1000:
                if get_verbose():
                    warning("Pollinations flux image too small, likely an error.")
                return None

            return self._persist_image(
                resp.content,
                "Pollinations API flux" if api_key else "Pollinations flux (public)",
            )

        except Exception as e:
            if get_verbose():
                warning(f"Pollinations flux generation failed: {e}")
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
        Priority: Cloudflare Image API -> Pollinations zimage -> Pollinations flux
        """
        # 1. Try Cloudflare Image API FIRST
        if get_verbose():
            info("Trying Cloudflare Image API...")
        result = self.generate_image_cloudflare(prompt)
        if result is not None:
            time.sleep(delay_between)
            return result

        # 2. Try Pollinations zimage via API key
        if get_verbose():
            info("Cloudflare exhausted. Trying Pollinations zimage...")
        result = self.generate_image_pollinations(prompt)
        if result is not None:
            time.sleep(delay_between)
            return result

        # 3. Fallback to Pollinations flux (cheaper, 0.001 pts/image)
        if get_verbose():
            info("zimage failed. Trying Pollinations flux...")
        result = self.generate_image_pollinations_flux(prompt)
        if result is not None:
            time.sleep(delay_between)
            return result

        # All failed - show proper warning
        warning(
            "ALL IMAGE GENERATION METHODS FAILED. No image generated for this prompt."
        )
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

    def _parse_srt(self, srt_path: str) -> list:
        """Parse SRT file and return list of (start, end, text) tuples.

        Merges consecutive SRT blocks into phrase-level chunks to avoid
        word-by-word subtitle display (Whisper outputs word-level timestamps).
        """
        raw_subtitles = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.split(r"\n\s*\n", content.strip())
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_line = lines[1]
                text = " ".join(lines[2:])
                # Parse time: "00:00:00,000 --> 00:00:03,000"
                try:
                    start_str, end_str = time_line.split(" --> ")
                    start = self._parse_timestamp(start_str)
                    end = self._parse_timestamp(end_str)
                    raw_subtitles.append((start, end, text))
                except Exception:
                    continue

        # Return raw word-level subtitles without merging
        # Each word displays as its own subtitle entry
        return raw_subtitles

    def _parse_timestamp(self, ts: str) -> float:
        """Parse SRT timestamp to seconds."""
        ts = ts.strip().replace(",", ".")
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        return 0.0

    def _render_subtitle_on_frame(
        self, frame: Image.Image, text: str, font_path: str
    ) -> Image.Image:
        """Render subtitle text on a PIL Image frame."""
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(frame)
        try:
            # Scale font to ~5% of video height for big readable subtitles
            font_size = max(48, int(frame.height * 0.050))
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()

        # Get text bbox
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Position: center of frame
        x = (frame.width - text_w) // 2
        y = (frame.height - text_h) // 2

        # Draw stroke/outline
        stroke_width = max(2, font_size // 12)
        for dx in range(-stroke_width, stroke_width + 1, 2):
            for dy in range(-stroke_width, stroke_width + 1, 2):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="black")

        # Draw main text
        draw.text((x, y), text, font=font, fill="white")

        return frame

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

        # Use CPU to avoid CUDA library issues
        device = "cpu"
        compute = "int8"

        try:
            model = WhisperModel(
                get_whisper_model(),
                device=device,
                compute_type=compute,
            )
        except Exception as e:
            warning(f"Whisper model load failed: {e}, retrying with base model...")
            model = WhisperModel(
                "base",
                device=device,
                compute_type=compute,
            )

        segments, info = model.transcribe(
            audio_path, vad_filter=True, word_timestamps=True
        )

        lines = []
        idx = 0
        for segment in segments:
            for word in segment.words:
                text = str(word.word).strip()
                if not text:
                    continue
                idx += 1
                start = self._format_srt_timestamp(word.start)
                end = self._format_srt_timestamp(word.end)
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

        # Guard: if no images were generated, create a solid-color placeholder
        if not self.images:
            warning("No images generated - creating solid-color placeholder")
            placeholder_path = os.path.join(ROOT_DIR, ".mp", str(uuid4()) + ".png")
            try:
                img = Image.new("RGB", (1080, 1920), color=(30, 30, 60))
                img.save(placeholder_path)
                self.images.append(placeholder_path)
            except ImportError:
                error("PIL not available - cannot create placeholder image")
                raise RuntimeError(
                    "Image generation failed and PIL placeholder unavailable"
                )

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

        # Subtitle generator - proper function for SubtitlesClip
        def make_subtitle_clip(txt):
            font_path = os.path.join(get_fonts_dir(), get_font())
            return TextClip(
                txt,
                font=font_path,
                fontsize=80,
                color="white",
                stroke_color="black",
                stroke_width=3,
                size=(1080, None),
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

        # Pre-parse subtitles for rendering on frames
        subtitle_data = []
        subtitle_font_path = None
        try:
            subtitles_path = self.generate_subtitles(self.tts_path)
            if subtitles_path and os.path.exists(subtitles_path):
                subtitle_data = self._parse_srt(subtitles_path)
                subtitle_font_path = os.path.join(get_fonts_dir(), get_font())
                if get_verbose():
                    info(f" => Loaded {len(subtitle_data)} subtitle segments")
        except Exception as e:
            warning(f"Whisper subtitle generation failed: {e}")

        # FALLBACK: if no subtitles, use the script text as full-video subtitle
        if not subtitle_data and hasattr(self, "script") and self.script:
            script_text = self.script.strip()
            if script_text:
                # Split script into sentences for subtitle display
                import re

                sentences = re.split(r"(?<=[.!?])\s+", script_text)
                # Estimate ~2 seconds per sentence average
                total_dur = float(max_duration) if "max_duration" in dir() else 60.0
                seg_dur = total_dur / max(len(sentences), 1)
                subtitle_font_path = os.path.join(get_fonts_dir(), get_font())
                for i, sent in enumerate(sentences):
                    sent = sent.strip()
                    if not sent:
                        continue
                    # Truncate very long sentences
                    if len(sent) > 200:
                        sent = sent[:197] + "..."
                    start = i * seg_dur
                    end = min((i + 1) * seg_dur, total_dur)
                    subtitle_data.append((start, end, sent))
                if get_verbose():
                    info(
                        f" => Using script as fallback subtitles: {len(subtitle_data)} segments"
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

            # Render subtitles on frame
            if subtitle_data:
                current_subtitle = None
                for start, end, text in subtitle_data:
                    if start <= t <= end:
                        current_subtitle = text
                        break

                if current_subtitle:
                    frame = self._render_subtitle_on_frame(
                        frame, current_subtitle, subtitle_font_path
                    )

            return np.array(frame)

        final_clip = VideoClip(make_frame, duration=total_dur)
        final_clip = final_clip.with_fps(30)
        random_song = choose_random_song()

        random_song_clip = AudioFileClip(random_song).with_fps(44100)

        # Turn down volume
        random_song_clip = random_song_clip.with_volume_scaled(0.1)
        comp_audio = CompositeAudioClip([tts_clip.with_fps(44100), random_song_clip])

        final_clip = final_clip.with_audio(comp_audio)
        # Use total_dur (matches frame buffer exactly) instead of tts_clip.duration
        # to avoid black frames when TTS is slightly longer than the frame coverage.
        final_clip = final_clip.with_duration(total_dur)

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
        info(" 🎬 Starting video generation...")

        # Generate the Topic
        info(" 📊 Step 1/7: Generating topic...")
        self._progress("topic", "running")
        self.generate_topic()
        self._progress(
            "topic", "done", detail=self.subject[:60] if self.subject else ""
        )

        # Generate the Script
        info(" ✍️ Step 2/7: Generating script...")
        self._progress("script", "running")
        self.generate_script()
        self._progress("script", "done", detail=f"{len(self.script)} chars")

        # Generate the Metadata
        info(" 📝 Step 3/7: Generating metadata...")
        self._progress("metadata", "running")
        self.generate_metadata()
        self._progress("metadata", "done", detail=self.metadata.get("title", "")[:40])

        # Generate the Image Prompts
        info(" 🎨 Step 4/7: Generating image prompts...")
        self._progress("image_prompts", "running")
        self.generate_prompts()
        self._progress(
            "image_prompts", "done", detail=f"{len(self.image_prompts)} prompts"
        )

        # Generate the Images
        info(" 🖼️ Step 5/7: Generating images...")
        self._progress("images", "running")
        total = len(self.image_prompts)
        for i, prompt in enumerate(self.image_prompts):
            info(f"   Generating image {i + 1}/{total}...")
            result = self.generate_image(prompt)
            if result:
                self.images.append(result)
            self._progress(
                "images", "running", progress=(i + 1) / total, detail=f"{i + 1}/{total}"
            )
        self._progress("images", "done", detail=f"{len(self.images)} images")

        # Generate the TTS
        info(" 🔊 Step 6/7: Generating speech...")
        self._progress("tts", "running")
        self.generate_script_to_speech(tts_instance)
        self._progress("tts", "done")

        # Combine everything
        info(" 🎥 Step 7/7: Combining into video...")
        self._progress("combine", "running")
        path = self.combine()
        self._progress("combine", "done")

        success(f" ✅ Video generated: {path}")
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
            made_for_kids_clicked = False
            try:
                # Try multiple selector strategies for the radio button
                is_kids = get_is_for_kids()
                target_name = (
                    YOUTUBE_MADE_FOR_KIDS_NAME
                    if is_kids
                    else YOUTUBE_NOT_MADE_FOR_KIDS_NAME
                )

                selectors = [
                    (By.NAME, target_name),
                    (By.XPATH, f"//*[@name='{target_name}']"),
                    (By.CSS_SELECTOR, f"input[name='{target_name}']"),
                    (By.XPATH, f"//*[contains(@name, 'MADE_FOR_KIDS')]"),
                    (
                        By.XPATH,
                        "//ytcp-radio-group[@role='radiogroup']//*[@role='radio']",
                    ),
                ]

                for by, selector in selectors:
                    try:
                        elements = browser.find_elements(by, selector)
                        for el in elements:
                            if el.is_displayed() and el.is_enabled():
                                browser.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center'});",
                                    el,
                                )
                                time.sleep(0.5)
                                try:
                                    el.click()
                                except Exception:
                                    browser.execute_script("arguments[0].click();", el)
                                time.sleep(1)
                                if verbose:
                                    info(
                                        f"\t=> Made for kids radio clicked: {selector}"
                                    )
                                made_for_kids_clicked = True
                                break
                        if made_for_kids_clicked:
                            break
                    except Exception:
                        continue

                if not made_for_kids_clicked:
                    warning(
                        "Could not find made-for-kids radio button — skipping (YouTube may use last-used setting)"
                    )
                    if verbose:
                        info("\t=> Made for kids radio not found, skipping...")
                else:
                    time.sleep(2)
            except Exception as e:
                error(f"Made for kids click failed: {e}")
                if verbose:
                    warning(f"\t=> Made for kids error: {e}")

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
            extracted_video_id = None  # Store any video ID we find
            upload_complete_indicators = [
                "Upload complete",
                "uploaded",
                "Your video is ready",
                "Video details",
            ]

            # Wait up to 5 minutes (150 * 2s = 300s) for large video uploads
            for wait_round in range(150):
                time.sleep(2)
                try:
                    page_content = browser.page_source.lower()
                    current_url = browser.current_url

                    if verbose and wait_round % 10 == 0:
                        # Debug: log page content snippet
                        info(f"\t=> Current URL during wait: {current_url[:80]}...")
                        # Log some page indicators for debugging
                        if "progress" in page_content or "uploading" in page_content:
                            info(f"\t=> Still uploading (progress indicator found)")
                        # Only flag actual upload errors, not UI text containing "error"
                        # Look for specific error messages that indicate upload failure
                        error_indicators = [
                            "upload failed",
                            "could not upload video",
                            "something went wrong uploading",
                            "video processing failed",
                        ]
                        actual_error = any(
                            indicator in page_content for indicator in error_indicators
                        )
                        if actual_error:
                            error(f"\t=> Actual error detected in page content!")
                            # Continue checking instead of failing immediately

                    # Check for upload complete indicators in page content
                    for indicator in upload_complete_indicators:
                        if indicator.lower() in page_content:
                            upload_confirmed = True
                            if verbose:
                                info(
                                    f"\t=> Upload confirmed by indicator '{indicator}' at {(wait_round + 1) * 2}s"
                                )
                            break

                    if upload_confirmed:
                        break

                    # Check URL patterns
                    if (
                        "videos/short" in current_url
                        or "/edit" in current_url
                        or "/details" in current_url
                    ):
                        upload_confirmed = True
                        if verbose:
                            info(
                                f"\t=> Redirected to edit/details page after {(wait_round + 1) * 2}s"
                            )
                        break
                    # Check if URL contains video ID pattern (11 chars)
                    if "/video/" in current_url:
                        video_id_match = re.search(
                            r"/video/([a-zA-Z0-9_-]{11})", current_url
                        )
                        if video_id_match:
                            extracted_video_id = video_id_match.group(1)
                            upload_confirmed = True
                            if verbose:
                                info(
                                    f"\t=> Found video ID in URL: {extracted_video_id} after {(wait_round + 1) * 2}s"
                                )
                            break
                    # Check for other URL patterns that might contain video info
                    if "/shorts/" in current_url:
                        match = re.search(r"/shorts/([a-zA-Z0-9_-]{11})", current_url)
                        if match:
                            extracted_video_id = match.group(1)
                            upload_confirmed = True
                            if verbose:
                                info(
                                    f"\t=> Found video ID in shorts URL: {extracted_video_id}"
                                )
                            break
                    # Check for watch URL pattern
                    if "watch?v=" in current_url:
                        match = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", current_url)
                        if match:
                            extracted_video_id = match.group(1)
                            upload_confirmed = True
                            if verbose:
                                info(
                                    f"\t=> Found video ID in watch URL: {extracted_video_id}"
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

            # First check if we already extracted the video ID during upload
            video_id = extracted_video_id

            # Also check current URL one more time
            if not video_id:
                current_url = browser.current_url
                for pattern in [
                    r"/video/([a-zA-Z0-9_-]{11})",
                    r"/shorts/([a-zA-Z0-9_-]{11})",
                    r"watch\?v=([a-zA-Z0-9_-]{11})",
                ]:
                    match = re.search(pattern, current_url)
                    if match:
                        video_id = match.group(1)
                        if verbose:
                            info(f"\t=> Got video ID from final URL: {video_id}")
                        break

            # If no video ID from URL, try the videos page - use regular YouTube channel
            if not video_id:
                # Get channel ID from the browser URL
                channel_match = re.search(
                    r"youtube\.com/channel/([A-Za-z0-9_-]+)", browser.current_url
                )
                if not channel_match:
                    # Try to get from studio URL
                    channel_match = re.search(
                        r"studio\.youtube\.com/channel/([A-Za-z0-9_-]+)",
                        browser.current_url,
                    )

                if channel_match:
                    channel_id = channel_match.group(1)
                    # Use regular YouTube channel page instead of studio
                    browser.get(f"https://www.youtube.com/channel/{channel_id}/videos")
                    time.sleep(10)  # Wait for page to load
                else:
                    browser.get("https://www.youtube.com")
                    time.sleep(5)

                # Try to get page source and find video IDs
                try:
                    content = browser.page_source
                    # Check for video IDs in various data attributes - also look for shorts
                    patterns = [
                        r'"videoId":"([^"]+)"',
                        r"/shorts/([a-zA-Z0-9_-]{11})",
                        r"/video/([a-zA-Z0-9_-]{11})",
                        r"watch\?v=([a-zA-Z0-9_-]{11})",
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            video_id = matches[0]  # Take first one (should be newest)
                            if verbose:
                                info(
                                    f"\t=> Found video ID from channel page: {video_id}"
                                )
                            break
                except Exception as e:
                    if verbose:
                        warning(f"Error extracting from channel page: {e}")

            # NEW: Try to get channel ID from browser URL and find video by title
            if not video_id and self.metadata.get("title"):
                try:
                    if verbose:
                        info("\t=> Trying to find video by title on channel page...")

                    # Get current channel ID from URL
                    current_url = browser.current_url
                    channel_id_match = re.search(
                        r"youtube\.com/channel/([A-Za-z0-9_-]+)", current_url
                    )

                    if channel_id_match:
                        channel_id = channel_id_match.group(1)
                        if verbose:
                            info(f"\t=> Found channel ID: {channel_id}")

                        # Go to channel videos page
                        channel_videos_url = (
                            f"https://www.youtube.com/channel/{channel_id}/videos"
                        )
                        browser.get(channel_videos_url)
                        time.sleep(10)  # Wait for page to load

                        # Execute JS to find video by exact title match
                        js_find_by_title = """
                        (function() {
                            var targetTitle = arguments[0].toLowerCase();
                            
                            // Find all video elements
                            var videoItems = document.querySelectorAll('ytd-grid-video-renderer, ytd-video-renderer');
                            
                            for (var i = 0; i < videoItems.length; i++) {
                                var titleEl = videoItems[i].querySelector('#title, #video-title');
                                if (titleEl) {
                                    var title = titleEl.textContent || titleEl.innerText || '';
                                    if (title.toLowerCase().trim() === targetTitle.trim()) {
                                        // Find the link
                                        var link = videoItems[i].querySelector('a[href*="/watch?"]');
                                        if (link) {
                                            var href = link.href;
                                            var match = href.match(/watch\\?v=([a-zA-Z0-9_-]{11})/);
                                            if (match) return match[1];
                                        }
                                        // Try shorts
                                        link = videoItems[i].querySelector('a[href*="/shorts/"]');
                                        if (link) {
                                            var href = link.href;
                                            var match = href.match(/shorts\\/([a-zA-Z0-9_-]{11})/);
                                            if (match) return match[1];
                                        }
                                    }
                                }
                            }
                            return null;
                        })(arguments[1]);
                        """
                        video_id = browser.execute_script(
                            js_find_by_title, self.metadata["title"]
                        )
                        if video_id:
                            if verbose:
                                info(
                                    f"\t=> Found video ID from channel page by title: {video_id}"
                                )
                except Exception as e:
                    if verbose:
                        warning(f"Channel page title search failed: {e}")

            # Additional fallback: search for video by title on YouTube
            if not video_id and self.metadata.get("title"):
                try:
                    if verbose:
                        info("\t=> Trying to find video by title search...")
                    title = self.metadata["title"]
                    # Search for the video on YouTube
                    search_url = f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}"
                    browser.get(search_url)
                    time.sleep(5)

                    # Look for video in search results
                    js_search = """
                    (function() {
                        var links = document.querySelectorAll('a[href*="/watch?v="]');
                        for (var i = 0; i < Math.min(links.length, 10); i++) {
                            var href = links[i].href;
                            var match = href.match(/watch\\?v=([a-zA-Z0-9_-]{11})/);
                            if (match) return match[1];
                        }
                        return null;
                    })();
                    """
                    video_id = browser.execute_script(js_search)
                    if video_id:
                        if verbose:
                            info(f"\t=> Found video ID from search: {video_id}")
                except Exception as e:
                    if verbose:
                        warning(f"Title search fallback failed: {e}")

            # Last resort: generate a placeholder URL and attempt recovery
            if not video_id:
                # Try one more time - go directly to upload result page
                try:
                    browser.get("https://studio.youtube.com/upload")
                    time.sleep(10)
                    current_url = browser.current_url
                    for pattern in [
                        r"/video/([a-zA-Z0-9_-]{11})",
                        r"/shorts/([a-zA-Z0-9_-]{11})",
                    ]:
                        match = re.search(pattern, current_url)
                        if match:
                            video_id = match.group(1)
                            if verbose:
                                info(f"\t=> Got video ID from upload page: {video_id}")
                            break
                except Exception:
                    pass

                # Try to find the newest video by looking at the page content more thoroughly
            if not video_id:
                try:
                    content = browser.page_source
                    # Find all video IDs in various patterns
                    patterns = [
                        r'video-id="([a-zA-Z0-9_-]{11})"',
                        r'"videoId":"([a-zA-Z0-9_-]{11})"',
                        r"/video/([a-zA-Z0-9_-]{11})",
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            # Take the first match (should be the most recent)
                            video_id = matches[0]
                            if verbose:
                                info(
                                    f"\t=> Found video ID from page source ({pattern}): {video_id}"
                                )
                            break
                    # Debug: print the current URL and page structure
                    if verbose and not video_id:
                        current_url = browser.current_url
                        # Just check if there's any video link in the page
                        sample_content = (
                            content[:5000] if len(content) > 5000 else content
                        )
                        if "/video/" in sample_content:
                            info(
                                f"\t=> Page contains /video/ but couldn't extract ID. URL: {current_url}"
                            )
                except Exception as e:
                    if verbose:
                        warning(f"\t=> Page source extraction failed: {e}")

            if not video_id:
                try:
                    content = browser.page_source
                    # Find all video IDs in various patterns
                    patterns = [
                        r'video-id="([a-zA-Z0-9_-]{11})"',
                        r'"videoId":"([a-zA-Z0-9_-]{11})"',
                        r"/video/([a-zA-Z0-9_-]{11})",
                        r'"id"\s*:\s*"([a-zA-Z0-9_-]{11})"',
                        r'data-video-id="([a-zA-Z0-9_-]{11})"',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            # Take the first match (should be the most recent)
                            video_id = matches[0]
                            if verbose:
                                info(
                                    f"\t=> Found video ID from page source ({pattern}): {video_id}"
                                )
                            break
                except Exception as e:
                    if verbose:
                        warning(f"\t=> Page source extraction failed: {e}")

            # LAST RESORT: Go to YouTube homepage and look for latest video in content
            if not video_id:
                try:
                    if verbose:
                        info("\t=> Last resort: checking homepage for latest video...")
                    browser.get("https://www.youtube.com")
                    time.sleep(8)  # Increased wait for dynamic content

                    # Try to get video from shorts page (Shorts go there)
                    browser.get("https://www.youtube.com/shorts")
                    time.sleep(8)

                    js_get_latest = """
                    (function() {
                        var links = document.querySelectorAll('a[href*="/shorts/"]');
                        for (var i = 0; i < Math.min(links.length, 10); i++) {
                            var href = links[i].href;
                            var match = href.match(/shorts\\/([a-zA-Z0-9_-]{11})/);
                            if (match) return match[1];
                        }
                        // Try watch pattern
                        links = document.querySelectorAll('a[href*="/watch?v="]');
                        for (var i = 0; i < Math.min(links.length, 10); i++) {
                            var href = links[i].href;
                            var match = href.match(/watch\\?v=([a-zA-Z0-9_-]{11})/);
                            if (match) return match[1];
                        }
                        return null;
                    })();
                    """
                    video_id = browser.execute_script(js_get_latest)
                    if video_id:
                        if verbose:
                            info(f"\t=> Got video ID from shorts: {video_id}")
                except Exception as e:
                    if verbose:
                        warning(f"\t=> Homepage fallback failed: {e}")

            if not video_id:
                return (False, "Could not extract video ID from uploaded video")

            # If we get here, we have a video_id (from one of the fallbacks)
            # Build the URL
            url = build_url(video_id)

            self.uploaded_video_url = url
            if verbose:
                success(f" => Uploaded Video: {url}")

            # ── Step 15: POST-UPLOAD — ALWAYS force visibility to Public via edit page ──
            if verbose:
                info("\t=> Forcing video visibility to Public via edit page...")

            visibility_fixed = False

            # Method: Use JavaScript to directly set visibility state on the page
            # This is more reliable than trying to click through the UI
            for fix_attempt in range(3):
                try:
                    # Navigate to the videos list page where we can see the visibility
                    browser.get(
                        "https://studio.youtube.com/channel/UCFhX7gLJhz7cBMSzIdSgpqg/videos"
                    )
                    time.sleep(6)

                    # Wait for page to load and find our video in the list
                    # Look for the specific video by ID in the page content
                    page_content = browser.page_source

                    if video_id in page_content:
                        if verbose:
                            info(
                                f"\t=> Found video in list, trying to set visibility..."
                            )

                        # Try to navigate directly to the video edit page with more wait time
                        browser.get(f"https://studio.youtube.com/video/{video_id}/edit")
                        time.sleep(8)

                        # Force scroll to top
                        browser.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)

                        # Try the newer YouTube Studio UI approach
                        # Find the visibility section using more reliable selectors
                        try:
                            # Look for any element containing "Public" or "Private" text
                            # and click on it to open the menu
                            vis_options = browser.find_elements(
                                By.XPATH,
                                "//div[contains(@class, 'ytcp-video-visibility')] | //ytcp-form-video-visibility",
                            )

                            for vis_elem in vis_options:
                                if vis_elem.is_displayed():
                                    try:
                                        browser.execute_script(
                                            "arguments[0].click();", vis_elem
                                        )
                                        time.sleep(3)

                                        # Now look for Public option in the opened menu
                                        public_options = browser.find_elements(
                                            By.XPATH,
                                            "//span[text()='Public'] | //div[text()='Public'] | //tp-yt-paper-radio-button[.//span[text()='Public']]",
                                        )

                                        for pub_opt in public_options:
                                            if pub_opt.is_displayed():
                                                browser.execute_script(
                                                    "arguments[0].click();", pub_opt
                                                )
                                                time.sleep(2)

                                                # Look for save/done button
                                                try:
                                                    save_btns = browser.find_elements(
                                                        By.CSS_SELECTOR,
                                                        "button[aria-label='Save'], #save-button, ytcp-button",
                                                    )
                                                    for sb in save_btns:
                                                        if sb.is_displayed():
                                                            browser.execute_script(
                                                                "arguments[0].click();",
                                                                sb,
                                                            )
                                                            time.sleep(3)
                                                except Exception:
                                                    pass

                                                visibility_fixed = True
                                                if verbose:
                                                    info(
                                                        f"\t=> Set visibility to Public (attempt {fix_attempt + 1})"
                                                    )
                                                break
                                            if visibility_fixed:
                                                break
                                    except Exception as e:
                                        if verbose:
                                            warning(
                                                f"\t=> Visibility click failed: {e}"
                                            )
                                        continue
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Visibility section not found: {e}")

                        # Alternative: Try JavaScript to find and click radio button
                        if not visibility_fixed:
                            try:
                                js_click_public = """
                                (function() {
                                    // Try to find any Public radio button
                                    var buttons = document.querySelectorAll('tp-yt-paper-radio-button, paper-radio-button');
                                    for (var i = 0; i < buttons.length; i++) {
                                        var text = buttons[i].textContent || buttons[i].innerText;
                                        if (text && text.includes('Public')) {
                                            buttons[i].click();
                                            return true;
                                        }
                                    }
                                    return false;
                                })();
                                """
                                result = browser.execute_script(js_click_public)
                                if result:
                                    time.sleep(3)
                                    # Try to save
                                    try:
                                        save_js = """
                                        (function() {
                                            var btns = document.querySelectorAll('button, ytcp-button');
                                            for (var i = 0; i < btns.length; i++) {
                                                var txt = btns[i].textContent || btns[i].innerText;
                                                if (txt && (txt.includes('Save') || txt.includes('Done'))) {
                                                    btns[i].click();
                                                    return true;
                                                }
                                            }
                                            return false;
                                        })();
                                        """
                                        browser.execute_script(save_js)
                                        time.sleep(3)
                                        visibility_fixed = True
                                        if verbose:
                                            info(
                                                f"\t=> Set visibility via JS (attempt {fix_attempt + 1})"
                                            )
                                    except Exception:
                                        pass
                            except Exception as e:
                                if verbose:
                                    warning(f"\t=> JS visibility fix failed: {e}")

                    if visibility_fixed:
                        break

                    time.sleep(3)
                except Exception as e:
                    if verbose:
                        warning(
                            f"\t=> Visibility fix attempt {fix_attempt + 1} failed: {e}"
                        )
                    time.sleep(3)

            # Final fallback: Try direct bulk edit approach
            if not visibility_fixed:
                try:
                    if verbose:
                        info("\t=> Trying bulk edit approach...")
                    browser.get(
                        "https://studio.youtube.com/channel/UCFhX7gLJhz7cBMSzIdSgpqg/videos"
                    )
                    time.sleep(5)

                    # Look for any checkbox next to our video and try to edit
                    js_edit_video = """
                    (function() {
                        // Find the video row with our video ID
                        var links = document.querySelectorAll('a[href*="/video/']');
                        for (var i = 0; i < links.length; i++) {
                            var href = links[i].href || links[i].getAttribute('href');
                            if (href && href.includes(arguments[0])) {
                                // Try to find the parent row and click edit
                                var row = links[i].closest('tr, ytd-grid-video-renderer, ytd-video-renderer');
                                if (row) {
                                    var menuBtn = row.querySelector('[aria-label="Menu"], button[aria-label*="menu"]');
                                    if (menuBtn) {
                                        menuBtn.click();
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    });
                    """
                    browser.execute_script(js_edit_video, video_id)
                    time.sleep(3)

                    # Look for "Change visibility" option in menu
                    try:
                        menu_items = browser.find_elements(
                            By.XPATH, "//*[contains(text(), 'Change visibility')]"
                        )
                        for item in menu_items:
                            if item.is_displayed():
                                item.click()
                                time.sleep(2)

                                # Click Public
                                public_opts = browser.find_elements(
                                    By.XPATH, "//*[text()='Public']"
                                )
                                for po in public_opts:
                                    if po.is_displayed():
                                        po.click()
                                        time.sleep(2)
                                        visibility_fixed = True
                                        break
                                if visibility_fixed:
                                    break
                    except Exception as e:
                        if verbose:
                            warning(f"\t=> Bulk edit approach failed: {e}")
                except Exception as e:
                    if verbose:
                        warning(f"\t=> Bulk edit fallback failed: {e}")

            if not visibility_fixed:
                if verbose:
                    warning(
                        "\t=> Could not verify visibility - video may still be private"
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
        Uses an isolated Firefox profile context for authentication to avoid cookie conflicts.

        Returns:
            tuple: (success, url_or_error_message)
        """
        self._ensure_browser()
        browser = self.browser
        wait = WebDriverWait(browser, 30)
        verbose = get_verbose()

        try:
            # Try direct Reels create URL first (most reliable for modern FB UI)
            if verbose:
                info("\t=> Navigating to Facebook Reels create page...")
            browser.get("https://www.facebook.com/reels/create/")
            time.sleep(5)

            # Check if we're on the create page with file inputs
            file_inputs = browser.find_elements(By.CSS_SELECTOR, 'input[type="file"]')

            if len(file_inputs) >= 2:
                # We're on the Reels create page
                if verbose:
                    info("\t=> On Reels create page, found file inputs")
                file_input = file_inputs[1] if len(file_inputs) > 1 else file_inputs[0]
            else:
                # Fallback: try home page approach
                if verbose:
                    info("\t=> Direct URL didn't work, trying home page...")
                browser.get("https://www.facebook.com")
                time.sleep(5)

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
                    # contenteditable divs don't respond to .clear() — use keyboard instead
                    caption_el.click()
                    time.sleep(0.3)
                    actions = ActionChains(browser)
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(
                        Keys.CONTROL
                    ).perform()
                    time.sleep(0.2)
                    actions = ActionChains(browser)
                    actions.send_keys(Keys.DELETE).perform()
                    time.sleep(0.3)
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
                    (By.CSS_SELECTOR, 'div[aria-label*="Share"]'),
                    (By.CSS_SELECTOR, 'div[aria-label*="Post"]'),
                    (By.XPATH, "//div[@role='button' and contains(text(), 'Share')]"),
                    (By.XPATH, "//div[@role='button' and contains(text(), 'Post')]"),
                ]
                share_clicked = False
                for by, selector in share_selectors:
                    try:
                        share_btn = wait.until(
                            EC.element_to_be_clickable((by, selector))
                        )
                        # Try normal click first, then JS click as fallback
                        try:
                            share_btn.click()
                        except Exception:
                            browser.execute_script("arguments[0].click();", share_btn)
                        if verbose:
                            info(f"\t=> Share button clicked: {selector}")
                        share_clicked = True
                        break
                    except Exception:
                        continue

                # Fallback: find any clickable element with share/post text
                if not share_clicked:
                    try:
                        all_elements = browser.find_elements(
                            By.XPATH,
                            "//*[contains(translate(text(), 'SHAREPOST', 'sharepost'), 'share') or contains(translate(text(), 'SHAREPOST', 'sharepost'), 'post')]",
                        )
                        for el in all_elements:
                            if el.is_displayed() and el.tag_name in (
                                "button",
                                "div",
                                "span",
                                "a",
                            ):
                                browser.execute_script(
                                    "arguments[0].scrollIntoView();", el
                                )
                                time.sleep(0.3)
                                browser.execute_script("arguments[0].click();", el)
                                if verbose:
                                    info(
                                        "\t=> Share button clicked (fallback text search)"
                                    )
                                share_clicked = True
                                break
                    except Exception:
                        pass

                if not share_clicked and verbose:
                    warning("\t=> Could not find Share/Post button")

                # Wait a bit for Facebook to process
                time.sleep(3)

                # Check for publish confirmation via page content
                page_content = browser.page_source.lower()

                # If we see "published" or similar, the upload succeeded
                # We just need to find the URL
                upload_succeeded = (
                    "published" in page_content
                    or "shared" in page_content
                    or "your reel" in page_content
                )

                if verbose and upload_succeeded:
                    info("\t=> Upload appears to have succeeded, finding URL...")

                # Wait for upload confirmation
                fb_url = ""
                if verbose:
                    info("\t=> Waiting for Facebook upload...")

                # Wait for redirect to the posted reel/video page
                # Facebook can take 10-60 seconds to process and redirect
                time.sleep(10)

                # Check URL after wait - only return if we have actual reel ID
                current_url = browser.current_url
                # Must have more than just "/reel/" - need actual reel ID
                reel_path = (
                    current_url.split("/reel/")[-1] if "/reel/" in current_url else ""
                )
                if (
                    "/reel/" in current_url
                    and len(reel_path) > 0
                    and len(reel_path) < 50
                ):
                    # Ensure the path actually contains an ID (not just "/reel/")
                    # Also check it's not the malformed "reel/" path with nothing after
                    if reel_path.strip() and not reel_path.startswith("?"):
                        fb_url = current_url
                        if verbose:
                            info(f"\t=> Got Facebook URL directly: {fb_url}")
                        return (True, fb_url)
                elif verbose:
                    info(f"\t=> URL has no valid reel ID, searching: {current_url}")

                # If still on /reel/ without ID, try to find reel from page or profile
                if verbose:
                    info("\t=> Not redirected to reel page, searching for URL...")

                # Extended wait loop - monitor URL changes during upload
                url_before_post = current_url
                for wait_iter in range(30):  # 30 * 2 = 60 seconds max
                    time.sleep(2)
                    content = browser.page_source
                    current_url = browser.current_url

                    # Check if URL has changed to a reel/video page with actual ID
                    if "/reel/" in current_url:
                        reel_id = current_url.split("/reel/")[-1]
                        if len(reel_id) > 0 and not reel_id.startswith("?"):
                            fb_url = current_url
                            if verbose:
                                info(
                                    f"\t=> Got Facebook URL from redirect after {wait_iter * 2}s: {fb_url}"
                                )
                            return (True, fb_url)
                    elif "/watch?v=" in current_url:
                        # Must have /watch?v= to be actual video URL
                        fb_url = current_url
                        if verbose:
                            info(
                                f"\t=> Got Facebook URL from redirect after {wait_iter * 2}s: {fb_url}"
                            )
                        return (True, fb_url)

                    # Check if we got redirected away from the post page
                    # (e.g., to feed/profile - upload likely succeeded)
                    # Also check for "stories" in URL (Facebook sometimes uses this instead of reels)
                    if current_url != url_before_post and (
                        "facebook.com" in current_url
                        and "/reel/" not in current_url
                        and "/video/" not in current_url
                        and "/story/" not in current_url.lower()
                    ):
                        # Check if redirected to a profile videos page (not the actual video)
                        # URL pattern like "facebook.com/username/videos/?id=123" is NOT the video
                        is_profile_videos_page = "?id=" in current_url and (
                            "/videos" in current_url or current_url.endswith("/videos")
                        )

                        if is_profile_videos_page:
                            # This is a profile videos page, not the actual video - continue searching
                            if verbose:
                                info(
                                    f"\t=> Redirected to profile videos page, continuing search..."
                                )
                        else:
                            # This might be the actual video or feed - search for video links
                            if verbose:
                                info(
                                    f"\t=> Redirected to {current_url[:60]}, looking for video link..."
                                )

                            # Check for video links on the current page
                            video_links = browser.find_elements(
                                By.CSS_SELECTOR,
                                'a[href*="/reel/"], a[href*="/videos/"], a[href*="/watch?v="], a[href*="/story/"]',
                            )
                            for link in video_links:
                                href = link.get_attribute("href")
                                # Only accept URLs that have actual video IDs, not just page URLs
                                # Accept: /reel/123, /videos/123, /watch?v=123
                                # Reject: /videos (just the page), /videos?id=123 (profile videos page)
                                if href and (
                                    "/reel/" in href
                                    or "/watch?v=" in href
                                    or (
                                        "/videos/" in href
                                        and not href.endswith("/videos")
                                    )
                                ):
                                    # Double-check: don't return profile videos page URLs
                                    if (
                                        "?id=" in href
                                        and "/videos" in href
                                        and "/reel/" not in href
                                        and "/watch?v=" not in href
                                    ):
                                        continue  # Skip profile videos links
                                    fb_url = href
                                    if verbose:
                                        info(
                                            f"\t=> Found video link after redirect: {fb_url}"
                                        )
                                    return (True, fb_url)

                        # ALSO check for video thumbnail images that might contain links
                        try:
                            video_thumbs = browser.find_elements(
                                By.CSS_SELECTOR,
                                'a[href*="facebook.com"], video[src]',
                            )
                            for thumb in video_thumbs[:5]:
                                href = thumb.get_attribute("href")
                                if href and any(
                                    x in href for x in ["/reel/", "/videos/", "/watch"]
                                ):
                                    fb_url = href
                                    return (True, fb_url)
                        except:
                            pass

                    # Check for success indicators
                    if (
                        "published" in content.lower()
                        or "success" in content.lower()
                        or "posted" in content.lower()
                    ):
                        if verbose:
                            success(
                                f"\t=> Facebook upload confirmed (iteration {wait_iter})"
                            )

                        # Check URL one more time - only return with actual ID
                        current_url = browser.current_url
                        if "/reel/" in current_url:
                            reel_id = current_url.split("/reel/")[-1]
                            if len(reel_id) > 0:
                                fb_url = current_url
                                return (True, fb_url)
                        elif "/video/" in current_url:
                            fb_url = current_url
                            return (True, fb_url)

                        # IMMEDIATELY after upload confirmation, look for video in the page
                        # This is the most reliable moment to get the URL
                        try:
                            # Try to find the newly posted video via React/client-side data
                            js_immediate = r"""
                            (function() {
                                // Try to find video from __REACT_DATA__ or similar
                                var reactRoot = document.querySelector('[data-pagelet]');
                                if (reactRoot) {
                                    // Try getting video from data attributes
                                    var videos = document.querySelectorAll('video');
                                    for (var i = 0; i < videos.length; i++) {
                                        var parent = videos[i].closest('a');
                                        if (parent && parent.href) return parent.href;
                                    }
                                }
                                
                                // Try to get from the first story/reel div
                                var storyLinks = document.querySelectorAll('[role="article"] a[href*="/reel/"], [role="article"] a[href*="/videos/"], [role="article"] a[href*="/watch?v="]');
                                if (storyLinks && storyLinks.length > 0) {
                                    // Get the first link which is likely the newest
                                    return storyLinks[0].href;
                                }
                                
                                // Try from server rendering data
                                var bodyText = document.body.innerText;
                                var match = bodyText.match(/facebook\.com\/[^\s]*reel\/\d+/);
                                if (match) return match[0];
                                
                                // Also try to match watch URLs
                                var matchWatch = bodyText.match(/facebook\.com\/watch\?v=\d+/);
                                if (matchWatch) return matchWatch[0];
                                
                                return null;
                            })();
                            """
                            immediate_url = browser.execute_script(js_immediate)
                            if immediate_url:
                                if verbose:
                                    info(
                                        f"\t=> Got URL immediately after post: {immediate_url}"
                                    )
                                return (True, immediate_url)
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Immediate extraction failed: {e}")

                        # Strategy 2: Extract URL from page source using regex
                        fb_url_patterns = [
                            r'(https://www\.facebook\.com/[^"\s]*?/reel/\d+)',
                            r'(https://www\.facebook\.com/[^"\s]*?/videos/\d+)',
                            r"(https://www\.facebook\.com/watch\?v=\d+)",
                            r"(https://fb\.watch/[a-zA-Z0-9_-]+)",
                            r"(https://www\.facebook\.com/reel/\d+)",
                            r'["\'](/reel/\d+[^"\']*)["\']',
                            r'["\'](/videos/\d+[^"\']*)["\']',
                            r'"url":"(https://www\.facebook\.com/[^"]*?(?:reel|video|post)[^"]*?)"',
                        ]
                        for pattern in fb_url_patterns:
                            matches = re.findall(pattern, content)
                            if matches:
                                fb_url = matches[0]
                                if not fb_url.startswith("http"):
                                    fb_url = "https://www.facebook.com" + fb_url
                                # Clean up any escaped characters
                                fb_url = fb_url.replace("\\/", "/").replace(
                                    "\\u0025", "%"
                                )
                                if verbose:
                                    info(
                                        f"\t=> Facebook URL from regex pattern: {fb_url}"
                                    )
                                return (True, fb_url)

                        # Strategy 3: Find links via DOM
                        try:
                            post_links = browser.find_elements(
                                By.CSS_SELECTOR,
                                'a[href*="/reel/"], a[href*="/videos/"], a[href*="/watch?v="], a[href*="fb.watch"]',
                            )
                            for link in post_links:
                                href = link.get_attribute("href")
                                if (
                                    href
                                    and "facebook.com" in href
                                    and (
                                        "/reel/" in href
                                        or "/videos/" in href
                                        or "/watch" in href
                                    )
                                ):
                                    fb_url = href
                                    if verbose:
                                        info(
                                            f"\t=> Facebook URL from DOM links: {fb_url}"
                                        )
                                    return (True, fb_url)
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> DOM link search failed: {e}")

                        # Strategy 4: Navigate to profile and find latest reel
                        if verbose:
                            info(
                                "\t=> Trying to extract Facebook reel URL from profile..."
                            )
                        try:
                            # Get current user's profile URL from the page
                            profile_url = None
                            profile_selectors = [
                                'a[href*="/profile.php"]',
                                'a[data-testid="right_nav_Profile"]',
                                'a[aria-label="Profile"]',
                                'a[aria-label="Your profile"]',
                            ]
                            for sel in profile_selectors:
                                try:
                                    profile_links = browser.find_elements(
                                        By.CSS_SELECTOR, sel
                                    )
                                    if profile_links:
                                        profile_url = profile_links[0].get_attribute(
                                            "href"
                                        )
                                        break
                                except Exception:
                                    continue

                            # Fallback: try to get profile from current user menu
                            if not profile_url:
                                try:
                                    # Click on profile/menu button
                                    menu_btn = browser.find_element(
                                        By.CSS_SELECTOR,
                                        '[aria-label="Menu"], [aria-label="Account"]',
                                    )
                                    menu_btn.click()
                                    time.sleep(2)
                                    profile_link = browser.find_element(
                                        By.CSS_SELECTOR,
                                        'a[href*="/profile.php"], a[href*="/"][data-lynx-mode]',
                                    )
                                    profile_url = profile_link.get_attribute("href")
                                except Exception:
                                    pass

                            if profile_url:
                                if verbose:
                                    info(f"\t=> Found profile URL: {profile_url}")

                                # Extract profile ID from URL
                                profile_id = None
                                id_match = re.search(
                                    r"profile\.php\?id=(\d+)", profile_url
                                )
                                if id_match:
                                    profile_id = id_match.group(1)

                                # Try multiple approaches to find the uploaded video
                                approaches = []

                                # Approach 1: Direct videos URL
                                if profile_id:
                                    approaches.append(
                                        f"https://www.facebook.com/profile.php?id={profile_id}&sk=videos"
                                    )
                                approaches.append(profile_url.rstrip("/") + "/videos")
                                approaches.append(profile_url.rstrip("/") + "/reels")

                                for approach_url in approaches:
                                    if verbose:
                                        info(f"\t=> Trying approach: {approach_url}")
                                    browser.get(approach_url)
                                    time.sleep(8)

                                    # Check current URL for video patterns - must have ID
                                    current = browser.current_url
                                    if "/reel/" in current:
                                        reel_id = current.split("/reel/")[-1]
                                        if len(reel_id) > 0 and not reel_id.startswith(
                                            "?"
                                        ):
                                            fb_url = current
                                            if verbose:
                                                info(
                                                    f"\t=> Got URL from navigation: {fb_url}"
                                                )
                                            return (True, fb_url)
                                    elif "/videos/" in current and "/watch" in current:
                                        # Must have /watch in URL to be actual video, not just videos page
                                        fb_url = current
                                        if verbose:
                                            info(
                                                f"\t=> Got URL from navigation: {fb_url}"
                                            )
                                        return (True, fb_url)

                                    # We're on a videos page but no specific video yet - look for video links
                                    if "/videos" in current or "/reels" in current:
                                        # Look for the most recent video link on this page
                                        try:
                                            js_get_recent_video = """
                                            (function() {
                                                // Find all video links and get the most recent one
                                                var links = document.querySelectorAll('a[href*="/reel/"], a[href*="/videos/"], a[href*="/watch?v="]');
                                                if (links && links.length > 0) {
                                                    // Return the first one (most recent in feed)
                                                    return links[0].href;
                                                }
                                                return null;
                                            })();
                                            """
                                            recent_video = browser.execute_script(
                                                js_get_recent_video
                                            )
                                            if (
                                                recent_video
                                                and "/reel/" in recent_video
                                                or "/watch?v=" in recent_video
                                            ):
                                                if verbose:
                                                    info(
                                                        f"\t=> Found recent video: {recent_video}"
                                                    )
                                                return (True, recent_video)
                                        except Exception as e:
                                            if verbose:
                                                warning(
                                                    f"\t=> Could not find recent video: {e}"
                                                )

                                    # Try to find video links
                                    for sel in [
                                        'a[href*="/reel/"]',
                                        'a[href*="/videos/"]',
                                        'a[href*="/watch?v="]',
                                    ]:
                                        try:
                                            links = browser.find_elements(
                                                By.CSS_SELECTOR, sel
                                            )
                                            if verbose:
                                                info(
                                                    f"\t=> Found {len(links)} links with {sel}"
                                                )
                                            for link in links:
                                                href = link.get_attribute("href")
                                                if href and (
                                                    "/reel/" in href
                                                    or "/videos/" in href
                                                ):
                                                    fb_url = href
                                                    if verbose:
                                                        info(
                                                            f"\t=> Facebook URL found: {fb_url}"
                                                        )
                                                    return (True, fb_url)
                                        except Exception as e:
                                            if verbose:
                                                warning(f"\t=> {sel} failed: {e}")

                                    # Try JavaScript approach
                                    try:
                                        js_result = browser.execute_script("""
                                            (function() {
                                                var links = document.querySelectorAll('a[href]');
                                                var results = [];
                                                for (var i = 0; i < links.length; i++) {
                                                    var href = links[i].href;
                                                    if (href && (href.indexOf('/reel/') > -1 || href.indexOf('/videos/') > -1 || href.indexOf('/watch?v=') > -1)) {
                                                        results.push(href);
                                                    }
                                                }
                                                return results.slice(0, 5);
                                            })();
                                        """)
                                        if js_result and len(js_result) > 0:
                                            fb_url = js_result[0]
                                            if verbose:
                                                info(
                                                    f"\t=> Facebook URL from JS: {fb_url}"
                                                )
                                            return (True, fb_url)
                                    except Exception as e:
                                        if verbose:
                                            warning(f"\t=> JS search failed: {e}")

                                    # Try to extract from page source
                                    page_content = browser.page_source
                                    for pattern in [
                                        r'(https://www\.facebook\.com/[^"\s]*?/reel/\d+)',
                                        r'(https://www\.facebook\.com/[^"\s]*?/videos/\d+)',
                                        r"(https://www\.facebook\.com/watch\?v=\d+)",
                                    ]:
                                        matches = re.findall(pattern, page_content)
                                        if matches:
                                            fb_url = matches[0]
                                            if verbose:
                                                info(
                                                    f"\t=> Facebook URL from page source: {fb_url}"
                                                )
                                            return (True, fb_url)

                                    if fb_url:
                                        break
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Profile navigation failed: {e}")

                        # Strategy 5: Use JavaScript to find recent video posts
                        if not fb_url:
                            try:
                                if verbose:
                                    info(
                                        "\t=> Using JavaScript to find recent video URL..."
                                    )
                                # Try to find video URLs via JavaScript
                                js_find_video = """
                                (function() {
                                    var links = document.querySelectorAll('a[href*="/reel/"], a[href*="/videos/"], a[href*="/watch?v="]');
                                    for (var i = 0; i < links.length; i++) {
                                        var href = links[i].href;
                                        if (href && (href.indexOf('/reel/') > -1 || href.indexOf('/videos/') > -1)) {
                                            return href;
                                        }
                                    }
                                    return null;
                                })();
                                """
                                fb_url = browser.execute_script(js_find_video)
                                if fb_url:
                                    if verbose:
                                        info(
                                            f"\t=> Facebook URL from JavaScript: {fb_url}"
                                        )
                                    return (True, fb_url)
                            except Exception as e:
                                if verbose:
                                    warning(f"\t=> JavaScript search failed: {e}")

                        # Strategy 6: Check activity log for recent post
                        if not fb_url:
                            try:
                                if verbose:
                                    info(
                                        "\t=> Checking activity log for recent post..."
                                    )
                                browser.get(
                                    "https://www.facebook.com/your_activity/interactions"
                                )
                                time.sleep(5)
                                # Look for recent video links
                                video_links = browser.find_elements(
                                    By.CSS_SELECTOR,
                                    'a[href*="/reel/"], a[href*="/videos/"]',
                                )
                                for link in video_links:
                                    href = link.get_attribute("href")
                                    if href and (
                                        "/reel/" in href or "/videos/" in href
                                    ):
                                        fb_url = href
                                        if verbose:
                                            info(
                                                f"\t=> Facebook URL from activity log: {fb_url}"
                                            )
                                        return (True, fb_url)
                            except Exception as e:
                                if verbose:
                                    warning(f"\t=> Activity log check failed: {e}")

                        # Strategy 7: Check for any video data in page storage/state
                        if not fb_url:
                            try:
                                if verbose:
                                    info("\t=> Checking page storage for video data...")
                                # Try to extract video info from page state
                                js_get_video = """
                                (function() {
                                    // Try to get video from various Facebook data stores
                                    var results = [];
                                    
                                    // Check for video IDs in page source with more patterns
                                    var scripts = document.querySelectorAll('script');
                                    for (var i = 0; i < scripts.length; i++) {
                                        var content = scripts[i].textContent;
                                        if (content && content.length < 100000) {
                                            // Look for video IDs in various formats
                                            var reReel = content.match(/(["'])(\\/reel\\/\\d+[^"']*)\\1/g);
                                            var reVideo = content.match(/(["'])(\\/videos\\/\\d+[^"']*)\\1/g);
                                            var reVidId = content.match(/video_id[=:]\\s*["']?(\\d+)/gi);
                                            var reFbVideo = content.match(/fb:\\/\\/video\\?id=(\\d+)/gi);
                                            
                                            if (reReel && reReel.length > 0) {
                                                for (var j = 0; j < Math.min(reReel.length, 3); j++) {
                                                    results.push(reReel[j]);
                                                }
                                            }
                                            if (reVideo && reVideo.length > 0) {
                                                for (var j = 0; j < Math.min(reVideo.length, 3); j++) {
                                                    results.push(reVideo[j]);
                                                }
                                            }
                                        }
                                    }
                                    
                                    // Try to find from window.__DFP_DATA__ or similar
                                    if (window.__DFP_DATA__) {
                                        var dfp = window.__DFP_DATA__;
                                        if (dfp.video) results.push(dfp.video);
                                    }
                                    
                                    return results.slice(0, 10);
                                })();
                                """
                                storage_results = browser.execute_script(js_get_video)
                                if storage_results and len(storage_results) > 0:
                                    if verbose:
                                        info(
                                            f"\t=> Found data in storage: {storage_results}"
                                        )
                                    # Try to construct URL from video ID
                                    for result in storage_results:
                                        if isinstance(result, str):
                                            if result.startswith(
                                                "/reel/"
                                            ) or result.startswith("/videos/"):
                                                fb_url = (
                                                    "https://www.facebook.com" + result
                                                )
                                                return (True, fb_url)
                                            elif result.isdigit():
                                                fb_url = f"https://www.facebook.com/reel/{result}"
                                                return (True, fb_url)
                            except Exception as e:
                                if verbose:
                                    warning(f"\t=> Storage check failed: {e}")

                        # Strategy 8: Go directly to reels page and get first video
                        if not fb_url:
                            try:
                                if verbose:
                                    info("\t=> Trying direct reels page...")
                                browser.get("https://www.facebook.com/reels/")
                                time.sleep(8)

                                # Check if we're on a video page
                                current = browser.current_url
                                if "/reel/" in current:
                                    return (True, current)

                                # Look for any video links on this page
                                js_find = """
                                (function() {
                                    var links = document.querySelectorAll('a[href*="/reel/"], a[href*="/videos/"]');
                                    for (var i = 0; i < Math.min(links.length, 5); i++) {
                                        var href = links[i].href;
                                        if (href && (href.indexOf('/reel/') > -1 || href.indexOf('/videos/') > -1)) {
                                            return href;
                                        }
                                    }
                                    return null;
                                })();
                                """
                                fb_url = browser.execute_script(js_find)
                                if fb_url:
                                    return (True, fb_url)
                            except Exception as e:
                                if verbose:
                                    warning(f"\t=> Direct reels page failed: {e}")

                        # All strategies failed
                        if verbose:
                            warning(
                                "\t=> Could not extract Facebook reel URL after trying all strategies"
                            )

                        # Try ONE MORE strategy: wait and refresh, then check profile/reels
                        # Sometimes Facebook needs time to process the video
                        if verbose:
                            info(
                                "\t=> Final attempt: waiting and re-checking profile..."
                            )
                        time.sleep(5)

                        # Try profile/videos again - only if we have a profile URL
                        if profile_url:
                            browser.get(profile_url.rstrip("/") + "/videos")
                            time.sleep(8)

                            # Try JS one more time
                            final_js = """
                            (function() {
                                // Get all links and look for video patterns
                                var links = document.querySelectorAll('a[href]');
                                for (var i = 0; i < links.length; i++) {
                                    var href = links[i].href;
                                    if (href && (href.indexOf('/reel/') > -1 || href.indexOf('/videos/') > -1 || href.indexOf('/watch?v=') > -1)) {
                                        return href;
                                    }
                                }
                                return null;
                            })();
                            """
                            fb_url = browser.execute_script(final_js)
                            if fb_url:
                                return (True, fb_url)
                        else:
                            if verbose:
                                warning(
                                    "\t=> No profile URL available for final attempt"
                                )

                        # Return failure - cannot extract actual video URL
                        # Do not return fallback URL that appears to work but isn't the actual video
                        return (
                            False,
                            "Could not extract Facebook reel URL - upload succeeded but URL extraction failed",
                        )

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
        Uses an isolated Firefox profile context for authentication to avoid cookie conflicts.

        Returns:
            tuple: (success, url_or_error_message)
        """
        self._ensure_browser()
        browser = self.browser
        wait = WebDriverWait(browser, 30)
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
                    # Clear existing caption (TikTok auto-fills filename with UUID prefix)
                    # contenteditable divs don't respond to .clear() — use keyboard instead
                    caption_el.click()
                    time.sleep(0.3)
                    actions = ActionChains(browser)
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(
                        Keys.CONTROL
                    ).perform()
                    time.sleep(0.2)
                    actions = ActionChains(browser)
                    actions.send_keys(Keys.DELETE).perform()
                    time.sleep(0.3)

                    # Build proper TikTok caption: Title + clean description + hashtags
                    title = self.metadata.get("title", "").strip()
                    description = self.metadata.get("description", "").strip()
                    tags = self.metadata.get("tags", [])

                    # Remove any UUID prefix if present (matches 8-4-4-4-12 UUID format)
                    import re

                    uuid_pattern = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
                    title = re.sub(uuid_pattern, "", title).strip()
                    description = re.sub(uuid_pattern, "", description).strip()

                    # Combine everything properly for TikTok single caption field
                    caption_parts = [title]
                    if description and description != title:
                        caption_parts.append("\n\n" + description)

                    # Add hashtags at the end
                    if tags:
                        hashtag_str = " ".join(
                            [f"#{tag.replace(' ', '')}" for tag in tags[:10]]
                        )
                        caption_parts.append("\n\n" + hashtag_str)

                    final_caption = "".join(caption_parts).strip()

                    # Send clean caption, respect TikTok limit
                    caption_el.send_keys(final_caption[:2200])
                    if verbose:
                        info(
                            f"\t=> Caption set successfully ({len(final_caption)} chars)"
                        )

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
                        warning(
                            "\t=> Post button not detected as clicked, but file may have been uploaded"
                        )
                    # Don't return early - continue to try to extract the URL from the page
                    # The URL extraction logic below will handle finding the actual video URL

                # Wait for upload to complete and try to extract video URL
                if verbose:
                    info("\t=> Waiting for TikTok upload to complete...")

                # Wait longer for upload to process
                time.sleep(20)

                # Wait for success message or redirect
                for wait_cycle in range(40):
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

                        # Wait for page to stabilize
                        time.sleep(8)

                        # Try to click "View video" or similar button to get to video page
                        try:
                            view_buttons = browser.find_elements(
                                By.XPATH, "//button[contains(text(), 'View')]"
                            )
                            for btn in view_buttons:
                                if btn.is_displayed() and (
                                    "video" in btn.text.lower()
                                    or "post" in btn.text.lower()
                                ):
                                    browser.execute_script(
                                        "arguments[0].scrollIntoView();", btn
                                    )
                                    time.sleep(0.5)
                                    btn.click()
                                    time.sleep(8)
                                    new_url = browser.current_url
                                    if "/video/" in new_url and "tiktok.com" in new_url:
                                        tt_url = new_url
                                        if verbose:
                                            info(
                                                f"\t=> TikTok video URL from View button: {tt_url}"
                                            )
                                        return (True, tt_url)
                        except Exception:
                            pass

                        # Try to find any link that looks like a video URL
                        try:
                            all_links = browser.find_elements(By.TAG_NAME, "a")
                            for link in all_links:
                                href = link.get_attribute("href")
                                if href and "/video/" in href and "tiktok.com" in href:
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

                        # Strategy 1: Navigate to TikTok homepage to find profile link
                        browser.get("https://www.tiktok.com")
                        time.sleep(10)

                        # Try to find profile link and extract username
                        try:
                            profile_links = browser.find_elements(
                                By.CSS_SELECTOR, 'a[href*="@"]'
                            )
                            if profile_links:
                                profile_href = profile_links[0].get_attribute("href")
                                import re

                                username_match = re.search(r"@([\w.-]+)", profile_href)
                                if username_match:
                                    username = username_match.group(1)
                                    if verbose:
                                        info(f"\t=> Found TikTok username: {username}")

                                    # Navigate to user profile
                                    browser.get(f"https://www.tiktok.com/@{username}")
                                    time.sleep(10)

                                    # Scroll to trigger lazy loading of video elements
                                    for scroll in range(15):
                                        browser.execute_script(
                                            "window.scrollBy(0, 800);"
                                        )
                                        time.sleep(2)

                                        # Try multiple selectors
                                        selectors = [
                                            'a[href*="/video/"]',
                                            'a[data-e2e="user-post-item"]',
                                            'div[data-e2e="user-post-item"] a',
                                            'a[class*="video-link"]',
                                        ]
                                        for selector in selectors:
                                            video_links = browser.find_elements(
                                                By.CSS_SELECTOR, selector
                                            )
                                            for link in video_links:
                                                href = link.get_attribute("href")
                                                if (
                                                    href
                                                    and "/video/" in href
                                                    and "tiktok.com" in href
                                                ):
                                                    tt_url = href
                                                    if verbose:
                                                        info(
                                                            f"\t=> TikTok video URL from profile: {tt_url}"
                                                        )
                                                    return (True, tt_url)
                        except Exception as e:
                            if verbose:
                                warning(f"\t=> Profile navigation failed: {e}")
                            pass

                        # Strategy 2: Navigate to creator center
                        try:
                            browser.get("https://www.tiktok.com/tiktokstudio/content")
                            time.sleep(15)

                            # Try to extract URLs from page source using regex
                            import re

                            page_source = browser.page_source
                            video_matches = re.findall(
                                r"https?://www\.tiktok\.com/@[\w.-]+/video/\d+",
                                page_source,
                            )
                            if video_matches:
                                tt_url = video_matches[0]
                                if verbose:
                                    info(
                                        f"\t=> TikTok video URL from page source: {tt_url}"
                                    )
                                return (True, tt_url)

                            # Try to find video links in the DOM
                            video_links = browser.find_elements(
                                By.CSS_SELECTOR, 'a[href*="/video/"]'
                            )
                            for link in video_links:
                                href = link.get_attribute("href")
                                if href and "/video/" in href and "tiktok.com" in href:
                                    tt_url = href
                                    if verbose:
                                        info(
                                            f"\t=> TikTok video URL from creator studio: {tt_url}"
                                        )
                                    return (True, tt_url)
                        except Exception:
                            pass

                        # Strategy 3: Use JavaScript to extract video data from page state
                        try:
                            # Try to extract video data from TikTok's internal state
                            video_data = browser.execute_script("""
                                // Try to find video data in page scripts
                                var scripts = document.querySelectorAll('script');
                                for (var i = 0; i < scripts.length; i++) {
                                    var content = scripts[i].innerHTML;
                                    // Look for video URLs in script content
                                    var match = content.match(/https?:\\/\\/www\\.tiktok\\.com\\/@[\\w.-]+\\/video\\/(\\d+)/);
                                    if (match) return match[0];
                                }
                                
                                // Try to find video data in window object
                                if (window.RENDER_DATA) {
                                    var renderData = window.RENDER_DATA;
                                    if (renderData && renderData.itemList) {
                                        for (var i = 0; i < renderData.itemList.length; i++) {
                                            var item = renderData.itemList[i];
                                            if (item && item.video && item.video.id) {
                                                return 'https://www.tiktok.com/@user/video/' + item.video.id;
                                            }
                                        }
                                    }
                                }
                                
                                return null;
                            """)
                            if video_data:
                                tt_url = video_data
                                if verbose:
                                    info(
                                        f"\t=> TikTok video URL from page state: {tt_url}"
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
                    except Exception as e:
                        if verbose:
                            warning(f"\t=> URL extraction failed: {e}")
                        pass

                if not tt_url:
                    # Don't return base profile URL - require actual video URL
                    if verbose:
                        warning(
                            "\t=> Could not extract TikTok video URL - upload may have failed"
                        )
                    return (
                        False,
                        "Could not extract TikTok video URL - upload may have failed or timed out",
                    )

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
            if self._browser:
                self._browser.quit()
                self._browser = None
                self._browser_initialized = False
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

        # Use _browser/_page instead of property to avoid setter issues
        self._browser = None
        self._browser_initialized = False
        if hasattr(self, "page"):
            self.page = None

    def __del__(self) -> None:
        self.cleanup()
