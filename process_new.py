import json
import os
import re
import urllib.request
from datetime import datetime
from html import unescape


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def strip_tags(html):
    text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_between(html, marker):
    if marker not in html:
        return ""
    start = html.find(marker)
    snippet = html[start:start + 200000]
    return snippet


def extract_article_text(html):
    snippet = extract_between(html, 'available-content')
    if not snippet:
        snippet = extract_between(html, 'body markup')
    return strip_tags(snippet)


def extract_title(html):
    match = re.search(r'<h1 class="post-title"[^>]*>(.*?)</h1>', html, flags=re.S | re.I)
    if match:
        return strip_tags(match.group(1))
    match = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
    return strip_tags(match.group(1)) if match else "Today I Learned"


def extract_date(html):
    match = re.search(r"<time[^>]*datetime=\"([^\"]+)\"", html, flags=re.S | re.I)
    if match:
        return match.group(1)
    return datetime.utcnow().isoformat()


def build_learning(text):
    sentences = [s.strip() for s in text.split(". ") if len(s.strip()) >= 60]
    if sentences:
        return ". ".join(sentences[:4]) + "."
    return text[:600]


def main():
    url = os.environ.get("NEW_URL")
    if not url:
        print("No NEW_URL provided.")
        return

    html = fetch(url)
    content = extract_article_text(html)
    if not content:
        print("Could not extract article text.")
        return

    new_learning = {
        "learning": build_learning(content),
        "articleUrl": url,
        "title": extract_title(html),
        "date": extract_date(html)
    }

    with open("learnings.json", "r", encoding="utf-8") as f:
        learnings = json.load(f)
    if not isinstance(learnings, list):
        learnings = []

    learnings.insert(0, new_learning)

    with open("learnings.json", "w", encoding="utf-8") as f:
        json.dump(learnings, f, indent=2)

    print("Added new learning.")


if __name__ == "__main__":
    main()
