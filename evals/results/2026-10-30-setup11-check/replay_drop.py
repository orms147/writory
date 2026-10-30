"""Phát lại bằng code, không gọi model: năm lượt `setup-11` đi qua đường "bỏ id fact thường khỏi
`answered_by`" mà chủ dự án chọn sau phép đo (D-135).

Câu trả lời thô của lần dựng đầu KHÔNG được lưu (calls.jsonl không có thân, không có rejected.jsonl,
đề lượt sửa không lưu). Vì vậy dựng lại từ những gì có trong `truth_dump.json`:
  - câu trả lời đã được nhận: bản kế hoạch + gói chương 0 đổi ngược về dạng đầu ra model (khoảng
    gỡ của mạch đã dời lấy lại khoảng trước khi dời, `thread_shifts`);
  - lần dựng đầu: câu trả lời đã nhận + các id `answered_by` mà danh sách lỗi của lượt sửa
    (`setup_repairs`) nêu tên.
Danh sách lỗi đó là đủ: lỗi `answered_by` chỉ được kiểm khi kế hoạch và gói đã qua pydantic, nên
mọi lỗi quy tắc khác của lần dựng đầu cũng đã có mặt trong danh sách.

Chạy từ `backend/`:
    uv run python ../evals/results/2026-10-30-setup11-check/replay_drop.py ../evals/results/*-run-setup11-*
"""

import json
import re
import sys
from pathlib import Path

from writory.config import load_config
from writory.graph.package import ChangePackage
from writory.pipeline import setup as setup_mod
from writory.pipeline.setup import BuildOutput, CharacterOption, SetupInvalidError, to_story_setup
from writory.pipeline.story_plan import StoryPlan

sys.stdout.reconfigure(encoding="utf-8")
WRONG_LINK = re.compile(r"mạch (\S+): answered_by có (\S+), là fact nhưng không phải bí mật")
MODEL_EDGES = ("RELATES_TO", "LOCATED_AT", "HOLDS", "MEMBER_OF")


def accepted_answer(dump: dict) -> tuple[BuildOutput, CharacterOption, str]:
    """Câu trả lời đã nhận, đổi ngược từ kế hoạch + gói chương 0."""
    plan, pkg = dump["plan"], dump["packages"]["0"]
    nodes, edges = pkg["nodes"], pkg["edges"]
    before = {s["thread_id"]: s["before"] for s in dump.get("thread_shifts") or []}
    must = {t["thread_id"]: t for t in plan["must_resolve_threads"]}

    def named(n: dict, *extra: str) -> dict:
        p = n["props"]
        return {"id": n["id"], "name": p["name"], "aliases": p.get("aliases", []),
                **{k: p.get(k, "") for k in extra}}

    by = {label: [n for n in nodes if n["label"] == label and not n["props"].get("is_protagonist")]
          for label in ("Character", "Location", "Faction", "Item", "Fact", "Thread")}
    threads = []
    for n in by["Thread"]:
        low, high = before.get(n["id"], (n["props"]["due_from_chapter"], n["props"]["due_to_chapter"]))
        threads.append({"id": n["id"], "description": n["props"]["description"],
                        "due_from_chapter": low, "due_to_chapter": high,
                        "must_resolve": n["id"] in must,
                        "answered_by": list(must[n["id"]]["answered_by"]) if n["id"] in must else []})
    pc = next(n for n in nodes if n["props"].get("is_protagonist"))["props"]
    data = {
        "acts": plan["acts"],
        "characters": [named(n, "personality", "backstory", "appearance") for n in by["Character"]],
        "locations": [named(n, "description", "visual") for n in by["Location"]],
        "factions": [named(n, "description") for n in by["Faction"]],
        "items": [named(n, "description") for n in by["Item"]],
        "facts": [{"id": n["id"], "text": n["props"]["text"],
                   "about": [e["to"] for e in edges if e["type"] == "ABOUT" and e["from"] == n["id"]],
                   "known_by": [e["from"] for e in edges if e["type"] == "KNOWS" and e["to"] == n["id"]]}
                  for n in by["Fact"]],
        "edges": [{"type": e["type"], "source": e["from"], "target": e["to"],
                   "kind": e["props"].get("kind"), "score": e["props"].get("score")}
                  for e in edges if e["type"] in MODEL_EDGES],
        "threads": threads,
        "secrets": plan["secrets"],
        "milestones": plan["milestones"],
        "protagonist_appearance": pc.get("appearance", ""),
    }
    protagonist = CharacterOption(name=pc["name"], personality=pc["personality"],
                                  backstory=pc["backstory"])
    return BuildOutput.model_validate(data), protagonist, pkg["commit_id"]


def with_wrong_links(output: BuildOutput, pairs: list[tuple[str, str]]) -> BuildOutput:
    data = output.model_dump()
    for t in data["threads"]:
        t["answered_by"] += [f for tid, f in pairs if tid == t["id"]]
    return BuildOutput.model_validate(data)


def check(output: BuildOutput, protagonist: CharacterOption, commit_id: str, level) -> dict:
    try:
        s = to_story_setup(output, protagonist=protagonist, commit_id=commit_id, level=level)
    except SetupInvalidError as e:
        return {"problems": [p.text for p in e.problems]}
    return {"problems": [], "plan": s.plan, "package": s.package,
            "dropped": getattr(s, "dropped_answers", None)}


def main() -> None:
    config = load_config()
    print(f"setup prompt: {setup_mod.PROMPT_VERSION}; bỏ id fact thường: "
          f"{'có' if hasattr(setup_mod, 'drop_plain_fact_answers') else 'chưa'}\n")
    for out in map(Path, sys.argv[1:]):
        dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
        meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
        level = config.story_lengths.levels[meta["scenario"]["content"]["length_level"]]
        saved_plan = StoryPlan.model_validate(dump["plan"])
        saved_pkg = ChangePackage.model_validate(dump["packages"]["0"])
        output, pc, commit_id = accepted_answer(dump)
        accepted = check(output, pc, commit_id, level)
        faithful = (not accepted["problems"] and accepted["plan"] == saved_plan
                    and accepted["package"] == saved_pkg)
        repairs = dump.get("setup_repairs") or []
        first_problems = repairs[0]["problems"] if repairs else []
        pairs = [m.groups() for p in first_problems if (m := WRONG_LINK.search(p))]
        print(f"## {meta['label']}")
        print(f"  dựng lại câu trả lời đã nhận khớp kế hoạch + gói đã lưu: {faithful}")
        print(f"  lỗi lượt sửa đã ghi: {first_problems or 'không có lượt sửa'}")
        if not pairs:
            print("  không có id fact thường nào để phát lại: đường mới không đổi gì ở lượt này\n")
            continue
        first = check(with_wrong_links(output, pairs), pc, commit_id, level)
        same_problems = first["problems"] == first_problems
        print(f"  lần dựng đầu dựng lại ({len(pairs)} id fact thường): lỗi = {first['problems']}")
        if first["problems"]:
            print(f"    trùng đúng danh sách lỗi đã ghi: {same_problems} -> code này còn cần lượt sửa")
        else:
            print(f"    không lỗi -> tránh được lượt sửa; bỏ {first['dropped']}")
            print(f"    kế hoạch giống kế hoạch đã lưu: {first['plan'] == saved_plan}; "
                  f"gói giống gói đã lưu: {first['package'] == saved_pkg}")
        print()


if __name__ == "__main__":
    main()
