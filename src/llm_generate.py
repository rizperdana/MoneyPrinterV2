from src.llm_provider import generate_text, get_model_for_job
from src.llm_prompts import get_prompt
import re, json


# ---------------------------------------------------------------------------
# Complexity Scoring (Reviewer Gap #1)
# ---------------------------------------------------------------------------

COMPLEXITY_WEIGHTS = {
    "entities": 0.25,
    "temporal": 0.20,
    "causal": 0.20,
    "abstract": 0.20,
    "technical": 0.15,
}

COMPLEXITY_TIERS = {
    "SIMPLE": (0, 0.35),
    "MODERATE": (0.35, 0.60),
    "COMPLEX": (0.60, 1.0),
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


def _count_pattern(text: str, pattern: str) -> int:
    """Count regex pattern matches in text."""
    import re
    return len(re.findall(pattern, text, re.IGNORECASE))


def analyze_complexity(subject: str) -> str:
    """
    Analyze subject complexity and return tier.
    
    Args:
        subject (str): The topic/subject to analyze.
        
    Returns:
        str: "SIMPLE", "MODERATE", or "COMPLEX"
    """
    if not subject or not subject.strip():
        return "SIMPLE"
    
    text = subject.strip()
    if len(text.split()) == 1:
        return "MODERATE"
    
    indicators = {
        "entities": _count_pattern(text, r'\b(\w+\s+){0,2}\w+(?:\s+\w+){0,2}(?:\s+and\s+|\s*,\s*)') / max(len(text.split()), 1),
        "temporal": _count_pattern(text, r'\b(now|then|past|future|century|year|day|age|ancient|modern|before|after|history|era|decade|1950|1960|1970|1980|1990|2000|1800|1900|1700|1600|1500)\b') / max(len(text.split()), 1),
        "causal": _count_pattern(text, r'\bbecause|therefore|so|thus|hence|reason|result|effect|impact|changed|led to|due to|caused|made|created|built|invented|discovered|proved\b') / max(len(text.split()), 1),
        "abstract": _count_pattern(text, r'\btheory|concept|belief|feeling|justice|meaning|truth|wisdom|love|hate|fear|hope|dream|idea|philosophy|spirit|soul|energy|force|mind|thought|emotion|principle|law|nature|reality|existence|purpose|destiny|karma|enlightenment\b') / max(len(text.split()), 1),
        "technical": _count_pattern(text, r'\balgorithm|system|process|method|formula|protocol|engine|formula|mechanism|function|structure|architecture|platform|network|database|API|quantum|relativity|physics|chemistry|biology|medicine|engineering|technology|software|hardware|circuit|neuron|synapse|gene|protein|cell|molecule|atom|scale|dimension|time|space|gravity|force|energy|mass|velocity|acceleration|thermal|electromagnetic|suclear\b') / max(len(text.split()), 1),
    }
    
    score = sum(indicators[key] * COMPLEXITY_WEIGHTS[key] for key in COMPLEXITY_WEIGHTS)
    score = min(max(score, 0), 1.0)
    
    for tier, (low, high) in COMPLEXITY_TIERS.items():
        if low <= score < high:
            return tier
    
    return "COMPLEX"


def get_duration_for_tier(tier: str) -> dict:
    """Get duration range for complexity tier."""
    return DURATION_RANGES.get(tier, DURATION_RANGES["MODERATE"])


def get_scenes_for_tier(tier: str, duration_seconds: int) -> int:
    """Calculate optimal scene count for tier and duration."""
    min_sec, max_sec = SCENE_SECONDS_PER_TIER.get(tier, (20, 25))
    return max(1, min(duration_seconds // min_sec, 16))


def validate_duration(duration_seconds: int, tier: str = "MODERATE") -> dict:
    """
    Validate duration against tier-appropriate range.
    
    Args:
        duration_seconds (int): Estimated duration in seconds.
        tier (str): Complexity tier (SIMPLE|MODERATE|COMPLEX).
        
    Returns:
        dict: {"valid": bool, "in_range": bool, "sweet": bool, "message": str}
    """
    tier_range = DURATION_RANGES.get(tier, DURATION_RANGES["MODERATE"])
    sweet_min, sweet_max = tier_range["sweet"]
    range_min, range_max = tier_range["range"]
    
    in_sweet = sweet_min <= duration_seconds <= sweet_max
    in_range = range_min <= duration_seconds <= range_max
    
    if in_sweet:
        return {"valid": True, "in_range": True, "sweet": True, "message": "Duration in sweet spot"}
    elif in_range:
        return {"valid": True, "in_range": True, "sweet": False, "message": "Acceptable range"}
    else:
        return {"valid": False, "in_range": False, "sweet": False, 
                "message": f"Duration {duration_seconds}s outside {tier} range ({range_min}-{range_max}s)"}


# ---------------------------------------------------------------------------
# Story Completion Validation
# ---------------------------------------------------------------------------

# Resolution phrase patterns
RESOLUTION_PATTERNS = [
    r"\bthat's why\b",
    r"\bin conclusion\b",
    r"\bthe answer is\b",
    r"\bso remember\b",
    r"\bthat's how\b",
    r"\bfinally\b",
    r"\bin the end\b",
    r"\bnow you know\b",
    r"\bas you can see\b",
    r"\bto summarize\b",
]

# Arc stage markers
ARC_MARKERS = {
    "STASIS": [r"^originally\b", r"^traditionally\b", r"^for centuries\b", r"^long ago\b", r"^once\b"],
    "DISRUPTION": [r"\bbut then\b", r"\bhowever\b", r"\beverything changed\b", r"\bsuddenly\b", r"\b挑战\b"],
    "ATTEMPT": [r"\bthey tried\b", r"\bpeople tried\b", r"\bscientists tried\b", r"\bresearchers tried\b", r"\bhowever\b"],
    "RESOLUTION": [r"\bsuccess\b", r"\bfinally\b", r"\bin the end\b", r"\btoday\b", r"\bnow\b"],
}


def validate_completion(script: str) -> dict:
    """
    Validate script has story completion.
    
    Args:
        script (str): Generated script text.
        
    Returns:
        dict: {"complete": bool, "has_resolution": bool, "arc_stages": list, "retry": bool, "message": str}
    """
    if not script or not script.strip():
        return {"complete": False, "has_resolution": False, "arc_stages": [], "retry": True, 
                "message": "Empty script"}
    
    text = script.strip()
    
    # Check resolution phrases
    has_resolution = any(re.search(p, text, re.IGNORECASE) for p in RESOLUTION_PATTERNS)
    
    # Check arc stages
    found_stages = []
    for stage, patterns in ARC_MARKERS.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            found_stages.append(stage)
    
    # Require STASIS->DISRUPTION->RESOLUTION or attempt->resolution
    arc_complete = "DISRUPTION" in found_stages or "RESOLUTION" in found_stages
    
    if has_resolution and arc_complete:
        return {"complete": True, "has_resolution": True, "arc_stages": found_stages, 
                "retry": False, "message": "Complete"}
    elif has_resolution:
        return {"complete": True, "has_resolution": True, "arc_stages": found_stages, 
                "retry": False, "message": "Complete (resolution only)"}
    else:
        return {"complete": False, "has_resolution": False, "arc_stages": found_stages, 
                "retry": True, "message": "Incomplete - missing resolution"}


def check_and_complete_script(script: str) -> tuple[str, bool]:
    """
    Check script completion and return (script, needs_retry).
    
    Args:
        script (str): Script to check.
        
    Returns:
        tuple: (checked_script, needs_retry_flag)
    """
    result = validate_completion(script)
    if result["retry"]:
        return script, True
    return script, False


def estimate_duration_from_word_count(word_count: int, wpm: int = 150) -> int:
    """Estimate TTS duration from word count."""
    return int((word_count / wpm) * 60)


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


def generate_topic_response(niche: str, research_context: str = None) -> str:
    """
    Generate topic ideas about niche, optionally using research context.

    Args:
        niche (str): The niche for topic generation.
        research_context (str, optional): Additional research context.

    Returns:
        str: Raw LLM response with topics.
    """
    if research_context:
        prompt = get_prompt("topic_with_research", niche=niche, research_context=research_context)
    else:
        prompt = get_prompt("topic_no_research", niche=niche)

    return generate_response(prompt, job="topic")


def generate_script_response(subject: str, locale: str, sentence_length: int) -> str:
    """
    Generate script for subject.

    Args:
        subject (str): The subject for the script.
        locale (str): BCP-47 locale code (e.g., en-US, id-ID).
        sentence_length (int): The number of sentences in the script.

    Returns:
        str: Raw script text.
    """
    prompt = get_prompt(
        "script",
        subject=subject,
        language=locale,
        locale=locale,
        sentence_length=sentence_length
    )

    completion = generate_response(prompt, job="script")
    completion = re.sub(r"\*", "", completion)
    return completion


def generate_title_response(subject: str) -> str:
    """
    Generate YouTube title for subject.

    Args:
        subject (str): The subject for the title.

    Returns:
        str: The title (validated 3-8 words).
    """
    prompt = get_prompt("title_retry", subject=subject)
    title = generate_response(prompt, job="title_desc")

    # Validate word count (3-8 words per FIX_STORYTELLING.md)
    word_count = len(title.split())
    if word_count < 3 or word_count > 8:
        # Retry once with explicit instruction
        title = generate_response(get_prompt("title_retry", subject=subject), job="title_desc")
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

    return title


def generate_description_response(script: str) -> str:
    """
    Generate description from script.

    Args:
        script (str): The script text.

    Returns:
        str: The description with hashtags.
    """
    prompt = get_prompt("description", script=script)
    return generate_response(prompt, job="title_desc")


def generate_tags_response(subject: str) -> list:
    """
    Generate SEO tags as JSON list.

    Args:
        subject (str): The subject for tags.

    Returns:
        list: List of tags.
    """
    prompt = get_prompt("seo_tags", subject=subject)
    tags_raw = generate_response(prompt, job="seo_tags")
    try:
        cleaned = str(tags_raw).replace("```json", "").replace("```", "").strip()
        tags = json.loads(cleaned)
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []
    return tags


def generate_image_prompts_response(subject: str, script: str, tier: str = "MODERATE") -> list:
    """
    Generate image prompts from script.

    Args:
        subject (str): The subject.
        script (str): The script text.
        tier (str): Quality tier - SIMPLE, MODERATE, or COMPLEX.

    Returns:
        list: List of image prompts.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", script) if len(s.strip()) > 10]

    # Dynamic scene count per tier (Reviewer Gap #3)
    # Simple: 4-6 scenes, Moderate: 6-8 scenes, Complex: 8-12 scenes
    tier_scene_ranges = {
        "SIMPLE": (4, 6),
        "MODERATE": (6, 8),
        "COMPLEX": (8, 12),
    }
    min_scenes, max_scenes = tier_scene_ranges.get(tier, (6, 8))
    n_scenes = min(max(len(sentences), min_scenes), max_scenes)

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
