"""
File + Git helpers (unchanged logic, now with logging & pathlib)
"""

import subprocess
import sys
import logging
from pathlib import Path
from typing import List

_LOGGER = logging.getLogger(__name__)


def run_command(cmd: str) -> None:
    _LOGGER.info("Running: %s", cmd)
    try:
        subprocess.run(cmd, shell=True, check=True, text=True)
    except subprocess.CalledProcessError as exc:
        _LOGGER.error("Command failed: %s", exc.stderr)
        sys.exit(1)


def clone_repo(url: str, base_dir: Path) -> Path:
    base_dir.mkdir(exist_ok=True)
    repo_name = url.split("/")[-1].removesuffix(".git")
    dest = base_dir / repo_name
    if dest.exists():
        _LOGGER.info("Repo already cloned: %s", dest)
        return dest
    run_command(f"git clone --depth 1 {url} {dest}")
    return dest


def list_files(root: Path) -> List[str]:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
