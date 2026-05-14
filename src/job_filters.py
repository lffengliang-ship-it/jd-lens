from __future__ import annotations

import re

from .schemas import RawJobRecord


# 排除明显不相关的岗位
EXCLUDE_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"实习",
        r"应届",
        r"校招",
        r"销售经理",
        r"销售总监",
        r"销售代表",
        r"电话销售",
        r"渠道销售",
        r"商务拓展",  # BD 不是我们要的运营
        r"法务",
        r"招聘专员",
        r"财务",
        r"出纳",
        r"行政前台",
        r"保洁",
        r"保安",
        r"司机",
    ]
]

# 岗位标题中必须包含的运营关键词
INCLUDE_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"运营",
        r"增长",
        r"社群",
        r"社区",
        r"内容",
        r"新媒体",
        r"私域",
        r"用户",
        r"活动策划",
        r"品牌",
        r"投放",
        r"直播",
        r"短视频",
        r"KOL",
        r"MCN",
    ]
]

# AI 相关信号词 —— 用于识别 AI 相关运营岗
AI_SIGNAL_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"\bAI\b",
        r"人工智能",
        r"大模型",
        r"\bLLM\b",
        r"\bAIGC\b",
        r"智能体",
        r"生成式",
        r"机器学习",
        r"深度学习",
        r"自然语言",
        r"\bNLP\b",
        r"ChatGPT",
        r"智能",
        r"数字化",
        r"数据驱动",
    ]
]

# 运营核心能力信号词 —— 更宽泛的匹配，只要岗位涉及运营即可
OPERATION_SIGNAL_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"运营",
        r"增长",
        r"留存",
        r"转化",
        r"拉新",
        r"促活",
        r"AARRR",
        r"社群",
        r"社区",
        r"内容",
        r"用户",
    ]
]


def is_target_job(record: RawJobRecord) -> bool:
    """判断是否为目标运营岗位。保留所有运营类岗位，不强制要求AI信号。"""
    title = (record.job_title or "").strip()
    if not title:
        return False
    if title in {"首页", "职位搜索"}:
        return False
    # 排除明显不相关的
    if any(pattern.search(title) for pattern in EXCLUDE_PATTERNS):
        return False
    # 必须包含运营相关关键词
    if not any(pattern.search(title) for pattern in INCLUDE_PATTERNS):
        return False
    return True


def is_ai_operation_job(record: RawJobRecord) -> bool:
    """判断是否为 AI 相关运营岗位（更严格的过滤）。"""
    if not is_target_job(record):
        return False
    combined = "\n".join([record.job_title, record.description_text or ""])
    return any(pattern.search(combined) for pattern in AI_SIGNAL_PATTERNS)
