#!/usr/bin/env python3
"""
Smart learning extractor - extracts actual valuable content from articles
"""

import json
import re
from html.parser import HTMLParser


class ParagraphExtractor(HTMLParser):
    """Extract paragraphs from HTML"""
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.current_p = []
        self.in_p = False
        self.skip_tags = {'script', 'style', 'iframe', 'noscript'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip_depth += 1
        elif tag == 'p' and self.skip_depth == 0:
            self.in_p = True
            self.current_p = []

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif tag == 'p' and self.in_p:
            self.in_p = False
            text = ' '.join(self.current_p).strip()
            if text:
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self.in_p and self.skip_depth == 0:
            self.current_p.append(data.strip())


def is_boilerplate(para):
    """Check if paragraph is boilerplate"""
    para_lower = para.lower()
    boilerplate = [
        'our goal with the daily brief',
        'listen to the podcast',
        'spotify',
        'apple podcasts',
        'watch the videos on youtube',
        'in today\'s edition',
        'in this edition',
        'welcome to',
        'i\'m your host',
        'for those of you who are new',
        'share this post',
        'leave a comment',
        'subscribe',
        'privacy',
        'terms',
        'collection notice',
    ]
    return any(bp in para_lower for bp in boilerplate)


def is_substantial(para):
    """Check if paragraph has substantial content"""
    if len(para) < 80:  # Too short
        return False
    if len(para) > 2000:  # Too long (probably includes unwanted content)
        return False

    # Check if mostly letters (not metadata/junk)
    letters = sum(c.isalpha() or c.isspace() for c in para)
    if letters < len(para) * 0.7:
        return False

    # Check if it's a real paragraph (has multiple sentences or is long)
    sentences = para.count('. ') + para.count('? ') + para.count('! ')
    if sentences >= 2 or len(para) > 200:
        return True

    return False


def extract_good_paragraphs(html, max_paragraphs=8):
    """Extract good content paragraphs from HTML"""
    parser = ParagraphExtractor()
    parser.feed(html)

    good_paras = []
    for para in parser.paragraphs:
        # Skip boilerplate
        if is_boilerplate(para):
            continue

        # Only keep substantial paragraphs
        if not is_substantial(para):
            continue

        good_paras.append(para)

        # Stop once we have enough
        if len(good_paras) >= max_paragraphs:
            break

    return good_paras


def create_learning(paragraphs, title):
    """Create a learning from paragraphs"""
    if not paragraphs:
        return None

    # Take first 4-6 paragraphs (about 400-600 words)
    learning_paras = paragraphs[:6]
    learning_text = '\n\n'.join(learning_paras)

    # Truncate if too long
    words = learning_text.split()
    if len(words) > 500:
        learning_text = ' '.join(words[:500])
        # Try to end at a sentence
        for ending in ['. ', '! ', '? ']:
            last_idx = learning_text.rfind(ending)
            if last_idx > len(learning_text) * 0.8:  # If we can find ending near the end
                learning_text = learning_text[:last_idx + 1]
                break

    # Clean up title
    title = title.strip()
    for prefix in ['The Daily Brief:', 'TDB:', 'Episode:']:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()

    # Truncate long titles
    if len(title) > 100:
        title = title[:97] + '...'

    return {
        'learning': learning_text,
        'title': title
    }


def main():
    print('Loading articles...')
    with open('/home/krishna.lohia/articles-full-content.json', 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f'Found {len(articles)} articles\n')

    learnings = []
    skipped = 0

    for i, article in enumerate(articles):
        url = article.get('url', '')
        title = article.get('title', 'Untitled')
        date = article.get('date', '')
        content_html = article.get('content', '')

        if not content_html or len(content_html) < 1000:
            skipped += 1
            continue

        # Extract good paragraphs
        paragraphs = extract_good_paragraphs(content_html)

        if len(paragraphs) < 3:
            skipped += 1
            continue

        # Create learning
        learning = create_learning(paragraphs, title)

        if learning and len(learning['learning']) > 200:
            learnings.append({
                'learning': learning['learning'],
                'title': learning['title'],
                'articleUrl': url,
                'date': date
            })

            if (i + 1) % 25 == 0:
                print(f'Processed {i + 1}/{len(articles)}... ({len(learnings)} good, {skipped} skipped)')

    print(f'\n✓ Done!')
    print(f'  Total articles: {len(articles)}')
    print(f'  Quality learnings: {len(learnings)}')
    print(f'  Skipped: {skipped}')

    # Save
    output_path = '/home/krishna.lohia/daily-learnings/learnings.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(learnings, f, indent=2, ensure_ascii=False)

    print(f'\nSaved to {output_path}')

    # Show a sample
    if learnings:
        print(f'\n--- Sample learning ---')
        print(f'Title: {learnings[0]["title"]}')
        print(f'Learning (first 300 chars): {learnings[0]["learning"][:300]}...')


if __name__ == '__main__':
    main()
