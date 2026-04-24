import re
import time
import os
import random
import requests
from datetime import datetime
from llm_provider import generate_text, get_model_for_job
from status import warning, info


# BCP-47 locale to 2-letter country code (ISO 3166-1 alpha-2)
LOCALE_TO_COUNTRY = {
    "en-US": "US",
    "en-GB": "GB",
    "id-ID": "ID",
    "ms-MY": "MY",
    "jv-ID": "ID",
    "su-ID": "ID",
    "ja-JP": "JP",
    "ko-KR": "KR",
    "zh-CN": "CN",
    "hi-IN": "IN",
    "es-ES": "ES",
    "fr-FR": "FR",
    "de-DE": "DE",
    "pt-PT": "PT",
}


def search_tavily(query, niche, max_results=8, locale=None):
    """
    Search Tavily for trending topics.

    Args:
        query (str): The search query
        niche (str): The niche for context
        max_results (int): Maximum number of results

    Returns:
        list: List of (title, content) tuples
    """
    try:
        from tavily import TavilyClient

        api_key = os.environ.get("TAVILY_API_KEY", "")
        if api_key:
            tavily_client = TavilyClient(api_key=api_key)
            # Use country code for locale if available
            search_kwargs = {
                "query": query,
                "max_results": max_results,
                "include_answer": True,
            }
            if locale and locale in LOCALE_TO_COUNTRY:
                search_kwargs["country"] = LOCALE_TO_COUNTRY[locale]
            response = tavily_client.search(**search_kwargs)
            if response.get("results"):
                results = []
                for r in response["results"][:max_results]:
                    title = r.get("title", "")
                    content = r.get("content", "")[:150]
                    if title and content:
                        results.append((title, content))
                return results
    except Exception as e:
        warning(f"Tavily failed: {e}")
    return []


def search_exa(query, niche, num_results=8, locale=None):
    """
    Search Exa for trending topics.

    Args:
        query (str): The search query
        niche (str): The niche for context
        num_results (int): Number of results

    Returns:
        list: List of (title, content) tuples
    """
    try:
        from exa_py import Exa

        api_key = os.environ.get("EXA_API_KEY", "")
        if api_key:
            exa = Exa(api_key=api_key)
            search_kwargs = {
                "query": query,
                "num_results": num_results,
                "type": "neural",
            }
            if locale and locale in LOCALE_TO_COUNTRY:
                search_kwargs["country"] = LOCALE_TO_COUNTRY[locale]
            response = exa.search(**search_kwargs)
            if response.results:
                results = []
                for r in response.results:
                    text = r.text[:150] if r.text else r.get("extract", "")[:150]
                    if r.title and text:
                        results.append((r.title, text))
                return results
    except Exception as e:
        warning(f"Exa failed: {e}")
    return []


def search_ddgs(query, max_results=8):
    """
    Search DuckDuckGo for trending topics.

    Args:
        query (str): The search query
        max_results (int): Maximum number of results

    Returns:
        list: List of (title, content) tuples
    """
    try:
        from ddgs import DDGS

        # Disable proxy
        for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
            os.environ.pop(k, None)

        ddg = DDGS()
        results = ddg.text(query, max_results=max_results)
        if results:
            res = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                if title and body:
                    res.append((title, body[:100]))
            return res
    except Exception as e:
        warning(f"ddgs failed: {e}")
    return []


