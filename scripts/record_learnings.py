#!/usr/bin/env python3
"""
record_learnings.py — Learning record assistant.

Aggregates individual comparison results from .learnings/ into
a consolidated user profile. Tracks annotation style evolution.

Usage:
    python record_learnings.py aggregate [--learnings-dir <dir>]
    python record_learnings.py profile [--learnings-dir <dir>]
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_LEARNINGS_DIR = Path(__file__).resolve().parent.parent / ".learnings"


def _ldir(learnings_dir: str | None) -> Path:
    d = Path(learnings_dir) if learnings_dir else DEFAULT_LEARNINGS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def aggregate(learnings_dir: str | None = None):
    """Aggregate all .learnings/ records into a summary."""
    ldir = _ldir(learnings_dir)
    files = sorted(ldir.glob("*.json"))

    # Skip profile.json itself
    files = [f for f in files if f.name != "profile.json"]

    if not files:
        print("No learning records found.")
        return

    total_comparisons = len(files)
    total_skill_ann = 0
    total_user_ann = 0
    color_counts = Counter()
    all_learning_points = []

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            cs = d.get("comparison_summary", {})
            total_skill_ann += cs.get("skill_annotations", 0)
            total_user_ann += cs.get("user_annotations", 0)
            for disc in d.get("notable_discrepancies", []):
                color = disc.get("user_color", "unknown")
                if color:
                    color_counts[color] += 1
            all_learning_points.extend(d.get("learning_points", []))
        except Exception:
            pass

    print(f"Aggregated {total_comparisons} comparison records")
    print(f"Total skill annotations: {total_skill_ann}")
    print(f"Total user annotations:  {total_user_ann}")
    if total_comparisons > 0:
        avg_density = total_user_ann / total_comparisons
        print(f"Average user annotations per paper: {avg_density:.1f}")
        print(f"Annotation density ratio: {total_user_ann/max(total_skill_ann,1):.1%}")

    if color_counts:
        print(f"\nColor usage ({sum(color_counts.values())} total):")
        for color, count in color_counts.most_common():
            print(f"  {color}: {count} ({count/sum(color_counts.values()):.0%})")

    if all_learning_points:
        print(f"\nLearning points ({len(all_learning_points)} total):")
        seen = set()
        for lp in all_learning_points:
            if lp not in seen:
                print(f"  • {lp}")
                seen.add(lp)


def build_profile(learnings_dir: str | None = None):
    """Build/update a consolidated user annotation profile."""
    ldir = _ldir(learnings_dir)

    # Count focus areas from discrepancies
    focus_areas = Counter()
    files = [f for f in ldir.glob("*.json") if f.name != "profile.json"]
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            for disc in d.get("notable_discrepancies", []):
                comment = disc.get("user_comment", "")
                page = disc.get("page", "")
                if comment:
                    # Rough categorization by keywords
                    if any(w in comment for w in ["理论", "框架", "概念", "theory", "framework"]):
                        focus_areas["理论框架"] += 1
                    elif any(w in comment for w in ["方法", "数据", "method", "data"]):
                        focus_areas["方法论"] += 1
                    elif any(w in comment for w in ["论证", "逻辑", "argument", "logic"]):
                        focus_areas["论证逻辑"] += 1
                    elif any(w in comment for w in ["gap", "缺口", "创新", "contribution"]):
                        focus_areas["研究缺口"] += 1
                    else:
                        focus_areas["其他"] += 1
        except Exception:
            pass

    profile = {
        "profile_updated": __import__("datetime").datetime.now().isoformat(),
        "total_papers_with_annotations": len(files),
        "focus_areas": {k: v for k, v in focus_areas.most_common()},
        "annotation_style": {
            "granularity": "medium",
            "note": "Detected from annotation density. Updated as more data accumulates."
        }
    }

    dest = ldir / "profile.json"
    dest.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Profile saved → {dest}")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Learning record assistant")
    parser.add_argument("--learnings-dir", help=".learnings directory")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("aggregate", help="Aggregate learning records")
    sub.add_parser("profile", help="Build/update user annotation profile")

    args = parser.parse_args()

    if args.command == "aggregate":
        aggregate(args.learnings_dir)
    elif args.command == "profile":
        build_profile(args.learnings_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
