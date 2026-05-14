"""统一 LLM 客户端，支持 OpenAI 和 Claude 协议格式。"""
from __future__ import annotations

import os
from typing import Literal

import requests


class LLMClient:
    """同时支持 OpenAI (GPT) 和 Anthropic (Claude) 的统一调用接口。"""

    PROVIDER_OPENAI = "openai"
    PROVIDER_ANTHROPIC = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        provider: Literal["openai", "anthropic"] | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o",
        temperature: float = 0.3,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        self.provider = provider or self._infer_provider(model)
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model
        self.temperature = temperature

    @staticmethod
    def _infer_provider(model: str) -> str:
        """根据模型名推断 Provider。"""
        claude_models = {"claude", "sonnet", "opus", "haiku", "anthropic"}
        if any(k in model.lower() for k in claude_models):
            return LLMClient.PROVIDER_ANTHROPIC
        return LLMClient.PROVIDER_OPENAI

    def chat(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4096,
    ) -> str:
        """统一的对话接口，自动路由到对应 Provider。"""
        if not self.api_key:
            raise ValueError("未设置 API Key，请先配置：OPENAI_API_KEY 或传入 api_key 参数")

        if self.provider == self.PROVIDER_ANTHROPIC:
            return self._chat_anthropic(system_prompt, user_content, max_tokens)
        else:
            return self._chat_openai(system_prompt, user_content, max_tokens)

    def _chat_openai(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int,
    ) -> str:
        """调用 OpenAI 兼容接口（OpenAI / 硅基流动 / 其他兼容 API）。"""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _chat_anthropic(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int,
    ) -> str:
        """调用 Anthropic Claude 接口（也支持代理 base_url）。"""
        base = self.base_url.rstrip("/")
        # 如果 base_url 不是官方地址，用 /v1/messages 路径（兼容代理）
        if "anthropic.com" in base:
            url = f"{base}/v1/messages"
        else:
            # 第三方代理：走 OpenAI 兼容协议更稳定，切换为 OpenAI 模式调用
            return self._chat_openai(system_prompt, user_content, max_tokens)

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_content},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if not response.ok:
            error_detail = response.text
            raise requests.HTTPError(f"{response.status_code} Error: {error_detail}", response=response)
        data = response.json()
        return data["content"][0]["text"]


