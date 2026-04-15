import builtins
import json
import unittest
from unittest.mock import patch

from src.browser import CdpProxyBossBrowser, JobDetailPayload


class FakeProxyBrowser(CdpProxyBossBrowser):
    def __init__(self) -> None:
        super().__init__(proxy_url='http://127.0.0.1:3456')
        self.calls: list[tuple] = []

    def _get_json(self, path: str):
        self.calls.append(("GET", path))
        if path.startswith('/new'):
            return {'targetId': 'target-1'}
        if path.startswith('/navigate'):
            return {'ok': True}
        if path.startswith('/close'):
            return {'success': True}
        raise AssertionError(path)

    def _post_json(self, path: str, body: str):
        self.calls.append(("POST", path, body))
        if path == '/eval?target=target-1':
            if 'querySelectorAll("a[href]")' in body:
                return {'value': json.dumps([
                    '/job_detail/abc.html',
                    'https://www.zhipin.com/job_detail/xyz.html',
                    '/job_detail/abc.html',
                ])}
            return {
                'value': json.dumps({
                    'job_title': 'AI Agent开发工程师',
                    'company_name': '公司名称\n矩网科技有限公司',
                    'salary_text': '15-25K',
                    'description_text': '职位描述：熟悉 LangChain、RAG、MCP。',
                    'company_text': '矩网科技有限公司 未融资 100-499人 计算机软件',
                    'job_tags': ['五险一金', '带薪年假'],
                    'body_text': 'AI Agent开发工程师\n15-25K\n北京 经验不限 学历不限\n职位描述：熟悉 LangChain、RAG、MCP。\n公司成立于2014年。',
                })
            }
        raise AssertionError((path, body))


class CdpProxyBossBrowserTests(unittest.TestCase):
    def test_open_creates_single_target_and_close_only_closes_owned_target(self) -> None:
        browser = FakeProxyBrowser()

        browser.open()
        browser.close()

        self.assertEqual('target-1', browser._target_id)
        self.assertEqual(("GET", '/new?url=about%3Ablank'), browser.calls[0])
        self.assertEqual(("GET", '/close?target=target-1'), browser.calls[-1])

    def test_fetch_job_urls_reuses_same_target_and_deduplicates(self) -> None:
        browser = FakeProxyBrowser()
        browser.open()

        urls = browser.fetch_job_urls(keyword='AI Agent', city_code='101010100', page_index=1)

        self.assertEqual(
            [
                'https://www.zhipin.com/job_detail/abc.html',
                'https://www.zhipin.com/job_detail/xyz.html',
            ],
            urls,
        )
        self.assertIn(
            (
                "GET",
                '/navigate?target=target-1&url=https%3A%2F%2Fwww.zhipin.com%2Fweb%2Fgeek%2Fjob%3Fquery%3DAI%2520Agent%26city%3D101010100%26page%3D1',
            ),
            browser.calls,
        )

    def test_fetch_job_detail_builds_payload_from_proxy_data(self) -> None:
        browser = FakeProxyBrowser()
        browser.open()

        payload = browser.fetch_job_detail('https://www.zhipin.com/job_detail/abc.html')

        self.assertIsInstance(payload, JobDetailPayload)
        self.assertEqual('AI Agent开发工程师', payload.job_title)
        self.assertEqual('矩网科技有限公司', payload.company_name)
        self.assertEqual('15-25K', payload.salary_text)
        self.assertEqual('经验不限', payload.experience_text)
        self.assertEqual('学历不限', payload.education_text)
        self.assertIn('五险一金', payload.job_tags)
        self.assertIn('LangChain', payload.description_text)

    def test_prompt_manual_login_uses_same_target(self) -> None:
        browser = FakeProxyBrowser()
        browser.open()

        with patch.object(builtins, 'input', return_value=''):
            browser.prompt_manual_login()

        self.assertIn(("GET", '/navigate?target=target-1&url=https%3A%2F%2Fwww.zhipin.com'), browser.calls)


if __name__ == '__main__':
    unittest.main()
