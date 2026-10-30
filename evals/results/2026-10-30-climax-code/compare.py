"""So hai tệp `replay.py` (cũ, mới) và in số liệu cho K1–K5 của `expectations.md`.

  python compare.py old.json new.json
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(old_path: str, new_path: str) -> None:
    old, new = load(old_path), load(new_path)
    differing: dict[str, list[int]] = {}
    stops_being_done: set[tuple[str, int]] = set()
    pending_only_new: list[tuple[str, int]] = []
    turning_diff = rest_diff = gap_diff = 0
    for run, o in old.items():
        climax = {i for i, kind, _, _ in o["plan_milestones"] if kind == "climax"}
        differing[run] = []
        for ch, oc in o["chapters"].items():
            nc = new[run]["chapters"][ch]
            if oc["milestone_lines"] != nc["milestone_lines"]:
                differing[run].append(int(ch))
            turning_diff += ([x for x in oc["milestone_lines"] if "bước ngoặt" in x]
                             != [x for x in nc["milestone_lines"] if "bước ngoặt" in x])
            rest_diff += oc["rest"] != nc["rest"]
            gap_diff += oc["gap"] != nc["gap"]
            old_done, new_done = {a for a, _ in oc["done"]}, {a for a, _ in nc["done"]}
            stops_being_done |= {(run, m) for m in climax if m in old_done and m not in new_done}
            if (set(nc["pending"]) & climax) - set(oc["pending"]):
                pending_only_new.append((run, int(ch)))
    print(json.dumps({
        "K1_climax_marks_that_stop_being_done": sorted(stops_being_done),
        "K2_chapters_with_a_different_milestone_section": differing,
        "K3_chapters_with_a_different_turning_point_line": turning_diff,
        "K4_chapters_with_a_different_rest_of_the_goals": rest_diff,
        "K4_chapters_with_a_different_gap_flag": gap_diff,
        "K5_chapters_where_a_climax_is_pending_only_in_the_new_code": pending_only_new,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
