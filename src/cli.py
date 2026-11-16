# Author: urumb
"""Command-line interface: audit a folder or file without the web UI.

    python main.py scan .                                  # full audit (needs Ollama)
    python main.py scan src --static-only --fail-on high   # fast, no Ollama: for CI
    python main.py scan . --format sarif -o results.sarif  # for GitHub code scanning

Exit codes: 0 = no finding at or above --fail-on, 1 = at least one,
2 = usage or runtime error.
"""
import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]
EXIT_OK, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def _collect(target: str, exclude: List[str]):
    from backend.app.schemas.code_file import CodeFile
    from backend.app.services.input_processor import ALLOWED_EXTENSIONS, collect_source_files

    if os.path.isfile(target):
        if os.path.splitext(target)[1].lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {target}")
        with open(target, "r", encoding="utf-8", errors="ignore") as fh:
            return [CodeFile(path=os.path.basename(target), content=fh.read())]
    if os.path.isdir(target):
        return collect_source_files(target, label=target, exclude=exclude)
    raise ValueError(f"No such file or folder: {target}")


def _audit_static(file) -> Dict[str, Any]:
    from src.findings import compute_risk_score, merge_findings
    from src.static_analysis import run_static_analysis

    findings = merge_findings([], run_static_analysis(file.content, file.path), file.content)
    risk = compute_risk_score(findings)
    return {"file_path": file.path, "findings": findings, "warnings": [], "cached": False,
            "risk_score": risk["risk_score"], "max_severity": risk["max_severity"], "error": None}


def _audit_full(file, total: int, depth: str, use_cache: bool) -> Dict[str, Any]:
    from backend.app.services.audit_jobs import audit_file

    result = audit_file(file, total, depth, use_cache=use_cache)
    report = json.loads(result["final_report"] or "{}")
    return {"file_path": file.path, "findings": report.get("findings", []),
            "warnings": report.get("warnings", []), "cached": result.get("cached", False),
            "risk_score": result["risk_score"], "max_severity": result["max_severity"],
            "error": result["error"]}


def _at_or_above(severity: str, threshold: str) -> bool:
    return SEVERITY_ORDER.index(severity) <= SEVERITY_ORDER.index(threshold)


def _print_text(results: List[Dict[str, Any]], out) -> None:
    total = 0
    for r in results:
        if r["error"]:
            print(f"\n{r['file_path']}: ERROR {r['error']}", file=out)
            continue
        if not r["findings"] and not r["warnings"]:
            continue
        note = " (unchanged, previous result)" if r.get("cached") else ""
        print(f"\n{r['file_path']}{note}", file=out)
        for w in r["warnings"]:
            print(f"  ! {w}", file=out)
        for f in r["findings"]:
            total += 1
            line = f":{f['line']}" if f.get("line") else ""
            rule = f" [{f['rule_id']}]" if f.get("rule_id") else ""
            print(f"  {f.get('severity', 'Low'):8} {r['file_path']}{line}  {f.get('issue', '')}{rule}"
                  f"  ({f.get('agent', '')}, {f.get('source', 'llm')})", file=out)
    counts = {s: sum(1 for r in results for f in r["findings"] if f.get("severity") == s) for s in SEVERITY_ORDER}
    summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n) or "no issues"
    print(f"\n{len(results)} file(s) audited, {total} finding(s): {summary}", file=out)


def _scan(args) -> int:
    start = time.time()
    try:
        files = _collect(args.target, args.exclude)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if not files:
        print("No auditable source files found.", file=sys.stderr)
        return EXIT_OK
    if args.max_files and len(files) > args.max_files:
        print(f"note: auditing the first {args.max_files} of {len(files)} files (--max-files)", file=sys.stderr)
        files = files[: args.max_files]

    results = []
    for i, file in enumerate(files, start=1):
        if not args.quiet:
            print(f"[{i}/{len(files)}] {file.path}", file=sys.stderr)
        try:
            results.append(
                _audit_static(file) if args.static_only
                else _audit_full(file, len(files), args.depth, not args.no_cache)
            )
        except Exception as exc:  # one bad file must not stop the scan
            results.append({"file_path": file.path, "findings": [], "warnings": [], "cached": False,
                            "risk_score": 0.0, "max_severity": "Low", "error": str(exc)})

    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.format == "sarif":
            from src.sarif import to_sarif
            json.dump(to_sarif(results), out, indent=2)
            out.write("\n")
        elif args.format == "json":
            json.dump({"files": results, "duration": round(time.time() - start, 2)}, out, indent=2)
            out.write("\n")
        else:
            _print_text(results, out)
    finally:
        if args.output:
            out.close()
            print(f"Wrote {args.format} report to {args.output}", file=sys.stderr)

    for r in results:
        for w in r["warnings"]:
            print(f"warning: {r['file_path']}: {w}", file=sys.stderr)
    if any(r["error"] for r in results):
        print("warning: some files could not be audited (see report)", file=sys.stderr)

    if args.fail_on == "none":
        return EXIT_OK
    threshold = args.fail_on.capitalize()
    hit = any(_at_or_above(f.get("severity", "Low"), threshold) for r in results for f in r["findings"])
    return EXIT_FINDINGS if hit else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Multi-Agent Code Auditor: free, local code auditing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="audit a folder or a single file")
    scan.add_argument("target", help="folder or file to audit")
    scan.add_argument("--depth", choices=["quick", "full"], default="full",
                      help="quick = security only; full = all agents (default)")
    scan.add_argument("--static-only", action="store_true",
                      help="only run bandit/ruff/semgrep: fast, no Ollama needed")
    scan.add_argument("--fail-on", choices=["critical", "high", "medium", "low", "none"], default="high",
                      help="exit with code 1 if any finding is at or above this severity (default: high)")
    scan.add_argument("--format", choices=["text", "json", "sarif"], default="text")
    scan.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    scan.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                      help="skip paths matching this glob (repeatable), e.g. --exclude 'tests/*'")
    scan.add_argument("--max-files", type=int, default=0, help="audit at most this many files")
    scan.add_argument("--no-cache", action="store_true",
                      help="re-audit every file even if it hasn't changed since the last audit")
    scan.add_argument("-q", "--quiet", action="store_true", help="don't print progress")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Keep stdout clean for the report; library logs go to stderr, quietly.
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    if args.command == "scan":
        return _scan(args)
    return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
