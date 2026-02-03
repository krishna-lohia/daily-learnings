#!/usr/bin/env python3
"""
Free learning extractor - no API costs
Extracts quality learnings from Daily Brief articles using smart heuristics
"""

import json
import re
from html.parser import HTMLParser
from html import unescape


class TextExtractor(HTMLParser):
    """Extract text from HTML, ignoring scripts, styles, etc."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ['script', 'style', 'iframe', 'noscript']:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ['script', 'style', 'iframe', 'noscript']:
            self.skip = False
        elif tag in ['p', 'div', 'li', 'h1', 'h2', 'h3']:
            self.text_parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.text_parts.append(data)

    def get_text(self):
        return ' '.join(self.text_parts)


def html_to_text(html):
    """Convert HTML to plain text"""
    extractor = TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_boilerplate(text):
    """Check if text is boilerplate/intro fluff"""
    boilerplate_phrases = [
        'our goal with the daily brief',
        'listen to the podcast',
        'spotify',
        'apple podcasts',
        'watch the videos on youtube',
        'subscribe',
        'in today\'s edition',
        'welcome to',
        'share this post',
        'leave a comment',
        'get the app',
        'privacy',
        'terms',
        'collection notice',
        'substack',
        'for informational purposes',
        'window.sentry',
        'we sat down with',
        'for those of you who are new',
        'i\'m your host',
        'let me quickly set the context',
        'we won\'t just tell you what happened',
        'we do this show in both formats',
        'this piece curates',
        'you can also watch',
        'if you prefer video',
        'audio version',
    ]

    text_lower = text.lower()
    return any(phrase in text_lower for phrase in boilerplate_phrases)


def find_content_start(text):
    """Find where the actual content starts, skipping intro"""
    # Look for common section headers that mark content start
    patterns = [
        r'(?:^|\n\s*)(?:The|A|An|In|When|Why|How|What)\s+[A-Z][a-z]+.*?(?:is|are|was|were|can|could|will|should)',
        r'(?:^|\n\s*)[A-Z][^.!?]{50,200}[.!?]',
    ]

    # Skip first 500 chars (likely all intro)
    search_start = min(500, len(text) // 4)
    search_text = text[search_start:]

    for pattern in patterns:
        match = re.search(pattern, search_text)
        if match:
            return search_start + match.start()

    # If no pattern matches, start from 25% of the way through
    return len(text) // 4


def extract_paragraphs(text):
    """Split text into paragraphs and filter out junk"""
    # Find where content actually starts
    content_start = find_content_start(text)
    text = text[content_start:]

    # Split by sentence-ending punctuation followed by space
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Group sentences into paragraphs
    paragraphs = []
    current_para = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 30:
            continue

        # Skip boilerplate sentences
        if is_boilerplate(sentence):
            # If we have a partial paragraph, save it
            if current_length >= 150:
                paragraphs.append(' '.join(current_para))
                current_para = []
                current_length = 0
            continue

        current_para.append(sentence)
        current_length += len(sentence)

        # Create a paragraph when we have enough content
        if current_length >= 300 and len(current_para) >= 3:
            para_text = ' '.join(current_para)
            paragraphs.append(para_text)
            current_para = []
            current_length = 0

            # Stop after we have enough paragraphs
            if len(paragraphs) >= 5:
                break

    # Add remaining sentences if substantial
    if current_length >= 200 and len(paragraphs) < 5:
        paragraphs.append(' '.join(current_para))

    return paragraphs


def create_learning(paragraphs, article_title):
    """Create a learning from good paragraphs"""
    if not paragraphs:
        return None

    # Take the first 3-5 substantial paragraphs
    learning_text = '\n\n'.join(paragraphs[:5])

    # Truncate if too long (max ~400 words)
    words = learning_text.split()
    if len(words) > 400:
        learning_text = ' '.join(words[:400]) + '...'

    # Generate a simple title from article title
    title = article_title

    # Remove common prefixes
    for prefix in ['The Daily Brief:', 'TDB:', 'Episode:', '#']:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()

    # Truncate long titles
    if len(title) > 80:
        title = title[:77] + '...'

    return {
        'learning': learning_text,
        'title': title
    }


def process_articles(input_file, output_file):
    """Process all articles and extract learnings"""
    print(f'Loading articles from {input_file}...')

    with open(input_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f'Found {len(articles)} articles')

    learnings = []
    skipped = 0

    for i, article in enumerate(articles):
        # Get basic info
        url = article.get('url', '')
        title = article.get('title', 'Untitled')
        date = article.get('date', '')
        content_html = article.get('content', '')

        if not content_html or len(content_html) < 500:
            skipped += 1
            continue

        # Extract text from HTML
        text = html_to_text(content_html)

        if len(text) < 300:
            skipped += 1
            continue

        # Get good paragraphs
        paragraphs = extract_paragraphs(text)

        if len(paragraphs) < 1:
            skipped += 1
            continue

        # Create learning
        learning = create_learning(paragraphs, title)

        if learning:
            learnings.append({
                'learning': learning['learning'],
                'title': learning['title'],
                'articleUrl': url,
                'date': date
            })

            if (i + 1) % 50 == 0:
                print(f'  Processed {i + 1}/{len(articles)}... ({len(learnings)} good, {skipped} skipped)')

    print(f'\nDone!')
    print(f'  Total articles: {len(articles)}')
    print(f'  Quality learnings: {len(learnings)}')
    print(f'  Skipped: {skipped}')

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(learnings, f, indent=2, ensure_ascii=False)

    print(f'\nSaved to {output_file}')


if __name__ == '__main__':
    process_articles(
        '/home/krishna.lohia/articles-full-content.json',
        '/home/krishna.lohia/daily-learnings/learnings.json'
    )
