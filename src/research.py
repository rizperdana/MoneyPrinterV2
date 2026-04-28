import re
import time
import os
import random
import requests
from datetime import datetime
from src.llm_provider import generate_text, get_model_for_job
from src.status import warning, info


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


def fetch_google_trends(locale: str = "en-US"):
    """
    Fetch Google Trends RSS.

    Args:
        locale (str): BCP-47 locale code (e.g., "en-US", "id-ID")

    Returns:
        list: List of (title, content) tuples
    """
    try:
        # Map locale to ISO 3166-1 alpha-2 country code
        geo = LOCALE_TO_COUNTRY.get(locale, "US") if locale else "US"
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


def search_linkup(query: str, max_results: int = 8) -> list:
    """Search via Linkup API. API key via LINKUP_API_KEY env var."""
    api_key = os.environ.get("LINKUP_API_KEY")
    if not api_key:
        logging.warning("LINKUP_API_KEY not set, skipping Linkup")
        return []
    try:
        response = requests.post(
            "https://api.linkup.so/v1/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "q": query,
                "depth": "standard",
                "maxResults": max_results,
                "outputType": "searchResults"
            },
            timeout=30
        )
        if response.status_code != 200:
            logging.warning(f"Linkup search failed: {response.status_code}")
            return []
        data = response.json()
        return [
            (item.get("name", ""), item.get("content", "")[:150])
            for item in data.get("results", [])[:max_results]
            if item.get("name") and item.get("content")
        ]
    except Exception as e:
        logging.warning(f"Linkup search exception: {e}")
        return []


def research_trending_topics(niche: str, locale: str = None) -> str:
    """
    3-phase tiered research strategy.
    Phase 1 — PREMIUM DISCOVERY: Rotate ONE premium service per run (Tavily→Exa→Firecrawl→Linkup).
    Phase 2 — FREE EXPANSION: Only if Phase 1 < 3 results. ddgs (2 queries), Wikipedia, Google Trends.
    Phase 3 — MERGE & RANK: Deduplicate by title, build context string.
    """
    from src.topic_tracker import load_research_state, save_research_state, get_next_premium_service

    now = datetime.now()
    state = load_research_state()

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
    random.seed(int(now.timestamp()) % 10000)
    angle = random.choice(angle_modifiers)
    base_query = niche
    dynamic_queries = [
        f"{angle} {base_query}",
        f"{base_query} {now.year} facts",
        f"what's trending in {base_query} right now",
        f"unknown {base_query} secrets",
        f"{base_query} viral moments",
    ]

    # === PHASE 1: PREMIUM DISCOVERY (one service, rotated) ========================
    premium_results = []
    seq = state.get("premium_sequence", ["tavily", "exa", "firecrawl", "linkup"])
    next_service = get_next_premium_service(state)
    try:
        svc_idx = seq.index(next_service)
    except ValueError:
        svc_idx = 0
    service_order = seq[svc_idx:] + seq[:svc_idx]

    info("   🔍 Phase 1: Premium discovery...")
    for service in service_order:
        if service == "tavily" and os.environ.get("TAVILY_API_KEY"):
            query = random.choice(dynamic_queries)
            topics_found = search_tavily(query, niche, max_results=8, locale=locale)
            if topics_found:
                premium_results.extend(topics_found)
                info(f"   ✅ Tavily: {len(topics_found)} results")
                state["last_premium"] = service
                if len(premium_results) >= 3:
                    break
        elif service == "exa" and os.environ.get("EXA_API_KEY"):
            query = random.choice(dynamic_queries)
            topics_found = search_exa(query, niche, num_results=8, locale=locale)
            if topics_found:
                premium_results.extend(topics_found)
                info(f"   ✅ Exa: {len(topics_found)} results")
                state["last_premium"] = service
                if len(premium_results) >= 3:
                    break
        elif service == "firecrawl" and os.environ.get("FIRECRAWL_API_KEY"):
            query = random.choice(dynamic_queries)
            topics_found = search_firecrawl(query, limit=8)
            if topics_found:
                premium_results.extend(topics_found)
                info(f"   ✅ Firecrawl: {len(topics_found)} results")
                state["last_premium"] = service
                if len(premium_results) >= 3:
                    break
        elif service == "linkup":
            topics_found = search_linkup(niche, max_results=8)
            if topics_found:
                premium_results.extend(topics_found)
                info(f"   ✅ Linkup: {len(topics_found)} results")
                state["last_premium"] = service
                if len(premium_results) >= 3:
                    break

    # === PHASE 2: FREE EXPANSION (only if premium < 3 results) ===================
    if len(premium_results) < 3:
        info("   🔍 Phase 2: Free expansion (premium yielded < 3 results)...")
        free_results = []
        # ddgs: 2 query variations
        ddgs_q1 = f"{niche} interesting facts"
        ddgs_q2 = f"{niche} surprising discoveries"
        free_results.extend(search_ddgs(ddgs_q1, max_results=4))
        free_results.extend(search_ddgs(ddgs_q2, max_results=4))
        # Wikipedia
        wiki_results = fetch_wikipedia()
        if wiki_results:
            free_results.extend(wiki_results)
        # Google Trends
        trends_results = fetch_google_trends(locale)
        if trends_results:
            free_results.extend(trends_results)
        # Merge and deduplicate by title
        if free_results:
            seen = set()
            unique_free = []
            for r in free_results:
                key = r[0][:50].lower()
                if key not in seen:
                    seen.add(key)
                    unique_free.append(r)
            premium_results.extend(unique_free[:max(0, 3 - len(premium_results))])

    save_research_state(state)

    # === PHASE 3: MERGE & RANK ===================================================
    seen = set()
    unique_results = []
    for r in premium_results:
        key = r[0][:50].lower()
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    if unique_results:
        return "\n\n".join([f"- {t}: {c[:100]}" for t, c in unique_results[:8]])
    return ""
