from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import datetime

from .parser import parse_raw_job
from .schemas import ParsedJobRecord, RawJobRecord, make_fallback_key


CATEGORY_TO_TERMS = {
    "LLM 基础能力": {"LLM", "Prompt", "Function Calling", "Tool Calling", "OpenAI SDK", "Anthropic"},
    "RAG / 知识库": {"RAG", "Embedding", "向量数据库", "Elasticsearch", "PostgreSQL"},
    "Agent / Workflow 编排": {"AI Agent", "Agent", "Workflow", "MCP", "LangGraph", "AutoGen", "CrewAI"},
    "Agent 应用框架": {"LangChain", "Dify", "Coze", "LlamaIndex"},
    "工程落地能力": {"Python", "FastAPI", "Node.js", "Redis"},
    "推理部署与系统工程": {"vLLM", "Ollama", "Docker", "Kubernetes", "推理", "评测", "多模态"},
}


def dedupe_raw_jobs(records: list[RawJobRecord]) -> list[RawJobRecord]:
    seen: set[str] = set()
    deduped: list[RawJobRecord] = []
    for record in records:
        key = record.job_id or make_fallback_key(record.job_title, record.company_name, record.salary_text, record.job_url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def categories_for_terms(terms: list[str]) -> list[str]:
    categories: list[str] = []
    term_set = set(terms)
    for category, known_terms in CATEGORY_TO_TERMS.items():
        if term_set & known_terms:
            categories.append(category)
    return categories


def parse_jobs(records: list[RawJobRecord]) -> list[ParsedJobRecord]:
    parsed: list[ParsedJobRecord] = []
    for record in dedupe_raw_jobs(records):
        item = parse_raw_job(record)
        parsed.append(replace(item, categories=categories_for_terms(item.skill_terms)))
    return parsed


def count_skill_terms(records: list[ParsedJobRecord]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.skill_terms)
    return counter


def count_categories(records: list[ParsedJobRecord]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for record in records:
        counter.update(record.categories)
    return counter


def learning_recommendations(category_counts: Counter[str]) -> list[str]:
    ordered = [category for category, _ in category_counts.most_common()]
    recommendations: list[str] = []
    for category in ordered:
        if category == "工程落地能力":
            recommendations.append("优先补 Python / API 服务化 / 数据处理基础，把 Agent 能力落到真实工程里。")
        elif category == "RAG / 知识库":
            recommendations.append("系统学习 RAG、Embedding、向量检索与知识库构建，这是大多数 AI 应用岗位的共通底座。")
        elif category == "Agent / Workflow 编排":
            recommendations.append("重点补 Agent 编排：Tool Calling、MCP、多步工作流与 LangGraph/AutoGen 类框架。")
        elif category == "Agent 应用框架":
            recommendations.append("选 1~2 个热门框架做项目：LangChain、Dify、Coze 或 LlamaIndex。")
        elif category == "推理部署与系统工程":
            recommendations.append("补部署与推理服务：Docker、Kubernetes、vLLM/Ollama，提升模型系统化落地能力。")
        elif category == "LLM 基础能力":
            recommendations.append("夯实 LLM 基础：Prompt、上下文管理、函数调用和模型接入 SDK。")
    return recommendations


def _representative_quotes(records: list[ParsedJobRecord]) -> dict[str, list[str]]:
    examples: dict[str, list[str]] = {}
    for category in CATEGORY_TO_TERMS:
        snippets: list[str] = []
        for record in records:
            if category not in record.categories:
                continue
            snippet = (record.requirement_text or record.bonus_text).replace("\n", " ").strip()
            if snippet and snippet not in snippets:
                snippets.append(f"- {record.job_title} / {record.company_name}: {snippet[:120]}")
            if len(snippets) == 3:
                break
        examples[category] = snippets
    return examples


def render_report(records: list[ParsedJobRecord]) -> str:
    term_counts = count_skill_terms(records)
    category_counts = count_categories(records)
    recommendations = learning_recommendations(category_counts)
    examples = _representative_quotes(records)
    lines = [
        "# 北京 AI Agent 岗位学习方向报告",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 去重后岗位数：{len(records)}",
        "",
        "## 高频技能词 Top 15",
        "",
    ]

    for term, count in term_counts.most_common(15):
        lines.append(f"- {term}: {count}")

    lines.extend(["", "## 高频学习方向", ""])
    for category, count in category_counts.most_common():
        lines.append(f"- {category}: {count}")

    lines.extend(["", "## 学习建议", ""])
    for item in recommendations:
        lines.append(f"- {item}")

    lines.extend(["", "## 代表性岗位摘录", ""])
    for category, snippets in examples.items():
        if not snippets:
            continue
        lines.append(f"### {category}")
        lines.extend(snippets)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_roadmap(records: list[ParsedJobRecord]) -> str:
    term_counts = count_skill_terms(records)
    category_counts = count_categories(records)
    lines = [
        "# 北京 AI Agent 技术岗学习 Roadmap",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 样本岗位数：{len(records)}",
        "",
        "## 市场信号",
        "",
    ]
    for term, count in term_counts.most_common(10):
        lines.append(f"- {term}: {count}")

    lines.extend(
        [
            "",
            "## 入门",
            "",
            "- 先补 Python、Linux、Git、HTTP/JSON、基础 SQL，把真实工程开发链路打通。",
            "- 夯实 LLM 基础：Prompt、上下文管理、函数/工具调用、模型 API 接入。",
            "- 入门 RAG：Embedding、向量检索、知识切分、召回与重排的基本概念。",
            "",
            "## 进阶",
            "",
            "- 重点补 Agent / Workflow 编排，优先学习 LangGraph、MCP、多步任务拆解与状态管理。",
            "- 选 1~2 个热门框架做深：LangChain、Dify、Coze、LlamaIndex。",
            "- 补部署与系统工程：Docker、Kubernetes、推理服务、评测流程、多模态接入。",
            "",
            "## 作品集",
            "",
            "- 做一个企业知识库 Agent：包含 RAG、向量检索、工具调用和对话界面。",
            "- 做一个多步骤 Workflow Agent：支持任务规划、执行、重试、日志与评测。",
            "- 做一个可部署 Demo：提供 API、容器化、README、架构图和效果评估指标。",
            "",
            "## 面试准备",
            "",
            "- 准备 3 段项目故事：问题背景、架构方案、效果指标、踩坑与权衡。",
            "- 高频题重点准备：RAG 方案设计、Agent 状态管理、Tool Calling、MCP、Prompt 评测。",
            "- 工程面要能讲清：服务化、缓存、消息队列、并发、容器化部署、故障定位。",
            "",
            "## 对应市场优先级",
            "",
        ]
    )
    for category, count in category_counts.most_common():
        lines.append(f"- {category}: {count}")
    return "\n".join(lines).rstrip() + "\n"
