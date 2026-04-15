from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from .config import DEFAULT_BASE_URL


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\n{3,}", "\n\n", value.replace("\r", "")).strip()


EXPERIENCE_PATTERNS = [r"经验不限", r"应届生", r"\d+\s*-\s*\d+\s*年", r"\d+\s*年(?:以上)?"]
EDUCATION_PATTERNS = [r"初中及以下", r"中专/中技", r"高中", r"大专", r"本科", r"硕士", r"博士", r"学历不限"]


@dataclass(slots=True)
class JobDetailPayload:
    job_title: str
    company_name: str
    salary_text: str
    experience_text: str
    education_text: str
    job_tags: list[str]
    description_text: str
    company_text: str


class BossBrowserBase:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        wait_seconds: float = 1.0,
        timeout_ms: int = 15_000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.wait_seconds = wait_seconds
        self.timeout_ms = timeout_ms

    def build_search_url(self, *, keyword: str, city_code: str, page_index: int) -> str:
        query = quote(keyword)
        return f"{self.base_url}/web/geek/job?query={query}&city={city_code}&page={page_index}"

    @staticmethod
    def _extract_by_patterns(text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _extract_salary_from_body(text: str) -> str:
        match = re.search(r"\d{1,2}\s*[-~—]\s*\d{1,2}K", text, re.I)
        return match.group(0) if match else ""

    @staticmethod
    def _extract_title_from_body(text: str) -> str:
        return text.splitlines()[0].strip() if text else ""

    @staticmethod
    def _extract_company_from_title(title: str) -> str:
        match = re.search(r"》_([^_]+?)招聘", title)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _normalize_company_name(value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            return ""
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return ""
        if lines[0] in {"公司名称", "企业名称"} and len(lines) > 1:
            return lines[1]
        return cleaned.replace("公司名称", "", 1).strip() if cleaned.startswith("公司名称") else cleaned

    @staticmethod
    def _header_excerpt(text: str, *, max_lines: int = 12) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines[:max_lines])


class PlaywrightBossBrowser(BossBrowserBase):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        user_data_dir: Path,
        headless: bool = False,
        wait_seconds: float = 1.0,
        timeout_ms: int = 15_000,
    ) -> None:
        super().__init__(base_url=base_url, wait_seconds=wait_seconds, timeout_ms=timeout_ms)
        self.user_data_dir = user_data_dir
        self.headless = headless
        self._playwright = None
        self._context = None
        self._page = None

    def open(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "缺少 playwright 依赖。请先执行 `pip install -r requirements.txt` "
                "和 `python -m playwright install chromium`。"
            ) from exc

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        chromium = self._playwright.chromium
        self._context = chromium.launch_persistent_context(
            str(self.user_data_dir),
            headless=self.headless,
            args=["--disable-crash-reporter", "--disable-breakpad"],
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        self._close_other_blank_pages()

    def close(self) -> None:
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass

    @property
    def page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Browser is not open.")
        return self._page

    def _close_other_blank_pages(self) -> None:
        if self._context is None or self._page is None:
            return
        for page in list(self._context.pages):
            if page == self._page:
                continue
            try:
                if page.url == "about:blank":
                    page.close()
            except Exception:
                continue

    def prompt_manual_login(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        self.page.bring_to_front()
        print("浏览器已打开 BOSS 首页。若未登录，请手动登录；若已登录，直接回车继续。")
        input("登录确认后按回车继续采集：")

    def fetch_job_urls(self, *, keyword: str, city_code: str, page_index: int) -> list[str]:
        search_url = self.build_search_url(keyword=keyword, city_code=city_code, page_index=page_index)
        self.page.goto(search_url, wait_until="domcontentloaded")
        time.sleep(self.wait_seconds)
        last_error: Exception | None = None
        hrefs: list[str] = []
        for _ in range(3):
            try:
                hrefs = self.page.eval_on_selector_all(
                    "a[href]",
                    """els => els
                        .map(el => el.href || el.getAttribute('href'))
                        .filter(Boolean)
                        .filter(href => href.includes('/job_detail/'))""",
                )
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                message = str(exc)
                if "Execution context was destroyed" not in message:
                    break
                time.sleep(self.wait_seconds)
        if last_error is not None:
            raise last_error
        unique: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            absolute = urljoin(self.base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                unique.append(absolute)
        return unique

    def _text_first(self, selectors: list[str]) -> str:
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if locator.count() == 0:
                    continue
                text = locator.inner_text(timeout=2_000)
                cleaned = _clean_text(text)
                if cleaned:
                    return cleaned
            except Exception:
                continue
        return ""

    def _texts(self, selectors: list[str]) -> list[str]:
        values: list[str] = []
        for selector in selectors:
            try:
                locator = self.page.locator(selector)
                count = locator.count()
                for idx in range(count):
                    text = _clean_text(locator.nth(idx).inner_text(timeout=1_000))
                    if text and text not in values:
                        values.append(text)
            except Exception:
                continue
        return values

    def fetch_job_detail(self, job_url: str) -> JobDetailPayload:
        self.page.goto(job_url, wait_until="domcontentloaded")
        time.sleep(self.wait_seconds)

        body_text = _clean_text(self.page.text_content("body"))
        job_title = self._text_first([".job-name", ".job-title", "h1"])
        company_name = self._text_first([".company-name", ".company-info a", ".company-info h2"])
        salary_text = self._text_first([".salary", ".job-salary", ".salary-box"])
        description_text = self._text_first(
            [
                ".job-sec-text",
                ".job-detail-section .text",
                ".job-description",
                "[class*='job-sec-text']",
                "[class*='detail-content']",
            ]
        )
        company_text = self._text_first(
            [
                ".company-detail",
                ".company-info-detail",
                "[class*='company-detail']",
            ]
        )
        job_tags = self._texts([".tag-list li", ".job-labels li", ".job-tags span", ".job-card-tag"])

        meta_text = " ".join(
            self._texts([".job-info li", ".job-primary .info-primary p", ".job-detail-head .info-primary *"])
        )
        experience_text = self._extract_by_patterns(meta_text or body_text, EXPERIENCE_PATTERNS)
        education_text = self._extract_by_patterns(meta_text or body_text, EDUCATION_PATTERNS)

        return JobDetailPayload(
            job_title=job_title or self._extract_title_from_body(body_text),
            company_name=company_name,
            salary_text=salary_text or self._extract_salary_from_body(body_text),
            experience_text=experience_text,
            education_text=education_text,
            job_tags=job_tags,
            description_text=description_text or body_text,
            company_text=company_text,
        )


class CdpProxyBossBrowser(BossBrowserBase):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        proxy_url: str = "http://127.0.0.1:3456",
        target_url: str = "about:blank",
        wait_seconds: float = 1.0,
        timeout_ms: int = 15_000,
    ) -> None:
        super().__init__(base_url=base_url, wait_seconds=wait_seconds, timeout_ms=timeout_ms)
        self.proxy_url = proxy_url.rstrip("/")
        self.target_url = target_url
        self._target_id: str | None = None
        self._closed = True

    def open(self) -> None:
        if self._target_id is not None and not self._closed:
            return
        response = self._get_json(f"/new?url={quote(self.target_url, safe='')}")
        target_id = response.get("targetId")
        if not target_id:
            raise RuntimeError(f"CDP proxy 未返回 targetId: {response}")
        self._target_id = str(target_id)
        self._closed = False

    def close(self) -> None:
        if self._target_id is None or self._closed:
            return
        try:
            self._get_json(f"/close?target={quote(self._target_id, safe='')}")
        finally:
            self._closed = True

    def prompt_manual_login(self) -> None:
        self._navigate(self.base_url)
        print("已复用当前 Chrome 的固定采集页。若未登录，请在该页完成登录；若已登录，直接回车继续。")
        input("登录确认后按回车继续采集：")

    def fetch_job_urls(self, *, keyword: str, city_code: str, page_index: int) -> list[str]:
        search_url = self.build_search_url(keyword=keyword, city_code=city_code, page_index=page_index)
        self._navigate(search_url)
        time.sleep(self.wait_seconds)
        payload = self._post_json(
            f"/eval?target={self._require_target_id()}",
            (
                'JSON.stringify(Array.from(document.querySelectorAll("a[href]"))'
                '.map(el => el.href || el.getAttribute("href"))'
                '.filter(Boolean)'
                '.filter(href => href.includes("/job_detail/")))'
            ),
        )
        hrefs = json.loads(payload.get("value") or "[]")

        unique: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            absolute = urljoin(self.base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                unique.append(absolute)
        return unique

    def fetch_job_detail(self, job_url: str) -> JobDetailPayload:
        self._navigate(job_url)
        time.sleep(self.wait_seconds)
        payload = self._post_json(
            f"/eval?target={self._require_target_id()}",
            """
JSON.stringify((() => {
  const text = el => (el && (el.innerText || el.textContent || '') || '').trim();
  const firstText = selectors => {
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        const value = text(el);
        if (value) return value;
      }
    }
    return '';
  };
  const texts = selectors => {
    const seen = new Set();
    const values = [];
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        const value = text(el);
        if (value && !seen.has(value)) {
          seen.add(value);
          values.push(value);
        }
      }
    }
    return values;
  };
  return {
    job_title: firstText(['h1', '.job-name', '.job-title']),
    company_name: firstText([
      '.job-detail-company .company-name',
      '.company-info h2',
      '.company-info .company-name',
      '.company-info a',
      '.company-name'
    ]),
    salary_text: firstText(['.salary', '.job-salary', '.salary-box']),
    description_text: firstText([
      '.job-sec-text',
      '.job-detail-section .text',
      '.job-description',
      '[class*="job-sec-text"]',
      '[class*="detail-content"]'
    ]),
    company_text: firstText([
      '.company-detail',
      '.company-info-detail',
      '.company-info',
      '.job-detail-company'
    ]),
    job_tags: texts(['.tag-list li', '.job-labels li', '.job-tags span', '.job-card-tag']),
    body_text: document.body ? (document.body.innerText || '') : '',
    page_title: document.title
  };
})())
""".strip(),
        )
        detail = json.loads(payload.get("value") or "{}")
        body_text = _clean_text(detail.get("body_text"))
        header_text = self._header_excerpt(body_text)
        job_title = _clean_text(detail.get("job_title"))
        company_name = self._normalize_company_name(detail.get("company_name", "")) or self._extract_company_from_title(
            detail.get("page_title", "")
        )
        salary_text = _clean_text(detail.get("salary_text")) or self._extract_salary_from_body(body_text)
        description_text = _clean_text(detail.get("description_text")) or body_text

        return JobDetailPayload(
            job_title=job_title or self._extract_title_from_body(body_text),
            company_name=company_name,
            salary_text=salary_text,
            experience_text=self._extract_by_patterns(header_text or body_text, EXPERIENCE_PATTERNS),
            education_text=self._extract_by_patterns(header_text or body_text, EDUCATION_PATTERNS),
            job_tags=[_clean_text(item) for item in detail.get("job_tags", []) if _clean_text(item)],
            description_text=description_text,
            company_text=_clean_text(detail.get("company_text")),
        )

    def _navigate(self, url: str) -> None:
        self._get_json(
            f"/navigate?{urlencode({'target': self._require_target_id(), 'url': url})}"
        )

    def _require_target_id(self) -> str:
        if self._target_id is None or self._closed:
            raise RuntimeError("CDP browser is not open.")
        return self._target_id

    def _get_json(self, path: str) -> dict[str, Any]:
        return self._request_json(path)

    def _post_json(self, path: str, body: str) -> dict[str, Any]:
        return self._request_json(path, data=body.encode("utf-8"))

    def _request_json(self, path: str, *, data: bytes | None = None) -> dict[str, Any]:
        request = Request(
            f"{self.proxy_url}{path}",
            data=data,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            method="POST" if data is not None else "GET",
        )
        with urlopen(request, timeout=self.timeout_ms / 1000) as response:
            payload = response.read().decode("utf-8")
        if not payload:
            return {}
        return json.loads(payload)
