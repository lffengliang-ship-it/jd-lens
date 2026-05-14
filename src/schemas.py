from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re


JOB_ID_PATTERNS = [
    re.compile(r"/job_detail/([^./?]+)"),
    re.compile(r"[?&]jobId=([^&]+)"),
]


def extract_job_id(job_url: str) -> str:
    for pattern in JOB_ID_PATTERNS:
        match = pattern.search(job_url)
        if match:
            return match.group(1)
    return job_url


def make_fallback_key(job_title: str, company_name: str, salary_text: str, job_url: str) -> str:
    return "||".join(
        [
            (job_title or "").strip(),
            (company_name or "").strip(),
            (salary_text or "").strip(),
            (job_url or "").strip(),
        ]
    )


@dataclass(slots=True)
class RawJobRecord:
    job_id: str
    keyword: str
    city: str
    job_title: str
    company_name: str
    salary_text: str
    experience_text: str
    education_text: str
    job_tags: list[str] = field(default_factory=list)
    job_url: str = ""
    description_text: str = ""
    company_text: str = ""
    crawl_time: str = ""
    page_index: int = 1
    list_rank: int = 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "RawJobRecord":
        return cls(**payload)


@dataclass(slots=True)
class ParsedJobRecord:
    job_id: str
    job_title: str
    company_name: str
    job_url: str
    keyword: str
    city: str = ""
    requirement_text: str = ""
    bonus_text: str = ""
    matched_keywords: list[str] = field(default_factory=list)
    skill_terms: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    salary_text: str = ""
    experience_text: str = ""
    education_text: str = ""
    crawl_time: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ParsedJobRecord":
        return cls(**payload)


@dataclass(slots=True)
class CrawlError:
    keyword: str
    stage: str
    error: str
    time: str
    job_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

