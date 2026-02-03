import json
import os
import re
import urllib.request
from datetime import datetime
from html import unescape
from html.parser import HTMLParser


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
    sentences = [s.strip() for s in cleaned.split(". ") if len(s.strip()) >= 60]
    if sentences:
        return ". ".join(sentences[:4]) + "."
    return cleaned[:600]


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
