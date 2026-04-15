import unittest

from src.schemas import RawJobRecord, extract_job_id, make_fallback_key


class SchemaTests(unittest.TestCase):
    def test_extract_job_id_from_detail_url(self) -> None:
        url = "https://www.zhipin.com/job_detail/abc123.html"
        self.assertEqual(extract_job_id(url), "abc123")

    def test_make_fallback_key_is_stable(self) -> None:
        self.assertEqual(
            make_fallback_key("AI Agent 工程师", "OpenAI", "30-50K", "u"),
            "AI Agent 工程师||OpenAI||30-50K||u",
        )

    def test_raw_record_roundtrip(self) -> None:
        record = RawJobRecord(
            job_id="1",
            keyword="AI Agent",
            city="北京",
            job_title="工程师",
            company_name="公司",
            salary_text="30-50K",
            experience_text="3-5年",
            education_text="本科",
            job_url="u",
            description_text="text",
        )
        self.assertEqual(RawJobRecord.from_dict(record.to_dict()).job_id, "1")


if __name__ == "__main__":
    unittest.main()

