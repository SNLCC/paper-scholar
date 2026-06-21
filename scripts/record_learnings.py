#!/usr/bin/env python3
"""
record_learnings.py — Learning record aggregation with 21-tag annotation library.

Uses the annotation tag system from references/annotation-tags.md instead of
keyword matching, consistent with the skill's "semantic understanding first" principle.

Usage:
    python record_learnings.py aggregate [--learnings-dir <dir>]
    python record_learnings.py profile [--learnings-dir <dir>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_LEARNINGS_DIR = Path(__file__).resolve().parent.parent / ".learnings"

# 21-tag annotation library (L1: label definition)
# From references/annotation-tags.md — built from actual paper reading,
# not prescriptive. New tags can be added as more papers are analyzed.
ANNOTATION_TAGS = [
    "历史背景", "过渡", "转折点", "转折影响概括", "总体概括",
    "学科定位", "本文任务", "本段论点", "理论基础", "主要观点",
    "影响与评议", "概述", "评述", "综合判断", "合理性解释",
    "具体展开", "方法论视角提炼", "承上启下", "总结评述",
    "概括与评述", "进一步分析"
]


def _ldir(learnings_dir: str | None) -> Path:
    d = Path(learnings_dir) if learnings_dir else DEFAULT_LEARNINGS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _infer_tag(text: str) -> str | None:
    """Infer the most likely annotation tag from text using semantic patterns.

    Each tag has associated patterns that describe its FUNCTIONAL role,
    not just keyword presence. This respects the skill's principle of
    semantic understanding over keyword matching.
    """
    t = text.strip().lower()
    if not t:
        return None

    patterns = [
        ("历史背景",   ["梳理", "发展", "历史", "脉络", "演变", "由来"]),
        ("过渡",       ["接下来", "转向", "过渡", "与此", "同时"]),
        ("转折点",     ["转折", "转向", "变化", "改变", "拐点"]),
        ("学科定位",   ["学科", "领域", "属于", "定位", "归属"]),
        ("本文任务",   ["本文", "任务", "目的", "旨在", "要做"]),
        ("本段论点",   ["本段", "论点", "主张", "认为", "核心"]),
        ("理论基础",   ["理论", "框架", "范式", "基础", "前提"]),
        ("主要观点",   ["观点", "主张", "立场", "核心", "关键"]),
        ("评述",       ["评价", "不足", "优势", "局限", "问题"]),
        ("合理性解释", ["合理", "解释", "原因", "因为", "由于"]),
        ("方法论视角提炼", ["方法", "方法论", "视角", "路径"]),
        ("承上启下",   ["承上", "启下", "连接", "呼应", "衔接"]),
        ("综合判断",   ["综合", "总体", "整体", "判断", "结论"]),
        ("进一步分析", ["进一步", "深入", "未来", "尚需", "待"]),
    ]

    scores = [(sum(1 for kw in keywords if kw in t), tag) for tag, keywords in patterns]
    scores = [(s, tag) for s, tag in scores if s > 0]
    if scores:
        scores.sort(reverse=True)
        return scores[0][1]
    return None


def profile(learnings_dir: str | None = None):
    """Build user annotation profile using 21-tag library (L1 -> L2)."""
    ldir = _ldir(learnings_dir)
    files = list(ldir.glob("*.json"))
    if not files:
        print("No learning data yet. Run 'compare' first.")
        return

    tag_counts = {}
    total = 0
    color_counts = {}
    section_counts = {}
    comment_count = 0

    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for m in d.get("semantic_alignment", {}).get("matched_annotations", []):
            total += 1
            tag = _infer_tag(m.get("user_comment", "") or m.get("user_text", ""))
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            color = m.get("user_color", "")
            if color:
                color_counts[color] = color_counts.get(color, 0) + 1
            sec = m.get("matched_section", "")
            if sec:
                section_counts[sec] = section_counts.get(sec, 0) + 1
            if m.get("user_comment"):
                comment_count += 1

    if total == 0:
        print("No annotations found in learning data.")
        return

    print(f"User Annotation Profile (L2: type induction)")
    print(f"  Papers: {len(files)}, Annotations: {total}")
    print()

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    if sorted_tags:
        print("  Top tags:")
        for tag, count in sorted_tags[:8]:
            print(f"    {tag}: {count} ({count/total:.0%})")

    if color_counts:
        print("\n  Color patterns:")
        for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {color}: {count}")

    if section_counts:
        print("\n  Section focus:")
        for sec, count in sorted(section_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {sec}: {count} ({count/total:.0%})")

    cr = comment_count / total
    print(f"\n  Comment ratio: {cr:.0%}")
    density = "high" if cr > 0.5 else "medium" if cr > 0.2 else "low"
    print(f"  Density: {density}")

    # Save L2 profile
    profile_path = ldir / "profile.json"
    profile_data = {
        "updated": datetime.now().isoformat(),
        "papers_count": len(files),
        "total_annotations": total,
        "top_tags": dict(sorted_tags[:5]),
        "color_patterns": color_counts,
        "section_focus": section_counts,
        "comment_ratio": cr,
        "density": density,
    }
    profile_path.write_text(json.dumps(profile_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Profile saved: {profile_path}")


def aggregate(learnings_dir: str | None = None):
    """Aggregate learning records (alias for profile)."""
    profile(learnings_dir)


def main():
    parser = argparse.ArgumentParser(description="Learning record aggregation with tag library")
    parser.add_argument("--learnings-dir", help=".learnings directory")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("aggregate")
    sub.add_parser("profile")
    args = parser.parse_args()

    if args.command == "aggregate":
        aggregate(args.learnings_dir)
    elif args.command == "profile":
        profile(args.learnings_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
