from __future__ import annotations

import re

from .schemas import RawJobRecord


EXCLUDE_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"实习",
        r"应届",
        r"校招",
        r"产品经理",
        r"产品",
        r"运营",
        r"销售",
        r"商务",
        r"顾问",
        r"法务",
        r"招聘",
        r"\bHR\b",
        r"人事",
        r"助理",
        r"编辑",
        r"客服",
        r"主播",
        r"行政",
        r"财务",
    ]
]

INCLUDE_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"工程师",
        r"开发",
        r"研发",
        r"算法",
        r"架构",
        r"后端",
        r"前端",
        r"全栈",
        r"测试",
        r"运维",
        r"\bSRE\b",
        r"\bDevOps\b",
        r"数据",
        r"机器学习",
        r"深度学习",
        r"\bNLP\b",
        r"大模型",
        r"\bAI\b",
        r"Agent",
        r"智能体",
        r"\bRAG\b",
        r"Prompt",
        r"\bMCP\b",
        r"LangChain",
        r"LangGraph",
        r"Dify",
        r"Coze",
        r"Python",
        r"Java",
        r"Golang",
        r"C\+\+",
    ]
]

AI_SIGNAL_PATTERNS = [
    re.compile(pattern, re.I)
    for pattern in [
        r"\bAI\b",
        r"人工智能",
        r"大模型",
        r"\bLLM\b",
        r"\bAIGC\b",
        r"Agent",
        r"智能体",
        r"\bRAG\b",
        r"\bMCP\b",
        r"LangChain",
        r"LangGraph",
        r"LlamaIndex",
        r"Dify",
        r"Coze",
        r"Prompt",
        r"多模态",
        r"向量数据库",
        r"Embedding",
        r"Tool Calling",
        r"Function Calling",
    ]
]


def is_target_job(record: RawJobRecord) -> bool:
    title = (record.job_title or "").strip()
    if not title:
        return False
    if title in {"首页", "职位搜索"}:
        return False
    if any(pattern.search(title) for pattern in EXCLUDE_PATTERNS):
        return False
    if not any(pattern.search(title) for pattern in INCLUDE_PATTERNS):
        return False
    combined = "\n".join([title, record.description_text or ""])
    return any(pattern.search(combined) for pattern in AI_SIGNAL_PATTERNS)
