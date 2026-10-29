"""Đếm lại, bằng code và không gọi model, lời thoại dày trong demo cũ của bộ xuất video (D-125, D-127).

Lệnh (chạy trong backend/):
    uv run python ../evals/results/2026-10-30-video-dialogue-pace/recount.py \
        ../evals/results/2026-10-29-video-export-demo/script.json zh

Đọc `script.json` của demo, dựng lại từng shot, áp nhịp thoại trong config/limits.yaml hiện hành và in:
số shot có thoại, số shot bị `scene_problems` bắt, số cảnh sẽ phải làm lại, và kết quả nếu code tách shot
(số shot sau khi tách, shot còn quá dày, cảnh vượt `max_shots_per_scene`).
"""

import json
import sys
from pathlib import Path

from writory.config import load_config
from writory.export import shots
from writory.export.shots import SceneOutput, ShotDraft

KEYS = ("location_id", "time_of_day", "shot_size", "camera_angle", "camera_move", "duration_s", "appears",
        "action_en", "covers")


def draft(raw: dict) -> ShotDraft:
    body = {k: raw[k] for k in KEYS} | {"dialogue": [
        {k: d[k] for k in ("speaker_id", "text", "source_text")} for d in raw["dialogue"]]}
    return SceneOutput.model_validate({"shots": [body]}).shots[0]


def main(path: str, tag: str) -> None:
    limits = load_config().limits.video_export
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rate = shots.pace_limit(limits, tag)
    most = limits.require("max_shots_per_scene")
    total = with_talk = flagged = scenes = redo = after = left = over_cap = 0
    for chapter in data["chapters"]:
        for scene in chapter["scenes"]:
            scenes += 1
            drafts = [draft(s) for s in scene["shots"]]
            total += len(drafts)
            with_talk += sum(1 for d in drafts if d.dialogue)
            bad = [d for d in drafts if shots.pace_exceeded(d, limits, tag)]
            flagged += len(bad)
            redo += bool(bad)
            parts, _ = shots.split_dense_shots(drafts, limits, tag)
            after += len(parts)
            left += sum(1 for p in parts if shots.pace_exceeded(p, limits, tag))
            if len(parts) > most:
                over_cap += 1
                print(f"  cảnh {scene['chapter']}.{scene['scene']}: {len(drafts)} -> {len(parts)} shot (trần {most})")
            assert all(limits.require("shot_seconds_min") <= p.duration_s <= limits.require("shot_seconds_max")
                       for p in parts)
    print(f"ngôn ngữ {tag}, giới hạn {rate} mỗi giây")
    print(f"cảnh: {scenes}; shot: {total}; shot có thoại: {with_talk}")
    print(f"shot bị bắt: {flagged}; cảnh phải làm lại: {redo}")
    print(f"sau khi code tách: {after} shot (từ {total}); shot còn quá dày: {left}; cảnh vượt trần shot: {over_cap}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
