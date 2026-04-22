# Spec: Fact-Ground Script & Image Generation

## Problem Statement

Research collects rich text from multiple sources, but after topic selection, all specificity is lost — the entire pipeline reduces everything to a single `self.subject` string.

**Example of broken behavior:**
- Research finds: "Judge John Smith in Ohio secretly stored 3000 preserved hearts in a cellar beneath the courthouse"
- Topic selected: "Why Did This Judge Hide 3000 Preserved Hearts in His Secret Cellar"
- Script generated: "A judge somewhere stored strange things in his cellar..." (no names, no location)
- Image prompts: "a dark cellar" (no Ohio, no judge name)
- Metadata: generic tags, no extracted facts

The LLM must hallucinate missing details because **structured facts never flow downstream**.

---

## Design

### 1. Structured Fact Extraction (NEW)

**Location:** `src/research.py` — extend with a new function `extract_facts(research_text: str, topic_hint: str) -> dict`

**Trigger:** After `_research_trending_topics()` but **before** `generate_topic()` — facts inform topic selection.

**Input:** Raw research text (same text used for topic inspiration), plus topic hint string.

**Output:** Structured `ExtractedFacts` dict:
```python
{
    "person_names": ["John Smith"],           # people's names found
    "locations": ["Ohio", "Columbus"],        # places found
    "dates": ["November 2023"],               # dates/years found
    "organizations": ["American Medical Board"], # org names found
    "key_facts": [                             # specific claims (numbers, events)
        "3000 preserved hearts",
        "secret cellar beneath courthouse",
        "hearts still beating when found"
    ],
    "topic_identifier": None,                 # explicit entity name if topic is a specific known thing (Bigfoot, Bermuda Triangle), else None
    "source_urls": ["https://..."],            # URLs facts came from
    "confidence": "high",                      # "high" | "medium" | "low"
    "extraction_note": "2 names, 2 locations, 4 key facts found"
}
```

**Prompt design for extraction LLM call:**
- System: "You are a fact extraction specialist. Extract all specific entities from the text."
- User: research text + "Topic hint: {topic_hint}"
- Parse output as JSON into the dict above
- If no facts found but topic string contains a specific name/noun (e.g., "Bigfoot", "Bermuda Triangle") → set `topic_identifier` to that, `confidence: "low"`

**Edge case — extraction failure handling:**
| Condition | Action |
|---|---|
| No facts found AND topic string has no specific identifier | Return `confidence: "low"`, empty lists. Downstream uses topic identifier as minimum. |
| No facts found BUT topic string is specific | Set `topic_identifier` from topic string, `confidence: "low"` |
| Some facts found | Normal flow. Even 1 fact is enough to ground. |
| LLM parse fails | Return `confidence: "low"`, empty lists, topic_identifier from topic string |

---

### 2. Pass Facts Through Topic Selection

**Change:** `generate_topic()` takes `extracted_facts` as input. Topic is still selected, but the LLM prompt includes extracted facts as grounding context alongside research text.

**Effect:** Topic selection is better informed — e.g., picks the variant "Judge John Smith hidden hearts case" instead of generic "Why Did This Judge Hide Preserved Hearts".

**Storage:** `self.extracted_facts = extracted_facts` on the YouTube object.

---

### 3. Script Generation — Facts as Context

**Change:** `generate_script()` passes `self.extracted_facts` alongside `self.subject`.

**Prompt update:**
```
FACTS FROM RESEARCH (you MUST use these in the script):
- Names to mention: {person_names}
- Locations to include: {locations}
- Specific claims to reference: {key_facts}

⚠️ MANDATORY: Script must include at least one name from person_names OR one location from locations OR one specific fact from key_facts. Do NOT write generic descriptions. If the topic is "Bigfoot", the script must say "Bigfoot" (or the topic_identifier), not "the mysterious creature".
```

**Fallback behavior:**
- If `confidence == "low"` and `topic_identifier` is set → script MUST use topic_identifier explicitly
- If `confidence == "low"` and no `topic_identifier` → script uses topic string only (current behavior)

**Word count:** Variable length (model decides) — user chose D, but within 70-180 word soft ceiling. Over 180 words triggers truncation warning.

---

### 4. Image Prompt Generation — Facts Ground Visuals

