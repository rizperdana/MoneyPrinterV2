from llm_provider import generate_text, get_model_for_job
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
    result = generate_text(prompt, model_name=model)
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
        trend_prompt = f"""You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

=== RESEARCH DATA (for inspiration only) ===
{research_context}
=== END RESEARCH DATA ===

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY about "{niche}". Do NOT pick general news, history, or unrelated trending topics. If the research data doesn't contain niche-relevant content, IGNORE it and generate topics from your own knowledge about "{niche}".

Generate 3 specific, engaging video topic ideas that:
1. Are STRICTLY and EXCLUSIVELY about: {niche}
2. Would perform well as YouTube Shorts (curiosity-driven, visual, surprising)
3. Are specific enough to make a 45-60 second video about

Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example (if niche is "cool animal facts"):
1. The mantis shrimp can punch so fast it boils the water around it
2. Tardigrades can survive in the vacuum of outer space
3. Octopuses have three hearts and blue blood"""
    else:
        trend_prompt = f"""You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY and EXCLUSIVELY about "{niche}". Do NOT drift into general knowledge, history, or unrelated subjects.

Consider:
1. What surprising or little-known facts exist about {niche}?
2. What recent discoveries or viral moments relate to {niche}?
3. What would make someone stop scrolling and watch about {niche}?

Generate 3 specific, engaging video topic ideas that would perform well as YouTube Shorts.
Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example (if niche is "cool animal facts"):
1. The mantis shrimp can punch so fast it boils the water around it
2. Tardigrades can survive in the vacuum of outer space
3. Octopuses have three hearts and blue blood"""

    return generate_response(trend_prompt, job="topic")


def generate_script_response(subject: str, language: str, sentence_length: int) -> str:
    """
    Generate script for subject.

    Args:
        subject (str): The subject for the script.
        language (str): The language for the script.
        sentence_length (int): The number of sentences in the script.

    Returns:
        str: Raw script text.
    """
    prompt = f"""Write a YouTube Shorts script about: {subject}

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
- Write in {language}
- Each sentence punchy (under 15 words)
- SPECIFIC over VAGUE: say "300 million years ago" not "a long time ago", say "as fast as a bullet" not "very fast"

Subject: {subject}
Language: {language}

Return ONLY the raw script text. No labels, no numbering."""

    completion = generate_response(prompt, job="script")
    completion = re.sub(r"\*", "", completion)
    return completion


def generate_title_response(subject: str) -> str:
    """
    Generate YouTube title for subject.

    Args:
        subject (str): The subject for the title.

    Returns:
        str: The title.
    """
    prompt = f"Generate a YouTube Shorts title for: {subject}. Rules: Under 50 characters. Front-load the most important keywords. No hashtags in the title. Return ONLY the title, nothing else."
    title = generate_response(prompt, job="title_desc")
    return title


def generate_description_response(script: str) -> str:
    """
    Generate description from script.

    Args:
        script (str): The script text.

    Returns:
        str: The description with hashtags.
    """
    prompt = f"Generate a YouTube Shorts description for the following script: {script}. Rules: Include 3-5 relevant hashtags. Add a brief, keyword-rich summary of the video content to index properly in YouTube Search. Return ONLY the description, nothing else."
    return generate_response(prompt, job="title_desc")


def generate_tags_response(subject: str) -> list:
    """
    Generate SEO tags as JSON list.

    Args:
        subject (str): The subject for tags.

    Returns:
        list: List of tags.
    """
    tags_raw = generate_response(
        f'Generate a JSON array of 10-15 YouTube SEO tags (single words or short phrases) for a video about: {subject}. Return ONLY a JSON array of strings, e.g. ["tag1", "tag2"]. No other text.',
        job="seo_tags",
    )
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

    prompt = f"""You are a visual director creating a storyboard for a YouTube Short.

Subject: {subject}
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

    # Fallback: generate from script sentences directly (1 per scene)
    if not image_prompts:
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
            visual = f"{variant} of {sentences[idx].strip()[:60]}, cinematic, detailed"
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
