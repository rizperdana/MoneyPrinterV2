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
        sentence_length=sentence_length,
        max_words_per_sentence=12,
        max_total_words=100
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


def generate_image_prompts_response(subject: str, script: str) -> list:
    """
    Generate image prompts from script.

    Args:
        subject (str): The subject.
        script (str): The script text.

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
                f"Scene showing {sentence.strip()[:100]} in Pixar 3D animation "
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
