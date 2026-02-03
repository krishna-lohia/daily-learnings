const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const Anthropic = require('@anthropic-ai/sdk');

const anthropic = process.env.ANTHROPIC_API_KEY
  ? new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  : null;

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

async function processNewArticle() {
  const newUrl = process.env.NEW_URL;
  if (!newUrl) {
    console.log('No new article URL found. Exiting.');
    return;
  }

  try {
    const response = await axios.get(newUrl);
    const $ = cheerio.load(response.data);

    const title = $('title').text();
    const articleText = $('.available-content').text();

    if (!articleText) {
      console.log('Could not extract article text. Exiting.');
      return;
    }

    let learning = '';
    if (anthropic) {
      const msg = await anthropic.messages.create({
        model: 'claude-3-haiku-20240307',
        max_tokens: 2048,
        messages: [
          {
            role: 'user',
            content: `Based on the following article, what is the single most important thing to learn? Provide a concise summary of the key learning. The article is from The Daily Brief by Zerodha.\n\nArticle:\n${articleText}`,
          },
        ],
      });
      learning = msg.content[0].text;
    } else {
      learning = buildFreeLearning(articleText);
    }

    const learnings = JSON.parse(fs.readFileSync('learnings.json', 'utf-8'));

    const newLearning = {
      learning: learning,
      articleUrl: newUrl,
      title: title,
      date: new Date().toISOString(),
    };

    learnings.unshift(newLearning);

    fs.writeFileSync('learnings.json', JSON.stringify(learnings, null, 2));
    console.log('Successfully processed and added new learning.');

  } catch (error) {
    console.error('Error processing new article:', error);
  }
}

processNewArticle();
