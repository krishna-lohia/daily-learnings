import json
import re
import time
import urllib.request
from datetime import datetime
from html import unescape


ARCHIVE_URL = "https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit={limit}&offset={offset}"


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_json(url):
    return json.loads(fetch(url))


def strip_tags(html):
    text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.S | re.I)
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
    snippet = extract_between(html, "available-content")
    if not snippet:
        snippet = extract_between(html, "body markup")
    return strip_tags(snippet)


def extract_title(html):
    match = re.search(r'<h1 class="post-title"[^>]*>(.*?)</h1>', html, flags=re.S | re.I)
    if match:
        return strip_tags(match.group(1))
    match = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
    return strip_tags(match.group(1)) if match else "Today I Learned"


def build_learning(text):
    sentences = [s.strip() for s in text.split(". ") if len(s.strip()) >= 60]
    if sentences:
        return ". ".join(sentences[:4]) + "."
    return text[:600]


def load_existing():
    try:
        with open("learnings.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except FileNotFoundError:
        pass
    return []


def main():
    existing = load_existing()
    seen = {item.get("articleUrl") for item in existing if isinstance(item, dict)}
    all_learnings = list(existing)

    offset = 0
    limit = 25
    added = 0

    while True:
        archive = fetch_json(ARCHIVE_URL.format(limit=limit, offset=offset))
        if not archive:
            break

        for article in archive:
            url = article.get("canonical_url")
            if not url or url in seen:
                continue

            try:
                html = fetch(url)
                content = extract_article_text(html)
                if not content:
                    continue
                learning = build_learning(content)
                all_learnings.append({
                    "learning": learning,
                    "articleUrl": url,
                    "title": extract_title(html),
                    "date": article.get("post_date") or datetime.utcnow().isoformat(),
                })
                seen.add(url)
                added += 1
                time.sleep(1)
            except Exception:
                continue

        offset += limit
        time.sleep(2)

    if added:
        with open("learnings.json", "w", encoding="utf-8") as f:
            json.dump(all_learnings, f, indent=2)

    print(f"Backfill complete. Added {added} learnings.")


if __name__ == "__main__":
    main()
