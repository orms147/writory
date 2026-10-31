"""Bộ viết kịch bản audio là công cụ CHỈ của admin (D-151): không có đường nào từ app tới nó, và nó không chạm
Postgres, Neo4j hay bộ xuất video (đọc lớp truth). docs/security.md."""

import re
from pathlib import Path

import pytest

from writory.config import REPO_ROOT

SRC = Path(__file__).resolve().parents[2] / "src" / "writory"
AUDIO_SRC = SRC / "audio"


def _sources(folder: Path) -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in folder.rglob("*.py")}


def test_nothing_in_the_app_imports_or_serves_the_audio_tool():
    for path, text in _sources(SRC).items():
        if AUDIO_SRC in path.parents:
            continue
        assert not re.search(r"(from|import)\s+writory\.audio|from\s+writory\s+import\s+audio", text), path
    # Không route nào tới công cụ admin: không đường dẫn chứa "audio". Giá trị kiểu truyện "audio" (D-153) không phải
    # đường dẫn, và bộ viết kịch bản admin vẫn không được nhập từ app (phép kiểm import ở trên).
    for path, text in _sources(SRC / "api").items():
        assert not re.search(r"""["']/[^"']*audio""", text, re.IGNORECASE), path


def test_the_frontend_has_no_way_to_ask_for_an_audio_script():
    frontend = REPO_ROOT / "frontend" / "src"
    if not frontend.exists():
        pytest.skip("không có frontend/src")
    for path in frontend.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".tsx"}:
            # Chuỗi đường dẫn trong dấu nháy (`'/audio...'`), không bắt nhầm regex của test giao diện (`/Audio ~45 phút/`).
            assert not re.search(r"""["'`]/audio\b""", path.read_text(encoding="utf-8"), re.IGNORECASE), path


def test_the_audio_tool_touches_no_database_and_not_the_truth_exporter():
    banned = r"(from|import)\s+(writory\.(db|api|export|pipeline)|writory\.graph\.(commit|queries|story)|psycopg|neo4j)\b"
    for path, text in _sources(AUDIO_SRC).items():
        assert not re.search(banned, text), path


def test_exports_stay_out_of_git():
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip().rstrip("/") in ("exports", "/exports") for line in ignored)
