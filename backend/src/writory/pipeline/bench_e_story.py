"""Nguồn truyện cho bài đo E (D-60): truyện mẫu dựng tay, hoặc truyện do pipeline viết; và sổ tay
đệm cho nhóm câu hỏi "sổ tay lớn".

- `load_sample_story`: gói dựng tay của `data/sample-story/`. Kế hoạch và thiết lập truyện do
  `plan.yaml` của đề khai, vì truyện mẫu không qua bước khởi tạo.
- `load_run_story`: đọc thư mục kết quả của `pipeline.bench_run` (`truth_dump.json`: kế hoạch và
  gói từng chương; `setup.json` + `meta.json`: lựa chọn của bước khởi tạo). Kế hoạch là kế hoạch
  model khởi tạo đã đặt, kể cả `leak_terms`; `story_brief` dựng lại bằng đúng hàm
  `pipeline.setup.story_brief` đã dùng lúc chạy. Đây chính là điều bài đo muốn đo: bộ dò lộ chạy
  với chuỗi cấm do model đặt, không phải chuỗi viết tay.
- `pad_view`: thêm mục giả vào `PlayerView` để dựng sổ tay hàng trăm mục từ truyện vài chương.
  Mục đệm sinh bằng code từ một hạt giống khai trong đề (tất định), có tên và từ ngữ giống truyện
  ("lò rèn của ...", "thanh kiếm ...") để truy hồi phải phân biệt, và không chứa tên hay chuỗi cấm
  của truyện (test kiểm bằng bộ chấm).
"""

import hashlib
import json
import random
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, PositiveInt, ValidationError

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.graph import ChangePackage, PlayerEntry, PlayerView
from writory.graph.sample import read_sample
from writory.pipeline.setup import (
    CharacterOption,
    PlotOption,
    SettingOption,
    StoryChoices,
    story_brief,
)
from writory.pipeline.story_plan import StoryPlan

SAMPLE_DIR = REPO_ROOT / "data" / "sample-story"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as e:
        raise ConfigError(f"không đọc được {path}: {e}") from None


