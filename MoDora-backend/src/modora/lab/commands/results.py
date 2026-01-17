from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import logging
import os

from modora.core.results_io import convert_results_file, validate_results_file


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

    p_convert_dir = sub.add_parser(
        "results-convert-dir", help="Convert all results JSONL files in a directory"
    )
    p_convert_dir.add_argument(
        "--in",
        dest="input_path",
        required=True,
        help="Path to input directory containing results JSONL files",
    )
    p_convert_dir.add_argument(
        "--out",
        dest="output_path",
        required=True,
        help="Path to output directory for converted JSONL files",
    )
    p_convert_dir.add_argument(
        "--dedup",
        choices=["latest", "none"],
        default="latest",
        help="Deduplicate results by latest or none",
    )
    p_convert_dir.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively find .jsonl files under input directory",
    )
    p_convert_dir.set_defaults(_handler=_handle_results_convert_dir)


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


def _handle_results_convert_dir(
    args: argparse.Namespace, logger: logging.Logger
) -> int:
    in_dir = args.input_path
    out_dir = args.output_path

    if not os.path.isdir(in_dir):
        logger.error("input is not a directory", extra={"in": in_dir})
        return 2

    os.makedirs(out_dir, exist_ok=True)

    paths: list[str] = []
    if args.recursive:
        for dirpath, _, filenames in os.walk(in_dir):
            for filename in filenames:
                if filename.lower().endswith(".jsonl"):
                    paths.append(os.path.join(dirpath, filename))
    else:
        for filename in os.listdir(in_dir):
            p = os.path.join(in_dir, filename)
            if os.path.isfile(p) and filename.lower().endswith(".jsonl"):
                paths.append(p)

    paths.sort()
    if not paths:
        logger.error(
            "no .jsonl files found", extra={"in": in_dir, "recursive": args.recursive}
        )
        return 2

    failed_files = 0
    total_rows = 0
    ok_rows = 0
    failed_rows = 0
    written_rows = 0

    for p in paths:
        rel = os.path.relpath(p, in_dir)
        out_path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        res = convert_results_file(p, out_path, args.dedup)
        total_rows += res.total
        ok_rows += res.ok
        failed_rows += res.failed
        written_rows += res.written

        if res.failed:
            failed_files += 1
            logger.error(
                "results convert failed",
                extra={
                    "in": p,
                    "out": out_path,
                    "dedup": args.dedup,
                    "total": res.total,
                    "ok": res.ok,
                    "failed": res.failed,
                    "written": res.written,
                },
            )
            for e in res.errors[:20]:
                logger.error(
                    "results convert error",
                    extra={"path": p, "line_no": e.line_no, "error": e.error},
                )
        else:
            logger.info(
                "converted results file",
                extra={
                    "in": p,
                    "out": out_path,
                    "dedup": args.dedup,
                    "total": res.total,
                    "ok": res.ok,
                    "failed": res.failed,
                    "written": res.written,
                },
            )

    logger.info(
        "converted results dir",
        extra={
            "in": in_dir,
            "out": out_dir,
            "recursive": args.recursive,
            "dedup": args.dedup,
            "total_files": len(paths),
            "failed_files": failed_files,
            "total_rows": total_rows,
            "ok_rows": ok_rows,
            "failed_rows": failed_rows,
            "written_rows": written_rows,
        },
    )

    return 2 if failed_files else 0
