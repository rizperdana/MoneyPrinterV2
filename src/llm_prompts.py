"""
Centralized LLM prompt definitions for MoneyPrinterV2.

All prompt strings are defined as constants here. Use `get_prompt()` to retrieve
and format prompts with dynamic values.
"""

# ---------------------------------------------------------------------------
# Topic generation prompts (from llm_generate.py)
# ---------------------------------------------------------------------------

TOPIC_WITH_RESEARCH = """You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

=== RESEARCH DATA (for inspiration only) ===
{research_context}
=== END RESEARCH DATA ===

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY about "{niche}". Do NOT pick general news, history, or unrelated trending topics. If the research data doesn't contain niche-relevant content, IGNORE it and generate topics from your own knowledge about "{niche}".

FACTUAL CLARITY REQUIRED:
- Every topic must explain HOW or WHY something works, not just that it exists
- Frame technology as educational, not scary or mysterious
- Avoid: trick, hack, fry, exploit, secret, track through walls, secretly
- Prefer: how things work, why they happen, real science behind it
- A good topic: "How face recognition works and how it's tested" not "Your phone can be fooled by a mask"

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

TOPIC_NO_RESEARCH = """You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

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

# ---------------------------------------------------------------------------
# Script generation prompt (from llm_generate.py)
# ---------------------------------------------------------------------------

SCRIPT = """You are generating a YouTube Shorts script with dynamic voice delivery prosody.

AUDIENCE: Elementary school children (ages 6-10)

CRITICAL RULES:
1. Use ONLY simple words. If a word has more than 2 syllables, find a simpler word.
2. Every sentence should paint a picture they can see in their head.
3. Use everyday comparisons they know: "like a playground swing", "like stacking blocks", "like your pet dog"
4. NO big words. "Fast" not "rapid", "big" not "enormous", "begin" not "commence"
5. Ask questions they can answer: "Have you ever wondered...?", "Did you know...?"

OUTPUT FORMAT: SSML (Speech Synthesis Markup Language).
Wrap entire script in <speak>...</speak> tags.
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

STRUCTURE:
1. HOOK (first sentence): Grab attention with surprising fact + appropriate prosody
2. BODY (sentences 2 to n-1): Facts, story, explanation — match prosody to topic tone
3. FINISH (last sentence): Most impactful line — deliberate pacing, strategic pause before if ending a story

CONSTRAINTS:
- Write naturally in {language}
- End when story is COMPLETE, not when sentence limit hit
- Minimum 4 sentences (story arc needs stasis → resolution)
- NO "welcome", NO "in this video", NO "subscribe"
- NO markdown, NO numbering, NO bullet points

EXPLANATION REQUIREMENT:
- By the end of the script, the central question MUST be answered
- Use accurate terminology (nuclear fusion, not "fireball")
- The goal is understanding, not suspense
- Avoid endings that just warn or deflect without explaining
- Script should leave viewer smarter, not just cautious

Subject: {subject}
Language: {language}

Return ONLY the SSML script wrapped in <speak> tags. No labels, no commentary."""

# ---------------------------------------------------------------------------
# Title generation prompts (from llm_generate.py)
# ---------------------------------------------------------------------------

TITLE_RETRY = "Generate a YouTube Shorts title for: {subject}. Rules: Under 50 characters. MUST be EXACTLY 3-8 words (no more, no less). Front-load the most important keywords. No hashtags. TITLE CLARITY:\n- Title must accurately describe the video content\n- Must be readable and make sense as a sentence\n- Avoid vague phrases like \"fires our solar system fast\"\n- Think: would someone know what the video is about from this title?\nReturn ONLY the title, nothing else."

# ---------------------------------------------------------------------------
# Description and hashtag prompts (from llm_generate.py)
# ---------------------------------------------------------------------------

DESCRIPTION = "Generate a YouTube Shorts description for the following script: {script}. Rules: Include 3-5 relevant hashtags. Add a brief, keyword-rich summary of the video content to index properly in YouTube Search. Return ONLY the description, nothing else."

DESCRIPTION_HASHTAG_COUNT = 3  # 3-5 hashtags

# ---------------------------------------------------------------------------
# SEO tags prompt (from llm_generate.py)
# ---------------------------------------------------------------------------

SEO_TAGS = 'Generate a JSON array of 10-15 YouTube SEO tags (single words or short phrases) for a video about: {subject}. Return ONLY a JSON array of strings, e.g. ["tag1", "tag2"]. No other text.'

# ---------------------------------------------------------------------------
# Image prompt template (from llm_generate.py)
# ---------------------------------------------------------------------------

