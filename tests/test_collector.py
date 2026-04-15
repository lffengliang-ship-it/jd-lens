import unittest

from src.collector import BossCollector
from src.schemas import CrawlError, RawJobRecord


class FakeDetail:
    def __init__(self, *, title: str = "AI Agent 工程师") -> None:
        self.job_title = title
        self.company_name = "测试公司"
        self.salary_text = "30-50K"
        self.experience_text = "3-5年"
        self.education_text = "本科"
        self.job_tags = ["Agent", "RAG"]
        self.description_text = "任职要求：熟悉 Python、RAG、MCP。"
        self.company_text = "一家做 AI 应用的公司"


class FakeBrowser:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False
        self.prompted = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    def prompt_manual_login(self) -> None:
        self.prompted = True

    def fetch_job_urls(self, *, keyword: str, city_code: str, page_index: int) -> list[str]:
        if keyword == "bad-list":
            raise RuntimeError("list failed")
        if page_index > 1:
            return []
        return [
            "https://www.zhipin.com/job_detail/ok1.html",
            "https://www.zhipin.com/job_detail/fail1.html",
        ]

    def fetch_job_detail(self, job_url: str) -> FakeDetail:
        if "fail1" in job_url:
            raise RuntimeError("detail failed")
        return FakeDetail()


class CollectorTests(unittest.TestCase):
    def test_iter_jobs_yields_record_and_error(self) -> None:
        collector = BossCollector(FakeBrowser(), city_code="101010100")
        items = list(
            collector.iter_jobs(
                keywords=["AI Agent"],
                max_pages=1,
                max_jobs_per_keyword=10,
                wait_for_login=False,
            )
        )
        self.assertTrue(any(isinstance(item, RawJobRecord) for item in items))
        self.assertTrue(any(isinstance(item, CrawlError) for item in items))

    def test_iter_jobs_skips_seen_job_ids(self) -> None:
        collector = BossCollector(FakeBrowser(), city_code="101010100")
        items = list(
            collector.iter_jobs(
                keywords=["AI Agent"],
                max_pages=1,
                max_jobs_per_keyword=10,
                seen_job_ids={"ok1"},
                wait_for_login=False,
            )
        )
        self.assertFalse(any(isinstance(item, RawJobRecord) for item in items))

    def test_iter_jobs_stops_at_max_total_jobs(self) -> None:
        collector = BossCollector(FakeBrowser(), city_code="101010100")
        items = list(
            collector.iter_jobs(
                keywords=["AI Agent", "agent"],
                max_pages=1,
                max_jobs_per_keyword=10,
                max_total_jobs=1,
                wait_for_login=False,
            )
        )
        records = [item for item in items if isinstance(item, RawJobRecord)]
        self.assertEqual(1, len(records))


if __name__ == "__main__":
    unittest.main()
