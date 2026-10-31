"""Bộ xuất kịch bản video: điều phối, trần chi phí, ghi file, lệnh (D-125, D-118).

    cd backend && uv run python -m writory.export.video --story <id> --dialogue-lang zh \\
        --chapters 1-3 --budget 0.10 [--out <thư mục>] [--env-file <file>]

CHỈ admin cầm DB chạy được: cần POSTGRES_DSN và NEO4J_* của máy; không endpoint, không nút (xem
`writory.export.__doc__`). Chỉ đọc, không ghi Postgres hay Neo4j. File xuất có lộ bí mật nên mặc định
nằm ở `exports/` (git bỏ qua) và mở đầu bằng cảnh báo.

Chế độ: `--sheets-only` (chỉ phần bằng code, không model, không key, không tốn tiền), `--dry-run` (model
giả, không mạng, không key), mặc định là chạy thật: bắt buộc `--budget` (USD) và không được vượt
`limits.video_export.max_budget_usd` (G8). Key: chỉ OPENROUTER_API_KEY của chủ dự án, từ biến môi trường
hoặc `--env-file`; không in, không ghi (G7). Hết trần giữa chừng thì dừng, vẫn ghi phần đã xong (mã thoát
2). Kiểm duyệt G9 trên prompt cuối của mỗi cảnh bật mặc định; `--no-moderate` tắt và in cảnh báo.

Mã thoát: 0 xong; 1 sai cấu hình hay tham số; 2 dừng vì chạm `--budget`; 3 có cảnh lỗi (đã ghi phần còn lại).
"""

import argparse
import asyncio
import json
import logging
import math
import re
import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, ClassVar

import psycopg
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from writory.config import (
    REPO_CONFIG_DIR,
    REPO_ROOT,
    AppConfig,
    ConfigError,
    ModelPrice,
    load_config,
)
from writory.db import StoryNotFoundError
from writory.errors import ErrorCode, WritoryError
from writory.export import sheets, shots
from writory.graph.package import quote_in_text
from writory.guard.state import GraphState
from writory.llm.base import (
    ChatResult,
    LLMClient,
    Usage,
    require_model,
    role_extra,
)
from writory.llm.capped import CappedClient
from writory.llm.fake import FakeLLM
from writory.llm.provider import llm_identity
from writory.quality.bench_d import EST_CHARS_PER_TOKEN, Budget
from writory.safety.moderate import Source, Verdict, moderate
from writory.safety.redact import install_log_redaction, redact

log = logging.getLogger(__name__)

FORMAT = "writory-video-script/1"
DEFAULT_OUT_ROOT = REPO_ROOT / "exports"  # .gitignore: không bao giờ commit bản xuất thật
EXIT_OK, EXIT_CONFIG, EXIT_BUDGET, EXIT_ERRORS = 0, 1, 2, 3
DRY_RUN_COST_USD = 0.0001
WARNING = (
    "SPOILER / TRUTH WARNING: this file is built from the full truth layer of the story (secrets, "
    "backstage, what characters hide) and from text the reader has seen. It reveals everything. Do not "
    "show it to players. | CẢNH BÁO LỘ BÍ MẬT: bản xuất dựng từ toàn bộ lớp truth của truyện; chỉ admin "
    "được giữ, không đưa cho người chơi."
)


# --- nguồn dữ liệu ------------------------------------------------------------------------------


@dataclass
class StorySource:
    """Truyện đã đọc vào bộ nhớ: chữ các cảnh đã commit của các chương được chọn và trạng thái đồ thị."""

    story_id: str
    chapters: dict[int, list[str]]  # số chương -> chữ từng cảnh, đúng chữ người đọc đã đọc
    state: GraphState


def parse_chapters(spec: str | None, last: int) -> list[int]:
    """`--chapters`: "N", "A-B" hoặc để trống (cả truyện, 1..last)."""
    if spec is None:
        return list(range(1, last + 1))
    found = re.fullmatch(r"(\d+)(?:-(\d+))?", spec.strip())
    if not found:
        raise ConfigError(f"--chapters {spec!r}: dạng N hoặc A-B, ví dụ 1-3")
    low = int(found.group(1))
    high = int(found.group(2) or low)
    if low < 1 or high < low:
        raise ConfigError(f"--chapters {spec!r}: cần 1 <= A <= B")
    if low > last:
        raise ConfigError(f"--chapters {spec!r}: truyện mới có {last} chương đã commit")
    return list(range(low, min(high, last) + 1))


