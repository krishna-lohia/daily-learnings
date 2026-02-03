#!/usr/bin/env python3
"""
Perfect learning extractor - gets straight to the good content
"""

import json
import re
from html.parser import HTMLParser


class ParagraphExtractor(HTMLParser):
    """Extract only <p> tag content from HTML"""
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.current_p = []
        self.in_p = False
        self.skip_tags = {'script', 'style', 'iframe', 'noscript', 'svg'}
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


def is_intro_fluff(para):
    """Check if paragraph is intro/promotional fluff"""
    para_lower = para.lower()

    # Obvious intro patterns
    intro_phrases = [
        'our goal with the daily brief',
        'listen to the podcast',
        'watch the videos',
        'spotify',
        'apple podcasts',
        'youtube',
        'in today\'s edition',
        'in this edition',
        'welcome to',
        'i\'m your host',
        'for those of you who are new',
        'just a quick heads-up',
        'heads up before we dive',
        'ipo is open now',
        'you can read the full story',
        'check out',
        'read full story',
        'share this post',
        'leave a comment',
        'subscribe',
        'substack',
    ]

    if any(phrase in para_lower for phrase in intro_phrases):
        return True

    # Short paragraphs that are just section headers
    if len(para) < 60:
        return True

    # Check if it's mostly a list of topics (like "In today's edition: X, Y, Z")
    if para_lower.startswith('in ') and ':' in para and para.count(',') > 2:
        return True

    return False


def is_good_content(para):
    """Check if paragraph is actual valuable content"""
    # Must be substantial
    if len(para) < 100:
        return False

    # Must have enough actual words
    words = para.split()
    if len(words) < 20:
        return False

    # Must be mostly letters (not code/data)
    letters = sum(c.isalpha() or c.isspace() for c in para)
    if letters < len(para) * 0.75:
        return False

    # Should have multiple sentences
    sentence_endings = para.count('. ') + para.count('? ') + para.count('! ')
    if sentence_endings < 1 and len(para) < 250:
        return False

    return True


def extract_content_paragraphs(html):
    """Extract good content paragraphs, skipping all intro fluff"""
    parser = ParagraphExtractor()
    parser.feed(html)

    good_paragraphs = []
    found_real_content = False

    for para in parser.paragraphs:
        # Skip intro fluff
        if is_intro_fluff(para):
            continue

        # Once we find real content, we're past the intro
        if not found_real_content:
            if is_good_content(para):
                found_real_content = True
                good_paragraphs.append(para)
        else:
            # After intro, take all good content
            if is_good_content(para):
                good_paragraphs.append(para)

        # Stop once we have enough
        if len(good_paragraphs) >= 8:
            break

    return good_paragraphs


def create_learning(paragraphs, title):
    """Create a learning from good paragraphs"""
    if not paragraphs or len(paragraphs) < 2:
        return None

    # Take first 5-7 paragraphs
    learning_paras = paragraphs[:7]
    learning_text = '\n\n'.join(learning_paras)

    # Truncate if too long (max 600 words)
    words = learning_text.split()
    if len(words) > 600:
        # Try to cut at paragraph boundary
        paras_to_use = []
        word_count = 0
        for para in learning_paras:
            para_words = len(para.split())
            if word_count + para_words <= 600:
                paras_to_use.append(para)
                word_count += para_words
            else:
                break

        if paras_to_use:
            learning_text = '\n\n'.join(paras_to_use)

    # Clean up title
    title = title.strip()
    for prefix in ['The Daily Brief:', 'TDB:', 'Episode:', '#']:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()

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

        # Extract content paragraphs
        paragraphs = extract_content_paragraphs(content_html)

        if len(paragraphs) < 2:
            skipped += 1
            continue

        # Create learning
        learning = create_learning(paragraphs, title)

        if learning and len(learning['learning']) > 300:
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

    # Show samples
    if len(learnings) >= 3:
        print(f'\n--- Sample learnings ---')
        for i in range(min(3, len(learnings))):
            print(f'\n[{i+1}] {learnings[i]["title"]}')
            print(f'First 250 chars: {learnings[i]["learning"][:250]}...\n')


if __name__ == '__main__':
    main()