**Change:** `generate_prompts()` passes `self.extracted_facts` alongside `self.subject` + `self.script`.

**Prompt update:**
```
VISUAL GROUNDING (facts from research — these MUST appear in the visuals):
- Subject: {topic_identifier or subject}
- Location: {locations[0] if locations else "unknown"}
- Key visual element: {key_facts[0] if key_facts else "mysterious setting"}

Example grounding:
- Good: "Ohio courthouse cellar with rows of preserved medical specimens" (grounded)
- Bad: "a dark underground room" (generic, no facts)
```

**Mandatory rule:** Image prompts MUST include at least the primary location (if found) OR the topic identifier in the visual description. Visual style can be creative, but the subject/location grounding is non-negotiable.

---

### 5. Metadata — Facts in Description, Tags, Title

**Change:** `generate_metadata()` passes `self.extracted_facts`.

**Title:**
- Stays curiosity-driven formula (unchanged)
- If facts are high-confidence, title can include identifier at end: "Judge Hidden Hearts Scandal (Ohio, 2023) — Can You Believe It?"
- Soft rule: identifier in parentheses at end only, not replacing the hook

**Description:**
- Include 1-2 extracted key facts in the description body
- End with open question (unchanged)

**Tags (SEO):**
- Always include `topic_identifier` as a tag if set (e.g., "Bigfoot", "BermudaTriangle")
- Include `locations` as tags if found (e.g., "Ohio", "Bermuda")
- Include `person_names` as tags if found (e.g., "JohnSmith")
- Keep total tags at 10-15

---

### 6. Hook Techniques as Advisory Context

**Change:** Add hook techniques reference to script generation prompt (as comment/guidance, not enforced structure).

**Reference content (from research):**
- 3-second window: viewers decide stay/scroll in under 3 seconds
- Pattern interrupt: unexpected element breaks expectation
- Curiosity gap: start with mystery, withhold key info
- Bold statement/stats: lead with shocking number or claim
- "I couldn't believe..." formula
- Hook → Hold → Payoff: 3-part retention control
- Multiple hooks: 2-3 per short (open, midpoint, close)

**Implementation:** Include these as an advisory note in the script prompt, not as required output format. LLM decides how to deploy them.

---

### 7. Pipeline Order Change

**Current order:**
```
research → topic → script → metadata → image_prompts → images → TTS → combine
```

**New order:**
```
research → extract_facts → topic (with facts context) → script (with facts) → metadata (with facts) → image_prompts (with facts) → images → TTS → combine
```

---

## File Changes

| File | Change |
|---|---|
| `src/research.py` | Add `extract_facts(research_text, topic_hint) -> dict` function |
| `src/classes/YouTube.py` | Add `self.extracted_facts`, update `generate_topic()`, `generate_script()`, `generate_metadata()`, `generate_prompts()` |
| `src/run_pipeline.py` | Store and pass `extracted_facts` between steps |

---

## Validation Checklist

After implementation, verify:

- [ ] Script mentions at least one extracted name/location/fact (not just topic string)
- [ ] Image prompts include specific location or topic identifier (not generic "a dark room")
- [ ] Tags include extracted names and locations
- [ ] Description body includes at least one key fact
- [ ] Title can include identifier suffix but keeps hook formula
- [ ] Low-confidence extraction still enforces topic_identifier usage
- [ ] Pipeline fails gracefully with warning if no facts AND no identifier
- [ ] Word count stays within 70-180 (soft ceiling)
- [ ] Hook patterns available to LLM as reference but not enforced

---

## Open Questions

1. **Extraction LLM call cost** — extraction adds one LLM call per run. Acceptable?
2. **Which model for extraction?** — could use a fast/cheap model. Default to `topic` model routing.
3. **Should extracted facts be stored in DB?** — `db.py` could store `extracted_facts` alongside video record for audit/debug.
4. **Test coverage** — how to test extraction quality without running full pipeline?

---

## Priority

1. **P0 (core fix):** `extract_facts()` in `research.py` + pass to `generate_script()`
2. **P1:** Pass facts to `generate_prompts()` and `generate_metadata()`
3. **P2:** Topic selection informed by facts
4. **P3:** DB storage + extraction quality testing
