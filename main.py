# Author: urumb
import os
import argparse

from backend.app.services.audit_runner import run_audit_on_code


def read_file(file_path):
    """Read a file and return its contents as a string."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """CLI entry point for the Multi-Agent Code Auditor."""
    parser = argparse.ArgumentParser(description="Multi-Agent Autonomous Code Auditor")
    parser.add_argument("file", help="Path to the code file to audit")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return

    code = read_file(args.file)
    print(f"Starting Audit for: {args.file}")

    # Run audit via shared service
    try:
        output = run_audit_on_code(code)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    print("\n" + "="*50)
    print("FINAL AUDIT REPORT")
    print("="*50 + "\n")
    print(output.get("final_report", "No report generated."))

    # Save report to file
    report_path = args.file + ".audit_report.md"
    with open(report_path, "w", encoding='utf-8') as f:
        f.write(output.get("final_report", ""))
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
