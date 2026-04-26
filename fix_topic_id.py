#!/usr/bin/env python3
content = open('src/classes/YouTube.py').read()

old = '''# Build visual grounding context from extracted facts
visual_grounding = ""
if self.extracted_facts:
    facts = self.extracted_facts
    primary_loc = facts.get("locations", [None])[0] if facts.get("locations") else None
    primary_kf = facts.get("key_facts", [None])[0] if facts.get("key_facts") else None
    topic_id = facts.get("topic_identifier") or self.subject
    visual_grounding = f"""
VISUAL GROUNDING (facts from research — these MUST appear in the visuals):
- Subject: {topic_id}
- Location: {primary_loc if primary_loc else 'unknown'}
- Key visual element: {primary_kf if primary_kf else 'mysterious setting'}
"""
prompt = f"""You are a visual storyboard director'''

new = '''# Build visual grounding context from extracted facts
facts = self.extracted_facts if self.extracted_facts else {}
primary_loc = (facts.get("locations") or [None])[0]
primary_kf = (facts.get("key_facts") or [None])[0]
topic_id = facts.get("topic_identifier") or self.subject
visual_grounding = ""
if self.extracted_facts:
    visual_grounding = f"""
VISUAL GROUNDING (facts from research — these MUST appear in the visuals):
- Subject: {topic_id}
- Location: {primary_loc if primary_loc else 'unknown'}
- Key visual element: {primary_kf if primary_kf else 'mysterious setting'}
"""
prompt = f"""You are a visual storyboard director'''

if old in content:
    content = content.replace(old, new)
    open('src/classes/YouTube.py', 'w').write(content)
    print('FIXED')
else:
    print('NOT FOUND')
    idx = content.find('# Build visual grounding context from extracted facts')
    if idx >= 0:
        print('Context:', repr(content[idx:idx+600]))