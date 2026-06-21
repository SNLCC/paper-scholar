#!/usr/bin/env python3
"""
reproduce_paper.py — Reproduction trigger: recall paper skeleton from memory.

When the user mentions a previously analyzed paper, or when writing needs
to reference past literature, this script extracts the paper's core argument,
structure, key quotes, and annotation threads from stored data.

Usage:
    python reproduce_paper.py recall <paper_id> [--data-dir <dir>] [--model-dir <dir>]
    python reproduce_paper.py list [--data-dir <dir>]
    python reproduce_paper.py search <keyword> [--data-dir <dir>]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


def _ddir(data_dir: str | None) -> Path:
    d = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    if not d.exists():
        print(f"No data directory at {d}. Analyze papers first.", file=sys.stderr)
        sys.exit(1)
    return d


def list_papers(data_dir: str | None = None):
    """List all papers available for reproduction."""
    ddir = _ddir(data_dir)
    files = sorted(ddir.glob("*.json"))
    if not files:
        print("No papers in data directory.")
        return
    print(f"{'Paper ID':<35} {'Title':<60}")
    print("-" * 95)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            pid = f.stem
            title = data.get("title", "(no title)")[:57]
            print(f"{pid:<35} {title:<60}")
        except Exception:
            print(f"{f.stem:<35} (invalid)")


def search_papers(keyword: str, data_dir: str | None = None):
    """Search papers by keyword in title."""
    ddir = _ddir(data_dir)
    kw = keyword.lower()
    found = False
    for f in sorted(ddir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            title = data.get("title", "").lower()
            if kw in title:
                print(f"[{f.stem}] {data.get('title', '(no title)')}")
                found = True
            # Also search in sections
            for section in data.get("sections", []):
                for para in section.get("paragraphs", []):
                    for sent in para.get("sentences", []):
                        if kw in sent.get("text", "").lower():
                            if not found:
                                print(f"[{f.stem}] {data.get('title', '(no title)')}")
                            print(f"  Match: {sent['text'][:100]}...")
                            found = True
                            break
        except Exception:
            continue
    if not found:
        print(f"No papers matching '{keyword}' found.")


def recall(paper_id: str, data_dir: str | None = None, model_dir: str | None = None):
    """Recall a paper's full skeleton from stored data and model library."""
    ddir = _ddir(data_dir)
    mdir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR

    # Load paper data
    paper_file = ddir / f"{paper_id}.json"
    if not paper_file.exists():
        # Try partial match
        matches = list(ddir.glob(f"*{paper_id}*"))
        if len(matches) == 1:
            paper_file = matches[0]
        elif len(matches) > 1:
            print(f"Multiple matches for '{paper_id}':")
            for m in matches:
                print(f"  {m.stem}")
            return
        else:
            print(f"Paper '{paper_id}' not found in data directory.")
            return

    data = json.loads(paper_file.read_text(encoding="utf-8"))
    title = data.get("title", paper_id)
    paper_type = data.get("paper_type", "unknown")

    print(f"=== Reproduction: {title} ===")
    print(f"Type: {paper_type}")
    print(f"Stored: {paper_file.stat().st_mtime}")
    print()

    # Core argument summary
    sections = data.get("sections", [])
    if sections:
        print("## Core Argument Structure")
        for i, section in enumerate(sections):
            func = section.get("rhetorical_function", f"Section {i+1}")
            print(f"\n### Section {i+1}: {func}")
            for para in section.get("paragraphs", []):
                for sent in para.get("sentences", []):
                    text = sent.get("text", "")
                    sfunc = sent.get("rhetorical_function", "")
                    if sfunc and text:
                        print(f"  [{sfunc}] {text[:150]}")

    # Key quotes
    print("\n## Key Quotes")
    quote_count = 0
    for section in sections:
        for para in section.get("paragraphs", []):
            for sent in para.get("sentences", []):
                if sent.get("is_key_quote"):
                    print(f"  > {sent.get('text', '')[:200]}")
                    quote_count += 1
    if quote_count == 0:
        print("  (no key quotes marked)")

    # Annotation threads (from .learnings/)
    learnings_file = Path(__file__).resolve().parent.parent / ".learnings" / f"{paper_id}.json"
    if learnings_file.exists():
        try:
            learnings = json.loads(learnings_file.read_text(encoding="utf-8"))
            print("\n## Annotation Threads")
            for m in learnings.get("semantic_alignment", {}).get("matched_annotations", []):
                color = m.get("user_color", "?")
                text = m.get("user_text", "")[:100]
                comment = m.get("user_comment", "")[:80]
                if text:
                    print(f"  [{color}] {text}")
                    if comment:
                        print(f"         Comment: {comment}")
        except Exception:
            pass

    # Model reference
    print("\n## Model Reference")
    model_found = False
    if mdir.exists():
        for mf in sorted(mdir.glob("*.json")):
            if mf.name in ("index.json",):
                continue
            try:
                model = json.loads(mf.read_text(encoding="utf-8"))
                papers = model.get("papers_analyzed", [])
                for p in papers:
                    if p.get("paper_id") == paper_id or paper_id in p.get("paper_id", ""):
                        print(f"  Model: {mf.stem}")
                        print(f"  Type family: {model.get('type_family', 'unknown')}")
                        print(f"  Confidence: {model.get('confidence', 0):.3f}")
                        print(f"  Papers in model: {len(papers)}")
                        model_found = True
                        break
            except Exception:
                continue
    if not model_found:
        print("  (not yet added to model library)")

    print(f"\n=== End of reproduction for {paper_id} ===")


def main():
    parser = argparse.ArgumentParser(description="Reproduce paper skeleton from memory")
    parser.add_argument("--data-dir", help="Data directory")
    parser.add_argument("--model-dir", help="Model directory")
    sub = parser.add_subparsers(dest="command")

    p_recall = sub.add_parser("recall", help="Recall a paper's full skeleton")
    p_recall.add_argument("paper_id")
    sub.add_parser("list", help="List all papers available for reproduction")
    p_search = sub.add_parser("search", help="Search papers by keyword")
    p_search.add_argument("keyword")

    args = parser.parse_args()

    if args.command == "recall":
        recall(args.paper_id, args.data_dir, args.model_dir)
    elif args.command == "list":
        list_papers(args.data_dir)
    elif args.command == "search":
        search_papers(args.keyword, args.data_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
