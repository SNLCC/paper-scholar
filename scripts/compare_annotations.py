#!/usr/bin/env python3
"""
compare_annotations.py — Bidirectional semantic comparison of skill analysis
vs user Zotero annotations.

Produces a structured comparison report with semantic alignment:
  - Matches annotations to analysis sections by page
  - Computes overlap, skill-only, and user-only metrics
  - Identifies learning patterns (user focus, annotation style)
  - Writes learning data to .learnings/ directory

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


def _extract_skill_coverage(analysis: dict) -> dict:
    """Extract skill's analysis points keyed by page number for matching."""
    coverage = {}
    for section in analysis.get("sections", []):
        section_name = section.get("rhetorical_function", section.get("title", "?"))
        for para_idx, para in enumerate(section.get("paragraphs", [])):
            page = para.get("page", "?")
            if page not in coverage:
                coverage[page] = {
                    "section": section_name,
                    "skill_points": [],
                }
            for sent in para.get("sentences", []):
                coverage[page]["skill_points"].append({
                    "text": sent.get("text", "")[:120],
                    "function": sent.get("rhetorical_function", ""),
                    "para_index": para_idx,
                })
    return coverage


def _match_by_page(user_annotations: list, skill_coverage: dict) -> list:
    """Match each user annotation to the closest skill analysis point by page."""
    matched = []
    for ann in user_annotations:
        page = str(ann.get("page", "?")).strip()
        # Try exact page match first, then prefix match
        skill_info = skill_coverage.get(page)
        if not skill_info:
            # Try matching just the numeric part with exact numeric equality
            # (avoid false match of "1" with "10" or "11")
            try:
                page_num = int(page)
                for cov_page in skill_coverage:
                    try:
                        cov_num = int(cov_page)
                        if cov_num == page_num:
                            skill_info = skill_coverage[cov_page]
                            page = cov_page
                            break
                    except ValueError:
                        continue
            except ValueError:
                # Non-numeric page, fall back to substring match
                for cov_page in skill_coverage:
                    if page and cov_page and (page == cov_page or page in cov_page or cov_page in page):
                        skill_info = skill_coverage[cov_page]
                        page = cov_page
                        break

        ann_text = ann.get("text", "").strip()
        ann_comment = ann.get("comment", "").strip()

        entry = {
            "user_text": ann_text[:120],
            "user_comment": ann_comment,
            "user_color": ann.get("color", ""),
            "page": page,
            "matched_section": skill_info.get("section", "unknown") if skill_info else "unknown",
            "skill_nearby_points": [],
        }

        if skill_info:
            # Find the most semantically similar skill point
            best_score = 0.0
            for sp in skill_info["skill_points"]:
                # Simple text overlap similarity
                skill_text = sp["text"][:120]
                # Count character overlap
                if ann_text and skill_text:
                    ann_chars = set(ann_text)
                    skill_chars = set(skill_text)
                    if ann_chars:
                        overlap = len(ann_chars & skill_chars) / len(ann_chars)
                        if overlap > best_score:
                            best_score = overlap
                entry["skill_nearby_points"].append({
                    "text": skill_text,
                    "function": sp["function"],
                    "overlap_score": round(best_score, 2),
                })

            entry["best_match_score"] = round(best_score, 2)

        matched.append(entry)
    return matched


def _compute_comparison_metrics(skill_coverage: dict, matched: list, user_count: int) -> dict:
    """Compute overlap and divergence metrics."""
    skill_total = sum(
        len(info["skill_points"])
        for info in skill_coverage.values()
    )

    # Pages where both skill and user have annotations
    user_pages = set()
    for m in matched:
        if m["page"] != "?":
            user_pages.add(m["page"])
    skill_pages = set(skill_coverage.keys())

    overlap_pages = user_pages & skill_pages
    skill_only_pages = skill_pages - user_pages
    user_only_pages = user_pages - skill_pages

    # Estimate overlap count (annotations on same page)
    high_match = sum(1 for m in matched if m.get("best_match_score", 0) > 0.4)
    low_match = sum(1 for m in matched if 0 < m.get("best_match_score", 0) <= 0.4)
    no_match = sum(1 for m in matched if m.get("best_match_score", 0) == 0)

    return {
        "skill_annotations": skill_total,
        "user_annotations": user_count,
        "overlap_pages": len(overlap_pages),
        "skill_only_pages": len(skill_only_pages),
        "user_only_pages": len(user_only_pages),
        "user_annotations_high_overlap": high_match,
        "user_annotations_low_overlap": low_match,
        "user_annotations_no_overlap": no_match,
    }


