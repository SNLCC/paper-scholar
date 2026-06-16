#!/usr/bin/env python3
"""
analyze_paper.py — Journal scoring, topic analysis, multi-dimension scoring.

This script provides the scoring framework for paper quality assessment.
It generates structured scoring output per references/quality-scoring.md.

Usage:
    python analyze_paper.py score <paper_metadata.json> [--output <path>]
    python analyze_paper.py template                    # Print scoring template
"""

import argparse
import json
import sys
from pathlib import Path


SCORING_TEMPLATE = {
    "paper_title": "",
    "overall_score": 0,
    "decision": "浏览",
    "dimensions": {
        "journal_level": {"score": 0, "max": 40, "detail": "", "confidence": "unknown"},
        "author_authority": {"score": 0, "max": 25, "detail": "", "confidence": "unknown"},
        "paper_characteristics": {"score": 0, "max": 35, "detail": "", "confidence": "unknown"},
    },
    "reading_depth": {"recommended": "浏览", "reason": ""},
    "adjustment_log": [],
}


def generate_scoring_template(output_path: str | None = None):
    """Print or save an empty scoring template."""
    text = json.dumps(SCORING_TEMPLATE, indent=2, ensure_ascii=False)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        print(f"Template saved to: {output_path}")
    else:
        print(text)


def main():
    parser = argparse.ArgumentParser(description="Paper quality analysis and scoring")
    sub = parser.add_subparsers(dest="command")

    p_score = sub.add_parser("score", help="Score a paper from metadata JSON")
    p_score.add_argument("metadata", help="Paper metadata JSON file path")
    p_score.add_argument("--output", "-o", help="Output scoring JSON path")

    p_temp = sub.add_parser("template", help="Generate an empty scoring template")
    p_temp.add_argument("--output", "-o", help="Output path")

    args = parser.parse_args()

    if args.command == "template":
        generate_scoring_template(args.output)
    elif args.command == "score":
        path = Path(args.metadata)
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)
        data = json.loads(path.read_text(encoding="utf-8"))
        # Scoring is performed by Codex using the quality-scoring.md reference.
        # This script provides the framework and stores the result.
        if args.output:
            Path(args.output).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"Scoring data saved to: {args.output}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
