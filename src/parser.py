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

# ── 运营能力词库 ──────────────────────────────────────────
SKILL_PATTERNS: OrderedDict[str, list[re.Pattern[str]]] = OrderedDict(
    {
        # 数据分析能力
        "数据分析": [re.compile(r"数据分析"), re.compile(r"\bSQL\b", re.I), re.compile(r"\bExcel\b", re.I), re.compile(r"数据看板")],
        "数据驱动": [re.compile(r"数据驱动"), re.compile(r"指标"), re.compile(r"漏斗"), re.compile(r"转化率")],
        "AB测试": [re.compile(r"\bAB\b.*测试", re.I), re.compile(r"A/B测试", re.I), re.compile(r"实验设计")],
        # 用户运营
        "用户增长": [re.compile(r"用户增长"), re.compile(r"增长"), re.compile(r"拉新"), re.compile(r"获客")],
        "用户留存": [re.compile(r"留存"), re.compile(r"促活"), re.compile(r"召回"), re.compile(r"唤醒")],
        "用户转化": [re.compile(r"转化"), re.compile(r"付费转化"), re.compile(r"变现")],
        "用户画像": [re.compile(r"用户画像"), re.compile(r"用户分层"), re.compile(r"分群"), re.compile(r"标签体系")],
        "AARRR": [re.compile(r"AARRR", re.I), re.compile(r"海盗模型"), re.compile(r"增长模型")],
        "用户生命周期": [re.compile(r"生命周期"), re.compile(r"LTV"), re.compile(r"用户旅程")],
        # 内容运营
        "内容策划": [re.compile(r"内容策划"), re.compile(r"内容运营"), re.compile(r"文案")],
        "短视频": [re.compile(r"短视频"), re.compile(r"抖音"), re.compile(r"视频号"), re.compile(r"TikTok", re.I)],
        "公众号": [re.compile(r"公众号"), re.compile(r"微信公众平台")],
        "小红书": [re.compile(r"小红书"), re.compile(r"种草")],
        # 社群运营
        "社群运营": [re.compile(r"社群运营"), re.compile(r"社群管理"), re.compile(r"微信群")],
        "私域运营": [re.compile(r"私域"), re.compile(r"私域流量"), re.compile(r"企微"), re.compile(r"企业微信")],
        "社区运营": [re.compile(r"社区运营"), re.compile(r"社区管理"), re.compile(r"论坛")],
        # 活动运营
        "活动策划": [re.compile(r"活动策划"), re.compile(r"活动运营"), re.compile(r"营销活动"), re.compile(r"裂变活动")],
        "事件营销": [re.compile(r"事件营销"), re.compile(r"热点营销"), re.compile(r"话题营销")],
        # 工具与平台
        "Python": [re.compile(r"\bPython\b", re.I)],
        "SQL": [re.compile(r"\bSQL\b", re.I)],
        "Tableau": [re.compile(r"\bTableau\b", re.I)],
        "GrowingIO": [re.compile(r"GrowingIO", re.I)],
        "神策": [re.compile(r"神策"), re.compile(r"Sensors", re.I)],
        # AI 相关
        "AI/大模型": [re.compile(r"\bAI\b"), re.compile(r"人工智能"), re.compile(r"大模型"), re.compile(r"\bLLM\b", re.I), re.compile(r"\bAIGC\b", re.I)],
        "Prompt": [re.compile(r"\bPrompt\b", re.I), re.compile(r"提示词")],
        "ChatGPT": [re.compile(r"ChatGPT", re.I), re.compile(r"智能对话"), re.compile(r"智能客服")],
        # 通用软技能
        "跨部门协作": [re.compile(r"跨部门"), re.compile(r"协作"), re.compile(r"沟通能力")],
        "项目管理": [re.compile(r"项目管理"), re.compile(r"\bPMP\b", re.I)],
        "复盘": [re.compile(r"复盘"), re.compile(r"总结")],
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
        city=record.city,
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