# --- client có trần chi phí (G8) -----------------------------------------------------------------

_ROLE_BY_SCHEMA = {"SheetOutput": shots.ROLE, "SceneOutput": shots.ROLE, "ModerationOutput": "moderate"}


class ExportClient(CappedClient):
    """`CappedClient` (llm/capped.py) với tên vai của bộ xuất: giữ chỗ chi phí tối đa trước mỗi lời gọi trong trần
    `--budget` của cả lần xuất, ghi mỗi lời gọi một dòng, không ghi chữ (chữ truyện là truth)."""

    def __init__(self, inner: LLMClient, *, budget: Budget, prices: Mapping[str, ModelPrice],
                 max_tokens: int, record: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(inner, budget=budget, prices=prices, max_tokens=max_tokens, record=record,
                         roles=_ROLE_BY_SCHEMA)


# --- model giả cho --dry-run và test -------------------------------------------------------------


class DryRunLLM(FakeLLM):
    """`--dry-run`: trả câu ghi sẵn theo schema, đủ hợp lệ để đi hết đường. Không mạng, không key."""

    def __init__(self, *, cost_usd: float | None = DRY_RUN_COST_USD) -> None:
        super().__init__([], cost_usd=cost_usd)

    # Tên trong lời thoại theo chữ của ngôn ngữ (SheetOutput kiểm bằng code, nên bản giả phải hợp lệ).
    _NATIVE_NAME: ClassVar[dict[str, str]] = {"zh": "名", "ja": "名", "ko": "이름", "th": "ชื่อ"}

    @classmethod
    def reply(cls, schema: str | None, text: str, system: str = "") -> dict[str, Any]:
        if schema == "SheetOutput":
            tag = re.search(r"\(([a-z]{2,3}(?:-[A-Za-z0-9]+)*)\) dialogue", system)
            native = cls._NATIVE_NAME.get(tag.group(1).split("-")[0]) if tag else None
            head, _, tail = text.partition("Locations:")

            def ids(block: str) -> list[str]:
                return re.findall(r"^- id: (\S+)", block, re.MULTILINE)

            return {"characters": [{"id": i, "visual_en": f"dry-run look of {i}",
                                    "dialogue_name": native or i} for i in ids(head)],
                    "locations": [{"id": i, "visual_en": f"dry-run view of {i}",
                                   "dialogue_name": native or i} for i in ids(tail)]}
        if schema == "SceneOutput":
            cast = text.split("Characters you may use (id: name):", 1)[-1]
            people, _, places = cast.partition("Locations you may use (id: name):")
            who = re.findall(r"^- ([A-Za-z0-9_]+):", people, re.MULTILINE)[:1]
            where = re.findall(r"^- ([A-Za-z0-9_]+):", places, re.MULTILINE)[:1] or ["unknown"]
            return {"shots": [{
                "location_id": where[0], "time_of_day": "unknown", "shot_size": "medium",
                "camera_angle": "eye_level", "camera_move": "static", "duration_s": 5,
                "appears": who, "action_en": "A dry-run action happens in the scene.",
                "dialogue": [], "covers": ""}]}
        if schema == "ModerationOutput":
            return {"findings": [], "reason": "dry-run"}
        raise AssertionError(f"DryRunLLM không biết schema {schema!r}")

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        self.calls.append(list(messages))
        self.extras.append(extra)
        if response_schema is not None:
            self.schemas.append(response_schema)
        body = self.reply(response_schema.__name__ if response_schema else None, messages[-1].content,
                          messages[0].content)
        text = json.dumps(body, ensure_ascii=False)
        chars = sum(len(m.content) for m in messages)
        usage = Usage(prompt_tokens=math.ceil(chars / EST_CHARS_PER_TOKEN),
                      completion_tokens=math.ceil(len(text) / EST_CHARS_PER_TOKEN),
                      cost_usd=self._cost_usd)
        return ChatResult(text=text, usage=usage, model=model, finish_reason="stop")


# --- kết quả ------------------------------------------------------------------------------------


@dataclass
class ShotOut:
    n: int
    location_id: str
    location: str | None
    time_of_day: str
    shot_size: str
    camera_angle: str
    camera_move: str
    duration_s: int
    appears: list[str]
    appears_names: list[str]
    appears_added: list[str]  # nhân vật có tên trong action_en mà model quên ghi vào appears: code bổ sung
    action_en: str
    dialogue: list[dict[str, str]]
    covers: str
    covers_verified: bool
    prompt_en: str | None  # None: bị giữ lại vì kiểm duyệt chặn cứng (G9)
    split_by_code: bool = False  # code sửa vì lời thoại dày hơn thời lượng: tách shot hay kéo dài (D-127)
    pace_over: bool = False  # lời thoại vẫn dày hơn nhịp cho phép (một lượt thoại dài hơn mọi shot)


@dataclass
class SceneOut:
    chapter: int
    scene: int
    status: str  # ok | skipped_budget | error | withheld_moderation | withheld_unmoderated
    shots: list[ShotOut] = field(default_factory=list)
    moderation: dict[str, Any] | None = None
    error: str | None = None
    withheld_shots: int = 0  # số shot bị giữ lại (chặn hay không kiểm duyệt được); chữ của chúng không được ghi


@dataclass
class Export:
    meta: dict[str, Any]
    characters: list[dict[str, Any]]
    locations: list[dict[str, Any]]
    chapters: list[dict[str, Any]]  # mỗi chương: overview (code) + scenes (model)
    stop: str | None = None  # lý do dừng sớm (trần), None = xong

    @property
    def scenes(self) -> list[SceneOut]:
        return [s for c in self.chapters for s in c["scenes"]]


@dataclass
class ExportOptions:
    dialogue_lang: str
    sheets_only: bool = False
    moderate: bool = True
    dry_run: bool = False
    budget_usd: float | None = None
    chapters_spec: str | None = None
    model: str | None = None  # chỉ để ghi vào meta


def _overview_json(o: sheets.ChapterOverview) -> dict[str, Any]:
    return asdict(o)


async def build_export(
    source: StorySource, *, config: AppConfig, llm: LLMClient | None, options: ExportOptions,
    on_scene: Callable[[SceneOut], None] | None = None,
) -> Export:
    """Dựng toàn bộ bản xuất. `llm` None khi `--sheets-only`. `llm` nên là `ExportClient` (trần G8)."""
    limits = config.limits.video_export
    cast = sheets.read_cast(source.state)
    numbers = sorted(source.chapters)
    overviews = {n: sheets.chapter_overview(source.state, cast, n) for n in numbers}
    chapters_json: list[dict[str, Any]] = [
        {"chapter": n, "overview": _overview_json(overviews[n]), "scenes": []} for n in numbers]
    meta = {
        "format": FORMAT, "story_id": source.story_id, "dialogue_lang": options.dialogue_lang,
        "chapters": numbers, "sheets_only": options.sheets_only, "dry_run": options.dry_run,
        "moderation": options.moderate and not options.sheets_only,
        "model": options.model, "prompt_version": shots.PROMPT_VERSION, "generated": date.today().isoformat(),
        # Nhà cung cấp của các model đã gọi (D-140); None khi không gọi model (`--sheets-only`).
        "provider": None if options.model is None else llm_identity(
            config, [options.model, *filter(None, [config.models.roles.moderate])])["provider"],
        "calls": 0, "cost_usd": 0.0, "budget_usd": options.budget_usd,
    }
    export = Export(meta, [], [], chapters_json)

    sheet: shots.Sheet | None = None
    if not options.sheets_only:
        assert llm is not None
        model = require_model(config.models.roles, shots.ROLE)
        extra = role_extra(config.models, shots.ROLE)
        retries = config.limits.retries
        try:
            sheet = await shots.make_sheet(llm, model, cast=cast, chapters=source.chapters,
                                           limits=limits, retries=retries,
                                           lang_tag=options.dialogue_lang, extra=extra)
        except WritoryError as e:
            export.stop = f"sheet: {e.code.value}"
            sheet = None
        if sheet is not None:
            finder = sheets.SceneFinder(cast)
            for entry in chapters_json:
                n = entry["chapter"]
                for k, text in enumerate(source.chapters[n], 1):
                    if export.stop and export.stop.startswith("budget"):
                        scene = SceneOut(n, k, "skipped_budget")
                    else:
                        scene = await _make_scene(
                            n, k, text, llm=llm, model=model, extra=extra, config=config, cast=cast,
                            sheet=sheet, finder=finder, overview=overviews[n], options=options)
                        if (scene.status == "skipped_budget"
                                or (scene.moderation or {}).get("error") == ErrorCode.COST_LIMIT_STORY.value):
                            export.stop = "budget"
                    entry["scenes"].append(scene)
                    if on_scene is not None:
                        on_scene(scene)

    export.characters = [
        {"id": c.id, "name": c.name, "aliases": list(c.aliases), "appearance": c.appearance,
         "personality": c.personality, "protagonist": c.protagonist,
         "visual_en": sheet.characters[c.id].visual_en if sheet else None,
         "dialogue_name": sheet.characters[c.id].dialogue_name if sheet else None,
         "inferred": sheet.characters[c.id].inferred if sheet else None}
        for c in cast.characters.values()]
    export.locations = [
        {"id": loc.id, "name": loc.name, "aliases": list(loc.aliases), "visual": loc.visual,
         "description": loc.description,
         "visual_en": sheet.locations[loc.id].visual_en if sheet else None,
         "dialogue_name": sheet.locations[loc.id].dialogue_name if sheet else None,
         "inferred": sheet.locations[loc.id].inferred if sheet else None}
        for loc in cast.locations.values()]
    return export


async def _make_scene(
    chapter: int, scene: int, text: str, *, llm: LLMClient, model: str, extra: Mapping[str, Any] | None,
    config: AppConfig, cast: sheets.Cast, sheet: shots.Sheet, finder: sheets.SceneFinder,
    overview: sheets.ChapterOverview, options: ExportOptions,
) -> SceneOut:
    limits, retries = config.limits.video_export, config.limits.retries
    people = [cast.characters[i] for i in finder.characters_in(text)]
    # Nơi được nhắc trong cảnh và nơi các nhân vật ở cuối chương đứng trước, rồi tới các nơi còn lại.
    place_ids = list(finder.locations_in(text))
    for _, place in overview.where:
        place_ids += [loc.id for loc in cast.locations.values() if loc.name == place]
    places = [cast.locations[i] for i in dict.fromkeys([*place_ids, *cast.locations])][:15]
    names = {c.id for c in people}
    authored = {c.name for c in people if c.user_authored}
    in_scene = {c.name for c in people}
    relations = [(f"{r.source} → {r.target}: {r.kind}" + ("" if r.score is None else f" ({r.score:+d})"),
                  bool({r.source, r.target} & authored))
                 for r in overview.relationships if r.source in in_scene and r.target in in_scene][:10]
    protagonist = cast.characters.get(cast.protagonist_id or "")
    place_name = next((place for who, place in overview.where if protagonist and who == protagonist.name),
                      None)
    where = None if place_name is None else (place_name, any(
        loc.user_authored for loc in cast.locations.values() if loc.name == place_name))
    known_names = [n for c in cast.characters.values() for n in (c.name, *c.aliases)]
    known_names += [n for loc in cast.locations.values() for n in (loc.name, *loc.aliases)]
    messages = shots.scene_messages(
        chapter=chapter, scene=scene, scene_text=text, characters=people, locations=places,
        relations=relations, where=where, lang_tag=options.dialogue_lang, limits=limits,
        said={i: item.dialogue_name for i, item in {**sheet.characters, **sheet.locations}.items()})
    try:
        draft = await shots.make_scene_shots(
            llm, model, messages, characters=sorted(names), locations=[loc.id for loc in places],
            limits=limits, retries=retries, names=known_names, extra=extra, lang_tag=options.dialogue_lang)
    except WritoryError as e:
        if e.code is ErrorCode.COST_LIMIT_STORY:
            return SceneOut(chapter, scene, "skipped_budget")
        return SceneOut(chapter, scene, "error", error=e.code.value)

    out = SceneOut(chapter, scene, "ok")
    for i, (shot, by_code) in enumerate(zip(draft.shots, draft.split_by_code, strict=True), 1):
        added = shots.mentioned_not_shown(shot.action_en, shot.appears,
                                          {c.id: c.name for c in people})
        shot = shot.model_copy(update={"appears": [*shot.appears, *added]})
        place = sheet.locations.get(shot.location_id)
        out.shots.append(ShotOut(
            n=i, location_id=shot.location_id, location=place.name if place else None,
            time_of_day=shot.time_of_day, shot_size=shot.shot_size, camera_angle=shot.camera_angle,
            camera_move=shot.camera_move, duration_s=shot.duration_s, appears=list(shot.appears),
            appears_names=[sheet.characters[a].name for a in shot.appears], appears_added=added,
            action_en=" ".join(shot.action_en.split()),
            dialogue=[{"speaker_id": d.speaker_id, "speaker": sheet.characters[d.speaker_id].name,
                       "text": " ".join(d.text.split()), "source_text": " ".join(d.source_text.split())}
                      for d in shot.dialogue],
            covers=shot.covers, covers_verified=quote_in_text(shot.covers, text),
            prompt_en=shots.assemble_prompt(shot, sheet=sheet, lang_tag=options.dialogue_lang),
            split_by_code=by_code,
            pace_over=shots.pace_exceeded(shot, limits, options.dialogue_lang)))
    if options.moderate:
        await _moderate_scene(out, llm=llm, config=config)
    return out


def _withhold(scene: SceneOut, status: str) -> None:
    """Giữ lại MỌI chữ model sinh của cảnh (hành động, thoại, prompt): chỉ còn id cảnh, trạng thái và
    danh mục kiểm duyệt, ở cả script.md, script.json và prompts.txt."""
    scene.withheld_shots = len(scene.shots)
    scene.shots = []
    scene.status = status


async def _moderate_scene(scene: SceneOut, *, llm: LLMClient, config: AppConfig) -> None:
    """Kiểm duyệt G9 trên mọi prompt của cảnh (cùng một lời gọi), fail-closed như `safety/moderate.py`:
    bị chặn (BLOCKED, HARD_BLOCKED) hay không kiểm được vì bất kỳ lỗi nào (nội dung bị nhà cung cấp chặn,
    hết lượt thử, hết trần...) thì cảnh bị giữ lại, không có chữ nào của nó trong bản xuất. Chỉ quá mức u
    tối thì giữ cảnh và đánh dấu để admin quyết."""
    text = "\n\n".join(s.prompt_en for s in scene.shots if s.prompt_en)
    try:
        result = await moderate(text, source=Source.SCENE, llm=llm, config=config)
    except WritoryError as e:
        scene.moderation = {"verdict": "not_checked", "error": e.code.value, "categories": []}
        _withhold(scene, "withheld_unmoderated")
        return
    scene.moderation = {"verdict": result.verdict.value, "categories": [c.value for c in result.categories]}
    if result.verdict in (Verdict.HARD_BLOCKED, Verdict.BLOCKED):
        _withhold(scene, "withheld_moderation")
    else:
        scene.moderation["reason"] = result.reason


# --- ghi file -----------------------------------------------------------------------------------


def _fence(text: str, lang: str = "text") -> str:
    return f"```{lang}\n{text}\n```"


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "/").replace("\n", " ")


