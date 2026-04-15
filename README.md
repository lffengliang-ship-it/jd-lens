# bossJD

> Local crawler + analysis toolkit for researching **AI / Agent-related technical jobs on BOSS 直聘**.

一个面向个人求职研究场景的本地工具：  
**抓取岗位 → 过滤技术岗 → 结构化分析 → 生成学习报告与 roadmap**。

> Current default configuration targets **Beijing**.  
> 当前默认配置仍以 **北京** 为主，多城市参数化可以后续扩展。

---

## Why this project

如果你在看 AI Agent、LLM、RAG、Workflow、Prompt Engineering 相关岗位，最大的痛点通常不是“找不到职位”，而是：

- 职位描述非常散，不成体系
- 技术岗与非技术岗混在一起
- 同一个方向在不同公司描述方式不同
- 很难从大量 JD 里总结出真正值得补的能力栈

`bossJD` 的目标就是把这个过程工程化：

1. **批量采集** BOSS 岗位
2. **过滤** 出 AI 相关技术岗
3. **抽取** 技能词、要求、加分项
4. **输出** CSV、学习报告和学习 roadmap

---

## Features

- Search BOSS job listings by keyword
- Crawl job detail pages with a local browser session
- Filter for technical AI-related roles
- Save raw crawl results as JSONL
- Convert raw jobs into structured CSV
- Generate:
  - a market-driven learning report
  - a practical learning roadmap

---

## Current scope

This repository currently focuses on:

- AI / Agent job discovery
- technical-role filtering
- local browser-driven crawling
- rule-based text extraction and reporting

It does **not** currently aim to:

- bypass CAPTCHA or anti-bot protections
- scrape private data without an authenticated local browser session
- provide a hosted service
- promise long-term schema stability for third-party integrations

---

## Project structure

```text
src/                    core source code
tests/                  unit tests
data/raw/               raw JSONL output (git-ignored)
data/processed/         processed CSV output (git-ignored)
reports/                generated markdown reports (git-ignored)
```

---

## Requirements

- Python 3.11+
- A local browser
- `playwright` installed from `requirements.txt`
- For CDP mode: Chrome remote debugging enabled in your local browser

---

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Quick start

### 1) Collect jobs with a standalone Playwright browser

```bash
python -m src.run_collect \
  --keyword "AI Agent" \
  --pages 2
```

### 2) Reuse an already logged-in local Chrome session (recommended for real use)

```bash
python -m src.run_collect \
  --browser-mode cdp \
  --cdp-proxy-url http://127.0.0.1:3456 \
  --keyword "AI Agent" \
  --pages 2 \
  --technical-only \
  --no-wait-for-login
```

### 3) Generate report + roadmap

```bash
python -m src.run_analyze
```

---

## Outputs

### Collection outputs

- `data/raw/jobs.jsonl`
- `data/raw/errors.jsonl`

### Analysis outputs

- `data/processed/jobs.csv`
- `reports/aiagent_beijing_learning_report.md`
- `reports/aiagent_beijing_learning_roadmap.md`

---

## Filtering rules

The current technical-role filter is intended to keep **AI-related engineering roles** and exclude obvious noise.

### Intended exclusions

- product / operations / HR / legal / recruiting roles
- intern / campus / fresh-graduate roles
- generic technical roles with no AI-related signals in title or description

### AI-related signals currently emphasized

- AI / 人工智能 / 大模型 / LLM / AIGC
- Agent / 智能体 / Workflow / MCP
- RAG / Prompt / 多模态
- LangChain / LangGraph / Dify / Coze / LlamaIndex

---

## Testing

```bash
python -m unittest discover -s tests
```

Or:

```bash
make test
```

---

## Known limitations

- The project depends on current page structure; selectors may need updates if BOSS changes its frontend
- The extraction pipeline is primarily rule-based rather than LLM-based
- City configuration is still conservative and currently defaults to Beijing-oriented settings
- Raw crawl quality depends on local browser session state and target page accessibility

---

## Compliance and responsible use

Use this repository responsibly and in accordance with:

- the target platform's terms
- applicable law
- your organization's internal policies

This project is intended for **local research workflows**, not abusive scraping.

---

## License

MIT
