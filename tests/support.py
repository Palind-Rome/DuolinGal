from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def ensure_src_on_path() -> None:
    import sys

    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


@contextmanager
def temporary_workspace() -> Path:
    root = ROOT / ".tmp-tests"
    root.mkdir(parents=True, exist_ok=True)
    temp_dir = root / f"case-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
