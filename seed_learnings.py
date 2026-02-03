import json
import re
import urllib.request
from html import unescape
from datetime import datetime


ARCHIVE_URL = "https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit=8"


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
    paragraphs = [p.strip() for p in text.split(". ") if len(p.strip()) >= 60]
    if paragraphs:
        return ". ".join(paragraphs[:4]) + "."
    return text[:600]


def main():
    with open("learnings.json", "r", encoding="utf-8") as f:
        existing = json.load(f)
    if isinstance(existing, list) and len(existing) >= 5:
        print("Seed not needed.")
        return

    archive = json.loads(fetch(ARCHIVE_URL))
    learnings = []

    for article in archive:
        url = article.get("canonical_url")
        if not url:
            continue
        try:
            html = fetch(url)
            content = extract_article_text(html)
            if not content:
                continue
            learning = build_learning(content)
            learnings.append({
                "learning": learning,
                "articleUrl": url,
                "title": extract_title(html),
                "date": extract_date(html)
            })
        except Exception:
            continue

    if learnings:
        with open("learnings.json", "w", encoding="utf-8") as f:
            json.dump(learnings, f, indent=2)
        print(f"Seeded {len(learnings)} learnings.")
    else:
        print("No learnings seeded.")


if __name__ == "__main__":
    main()
