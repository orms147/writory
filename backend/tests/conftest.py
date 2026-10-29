"""Mọi test: không chờ thời gian thật khi thử lại có lùi (§6). `retry._sleep` là chỗ duy nhất production
chờ; ở đây thay bằng hàm ghi lại số giây đã định chờ. Test nào cần quan sát thì lấy fixture `slept`."""

import pytest

from writory.llm import retry


@pytest.fixture(autouse=True)
def slept(monkeypatch):
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(retry, "_sleep", fake_sleep)
    return waits
