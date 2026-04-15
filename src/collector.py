from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterator

from .browser import PlaywrightBossBrowser
from .config import BEIJING_CITY_NAME
from .schemas import CrawlError, RawJobRecord, extract_job_id


class BossCollector:
    def __init__(self, browser: PlaywrightBossBrowser, *, city_name: str = BEIJING_CITY_NAME, city_code: str) -> None:
        self.browser = browser
        self.city_name = city_name
        self.city_code = city_code

    def iter_jobs(
        self,
        *,
        keywords: list[str],
        max_pages: int,
        max_jobs_per_keyword: int,
        max_total_jobs: int | None = None,
        seen_job_ids: set[str] | None = None,
        wait_for_login: bool = True,
        job_filter: Callable[[RawJobRecord], bool] | None = None,
    ) -> Iterator[RawJobRecord | CrawlError]:
        seen_job_ids = seen_job_ids or set()
        self.browser.open()
        total_records = 0
        try:
            if wait_for_login:
                self.browser.prompt_manual_login()
            for keyword in keywords:
                if max_total_jobs is not None and total_records >= max_total_jobs:
                    break
                fetched_for_keyword = 0
                for page_index in range(1, max_pages + 1):
                    try:
                        urls = self.browser.fetch_job_urls(
                            keyword=keyword,
                            city_code=self.city_code,
                            page_index=page_index,
                        )
                    except Exception as exc:
                        yield CrawlError(
                            keyword=keyword,
                            stage="list",
                            error=str(exc),
                            time=self._now(),
                        )
                        break

                    if not urls:
                        break

                    for list_rank, job_url in enumerate(urls, start=1):
                        if max_total_jobs is not None and total_records >= max_total_jobs:
                            break
                        job_id = extract_job_id(job_url)
                        if job_id in seen_job_ids:
                            continue

                        try:
                            detail = self.browser.fetch_job_detail(job_url)
                            record = RawJobRecord(
                                job_id=job_id,
                                keyword=keyword,
                                city=self.city_name,
                                job_title=detail.job_title,
                                company_name=detail.company_name,
                                salary_text=detail.salary_text,
                                experience_text=detail.experience_text,
                                education_text=detail.education_text,
                                job_tags=detail.job_tags,
                                job_url=job_url,
                                description_text=detail.description_text,
                                company_text=detail.company_text,
                                crawl_time=self._now(),
                                page_index=page_index,
                                list_rank=list_rank,
                            )
                            if job_filter is not None and not job_filter(record):
                                continue
                            seen_job_ids.add(record.job_id)
                            fetched_for_keyword += 1
                            total_records += 1
                            yield record
                        except Exception as exc:
                            yield CrawlError(
                                keyword=keyword,
                                job_url=job_url,
                                stage="detail",
                                error=str(exc),
                                time=self._now(),
                            )

                        if fetched_for_keyword >= max_jobs_per_keyword:
                            break

                    if fetched_for_keyword >= max_jobs_per_keyword:
                        break
                    if max_total_jobs is not None and total_records >= max_total_jobs:
                        break
        finally:
            self.browser.close()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
