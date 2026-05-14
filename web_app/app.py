"""JD 分析工具 - Flask 后端（v2 版本，含简历上传 + LLM 分析）。"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from ocr_engine import ocr_image
from jd_analyzer import parse_jd_text, save_job, load_all_jobs, delete_job
from resume_parser import parse_resume, save_resume, load_resume, delete_resume
from resume_desensitizer import ResumeDesensitizer
from llm_client import LLMClient, build_market_report_prompt, build_resume_feedback_prompt

app = Flask(__name__, static_folder="static", static_url_path="")

# ── LLM 配置 ──────────────────────────────────────────────
llm_config_path = Path(__file__).parent / "data" / "llm_config.json"


def get_llm_client() -> LLMClient:
    """从本地配置文件读取 LLM 设置并创建客户端。"""
    if not llm_config_path.exists():
        raise ValueError("请先配置 LLM：在页面设置中填写 API Key、Base URL 和模型名")

    config = json.loads(llm_config_path.read_text(encoding="utf-8"))
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.openai.com/v1")
    model = config.get("model", "gpt-4o")
    provider = config.get("provider", "openai")

    if not api_key:
        raise ValueError("API Key 未设置")

    return LLMClient(api_key=api_key, base_url=base_url, model=model, provider=provider)


# ── 页面路由 ──────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── 截图分析 ──────────────────────────────────────────────
@app.route("/api/analyze", methods=["POST"])
def analyze():
    """接收截图，OCR 识别 + 解析分析。"""
    if "image" not in request.files:
        return jsonify({"error": "请上传图片"}), 400

    file = request.files["image"]
    image_bytes = file.read()
    if not image_bytes:
        return jsonify({"error": "图片为空"}), 400

    try:
        ocr_text = ocr_image(image_bytes)
    except Exception as e:
        return jsonify({"error": f"OCR 识别失败: {str(e)}"}), 500

    if not ocr_text.strip():
        return jsonify({"error": "未能识别出文字，请确保截图清晰"}), 400

    job = parse_jd_text(ocr_text, source="screenshot")
    save_job(job)

    return jsonify({
        "ocr_text": ocr_text,
        "job": {
            "id": job.id,
            "job_title": job.job_title,
            "salary": job.salary,
            "city": job.city,
            "experience": job.experience,
            "education": job.education,
            "company": job.company,
            "skills": job.skills,
            "categories": job.categories,
        }
    })


@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """获取所有已收集的岗位。"""
    jobs = load_all_jobs()
    jobs.reverse()
    return jsonify({"jobs": jobs, "total": len(jobs)})


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def remove_job(job_id: str):
    """删除指定岗位。"""
    delete_job(job_id)
    return jsonify({"ok": True})


# ── 简历上传 ──────────────────────────────────────────────
@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    """上传简历文件（PDF/Word/图片），解析并脱敏后保存。"""
    if "file" not in request.files:
        return jsonify({"error": "请上传简历文件"}), 400

    file = request.files["file"]
    file_bytes = file.read()
    filename = file.filename or "resume.pdf"
    if not file_bytes:
        return jsonify({"error": "文件为空"}), 400

    # 解析简历
    parsed = parse_resume(file_bytes, filename)
    if not parsed.raw_text.strip():
        return jsonify({"error": "未能解析出简历内容，请确保文件格式正确"}), 400

    # 脱敏处理
    desensitizer = ResumeDesensitizer()
    masked_text, mask_map = desensitizer.mask(parsed.raw_text)

    # 更新各段落的脱敏版本
    masked_personal = desensitizer.mask(parsed.personal_info)[0]
    masked_work = parsed.work_experience  # 工作经历一般不含隐私
    masked_edu = parsed.education         # 教育一般不含隐私
    masked_skills = parsed.skills         # 技能不含隐私
    masked_summary = parsed.summary       # 总结不含隐私

    # 保存原始 + 脱敏版本
    parsed.raw_text = masked_text
    parsed.personal_info = masked_personal
    save_resume(parsed)

    return jsonify({
        "resume": {
            "id": parsed.id,
            "personal_info": masked_personal,
            "work_experience": masked_work,
            "education": masked_edu,
            "skills": masked_skills,
            "summary": masked_summary,
            "desensitization_summary": desensitizer.get_mask_summary(),
        }
    })


@app.route("/api/resume", methods=["GET"])
def get_resume():
    """获取已保存的简历。"""
    data = load_resume()
    return jsonify({"resume": data.get("resume", None)})


@app.route("/api/resume", methods=["DELETE"])
def remove_resume():
    """删除已保存的简历。"""
    delete_resume()
    return jsonify({"ok": True})


# ── LLM 配置 ──────────────────────────────────────────────
@app.route("/api/llm_config", methods=["GET"])
def get_llm_config():
    """获取 LLM 配置。"""
    if not llm_config_path.exists():
        return jsonify({"config": None})
    config = json.loads(llm_config_path.read_text(encoding="utf-8"))
    # 不返回完整 API Key，只返回前几位 + 星号
    masked_key = ""
    if config.get("api_key"):
        key = config["api_key"]
        masked_key = key[:8] + "*" * (len(key) - 8) if len(key) > 8 else "****"
    return jsonify({
        "config": {
            "api_key_masked": masked_key,
            "base_url": config.get("base_url", "https://api.openai.com/v1"),
            "model": config.get("model", "gpt-4o"),
            "provider": config.get("provider", "openai"),
        }
    })


@app.route("/api/llm_config", methods=["POST"])
def set_llm_config():
    """设置 LLM 配置。"""
    data = request.get_json()
    api_key = data.get("api_key", "")
    base_url = data.get("base_url", "https://api.openai.com/v1")
    model = data.get("model", "gpt-4o")
    provider = data.get("provider", "openai")

    # 如果 API Key 是 masked 格式（包含星号），保留原来的
    if "*" in api_key and llm_config_path.exists():
        old_config = json.loads(llm_config_path.read_text(encoding="utf-8"))
        api_key = old_config.get("api_key", "")

    config = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "provider": provider,
    }
    llm_config_path.parent.mkdir(parents=True, exist_ok=True)
    llm_config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    return jsonify({"ok": True})


# ── LLM 分析 ──────────────────────────────────────────────
@app.route("/api/market_report", methods=["POST"])
def market_report():
    """生成市场分析报告（调用 LLM）。"""
    jobs = load_all_jobs()
    if not jobs:
        return jsonify({"error": "还没有收集任何岗位数据"}), 400

    try:
        client = get_llm_client()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    system_prompt, user_prompt = build_market_report_prompt(jobs)

    try:
        result = client.chat(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        return jsonify({"error": f"LLM 调用失败: {str(e)}"}), 500

    return jsonify({"report": result})


@app.route("/api/resume_feedback", methods=["POST"])
def resume_feedback():
    """生成简历优化建议（调用 LLM）。"""
    resume_data = load_resume()
    if not resume_data or not resume_data.get("resume"):
        return jsonify({"error": "请先上传简历"}), 400

    jobs = load_all_jobs()
    if not jobs:
        return jsonify({"error": "请先收集一些目标岗位 JD"}), 400

    try:
        client = get_llm_client()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    resume_text = resume_data["resume"].get("raw_text", "")
    system_prompt, user_prompt = build_resume_feedback_prompt(resume_text, jobs)

    try:
        result = client.chat(system_prompt, user_prompt, max_tokens=4096)
    except Exception as e:
        return jsonify({"error": f"LLM 调用失败: {str(e)}"}), 500

    return jsonify({"feedback": result})


if __name__ == "__main__":
    print("=" * 50)
    print("  JD 分析工具 v2 已启动")
    print("  浏览器打开: http://127.0.0.1:5888")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5888, debug=False)