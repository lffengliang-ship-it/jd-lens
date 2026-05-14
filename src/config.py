from pathlib import Path

# ── 城市配置 ──────────────────────────────────────────────
CITY_MAP: dict[str, str] = {
    "北京": "101010100",
    "上海": "101020100",
    "深圳": "101280600",
    "广州": "101280100",
    "杭州": "101210100",
    "成都": "101270100",
    "南京": "101190100",
    "武汉": "101200100",
    "西安": "101110100",
    "苏州": "101190400",
    "长沙": "101250100",
    "厦门": "101230200",
    "重庆": "101040100",
    "天津": "101030100",
    "郑州": "101180100",
}

DEFAULT_CITY = "北京"

# ── 搜索关键词 ────────────────────────────────────────────
DEFAULT_KEYWORDS = [
    "AI运营",
    "AI产品运营",
    "AI用户运营",
    "用户运营",
    "社群运营",
    "内容运营",
    "产品运营",
    "增长运营",
    "社区运营",
    "新媒体运营",
    "数据运营",
    "私域运营",
]

# ── 分析时聚焦的关键词 ────────────────────────────────────
FOCUS_KEYWORDS = [
    "AI运营",
    "AI产品运营",
    "AI用户运营",
    "用户运营",
    "社群运营",
    "内容运营",
    "产品运营",
    "增长运营",
    "社区运营",
    "新媒体运营",
    "数据运营",
    "私域运营",
    "AIGC运营",
]

# ── 爬虫参数 ──────────────────────────────────────────────
DEFAULT_BASE_URL = "https://www.zhipin.com"
DEFAULT_MAX_PAGES = 5
DEFAULT_MAX_JOBS_PER_KEYWORD = 50
DEFAULT_WAIT_SECONDS = 1.0
DEFAULT_USER_DATA_DIR = Path(".boss_profile")

# ── 文件路径 ──────────────────────────────────────────────
DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")

RAW_JOBS_PATH = DATA_RAW_DIR / "jobs.jsonl"
ERRORS_PATH = DATA_RAW_DIR / "errors.jsonl"
PROCESSED_CSV_PATH = DATA_PROCESSED_DIR / "jobs.csv"
REPORT_PATH = REPORTS_DIR / "ai_operation_jd_report.md"
