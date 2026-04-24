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
    prompt = f"""You are generating a YouTube Shorts script with dynamic voice delivery prosody.

AUDIENCE: Elementary school children (ages 6-10)

CRITICAL RULES:
1. Use ONLY simple words. If a word has more than 2 syllables, find a simpler word.
2. Every sentence should paint a picture they can see in their head.
3. Use everyday comparisons they know: "like a playground swing", "like stacking blocks", "like your pet dog"
4. NO big words. "Fast" not "rapid", "big" not "enormous", "begin" not "commence"
5. Ask questions they can answer: "Have you ever wondered...?", "Did you know...?"

OUTPUT FORMAT: SSML (Speech Synthesis Markup Language).
Wrap entire script in <speak version='1.0' xml:lang='{locale}'>...</speak> tags.
Do NOT output plain text. Output valid SSML only.

SSML TAGS AVAILABLE:
- <prosody rate="X%" pitch="±Yst" volume="±ZdB">text</prosody>
  rate: percentage or keyword (fast=150%, medium=100%, slow=75%, very-slow=60%)
  pitch: semitones (e.g., +5st higher, -3st lower) or keyword (high, low)
  volume: +dB/-dB or keyword (loud, soft, medium)
- <break time="300ms"/> or <break time="1s"/> — strategic pause
- <emphasis level="strong"> or level="moderate">word</emphasis> — stress
- <say-as interpret-as="whispered">text</say-as> — whisper effect

PROSODY DECISION RULES — decide per script based on topic emotional tone:
- MYSTERY/SUSPENSE: slower base rate (75-85%), lower pitch, deliberate pacing, pauses before reveals
  Example: <prosody rate="80%" pitch="-3st">But what they found in the dark was...</prosody>
- NEWS/URGENT: faster rate (120-150%), higher pitch, clipped sentences
  Example: <prosody rate="fast" pitch="+5st">Breaking news! NASA just announced...</prosody>
- MOTIVATIONAL: building energy — slower opening, faster middle, slower emphatic finish
  Example: <prosody rate="85%">You have the power...</prosody><break time="600ms"/><prosody rate="fast">to make it happen!</prosody>
- SCIENCE/EXPLAINER: medium rate (100%), authoritative pitch, clear diction, occasional emphasis
  Example: <prosody rate="medium" pitch="+2st">The answer lies in...</prosody>
- HUMOR/WITTY: faster rate with pitch variation, natural breaks at punchline timing
  Example: <prosody rate="fast" pitch="+3st">So I tried that trick and... [pause] it worked!</prosody>
- QUESTIONS: raised pitch on question word, pause before answer
Example: Did you know <prosody pitch="+5st">sharks</prosody> could detect your heartbeat?

INDONESIAN-SPECIFIC GUIDANCE (for id-ID voices like ArdiNeural, GadisNeural):
- Indonesian is a stress-timed language with consistent syllable timing
- Use rate="85-95%" (Indonesian doesn't have English-style stress emphasis — slower than English default)
- Use pitch adjustments sparingly — Indonesian uses only negative pitch: -1st to -2st maximum
- Prefer <break time="200-400ms"> over prosody rate changes for pacing
- Use <emphasis level="moderate"> instead of "strong" — heavy emphasis sounds unnatural in Indonesian
- Keep sentences shorter (6-10 words) — Indonesian syntax is head-final
    - ALWAYS wrap SSML with xml:lang attribute using the locale value: <speak version="1.0" xml:lang="{locale}">

MALAY-SPECIFIC GUIDANCE (for ms-MY voices):
- Similar phonology to Indonesian — apply similar rules
- Rate: 85-95%, pitch: -1st to -2st maximum

STRUCTURE:
1. HOOK (first sentence): Grab attention with surprising fact + appropriate prosody
2. BODY (sentences 2 to n-1): Facts, story, explanation — match prosody to topic tone
3. FINISH (last sentence): Most impactful line — deliberate pacing, strategic pause before if ending a story

CONSTRAINTS:
- Total: {sentence_length} sentences
- Each sentence: 8-12 words maximum (keep it SHORT for kids)
- Total: 60-100 words
- Each sentence wrapped in <prosody>...</prosody> or natural SSML
- NO "welcome", NO "in this video", NO "subscribe"
- NO markdown, NO numbering, NO bullet points
        - Write in {locale}
- Make it SOUND LIKE A PERSON TALKING, not a textbook
- Add simple sound effects as <break> tags or whispered segments

Subject: {subject}
Locale: {locale}

Return ONLY the SSML script wrapped in <speak> tags. No labels, no commentary."""

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
    prompt = f"Generate a YouTube Shorts title for: {subject}. Rules: Under 50 characters. MUST be 3-8 words. Front-load the most important keywords. No hashtags in the title. Return ONLY the title, nothing else."
    title = generate_response(prompt, job="title_desc")

    # Validate word count (3-8 words per FIX_STORYTELLING.md)
    word_count = len(title.split())
    if word_count < 3 or word_count > 8:
        # Retry once with explicit instruction
        retry_prompt = f"Generate a YouTube Shorts title for: {subject}. Rules: Under 50 characters. MUST be EXACTLY 3-8 words (no more, no less). Front-load the most important keywords. No hashtags. Return ONLY the title, nothing else."
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

    # Z-Image Turbo optimized prompt template
    # Structure: subject+action, environment, lighting, composition, style, quality, inline constraints
    # Target: 80-250 words per prompt (supports full detail richness)
    prompt = f"""You are a visual director crafting ultra-detailed scene prompts for Z-Image Turbo (pollinations.ai zimage model).

Subject: {subject}
Script sentences (in order):
{chr(10).join(str(i + 1) + ". " + s for i, s in enumerate(sentences[:n_scenes]))}

For EACH sentence above, write ONE comprehensive visual scene prompt optimized for Z-Image Turbo.

PROMPT STRUCTURE (follow for every scene):
1. MAIN SUBJECT + ACTION: Detailed description of the primary subject including specific attributes (age if human/creature, materials, pose, clothing, expression).
2. ENVIRONMENT/SETTING: Precise location, time of day, weather conditions, atmosphere.
3. LIGHTING/MOOD: Specific light quality (golden hour, overcast soft, dramatic rim light, cinematic shadows), emotional tone (serene, mysterious, energetic).
4. COMPOSITION/FRAMING: Shot type (wide establishing, medium, close-up), camera angle, rule of thirds placement.
5. STYLE/TECHNICAL: "shot on RED/ARRI/cinematic", "photorealistic", "8K ultra-detailed", lens style (85mm portrait, wide-angle landscape).
6. QUALITY BOOSTERS: "sharp focus throughout", "crisp textures", "no artifacts", "no blur/distortion", "professional color grading".
7. INLINE CONSTRAINTS: Embed "no text/gibberish/watermarks", "clean composition", "no blurry elements" directly in prompt.

TECHNICAL PARAMS (append to each prompt):
"Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9"

OUTPUT FORMAT: Numbered 1 to {n_scenes}. Each prompt on its own line.
- Target length: 80-250 words per prompt
- Use complete natural sentences (NOT tags/lists)
- NO JSON, NO quotes, NO bullet points
- Scenes must flow as a visual narrative (beginning → middle → end)
- Cinematic style consistent across ALL scenes

Example output:
1. A weathered prospector in a torn flannel shirt and dusty denim crouches beside a rushing mountain stream, panning for gold with calloused hands and a look of desperate hope etched on his weathered face. The scene unfolds in a secluded Sierra Nevada canyon during late autumn golden hour, the air crisp with pine and possibility. Soft directional sunlight streams through towering Douglas firs casting long dramatic shadows across the riverbed while volumetric fog clings to the distant ridgeline. Shot in anamorphic wide-angle cinematic style with the subject placed using rule of thirds, evoking a sense of rugged solitude and perseverance. Ultra-sharp 8K resolution with crisp fabric textures and meticulous detail on weathered skin. Professional color grading with warm amber highlights and cool shadow tones. No text, no gibberish, no watermarks, no artifacts. Params: num_inference_steps=12, acceleration=high, image_size=landscape_16_9
2. An extreme aerial drone shot soaring over the canyon rim at sunrise, revealing the vast scale of the Sierra Nevada wilderness bathed in pink and orange alpenglow..."""

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
                f"in a wide establishing shot with dramatic lighting and atmospheric depth. "
                f"Photorealistic 8K quality with sharp focus, crisp textures, and professional color grading. "
                f"No text, no gibberish, no watermarks, clean composition. "
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
                f"with dramatic lighting and cinematic atmosphere. "
                f"8K photorealistic with sharp focus, no artifacts. "
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
