from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import datetime

from .parser import parse_raw_job
from .schemas import ParsedJobRecord, RawJobRecord, make_fallback_key


# ── 运营能力分类 ──────────────────────────────────────────
CATEGORY_TO_TERMS = {
    "数据分析能力": {"数据分析", "数据驱动", "AB测试", "SQL", "Tableau", "GrowingIO", "神策"},
    "用户增长能力": {"用户增长", "用户留存", "用户转化", "用户画像", "AARRR", "用户生命周期"},
    "内容运营能力": {"内容策划", "短视频", "公众号", "小红书"},
    "社群/私域能力": {"社群运营", "私域运营", "社区运营"},
    "活动策划能力": {"活动策划", "事件营销"},
    "AI 相关能力": {"AI/大模型", "Prompt", "ChatGPT"},
    "通用能力": {"跨部门协作", "项目管理", "复盘"},
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


def _salary_stats(records: list[ParsedJobRecord]) -> dict:
    """从薪资文本中提取统计信息。"""
    import re
    salaries = []
    for record in records:
        text = record.salary_text or ""
        # 匹配 "15-25K" 或 "15k-25k" 或 "15000-25000"
        match = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*[kK万]?", text)
        if match:
            low = int(match.group(1))
            high = int(match.group(2))
            if high < 100:  # K 为单位
                low *= 1000
                high *= 1000
            salaries.append((low, high))
    if not salaries:
        return {"count": 0}
    avg_low = sum(s[0] for s in salaries) // len(salaries)
    avg_high = sum(s[1] for s in salaries) // len(salaries)
    min_low = min(s[0] for s in salaries)
    max_high = max(s[1] for s in salaries)
    return {
        "count": len(salaries),
        "avg_low": avg_low,
        "avg_high": avg_high,
        "avg_mid": (avg_low + avg_high) // 2,
        "min": min_low,
        "max": max_high,
    }


def _experience_distribution(records: list[ParsedJobRecord]) -> dict[str, int]:
    import re
    dist: dict[str, int] = Counter()
    for record in records:
        text = record.experience_text or ""
        if "不限" in text or not text:
            dist["经验不限"] += 1
        elif "应届" in text:
            dist["应届生"] += 1
        elif "1" in text and ("3" in text or "年" in text):
            match = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*年", text)
            if match:
                dist[f"{match.group(1)}-{match.group(2)}年"] += 1
            else:
                dist["1-3年"] += 1
        elif "3" in text and "5" in text:
            dist["3-5年"] += 1
        elif "5" in text and ("10" in text or "年" in text):
            dist["5-10年"] += 1
        else:
            dist[text.strip() or "其他"] += 1
    return dict(dist)


def _education_distribution(records: list[ParsedJobRecord]) -> dict[str, int]:
    dist: dict[str, int] = Counter()
    for record in records:
        text = record.education_text or ""
        if "不限" in text or not text:
            dist["学历不限"] += 1
        elif "大专" in text:
            dist["大专"] += 1
        elif "本科" in text:
            dist["本科"] += 1
        elif "硕士" in text:
            dist["硕士"] += 1
        elif "博士" in text:
            dist["博士"] += 1
        else:
            dist[text.strip() or "其他"] += 1
    return dict(dist)


def _city_distribution(records: list[ParsedJobRecord]) -> dict[str, int]:
    dist: dict[str, int] = Counter()
    for record in records:
        city = getattr(record, "city", None) or "未知"
        dist[city] += 1
    return dict(dist)


def _representative_quotes(records: list[ParsedJobRecord]) -> dict[str, list[str]]:
    examples: dict[str, list[str]] = {}
    for category in CATEGORY_TO_TERMS:
        snippets: list[str] = []
        for record in records:
            if category not in record.categories:
                continue
            snippet = (record.requirement_text or record.bonus_text).replace("\n", " ").strip()
            if snippet and snippet not in snippets:
                snippets.append(f"- [{record.city}] {record.job_title} / {record.company_name}: {snippet[:150]}")
            if len(snippets) == 3:
                break
        examples[category] = snippets
    return examples


def resume_suggestions(category_counts: Counter[str], term_counts: Counter[str]) -> list[str]:
    """根据分析结果生成简历优化建议。"""
    suggestions: list[str] = []
    top_categories = [cat for cat, _ in category_counts.most_common(5)]
    top_terms = [term for term, _ in term_counts.most_common(10)]

    if "数据分析能力" in top_categories:
        suggestions.append("简历中突出数据成果：用具体数字描述你运营过的项目效果（如「DAU提升30%」「转化率从2%提升到5%」），这比堆砌技能更有说服力。")

    if "用户增长能力" in top_categories:
        suggestions.append("体现增长思维：写清楚你是如何设计增长实验、如何定义北极星指标、如何通过AARRR漏斗分析找到增长点的。")

    if "内容运营能力" in top_categories:
        suggestions.append("展示内容作品：附上你策划过的爆款内容链接或数据截图，比文字描述有力10倍。如果目标公司重视小红书/抖音，准备对应平台的作品集。")

    if "社群/私域能力" in top_categories:
        suggestions.append("量化社群运营成果：如「管理20个社群共5000人」「社群月活跃度60%」「社群贡献GMV占比30%」等。")

    if "AI 相关能力" in top_categories:
        suggestions.append("重点展示 AI 实践经验：即使是个人项目也行，比如用 ChatGPT/AIGC 工具优化内容生产流程、用数据分析+AI模型做用户分群等。这块是差异化竞争力。")

    if "活动策划能力" in top_categories:
        suggestions.append("列出代表性活动案例：活动主题、你的角色、活动效果数据（参与人数、转化率、ROI等）。")

    suggestions.append(f"建议简历中优先突出这些高频关键词：{', '.join(top_terms[:6])}，它们出现在大量JD中，HR和ATS系统会优先匹配。")

    return suggestions


def render_report(records: list[ParsedJobRecord]) -> str:
    term_counts = count_skill_terms(records)
    category_counts = count_categories(records)
    salary = _salary_stats(records)
    exp_dist = _experience_distribution(records)
    edu_dist = _education_distribution(records)
    city_dist = _city_distribution(records)
    examples = _representative_quotes(records)
    suggestions = resume_suggestions(category_counts, term_counts)

    lines = [
        "# AI 运营 / 用户运营岗位 JD 分析报告",
        "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 去重后岗位数：{len(records)}",
        "",
    ]

    # 薪资概况
    if salary["count"] > 0:
        lines.extend([
            "## 薪资概况",
            "",
            f"- 有效薪资样本：{salary['count']} 条",
            f"- 平均薪资范围：{salary['avg_low']:,} - {salary['avg_high']:,} 元/月",
            f"- 整体薪资范围：{salary['min']:,} - {salary['max']:,} 元/月",
            "",
        ])

    # 经验要求分布
    if exp_dist:
        lines.extend(["## 经验要求分布", ""])
        for exp, count in sorted(exp_dist.items(), key=lambda x: -x[1]):
            lines.append(f"- {exp}: {count} 个岗位")
        lines.append("")

    # 学历要求分布
    if edu_dist:
        lines.extend(["## 学历要求分布", ""])
        for edu, count in sorted(edu_dist.items(), key=lambda x: -x[1]):
            lines.append(f"- {edu}: {count} 个岗位")
        lines.append("")

    # 城市分布
    if city_dist:
        lines.extend(["## 城市分布", ""])
        for city, count in sorted(city_dist.items(), key=lambda x: -x[1]):
            lines.append(f"- {city}: {count} 个岗位")
        lines.append("")

    # 高频能力词
    lines.extend(["## 高频能力词 Top 20", ""])
    for term, count in term_counts.most_common(20):
        lines.append(f"- {term}: {count}")

    # 能力方向分布
    lines.extend(["", "## 能力方向分布", ""])
    for category, count in category_counts.most_common():
        lines.append(f"- {category}: {count}")

    # 简历优化建议
    lines.extend(["", "## 简历优化建议", ""])
    for item in suggestions:
        lines.append(f"- {item}")

    # 代表性岗位摘录
    lines.extend(["", "## 代表性岗位摘录", ""])
    for category, snippets in examples.items():
        if not snippets:
            continue
        lines.append(f"### {category}")
        lines.extend(snippets)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