def _json(path: Path, raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ConfigError(f"{path.name} không phải JSON hợp lệ: {e}") from None


@dataclass(frozen=True)
class Story:
    """Những gì bài đo cần biết về một truyện: gói thay đổi theo chương (gồm chương 0)."""

    kind: str  # "sample" | "run"
    packages: tuple[tuple[int, ChangePackage], ...]
    plan: StoryPlan | None  # kế hoạch lúc chạy thật; None: `plan.yaml` của đề khai
    brief: str | None  # thiết lập truyện người chơi đã đọc; None: `plan.yaml` khai
    hashes: Mapping[str, str]  # sha256 các file nguồn, ghi vào meta.json của kết quả

    @property
    def chapters(self) -> tuple[int, ...]:
        return tuple(n for n, _ in self.packages if n >= 1)

    def packages_upto(self, chapter: int) -> list[ChangePackage]:
        return [pkg for n, pkg in self.packages if n <= chapter]

    def all_packages(self) -> list[ChangePackage]:
        return [pkg for _, pkg in self.packages]


def load_sample_story(sample_dir: Path | None = None) -> Story:
    root = sample_dir or SAMPLE_DIR
    sample = read_sample(root)
    graph_raw = _read(root / "graph.yaml")
    return Story("sample", tuple((c.number, c.package) for c in sample.chapters), None, None,
                 {"sample-story/graph.yaml": _sha256(graph_raw)})


def _option(setup: Mapping[str, Any], step: str, cls: type[BaseModel]) -> Any:
    try:
        block = setup[step]
        return cls.model_validate(block["options"][block["picked"]])
    except (KeyError, IndexError, TypeError, ValidationError) as e:
        raise ConfigError(f"setup.json: bước {step!r} thiếu hoặc sai ({type(e).__name__})") from None


def load_run_story(run_dir: Path | str) -> Story:
    """Đọc thư mục kết quả của `bench_run`. Thiếu file hoặc sai dạng thì ConfigError, nêu tên file."""
    run_dir = Path(run_dir)
    files = {name: _read(run_dir / name) for name in ("truth_dump.json", "setup.json", "meta.json")}
    dump = _json(Path("truth_dump.json"), files["truth_dump.json"])
    setup = _json(Path("setup.json"), files["setup.json"])
    meta = _json(Path("meta.json"), files["meta.json"])
    try:
        raw_packages = dump["packages"]
        packages = tuple(sorted(
            ((int(n), ChangePackage.model_validate(p)) for n, p in raw_packages.items()),
            key=lambda item: item[0]))
        plan = StoryPlan.model_validate(dump["plan"])
    except (KeyError, AttributeError, TypeError, ValueError, ValidationError) as e:
        raise ConfigError(f"truth_dump.json thiếu hoặc sai `packages`/`plan`: "
                          f"{type(e).__name__}: {e}") from None
    if not packages or packages[0][0] != 0:
        raise ConfigError("truth_dump.json: `packages` phải có gói chương 0")
    try:
        content = meta["scenario"]["content"]
        # Lần chạy sau D-67 ghi `darkness_level` vào đề (kể cả null = mặc định), và thiết lập của
        # nó có dòng mức u tối; lần chạy trước đó không có dòng này.
        keys = ("tags", "length_level", "pov", "naming", "darkness_level")
        choices = StoryChoices.model_validate({k: content[k] for k in keys if k in content})
        with_level = "darkness_level" in content
    except (KeyError, TypeError, ValidationError) as e:
        raise ConfigError(f"meta.json: thiếu hoặc sai `scenario.content` ({type(e).__name__})"
                          ) from None
    # Chữ mức u tối lấy từ config/moderation.yaml hiện hành (lần chạy không lưu chữ thiết lập).
    brief = story_brief(choices, _option(setup, "settings", SettingOption),
                        _option(setup, "plots", PlotOption),
                        _option(setup, "characters", CharacterOption),
                        moderation=load_config().moderation if with_level else None)
    return Story("run", packages, plan, brief,
                 {f"run/{name}": _sha256(raw) for name, raw in files.items()})


# --- sổ tay đệm -------------------------------------------------------------------------------


class PadSpec(BaseModel):
    """Tham số sổ tay đệm, khai trong đề (`notebook_pad`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    count: PositiveInt
    seed: int


# Họ, đệm, tên và địa danh cố ý khác tên trong truyện mẫu và truyện tu tiên đã chạy.
_HO = ("Ngô", "Dương", "Tạ", "Lương", "Mạc", "Quách", "Tô", "Cao", "Viên", "Thái")
_DEM = ("Văn", "Thị", "Đình", "Quang", "Gia", "Kim", "Hữu")
_TEN = ("Phúc", "Hạnh", "Tín", "Nghĩa", "Thịnh", "Hải", "Quý", "Tùng", "Bảo", "Khoa", "Duyên",
        "Hiếu", "Lộc", "Thảo")
_NICK = ("Bác", "Chú", "Cô", "Thím", "Lão")
_STREET = ("chợ", "bến", "miếu", "quán trà", "quán rượu", "lò rèn", "tiệm thuốc", "nhà kho",
           "xưởng thuyền", "trạm gác")
_THING = ("thanh kiếm cũ", "lá thư", "chiếc nhẫn đồng", "cuốn sổ nợ", "gói trà", "tấm bản đồ",
          "chiếc chìa khoá", "con dao nhỏ")
_ACT = ("trả nợ cho", "mượn tiền của", "cãi nhau với", "nhờ vả", "gửi lời cho", "bán hàng cho")

_KIND_SHARE = (("Character", 0.25), ("Location", 0.15), ("Item", 0.15), ("Fact", 0.25),
               ("Event", 0.20))


def pad_view(view: PlayerView, spec: PadSpec) -> PlayerView:
    """`view` cộng `spec.count` mục giả. Mục thật giữ nguyên; mục giả có id `pad-NNNN`, chương từ
    1 tới chương của `view`, và chỉ liên kết (`about`) với mục giả khác."""
    rng = random.Random(spec.seed)
    taken = {e.text for e in view.entries}
    top = max(1, view.chapter)

    def fresh(make) -> str:
        for _ in range(60):
            text = make()
            if text not in taken:
                taken.add(text)
                return text
        text = f"{make()} số {len(taken)}"
        taken.add(text)
        return text

    def person() -> str:
        return f"{rng.choice(_HO)} {rng.choice(_DEM)} {rng.choice(_TEN)}"

    def place(owner: str) -> str:
        return f"{rng.choice(_STREET)} của {owner}"

    counts = {k: max(1, round(spec.count * share)) for k, share in _KIND_SHARE}
    counts["Event"] += spec.count - sum(counts.values())  # đủ đúng `count`
    rows: list[PlayerEntry] = []
    people: list[str] = []

    def add(kind: str, text: str, about: tuple[str, ...] = (), aliases: tuple[str, ...] = ()):
        nid = f"pad-{len(rows):04d}"
        quote = f"Trên trang có nhắc: {text}."
        rows.append(PlayerEntry(nid, kind, text, aliases, rng.randint(1, top), quote, about,
                                (quote,)))
        return nid

    for _ in range(counts["Character"]):
        name = fresh(person)
        nick = (f"{rng.choice(_NICK)} {name.split()[-1]}",) if rng.random() < 0.4 else ()
        people.append(add("Character", name, aliases=nick))
    ids = [e.id for e in rows]
    for _ in range(counts["Location"]):
        add("Location", fresh(lambda: place(rng.choice(people))))
    for _ in range(counts["Item"]):
        add("Item", fresh(lambda: f"{rng.choice(_THING)} của {rng.choice(people)}"))
    for _ in range(counts["Fact"]):
        a, b = rng.sample(range(len(people)), 2)
        text = fresh(lambda a=a, b=b: f"{people[a]} đã {rng.choice(_ACT)} {people[b]}")
        add("Fact", text, about=(ids[a], ids[b]))
    for _ in range(counts["Event"]):
        a = rng.randrange(len(people))
        text = fresh(lambda a=a: f"{people[a]} đến {place(rng.choice(people))} vào canh "
                                 f"{rng.randint(1, 5)}")
        add("Event", text, about=(ids[a],))
    return PlayerView(view.story_id, view.chapter, (*view.entries, *rows), view.lies)
