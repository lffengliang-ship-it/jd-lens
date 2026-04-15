from pathlib import Path

BEIJING_CITY_NAME = "北京"
BEIJING_CITY_CODE = "101010100"
DEFAULT_BASE_URL = "https://www.zhipin.com"
DEFAULT_MAX_PAGES = 3
DEFAULT_MAX_JOBS_PER_KEYWORD = 50
DEFAULT_WAIT_SECONDS = 1.0
DEFAULT_USER_DATA_DIR = Path(".boss_profile")

DEFAULT_KEYWORDS = [
    "AI Agent",
    "agent",
    "智能体",
    "大模型应用",
    "LLM",
    "RAG",
    "Workflow",
    "LangChain",
    "LangGraph",
    "AutoGen",
    "Dify",
    "Coze",
    "MCP",
]

FOCUS_KEYWORDS = [
    "AI Agent",
    "agent",
    "智能体",
    "LLM",
    "大模型",
    "RAG",
    "Workflow",
    "LangChain",
    "LangGraph",
    "AutoGen",
    "Dify",
    "Coze",
    "MCP",
]

DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")

RAW_JOBS_PATH = DATA_RAW_DIR / "jobs.jsonl"
ERRORS_PATH = DATA_RAW_DIR / "errors.jsonl"
PROCESSED_CSV_PATH = DATA_PROCESSED_DIR / "jobs.csv"
REPORT_PATH = REPORTS_DIR / "aiagent_beijing_learning_report.md"

