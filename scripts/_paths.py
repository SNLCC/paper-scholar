"""
_paths.py — Shared data-directory resolution for paper-scholar.

All user-accumulated data (papers, models, learnings, prescriptions, state)
lives under a single data root, NOT inside the skill's installation directory
(which may be read-only for Codex / the AI runtime).

Data root priority:
  1. PAPER_SCHOLAR_DATA_DIR environment variable
  2. $CWD/.paper-scholar/   (hidden folder in the current project directory)

Within that root the sub-directories are: data/, models/, .learnings/,
prescriptions/, plus the state file .skill_state.json.
"""

import os
from pathlib import Path


def _resolve_root() -> Path:
    env = os.environ.get("PAPER_SCHOLAR_DATA_DIR")
    if env:
        root = Path(env)
    else:
        root = Path.cwd() / ".paper-scholar"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def data_dir() -> Path:
    d = _resolve_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def models_dir() -> Path:
    d = _resolve_root() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def learnings_dir() -> Path:
    d = _resolve_root() / ".learnings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def prescriptions_dir() -> Path:
    d = _resolve_root() / "prescriptions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_file() -> Path:
    return _resolve_root() / ".skill_state.json"
