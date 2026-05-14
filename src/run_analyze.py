from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import parse_jobs, render_report
from .config import PROCESSED_CSV_PATH, RAW_JOBS_PATH, REPORT_PATH
from .schemas import RawJobRecord
from .storage import read_jsonl, write_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="分析已采集的 Boss 运营岗位 JD，生成 CSV 和分析报告。")
    parser.add_argument("--input", default=str(RAW_JOBS_PATH), help="输入 JSONL 路径")
    parser.add_argument("--csv-output", default=str(PROCESSED_CSV_PATH), help="输出 CSV 路径")
    parser.add_argument("--report-output", default=str(REPORT_PATH), help="输出分析报告路径")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    csv_output = Path(args.csv_output)
    report_output = Path(args.report_output)

    raw_records = [RawJobRecord.from_dict(item) for item in read_jsonl(input_path)]
    print(f"读取到 {len(raw_records)} 条原始记录")

    parsed_records = parse_jobs(raw_records)
    print(f"解析得到 {len(parsed_records)} 条有效记录")

    write_csv(
        csv_output,
        [
            {
                **record.to_dict(),
                "matched_keywords": " | ".join(record.matched_keywords),
                "skill_terms": " | ".join(record.skill_terms),
                "categories": " | ".join(record.categories),
            }
            for record in parsed_records
        ],
    )

    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(render_report(parsed_records), encoding="utf-8")

    print(f"\n分析完成:")
    print(f"  CSV:  {csv_output}")
    print(f"  报告: {report_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
