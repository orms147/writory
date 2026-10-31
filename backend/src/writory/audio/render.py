"""Phần bằng code của bộ viết kịch bản audio (D-151): đổi phút ra chữ, đọc hướng đi, ghi file.

Không gọi model. Số (tốc độ đọc, cỡ đoạn, trần) đọc từ `limits.audio_script`.
"""

import json
import math
import re
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from writory.config import AudioScriptLimits, ConfigError

FORMAT = "writory-audio-script/1"
NARRATOR = "narrator"  # người nói của lời dẫn; mọi người nói khác là id nhân vật trong kế hoạch
OUTPUT_FILES = ("script.md", "script.json", "tts.txt", "calls.jsonl")
IDEA_FILES = ("ideas.md", "ideas.yaml", "calls.jsonl")
_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
_PREMISE_KEYS = {"id", "premise", "minutes", "title", "hooks"}


# --- phút -> chữ -> đoạn --------------------------------------------------------------------------


@dataclass(frozen=True)
class Targets:
    minutes: int
    words_per_minute: int
    total_words: int
    segments: int
    words_per_segment: int


def targets(minutes: int, limits: AudioScriptLimits, *, words_per_minute: int | None = None) -> Targets:
    """Số chữ (âm tiết) cần cho `minutes` phút nói, chia đều thành các đoạn không quá `segment_words`."""
    low, high = limits.require("minutes_min"), limits.require("minutes_max")
    if not low <= minutes <= high:
        raise ConfigError(f"--minutes {minutes}: phải trong [{low}, {high}] (limits.audio_script.minutes_*)")
    wpm = words_per_minute or limits.require("words_per_minute")
    if wpm <= 0:
        raise ConfigError("--wpm phải > 0")
    total = minutes * wpm
    segments = max(1, math.ceil(total / limits.require("segment_words")))
    return Targets(minutes, wpm, total, segments, math.ceil(total / segments))


def word_count(text: str) -> int:
    """Số chữ nói: tiếng Việt viết mỗi âm tiết một từ, nên đếm theo khoảng trắng."""
    return len(text.split())


# --- hướng đi admin đưa vào -----------------------------------------------------------------------


@dataclass(frozen=True)
class Premise:
    id: str
    text: str
    minutes: int | None = None


def _premise_text(item: dict[str, Any]) -> str:
    text = str(item.get("premise") or "").strip()
    title = str(item.get("title") or "").strip()
    hooks = [str(h).strip() for h in item.get("hooks") or [] if str(h).strip()]
    if text and title:
        text = f"{title}: {text}"
    if text and hooks:
        text += "\nCảnh đáng chờ: " + "; ".join(hooks)
    return text


def parse_premises(data: Any, *, max_chars: int) -> list[Premise]:
    """Danh sách hướng đi: mỗi mục là chữ, hay dict {id, premise, minutes, title, hooks} (file `ideas.yaml`
    của `propose` đọc lại được). Kiểm trước mọi lời gọi."""
    if not isinstance(data, list) or not data:
        raise ConfigError("không có hướng đi nào (--premise hay --premise-file)")
    out: list[Premise] = []
    for n, item in enumerate(data, 1):
        if isinstance(item, str):
            item = {"premise": item}
        if not isinstance(item, dict):
            raise ConfigError(f"hướng đi thứ {n}: phải là chữ hay dict có khoá premise")
        unknown = set(item) - _PREMISE_KEYS
        if unknown:
            raise ConfigError(f"hướng đi thứ {n}: khoá lạ {', '.join(sorted(map(str, unknown)))}")
        pid = str(item.get("id") or f"p{n}")
        if not _ID_RE.fullmatch(pid):
            raise ConfigError(f"hướng đi thứ {n}: id {pid!r} chỉ gồm a-z, 0-9, '-', '_' (dùng làm tên thư mục)")
        text = _premise_text(item)
        if not text:
            raise ConfigError(f"hướng đi {pid}: rỗng")
        if len(text) > max_chars:
            raise ConfigError(f"hướng đi {pid}: dài {len(text)} ký tự, quá {max_chars} "
                              "(limits.audio_script.premise_max_chars)")
        minutes = item.get("minutes")
        if minutes is not None and (not isinstance(minutes, int) or isinstance(minutes, bool)):
            raise ConfigError(f"hướng đi {pid}: minutes phải là số nguyên")
        out.append(Premise(pid, text, minutes))
    ids = [p.id for p in out]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ConfigError(f"id hướng đi trùng: {', '.join(dup)}")
    return out


