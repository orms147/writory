"""Biến thể đề cho bộ đo (D-109): so hai bản đề trên CÙNG một thế giới mà không đổi mã.

Một biến thể là một thư mục `evals/scenarios/prompts/<tên>/`, mỗi file thay một đề; thiếu file nào
thì dùng đề mặc định của mã:

- `outline_system.md`: system prompt của vai dàn ý (thay `scene.OUTLINE_SYSTEM_PROMPT`);
- `choices_system.md`: system prompt của vai tạo lựa chọn (thay `choices.SYSTEM_PROMPT`);
- `goals.yaml`: ánh xạ khoá → câu, thay các câu cố định của mục tiêu chương
  (`pacing.GOAL_DEFAULTS`). `standstill` phải có đủ `{place}` và `{chapters}`; `idle` và `phase_shift`
  phải có `{chapters}`; các khoá khác không được có chỗ điền.

Hướng dẫn văn phong của model viết (system prompt của vai viết) KHÔNG nằm ở đây: dùng cờ
`--style-guide <file>` của `bench_run`.

Chỉ bộ đo đọc module này (`bench_run`). Sản phẩm nhận `PromptTexts` (chuỗi thuần) hoặc không nhận gì;
nó không biết thư mục, tên biến thể hay cờ nào. Đề ghi đè là chữ của nhà phát triển: vào vai system
(`system_message` vẫn từ chối khối `player_data`) hoặc là câu cố định của mục tiêu chương; chữ người
chơi không đi qua đây và vẫn được bọc như cũ (G4).
"""

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from writory.config import REPO_ROOT, ConfigError
from writory.pipeline.pacing import GOAL_DEFAULTS
from writory.pipeline.scene import PromptTexts
from writory.safety.wrap import OPEN_TAG_START

PROMPTS_DIR = REPO_ROOT / "evals" / "scenarios" / "prompts"
OUTLINE_FILE, CHOICES_FILE, GOALS_FILE = "outline_system.md", "choices_system.md", "goals.yaml"
VARIANT_FILES = (OUTLINE_FILE, CHOICES_FILE, GOALS_FILE)
IGNORED_FILES = ("README.md",)
GOAL_KEYS = frozenset(GOAL_DEFAULTS)
_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
_PLACEHOLDERS = {"standstill": ("{place}", "{chapters}"), "idle": ("{chapters}",),
                 "phase_shift": ("{chapters}",)}
_ANY_PLACEHOLDER = ("{place}", "{chapters}")


@dataclass(frozen=True)
class PromptVariant:
    name: str
    outline_system: str | None = None
    choices_system: str | None = None
    goal_texts: Mapping[str, str] = field(default_factory=dict)
    files: Mapping[str, str] = field(default_factory=dict)  # tên file -> sha256 của nội dung

    def overrides(self) -> list[str]:
        out = []
        if self.outline_system is not None:
            out.append("outline_system")
        if self.choices_system is not None:
            out.append("choices_system")
        out += [f"goals:{key}" for key in self.goal_texts]
        return out

    def texts(self) -> PromptTexts:
        return PromptTexts(self.outline_system, self.choices_system, dict(self.goal_texts))

    def as_meta(self) -> dict[str, Any]:
        """Ghi vào `meta.json`: tên, hash từng file và các đề bị thay. Hash là danh tính của biến thể
        (hai tên khác nhau mà cùng nội dung là cùng một đề)."""
        return {"name": self.name, "files": dict(self.files), "overrides": self.overrides()}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8").strip()
    if not text:
        raise ConfigError(f"{path.name} rỗng: xoá file nếu muốn dùng đề mặc định")
    if OPEN_TAG_START in text:
        raise ConfigError(f"{path.name} chứa khối player_data: đề ghi đè là chữ của nhà phát triển "
                          "(G4)")
    return text, _sha256(raw)


def _goals(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"{path.name} không phải YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name} phải là một ánh xạ khoá → câu (khoá: {sorted(GOAL_KEYS)})")
    unknown = sorted(set(data) - GOAL_KEYS)
    if unknown:
        raise ConfigError(f"{path.name}: khoá lạ {unknown}; khoá hợp lệ: {sorted(GOAL_KEYS)}")
    out = {}
    for key, value in data.items():
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"{path.name}: {key} rỗng hoặc không phải chuỗi")
        if OPEN_TAG_START in value:
            raise ConfigError(f"{path.name}: {key} chứa khối player_data (G4)")
        needed = _PLACEHOLDERS.get(key, ())
        for holder in needed:
            if holder not in value:
                raise ConfigError(f"{path.name}: {key} thiếu chỗ điền {holder}")
        for holder in _ANY_PLACEHOLDER:
            if holder in value and holder not in needed:
                raise ConfigError(f"{path.name}: {key} không có chỗ điền {holder}")
        out[key] = value.strip()
    return out, _sha256(raw)


def load_prompt_variant(name: str, *, root: Path = PROMPTS_DIR) -> PromptVariant:
    """Đọc một biến thể. Lỗi (tên lạ, thiếu thư mục, file lạ, nội dung sai) báo trước khi gọi model."""
    if not _NAME.fullmatch(name or ""):
        raise ConfigError(f"tên biến thể {name!r} không hợp lệ: chỉ a-z, 0-9, '_' và '-', "
                          "bắt đầu bằng chữ hoặc số")
    folder = root / name
    if not folder.is_dir():
        have = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        raise ConfigError(f"không có biến thể {name!r} trong {root.name}/ (có: {have or 'chưa có'})")
    present = {p.name for p in folder.iterdir() if p.is_file()}
    odd = sorted(present - set(VARIANT_FILES) - set(IGNORED_FILES))
    if odd:
        raise ConfigError(f"biến thể {name!r} có file lạ {odd}; chỉ nhận {list(VARIANT_FILES)}")
    if not present & set(VARIANT_FILES):
        raise ConfigError(f"biến thể {name!r} không đổi gì: cần ít nhất một trong {list(VARIANT_FILES)}")
    files: dict[str, str] = {}
    outline = choices = None
    goals: dict[str, str] = {}
    if OUTLINE_FILE in present:
        outline, files[OUTLINE_FILE] = _text(folder / OUTLINE_FILE)
    if CHOICES_FILE in present:
        choices, files[CHOICES_FILE] = _text(folder / CHOICES_FILE)
    if GOALS_FILE in present:
        goals, files[GOALS_FILE] = _goals(folder / GOALS_FILE)
    return PromptVariant(name=name, outline_system=outline, choices_system=choices,
                         goal_texts=goals, files=files)