def _table_head() -> list[str]:
    cols = ["id", "Name", "Name in dialogue", "Look set at story setup (Vietnamese)",
            "Canonical English description", "Source"]
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]


def render_markdown(export: Export) -> str:
    m = export.meta
    out = [f"# Video script: {m['story_id']}", "", f"> **{WARNING}**", ""]
    out.append(f"- Dialogue language: `{m['dialogue_lang']}` ({shots.lang_name(m['dialogue_lang'])})")
    out.append(f"- Chapters: {', '.join(str(c) for c in m['chapters']) or '-'}")
    out.append(f"- Model: `{m['model'] or '-'}` · prompt version `{m['prompt_version']}` · "
               f"calls {m['calls']} · cost {m['cost_usd']:.4f} USD")
    if m["sheets_only"]:
        out.append("- Mode: sheets only (no model): no shots, no prompts.")
    if not m["moderation"] and not m["sheets_only"]:
        out.append("- **Moderation (G9) was OFF for this export.**")
    if export.stop:
        out.append(f"- **Stopped early: {export.stop}.** Shots after this point are missing.")
    out += ["", "## Characters", "", *_table_head()]
    for c in export.characters:
        src = "-" if c["inferred"] is None else ("inferred at export" if c["inferred"] else "setup")
        out.append(f"| {c['id']} | {_cell(c['name'])}{' (protagonist)' if c['protagonist'] else ''} | "
                   f"{_cell(c['dialogue_name'])} | {_cell(c['appearance'])} | {_cell(c['visual_en'])} | {src} |")
    out += ["", "## Locations", "", *_table_head()]
    for loc in export.locations:
        src = "-" if loc["inferred"] is None else ("inferred at export" if loc["inferred"] else "setup")
        out.append(f"| {loc['id']} | {_cell(loc['name'])} | {_cell(loc['dialogue_name'])} | "
                   f"{_cell(loc['visual'])} | {_cell(loc['visual_en'])} | {src} |")
    for chapter in export.chapters:
        o = chapter["overview"]
        out += ["", f"## Chapter {chapter['chapter']}", "", "### Relationship map (end of chapter)", "",
                _fence(o["mermaid"], "mermaid"), ""]
        if o["where"]:
            out.append("**Where they are:** " + "; ".join(f"{w} at {p}" for w, p in o["where"]))
        for k in o["knowledge"]:
            how = f" ({k['how']})" if k["how"] else ""
            out.append(f"- **Learns ({k['kind']}):** {k['who']}{how}: {k['text']}")
        for e in o["events"]:
            who = f" [{', '.join(e['participants'])}]" if e["participants"] else ""
            died = f" **Dies: {', '.join(e['died'])}.**" if e["died"] else ""
            out.append(f"- **Event:** {e['text']}{who}{died}")
        for lie in o["lies"]:
            out.append(f"- **Lie told by {lie['speaker'] or '?'}:** {lie['text']}")
        for scene in chapter["scenes"]:
            out += ["", f"### Scene {scene.chapter}.{scene.scene}", ""]
            if scene.status != "ok":
                out.append(f"*Status: {scene.status}" + (f" ({scene.error})" if scene.error else "") + "*")
            if scene.moderation:
                mod = scene.moderation
                out.append(f"*Moderation: {mod['verdict']}"
                           + (f" [{', '.join(mod['categories'])}]" if mod["categories"] else "") + "*")
            for s in scene.shots:
                head = (f"{s.shot_size} · {s.camera_angle} · {s.camera_move} · {s.duration_s} s · "
                        f"{s.time_of_day} · {s.location or 'unknown place'}")
                out += ["", f"#### Shot {s.n}: {head}", ""]
                out.append(f"- Appears: {', '.join(s.appears_names) or '-'}")
                out.append(f"- Action: {s.action_en}")
                for d in s.dialogue:
                    out.append(f"- {d['speaker']}: \"{d['text']}\" (original: \"{d['source_text']}\")")
                if not s.covers_verified:
                    out.append("- *Note: the quoted source phrase was not found verbatim in the scene.*")
                if s.split_by_code:
                    out.append("- *Note: dialogue pace fixed by code (the shot was split or lengthened to fit "
                               "its lines).*")
                if s.pace_over:
                    out.append("- *Note: the dialogue is denser than the pace limit; one line is longer than "
                               "any shot can carry.*")
                out += ["", _fence(s.prompt_en or "[withheld: moderation hard block]")]
    return "\n".join(out) + "\n"


