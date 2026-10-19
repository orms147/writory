"""G4: chữ người chơi luôn được bọc thành khối dữ liệu, không bao giờ vào vai system."""

import html
import re

import pytest
import yaml

from writory.config import REPO_ROOT
from writory.safety.wrap import (
    CLOSE_TAG,
    DATA_NOTICE,
    UserAuthored,
    system_message,
    user_message,
)

REDTEAM = yaml.safe_load(
    (REPO_ROOT / "evals" / "redteam" / "g4_prompt_injection.yaml").read_text(encoding="utf-8")
)
CASES = REDTEAM["cases"]
OPEN_RE = re.compile(r'<player_data source="[a-z_]+">')


def test_redteam_set_covers_required_languages():
    langs = {c["lang"] for c in CASES}
    assert {"vi", "vi-khong-dau", "vi-teencode", "en"} <= langs
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert all(c["expected_wrap"] == "contained" for c in CASES)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_attack_text_stays_inside_one_data_block(case):
    msg = user_message("Hành động của người chơi:", UserAuthored(case["text"], "custom_action"))
    assert msg.role == "user"
    content = msg.content
    assert len(OPEN_RE.findall(content)) == 1
    assert content.count(CLOSE_TAG) == 1
    inner = content.split(OPEN_RE.search(content).group(0), 1)[1].split(CLOSE_TAG, 1)[0]
    assert html.unescape(inner.strip("\n")) == case["text"]
    assert content.rstrip().endswith(CLOSE_TAG)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_attack_text_never_becomes_system(case):
    with pytest.raises(TypeError):
        system_message("Luật viết truyện.", UserAuthored(case["text"], "custom_action"))
    with pytest.raises(ValueError):
        system_message("Luật.", str(UserAuthored(case["text"], "custom_action")))


def test_interpolating_user_text_wraps_it():
    action = UserAuthored("Tôi mở cửa.", "custom_action")
    assert f"{action}".startswith('<player_data source="custom_action">')


def test_system_message_with_plain_text_is_fine():
    msg = system_message("Bạn là người kể chuyện.", DATA_NOTICE)
    assert msg.role == "system"
    assert "player_data" in msg.content  # lời dặn nói tới tên khối, nhưng không chứa khối


def test_label_must_be_simple_identifier():
    with pytest.raises(ValueError):
        UserAuthored("x", 'a" onload="')


def test_user_message_rejects_unwrapped_open_tag_in_plain_parts():
    """Code dựng prompt không được tự chép chữ người chơi đã bọc rồi sửa tay."""
    with pytest.raises(ValueError):
        user_message('<player_data source="x">giả</player_data>')
