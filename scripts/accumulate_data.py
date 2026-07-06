#!/usr/bin/env python3
"""
accumulate_data.py — Store analyzed paper content into data/.

Each paper analysis is saved as a structured JSON file with metadata,
raw analysis text, and structured annotations.

Usage:
    python accumulate_data.py store <analysis.json> [--data-dir <dir>]
    python accumulate_data.py append <analysis.json> <paper_id> [--data-dir <dir>]
    python accumulate_data.py list [--data-dir <dir>]
    python accumulate_data.py show <paper_id> [--data-dir <dir>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from _paths import data_dir as _data_dir

DEFAULT_DATA_DIR = _data_dir()


def _resolve_dir(data_dir: str | None) -> Path:
    d = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_by_paper_id(paper_id: str, ddir: Path) -> Path | None:
    """Find an existing file by paper_id (filename fragment or field match)."""
    for f in ddir.glob(f"*{paper_id}*"):
        return f
    for f in ddir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("paper_id") == paper_id:
                return f
        except (json.JSONDecodeError, OSError):
            continue
    return None


def store_analysis(analysis_path: str, data_dir: str | None = None):
    """Store a paper analysis JSON into the data directory."""
    ddir = _resolve_dir(data_dir)
    src = Path(analysis_path)
    analysis = json.loads(src.read_text(encoding="utf-8"))

    paper_id = analysis.get("paper_id") or src.stem
    title = analysis.get("title", paper_id)[:40]
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"{timestamp}_{safe_name}_{paper_id}.json"
    dest = ddir / filename

    analysis["_stored_at"] = datetime.now().isoformat()
    analysis["_filename"] = filename

    dest.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Stored → {dest}")


def append_analysis(analysis_path: str, paper_id: str, data_dir: str | None = None):
    """Append new analysis content to an existing stored paper (incremental merge).

    Merges new sections/paragraphs/sentences into the existing analysis data.
    If the paper doesn't exist yet, falls back to store.
    """
    ddir = _resolve_dir(data_dir)
    existing_file = _find_by_paper_id(paper_id, ddir)
    new_data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))

    if not existing_file:
        print(f"Paper '{paper_id}' not found, falling back to store.", file=sys.stderr)
        return store_analysis(analysis_path, data_dir)

    existing = json.loads(existing_file.read_text(encoding="utf-8"))

    # Merge sections: append new ones, avoid duplicates by rhetorical_function
    existing_sections = existing.get("sections", [])
    existing_funcs = {s.get("rhetorical_function", "") for s in existing_sections}
    for ns in new_data.get("sections", []):
        func = ns.get("rhetorical_function", "")
        if func and func not in existing_funcs:
            existing_sections.append(ns)
            existing_funcs.add(func)
    existing["sections"] = existing_sections

    # Merge model fields (prefer new data for unstructured fields)
    for key in ["writing_pattern_model", "argumentation_model", "concept_usage_model",
                "chapter_templates", "structural_patterns"]:
        if key in new_data and new_data[key]:
            if key not in existing or not existing[key]:
                existing[key] = new_data[key]
            elif isinstance(new_data[key], dict) and isinstance(existing.get(key), dict):
                for k, v in new_data[key].items():
                    if k not in existing[key]:
                        existing[key][k] = v

    # Update metadata
    existing["_append_count"] = existing.get("_append_count", 1) + 1
    existing["_last_appended"] = datetime.now().isoformat()

    existing_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Appended → {existing_file} (append #{existing['_append_count']})")


def list_papers(data_dir: str | None = None):
    """List all stored papers."""
    ddir = _resolve_dir(data_dir)
    files = sorted(ddir.glob("*.json"))
    if not files:
        print("No papers in data/")
        return
    print(f"{'File':<45} {'Title':<50} {'Date'}")
    print("-" * 110)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            title = data.get("title", f.stem)[:48]
            date = data.get("_stored_at", "")[:10]
            print(f"{f.name:<45} {title:<50} {date}")
        except (json.JSONDecodeError, OSError):
            print(f"{f.name:<45} {'(invalid JSON)':<50}")


def show_paper(paper_id: str, data_dir: str | None = None):
    """Show a stored paper by ID or filename fragment."""
    ddir = _resolve_dir(data_dir)
    for f in ddir.glob(f"*{paper_id}*"):
        print(f.read_text(encoding="utf-8"))
        return
    for f in ddir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("paper_id") == paper_id:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
        except (json.JSONDecodeError, OSError):
            continue
    print(f"No paper found matching '{paper_id}'", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Store and manage accumulated paper data")
    parser.add_argument("--data-dir", help=f"Data directory (default: {DEFAULT_DATA_DIR})")
    sub = parser.add_subparsers(dest="command")

    p_store = sub.add_parser("store", help="Store an analysis JSON")
    p_store.add_argument("analysis_json", help="Path to analysis JSON")

    p_append = sub.add_parser("append", help="Append analysis to existing paper")
    p_append.add_argument("analysis_json", help="New analysis JSON path")
    p_append.add_argument("paper_id", help="Existing paper ID to append to")

    sub.add_parser("list", help="List stored papers")

    p_show = sub.add_parser("show", help="Show a stored paper")
    p_show.add_argument("paper_id", help="Paper ID or filename fragment")

    args = parser.parse_args()

    if args.command == "store":
        store_analysis(args.analysis_json, args.data_dir)
    elif args.command == "append":
        append_analysis(args.analysis_json, args.paper_id, args.data_dir)
    elif args.command == "list":
        list_papers(args.data_dir)
    elif args.command == "show":
        show_paper(args.paper_id, args.data_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
