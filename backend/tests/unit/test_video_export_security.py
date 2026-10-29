"""Bộ xuất kịch bản video đọc TOÀN BỘ lớp truth nên chỉ admin cầm DB được chạy (D-125, D-118): không có
đường nào từ app tới nó, nó chỉ đọc, và bản xuất thật không bao giờ lọt vào git. docs/security.md."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from writory.config import REPO_ROOT
from writory.export import video

SRC = Path(__file__).resolve().parents[2] / "src" / "writory"
EXPORT_SRC = SRC / "export"


def _sources(folder: Path) -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in folder.rglob("*.py")}


def test_nothing_in_the_app_imports_or_serves_the_export():
    """Không endpoint, không nút: không file nào ngoài export/ import `writory.export`, và api/ không có
    đường nào tên export hay video."""
    for path, text in _sources(SRC).items():
        if EXPORT_SRC in path.parents:
            continue
        assert not re.search(r"(from|import)\s+writory\.export|from\s+writory\s+import\s+export", text), path
    for path, text in _sources(SRC / "api").items():
        assert not re.search(r"""["'/]\w*(export|video)\w*["']""", text, re.IGNORECASE), path
        assert "writory.export" not in text


def test_the_frontend_has_no_way_to_ask_for_an_export():
    frontend = REPO_ROOT / "frontend" / "src"
    if not frontend.exists():
        pytest.skip("không có frontend/src")
    for path in frontend.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".tsx"}:
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"/(export|video)\b", text, re.IGNORECASE), path


def test_the_export_only_reads_the_databases():
    """Không câu lệnh ghi nào: không execute_write, không INSERT/UPDATE/DELETE/MERGE/CREATE/SET/DETACH/REMOVE/DROP,
    không gọi hàm ghi của db/ hay graph/ (apply_package, commit_chapter, delete_*, save_*, set_*)."""
    # Tên hàm ghi, và từ khoá SQL/Cypher viết HOA (list.insert của Python là chữ thường, không tính).
    banned = re.compile(
        r"execute_write|apply_package|commit_chapter|delete_commit|delete_story|save_story_plan|"
        r"set_story_brief|\b(INSERT|UPDATE|DELETE|MERGE|DETACH|CREATE|SET|REMOVE|DROP)\b")
    for path, text in _sources(EXPORT_SRC).items():
        found = [m.group(0) for m in banned.finditer(text)]
        assert not found, (path, found)
    # Postgres: connect() mở autocommit, nên chỉ có SELECT nằm trong các hàm đọc nó gọi.
    reads = video.load_source.__code__.co_names
    assert "chapter_scenes" in reads and "get_story" in reads


def test_the_export_does_not_open_the_player_paths_or_keys():
    """Nó dùng key của chủ dự án từ môi trường, không đọc key người chơi đã mã hoá (G7)."""
    for path, text in _sources(EXPORT_SRC).items():
        assert "decrypt" not in text and "player_key" not in text and "db.keys" not in text, path


def test_the_default_output_folder_is_not_in_any_committed_folder():
    root = video.DEFAULT_OUT_ROOT
    assert root.parent == REPO_ROOT and root.name == "exports"
    committed = {"backend", "frontend", "docs", "evals", "config", "data", "deploy", ".github"}
    assert root.name not in committed
    assert "exports/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").split()


@pytest.mark.skipif(shutil.which("git") is None, reason="cần git")
def test_git_really_ignores_the_default_output_folder():
    sample = video.default_out("run-xyz").relative_to(REPO_ROOT) / "script.md"
    result = subprocess.run(["git", "check-ignore", "-q", sample.as_posix()], cwd=REPO_ROOT,
                            capture_output=True, check=False)
    assert result.returncode == 0, "exports/ phải bị .gitignore bỏ qua"
    kept = subprocess.run(["git", "check-ignore", "-q", "evals/results/x/script.md"], cwd=REPO_ROOT,
                          capture_output=True, check=False)
    assert kept.returncode == 1  # kết quả đo ở evals/results/ vẫn commit được (bản demo)


def test_every_export_file_starts_with_the_spoiler_warning(tmp_path):
    from writory.export.video import WARNING, Export, render_markdown

    export = Export({"format": video.FORMAT, "story_id": "s", "dialogue_lang": "en", "chapters": [],
                     "sheets_only": True, "moderation": False, "model": None, "prompt_version": "v",
                     "calls": 0, "cost_usd": 0.0}, [], [], [])
    assert WARNING in render_markdown(export).split("\n")[2]
    assert "SPOILER" in WARNING and "CẢNH BÁO" in WARNING
