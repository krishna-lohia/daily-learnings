import json
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_p = False

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.in_p = True

    def handle_endtag(self, tag):
        if tag == 'p':
            self.in_p = False
            self.text.append('\n\n')

    def handle_data(self, data):
        if self.in_p:
            self.text.append(data)

with open('/home/krishna.lohia/articles-full-content.json', 'r') as f:
    articles = json.load(f)

# Look at first article
article = articles[0]
print(f"Title: {article['title']}\n")
print(f"URL: {article['url']}\n")

parser = TextExtractor()
parser.feed(article['content'])
text = ''.join(parser.text)

# Print first 1500 chars
print("First 1500 chars of content:")
print(text[:1500])
print("\n\n---\n\n")

# Print paragraphs
paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
print(f"Total paragraphs: {len(paragraphs)}\n")
print("First 5 paragraphs:")
for i, p in enumerate(paragraphs[:5]):
    print(f"\n[Para {i+1}]: {p[:300]}...")
