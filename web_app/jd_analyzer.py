"""从 OCR 识别的文本中解析岗位信息并分析。"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path


@dataclass
class JobInfo:
    """解析后的岗位信息。"""
    id: str = ""
    job_title: str = ""
    salary: str = ""
    city: str = ""
    experience: str = ""
    education: str = ""
    company: str = ""
    company_size: str = ""
    description: str = ""
    section_duties: str = ""      # 岗位职责
    section_requirements: str = "" # 岗位要求
    section_bonus: str = ""       # 加分项
    section_other: str = ""       # 其他描述
    skills: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    raw_text: str = ""
    created_at: str = ""
    source: str = ""


# ── 技能词库（同 parser.py）──────────────────────────────
SKILL_PATTERNS: OrderedDict[str, list[re.Pattern[str]]] = OrderedDict({
    "数据分析": [re.compile(r"数据分析"), re.compile(r"\bSQL\b", re.I), re.compile(r"\bExcel\b", re.I), re.compile(r"数据看板")],
    "数据驱动": [re.compile(r"数据驱动"), re.compile(r"指标"), re.compile(r"漏斗"), re.compile(r"转化率")],
    "AB测试": [re.compile(r"\bAB\b.*测试", re.I), re.compile(r"A/B测试", re.I)],
    "用户增长": [re.compile(r"用户增长"), re.compile(r"增长"), re.compile(r"拉新"), re.compile(r"获客")],
    "用户留存": [re.compile(r"留存"), re.compile(r"促活"), re.compile(r"召回"), re.compile(r"唤醒")],
    "用户转化": [re.compile(r"转化"), re.compile(r"付费转化"), re.compile(r"变现")],
    "用户画像": [re.compile(r"用户画像"), re.compile(r"用户分层"), re.compile(r"分群")],
    "AARRR": [re.compile(r"AARRR", re.I), re.compile(r"海盗模型")],
    "用户生命周期": [re.compile(r"生命周期"), re.compile(r"LTV")],
    "内容策划": [re.compile(r"内容策划"), re.compile(r"内容运营"), re.compile(r"文案")],
    "短视频": [re.compile(r"短视频"), re.compile(r"抖音"), re.compile(r"视频号")],
    "公众号": [re.compile(r"公众号"), re.compile(r"微信公众平台")],
    "小红书": [re.compile(r"小红书"), re.compile(r"种草")],
    "社群运营": [re.compile(r"社群运营"), re.compile(r"社群管理"), re.compile(r"微信群")],
    "私域运营": [re.compile(r"私域"), re.compile(r"私域流量"), re.compile(r"企微"), re.compile(r"企业微信")],
    "社区运营": [re.compile(r"社区运营"), re.compile(r"社区管理")],
    "活动策划": [re.compile(r"活动策划"), re.compile(r"活动运营"), re.compile(r"裂变活动")],
    "事件营销": [re.compile(r"事件营销"), re.compile(r"热点营销")],
    "Python": [re.compile(r"\bPython\b", re.I)],
    "SQL": [re.compile(r"\bSQL\b", re.I)],
    "AI/大模型": [re.compile(r"\bAI\b"), re.compile(r"人工智能"), re.compile(r"大模型"), re.compile(r"\bLLM\b", re.I), re.compile(r"\bAIGC\b", re.I)],
    "Prompt": [re.compile(r"\bPrompt\b", re.I), re.compile(r"提示词")],
    "ChatGPT": [re.compile(r"ChatGPT", re.I), re.compile(r"智能对话")],
    "跨部门协作": [re.compile(r"跨部门"), re.compile(r"协作")],
    "项目管理": [re.compile(r"项目管理"), re.compile(r"\bPMP\b", re.I)],
    "复盘": [re.compile(r"复盘")],
})

# ── 能力分类 ──
CATEGORY_TO_TERMS = {
    "数据分析能力": {"数据分析", "数据驱动", "AB测试", "SQL"},
    "用户增长能力": {"用户增长", "用户留存", "用户转化", "用户画像", "AARRR", "用户生命周期"},
    "内容运营能力": {"内容策划", "短视频", "公众号", "小红书"},
    "社群/私域能力": {"社群运营", "私域运营", "社区运营"},
    "活动策划能力": {"活动策划", "事件营销"},
    "AI 相关能力": {"AI/大模型", "Prompt", "ChatGPT"},
    "通用能力": {"跨部门协作", "项目管理", "复盘"},
}

# ── 薪资提取 ──
SALARY_PATTERNS = [
    re.compile(r"(\d{1,2}[-~—]\d{1,2}[Kk万])"),
    re.compile(r"(\d{4,}[-~—]\d{4,})"),
]

# ── 经验提取 ──
EXPERIENCE_PATTERNS = [r"经验不限", r"应届生", r"\d+\s*-\s*\d+\s*年", r"\d+\s*年(?:以上)?"]

# ── 学历提取 ──
EDUCATION_PATTERNS = [r"初中及以下", r"中专/中技", r"高中", r"大专", r"本科", r"硕士", r"博士", r"学历不限"]

# ── 城市提取 ──
CITY_NAMES = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "武汉", "西安", "苏州", "长沙", "厦门", "重庆", "天津", "郑州"]


def _extract_by_patterns(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def extract_skills(text: str) -> list[str]:
    """从文本中提取匹配的技能词。"""
    found = []
    for term, patterns in SKILL_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            found.append(term)
    return found


def categorize_skills(skills: list[str]) -> list[str]:
    """将技能词归入能力分类。"""
    categories = []
    skill_set = set(skills)
    for category, terms in CATEGORY_TO_TERMS.items():
        if skill_set & terms:
            categories.append(category)
    return categories


def parse_jd_text(text: str, source: str = "screenshot") -> JobInfo:
    """从 OCR 识别的文本中解析结构化岗位信息。"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return JobInfo(raw_text=text, source=source, created_at=datetime.now().isoformat(timespec="seconds"))

    # 尝试从文本中提取各字段
    combined = "\n".join(lines)

    # 岗位名称：通常是第一行或前几行中的关键内容
    job_title = ""
    for line in lines[:5]:
        # 排除纯数字、薪资行等
        if re.match(r"^[\dKk\-~—·]+$", line):
            continue
        if re.search(r"\d+[-~—]\d+[Kk]", line) and len(line) < 15:
            continue
        if "BOSS" in line or "zhipin" in line.lower() or "直聘" in line:
            continue
        if len(line) > 3 and len(line) < 40:
            job_title = line
            break
    if not job_title and lines:
        job_title = lines[0][:30]

    # 薪资
    salary = ""
    for p in SALARY_PATTERNS:
        m = p.search(combined)
        if m:
            salary = m.group(1)
            break

    # 城市
    city = ""
    for c in CITY_NAMES:
        if c in combined:
            city = c
            break

    # 经验
    experience = _extract_by_patterns(combined, EXPERIENCE_PATTERNS)

    # 学历
    education = _extract_by_patterns(combined, EDUCATION_PATTERNS)

    # 公司名：通常在岗位名称后面，或包含"有限公司""科技"等
    company = ""
    company_pattern = re.compile(r"([\u4e00-\u9fa5]+(?:有限公司|科技|网络|信息|数据|集团|公司))")
    m = company_pattern.search(combined)
    if m:
        company = m.group(1)

    # 公司规模
    size_match = re.search(r"(\d+[-~—]\d+人|\d+人以上|少于\d+人)", combined)
    company_size = size_match.group(1) if size_match else ""

    # 技能词
    skills = extract_skills(combined)
    categories = categorize_skills(skills)

    # ── 分段提取：职责 / 要求 / 加分项 ──
    section_duties = ""
    section_requirements = ""
    section_bonus = ""
    section_other = ""

    duties_headings = ["岗位职责", "职责描述", "工作职责", "职位描述", "岗位描述", "工作内容", "工作描述", "职责"]
    req_headings = ["岗位要求", "任职要求", "职位要求", "技术要求", "技能要求", "任职条件", "资格要求", "任职资格", "要求"]
    bonus_headings = ["加分项", "优先条件", "优先考虑", "优先"]

    current_section = None
    other_lines = []
    duties_lines = []
    req_lines = []
    bonus_lines = []

    for line in lines:
        stripped = line.strip()
        # 去掉末尾的冒号/破折号
        cleaned_heading = re.sub(r"[：:\-—\s]+$", "", stripped)

        if cleaned_heading in duties_headings:
            current_section = "duties"
            continue
        elif cleaned_heading in req_headings:
            current_section = "req"
            continue
        elif cleaned_heading in bonus_headings:
            current_section = "bonus"
            continue

        # 检查行内标题（如 "岗位职责：1. xxx"）
        matched_inline = False
        for heading_list, section_name in [(duties_headings, "duties"), (req_headings, "req"), (bonus_headings, "bonus")]:
            for h in heading_list:
                if stripped.startswith(h):
                    remainder = stripped[len(h):].lstrip("：: -—")
                    if remainder:
                        current_section = section_name
                        if section_name == "duties":
                            duties_lines.append(remainder)
                        elif section_name == "req":
                            req_lines.append(remainder)
                        elif section_name == "bonus":
                            bonus_lines.append(remainder)
                    else:
                        current_section = section_name
                    matched_inline = True
                    break
            if matched_inline:
                break
        if matched_inline:
            continue

        # 归入当前段落
        if current_section == "duties":
            duties_lines.append(stripped)
        elif current_section == "req":
            req_lines.append(stripped)
        elif current_section == "bonus":
            bonus_lines.append(stripped)
        else:
            other_lines.append(stripped)

    section_duties = "\n".join(duties_lines) if duties_lines else ""
    section_requirements = "\n".join(req_lines) if req_lines else ""
    section_bonus = "\n".join(bonus_lines) if bonus_lines else ""
    section_other = "\n".join(other_lines) if other_lines else ""

    return JobInfo(
        id=datetime.now().strftime("%Y%m%d%H%M%S"),
        job_title=job_title,
        salary=salary,
        city=city,
        experience=experience,
        education=education,
        company=company,
        company_size=company_size,
        description=combined,
        section_duties=section_duties,
        section_requirements=section_requirements,
        section_bonus=section_bonus,
        section_other=section_other,
        skills=skills,
        categories=categories,
        raw_text=text,
        created_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
    )


