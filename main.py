# Author: urumb
import os
import argparse
from src.graph import graph
from src.config import Config

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    # Validate Config
    Config.validate()

    parser = argparse.ArgumentParser(description="Multi-Agent Autonomous Code Auditor")
    parser.add_argument("file", help="Path to the code file to audit")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File '{args.file}' not found.")
        return

    code = read_file(args.file)
    print(f"Starting Audit for: {args.file}")
    
    initial_state = {
        "original_code": code,
        "code_snippets": [],
        "security_analysis": [],
        "performance_analysis": [],
        "past_audits": [],
        "final_report": ""
    }

    # Run Graph
    output = graph.invoke(initial_state)

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
