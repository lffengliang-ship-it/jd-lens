# bossJD

A local, repeatable crawler-and-analysis toolkit for researching BOSS 直聘 AI / Agent-related technical jobs.

> Current default configuration targets **Beijing**. Multi-city configuration can be added later.

## What this project does

- Search BOSS job listings by keyword
- Open job detail pages and extract role descriptions
- Filter for technical AI-related roles
- Save raw crawl output as JSONL
- Convert raw records into structured CSV
- Generate a market-driven learning report and roadmap

## Current scope

This repository currently focuses on:

- AI / Agent job discovery
- Technical-role filtering
- Local browser-driven crawling
- Rule-based text extraction and reporting

It does **not** currently aim to:

- bypass CAPTCHA or anti-bot protections
- scrape private data without an authenticated local browser session
- provide a hosted service

## Project structure

```text
src/                    source code
tests/                  unit tests
data/raw/               raw JSONL output (git-ignored)
data/processed/         processed CSV output (git-ignored)
reports/                generated markdown reports (git-ignored)
```

## Requirements

- Python 3.11+
- A local browser
- `playwright` installed from `requirements.txt`
- For CDP mode: Chrome remote debugging enabled in your local browser

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Collection

### 1) Persistent Playwright browser mode

```bash
python -m src.run_collect \
  --keyword "AI Agent" \
  --pages 2
```

### 2) Reuse an already logged-in local Chrome session (CDP mode)

```bash
python -m src.run_collect \
  --browser-mode cdp \
  --cdp-proxy-url http://127.0.0.1:3456 \
  --keyword "AI Agent" \
  --pages 2 \
  --technical-only \
  --no-wait-for-login
```

### Collection outputs

- `data/raw/jobs.jsonl`
- `data/raw/errors.jsonl`

## Analysis

```bash
python -m src.run_analyze
```

### Analysis outputs

- `data/processed/jobs.csv`
- `reports/aiagent_beijing_learning_report.md`
- `reports/aiagent_beijing_learning_roadmap.md`

## Testing

```bash
python -m unittest discover -s tests
```

## Notes on filtering

This project includes a technical-role filter intended to exclude:

- product / operations / HR / legal / recruiting roles
- intern / campus / fresh-graduate roles
- non-AI technical roles without AI-related signals in title or description

## Compliance and responsible use

Use this repository responsibly and in accordance with the target platform's terms, applicable law, and your organization's policies. This project is intended for local research workflows, not abusive scraping.

## License

MIT
