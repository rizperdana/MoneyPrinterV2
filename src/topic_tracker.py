"""
Topic Uniqueness Tracker — 3-level dedup pipeline.
Level 1: MinHashLSH (datasketch) — O(1) near-duplicate detection.
Level 2: Entity+Aspect Fingerprint — pure Python, catches same-subject-different-aspect.
Level 3: LLM Judge — existing infrastructure, borderline cases.
"""

from __future__ import annotations
import os
import re
import json
import math
import pickle
import tempfile
import hashlib
from pathlib import Path
from typing import Optional

# Optional: datasketch (Level 1)
try:
    from datasketch import MinHash, MinHashLSH
    DASKETCH_AVAILABLE = True
except ImportError:
    DASKETCH_AVAILABLE = False

ROOT_DIR = Path(__file__).parent.parent
USED_TOPICS_FILE = os.path.join(ROOT_DIR, ".mp", "used_topics.json")
FAMILY_FILE = os.path.join(ROOT_DIR, ".mp", "topic_family.json")
LSH_FILE = os.path.join(ROOT_DIR, ".mp", "topic_lsh.blob")
RESEARCH_STATE_FILE = os.path.join(ROOT_DIR, ".mp", "research_state.json")

# ─── Level 2: Pure Python Fingerprint ─────────────────────────────────────────

ENTITY_PATTERN = re.compile(r'\b[a-z]{3,}(?:\s+[a-z]{3,}){0,1}\b')

ASPECT_WORDS = {
    'speed', 'fast', 'slow', 'strong', 'weak', 'big', 'small', 'tiny', 'huge', 'giant',
    'old', 'new', 'young', 'ancient', 'weird', 'strange', 'weirdest', 'fastest', 'strongest',
    'dangerous', 'poison', 'venom', 'electric', 'glow', 'dark', 'deep', 'secret', 'hidden',
    'live', 'survive', 'die', 'kill', 'attack', 'defend', 'discover', 'science', 'fact',
    'history', 'future', 'past', 'present', 'how', 'why', 'what', 'work', 'happen',
    'eyes', 'vision', 'color', 'size', 'weight', 'habitat', 'diet', 'predator', 'prey',
}

STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def get_fingerprint(topic: str) -> dict:
    """Entity + Aspect + n-gram fingerprint."""
    topic_lower = topic.lower()
    tokens = tokenize(topic_lower)
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    entities = [
        m.group().replace(' ', '_')
        for m in ENTITY_PATTERN.finditer(topic_lower)
        if len(m.group()) >= 3
    ]
    aspects = [t for t in tokens if t in ASPECT_WORDS]
    return {
        "tokens": set(tokens),
        "bigrams": set(bigrams),
        "entities": set(entities),
        "aspects": set(aspects),
    }


def fingerprint_similarity(fp1: dict, fp2: dict) -> float:
    """Weighted cosine similarity. entity_sim weight=0.4."""
    if not fp1["tokens"] or not fp2["tokens"]:
        return 0.0
    common_tokens = len(fp1["tokens"] & fp2["tokens"])
    token_sim = common_tokens / math.sqrt(len(fp1["tokens"]) * len(fp2["tokens"]) + 1)
    common_bigrams = len(fp1["bigrams"] & fp2["bigrams"])
    bigram_sim = common_bigrams / math.sqrt(len(fp1["bigrams"]) * len(fp2["bigrams"]) + 1)
    entity_sim = 0.0
    if fp1["entities"] and fp2["entities"]:
        common_entities = len(fp1["entities"] & fp2["entities"])
        entity_sim = common_entities / math.sqrt(len(fp1["entities"]) * len(fp2["entities"]) + 1)
    return (token_sim * 0.3) + (bigram_sim * 0.3) + (entity_sim * 0.4)


# ─── Level 1: MinHashLSH ───────────────────────────────────────────────────────

def topic_to_minhash(topic: str, num_perm: int = 128) -> MinHash:
    """Create MinHash from topic string."""
    tokens = tokenize(topic)
    m = MinHash(num_perm=num_perm)
    for t in tokens:
        m.update(t.encode('utf8'))
    return m


def save_lsh_atomically(lsh, path: str) -> None:
    """Atomic write: write to temp file, then rename. Prevents corruption on crash."""
    dir = os.path.dirname(path)
    if not dir:
        dir = "."
    fd, tmp = tempfile.mkstemp(dir=dir)
    try:
        with os.fdopen(fd, 'wb') as f:
            pickle.dump(lsh, f)
        os.replace(tmp, path)  # atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_lsh(path: str, fallback_fn) -> Optional[MinHashLSH]:
    """Load LSH from blob. If corrupt or missing, rebuild via fallback_fn."""
    if not os.path.exists(path):
        return fallback_fn()
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except Exception:
        return fallback_fn()


