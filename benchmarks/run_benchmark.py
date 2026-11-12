# Author: urumb
"""Score the auditor against labeled sample files.

Each file in benchmarks/cases marks real issues with a trailing comment:

    query = "SELECT ... " + name  # EXPECT: security

The markers are stripped before auditing (so neither the tools nor the LLM
can see them) and only used for scoring. A reported finding matches an
expected issue when it has the same category and its line is within
LINE_TOLERANCE lines. Findings without a verified line can't match and
count as false positives — an unlocatable finding is not useful to a user.

Usage:
    python -m benchmarks.run_benchmark --static-only   # tools only, no Ollama needed
    python -m benchmarks.run_benchmark                 # full pipeline (needs Ollama)
    python -m benchmarks.run_benchmark --json out.json # also save raw results
"""
import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASES_DIR = Path(__file__).resolve().parent / "cases"
LINE_TOLERANCE = 2
_MARKER = re.compile(r"\s*(#|//)\s*EXPECT:\s*(security|performance|quality)\s*$")


@dataclass
class CaseResult:
    name: str
    expected: List[Tuple[int, str]]
    findings: List[Dict]
    matched_expected: int = 0
    true_positives: int = 0
    seconds: float = 0.0
    error: Optional[str] = None
    missed: List[Tuple[int, str]] = field(default_factory=list)
    false_positives: List[Dict] = field(default_factory=list)


def load_case(path: Path) -> Tuple[str, List[Tuple[int, str]]]:
    """Return (code without markers, [(line, category), ...])."""
    expected = []
    clean_lines = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = _MARKER.search(line)
        if match:
            expected.append((number, match.group(2)))
            line = line[: match.start()]
        clean_lines.append(line)
    return "\n".join(clean_lines) + "\n", expected


def score(expected: List[Tuple[int, str]], findings: List[Dict]) -> Tuple[int, int, list, list]:
    """Return (expected issues found, findings that were correct, missed, false positives)."""
    found = set()
    correct = 0
    false_positives = []
    for f in findings:
        line, category = f.get("line"), f.get("agent")
        hits = [
            i for i, (exp_line, exp_cat) in enumerate(expected)
            if line is not None and exp_cat == category and abs(exp_line - line) <= LINE_TOLERANCE
        ]
        if hits:
            correct += 1
            found.update(hits)
        else:
            false_positives.append(f)
    missed = [e for i, e in enumerate(expected) if i not in found]
    return len(found), correct, missed, false_positives


def audit_static_only(code: str, file_path: str) -> List[Dict]:
    from src.findings import merge_findings
    from src.static_analysis import run_static_analysis

    return merge_findings([], run_static_analysis(code, file_path), code)


def audit_full(code: str, file_path: str, depth: str) -> List[Dict]:
    from backend.app.services.audit_runner import run_audit_on_code

    output = run_audit_on_code(code, file_path=file_path, depth=depth)
    return json.loads(output.get("final_report") or "{}").get("findings", [])


def run(static_only: bool, depth: str = "full", only: Optional[str] = None) -> List[CaseResult]:
    results = []
    for path in sorted(CASES_DIR.iterdir()):
        if path.suffix not in (".py", ".js", ".ts") or (only and only not in path.name):
            continue
        code, expected = load_case(path)
        result = CaseResult(name=path.name, expected=expected, findings=[])
        start = time.time()
        try:
            result.findings = (
                audit_static_only(code, path.name) if static_only else audit_full(code, path.name, depth)
            )
        except Exception as exc:
            result.error = str(exc)
        result.seconds = round(time.time() - start, 1)
        (result.matched_expected, result.true_positives,
         result.missed, result.false_positives) = score(expected, result.findings)
        results.append(result)
    return results


def summarize(results: List[CaseResult]) -> Dict[str, float]:
    expected = sum(len(r.expected) for r in results)
    found = sum(r.matched_expected for r in results)
    reported = sum(len(r.findings) for r in results)
    correct = sum(r.true_positives for r in results)
    return {
        "expected": expected,
        "found": found,
        "reported": reported,
        "correct": correct,
        "recall": round(found / expected, 3) if expected else 1.0,
        "precision": round(correct / reported, 3) if reported else 1.0,
        "seconds": round(sum(r.seconds for r in results), 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--static-only", action="store_true", help="run only bandit/ruff/semgrep (no LLM)")
    parser.add_argument("--depth", choices=["quick", "full"], default="full")
    parser.add_argument("--case", help="only run cases whose filename contains this text")
    parser.add_argument("--json", help="write detailed results to this file")
    parser.add_argument("-v", "--verbose", action="store_true", help="list missed issues and false positives")
    args = parser.parse_args()

    results = run(args.static_only, args.depth, args.case)
    mode = "static analysis only" if args.static_only else f"full pipeline ({args.depth})"
    print(f"\nBenchmark - {mode}\n")
    print(f"{'case':28} {'expected':>8} {'found':>6} {'reported':>9} {'correct':>8} {'secs':>6}")
    for r in results:
        print(
            f"{r.name:28} {len(r.expected):>8} {r.matched_expected:>6} {len(r.findings):>9} "
            f"{r.true_positives:>8} {r.seconds:>6}" + (f"  ERROR: {r.error[:60]}" if r.error else "")
        )
        if args.verbose:
            for line, cat in r.missed:
                print(f"    missed      line {line:>3} [{cat}]")
            for f in r.false_positives:
                print(f"    unexpected  line {str(f.get('line')):>3} [{f.get('agent')}] {f.get('source')}: {f.get('issue')}")

    totals = summarize(results)
    print(
        f"\nRecall {totals['recall']:.0%} ({totals['found']}/{totals['expected']} labeled issues found)   "
        f"Precision {totals['precision']:.0%} ({totals['correct']}/{totals['reported']} findings correct)   "
        f"{totals['seconds']}s\n"
    )

    if args.json:
        Path(args.json).write_text(json.dumps({
            "mode": mode,
            "totals": totals,
            "cases": [
                {"name": r.name, "expected": r.expected, "findings": r.findings, "error": r.error,
                 "missed": r.missed, "seconds": r.seconds}
                for r in results
            ],
        }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