def _derive_learning_points(matched: list, skill_coverage: dict, annotations: list) -> list:
    """Derive actionable learning points from the comparison."""
    points = []

    # 1. Color pattern analysis
    color_counts = {}
    for m in matched:
        c = m.get("user_color", "unknown")
        color_counts[c] = color_counts.get(c, 0) + 1
    if color_counts:
        dominant = max(color_counts, key=color_counts.get)
        points.append(
            f"User annotation color pattern: {dominant} is most used "
            f"({color_counts[dominant]}/{sum(color_counts.values())} annotations)"
        )

    # 2. Section focus analysis
    section_counts = {}
    for m in matched:
        sec = m.get("matched_section", "unknown")
        section_counts[sec] = section_counts.get(sec, 0) + 1
    if section_counts:
        top_section = max(section_counts, key=section_counts.get)
        points.append(
            f"User focus: '{top_section}' receives most annotations "
            f"({section_counts[top_section]}/{sum(section_counts.values())})"
        )

    # 3. Annotation granularity
    density = len(annotations) / max(sum(
        len(info["skill_points"])
        for info in skill_coverage.values()
    ), 1)
    if density < 0.3:
        points.append("User annotation density is low (<30% of skill coverage) — user prefers selective annotation")
    elif density > 0.7:
        points.append("User annotation density is high (>70%) — user prefers thorough annotation")
    else:
        points.append(f"User annotation density is moderate ({density:.0%}) — balanced approach")

    # 4. Comment ratio
    with_comments = sum(1 for m in matched if m.get("user_comment"))
    if matched:
        comment_ratio = with_comments / len(matched)
        if comment_ratio > 0.5:
            points.append(f"User frequently adds comments ({comment_ratio:.0%}) — values analytical notes")
        else:
            points.append(f"User mostly highlights without comments ({1-comment_ratio:.0%}) — prefers marking key points")

    # 5. Blind spots: pages user annotated that skill didn't cover
    user_pages = set(m["page"] for m in matched if m["page"] != "?")
    skill_pages = set(skill_coverage.keys())
    blind_spots = user_pages - skill_pages
    if blind_spots:
        points.append(
            f"Skill blind spots: {len(blind_spots)} pages annotated by user but not "
            f"covered by skill analysis (pages: {', '.join(sorted(blind_spots)[:5])})"
        )

    return points


def compare(analysis_path: str, annotations_path: str, learnings_dir: str | None = None):
    """Compare skill analysis vs user annotations with semantic alignment."""
    analysis = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    annotations = json.loads(Path(annotations_path).read_text(encoding="utf-8"))
    ldir = _ldir(learnings_dir)

    paper_id = analysis.get("paper_id", "unknown")
    user_anns = annotations if isinstance(annotations, list) else []

    # Extract skill coverage by page
    skill_coverage = _extract_skill_coverage(analysis)

    # Match user annotations to skill analysis
    matched = _match_by_page(user_anns, skill_coverage)

    # Compute metrics
    metrics = _compute_comparison_metrics(skill_coverage, matched, len(user_anns))

    # Derive learning points
    learning_points = _derive_learning_points(matched, skill_coverage, user_anns)

    report = {
        "paper_id": paper_id,
        "title": analysis.get("title", ""),
        "compared_at": datetime.now().isoformat(),
        "comparison_summary": metrics,
        "semantic_alignment": {
            "matched_annotations": matched[:20],  # Top 20 for brevity
            "total_matched": len(matched),
        },
        "learning_points": learning_points,
    }

    # Determine learning direction: does skill learn from user, or does user learn from skill?
    learning_direction = []
    if metrics["user_annotations"] > 0 and metrics["skill_annotations"] > 0:
        # If user has more annotations than skill coverage on overlapping pages, user may be more thorough
        if metrics["user_annotations_high_overlap"] > metrics["user_annotations_low_overlap"]:
            learning_direction.append("user_aligned: skill and user agree on most pages")
        if metrics["user_only_pages"] > 0:
            learning_direction.append(f"skill_blindspot: {metrics['user_only_pages']} pages user annotated but skill missed")
        if metrics["skill_only_pages"] > 0:
            learning_direction.append(f"user_blindspot: {metrics['skill_only_pages']} pages skill covered but user didn't annotate")
    elif metrics["user_annotations"] == 0:
        learning_direction.append("no_user_annotations: skill analysis stands alone, no user data to learn from")
    report["learning_direction"] = learning_direction

    dest = ldir / f"{paper_id}.json"
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Comparison saved -> {dest}")

    # Print summary
    print(f"\nSemantic Comparison Summary for '{analysis.get('title', paper_id)}':")
    print(f"  Skill coverage: {metrics['skill_annotations']} analysis points")
    print(f"  User annotations: {metrics['user_annotations']}")
    print(f"  Page overlap: {metrics['overlap_pages']} pages")
    print(f"  Skill-only pages: {metrics['skill_only_pages']}")
    print(f"  User-only pages: {metrics['user_only_pages']}")
    print(f"  Alignment quality:")
    print(f"    High overlap (>40%): {metrics['user_annotations_high_overlap']}")
    print(f"    Low overlap (1-40%):  {metrics['user_annotations_low_overlap']}")
    print(f"    No overlap:          {metrics['user_annotations_no_overlap']}")

    if learning_points:
        print(f"\n  Learning points:")
        for pt in learning_points:
            print(f"    - {pt}")


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
            summary_data = d.get("comparison_summary", {})
            print(f"  {f.stem:<30} {title:<50} "
                  f"skill={summary_data.get('skill_annotations',0)} "
                  f"user={summary_data.get('user_annotations',0)}")
        except Exception:
            print(f"  {f.stem:<30} (invalid)")


def main():
    parser = argparse.ArgumentParser(description="Bidirectional semantic comparison of analysis vs annotations")
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
