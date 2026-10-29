"""Bảng lỗi của lớp mock giao diện khớp máy chủ cho nhóm LLM_* (frontend/src/mock/messages.ts)."""

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
