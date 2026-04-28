COMPLEXITY_WEIGHTS = {
    "entities": 0.25,
    "temporal": 0.20,
    "causal": 0.20,
    "abstract": 0.20,
    "technical": 0.15,
}

COMPLEXITY_TIERS = {
    "SIMPLE": (0, 0.15),
    "MODERATE": (0.15, 0.35),
    "COMPLEX": (0.35, 1.0),
}

DURATION_RANGES = {
    "SIMPLE": {"sweet": (50, 70), "range": (40, 90)},
    "MODERATE": {"sweet": (90, 120), "range": (60, 180)},
    "COMPLEX": {"sweet": (120, 180), "range": (90, 240)},
}

SCENE_SECONDS_PER_TIER = {
    "SIMPLE": (25, 30),
    "MODERATE": (20, 25),
    "COMPLEX": (15, 20),
}


def analyze_complexity(subject: str, audience: str = "general") -> dict:
    """Analyze subject complexity and return tier."""
    if not subject or not subject.strip():
        return {"tier": "SIMPLE", "audience": audience}
    text = subject.strip()
    words = text.split()
    word_count = len(words)
    
    # VERY short simple subjects are SIMPLE
    if word_count <= 2:
        has_complex = any([
            re.search(r'\b(quantum|algorithm|physics|philosophy|theory|concept)\b', text, re.I),
            re.search(r'\b(how|why|what if)\b', text, re.I)
        ])
        if not has_complex:
            return {"tier": "SIMPLE", "audience": audience}
    
    # Known complex topic patterns -> COMPLEX
    complex_patterns = [
        r'\bquantum\s+entanglement\b',
        r'\bgeneral\s+relativity\b',
        r'\bspecial\s+relativity\b',
        r'\bblack\s+hole\b',
        r'\bneural\s+network\b',
        r'\bdeep\s+learning\b',
        r'\bmachine\s+learning\b',
        r'\bhistory\s+of\s+ancient\b',
        r'\bancient\s+civilization\b',
        r'\bworld\s+war\s+\d+\b',
    ]
    for pat in complex_patterns:
        if re.search(pat, text, re.I):
            return {"tier": "COMPLEX", "audience": audience}
    
    indicators = {
        "entities": min(word_count, 3) / 3.0,
        "temporal": len(re.findall(r'\b(now|then|past|future|century|year|day|age|ancient|modern|history|era)\b', text, re.I)) / max(word_count, 1),
        "causal": len(re.findall(r'\bbecause|therefore|so|thus|reason|result|effect\b', text, re.I)) / max(word_count, 1),
        "abstract": len(re.findall(r'\btheory|concept|belief|feeling|justice|meaning|truth|wisdom|love\b', text, re.I)) / max(word_count, 1),
        "technical": len(re.findall(r'\balgorithm|system|process|method|quantum|physics|technology\b', text, re.I)) / max(word_count, 1),
    }
    score = sum(indicators[k] * COMPLEXITY_WEIGHTS[k] for k in COMPLEXITY_WEIGHTS)
    for tier, (lo, hi) in COMPLEXITY_TIERS.items():
        if lo <= score < hi:
            return {"tier": tier, "audience": audience}
    return {"tier": "COMPLEX", "audience": audience}


def get_duration_for_tier(tier: str) -> dict:
    return DURATION_RANGES.get(tier, DURATION_RANGES["MODERATE"])


