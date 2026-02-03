const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');

function extractParagraphs(text) {
  return (text || '')
    .split('\n')
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter((line) => line.length >= 60);
}

function buildFreeLearning(articleText) {
  const paragraphs = extractParagraphs(articleText);
  if (paragraphs.length >= 2) {
    return paragraphs.slice(0, 3).join('\n\n');
  }

  const sentences = (articleText || '')
    .replace(/\s+/g, ' ')
    .split('. ')
    .map((s) => s.trim())
    .filter((s) => s.length >= 40);

  return sentences.slice(0, 4).join('. ') + (sentences.length ? '.' : '');
}

async function fetchArticle(url) {
  const response = await axios.get(url);
  const $ = cheerio.load(response.data);
  const title = $('h1.post-title').text().trim() || $('title').text().trim();
  const date = $('time').attr('datetime') || $('time').text().trim();
  const articleText = $('.available-content').text().trim() || $('.body.markup').text().trim();
  return { title, date, articleText };
}

async function seedLearnings() {
  const existing = JSON.parse(fs.readFileSync('learnings.json', 'utf-8'));
  if (Array.isArray(existing) && existing.length >= 5) {
    console.log('Seed not needed. Learnings already populated.');
    return;
  }

  const response = await axios.get('https://thedailybrief.zerodha.com/api/v1/archive?sort=new&limit=8');
  const articles = response.data || [];
  const seeded = [];

  for (const article of articles) {
    try {
      const { title, date, articleText } = await fetchArticle(article.canonical_url);
      if (!articleText) continue;

      const learning = buildFreeLearning(articleText);
      if (!learning) continue;

      seeded.push({
        learning,
        articleUrl: article.canonical_url,
        title: title || article.title || 'Today I Learned',
        date: date || article.post_date || new Date().toISOString()
      });
    } catch (error) {
      console.error(`Seed failed for ${article.canonical_url}:`, error.message);
    }
  }

  if (!seeded.length) {
    console.log('No learnings seeded.');
    return;
  }

  fs.writeFileSync('learnings.json', JSON.stringify(seeded, null, 2));
  console.log(`Seeded ${seeded.length} learnings.`);
}

seedLearnings().catch((err) => {
  console.error('Seed error:', err);
  process.exit(1);
});
