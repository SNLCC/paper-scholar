#!/usr/bin/env python3
"""
paper-scholar 安装脚本

从 GitHub 下载并安装到 Codex 的 skills 目录。

用法：
    python install.py

或者一条命令：
    python -c "$(curl -fsSL https://raw.githubusercontent.com/YOUR_USER/paper-scholar/main/install.py)"
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


# 填写你的 GitHub 信息
GITHUB_USER = "SNLCC"
REPO_NAME = "PaperScholar"
BRANCH = "main"


def _download_zip() -> bytes:
    """Download the repository as a ZIP archive from GitHub."""
    url = f"https://github.com/{GITHUB_USER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
    print(f"  Downloading from {url} ...")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        print(f"  Downloaded {len(data):,} bytes.")
        return data
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        print(f"  Check that https://github.com/{GITHUB_USER}/{REPO_NAME} exists.", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"  Network error: {e.reason}", file=sys.stderr)
        print("  Please check your internet connection.", file=sys.stderr)
        sys.exit(1)


def _extract_zip(zip_data: bytes, temp_dir: Path) -> Path:
    """Extract ZIP to temp_dir and return the extracted project root."""
    import zipfile
    import io
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(temp_dir)
    # GitHub ZIP contains a top-level folder: PaperScholar-main/
    extracted = [d for d in temp_dir.iterdir() if d.is_dir()]
    if not extracted:
        print("  Error: empty archive.", file=sys.stderr)
        sys.exit(1)
    return extracted[0]


def _ensure_python_deps(project_dir: Path):
    """Install Python dependencies from requirements.txt."""
    req_file = project_dir / "requirements.txt"
    if req_file.exists():
        print("  Installing Python dependencies ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  Dependencies installed.")
        else:
            print("  Note: pip install had a warning (deps may already be installed).")
            if result.stderr.strip():
                print(f"  {result.stderr.strip()}")


def _copy_to_skills(source_dir: Path) -> Path:
    """Copy the project to the Codex skills directory."""
    codex_home = os.environ.get("CODEX_HOME", "")
    if codex_home:
        target = Path(codex_home) / "skills" / "paper-scholar"
    else:
        target = Path.home() / ".codex" / "skills" / "paper-scholar"

    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        print(f"  Removing existing installation at {target} ...")
        shutil.rmtree(target)

    shutil.copytree(
        str(source_dir),
        str(target),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
    )
    print(f"  Installed to: {target}")
    return target


def main():
    print()
    print("  paper-scholar 安装工具")
    print("  ====================")
    print()

    # Step 1: Download
    print("  [1/4] 从 GitHub 下载 ...")
    zip_data = _download_zip()

    # Step 2: Extract
    print("  [2/4] 解压 ...")
    with tempfile.TemporaryDirectory(prefix="paper-scholar-") as tmp:
        tmp_path = Path(tmp)
        project_dir = _extract_zip(zip_data, tmp_path)

        # Step 3: Install Python deps
        print("  [3/4] 安装 Python 依赖 ...")
        _ensure_python_deps(project_dir)

        # Step 4: Copy to Codex skills
        print("  [4/4] 安装到 Codex ...")
        target = _copy_to_skills(project_dir)

    print()
    print("  ✅ 安装完成！")
    print()
    print(f"  paper-scholar 已安装到:")
    print(f"    {target}")
    print()
    print("  重新启动 Codex 后，你可以说：")
    print('    "帮我精读这篇论文"')
    print('    "用 paper-scholar 分析这篇论文的结构"')
    print('    "我想写论文，给我写作指导"')
    print()
    print("  或者手动运行：")
    print(f"    python {target / 'run.py'} --help")
    print()


if __name__ == "__main__":
    main()
