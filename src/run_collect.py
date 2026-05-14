from __future__ import annotations

import argparse

from .browser import CdpProxyBossBrowser, PlaywrightBossBrowser
from .collector import BossCollector
from .config import (
    CITY_MAP,
    DEFAULT_BASE_URL,
    DEFAULT_CITY,
    DEFAULT_KEYWORDS,
    DEFAULT_MAX_JOBS_PER_KEYWORD,
    DEFAULT_MAX_PAGES,
    DEFAULT_USER_DATA_DIR,
    DEFAULT_WAIT_SECONDS,
    ERRORS_PATH,
    RAW_JOBS_PATH,
)
from .job_filters import is_ai_operation_job, is_target_job
from .schemas import CrawlError, extract_job_id
from .storage import append_jsonl, read_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集 Boss直聘 AI运营/用户运营 岗位 JD")
    parser.add_argument("--keyword", action="append", dest="keywords", help="搜索关键词，可重复使用")
    parser.add_argument("--pages", type=int, default=DEFAULT_MAX_PAGES, help="每个关键词的最大页数")
    parser.add_argument(
        "--max-jobs-per-keyword",
        type=int,
        default=DEFAULT_MAX_JOBS_PER_KEYWORD,
        help="每个关键词最多保存多少个岗位",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Boss直聘基础URL")
    parser.add_argument("--city", default=DEFAULT_CITY, help=f"城市名称，默认{DEFAULT_CITY}。可选：{', '.join(CITY_MAP.keys())}")
    parser.add_argument("--city-code", default=None, help="Boss直聘城市代码（优先级高于--city）")
    parser.add_argument(
        "--browser-mode",
        choices=["persistent", "cdp"],
        default="persistent",
        help="persistent=独立 Playwright 浏览器；cdp=复用已开启 remote debugging 的 Chrome",
    )
    parser.add_argument("--user-data-dir", default=str(DEFAULT_USER_DATA_DIR), help="浏览器 profile 目录")
    parser.add_argument("--cdp-proxy-url", default="http://127.0.0.1:3456", help="CDP proxy URL")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--wait-seconds", type=float, default=DEFAULT_WAIT_SECONDS, help="页面加载等待时间")
    parser.add_argument("--wait-for-login", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-total-jobs", type=int, default=None, help="最多保存多少个岗位后停止")
    parser.add_argument("--ai-only", action=argparse.BooleanOptionalAction, default=False, help="只保留 AI 相关运营岗")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    keywords = args.keywords or DEFAULT_KEYWORDS

    # 解析城市
    city_code = args.city_code
    city_name = args.city
    if city_code is None:
        if city_name not in CITY_MAP:
            print(f"错误：不支持的城市「{city_name}」。可选：{', '.join(CITY_MAP.keys())}")
            return 1
        city_code = CITY_MAP[city_name]

    seen = {extract_job_id(item["job_url"]) for item in read_jsonl(RAW_JOBS_PATH) if item.get("job_url")}

    if args.browser_mode == "cdp":
        browser = CdpProxyBossBrowser(
            base_url=args.base_url,
            proxy_url=args.cdp_proxy_url,
            wait_seconds=args.wait_seconds,
        )
    else:
        browser = PlaywrightBossBrowser(
            base_url=args.base_url,
            user_data_dir=DEFAULT_USER_DATA_DIR.__class__(args.user_data_dir),
            headless=args.headless,
            wait_seconds=args.wait_seconds,
        )
    collector = BossCollector(browser, city_name=city_name, city_code=city_code)

    # 选择过滤器
    if args.ai_only:
        job_filter = is_ai_operation_job
    else:
        job_filter = is_target_job

    total_records = 0
    total_errors = 0
    for item in collector.iter_jobs(
        keywords=keywords,
        max_pages=args.pages,
        max_jobs_per_keyword=args.max_jobs_per_keyword,
        max_total_jobs=args.max_total_jobs,
        seen_job_ids=seen,
        wait_for_login=args.wait_for_login,
        job_filter=job_filter,
    ):
        if isinstance(item, CrawlError):
            append_jsonl(ERRORS_PATH, item.to_dict())
            total_errors += 1
            print(f"[error] {item.stage} {item.keyword} {item.job_url or ''} {item.error}")
            continue
        append_jsonl(RAW_JOBS_PATH, item.to_dict())
        total_records += 1
        print(f"[saved] {item.keyword} | {item.city} | {item.job_title} | {item.company_name} | {item.salary_text}")

    print(f"\n采集完成: 保存={total_records} 错误={total_errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
