#!/usr/bin/env python3
"""
compare_annotations.py — Compare semantic analysis vs user Zotero annotations.

Produces a structured comparison report and writes learning data
to the .learnings/ directory.

Usage:
    python compare_annotations.py compare <analysis.json> <annotations.json> [--learnings-dir <dir>]
    python compare_annotations.py summary [--learnings-dir <dir>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_LEARNINGS_DIR = Path(__file__).resolve().parent.parent / ".learnings"


def _ldir(learnings_dir: str | None) -> Path:
    d = Path(learnings_dir) if learnings_dir else DEFAULT_LEARNINGS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def compare(analysis_path: str, annotations_path: str, learnings_dir: str | None = None):
    """Compare skill analysis vs user annotations and record differences."""
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    annotations = json.loads(Path(annotations_path).read_text(encoding="utf-8"))
    ldir = _ldir(learnings_dir)

    paper_id = analysis.get("paper_id", "unknown")

    # Count annotations
    skill_ann_count = sum(
        len(p.get("sentences", []))
        for s in analysis.get("sections", [])
        for p in s.get("paragraphs", [])
    )
    user_ann_count = len(annotations) if isinstance(annotations, list) else 0

    # Extract notable discrepancies
    discrepancies = []
    if isinstance(annotations, list):
        for ann in annotations:
            text = ann.get("text", "").strip()
            comment = ann.get("comment", "").strip()
            if text:
                discrepancies.append({
                    "user_text": text[:80],
                    "user_comment": comment,
                    "user_color": ann.get("color", ""),
                    "page": ann.get("page", ""),
                })

    report = {
        "paper_id": paper_id,
        "title": analysis.get("title", ""),
        "compared_at": datetime.now().isoformat(),
        "comparison_summary": {
            "skill_annotations": skill_ann_count,
            "user_annotations": user_ann_count,
        },
        "notable_discrepancies": discrepancies,
        "learning_points": [
            "Review discrepancies above for annotation pattern insights."
        ],
    }

    dest = ldir / f"{paper_id}.json"
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comparison saved → {dest}")

    # Print summary
    print(f"\nComparison Summary for '{analysis.get('title', paper_id)}':")
    print(f"  Skill annotations: {skill_ann_count}")
    print(f"  User annotations:  {user_ann_count}")
    print(f"  Discrepancies logged: {len(discrepancies)}")
    if discrepancies:
        print("\n  Top discrepancies:")
        for d in discrepancies[:5]:
            print(f"    p.{d['page']} [{d['user_color']}] {d['user_text'][:50]}")
            if d['user_comment']:
                print(f"      Comment: {d['user_comment'][:60]}")


def summary(learnings_dir: str | None = None):
    """Show aggregated learning summary."""
    ldir = _ldir(learnings_dir)
    files = list(ldir.glob("*.json"))
    if not files:
        print("No learning data yet. Run 'compare' first.")
        return
    print(f"Learning records: {len(files)}")
    for f in sorted(files):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            title = d.get("title", f.stem)[:50]
            summary = d.get("comparison_summary", {})
            print(f"  {f.stem:<30} {title:<50} "
                  f"skill={summary.get('skill_annotations',0)} "
                  f"user={summary.get('user_annotations',0)}")
        except Exception:
            print(f"  {f.stem:<30} (invalid)")


def main():
    parser = argparse.ArgumentParser(description="Compare analysis vs user annotations")
    parser.add_argument("--learnings-dir", help=".learnings directory")
    sub = parser.add_subparsers(dest="command")

    p_comp = sub.add_parser("compare")
    p_comp.add_argument("analysis_json")
    p_comp.add_argument("annotations_json")

    sub.add_parser("summary")

    args = parser.parse_args()

    if args.command == "compare":
        compare(args.analysis_json, args.annotations_json, args.learnings_dir)
    elif args.command == "summary":
        summary(args.learnings_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
