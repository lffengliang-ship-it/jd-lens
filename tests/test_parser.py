import unittest

from src.parser import extract_bonus_text, extract_requirement_text, extract_skill_terms, split_sections


SAMPLE_TEXT = """
岗位职责：
负责 AI Agent 应用设计与落地。

任职要求：
熟悉 Python、LangChain、RAG、向量数据库。
有 MCP 或工作流编排经验优先。

加分项：
了解 LangGraph、Dify。
""".strip()


class ParserTests(unittest.TestCase):
    def test_split_sections_by_heading(self) -> None:
        sections = split_sections(SAMPLE_TEXT)
        self.assertIn("岗位要求", sections)
        self.assertIn("加分项", sections)

    def test_extract_requirement_prefers_requirement_section(self) -> None:
        requirement = extract_requirement_text(SAMPLE_TEXT)
        self.assertIn("熟悉 Python", requirement)
        self.assertNotIn("了解 LangGraph", requirement)

    def test_extract_bonus_text(self) -> None:
        bonus = extract_bonus_text(SAMPLE_TEXT)
        self.assertIn("LangGraph", bonus)

    def test_extract_skill_terms(self) -> None:
        terms = extract_skill_terms(SAMPLE_TEXT)
        for item in ["AI Agent", "Python", "LangChain", "RAG", "向量数据库", "MCP", "Workflow", "LangGraph", "Dify"]:
            self.assertIn(item, terms)

    def test_inline_heading_lines_split_requirement_and_bonus(self) -> None:
        text = "任职要求：熟悉 Python、LangChain、RAG、MCP。\n加分项：了解 Docker 和 vLLM。"
        requirement = extract_requirement_text(text)
        bonus = extract_bonus_text(text)
        self.assertIn("熟悉 Python", requirement)
        self.assertNotIn("Docker", requirement)
        self.assertIn("Docker", bonus)


if __name__ == "__main__":
    unittest.main()