def load_premises(path: Path, *, max_chars: int) -> list[Premise]:
    """`.yaml`/`.yml`: danh sách như `parse_premises`. File khác: mỗi khối cách nhau một dòng trống là một hướng đi."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"không đọc được {path}: {type(e).__name__}") from None
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ConfigError(f"{path}: YAML sai ({type(e).__name__})") from None
    else:
        data = [b.strip() for b in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")) if b.strip()]
    return parse_premises(data, max_chars=max_chars)


# --- kết quả --------------------------------------------------------------------------------------


@dataclass
class SegmentOut:
    index: int
    title: str
    status: str  # ok | withheld_moderation | withheld_unmoderated | error | skipped_budget
    lines: list[dict[str, Any]] = field(default_factory=list)  # {speaker, text, cue, sfx}
    words: int = 0
    target_words: int = 0
    length_off: bool = False  # hết lượt viết lại mà số chữ vẫn lệch mục tiêu quá `length_tolerance`
    reveals: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""
    moderation: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class AudioScript:
    meta: dict[str, Any]
    plan: dict[str, Any] | None = None  # PlanOutput.model_dump(); None khi lập kế hoạch thất bại
    segments: list[SegmentOut] = field(default_factory=list)
    stop: str | None = None  # lý do dừng sớm (budget, moderation, plan...), None = xong

    def names(self) -> dict[str, str]:
        cast = (self.plan or {}).get("cast", [])
        return {NARRATOR: "Người kể", **{c["id"]: c["name"] for c in cast}}


def script_json(script: AudioScript) -> dict[str, Any]:
    return {"format": FORMAT, "meta": script.meta, "plan": script.plan, "stop": script.stop,
            "segments": [asdict(s) for s in script.segments]}


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "/").replace("\n", " ")


def render_markdown(script: AudioScript) -> str:
    m, plan, names = script.meta, script.plan or {}, script.names()
    out = [f"# {plan.get('title') or 'Kịch bản audio'}", ""]
    if plan.get("logline"):
        out += [f"> {plan['logline']}", ""]
    out.append(f"- Hướng đi `{m['premise_id']}`; mục tiêu {m['minutes']} phút ở {m['words_per_minute']} chữ/phút "
               f"({m['target_words']} chữ); đã viết {m['words']} chữ, khoảng {m['est_minutes']} phút.")
    out.append(f"- Model `{m['model']}` · đề `{m['prompt_version']}` · {m['calls']} lời gọi · "
               f"{m['cost_usd']:.4f} USD")
    if not m["moderation"]:
        out.append("- **Kiểm duyệt (G9) TẮT cho lần viết này.**")
    if script.stop:
        out.append(f"- **Dừng sớm: {script.stop}.** Các đoạn sau đó chưa có.")
    if plan.get("cast"):
        out += ["", "## Nhân vật", "", "| id | Tên | Giới tính | Tuổi | Vai | Giọng gợi ý |", "|---|---|---|---|---|---|"]
        for c in plan["cast"]:
            star = " (nhân vật chính)" if c["id"] == plan.get("protagonist_id") else ""
            out.append(f"| {c['id']} | {_cell(c['name'])}{star} | {c['gender']} | {c['age']} | {_cell(c['role'])} | "
                       f"{_cell(c['voice'])} |")
    if plan.get("secrets"):
        out += ["", "## Bí mật và đoạn lộ", ""]
        out += [f"- `{s['id']}` (đoạn {s['reveal_segment']}): {s['text']}" for s in plan["secrets"]]
    if plan.get("ending"):
        out += ["", f"**Kết:** {plan['ending']}"]
    for seg in script.segments:
        out += ["", f"## Đoạn {seg.index}: {seg.title}", ""]
        if seg.status != "ok":
            out.append(f"*Đoạn này bị giữ lại hay chưa viết ({seg.status}"
                       f"{', ' + seg.error if seg.error else ''}).*")
            continue
        flag = " · **lệch độ dài**" if seg.length_off else ""
        out += [f"*{seg.words}/{seg.target_words} chữ{flag}*", ""]
        for line in seg.lines:
            if line.get("sfx"):
                out.append(f"*[Âm thanh: {line['sfx']}]*")
            who = names.get(line["speaker"], line["speaker"])
            cue = f" *({line['cue']})*" if line.get("cue") else ""
            out.append(f"**{who}**{cue}: {line['text']}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_tts(script: AudioScript) -> str:
    """Chữ đọc liền cho TTS một giọng: lời dẫn giữ nguyên, lời nhân vật đặt trong ngoặc kép; không tên người
    nói, không cách đọc, không âm thanh, không tiêu đề đoạn. Đoạn bị giữ lại không có chữ nào ở đây."""
    blocks: list[str] = []
    for seg in script.segments:
        if seg.status != "ok":
            continue
        lines = [line["text"].strip() if line["speaker"] == NARRATOR else f"“{line['text'].strip()}”"
                 for line in seg.lines if line["text"].strip()]
        if lines:
            blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def render_ideas_md(ideas: list[dict[str, Any]], *, tags: str, meta: dict[str, Any]) -> str:
    cost = f"- Model `{meta['model']}` · {meta['calls']} lời gọi · {meta['cost_usd']:.4f} USD"
    out = ["# Hướng đi đề xuất", "", f"- Tag: {tags}", cost, "",
           "Chọn hướng đi bằng `write --premise-file ideas.yaml --pick <id>` (sửa file trước nếu muốn).", ""]
    for idea in ideas:
        out += [f"## {idea['id']}: {idea['title']}", "", idea["premise"], ""]
        out += [f"- {h}" for h in idea["hooks"]]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def ideas_yaml(ideas: list[dict[str, Any]]) -> str:
    return yaml.safe_dump(ideas, allow_unicode=True, sort_keys=False, width=1000)


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


# --- ghi file -------------------------------------------------------------------------------------


def check_fresh(out: Path, names: Sequence[str]) -> None:
    """Từ chối khi thư mục đã có kết quả: lần chạy sau không đè kịch bản đã trả tiền."""
    found = [n for n in names if (out / n).exists()]
    if found:
        raise ConfigError(f"đã có kết quả ở {out} ({', '.join(found)}); dùng --out khác hoặc xoá thư mục đó")


def write_dir(out: Path, files: Mapping[str, str], names: Sequence[str]) -> list[Path]:
    """Ghi vào thư mục tạm cạnh `out` rồi đổi tên: lỗi giữa chừng không để lại nửa bản xuất."""
    check_fresh(out, names)
    tmp = out.parent / f".{out.name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        for name, text in files.items():
            (tmp / name).write_text(text, encoding="utf-8", newline="\n")
        if out.exists():
            out.rmdir()  # thư mục rỗng có sẵn
        tmp.rename(out)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return [out / name for name in files]