def render_prompts(export: Export) -> str:
    blocks = []
    for scene in export.scenes:
        for s in scene.shots:
            if s.prompt_en:
                blocks.append(f"# {scene.chapter}.{scene.scene}.{s.n}\n{s.prompt_en}")
    return "\n\n".join([f"// {WARNING}", *blocks]) + "\n"


def export_json(export: Export) -> dict[str, Any]:
    chapters = [{**c, "scenes": [asdict(s) for s in c["scenes"]]} for c in export.chapters]
    return {"warning": WARNING, "meta": export.meta, "characters": export.characters,
            "locations": export.locations, "chapters": chapters, "stop": export.stop}


OUTPUT_FILES = ("script.md", "script.json", "prompts.txt", "calls.jsonl")


def check_fresh(out: Path) -> None:
    """Từ chối khi thư mục đã có kết quả: một lần chạy sau không đè bản xuất đã trả tiền, và không để lại
    `calls.jsonl` cũ cạnh bản mới."""
    found = [n for n in OUTPUT_FILES if (out / n).exists()]
    if found:
        raise ConfigError(f"đã có kết quả ở {out} ({', '.join(found)}); dùng --out khác hoặc xoá thư mục đó")


def _write_atomically(out: Path, files: Mapping[str, str]) -> list[Path]:
    """Ghi vào thư mục tạm cạnh `out` rồi đổi tên: lỗi giữa chừng không để lại nửa bản xuất."""
    check_fresh(out)
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


