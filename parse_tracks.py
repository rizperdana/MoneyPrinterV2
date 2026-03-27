import re
import json
import sys

def parse_pixabay_html(html_text):
    # Pattern to match each track entry
    # We look for lines that start with ![Image ...](https://pixabay.com/static/img/blank.gif)
    # Then capture the title link, artist link, duration, and genre tags.
    pattern = re.compile(
        r'!\[Image \d+\]\(https://pixabay\.com/static/img/blank\.gif\)\s*'
        r'\[([^\]]+)\]\(([^)]+)\)\s*'  # title and track_url
        r'\[([^\]]+)\]\(([^)]+)\)\s*'  # artist and artist_url (ignored)
        r'(\d+:\d+)\s*'                # duration
        r'((?:\[[^\]]+\]\([^)]+\)\s*)*)' # genre tags (capture the whole group)
    , re.DOTALL)
    
    matches = pattern.findall(html_text)
    tracks = []
    for match in matches:
        title, track_url, artist, artist_url, duration, tags_string = match
        # Extract genre tags from tags_string
        tag_pattern = re.compile(r'\[([^\]]+)\]\([^)]+\)')
        tags = tag_pattern.findall(tags_string)
        tracks.append({
            'title': title.strip(),
            'track_url': track_url.strip(),
            'duration': duration.strip(),
            'tags': tags
        })
    return tracks

if __name__ == '__main__':
    # Read HTML from stdin
    html_text = sys.stdin.read()
    tracks = parse_pixabay_html(html_text)
    # Output as JSON
    print(json.dumps(tracks, indent=2))