def rebuild_lsh_from_used_topics() -> MinHashLSH:
    """Rebuild LSH index from used_topics.json entries."""
    lsh = MinHashLSH(threshold=0.5, num_perm=128)
    if not os.path.exists(USED_TOPICS_FILE):
        return lsh
    try:
        with open(USED_TOPICS_FILE, 'r') as f:
            data = json.load(f)
        for entry in data.get("topics", []):
            topic = entry.get("topic", "")
            if topic:
                key = f"topic_{hashlib.md5(topic.encode('utf8')).hexdigest()[:8]}"
                lsh.insert(key, topic_to_minhash(topic))
    except Exception:
        pass
    return lsh


# ─── TopicFamilyTracker ───────────────────────────────────────────────────────

class TopicFamilyTracker:
    """Track entity families and enforce max-videos-per-entity rule.
    
    FIX v4: If no entity detected, use topic-hash as family key instead of "unknown".
    Previously all non-entity topics shared one "unknown" family, exhausting at 3
    videos and blocking ALL future topics without detectable entities.
    """

    def __init__(self, family_file: str = FAMILY_FILE):
        self.family_file = family_file
        self._load()

    def _load(self):
        self.data = {}
        if os.path.exists(self.family_file):
            try:
                with open(self.family_file, 'r') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.family_file), exist_ok=True)
        with open(self.family_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def record_topic(self, topic: str):
        """Record a topic, assigning it to an entity family."""
        fp = get_fingerprint(topic)
        entities = list(fp["entities"]) if fp["entities"] else []

        if not entities:
            # FIX v4: hash-based family key for no-entity topics
            topic_hash = hashlib.md5(topic.encode('utf8')).hexdigest()[:8]
            entities = [f"topic_{topic_hash}"]

        for entity in entities:
            if entity not in self.data:
                self.data[entity] = {"count": 0, "aspects": []}
            self.data[entity]["count"] += 1
            for a in fp["aspects"]:
                if a not in self.data[entity]["aspects"]:
                    self.data[entity]["aspects"].append(a)
        self._save()

    def is_entity_exhausted(self, entity: str, max_videos: int = 3) -> bool:
        return self.data.get(entity, {}).get("count", 0) >= max_videos

    def get_exhausted_hint(self, entity: str) -> str:
        count = self.data.get(entity, {}).get("count", 0)
        if entity.startswith("topic_"):
            return "(This specific topic angle already covered. Pick a DIFFERENT subject.)"
        return f"(Entity '{entity}' covered {count} times. Pick a DIFFERENT subject.)"

    def get_all_exhausted(self, max_videos: int = 3) -> list[str]:
        return [e for e, d in self.data.items() if d.get("count", 0) >= max_videos]


# ─── TopicUniquenessChecker ────────────────────────────────────────────────────

class TopicUniquenessChecker:
    """3-level topic dedup pipeline.
    
    Level 1: MinHashLSH — O(1) lookup, catches paraphrases/near-duplicates.
             FAILS for same-subject-different-aspect (Jaccard=0.133 verified).
    Level 2: Fingerprint — pure Python, entity_sim weight=0.4 catches same-subject.
    Level 3: LLM Judge — borderline cases 0.40-0.65 similarity.
    """

    def __init__(self):
        self.family_tracker = TopicFamilyTracker()
        self._lsh = None

    # Lazily initialized LSH index
    @property
    def lsh(self) -> Optional[MinHashLSH]:
        if self._lsh is None and DASKETCH_AVAILABLE:
            self._lsh = load_lsh(LSH_FILE, rebuild_lsh_from_used_topics)
        return self._lsh

    def save_lsh(self):
        """Atomic write current LSH state to blob."""
        if self._lsh is not None:
            save_lsh_atomically(self._lsh, LSH_FILE)

    def _level1_check(self, topic: str) -> list[str]:
        """Level 1: MinHashLSH lookup. Returns list of duplicate topics."""
        if not DASKETCH_AVAILABLE or self.lsh is None:
            return []
        m = topic_to_minhash(topic)
        # Check if we have any tokens (avoid querying empty MinHash)
        tokens = tokenize(topic)
        return self.lsh.query(m) if tokens else []

    def _level2_check(self, topic: str, used_topics: list[str]) -> float:
        """Level 2: Fingerprint similarity. Returns max similarity."""
        fp = get_fingerprint(topic)
        if not fp["tokens"]:
            return 0.0
        max_sim = 0.0
        for used in used_topics:
            fp_used = get_fingerprint(used)
            if not fp_used["tokens"]:
                continue
            sim = fingerprint_similarity(fp, fp_used)
            if sim > max_sim:
                max_sim = sim
        return max_sim

    def check_topic(self, topic: str, used_topics: list[str], llm_judge_fn=None) -> dict:
        """Run 3-level dedup check.
        
        Args:
            topic: New topic to check
            used_topics: List of already-used topic strings
            llm_judge_fn: Optional callable(topic_a, topic_b) -> bool returning True if unique
        
        Returns:
            dict with keys: accepted (bool), rejected (bool), reason (str),
                           level (int 1|2|3|family), duplicate_of (str or None)
        """
        result = {"accepted": False, "rejected": False, "reason": "", "level": 0, "duplicate_of": None}

        # Level 1: MinHashLSH
        if DASKETCH_AVAILABLE:
            l1_dups = self._level1_check(topic)
            if l1_dups:
                result["rejected"] = True
                result["reason"] = f"Level-1 MinHashLSH: near-duplicate detected ({l1_dups[0]})"
                result["level"] = 1
                result["duplicate_of"] = l1_dups[0]
                return result

        # Level 2: Fingerprint
        fp = get_fingerprint(topic)
        max_sim = self._level2_check(topic, used_topics)

        if max_sim > 0.65:
            result["rejected"] = True
            result["reason"] = f"Level-2 Fingerprint: similarity={max_sim:.3f} > 0.65"
            result["level"] = 2
            return result

        if max_sim >= 0.40 and max_sim <= 0.65:
            # Level 3: LLM Judge
            if llm_judge_fn is not None:
                for used in used_topics:
                    if llm_judge_fn(topic, used):
                        result["accepted"] = True
                        result["reason"] = "Level-3 LLM Judge: genuinely different"
                        result["level"] = 3
                        return result
                result["rejected"] = True
                result["reason"] = "Level-3 LLM Judge: not sufficiently different"
                result["level"] = 3
                return result
            # No LLM judge available — conservative reject
            result["rejected"] = True
            result["reason"] = f"Level-2 Fingerprint: similarity={max_sim:.3f} in [0.40,0.65], no LLM judge"
            result["level"] = 2
            return result

        # max_sim < 0.40 — ACCEPT
        result["accepted"] = True
        result["reason"] = f"Level-2 Fingerprint: similarity={max_sim:.3f} < 0.40"
        result["level"] = 2
        return result

    def record_topic(self, topic: str):
        """Record a topic after acceptance."""
        # Update family tracker
        self.family_tracker.record_topic(topic)
        # Update LSH
        if DASKETCH_AVAILABLE and self._lsh is not None:
            key = f"topic_{hashlib.md5(topic.encode('utf8')).hexdigest()[:8]}"
            self._lsh.insert(key, topic_to_minhash(topic))
            self.save_lsh()
        # Update used_topics.json
        self._append_to_used_topics(topic)

    def _append_to_used_topics(self, topic: str):
        fp = get_fingerprint(topic)
        entities = list(fp["entities"]) if fp["entities"] else []
        aspects = list(fp["aspects"]) if fp["aspects"] else []
        if not entities:
            topic_hash = hashlib.md5(topic.encode('utf8')).hexdigest()[:8]
            entities = [f"topic_{topic_hash}"]

        os.makedirs(os.path.dirname(USED_TOPICS_FILE), exist_ok=True)
        try:
            with open(USED_TOPICS_FILE, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {"topics": []}

        data.setdefault("topics", []).append({
            "topic": topic,
            "entity": entities[0] if entities else None,
            "aspect": aspects[0] if aspects else None,
            "account": "auto-pipeline",
            "date": "2026-04-28",
        })

        # Atomic write
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(USED_TOPICS_FILE))
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, USED_TOPICS_FILE)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


# ─── Research State ────────────────────────────────────────────────────────────

PREMIUM_SERVICES = ["tavily", "exa", "firecrawl", "linkup"]


def load_research_state() -> dict:
    if os.path.exists(RESEARCH_STATE_FILE):
        try:
            with open(RESEARCH_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_premium": "tavily",
        "premium_sequence": PREMIUM_SERVICES,
        "last_run": "2026-04-28",
    }


def save_research_state(state: dict):
    os.makedirs(os.path.dirname(RESEARCH_STATE_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(RESEARCH_STATE_FILE))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2)
        os.replace(tmp, RESEARCH_STATE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get_next_premium_service(state: dict) -> str:
    """Get next premium service in rotation."""
    seq = state.get("premium_sequence", PREMIUM_SERVICES)
    last = state.get("last_premium", seq[0])
    try:
        idx = seq.index(last)
        return seq[(idx + 1) % len(seq)]
    except ValueError:
        return seq[0]