def write_export(export: Export, out: Path, calls: Sequence[dict[str, Any]] = ()) -> list[Path]:
    files = {
        "script.md": render_markdown(export),
        "script.json": json.dumps(export_json(export), ensure_ascii=False, indent=2) + "\n",
        "prompts.txt": render_prompts(export),
    }
    if calls:
        files["calls.jsonl"] = "".join(
            json.dumps(c, ensure_ascii=False) + "\n" for c in [{"note": WARNING}, *calls])
    return _write_atomically(out, files)


# --- lệnh ---------------------------------------------------------------------------------------


class ExportServices(BaseSettings):
    """Kết nối Neo4j + Postgres. Chỉ đọc bốn biến này, không đọc key nào."""

    model_config = SettingsConfigDict(extra="ignore", hide_input_in_errors=True)  # G7
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr
    postgres_dsn: SecretStr


def default_out(story_id: str, today: date | None = None) -> Path:
    return DEFAULT_OUT_ROOT / f"{story_id}-{(today or date.today()).strftime('%Y%m%d')}"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m writory.export.video",
        description="Xuất kịch bản video của một truyện (chỉ admin; có lộ bí mật).")
    p.add_argument("--story", required=True, help="id truyện")
    p.add_argument("--dialogue-lang", default="en", help="ngôn ngữ lời thoại: zh, vi, en... (mặc định en)")
    p.add_argument("--chapters", help="N hoặc A-B (mặc định cả truyện)")
    p.add_argument("--out", help="thư mục xuất (mặc định exports/<story>-<ngày>/, git bỏ qua)")
    p.add_argument("--budget", type=float, help="trần chi phí USD của lần xuất (bắt buộc khi chạy thật)")
    p.add_argument("--env-file", default=str(REPO_ROOT / ".env"))
    p.add_argument("--config-dir", default=str(REPO_CONFIG_DIR))
    p.add_argument("--sheets-only", action="store_true", help="chỉ phần bằng code: không model, không tiền")
    p.add_argument("--dry-run", action="store_true", help="model giả, không mạng, không key")
    p.add_argument("--no-moderate", action="store_true", help="tắt kiểm duyệt G9 trên prompt cuối")
    return p


