from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import parse_jobs, render_report, render_roadmap
from .config import PROCESSED_CSV_PATH, RAW_JOBS_PATH, REPORT_PATH
from .schemas import RawJobRecord
from .storage import read_jsonl, write_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze collected BOSS jobs and write CSV/report.")
    parser.add_argument("--input", default=str(RAW_JOBS_PATH), help="input JSONL path")
    parser.add_argument("--csv-output", default=str(PROCESSED_CSV_PATH), help="output CSV path")
    parser.add_argument("--report-output", default=str(REPORT_PATH), help="output Markdown report path")
    parser.add_argument(
        "--roadmap-output",
        default="reports/aiagent_beijing_learning_roadmap.md",
        help="output Markdown roadmap path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    csv_output = Path(args.csv_output)
    report_output = Path(args.report_output)
    roadmap_output = Path(args.roadmap_output)

    raw_records = [RawJobRecord.from_dict(item) for item in read_jsonl(input_path)]
    parsed_records = parse_jobs(raw_records)
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
    roadmap_output.parent.mkdir(parents=True, exist_ok=True)
    roadmap_output.write_text(render_roadmap(parsed_records), encoding="utf-8")
    print(
        f"analyze finished: parsed={len(parsed_records)} csv={csv_output} "
        f"report={report_output} roadmap={roadmap_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
