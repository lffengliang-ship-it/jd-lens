from __future__ import annotations

import re
from collections import OrderedDict

from .config import FOCUS_KEYWORDS
from .schemas import ParsedJobRecord, RawJobRecord


HEADING_ALIASES = {
    "岗位要求": ["岗位要求", "任职要求", "职位要求", "技术要求", "技能要求", "任职条件", "资格要求", "任职资格"],
    "岗位职责": ["岗位职责", "职责描述", "工作职责"],
    "职位描述": ["职位描述", "岗位描述", "工作内容", "工作描述"],
    "加分项": ["加分项", "优先条件", "优先考虑"],
}

PREFERRED_REQUIREMENT_HEADINGS = ["岗位要求", "职位描述", "岗位职责"]
BONUS_HEADINGS = ["加分项"]

SKILL_PATTERNS: OrderedDict[str, list[re.Pattern[str]]] = OrderedDict(
    {
        "AI Agent": [re.compile(r"\bAI\s*Agent\b", re.I)],
        "Agent": [re.compile(r"\bagent\b", re.I), re.compile(r"智能体")],
        "LLM": [re.compile(r"\bLLM\b", re.I), re.compile(r"大模型")],
        "RAG": [re.compile(r"\bRAG\b", re.I), re.compile(r"检索增强"), re.compile(r"知识库")],
        "Workflow": [re.compile(r"\bWorkflow\b", re.I), re.compile(r"工作流"), re.compile(r"编排")],
        "Prompt": [re.compile(r"\bPrompt\b", re.I), re.compile(r"提示词")],
        "Function Calling": [re.compile(r"Function Calling", re.I)],
        "Tool Calling": [re.compile(r"Tool Calling", re.I)],
        "MCP": [re.compile(r"\bMCP\b", re.I)],
        "LangChain": [re.compile(r"\bLangChain\b", re.I)],
        "LangGraph": [re.compile(r"\bLangGraph\b", re.I)],
        "AutoGen": [re.compile(r"\bAutoGen\b", re.I)],
        "CrewAI": [re.compile(r"\bCrewAI\b", re.I)],
        "Dify": [re.compile(r"\bDify\b", re.I)],
        "Coze": [re.compile(r"\bCoze\b", re.I)],
        "LlamaIndex": [re.compile(r"\bLlamaIndex\b", re.I)],
        "OpenAI SDK": [re.compile(r"OpenAI\s*SDK", re.I)],
        "Anthropic": [re.compile(r"\bAnthropic\b", re.I)],
        "vLLM": [re.compile(r"\bvLLM\b", re.I)],
        "Ollama": [re.compile(r"\bOllama\b", re.I)],
        "Python": [re.compile(r"\bPython\b", re.I)],
        "FastAPI": [re.compile(r"\bFastAPI\b", re.I)],
        "Node.js": [re.compile(r"\bNode\.?js\b", re.I)],
        "Docker": [re.compile(r"\bDocker\b", re.I)],
        "Kubernetes": [re.compile(r"\bKubernetes\b", re.I), re.compile(r"\bK8s\b", re.I)],
        "Redis": [re.compile(r"\bRedis\b", re.I)],
        "PostgreSQL": [re.compile(r"\bPostgreSQL\b", re.I), re.compile(r"\bpgvector\b", re.I)],
        "向量数据库": [re.compile(r"向量数据库"), re.compile(r"\bMilvus\b", re.I)],
        "Elasticsearch": [re.compile(r"\bElasticsearch\b", re.I)],
        "Embedding": [re.compile(r"\bEmbedding\b", re.I)],
        "推理": [re.compile(r"推理")],
        "评测": [re.compile(r"评测"), re.compile(r"evaluation", re.I)],
        "多模态": [re.compile(r"多模态")],
    }
)


def normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _canonical_heading(line: str) -> str | None:
    candidate = re.sub(r"[：:\-—\s]+$", "", line.strip())
    for canonical, aliases in HEADING_ALIASES.items():
        if candidate in aliases:
            return canonical
    return None


def _match_inline_heading(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    for canonical, aliases in HEADING_ALIASES.items():
        for alias in aliases:
            if stripped.startswith(alias):
                remainder = stripped[len(alias) :].lstrip("：: -—")
                if remainder:
                    return canonical, remainder.strip()
    return None


def split_sections(text: str) -> OrderedDict[str, str]:
    sections: OrderedDict[str, list[str]] = OrderedDict()
    current: str | None = None

    for raw_line in normalize_text(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _canonical_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        inline_heading = _match_inline_heading(line)
        if inline_heading:
            current, remainder = inline_heading
            sections.setdefault(current, []).append(remainder)
            continue
        if current is None:
            sections.setdefault("全文", []).append(line)
        else:
            sections[current].append(line)

    return OrderedDict((key, "\n".join(lines).strip()) for key, lines in sections.items() if lines)


def extract_requirement_text(text: str) -> str:
    sections = split_sections(text)
    for heading in PREFERRED_REQUIREMENT_HEADINGS:
        content = sections.get(heading, "")
        if content:
            return content
    return normalize_text(text)


def extract_bonus_text(text: str) -> str:
    sections = split_sections(text)
    for heading in BONUS_HEADINGS:
        content = sections.get(heading, "")
        if content:
            return content
    return ""


def extract_skill_terms(text: str) -> list[str]:
    haystack = normalize_text(text)
    found: list[str] = []
    for term, patterns in SKILL_PATTERNS.items():
        if any(pattern.search(haystack) for pattern in patterns):
            found.append(term)
    return found


def extract_matched_keywords(text: str) -> list[str]:
    haystack = normalize_text(text)
    matches: list[str] = []
    for keyword in FOCUS_KEYWORDS:
        if keyword.lower() in haystack.lower():
            matches.append(keyword)
    return matches


def parse_raw_job(record: RawJobRecord, categories: list[str] | None = None) -> ParsedJobRecord:
    requirement_text = extract_requirement_text(record.description_text)
    bonus_text = extract_bonus_text(record.description_text)
    skills = extract_skill_terms("\n".join([record.job_title, requirement_text, bonus_text, record.description_text]))
    matched_keywords = extract_matched_keywords("\n".join([record.job_title, requirement_text, bonus_text]))
    return ParsedJobRecord(
        job_id=record.job_id,
        job_title=record.job_title,
        company_name=record.company_name,
        job_url=record.job_url,
        keyword=record.keyword,
        requirement_text=requirement_text,
        bonus_text=bonus_text,
        matched_keywords=matched_keywords,
        skill_terms=skills,
        categories=categories or [],
        salary_text=record.salary_text,
        experience_text=record.experience_text,
        education_text=record.education_text,
        crawl_time=record.crawl_time,
    )