def check_budget(config: AppConfig, budget: float | None, *, real: bool) -> float | None:
    cap = config.limits.video_export.require("max_budget_usd")
    if not real:
        return budget
    if budget is None:
        raise ConfigError("chạy thật cần --budget (USD)")
    if not (math.isfinite(budget) and 0 < budget <= cap):  # nan, inf: qua được phép so, nên kiểm thẳng
        raise ConfigError(f"--budget {budget} phải trong (0, {cap}] (limits.video_export.max_budget_usd)")
    return budget


def load_source(services: ExportServices, story_id: str, spec: str | None) -> tuple[StorySource, Any]:
    """Đọc truyện từ Postgres và Neo4j. Chỉ đọc. Trả cả driver để nơi gọi đóng."""
    from neo4j import GraphDatabase

    from writory.db.chapters import chapter_scenes, get_story
    from writory.db.connection import connect
    from writory.guard.state import Neo4jState

    class _Settings:  # connect() chỉ cần postgres_dsn
        postgres_dsn = services.postgres_dsn

    conn = connect(_Settings())  # type: ignore[arg-type]
    try:
        story = get_story(conn, story_id)
        last = story.committed_chapter
        if not last:
            raise ConfigError(f"truyện {story_id} chưa có chương nào đã commit")
        numbers = parse_chapters(spec, last)
        chapters = {n: list(chapter_scenes(conn, story_id, n) or []) for n in numbers}
    finally:
        conn.close()
    driver = GraphDatabase.driver(
        services.neo4j_uri, auth=(services.neo4j_user, services.neo4j_password.get_secret_value()))
    return StorySource(story_id, chapters, Neo4jState(driver, story_id)), driver


