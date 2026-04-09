# MoneyPrinter V2

An AI-powered automated video creation and social media publishing system.

> **Note:** MoneyPrinterV2 requires Python 3.12 to function effectively.
> Watch the YouTube video [here](https://youtu.be/wAZ_ZSuIqfk)

---

## Features

### Video Generation
- [x] **AI-Powered Shorts Generation** - Automatically creates vertical videos with:
  - Topic research from Wikipedia, Google Trends, and DuckDuckGo
  - AI-generated scripts with high-retention video structure
  - Dynamic images using Ghibli-style AI generation (Cloudflare, Pollinations)
  - Ken Burns pan/zoom effect on images
  - **Mascot overlay** - Cute orange cat in bottom-left corner of every frame
  - AI text-to-speech (KittenTTS)
  - Auto-generated subtitles using Whisper
  - Background music

### Platform Support
- [x] **YouTube Shorts** - Full automation with CRON scheduling
- [x] **TikTok** - Automated uploads with proper caption formatting
- [x] **Facebook Reels** - Automated uploads with description support
- [x] **Cross-posting** - Via Post Bridge API to multiple platforms simultaneously

### Additional Features
- [x] **Twitter Bot** - Auto-post tweets with CRON scheduling
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
    "llm_model": "kilo-auto/free",
    "CLIPROXY_API_KEY": "your-api-key",
    "firefox_profile": "/path/to/firefox/profile",
    "stt_provider": "local_whisper",
    "whisper_model": "base"
}
```

**Required Environment Variables:**
- `CLIPROXY_API_KEY` - For LLM text generation (uses kilo-auto/free model)

**Optional API Keys:**
- `GEMINI_API_KEY` - For AI image generation
- `PIXABAY_API_KEY` - For stock image fallback
- `POLLINATIONS_API_KEY` - For AI image generation

### Running

```bash
# Interactive mode
python src/main.py

# Non-interactive pipeline (automated)
python src/run_pipeline.py --niche "interesting science facts" --language English --upload

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
│   ├── scheduler.py        # CRON-based scheduling
│   ├── cron.py             # CRON job implementation
│   ├── config.py           # Configuration management
│   ├── llm_provider.py     # LLM API integration (cliproxyapi)
│   ├── tracker.py          # Upload tracking and deduplication
│   ├── cache.py            # Account and data caching
│   ├── utils.py            # Utility functions
│   ├── constants.py        # Constants and selectors
│   ├── status.py           # Status output utilities
│   ├── classes/
│   │   ├── YouTube.py      # YouTube Shorts automation
│   │   ├── Twitter.py      # Twitter bot
│   │   ├── Tts.py          # Text-to-speech
│   │   ├── AFM.py          # Affiliate marketing
│   │   └── Outreach.py     # Business outreach
│   └── ...
├── .mp/                    # Generated media cache
├── output/                 # Output videos
├── docs/                   # Documentation
└── scripts/                # Helper scripts
```

---

## How It Works

### Video Generation Pipeline

1. **Topic Research** - Gathers trending topics from Wikipedia, Google Trends, and web searches based on your niche
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
6. **Text-to-Speech** - Converts script to audio using KittenTTS
7. **Subtitle Generation** - Creates SRT subtitles using Whisper
8. **Video Assembly** - Combines everything using MoviePy

### Platform Upload

- **YouTube** - Selenium-based upload to YouTube Studio
- **TikTok** - Direct upload via TikTok Studio with proper caption/hashtag formatting
- **Facebook** - Reels upload with description
- **Cross-post** - Post Bridge API for simultaneous multi-platform posting

---

## LLM Configuration

MoneyPrinterV2 uses **cliproxyapi** as the primary LLM provider with automatic fallback:

### Primary: cliproxyapi
```bash
# API endpoint
http://localhost:8317/v1

# Default model: kilo-auto/free
```

### Fallback: llama.cpp
If cliproxyapi is unavailable, automatically falls back to local llama.cpp with gemma4 model.

---

## Troubleshooting

### Video generation fails
- Check API keys are set in config.json
- Ensure cliproxyapi service is running
- Try running with `--verbose` flag for detailed logs

### Upload fails
- Verify Firefox profile is logged into the platform
- Check for daily upload limits
- Ensure selectors in constants.py match current platform UI

### No subtitles
- Install faster-whisper: `pip install faster-whisper`
- Or set `stt_provider: "third_party_assemblyai"` with AssemblyAI key

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
- [gpt4free](https://github.com/xtekky/gpt4free) - Free AI API
- [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) - Free AI image generation
