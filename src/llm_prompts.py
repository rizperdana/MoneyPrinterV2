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

SCRIPT = """You are generating a YouTube Shorts script with a clear, 4-step structure.

AUDIENCE: General audience (ages 12+)

4-STEP STRUCTURE:

STEP 1 - SETUP (1 sentence):
Hook with ONE surprising fact about the topic. Grab attention. Stay on ONE point.

STEP 2 - DISCOVERY (2-3 sentences):
What happened / What is it / The facts. Be specific. No jumping between topics.

STEP 3 - EXPLANATION (2-3 sentences):
WHY this matters / WHY it works. Use simple analogy like "like [something everyone knows]". Skip jargon or explain in 3 words max.

STEP 4 - TAKEAWAY (1-2 sentences):
MUST answer "so what?" or "why should I care?" Use "That's why..." or "...and here's what this means". Viewer leaves SMARTER.

RULES:
1. ONE topic only — if you catch yourself saying "but also..." STOP
2. NEW info every sentence — no filler, no repeat
3. Simple words — explain or replace any jargon
4. MUST end with TAKEAWAY that answers "so what?"
5. Always reinforce the subject throughout the script

OUTPUT FORMAT: Plain text wrapped in <speak> tags. No SSML prosody tags. No labels, no commentary.

Subject: {subject}
Language: {language}

Return ONLY the script wrapped in <speak> tags. No labels, no commentary."""

SCRIPT_COMPLETE = """Complete this story by adding the resolution.
The story starts well but ends incompletely. Your task:
1. Read the existing script
2. Add 1-3 sentences that resolve the story arc
3. End with a clear resolution, answer, or payoff

EXISTING SCRIPT:
{original_script}

OUTPUT: Add ONLY the completion sentences (no labels, no "here's the ending")."""

# ---------------------------------------------------------------------------
# Title generation prompts (from llm_generate.py)
# ---------------------------------------------------------------------------

TITLE_RETRY = "Generate a YouTube Shorts title for: {subject}. Rules: MAX 100 characters. MUST be EXACTLY 3-8 words (no more, no less). Front-load the most important keywords. No hashtags. TITLE CLARITY:\n- Title must accurately describe the video content\n- Must be readable and make sense as a sentence\n- Avoid vague phrases like \"fires our solar system fast\"\n- Think: would someone know what the video is about from this title?\nReturn ONLY the title, nothing else."

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

STYLE: Pixar 3D animation in Studio Ghibli style, soft earthy watercolor lighting, warm inviting palette.
Apply this style to every prompt without exception.

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

RULES:
- Subject must be clearly identifiable in every prompt
- If script is about a PERSON, show that specific person with distinguishing traits — NOT a generic human figure
- If script is about an OBJECT, show that object clearly with defining characteristics — NOT a generic item
- If script is about a PLACE, show recognizable features of that place — NOT a generic looking location
- If the topic is ABSTRACT (e.g., "justice", "freedom", "time"), represent it through a concrete visual metaphor
- No text, letters, numbers, signs, logos, or writing of any kind
- No close-ups of hands, fingers, or human extremities (unless hands are the actual subject)
- 90-150 words per prompt (Z-Image Turbo sweet spot)
- Use complete natural sentences, NOT tag lists

TECHNICAL PARAMS (append to each prompt):
"Params: num_inference_steps={num_inference_steps}, acceleration={acceleration}, image_size={image_size}"

OUTPUT FORMAT:
Numbered 1 to {n_scenes}. Each prompt on its own line.
- Target length: 90-150 words per prompt
- Use complete natural sentences (NOT tags/lists)
- NO JSON, NO quotes, NO bullet points
- Scenes must flow as a visual narrative (beginning → middle → end)
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
        "script_complete": SCRIPT_COMPLETE,
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