async def run(args: argparse.Namespace, *, source: StorySource | None = None,
              llm: LLMClient | None = None, today: date | None = None) -> int:
    """`source` và `llm` chỉ để test truyền vào; lệnh thật tự dựng."""
    from writory.config import LimitNotSetError

    install_log_redaction()
    try:
        lang = shots.check_lang(args.dialogue_lang)
        config = load_config(Path(args.config_dir))
        real = not (args.dry_run or args.sheets_only)
        budget = check_budget(config, args.budget, real=real)
        if args.sheets_only and (args.dry_run or args.budget is not None):
            raise ConfigError("--sheets-only không dùng model: bỏ --dry-run và --budget")
        out = Path(args.out) if args.out else default_out(args.story, today)
        check_fresh(out)  # trước mọi lời gọi tốn tiền: không đè bản xuất cũ
        if args.no_moderate and not args.sheets_only:
            print("CẢNH BÁO: --no-moderate: prompt cuối KHÔNG qua kiểm duyệt G9 (D-125); admin chịu "
                  "trách nhiệm trước khi đưa sang app video.", file=sys.stderr)
        services = driver = None
        if source is None:
            env_file = Path(args.env_file)
            services = ExportServices(_env_file=env_file if env_file.exists() else None)  # type: ignore[call-arg]
            source, driver = load_source(services, args.story, args.chapters)
        calls: list[dict[str, Any]] = []
        client: ExportClient | None = None
        options = ExportOptions(lang, sheets_only=args.sheets_only, moderate=not args.no_moderate,
                                dry_run=args.dry_run, budget_usd=budget, chapters_spec=args.chapters)
        if not args.sheets_only:
            limits = config.limits.video_export
            options.model = require_model(config.models.roles, shots.ROLE)
            inner = llm
            if inner is None:
                if args.dry_run:
                    inner = DryRunLLM()
                else:
                    from writory.llm.openrouter import call_deadline
                    from writory.llm.provider import bench_llm

                    deadline = call_deadline(config)  # chưa đặt: CONFIG_LIMIT_NOT_SET (D-113)
                    inner = bench_llm(config, Path(args.env_file), deadline_s=deadline,
                                      models=[options.model, *filter(None, [config.models.roles.moderate])])
            client = ExportClient(
                inner, budget=Budget("export", math.inf if budget is None else budget),
                prices=config.models.prices, max_tokens=limits.require("max_output_tokens"),
                record=calls.append)
    except ValidationError as e:
        names = ", ".join(sorted({str(err["loc"][0]).upper() for err in e.errors() if err["loc"]}))
        return _fail("EXPORT_ENV_MISSING", f"Thiếu biến môi trường {names} (trong môi trường hoặc "
                     "--env-file). Đặt chúng như trong .env.example rồi chạy lại.")
    except StoryNotFoundError:
        return _fail("EXPORT_STORY_NOT_FOUND", f"Không có truyện {args.story} trong database. Kiểm lại "
                     "--story: id nằm ở cột id của bảng stories trong Postgres.")
    except (psycopg.Error, Neo4jError, DriverError) as e:
        # Chỉ ghi tên loại lỗi: thân lỗi của driver có thể chứa DSN hay mật khẩu (G7).
        return _fail("EXPORT_DB_UNAVAILABLE", "Không kết nối hay đọc được Postgres hoặc Neo4j "
                     f"({type(e).__name__}). Kiểm Docker đang chạy (docker compose up -d) và các biến "
                     "POSTGRES_DSN, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD.")
    except (ConfigError, ValueError, LimitNotSetError, WritoryError) as e:
        print(f"lỗi: {redact(str(e))}", file=sys.stderr)
        return EXIT_CONFIG
    try:
        export = await build_export(source, config=config, llm=client, options=options)
    finally:
        if driver is not None:
            driver.close()
    export.meta["calls"] = len(calls)
    export.meta["cost_usd"] = round(client.spent_usd if client else 0.0, 6)
    written = write_export(export, out, calls)
    print(f"đã ghi {len(written)} file vào {out}; {export.meta['calls']} lời gọi, "
          f"{export.meta['cost_usd']:.4f} USD", file=sys.stderr)
    if export.stop in ("budget", f"sheet: {ErrorCode.COST_LIMIT_STORY.value}"):
        return EXIT_BUDGET
    if export.stop or any(s.status in ("error", "withheld_unmoderated") for s in export.scenes):
        return EXIT_ERRORS
    return EXIT_OK


def _fail(code: str, sentence: str) -> int:
    """Lỗi của lệnh: mã riêng và câu tiếng Việt nói rõ chuyện gì xảy ra và làm gì tiếp (G12), qua `redact`."""
    print(f"lỗi {code}: {redact(sentence)}", file=sys.stderr)
    return EXIT_CONFIG


def main(argv: Sequence[str] | None = None) -> int:
    # Console Windows mặc định cp1252: chữ Việt của --help và của lỗi làm lệnh sập (như bench_run).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return asyncio.run(run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