def build_market_report_prompt(jobs: list[dict]) -> tuple[str, str]:
    """构建市场分析报告的 system prompt 和 user prompt。"""
    system = """你是一位资深的人力资源分析师，专注互联网运营和AI产品领域。
你正在帮一个求职者看清市场：他想知道目标岗位到底要什么人、什么能力是必须的、什么能力能拉开差距、薪资大概什么水平。
你要像一个内行朋友跟他聊天，用数据和洞察说话，不说空话和废话。

重要规则：如果用户收集的JD涉及多个不同的岗位方向（比如AI运营 vs 用户运营 vs 社群运营）或多个行业（比如电商 vs 知识付费 vs 金融），你必须分方向分别分析，然后再做一个横向对比。不要把不同方向的岗位混在一起笼统总结。

输出严格按以下结构，每个板块都要有实质内容："""

    # 能力词频统计
    from collections import Counter
    skill_counter = Counter()
    for job in jobs:
        skill_counter.update(job.get("skills", []))
    top_skills = skill_counter.most_common(20)

    # 薪资统计
    import re
    salaries = []
    for job in jobs:
        m = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*[Kk万]?", job.get("salary", ""))
        if m:
            low, high = int(m.group(1)), int(m.group(2))
            if high < 100:
                low, high = low * 1000, high * 1000
            salaries.append((low, high))

    salary_stats = ""
    if salaries:
        avg = (sum(s[0] for s in salaries) // len(salaries), sum(s[1] for s in salaries) // len(salaries))
        min_s = min(s[0] for s in salaries)
        max_s = max(s[1] for s in salaries)
        salary_stats = f"薪资范围：{min_s:,} - {max_s:,} 元/月，平均 {avg[0]:,} - {avg[1]:,}（共{len(salaries)}个样本）"
    else:
        salary_stats = "薪资数据样本不足"

    # JD 详细内容（全部给出，让 LLM 能识别方向差异）
    jd_details = []
    for job in jobs[:8]:
        duties = (job.get("section_duties") or job.get("description") or "")[:300]
        reqs = (job.get("section_requirements") or "")[:300]
        bonus = (job.get("section_bonus") or "")[:200]
        jd_details.append(
            f"### {job.get('job_title', '未知岗位')} @ {job.get('company', '')} [{job.get('salary', '')}] [{job.get('city', '')}]\n"
            f"职责：{duties}\n"
            f"要求：{reqs}\n"
            f"加分项：{bonus}"
        )

    # 经验/学历分布
    exp_dist = Counter()
    edu_dist = Counter()
    for job in jobs:
        if job.get("experience"): exp_dist[job["experience"]] += 1
        if job.get("education"): edu_dist[job["education"]] += 1

    exp_summary = "；".join(f"{k}:{v}条" for k, v in exp_dist.most_common()) or "数据不足"
    edu_summary = "；".join(f"{k}:{v}条" for k, v in edu_dist.most_common()) or "数据不足"

    # 自动分组提示：告诉 LLM 数据里可能存在不同方向
    job_titles = [j.get("job_title", "") for j in jobs]
    direction_hint = ""
    unique_titles = set(job_titles)
    if len(unique_titles) > 3:
        direction_hint = "\n【提示】这些岗位标题看起来涉及不同方向，请识别并分组分析。"
    else:
        direction_hint = ""

    user = f"""基于 {len(jobs)} 条目标岗位JD的分析数据：

【能力词频统计】
{chr(10).join(f"  {i+1}. {s} — 出现 {c} 次" for i, (s, c) in enumerate(top_skills))}

【薪资情况】
{salary_stats}

【经验要求分布】{exp_summary}
【学历要求分布】{edu_summary}

【所有岗位列表】
{chr(10).join(f"  - {j.get('job_title', '未知')} @ {j.get('company', '')} [{j.get('salary', '')}] [{j.get('city', '')}]" for j in jobs)}
{direction_hint}

【JD原文节选】
{chr(10).join(jd_details)}

请按以下结构输出（每个板块必须有实质洞察，不要泛泛而谈）：

## 一、岗位方向识别
先看这些JD涉及几个不同的岗位方向（比如AI运营、用户运营、社群运营、内容运营等），明确列出每个方向包含哪些岗位。
如果只有一个方向，直接说明即可。如果有多个方向，后续分析必须分方向展开。

## 二、各方向人才需求画像
按每个方向分别描述（如果只有一个方向就只写一个）：

### 方向A：[方向名称]（N条JD）
用3-5句话描述：这类岗位到底在找什么样的人？最核心的1-2个特质是什么？不是废话，而是真正能区分合格和不合格的标准。

### 方向B：[方向名称]（N条JD）
...

（如果有多个方向，还要加一个**方向对比**：不同方向的核心差异是什么？哪个方向门槛更高？哪个方向机会更多？）

## 三、能力模型：及格线 vs 拉开差距的能力
按每个方向分别列出（如果只有一个方向就只写一个）：

### 方向A：[方向名称]
**及格线能力：**
- XXX（出现N次）：为什么是硬门槛
- ...

**拉开差距的能力：**
- XXX（出现N次）：它能帮你做什么
- ...

### 方向B：[方向名称]
...

（如果有多个方向，还要加一个**方向能力差异对比**：哪个方向的及格线更高？哪个方向的加分项更稀缺？）

## 四、薪资全景
- 整体薪资区间和平均值
- 按经验分段的薪资参考（1-3年 / 3-5年 / 5年以上）
- 大厂 vs 中小厂的薪资差异
- 薪资和哪些能力正相关（哪些能力拿高薪必须具备）
- 如果有多个方向，分别给出各方向的薪资参考

## 五、求职策略建议
- 如果你是应届/1-3年：应该重点补什么、简历怎么写、面试准备什么
- 如果你是3-5年想转型AI运营：转型路径、需要额外证明什么
- 如果你在小厂想跳大厂：大厂额外看重什么、怎么准备
- 如果有多个方向，建议求职者选哪个方向入场、为什么
- 一句话总结：现在入场的最佳策略是什么"""

    return system, user


def build_resume_feedback_prompt(resume_text: str, jobs: list[dict]) -> tuple[str, str]:
    """构建简历优化建议的 system prompt 和 user prompt。"""
    system = """你是一位顶级简历优化专家，专为互联网运营/AI运营岗位求职者提供个性化建议。
你的核心能力：
1. 深度理解运营岗位JD的市场需求
2. 精准识别求职者简历与目标岗位的能力差距
3. 给出可执行的补齐路径，而不是空泛的建议

输出风格：专业、直接、有数据支撑，不说废话。
输出格式：严格按以下结构："""

    # 拼接 JD 要求
    jd_summaries = []
    for job in jobs[:5]:
        duties = (job.get("section_duties") or "")[:300]
        reqs = (job.get("section_requirements") or "")[:300]
        bonus = (job.get("section_bonus") or "")[:200]
        jd_summaries.append(
            f"### {job.get('job_title', '未知岗位')} @ {job.get('company', '')} [{job.get('salary', '')}]\n"
            f"职责：{duties}\n"
            f"要求：{reqs}\n"
            f"加分项：{bonus}"
        )

    user = f"""【我的简历】
{resume_text}

【目标岗位JD（共{len(jobs)}条，节选前{len(jd_summaries)}条）】
{chr(10).join(jd_summaries)}

请按以下结构输出：

## 一、匹配度评估
- 综合匹配打分（0-100）：[分数]
- 一句话结论：[直接指出最大差距在哪]

## 二、差距分析
### 经验层面
（工作经历中缺什么、弱什么）

### 技能层面
（硬技能和软技能上分别差什么）

### 项目经历层面
（有没有拿得出手的、HR会问的项目）

## 三、补齐优先级排序
不要用表格，用列表格式：

**P0（必须补，否则简历被筛）：**
- 缺口方向 → 预计补齐难度 → 可行路径

**P1（建议补，能显著提升竞争力）：**
- ...

**P2（有余力再补，锦上添花）：**
- ...

## 四、简历具体改写建议
### 个人信息/求职意向
（怎么写更吸引）

### 工作经历（逐条）
（每段经历怎么重写，强调什么数据，淡化什么）

### 技能清单
（怎么调整权重，哪些要加，哪些删掉或降优先级）

### 自我总结
（怎么结合JD关键词写）

## 五、下一步行动计划
（本周可以做的3件事，要有具体动作，不是空话）
"""

    return system, user