# JD Lens — Understand the Market, Bridge the Gap, Land the Job

> Collect target job JDs via screenshots → AI analyzes market demand → Compare with your resume → Get actionable improvement paths

## The Problem

When job hunting, you might wonder:
- What kind of person do target roles actually want?
- Which skills are must-haves vs. differentiators?
- Where does your resume fall short, and how to fix it?
- How do requirements differ across industries or role types?

JD Lens turns vague market demand into **clear data and insights**, then tells you **exactly how to bridge the gap**.

## Who It's For

Job seekers targeting Operations / AI Operations / User Operations / Product Operations / Community Operations roles.

## Core Features

| Feature | Description |
|---------|-------------|
| 📸 Screenshot JD Collection | Browse job sites, screenshot JDs, Ctrl+V paste to auto-recognize and parse |
| 🔍 Structured Parsing | Auto-extract job title, salary, duties, requirements, bonus items; 30+ ops skill tags |
| 📊 Market Analysis Report | AI output: talent demand profile, baseline vs. differentiator skills, salary landscape, cross-direction comparison |
| 💡 Resume Optimization Advice | AI output: match score, gap analysis, improvement priority, resume rewrite suggestions, action plan |
| 🔒 Resume Desensitization | Auto-mask name/phone/email/WeChat/ID before uploading to LLM |

## How It Works

```
1. Start the tool → Open browser
2. Screenshot JD → Ctrl+V paste → Auto OCR + parse
3. Upload resume → Auto desensitize
4. Click "Market Analysis" → Understand what the market wants
5. Click "Resume Optimization" → Know your gaps and how to fix them
```

## Installation & Setup

### Requirements
- macOS (OCR uses built-in Vision framework)
- Python 3.11+

### Install

```bash
git clone https://github.com/your-username/jd-lens.git
cd jd-lens/web_app
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

Open **http://127.0.0.1:5888** in your browser.

### Configure LLM

Click the ⚙️ button in the top right corner:
- **API Key**: Your LLM API key
- **Base URL**: API endpoint (OpenAI official / SiliconFlow / any OpenAI-compatible proxy)
- **Model**: e.g. `gpt-4o`, `claude-sonnet-4-20250514`
- **Provider**: Select `OpenAI` for compatible APIs, `Anthropic` for direct Claude access

> Supports any OpenAI-protocol compatible API (SiliconFlow, DeepSeek, Qwen, etc.) and Anthropic Claude official API.

## Project Structure

```
web_app/
├── app.py                  # Flask backend (routes + APIs)
├── ocr_engine.py           # macOS Vision OCR engine
├── jd_analyzer.py          # JD structured parsing + skill dictionary + local storage
├── resume_parser.py        # Resume parser (PDF/Word/Image)
├── resume_desensitizer.py  # Resume desensitization module
├── llm_client.py           # Unified LLM client + Prompt builder
├── static/
│   └── index.html          # Frontend UI
└── data/                   # Local data storage (auto-generated)
```

## Architecture

```
Screenshot → [macOS Vision OCR] → Raw text
                                     ↓
                           [Rule engine: regex + dictionary] → Structured fields
                                     ↓
                               [Local JSON storage]
                                     ↓
                  ┌──────────────────┴──────────────────┐
                  ↓                                     ↓
         [LLM: Market Analysis]          [LLM: Resume Optimization]
         Input: Structured JD data       Input: Desensitized resume + JD data
         Output: Demand profile          Output: Gap analysis + action plan
```

- **OCR Layer**: macOS native Vision framework, offline Chinese/English recognition
- **Parsing Layer**: Pure rule engine (regex + keyword dictionary), zero API cost
- **Analysis Layer**: Cloud LLM for insights and personalized advice

## Why Screenshots, Not Scrapers

Job sites like Boss Zhipin enforce strict anti-bot measures. Scraping can get your account banned and hurt your job search. JD Lens uses **screenshots + OCR**:
- Zero risk of account bans
- You're already browsing job sites — screenshotting is effortless
- All data stays local, never uploaded to third parties

## Data Security

- All JD data and resumes stored in **local JSON files**, never uploaded to any server
- Resumes are **auto-desensitized** on upload (name, phone, email, WeChat, ID card)
- Only desensitized resume text and JD data are sent to the cloud LLM during analysis
- LLM API keys are configured by the user; the tool never collects any keys

## License

MIT