IMAGE_PROMPT = """
You are a text-to-image prompt engineer writing for Z-Image Turbo (pollinations.ai zimage model).

STYLE (MANDATORY — use this exact style for every prompt, do not omit or modify):
Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette.

TASK:
For each script sentence below, write ONE complete visual scene prompt for Z-Image Turbo.
The prompt must tell the image model EXACTLY what to show — subject, environment, shot type, lighting, and nuance.
Write prompts that work WITHOUT any additional enhancement or post-processing.

SUBJECT FROM VIDEO: {subject}

SCRIPT SENTENCES (write one prompt per sentence, in order):
{sentences}

FOR EACH SENTENCE, CREATE A PROMPT WITH THESE ELEMENTS:
1. SUBJECT — Who or what is the primary focus? Give 2-3 specific defining traits.
   If the script mentions a person (e.g., "Hitler"), describe the figure specifically:
   "a figure in a 1940s German military uniform with Iron Cross medal, not a generic soldier"
   If the script mentions an object (e.g., "the mantis shrimp's claw"), be specific:
   "the raptorial claw of a mantis shrimp, extended and ready to strike"
   If the script mentions a place (e.g., "the Brandenburg Gate"), show recognizable features:
   "the Brandenburg Gate in Berlin with its quadriga statue, sandstone columns"
2. ACTION/STATE — What is the subject doing or how does it appear in this moment?
3. ENVIRONMENT — Where is it? Include only setting details that directly support subject identification.
4. SHOT TYPE — Wide establishing / medium / close-up / aerial? Choose what best shows the subject clearly.
5. LIGHTING — Type and direction: golden hour sunlight, soft overcast, dramatic rim light, etc.
6. NUANCE — Any specific visual details that further clarify the subject (materials, textures, colors)?

RULES (STRICT — every prompt must follow these):
- SUBJECT MUST appear and be clearly identifiable in every prompt
- If script is about a PERSON, show that specific person with distinguishing traits — NOT a generic human figure
- If script is about an OBJECT, show that object clearly with defining characteristics — NOT a generic item
- If script is about a PLACE, show recognizable features of that place — NOT a generic looking location
- DO NOT substitute generic alternatives for the specific subject in the script
- MANDATORY STYLE: Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette
- NO text, no letters, no numbers, no signs, no logos, no writing of any kind
- NO close-ups of hands, fingers, or human extremities (unless hands are the actual subject)
- NO vague adjectives alone: do not use "cinematic", "beautiful", "epic", "magical", "dreamlike" without concrete subject info
- If the topic is ABSTRACT (e.g., "justice", "freedom", "time"), represent it through a concrete visual metaphor before applying style
- 90-150 words per prompt (Z-Image Turbo sweet spot)
- Use complete natural sentences, NOT tag lists
- Mention the primary subject 2-3 times in different forms within the prompt for reinforcement

TECHNICAL PARAMS (append to each prompt):
"Params: num_inference_steps={num_inference_steps}, acceleration={acceleration}, image_size={image_size}"

OUTPUT FORMAT:
Numbered 1 to {n_scenes}. Each prompt on its own line.
- Target length: 90-150 words per prompt
- Use complete natural sentences (NOT tags/lists)
- NO JSON, NO quotes, NO bullet points
- Scenes must flow as a visual narrative (beginning → middle → end)
- Same Ghibli/watercolor style across ALL scenes
"""

# Default image generation parameters (kept in spec)
IMAGE_MAX_PROMPTS = 12  # Cap at 12 images max

# Script constraints (hardcoded in SCRIPT prompt template, no separate constants)

# Topic constraints
TOPIC_MIN_LENGTH = 20  # Minimum topic length to accept

# ---------------------------------------------------------------------------
# YouTube-specific prompts (from classes/YouTube.py)
# ---------------------------------------------------------------------------

