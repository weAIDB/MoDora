from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
import os

from modora.core.results_jsonl import convert_results_file, validate_results_file


def register(sub: argparse._SubParsersAction) -> None:
    p_validate = sub.add_parser("results-validate", help="Validate results JSONL file")
    p_validate.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to input results JSONL file",
    )
    p_validate.add_argument(
        "--out", dest="output_path", help="Path to output validate results"
    )
    p_validate.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="Disable recursive validation",
    )
    p_validate.set_defaults(recursive=True, _handler=_handle_results_validate)

    p_convert = sub.add_parser("results-convert", help="Convert results JSONL file")
    p_convert.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to input results JSONL file",
    )
    p_convert.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output results JSONL file",
    )
    p_convert.add_argument(
        "--dedup",
        choices=["latest", "none"],
        default="latest",
        help="Deduplicate results by latest or none",
    )
    p_convert.set_defaults(_handler=_handle_results_convert)


def _handle_results_validate(args: argparse.Namespace, logger: logging.Logger) -> int:
    in_path = args.input_path
    out_path = args.output_path
    if os.path.isdir(in_path):
        paths: list[str] = []
        if args.recursive:
            for dirpath, _, filenames in os.walk(in_path):
                for filename in filenames:
                    if filename.lower().endswith(".jsonl"):
                        paths.append(os.path.join(dirpath, filename))
        else:
            for filename in os.listdir(in_path):
                p = os.path.join(in_path, filename)
                if os.path.isfile(p) and filename.lower().endswith(".jsonl"):
                    paths.append(p)

        paths.sort()
        reports = []
        total_rows = 0
        ok_rows = 0
        failed_rows = 0
        failed_files = 0

        for p in paths:
            logger.info("validating results file", extra={"path": p})
            res = validate_results_file(p)
            total_rows += res.total
            ok_rows += res.ok
            failed_rows += res.failed
            if res.failed:
                failed_files += 1
            reports.append(
                {
                    "path": p,
                    "total": res.total,
                    "ok": res.ok,
                    "failed": res.failed,
                    "errors": [asdict(e) for e in res.errors],
                }
            )

        out_obj = {
            "root": in_path,
            "recursive": args.recursive,
            "total_files": len(paths),
            "total_rows": total_rows,
            "ok_rows": ok_rows,
            "failed_rows": failed_rows,
            "failed_files": failed_files,
            "reports": reports,
        }

        logger.info(
            "validated results dir",
            extra={
                "root": in_path,
                "recursive": args.recursive,
                "total_files": len(paths),
                "failed_files": failed_files,
                "total_rows": total_rows,
                "ok_rows": ok_rows,
                "failed_rows": failed_rows,
            },
        )

        if args.output_path:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out_obj, f, ensure_ascii=False, indent=2)
            logger.info("wrote results validation report", extra={"path": out_path})

        return 2 if failed_files > 0 else 0

    report = validate_results_file(in_path)
    logger.info(
        "validated results file",
        extra={
            "path": in_path,
            "total": report.total,
            "ok": report.ok,
            "failed": report.failed,
        },
    )

    if args.output_path:
        out_obj = {
            "path": in_path,
            "total": report.total,
            "ok": report.ok,
            "failed": report.failed,
            "errors": [asdict(e) for e in report.errors],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)
        logger.info("wrote results validation report", extra={"path": out_path})

    if report.failed:
        for e in report.errors[:20]:
            logger.error(
                "results validation error",
                extra={
                    "path": in_path,
                    "line_no": e.line_no,
                    "error": e.error,
                },
            )
        return 2

    return 0


def _handle_results_convert(args: argparse.Namespace, logger: logging.Logger) -> int:
    out = convert_results_file(args.input_path, args.output_path, args.dedup)
    logger.info(
        "converted results file",
        extra={
            "in": args.input_path,
            "out": args.output_path,
            "dedup": args.dedup,
            "total": out.total,
            "ok": out.ok,
            "failed": out.failed,
            "written": out.written,
        },
    )
    if out.failed:
        for e in out.errors[:20]:
            logger.error(
                "results convert error",
                extra={"path": args.input_path, "line_no": e.line_no, "error": e.error},
            )
        return 2
    return 0
