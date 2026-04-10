# MoneyPrinter V2

An AI-powered automated video creation and social media publishing system.

> **Note:** MoneyPrinterV2 requires Python 3.12 to function effectively.
> Watch the YouTube video [here](https://youtu.be/wAZ_ZSuIqfk)

---

## Features

### Video Generation
- [x] **AI-Powered Shorts Generation** - Automatically creates vertical videos with:
  - Topic research from Tavily, Exa, Bing (ddgs), Wikipedia, Google Trends, and Firecrawl
  - AI-generated scripts with high-retention video structure
  - Dynamic images using Cloudflare Workers AI + Pollinations
  - Ken Burns pan/zoom effect on images
  - **Mascot overlay** - Cute orange cat in bottom-left corner of every frame
  - Text-to-speech (KittenTTS + Edge-TTS)
  - Auto-generated subtitles using Whisper
  - Background music

### Platform Support
- [x] **YouTube Shorts** - Full automation with CRON scheduling
- [x] **TikTok** - Automated uploads via Post Bridge API
- [x] **Facebook Reels** - Automated uploads via Post Bridge API
- [x] **Cross-posting** - Via Post Bridge API to multiple platforms simultaneously

### Additional Features
- [x] **Twitter Bot** - Auto-post tweets with CRON scheduling
- [x] **Reddit Bot** - Auto-post to subreddits
- [x] **Affiliate Marketing** - Amazon affiliate link promotion
- [x] **Cold Outreach** - Find local businesses and send promotional emails

---

## Quick Start

### Prerequisites
- Python 3.12
- Firefox browser (for Selenium automation)
- API keys (see Configuration below)

### Installation

```bash
git clone https://github.com/FujiwaraChoki/MoneyPrinterV2.git
cd MoneyPrinterV2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp config.example.json config.json
# Edit config.json with your API keys
```

### Configuration

Edit `config.json` with your API keys:

```json
{
    "CLIPROXY_API_KEY": "your-api-key",
    "firefox_profile": "/path/to/firefox/profile",
    "stt_provider": "local_whisper",
    "whisper_model": "base"
}
```

**Required Environment Variables:**
- `CLIPROXY_API_KEY` - For LLM text generation (uses cliproxyapi with job-specific model routing)

**Optional API Keys:**
- `GEMINI_API_KEY` - For AI image generation
- `PIXABAY_API_KEY` - For stock image fallback
- `POLLINATIONS_API_KEY` - For AI image generation
- `TAVILY_API_KEY` - For topic research
- `EXA_API_KEY` - For topic research

### Running

```bash
# Interactive mode
python src/main.py

# Non-interactive pipeline (automated)
python src/run_pipeline.py --niche "interesting science facts" --language English --upload

# Batch mode
python src/batch_run.py --niche "your niche" --count 5

# 24/7 scheduler mode
python src/scheduler.py start
```

---

## Project Structure

```
MoneyPrinterV2/
├── src/
│   ├── main.py              # Interactive CLI application
│   ├── run_pipeline.py      # Non-interactive video generation pipeline
│   ├── run_24_7.py         # 24/7 continuous operation mode
│   ├── batch_run.py         # Batch video generation
│   ├── scheduler.py         # CRON-based scheduling
│   ├── cron.py              # CRON job implementation
│   ├── config.py            # Configuration management
│   ├── llm_provider.py      # LLM API integration (cliproxyapi) with model routing
│   ├── llm_generate.py      # Prompt construction and response parsing
│   ├── research.py           # Topic research (Tavily, Exa, Bing, Wikipedia, etc.)
│   ├── db.py                # SQLite in-memory ORM (topics, videos, accounts)
│   ├── tracker.py           # Upload tracking and deduplication
│   ├── cache.py             # Account and data caching
│   ├── utils.py             # Utility functions
│   ├── constants.py         # Constants and selectors
│   ├── status.py            # Status output utilities
│   ├── art.py               # ASCII banner
│   └── classes/
│       ├── YouTube.py       # YouTube Shorts automation
│       ├── Twitter.py        # Twitter bot
│       ├── Reddit.py         # Reddit bot
│       ├── PostBridge.py     # Cross-platform posting API
│       ├── Tts.py           # Text-to-speech (KittenTTS)
│       ├── EdgeTts.py       # Edge TTS provider
│       ├── AFM.py           # Affiliate marketing
│       └── Outreach.py      # Business outreach
├── .mp/                     # Generated media cache
├── output/                  # Output videos
├── docs/                    # Documentation
├── assets/                  # Static assets
├── fonts/                   # Font files
└── scripts/                 # Helper scripts
```

---

## How It Works

### Video Generation Pipeline

1. **Topic Research** - Gathers trending topics from multiple sources:
   - Tavily AI (primary)
   - Exa search
   - Bing via ddgs (fallback, works in Indonesia)
   - Wikipedia
   - Google Trends
   - Firecrawl web scraping
2. **Script Generation** - Creates engaging scripts using AI with:
   - Hook statement (first 3 seconds)
   - Core delivery (information density)
   - Climax/payoff
   - Seamless loop
3. **Image Generation** - Creates dynamic visuals using:
   - Cloudflare Workers AI (Leonardo, Flux)
   - Pollinations AI
   - Pixabay stock images (fallback)
4. **Ken Burns Effect** - Adds subtle pan/zoom animation to images
5. **Mascot Overlay** - Places cute orange cat mascot in bottom-left corner
6. **Text-to-Speech** - Converts script to audio using KittenTTS or Edge TTS
7. **Subtitle Generation** - Creates SRT subtitles using Whisper
8. **Video Assembly** - Combines everything using MoviePy

### Platform Upload

- **YouTube** - Selenium-based upload to YouTube Studio
- **TikTok** - Via Post Bridge API
- **Facebook** - Reels upload via Post Bridge API
- **Cross-post** - Post Bridge API for simultaneous multi-platform posting

---

## LLM Configuration

MoneyPrinterV2 uses **cliproxyapi** as the LLM provider with job-specific model routing:

| Job | Primary Model | Fallbacks |
|-----|--------------|-----------|
| topic | arcee-ai/trinity-large-thinking:free | dola-seed-2.0-pro, minimax-m2.5, nemotron |
| script | arcee-ai/trinity-large-thinking:free | dola-seed-2.0-pro, minimax-m2.5, nemotron |
| seo_tags | arcee-ai/trinity-large-thinking:free | dola-seed-2.0-pro, minimax-m2.5 |
| image_prompts | bytedance-seed/dola-seed-2.0-pro:free | trinity-large-thinking, minimax-m2.5 |
| title_desc | arcee-ai/trinity-large-thinking:free | dola-seed-2.0-pro, minimax-m2.5, nemotron |

```bash
# API endpoint
http://localhost:8317/v1
```

---

## Troubleshooting

### Video generation fails
- Check API keys are set in config.json
- Ensure cliproxyapi service is running
- Try running with `--verbose` flag for detailed logs
- Run `python3 scripts/preflight_local.py` to validate all providers

### Upload fails
- Verify Firefox profile is logged into the platform
- Check for daily upload limits
- Ensure selectors in constants.py match current platform UI

### No subtitles
- Install faster-whisper: `pip install faster-whisper`
- Or set `stt_provider: "third_party_assemblyai"` with AssemblyAI key

### Research returns no results
- Check API keys for Tavily/Exa
- Verify internet connectivity
- ddgs uses Bing backend (works in Indonesia where DuckDuckGo is blocked)

---

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/setup_local.sh` | Initial setup and configuration |
| `scripts/preflight_local.py` | Validate provider readiness |
| `scripts/upload_video.sh` | Direct script-based upload |

---

## License

MoneyPrinterV2 is licensed under **Affero General Public License v3.0**.

---

## Acknowledgments

- [KittenTTS](https://github.com/KittenML/KittenTTS) - Text-to-Speech
- [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) - Free AI image generation
- [Pollinations.ai](https://pollinations.ai/) - Free AI image generation
- [Whisper](https://github.com/openai/whisper) - Speech recognition
