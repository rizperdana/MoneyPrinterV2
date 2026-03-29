#!/usr/bin/env python3
"""Fresh pipeline runner - standalone, no imports from run_pipeline.py"""
import os
import sys
import json
import time

os.environ["TMPDIR"] = "/home/anon/.nanobot/workspace/tmp"

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from config import get_ollama_model, ROOT_DIR
from llm_provider import select_model
from classes.YouTube import YouTube
from classes.Tts import TTS

def main():
    niche = sys.argv[1] if len(sys.argv) > 1 else "things that existed before the internet"
    
    model = get_ollama_model()
    select_model(model)
    print(f"Model: {model}", flush=True)
    
    yt = YouTube.__new__(YouTube)
    yt._account_uuid = "auto-pipeline"
    yt._account_nickname = "Auto Pipeline"
    yt._niche = niche
    yt._language = "English"
    yt.images = []
    yt.subject = None
    yt.script = None
    yt.metadata = None
    yt.image_prompts = None
    yt.tts_path = None
    yt.video_path = None
    
    print("Step 1: Topic", flush=True)
    topic = yt.generate_topic()
    print(f"  Topic: {topic[:80]}", flush=True)
    
    print("Step 2: Script", flush=True)
    script = yt.generate_script()
    print(f"  Script: {len(script)} chars", flush=True)
    
    print("Step 3: Metadata", flush=True)
    meta = yt.generate_metadata()
    print(f"  Title: {meta['title'][:60]}", flush=True)
    
    print("Step 4: Prompts", flush=True)
    prompts = yt.generate_prompts()
    print(f"  Prompts: {len(prompts)}", flush=True)
    
    print("Step 5: Images", flush=True)
    for i, p in enumerate(prompts):
        img = yt.generate_image(p, delay_between=2)
        print(f"  Image {i+1}: {'OK' if img else 'FAIL'}", flush=True)
    
    print("Step 6: TTS", flush=True)
    tts = TTS()
    yt.generate_script_to_speech(tts)
    print(f"  TTS: {yt.tts_path}", flush=True)
    
    print("Step 7: Combine", flush=True)
    path = yt.combine()
    print(f"  Video: {path}", flush=True)
    
    result = {
        "topic": topic,
        "title": meta["title"],
        "tags": meta.get("tags", []),
        "video_path": path,
        "uploaded": False
    }
    with open(os.path.join(ROOT_DIR, ".mp", "last_run.json"), "w") as f:
        json.dump(result, f, indent=2)
    
    print("DONE!", flush=True)

if __name__ == "__main__":
    main()
