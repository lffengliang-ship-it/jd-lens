"""简历解析引擎：支持 PDF / Word / 图片三种格式。"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime

from PIL import Image
from ocr_engine import ocr_image


@dataclass
class ParsedResume:
    """解析后的简历结构。"""
    id: str = ""
    raw_text: str = ""
    personal_info: str = ""      # 个人信息段
    work_experience: str = ""  # 工作经历
    education: str = ""        # 教育背景
    skills: str = ""           # 技能清单
    summary: str = ""          # 自我总结
    created_at: str = ""


# ── PDF 解析 ──────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从 PDF 提取文字，优先提取文字层，图片页走 OCR 兜底。"""
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(io.BytesIO(file_bytes))
        if text and text.strip():
            return text.strip()
    except ImportError:
        pass

    # PDFMiner 失败或有图片页 → 走 OCR 兜底
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
        from pdfminer.converter import PDFPageAggregator
        from pdfminer.layout import LAParams
    except ImportError:
        pass

    # 方案B：把 PDF 每页转成图片走 OCR
    try:
        import subprocess
        # 用 macOS 自带 pdftoppm 转图片
        result = subprocess.run(
            ["which", "pdftoppm"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["pdftoppm", "-r", "200", "-png", "-", tmp_path],
                input=file_bytes, capture_output=True
            )
            # 读取生成的文件
            import glob
            pages = sorted(glob.glob(tmp_path.replace(".png", "-*.png")))
            texts = []
            for page_file in pages:
                img = Image.open(page_file)
                texts.append(ocr_image(file_bytes if False else page_file))
                Path(page_file).unlink()
            Path(tmp_path.replace(".png", "-0.png")).unlink(missing_ok=True)
            return "\n".join(texts)
    except Exception:
        pass

    return ""


# ── Word 解析 ──────────────────────────────────────────────
def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 Word 文档提取段落文字。"""
    try:
        import docx
    except ImportError:
        return ""

    try:
        doc = docx.load_docx(io.BytesIO(file_bytes))
    except Exception:
        return ""

    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # 从表格提取
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.strip()
                if text:
                    paragraphs.append(text)

    return "\n".join(paragraphs)


# ── 图片解析（复用 OCR） ──────────────────────────────────
def extract_text_from_image(image_bytes: bytes) -> str:
    """图片走 OCR 识别文字。"""
    return ocr_image(image_bytes)


# ── 分段解析 ──────────────────────────────────────────────
def parse_resume_text(text: str) -> ParsedResume:
    """
    将简历纯文本按结构分段：
    - 个人信息
    - 工作经历
    - 教育背景
    - 技能清单
    - 自我总结
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ParsedResume(raw_text=text, created_at=datetime.now().isoformat(timespec="seconds"))

    # 分段标题关键词
    personal_headings = ["个人信息", "基本信息", "个人简历", "个人信息"]
    work_headings = ["工作经历", "工作经历", "实习经历", "经历", "工作简历"]
    edu_headings = ["教育背景", "教育经历", "学历", "教育"]
    skills_headings = ["专业技能", "技能特长", "技能清单", "技能", "掌握技能"]
    summary_headings = ["自我评价", "自我总结", "个人评价", "关于我", "个人简介"]

    sections: dict[str, list[str]] = {
        "personal": [], "work": [], "edu": [], "skills": [], "summary": []
    }
    current = "personal"

    heading_map = {}
    for h in personal_headings: heading_map[h] = "personal"
    for h in work_headings: heading_map[h] = "work"
    for h in edu_headings: heading_map[h] = "edu"
    for h in skills_headings: heading_map[h] = "skills"
    for h in summary_headings: heading_map[h] = "summary"

    for line in lines:
        stripped = line.strip()
        # 检查是否是标题行
        matched = False
        for heading, section_key in heading_map.items():
            if stripped.startswith(heading) or stripped == heading:
                current = section_key
                # 去掉标题后的冒号和内容
                remainder = stripped[len(heading):].lstrip("：: \t")
                if remainder:
                    sections[section_key].append(remainder)
                matched = True
                break
        if not matched:
            sections[current].append(stripped)

    # 组合各段
    personal_info = "\n".join(sections["personal"])
    work_experience = "\n".join(sections["work"])
    education = "\n".join(sections["edu"])
    skills = "\n".join(sections["skills"])
    summary = "\n".join(sections["summary"])

    # 兜底：如果 personal 段为空但首行看起来像个人信息，移到 personal
    if not personal_info and lines:
        first = lines[0]
        if any(kw in first for kw in ["姓名", "手机", "邮箱", "求职", "意向"]):
            personal_info = first

    return ParsedResume(
        id=datetime.now().strftime("%Y%m%d%H%M%S"),
        raw_text=text,
        personal_info=personal_info,
        work_experience=work_experience,
        education=education,
        skills=skills,
        summary=summary,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


# ── 主解析入口 ──────────────────────────────────────────────
def parse_resume(file_bytes: bytes, filename: str) -> ParsedResume:
    """根据文件名自动判断格式并解析。"""
    ext = Path(filename).suffix.lower()
    text = ""

    if ext == ".pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext in (".docx", ".doc"):
        text = extract_text_from_docx(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        text = extract_text_from_image(file_bytes)
    else:
        # 尝试把文件当文本读
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if not text.strip():
        # 兜底：整张图片走 OCR
        text = extract_text_from_image(file_bytes)

    return parse_resume_text(text)


# ── 简历存储 ──────────────────────────────────────────────
RESUME_FILE = Path(__file__).parent / "data" / "collected_resume.json"


def save_resume(resume: ParsedResume) -> None:
    """保存简历到本地 JSON。"""
    from pathlib import Path
    DATA_DIR = Path(__file__).parent / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_resume()
    existing["resume"] = asdict(resume)
    RESUME_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def load_resume() -> dict:
    """加载已保存的简历。"""
    if not RESUME_FILE.exists():
        return {}
    return json.loads(RESUME_FILE.read_text(encoding="utf-8"))


def delete_resume() -> None:
    """删除已保存的简历。"""
    if RESUME_FILE.exists():
        RESUME_FILE.unlink()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = sys.argv[1]
        text = extract_text_from_pdf(open(path, "rb").read()) if path.endswith(".pdf") else ""
        print(parse_resume_text(text))