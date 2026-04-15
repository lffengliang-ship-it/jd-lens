import unittest

from src.analyzer import categories_for_terms, parse_jobs, render_report, render_roadmap
from src.schemas import RawJobRecord


def make_record(job_id: str, company: str, url: str) -> RawJobRecord:
    return RawJobRecord(
        job_id=job_id,
        keyword="AI Agent",
        city="北京",
        job_title="AI Agent 工程师",
        company_name=company,
        salary_text="30-50K",
        experience_text="3-5年",
        education_text="本科",
        job_url=url,
        description_text="""
任职要求：
熟悉 Python、LangChain、RAG、向量数据库、MCP。
有 Docker 和 vLLM 经验优先。
""".strip(),
    )


class AnalyzerTests(unittest.TestCase):
    def test_categories_for_terms(self) -> None:
        categories = categories_for_terms(["Python", "RAG", "MCP", "LangChain", "Docker"])
        self.assertIn("工程落地能力", categories)
        self.assertIn("RAG / 知识库", categories)
        self.assertIn("Agent / Workflow 编排", categories)
        self.assertIn("Agent 应用框架", categories)
        self.assertIn("推理部署与系统工程", categories)

    def test_parse_jobs_dedupes_by_job_id(self) -> None:
        parsed = parse_jobs([make_record("1", "甲", "u1"), make_record("1", "乙", "u2")])
        self.assertEqual(len(parsed), 1)

    def test_render_report_contains_core_sections(self) -> None:
        report = render_report(parse_jobs([make_record("1", "甲", "u1")]))
        self.assertIn("高频技能词", report)
        self.assertIn("学习建议", report)
        self.assertIn("代表性岗位摘录", report)

    def test_render_roadmap_contains_learning_phases(self) -> None:
        roadmap = render_roadmap(parse_jobs([make_record("1", "甲", "u1")]))
        self.assertIn("入门", roadmap)
        self.assertIn("进阶", roadmap)
        self.assertIn("作品集", roadmap)
        self.assertIn("面试准备", roadmap)


if __name__ == "__main__":
    unittest.main()
