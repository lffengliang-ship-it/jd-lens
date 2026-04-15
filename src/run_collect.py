from __future__ import annotations

import argparse

from .browser import CdpProxyBossBrowser, PlaywrightBossBrowser
from .collector import BossCollector
from .config import (
    BEIJING_CITY_CODE,
    DEFAULT_BASE_URL,
    DEFAULT_KEYWORDS,
    DEFAULT_MAX_JOBS_PER_KEYWORD,
    DEFAULT_MAX_PAGES,
    DEFAULT_USER_DATA_DIR,
    DEFAULT_WAIT_SECONDS,
    ERRORS_PATH,
    RAW_JOBS_PATH,
)
from .job_filters import is_target_job
from .schemas import CrawlError, extract_job_id
from .storage import append_jsonl, read_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect BOSS AI Agent jobs for Beijing.")
    parser.add_argument("--keyword", action="append", dest="keywords", help="keyword to search; repeatable")
    parser.add_argument("--pages", type=int, default=DEFAULT_MAX_PAGES, help="max pages per keyword")
    parser.add_argument(
        "--max-jobs-per-keyword",
        type=int,
        default=DEFAULT_MAX_JOBS_PER_KEYWORD,
        help="max jobs to save for each keyword",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="BOSS base URL")
    parser.add_argument("--city-code", default=BEIJING_CITY_CODE, help="BOSS city code, Beijing default")
    parser.add_argument(
        "--browser-mode",
        choices=["persistent", "cdp"],
        default="persistent",
        help="persistent=独立 Playwright 浏览器；cdp=复用当前已开启 remote debugging 的 Chrome 固定采集页",
    )
    parser.add_argument("--user-data-dir", default=str(DEFAULT_USER_DATA_DIR), help="persistent browser profile dir")
    parser.add_argument("--cdp-proxy-url", default="http://127.0.0.1:3456", help="local CDP proxy URL for --browser-mode cdp")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--wait-seconds", type=float, default=DEFAULT_WAIT_SECONDS, help="wait after navigation")
    parser.add_argument("--wait-for-login", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-total-jobs", type=int, default=None, help="stop after saving this many filtered jobs")
    parser.add_argument("--technical-only", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    keywords = args.keywords or DEFAULT_KEYWORDS
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
    collector = BossCollector(browser, city_code=args.city_code)
    job_filter = is_target_job if args.technical_only else None

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
        print(f"[saved] {item.keyword} | {item.job_title} | {item.company_name}")

    print(f"collect finished: saved={total_records} errors={total_errors}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