def fetch_wikipedia():
    """
    Fetch Wikipedia featured content.

    Returns:
        list: List of (title, content) tuples
    """
    try:
        now = datetime.now()
        today = now.strftime("%Y/%m/%d")
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/feed/featured/{today}"
        resp = requests.get(wiki_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            results = []

            # News
            news = data.get("news", [])
            for item in news[:8]:
                story = re.sub(r"<[^>]+>", "", item.get("story", "")).strip()
                links = item.get("links", [])
                titles = [l.get("titles", {}).get("normalized", "") for l in links]
                if story:
                    entry = story[:150]
                    if titles:
                        entry += f" ({', '.join(titles[:2])})"
                    results.append(("Wikipedia News", entry))

            # Featured Article
            tfa = data.get("tfa", {})
            if tfa:
                title = tfa.get("titles", {}).get("normalized", "")
                extract = tfa.get("extract", "")[:200]
                if title and extract:
                    results.append((f"Wikipedia Featured Article: {title}", extract))

            # Most Read
            most_read = data.get("mostread", {}).get("articles", [])
            for a in most_read[:10]:
                title = a.get("titles", {}).get("normalized", "")
                if title:
                    results.append(("Wikipedia Most Read", title))

            return results
    except Exception as e:
        warning(f"Wikipedia API failed: {e}")
    return []


def fetch_google_trends(geo="US"):
    """
    Fetch Google Trends RSS.

    Args:
        geo (str): Geographic region

    Returns:
        list: List of (title, content) tuples
    """
    try:
        trends_url = f"https://trends.google.com/trending/rss?geo={geo}"
        resp = requests.get(
            trends_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"}
        )
        if resp.status_code == 200:
            titles = re.findall(r"<title>(.*?)</title>", resp.text)
            results = []
            for t in titles[1:20]:
                t_clean = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", t).strip()
                if t_clean and len(t_clean) > 3:
                    results.append((f"Google Trends ({geo or 'Global'})", t_clean))
            return results
    except Exception as e:
        warning(f"Google Trends failed: {e}")
    return []


def search_firecrawl(query, limit=8):
    """
    Search Firecrawl for trending topics.

    Args:
        query (str): The search query
        limit (int): Maximum number of results

    Returns:
        list: List of (title, content) tuples
    """
    try:
        from firecrawl import Firecrawl

        api_key = os.environ.get("FIRECRAWL_API_KEY", "")
        if api_key:
            firecrawl = Firecrawl(api_key=api_key)
            search_result = firecrawl.search(
                query=query,
                limit=limit,
            )
            if search_result and hasattr(search_result, "web"):
                web_results = search_result.web or []
                results = []
                for item in web_results[:limit]:
                    title = item.title if hasattr(item, "title") else ""
                    desc = (
                        item.description[:120]
                        if hasattr(item, "description") and item.description
                        else ""
                    )
                    if title and desc:
                        results.append((title, desc))
                return results
    except Exception as e:
        warning(f"Firecrawl failed: {e}")
    return []


def research_trending_topics(niche: str, locale: str = None) -> str:
    """
    Researches trending topics with dynamic, unique queries.
    Priority: Tavily -> Exa -> ddgs -> Wikipedia -> Google RSS -> Firecrawl
    Uses randomized angles to ensure unique results every time.
    """
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
    base_query = niche
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
    query = random.choice(dynamic_queries)
    topics_found = search_tavily(query, niche, max_results=8, locale=locale)
    if topics_found:
        context_parts.append(
            f"Tavily ({query[:40]}):\n"
            + "\n".join(f"- {t}: {c}" for t, c in topics_found[:8])
        )
        info(f"   ✅ Tavily: {len(topics_found)} results")

    # Method 2: Exa
    info("   🔍 Searching Exa...")
    query = random.choice(dynamic_queries)
    topics_found = search_exa(query, niche, num_results=8, locale=locale)
    if topics_found:
        context_parts.append(
            f"Exa ({query[:40]}):\n"
            + "\n".join(f"- {t}: {c}" for t, c in topics_found[:8])
        )
        info(f"   ✅ Exa: {len(topics_found)} results")

    # Method 3: ddgs (DuckDuckGo via Bing backend - bypasses Indonesia block)
    info("   🔍 Searching DuckDuckGo (ddgs)...")
    query = random.choice(dynamic_queries)
    topics_found = search_ddgs(query, max_results=8)
    if topics_found:
        context_parts.append(
            f"DuckDuckGo ({query[:40]}):\n"
            + "\n".join(f"- {t}: {c}" for t, c in topics_found[:8])
        )
        info(f"   ✅ ddgs: {len(topics_found)} results")

    # Method 4: Wikipedia
    info("   🔍 Fetching Wikipedia...")
    topics_found = fetch_wikipedia()
    if topics_found:
        # Group by type
        wiki_parts = []
        for title, content in topics_found:
            wiki_parts.append(f"- {title}: {content}")
        context_parts.append("Wikipedia:\n" + "\n".join(wiki_parts))
        info(f"   ✅ Wikipedia: fetched")

    # Method 5: Google Trends RSS
    info("   🔍 Fetching Google Trends...")
    for geo in ["US", ""]:
        topics_found = fetch_google_trends(geo)
        if topics_found:
            context_parts.append(
                f"Google Trends ({geo or 'Global'}):\n"
                + "\n".join(f"- {t}: {c}" for t, c in topics_found[:15])
            )
            info(f"   ✅ Google Trends: {len(topics_found)} topics")
            break

    # Method 6: Firecrawl (last fallback)
    info("   🔍 Searching Firecrawl...")
    if not any(
        p
        for p in context_parts
        if any(x in p.lower() for x in ["tavily", "exa", "duckduckgo", "ddgs"])
    ):
        query = random.choice(dynamic_queries)
        topics_found = search_firecrawl(query, limit=8)
        if topics_found:
            context_parts.append(
                f"Firecrawl ({query[:40]}):\n"
                + "\n".join(f"- {t}: {c}" for t, c in topics_found[:8])
            )
            info(f"   ✅ Firecrawl: {len(topics_found)} results")

    if context_parts:
        return "\n\n".join(context_parts)
    return ""


def extract_facts(research_text: str, topic_hint: str) -> dict:
    """
    Extract structured facts from raw research text.

    Args:
        research_text: Raw text from web research (same text used for topic inspiration)
        topic_hint: The topic string being researched (used for fallback topic_identifier)

    Returns:
        dict with keys:
            person_names: list[str] — people's names found
            locations: list[str] — places found
            dates: list[str] — dates/years found
            organizations: list[str] — org names found
            key_facts: list[str] — specific claims (numbers, events)
            topic_identifier: str|None — explicit entity name if topic is a specific known thing 
                (Bigfoot, Bermuda Triangle), else None
            source_urls: list[str] — URLs facts came from
            confidence: str — "high" | "medium" | "low"
            extraction_note: str — human-readable summary
    """
    # Check if topic_hint is a specific known identifier (heuristic)
    specific_identifiers = [
        "bigfoot", "bermuda triangle", "loch ness", "area 51",
        "roswell", "yeti", "mothman", "chupacabra",
        "jack the ripper", "zodiac killer", "d bunker"
    ]
    topic_is_specific = topic_hint.lower().strip() in specific_identifiers or any(
        topic_hint.lower().strip() in ident for ident in specific_identifiers
    )
    
    # Build LLM prompt (system prompt incorporated into user prompt)
    system_prompt = "You are a fact extraction specialist. Extract all specific entities from the text. Return ONLY a JSON object."
    user_prompt = f"{system_prompt}\n\nText to extract from:\n{research_text}\n\nTopic hint: {topic_hint}"
    
    try:
        model = get_model_for_job("topic")
        response = generate_text(user_prompt, model_name=model, job="topic")
        
        # Try to parse JSON from response
        import json
        
        # Find JSON in response
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # Extract fields with defaults
            person_names = data.get("person_names", [])
            locations = data.get("locations", [])
            dates = data.get("dates", [])
            organizations = data.get("organizations", [])
            key_facts = data.get("key_facts", [])
            topic_identifier = data.get("topic_identifier")
            source_urls = data.get("source_urls", [])
            
            # Calculate confidence
            total_facts = len(person_names) + len(locations) + len(dates) + len(organizations) + len(key_facts)
            if total_facts >= 3:
                confidence = "high"
            elif total_facts >= 1:
                confidence = "medium"
            else:
                confidence = "low"
            
            # Build extraction note
            extraction_note = f"Extracted {total_facts} facts from research text"
            
            return {
                "person_names": person_names,
                "locations": locations,
                "dates": dates,
                "organizations": organizations,
                "key_facts": key_facts,
                "topic_identifier": topic_identifier,
                "source_urls": source_urls,
                "confidence": confidence,
                "extraction_note": extraction_note
            }
        else:
            raise ValueError("No JSON found in response")
    except Exception:
        # Edge case: no facts found
        if topic_is_specific:
            return {
                "person_names": [],
                "locations": [],
                "dates": [],
                "organizations": [],
                "key_facts": [],
                "topic_identifier": topic_hint,
                "source_urls": [],
                "confidence": "low",
                "extraction_note": f"No facts found, using topic hint as identifier: {topic_hint}"
            }
        else:
            return {
                "person_names": [],
                "locations": [],
                "dates": [],
                "organizations": [],
                "key_facts": [],
                "topic_identifier": None,
                "source_urls": [],
                "confidence": "low",
                "extraction_note": "No facts extracted from research text"
            }
