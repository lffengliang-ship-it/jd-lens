import unittest

from src.job_filters import is_target_job
from src.schemas import RawJobRecord


def make_record(title: str, description: str = "负责 AI Agent 开发与落地。") -> RawJobRecord:
    return RawJobRecord(
        job_id=title,
        keyword="AI Agent",
        city="北京",
        job_title=title,
        company_name="测试公司",
        salary_text="30-50K",
        experience_text="3-5年",
        education_text="本科",
        job_url=f"https://example.com/{title}",
        description_text=description,
    )


class JobFilterTests(unittest.TestCase):
    def test_keeps_technical_engineering_role(self) -> None:
        self.assertTrue(is_target_job(make_record("AI Agent开发工程师")))

    def test_excludes_product_manager_role(self) -> None:
        self.assertFalse(is_target_job(make_record("高级产品经理（企业版）")))

    def test_excludes_intern_role(self) -> None:
        self.assertFalse(is_target_job(make_record("AI Agent开发实习生")))

    def test_excludes_fresh_graduate_role(self) -> None:
        self.assertFalse(is_target_job(make_record("AI后端开发工程师（应届毕业生）")))

    def test_excludes_operations_role_even_if_ai_related(self) -> None:
        self.assertFalse(is_target_job(make_record("AI数据运营专家-Agent方向/Prompt/搭建Coze")))

    def test_keeps_technical_leadership_role(self) -> None:
        self.assertTrue(is_target_job(make_record("智能体研发负责人")))

    def test_excludes_generic_backend_role_without_ai_signal(self) -> None:
        self.assertFalse(is_target_job(make_record("后端开发工程师", "负责订单系统和支付链路开发。")))

    def test_excludes_placeholder_homepage_title_even_if_description_mentions_ai(self) -> None:
        self.assertFalse(is_target_job(make_record("首页", "AI智能体开发实习生（GUI Agent方向）-CQC")))


if __name__ == "__main__":
    unittest.main()
