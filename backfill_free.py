import json
import re
import time
import urllib.request
from datetime import datetime
from html import unescape
from html.parser import HTMLParser


ARCHIVE_URL = "https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit={limit}&offset={offset}"


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_json(url):
    return json.loads(fetch(url))


class ContentExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.capture_article = False
        self.depth = 0
        self.text = []
        self.article_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_attr = attrs_dict.get("class", "")
        if isinstance(class_attr, list):
            class_attr = " ".join(class_attr)
        class_attr = class_attr or ""

        if tag == "article":
            self.capture_article = True

        if any(key in class_attr for key in [
            "available-content",
            "post-content",
            "post-body",
            "post-content-container",
            "article-body",
        ]):
            self.capture = True
            self.depth = 1
            return

        if self.capture:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "article":
            self.capture_article = False
        if self.capture:
            self.depth -= 1
            if self.depth <= 0:
                self.capture = False

    def handle_data(self, data):
        if not data or not data.strip():
            return
        if self.capture:
            self.text.append(data)
        elif self.capture_article:
            self.article_text.append(data)


def normalize_text(text):
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_boilerplate(text):
    if not text:
        return ""
    patterns = [
        r"our goal with the daily brief",
        r"check out the audio",
        r"spotify",
        r"apple podcasts",
        r"if you prefer video",
        r"marketsbyzerodha",
        r"thedailybriefing\.substack\.com",
        r"this content is for informational purposes",
        r"we publish a new episode every day",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_article_text(html):
    parser = ContentExtractor()
    parser.feed(html)
    text = " ".join(parser.text).strip()
    if not text:
        text = " ".join(parser.article_text).strip()
    return normalize_text(text)


def extract_title(html):
    match = re.search(r'<h1 class="post-title"[^>]*>(.*?)</h1>', html, flags=re.S | re.I)
    if match:
        return normalize_text(match.group(1))
    match = re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I)
    return normalize_text(match.group(1)) if match else "Today I Learned"


def build_learning(text):
    cleaned = strip_boilerplate(text)
    sentences = [s.strip() for s in cleaned.split(". ") if len(s.strip()) >= 60]
    if sentences:
        return ". ".join(sentences[:4]) + "."
    return cleaned[:600]


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
                if not learning:
                    continue
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