YOUTUBE_TOPIC_WITH_RESEARCH = """You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

{facts_context}
=== END EXTRACTED FACTS ===

=== RESEARCH DATA (for inspiration only) ===
{research_context}
=== END RESEARCH DATA ===

{existing_context}
=== END ALREADY-DONE TOPICS ===

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY about "{niche}". Do NOT pick general news, history, or unrelated trending topics. If the research data doesn't contain niche-relevant content, IGNORE it and generate topics from your own knowledge about "{niche}".

FACTUAL CLARITY REQUIRED:
- Every topic must explain HOW or WHY something works, not just that it exists
- Frame technology as educational, not scary or mysterious
- Avoid: trick, hack, fry, exploit, secret, track through walls, secretly
- Prefer: how things work, why they happen, real science behind it
- A good topic: "How face recognition works and how it's tested" not "Your phone can be fooled by a mask"

Generate 3 specific, engaging video topic ideas that:
1. Are STRICTLY and EXCLUSIVELY about: {niche}
2. Would perform well as YouTube Shorts (curiosity-driven, visual, surprising)
3. Are specific enough to make a 45-60 second video about
4. Incorporate at least one specific extracted fact when provided

Each topic should be one sentence, specific, and curiosity-driven.

Output format: Just list 3 topics, one per line, numbered 1-3.
Example (if niche is "cool animal facts"):
1. The mantis shrimp can punch so fast it boils the water around it
2. Tardigrades can survive in the vacuum of outer space
3. Octopuses have three hearts and blue blood"""

YOUTUBE_TOPIC_NO_RESEARCH = """You are a YouTube content strategist. Your ONLY job is to generate topics STRICTLY about: {niche}

⚠️ CRITICAL RULE: Every topic MUST be DIRECTLY and EXCLUSIVELY about "{niche}". Do NOT drift into general knowledge, history, or unrelated subjects.

FACTUAL CLARITY REQUIRED:
- Every topic must explain HOW or WHY something works, not just that it exists
- Frame technology as educational, not scary or mysterious
- Avoid: trick, hack, fry, exploit, secret, track through walls, secretly
- Prefer: how things work, why they happen, real science behind it
- A good topic: "How face recognition works and how it's tested" not "Your phone can be fooled by a mask"

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
3. Octopuses have three hearts and blue blood

{existing_context}
=== END ALREADY-DONE TOPICS ==="""

# ---------------------------------------------------------------------------
# SEO keywords prompt (from classes/YouTube.py)
# ---------------------------------------------------------------------------

SEO_KEYWORDS = """Generate SEO keywords for a video about: {subject}.
Return ONLY a JSON object with these fields:
- "main": one broad topic keyword (e.g., "AI", "cryptocurrency", "productivity")
- "related": one specific aspect keyword (e.g., "ChatGPT tips", "Bitcoin investing", "time management")
- "emotional": one fear/wonder/disbelief keyword (e.g., "AI replace jobs", "crypto scam", "too late to start")
- "tags": array of 10-15 SEO tags mixing main, related, and emotional types
Example: {{"main": "AI", "related": "ChatGPT prompts", "emotional": "AI taking over", "tags": ["AI", "ChatGPT", "AI tools", "artificial intelligence", "ChatGPT prompts", "AI tips", "AI trends", "future of AI", "AI taking over", "job automation", "AI helpers", "productivity"]}}"""

# ---------------------------------------------------------------------------
# Twitter prompt (from classes/Twitter.py)
# ---------------------------------------------------------------------------

TWITTER_POST = "Generate a Twitter post about: {topic} in {language}. The Limit is 2 sentences. Choose a specific sub-topic of the provided topic."

# ---------------------------------------------------------------------------
# Helper function to retrieve and format prompts
# ---------------------------------------------------------------------------

def get_prompt(prompt_name: str, **kwargs) -> str:
    """
    Retrieve a prompt by name, formatting with kwargs if provided.

    Args:
        prompt_name: Name of the prompt (e.g., "topic_with_research", "script")
        **kwargs: Dynamic values to inject into the prompt using .format()

    Returns:
        The formatted prompt string.

    Raises:
        ValueError: If the prompt_name is not found.
    """
    prompt_map = {
        # Topic prompts
        "topic_with_research": TOPIC_WITH_RESEARCH,
        "topic_no_research": TOPIC_NO_RESEARCH,
        # Script prompt
        "script": SCRIPT,
        # Title prompts (only TITLE_RETRY per spec)
        "title_retry": TITLE_RETRY,
        # Description prompt
        "description": DESCRIPTION,
        # SEO tags
        "seo_tags": SEO_TAGS,
        # Image prompt
        "image_prompt": IMAGE_PROMPT,
        # YouTube-specific prompts
        "youtube_topic_with_research": YOUTUBE_TOPIC_WITH_RESEARCH,
        "youtube_topic_no_research": YOUTUBE_TOPIC_NO_RESEARCH,
        # SEO keywords (YouTube)
        "seo_keywords": SEO_KEYWORDS,
        # Twitter post
        "twitter_post": TWITTER_POST,
    }

    prompt = prompt_map.get(prompt_name)
    if prompt is None:
        raise ValueError(f"Unknown prompt: {prompt_name}")

    # Format with kwargs if any provided
    if kwargs:
        return prompt.format(**kwargs)
    return prompt
