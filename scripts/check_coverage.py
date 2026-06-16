#!/usr/bin/env python3
"""
check_coverage.py — Fine analysis coverage checker.

Ensures 100% coverage across the three levels of analysis:
chapter, paragraph, and sentence.

Usage:
    python check_coverage.py report <analysis.json>
    python check_coverage.py verify <analysis.json> <original_text.txt>
"""

import argparse
import json
import sys
from pathlib import Path


def count_sentences(text: str) -> int:
    """Rough sentence count for academic text (handles zh/en)."""
    import re
    # English sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Chinese sentence boundaries (。！？)
    all_sentences = []
    for s in sentences:
        # Split Chinese
        parts = re.split(r'(?<=[。！？])', s)
        all_sentences.extend(p for p in parts if p.strip())
    return len([s for s in all_sentences if len(s.strip()) > 5])


def generate_report(analysis_path: str):
    """Generate a coverage report from an analysis JSON."""
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    sections = analysis.get("sections", [])

    total_chapters = len(sections)
    total_paragraphs = sum(len(s.get("paragraphs", [])) for s in sections)
    total_sentences = sum(
        len(p.get("sentences", []))
        for s in sections
        for p in s.get("paragraphs", [])
    )

    print("=" * 60)
    print("Coverage Report")
    print("=" * 60)
    print(f"Paper: {analysis.get('title', 'Unknown')}")
    print(f"Paper ID: {analysis.get('paper_id', 'N/A')}")
    print()

    # Chapter level
    print(f"Chapters analyzed: {total_chapters}")
    if total_chapters > 0:
        for i, sec in enumerate(sections):
            p_count = len(sec.get("paragraphs", []))
            s_count = sum(len(p.get("sentences", [])) for p in sec.get("paragraphs", []))
            bar_length = 20
            filled = int(bar_length * (s_count / max(s_count, 1)))
            bar = "█" * min(filled, bar_length) + "░" * (bar_length - min(filled, bar_length))
            title = sec.get("title", f"Chapter {i+1}")[:40]
            print(f"  [{bar}] {title} ({p_count} paras, {s_count} sentences)")

    print()
    print(f"Total paragraphs: {total_paragraphs}")
    print(f"Total sentences:  {total_sentences}")
    print()

    # Check for gaps
    gaps = []
    for i, sec in enumerate(sections):
        for j, para in enumerate(sec.get("paragraphs", [])):
            if "sentences" not in para or len(para.get("sentences", [])) == 0:
                gaps.append(f"  Chapter {i+1}, Paragraph {j+1}: no sentence analysis")
    if gaps:
        print("Gaps found:")
        for g in gaps:
            print(g)
    else:
        print("✅ No coverage gaps detected at paragraph level.")

    print("=" * 60)


def verify_against_original(analysis_path: str, original_text_path: str):
    """Verify analysis coverage against original text."""
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    original = Path(original_text_path).read_text(encoding="utf-8")

    total_original_sentences = count_sentences(original)

    sections = analysis.get("sections", [])
    analyzed_sentences = sum(
        len(p.get("sentences", []))
        for s in sections
        for p in s.get("paragraphs", [])
    )

    ratio = analyzed_sentences / max(total_original_sentences, 1)

    print(f"Original text: ~{total_original_sentences} sentences")
    print(f"Analyzed:      {analyzed_sentences} sentences")
    print(f"Coverage:      {ratio:.1%}")
    print()

    if ratio >= 0.95:
        print("✅ Coverage meets 95% threshold.")
    elif ratio >= 0.80:
        print("⚠️  Coverage is acceptable but could be improved (target: 95%).")
    else:
        print("❌ Coverage below acceptable threshold. More analysis needed.")
        print(f"   Uncovered: ~{total_original_sentences - analyzed_sentences} sentences")

    return ratio


def main():
    parser = argparse.ArgumentParser(description="Check analysis coverage")
    sub = parser.add_subparsers(dest="command")

    p_report = sub.add_parser("report", help="Generate coverage report from analysis JSON")
    p_report.add_argument("analysis_json")

    p_verify = sub.add_parser("verify", help="Verify coverage against original text")
    p_verify.add_argument("analysis_json")
    p_verify.add_argument("original_text")

    args = parser.parse_args()

    if args.command == "report":
        generate_report(args.analysis_json)
    elif args.command == "verify":
        verify_against_original(args.analysis_json, args.original_text)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
