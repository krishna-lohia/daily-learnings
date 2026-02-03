# Today I Learned

A daily learning website featuring insights from [The Daily Brief by Zerodha](https://thedailybrief.zerodha.com).

Every day, one interesting insight about finance, business, or economics—explained in plain English.

Live site: `https://krishna-lohia.github.io/daily-learnings` (default GitHub Pages URL)

## Features

- 📚 Curated learnings from The Daily Brief
- 🔄 New learning automatically added daily
- 📱 Mobile-friendly design
- 🎨 Clean, readable typography

## Setup (Free)

1. Push to GitHub
2. Enable GitHub Pages from Settings → Pages → Source: main branch
3. Enable GitHub Actions (if not already)

The daily update workflow uses a free, heuristic summarizer in `process_new.py`.

## Local Development

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000

## Backfill All Articles (Free)

Run this once to populate `learnings.json` with all available archive items.

```bash
python3 backfill_free.py
```