# ── 数据存储 ──────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
JOBS_FILE = DATA_DIR / "collected_jobs.json"


def save_job(job: JobInfo) -> None:
    """保存一个岗位到本地 JSON 文件。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    jobs = load_all_jobs()
    jobs.append(asdict(job))
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def load_all_jobs() -> list[dict]:
    """加载所有已保存的岗位。"""
    if not JOBS_FILE.exists():
        return []
    return json.loads(JOBS_FILE.read_text(encoding="utf-8"))


def delete_job(job_id: str) -> None:
    """删除指定岗位。"""
    jobs = load_all_jobs()
    jobs = [j for j in jobs if j.get("id") != job_id]
    JOBS_FILE.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 报告生成 ──────────────────────────────────────────────
def generate_report() -> str:
    """根据所有已收集的岗位生成分析报告。"""
    jobs = load_all_jobs()
    if not jobs:
        return "还没有收集任何岗位数据，请先添加一些截图。"

    # 统计
    all_skills: Counter = Counter()
    all_categories: Counter = Counter()
    salaries = []
    cities: Counter = Counter()

    for job in jobs:
        all_skills.update(job.get("skills", []))
        all_categories.update(job.get("categories", []))
        cities[job.get("city", "未知")] += 1

        sal = job.get("salary", "")
        m = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*[Kk万]?", sal)
        if m:
            low, high = int(m.group(1)), int(m.group(2))
            if high < 100:
                low *= 1000
                high *= 1000
            salaries.append((low, high))

    lines = [
        f"# AI 运营岗位 JD 分析报告",
        f"",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 已收集岗位数：{len(jobs)}",
        f"",
    ]

    # 薪资
    if salaries:
        avg_low = sum(s[0] for s in salaries) // len(salaries)
        avg_high = sum(s[1] for s in salaries) // len(salaries)
        lines.extend([
            "## 薪资概况",
            "",
            f"- 样本数：{len(salaries)}",
            f"- 平均范围：{avg_low:,} - {avg_high:,} 元/月",
            f"- 最低：{min(s[0] for s in salaries):,}",
            f"- 最高：{max(s[1] for s in salaries):,}",
            "",
        ])

    # 城市
    if cities:
        lines.extend(["## 城市分布", ""])
        for city, count in cities.most_common():
            lines.append(f"- {city}: {count}")
        lines.append("")

    # 高频技能
    lines.extend(["## 高频能力词", ""])
    for term, count in all_skills.most_common(20):
        bar = "█" * count
        lines.append(f"- {term}: {count} {bar}")

    # 能力方向
    lines.extend(["", "## 能力方向分布", ""])
    for cat, count in all_categories.most_common():
        lines.append(f"- {cat}: {count}")

    # 简历建议
    lines.extend(["", "## 简历优化建议", ""])
    top_skills = [s for s, _ in all_skills.most_common(8)]
    top_cats = [c for c, _ in all_categories.most_common(3)]

    suggestions = []
    if "数据分析能力" in top_cats:
        suggestions.append("简历中突出数据成果：用具体数字描述项目效果（如「DAU提升30%」「转化率从2%提升到5%」）。")
    if "用户增长能力" in top_cats:
        suggestions.append("体现增长思维：写清楚你如何设计增长实验、定义北极星指标、通过AARRR漏斗找增长点。")
    if "内容运营能力" in top_cats:
        suggestions.append("展示内容作品：附上爆款内容链接或数据截图，比文字描述有力10倍。")
    if "社群/私域能力" in top_cats:
        suggestions.append("量化社群运营成果：如「管理20个社群共5000人」「社群月活60%」「贡献GMV占比30%」。")
    if "AI 相关能力" in top_cats:
        suggestions.append("重点展示 AI 实践：用 ChatGPT/AIGC 优化内容生产、用 AI 做用户分群等，这是差异化竞争力。")

    if top_skills:
        suggestions.append(f"建议简历中优先突出这些关键词：{', '.join(top_skills[:6])}。")

    for s in suggestions:
        lines.append(f"- {s}")

    return "\n".join(lines)