def get_scenes_for_tier(tier: str, duration_seconds: int) -> int:
    min_sec, max_sec = SCENE_SECONDS_PER_TIER.get(tier, (20, 25))
    return max(1, min(duration_seconds // min_sec, 16))


def validate_duration(duration_seconds: int, tier: str = "MODERATE") -> dict:
    tier_range = DURATION_RANGES.get(tier, DURATION_RANGES["MODERATE"])
    sweet_min, sweet_max = tier_range["sweet"]
    range_min, range_max = tier_range["range"]
    in_sweet = sweet_min <= duration_seconds <= sweet_max
    in_range = range_min <= duration_seconds <= range_max
    if in_sweet:
        return {"valid": True, "in_range": True, "sweet": True, "message": "Duration in sweet spot"}
    elif in_range:
        return {"valid": True, "in_range": True, "sweet": False, "message": "Acceptable range"}
    return {"valid": False, "in_range": False, "sweet": False, "message": f"Duration {duration_seconds}s outside {tier} range ({range_min}-{range_max}s)"}


def estimate_duration_from_word_count(word_count: int, wpm: int = 150) -> int:
    return int((word_count / wpm) * 60)


RESOLUTION_PATTERNS = [
    r"\bthat's\s+why", r"\bin\s+conclusion", r"\bthe\s+answer\s+is", r"\bso\s+remember", 
    r"\bthat's\s+how", r"\bfinally", r"\bin\s+the\s+end", r"\bnow\s+you\s+know",
    r"\bbut\s+then\b", r"\beverything\s+changed", r"\bhappily\s+ever\s+after",
    r"\blived\s+happily", r"\bthey\s+lived", r"\bto\s+sum up",
]
ARC_MARKERS = {
    "STASIS": [r"\boriginally\b", r"\btraditionally\b", r"\bfor\s+centuries\b"],
    "DISRUPTION": [r"\bbut\s+then\b", r"\bhowever\b", r"\beverything\s+changed\b", r"\bsuddenly\b"],
    "ATTEMPT": [r"\bthey\s+tried\b", r"\bpeople\s+tried\b"],
    "RESOLUTION": [r"\bsuccess\b", r"\bfinally\b", r"\bin\s+the\s+end\b", r"\btoday\b", r"\bnow\s+you\s+know\b"],
}


def validate_completion(script: str) -> dict:
    if not script or not script.strip():
        return {"complete": False, "has_resolution": False, "arc_stages": [], "retry": True, "message": "Empty script"}
    text = script.strip()
    has_resolution = any(re.search(p, text, re.I) for p in RESOLUTION_PATTERNS)
    found_stages = [stage for stage, patterns in ARC_MARKERS.items() if any(re.search(p, text, re.I) for p in patterns)]
    arc_complete = "DISRUPTION" in found_stages or "RESOLUTION" in found_stages
    if has_resolution and arc_complete:
        return {"complete": True, "has_resolution": True, "arc_stages": found_stages, "retry": False, "message": "Complete"}
    elif has_resolution:
        return {"complete": True, "has_resolution": True, "arc_stages": found_stages, "retry": False, "message": "Complete (resolution only)"}
    return {"complete": False, "has_resolution": False, "arc_stages": found_stages, "retry": True, "message": "Incomplete - missing resolution"}


def check_and_complete_script(script: str) -> tuple[str, bool]:
    result = validate_completion(script)
    return (script, result["retry"]) if result["retry"] else (script, False)


from src.llm_provider import generate_text, get_model_for_job
from src.llm_prompts import get_prompt
import re, json


def generate_response(prompt: str, job: str = None) -> str:
    """
    Generates an LLM Response based on a prompt and optional job type.

    Args:
        prompt (str): The prompt to use in the text generation.
        job (str, optional): The job type (topic, script, seo_tags, image_prompts, title_desc)

    Returns:
        response (str): The generated AI response.
    """
    model = get_model_for_job(job) if job else None
    print(f"[📝 LLM] Using model: {model}")
    result = generate_text(prompt, model_name=model, job=job)
    print(f"[✅ LLM] Generated {len(result)} chars")
    return result


def generate_topic_response(niche: str, research_context: str = None, audience: str = "general") -> str:
    """
    Generate topic ideas about niche, optionally using research context.

    Args:
        niche (str): The niche for topic generation.
        research_context (str, optional): Additional research context.
        audience (str): Target audience level (default: "general").

    Returns:
        str: Raw LLM response with topics.
    """
    if research_context:
        prompt = get_prompt("topic_with_research", niche=niche, research_context=research_context)
    else:
        prompt = get_prompt("topic_no_research", niche=niche)

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    return generate_response(prompt, job="topic")


def generate_script_response(subject: str, locale: str, sentence_length: int, audience: str = "general") -> str:
    """
    Generate script for subject.

    Args:
        subject (str): The subject for the script.
        locale (str): BCP-47 locale code (e.g., en-US, id-ID).
        sentence_length (int): The number of sentences in the script.
        audience (str): Target audience level (default: "general").

    Returns:
        str: Raw script text.
    """
    prompt = get_prompt(
        "script",
        subject=subject,
        language=locale,
        locale=locale,
        sentence_length=sentence_length,
        max_words_per_sentence=12,
        max_total_words=100
    )

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    completion = generate_response(prompt, job="script")
    completion = re.sub(r"\*", "", completion)
    return completion


def generate_title_response(subject: str, audience: str = "general") -> str:
    """
    Generate YouTube title for subject.

    Args:
        subject (str): The subject for the title.
        audience (str): Target audience level (default: "general").

    Returns:
        str: The title (validated 3-8 words).
    """
    prompt = get_prompt("title_retry", subject=subject)

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    title = generate_response(prompt, job="title_desc")

    # Validate word count (3-8 words per FIX_STORYTELLING.md)
    word_count = len(title.split())
    if word_count < 3 or word_count > 8:
        # Retry once with explicit instruction
        retry_prompt = get_prompt("title_retry", subject=subject)
        retry_prompt += f"\n\nAudience level: {audience}"
        title = generate_response(retry_prompt, job="title_desc")
        word_count = len(title.split())
        # If still invalid after retry, truncate to fit
        if word_count > 8:
            words = title.split()[:8]
            title = " ".join(words)
        elif word_count < 3:
            words = title.split()
            while len(words) < 3:
                words.append("interesting")
            title = " ".join(words)

    # Hard cap: truncate to 100 chars (prefer word boundaries)
    if len(title) > 100:
        title = title[:101]
        last_space = title.rfind(" ")
        if last_space > 50:
            title = title[:last_space]
        else:
            title = title[:100].rstrip()

    return title


def generate_description_response(script: str, audience: str = "general") -> str:
    """
    Generate description from script.

    Args:
        script (str): The script text.
        audience (str): Target audience level (default: "general").

    Returns:
        str: The description with hashtags.
    """
    prompt = get_prompt("description", script=script)

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    return generate_response(prompt, job="title_desc")


def generate_tags_response(subject: str, audience: str = "general") -> list:
    """
    Generate SEO tags as JSON list.

    Args:
        subject (str): The subject for tags.
        audience (str): Target audience level (default: "general").

    Returns:
        list: List of tags.
    """
    prompt = get_prompt("seo_tags", subject=subject)

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    tags_raw = generate_response(prompt, job="seo_tags")
    try:
        cleaned = str(tags_raw).replace("```json", "").replace("```", "").strip()
        tags = json.loads(cleaned)
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []
    return tags


def generate_image_prompts_response(subject: str, script: str, audience: str = "general") -> list:
    """
    Generate image prompts from script.

    Args:
        subject (str): The subject.
        script (str): The script text.
        audience (str): Target audience level (default: "general").

    Returns:
        list: List of image prompts.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", script) if len(s.strip()) > 10]
    n_scenes = min(max(len(sentences), 3), 5)

    # Z-Image Turbo optimized prompt template
    # Structure: subject+action, environment, lighting, composition, style, quality, inline constraints
    # Target: 80-250 words per prompt (supports full detail richness)
    formatted_sentences = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences[:n_scenes]))
    prompt = get_prompt(
        "image_prompt",
        subject=subject,
        sentences=formatted_sentences,
        n_scenes=n_scenes,
        num_inference_steps=12,
        acceleration="high",
        image_size="landscape_16_9"
    )

    # Add audience context to prompt
    prompt += f"\n\nAudience level: {audience}"

    completion = generate_response(prompt, job="image_prompts")

    image_prompts = []
    lines = completion.split("\n")
    for line in lines:
        line = line.strip()
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

    # Fallback: generate Z-Image Turbo formatted prompts from script sentences
    if not image_prompts:
        for sentence in sentences[:n_scenes]:
            visual = (
                f"A cinematic scene depicting {sentence.strip()[:100]} "
                f"in Studio Ghibli style with soft earthy watercolor lighting and warm inviting palette. "
                f"Subject clearly visible with defining characteristics, wide establishing shot, "
                f"no text, no random characters, no watermarks, no logos, sharp focus throughout. "
                f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
            )
            image_prompts.append(visual)

    # Ensure minimum of 4 images (Z-Image Turbo formatted fallbacks)
    while len(image_prompts) < 4 and sentences:
        idx = len(image_prompts) // 2
        if idx < len(sentences):
            variant = (
                "wide establishing aerial shot"
                if len(image_prompts) % 2 == 0
                else "cinematic medium shot"
            )
            visual = (
                f"{variant} depicting {sentences[idx].strip()[:80]} "
                f"in Pixar 3D animation in Studio Ghibli style with soft earthy watercolor lighting. "
                f"Warm inviting palette, no text, no random characters, no watermarks, sharp focus. "
                f"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"
            )
            image_prompts.append(visual)
        else:
            break

    # Cap at 12 images max
    image_prompts = image_prompts[:12]

    return image_prompts


def parse_topics(response: str) -> list:
    """
    Parse numbered topics from LLM response.

    Args:
        response (str): The LLM response.

    Returns:
        list: List of topic strings.
    """
    topics = []
    for line in response.split("\n"):
        line = line.strip()
        match = re.match(r"^[\d]+[\.\)\-\s]+(.+)$", line)
        if match:
            topic = match.group(1).strip()
            if len(topic) > 20:
                topics.append(topic)
    return topics


def parse_tags(response: str) -> list:
    """
    Parse JSON tags from LLM response.

    Args:
        response (str): The LLM response.

    Returns:
        list: List of tags, fallback to empty.
    """
    try:
        cleaned = str(response).replace("```json", "").replace("```", "").strip()
        tags = json.loads(cleaned)
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []
    return tags


def parse_image_prompts(response: str) -> list:
    """
    Parse numbered prompts from response.

    Args:
        response (str): The LLM response.

    Returns:
        list: List of prompts.
    """
    image_prompts = []
    lines = response.split("\n")
    for line in lines:
        line = line.strip()
        match = re.match(r"^[\d]+[\.\)\-\s]+(.+)$", line)
        if match:
            scene = match.group(1).strip().strip('"').strip("'")
            if len(scene) > 10:
                image_prompts.append(scene)
    return image_prompts
