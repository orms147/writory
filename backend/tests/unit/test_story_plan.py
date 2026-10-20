import pytest
from pydantic import ValidationError

from writory.pipeline.story_plan import StoryPlan


def plan(**overrides) -> dict:
    data = {
        "acts": [
            {"name": "mở đầu", "from_chapter": 1, "to_chapter": 2},
            {"name": "phát triển", "from_chapter": 3, "to_chapter": 6},
        ],
        "secrets": [{"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6}],
        "must_resolve_threads": ["t_who_killed"],
    }
    return data | overrides


def test_valid_plan_and_secret_lookup():
    p = StoryPlan.model_validate(plan())
    assert p.secret("f_lan_spy").reveal_from_chapter == 5
    assert p.secret("f_unknown") is None


@pytest.mark.parametrize(
    "bad",
    [
        {"acts": []},
        {"acts": [{"name": "x", "from_chapter": 3, "to_chapter": 2}]},
        {"acts": [{"name": "a", "from_chapter": 1, "to_chapter": 3},
                  {"name": "b", "from_chapter": 3, "to_chapter": 5}]},  # chồng chương 3
        {"acts": [{"name": "b", "from_chapter": 4, "to_chapter": 5},
                  {"name": "a", "from_chapter": 1, "to_chapter": 3}]},  # sai thứ tự
        {"secrets": [{"fact_id": "f", "reveal_from_chapter": 6, "reveal_to_chapter": 5}]},
        {"secrets": [{"fact_id": "f", "reveal_from_chapter": 1, "reveal_to_chapter": 2},
                     {"fact_id": "f", "reveal_from_chapter": 3, "reveal_to_chapter": 4}]},
        {"secrets": [{"fact_id": "có dấu cách", "reveal_from_chapter": 1, "reveal_to_chapter": 2}]},
        {"must_resolve_threads": ["t", "t"]},
        {"extra_field": 1},
    ],
)
def test_invalid_plan_rejected(bad):
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(plan(**bad))
