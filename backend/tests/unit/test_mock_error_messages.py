"""Bảng lỗi của lớp mock giao diện khớp máy chủ cho nhóm LLM_* và lỗi của bộ định tuyến
(frontend/src/mock/messages.ts)."""

import re

from writory.api.errors import HTTP_STATUS
from writory.config import REPO_ROOT
from writory.errors import MESSAGES, ErrorCode

MOCK = (REPO_ROOT / "frontend" / "src" / "mock" / "messages.ts").read_text(encoding="utf-8")


def _mock(code: ErrorCode) -> tuple[str, int] | None:
    found = re.search(rf'^\s*{code.value}: \{{ message: "(.*)", status: (\d+) \}},$', MOCK, re.MULTILINE)
    return (found.group(1).replace('\\"', '"'), int(found.group(2))) if found else None


def test_every_llm_error_has_the_same_text_and_status_in_the_mock_table():
    for code in ErrorCode:
        if not code.value.startswith("LLM_"):
            continue
        assert _mock(code) == (MESSAGES[code].text(), HTTP_STATUS[code]), code.value


def test_router_errors_have_the_same_text_and_status_in_the_mock_table():
    """Lớp mock trả ROUTE_NOT_FOUND cho đường dẫn nó không biết, như máy chủ (`api/errors.py`)."""
    for code in (ErrorCode.ROUTE_NOT_FOUND, ErrorCode.METHOD_NOT_ALLOWED):
        assert _mock(code) == (MESSAGES[code].text(), HTTP_STATUS[code]), code.value


def test_moderation_errors_of_setup_and_narrator_are_in_the_mock_table():
    """Mã mới của kiểm duyệt đầu ra (D-137): giao diện chạy với máy chủ giả cũng hiện đúng câu."""
    for code in (ErrorCode.SETUP_OPTIONS_BLOCKED, ErrorCode.NARRATOR_ANSWER_BLOCKED):
        assert _mock(code) == (MESSAGES[code].text(), HTTP_STATUS[code]), code.value


def test_scene_block_errors_have_the_same_text_and_status_in_the_mock_table():
    """Hai mã của `scene_blocked`: lộ bí mật (G2) và chiều theo hành động vượt luật (G6, D-138)."""
    for code in (ErrorCode.SCENE_LEAK_BLOCKED, ErrorCode.SCENE_OVERREACH_BLOCKED):
        assert _mock(code) == (MESSAGES[code].text(), HTTP_STATUS[code]), code.value
