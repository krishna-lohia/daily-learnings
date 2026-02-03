import json
import re
import urllib.request
from html import unescape
from datetime import datetime
from html.parser import HTMLParser


ARCHIVE_URL = "https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit=8"


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


def strip_tags(html):
    text = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def extract_date(html):
    match = re.search(r"<time[^>]*datetime=\"([^\"]+)\"", html, flags=re.S | re.I)
    if match:
        return match.group(1)
    return datetime.utcnow().isoformat()


def build_learning(text):
    cleaned = strip_boilerplate(text)
    paragraphs = [p.strip() for p in cleaned.split(". ") if len(p.strip()) >= 60]
    if paragraphs:
        return ". ".join(paragraphs[:4]) + "."
    return cleaned[:600]


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
