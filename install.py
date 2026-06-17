#!/usr/bin/env python3
"""paper-scholar 安装与更新工具

用法：
    python install.py

自动判断：
  - 未安装 → 安装
  - 已安装 + 有新版 → 更新（保留用户数据）
  - 已安装 + 已是最新版 → 跳过
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass

import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

GITHUB_USER = "SNLCC"
REPO_NAME = "paper-scholar"
BRANCH = "main"

# 用户数据目录——更新时必须保留
USER_DATA_DIRS = {"models", "data", ".learnings", "prescriptions"}


def _version_from_path(path: Path) -> str:
    vf = path / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


def _fetch_remote_version() -> str:
    """从 GitHub 获取远程 VERSION 文件内容，不下载整个仓库。"""
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/{BRANCH}/VERSION"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.read().decode("utf-8").strip()
    except urllib.error.HTTPError:
        return "0.0.0"
    except urllib.error.URLError:
        return "0.0.0"


def _download_zip() -> bytes:
    url = f"https://github.com/{GITHUB_USER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
    print(f"  Downloading {REPO_NAME} ...")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"  Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _extract_zip(zip_data: bytes, temp_dir: Path) -> Path:
    import zipfile, io
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(temp_dir)
    extracted = [d for d in temp_dir.iterdir() if d.is_dir()]
    return extracted[0] if extracted else temp_dir


def _install_deps(project_dir: Path):
    req = project_dir / "requirements.txt"
    if req.exists():
        print("  Installing dependencies ...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req.resolve())],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  Dependencies installed.")
        else:
            print("  (dependencies may already be installed)")


def _get_target_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME", "")
    if codex_home:
        return Path(codex_home) / "skills" / "paper-scholar"
    return Path.home() / ".codex" / "skills" / "paper-scholar"


def _print_next_steps(target: Path):
    print(f"  位置: {target}")
    print()
    print(f"  重新启动 Codex 后，告诉它：")
    print(f'    "帮我精读这篇论文"')
    print(f'    "我想写论文，给我写作指导"')
    print()


def _do_install(target: Path):
    """执行安装（从 GitHub 下载并复制）"""
    with tempfile.TemporaryDirectory(prefix="ps-install-") as tmp:
        project = _extract_zip(_download_zip(), Path(tmp))
        _install_deps(project)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            str(project), str(target),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
        )


def _do_update(target: Path):
    """执行更新（保留用户数据）"""
    # 1. 备份用户数据
    backup_dir = Path(tempfile.mkdtemp(prefix="ps-backup-"))
    for dirname in USER_DATA_DIRS:
        src = target / dirname
        if src.exists():
            try:
                shutil.copytree(str(src), str(backup_dir / dirname))
            except Exception:
                pass

    # 2. 下载新版并替换
    with tempfile.TemporaryDirectory(prefix="ps-update-") as tmp:
        new_project = _extract_zip(_download_zip(), Path(tmp))
        new_ver = _version_from_path(new_project)

        shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            str(new_project), str(target),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
        )

        # 3. 恢复用户数据
        for dirname in USER_DATA_DIRS:
            src = backup_dir / dirname
            if src.exists():
                dst = target / dirname
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(str(src), str(dst))

        _install_deps(target)

    shutil.rmtree(backup_dir, ignore_errors=True)
    print(f"  paper-scholar 已更新到 v{new_ver}")
    print(f"  用户数据（模型/批注/论文/写作指导）已保留。")


def main():
    target = _get_target_dir()

    # 情况1：未安装
    if not target.exists():
        print(f"  安装 paper-scholar → {target}")
        _do_install(target)
        ver = _version_from_path(target)
        print(f"  ✅ v{ver} 安装完成")
        _print_next_steps(target)
        return

    # 情况2：目录存在但无效（缺少核心文件）
    if not (target / "SKILL.md").exists():
        print(f"  目录 {target} 已存在但缺少 SKILL.md，可能是无效安装。")
        print(f"  正在覆盖安装 ...")
        _do_install(target)
        ver = _version_from_path(target)
        print(f"  ✅ v{ver} 安装完成")
        _print_next_steps(target)
        return

    # 情况3：已安装 → 检查版本
    local_ver = _version_from_path(target)
    print(f"  已安装: v{local_ver}")

    remote_ver = _fetch_remote_version()
    if remote_ver == "0.0.0":
        print(f"  无法检测远程版本，请检查网络连接。")
        return

    print(f"  最新版: v{remote_ver}")

    # 版本比较：a.b.c 逐段比较
    def _parse_ver(v: str):
        parts = v.strip().split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts)

    if _parse_ver(local_ver) >= _parse_ver(remote_ver):
        print(f"  已是最新版本，无需更新。")
        return

    # 需要更新
    print(f"  发现新版本，正在更新 ...")
    old_ver = local_ver
    _do_update(target)
    print(f"  ✅ v{old_ver} → v{remote_ver} 更新完成")
    _print_next_steps(target)


if __name__ == "__main__":
    main()
