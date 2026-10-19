"""Kiểm chất lượng văn bằng code (design §6.5 mục 5). Không gọi model.

Mọi hàm chuẩn hoá NFC trước khi kiểm; vị trí `start`/`end` tính trên chuỗi đã chuẩn hoá NFC.
Ngưỡng và danh sách lấy từ config/quality.yaml (D-19); độ dài từ config/story_lengths.yaml.
Regex ở đây chỉ kiểm định dạng chữ, không đọc ý định người dùng (G5).
"""

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from writory.config import LimitNotSetError, QualityConfig, StoryLengthsConfig
from writory.errors import ErrorCode, WritoryError

_EXCERPT_MAX_CHARS = 120


class IssueKind(StrEnum):
    LENGTH = "length"
    REPETITION = "repetition"
    CLICHE = "cliche"
    FOREIGN_SCRIPT = "foreign_script"
    DIALOGUE_FORMAT = "dialogue_format"
    UNCLOSED_QUOTE = "unclosed_quote"


@dataclass(frozen=True)
class QualityIssue:
    kind: IssueKind
    start: int
    end: int
    excerpt: str
    detail: str


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _issue(text: str, kind: IssueKind, start: int, end: int, detail: str) -> QualityIssue:
    excerpt = text[start:end]
    if len(excerpt) > _EXCERPT_MAX_CHARS:
        excerpt = excerpt[:_EXCERPT_MAX_CHARS] + "…"
    return QualityIssue(kind, start, end, excerpt, detail)


def _require(section, name: str):
    try:
        return section.require(name)
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None


# --- độ dài -------------------------------------------------------------------------------


def check_length(
    text: str, scenes_in_chapter: int, lengths: StoryLengthsConfig
) -> list[QualityIssue]:
    """Khoảng ký tự của một cảnh = chapter_chars chia cho số cảnh thực tế của chương."""
    allowed = lengths.scenes_per_chapter
    if not allowed.min <= scenes_in_chapter <= allowed.max:
        raise ValueError(
            f"scenes_in_chapter={scenes_in_chapter} ngoài khoảng {allowed.min}–{allowed.max}"
        )
    text = _nfc(text)
    count = len(re.sub(r"\s+", " ", text).strip())
    low = lengths.chapter_chars.min // scenes_in_chapter
    high = lengths.chapter_chars.max // scenes_in_chapter
    if low <= count <= high:
        return []
    return [
        _issue(
            text, IssueKind.LENGTH, 0, len(text),
            f"cảnh dài {count} ký tự, cần {low}–{high} (chương {scenes_in_chapter} cảnh)",
        )
    ]


# --- lặp cụm từ ---------------------------------------------------------------------------

_WORD = re.compile(r"[^\W\d_]+")


def check_repetition(text: str, quality: QualityConfig) -> list[QualityIssue]:
    """Cụm `ngram_words` từ xuất hiện quá `max_repeats` lần. Báo ở các lần vượt; các lần vượt
    chồng lên nhau (một câu dài bị lặp) gộp thành một lỗi."""
    n = _require(quality.repetition, "ngram_words")
    max_repeats = _require(quality.repetition, "max_repeats")
    text = _nfc(text)
    words = [(m.group().casefold(), m.start(), m.end()) for m in _WORD.finditer(text)]
    occurrences: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i in range(len(words) - n + 1):
        occurrences[tuple(w for w, _, _ in words[i : i + n])].append(i)

    spans: list[tuple[int, int, int, tuple[str, ...]]] = []
    for gram, starts in occurrences.items():
        for i in starts[max_repeats:]:
            spans.append((words[i][1], words[i + n - 1][2], len(starts), gram))
    spans.sort()

    merged: list[list] = []
    for start, end, count, gram in spans:
        if merged and start <= merged[-1][1]:
            last = merged[-1]
            last[1] = max(last[1], end)
            if count > last[2]:
                last[2], last[3] = count, gram
        else:
            merged.append([start, end, count, gram])
    return [
        _issue(
            text, IssueKind.REPETITION, start, end,
            f'cụm "{" ".join(gram)}" xuất hiện {count} lần (tối đa {max_repeats})',
        )
        for start, end, count, gram in merged
    ]


# --- sáo ngữ ------------------------------------------------------------------------------


def check_cliches(text: str, quality: QualityConfig) -> list[QualityIssue]:
    text = _nfc(text)
    issues = []
    for phrase in quality.cliches.phrases:
        words = _nfc(phrase).split()
        pattern = re.compile(
            r"(?<!\w)" + r"\s+".join(re.escape(w) for w in words) + r"(?!\w)", re.IGNORECASE
        )
        for m in pattern.finditer(text):
            issues.append(
                _issue(text, IssueKind.CLICHE, m.start(), m.end(), f'sáo ngữ: "{phrase}"')
            )
    return issues


# --- lẫn chữ khác hệ ----------------------------------------------------------------------

_CJK_RUN = re.compile(
    "["
    "ᄀ-ᇿ"  # Hangul Jamo
    "　-〿"  # dấu câu CJK
    "぀-ヿ"  # Hiragana, Katakana
    "㄰-㆏"  # Hangul Compatibility Jamo
    "㐀-䶿"  # Hán mở rộng A
    "一-鿿"  # Hán
    "가-힯"  # Hangul
    "豈-﫿"  # Hán tương thích
    "＀-￯"  # ký tự toàn độ rộng
    "\U00020000-\U0002ebef"  # Hán mở rộng B–F
    "]+"
)

# Âm tiết tiếng Việt viết không dấu (chỉ chữ ASCII). Cố ý rộng: thà bỏ sót từ ngoại
# còn hơn báo nhầm một âm tiết tiếng Việt không dấu như "anh", "ta", "con".
_VI_SYLLABLE_ASCII = re.compile(
    r"(ngh|ng|gh|gi|kh|nh|ph|qu|th|tr|ch|[bcdghklmnprstvx])?"
    r"[ou]?"
    r"(ie|ye|ia|ya|uo|ua|oo|[aeiouy])"
    r"(ch|nh|ng|[cmnptiyou])?"
)


def check_foreign_script(text: str, quality: QualityConfig) -> list[QualityIssue]:
    """Chữ Hán/Kana/Hangul: luôn báo, mỗi đoạn liền một lỗi.
    Chữ Latin: báo khi có từ `latin_run_min_words` từ không phải âm tiết tiếng Việt và không
    nằm trong danh sách từ mượn, đứng trong một chuỗi không bị từ có dấu chen ngang."""
    min_words = _require(quality.foreign_script, "latin_run_min_words")
    allowed = {w.casefold() for w in quality.foreign_script.allowed_latin_words}
    text = _nfc(text)
    issues = [
        _issue(text, IssueKind.FOREIGN_SCRIPT, m.start(), m.end(), "chữ Hán/Nhật/Hàn")
        for m in _CJK_RUN.finditer(text)
    ]

    def flush(run: list[re.Match]) -> None:
        if len(run) >= min_words:
            issues.append(
                _issue(
                    text, IssueKind.FOREIGN_SCRIPT, run[0].start(), run[-1].end(),
                    f"{len(run)} từ Latin không phải tiếng Việt liền nhau",
                )
            )

    run: list[re.Match] = []
    for m in _WORD.finditer(text):
        word = m.group()
        if not word.isascii():
            flush(run)  # từ có dấu (hoặc chữ hệ khác) cắt chuỗi
            run = []
            continue
        folded = word.casefold()
        if folded in allowed or _VI_SYLLABLE_ASCII.fullmatch(folded):
            continue  # không đếm, không cắt chuỗi
        run.append(m)
    flush(run)
    return issues


# --- lời thoại ----------------------------------------------------------------------------

_EM_DASH = "—"
_WRONG_DASHES = "–-−"  # en dash, gạch nối, dấu trừ
_ONLY_DASHES = re.compile(rf"[{_EM_DASH}{_WRONG_DASHES}\s]+")


def _unclosed_quotes(line: str) -> list[int]:
    """Vị trí (trong dòng) các dấu mở ngoặc kép không có dấu đóng trên cùng dòng."""
    unclosed: list[int] = []
    curly: list[int] = []
    straight: int | None = None
    for i, ch in enumerate(line):
        if ch == "“":
            curly.append(i)
        elif ch == "”" and curly:
            curly.pop()
        elif ch == '"':
            straight = i if straight is None else None
    unclosed.extend(curly)
    if straight is not None:
        unclosed.append(straight)
    return sorted(unclosed)


def _quote_wraps_whole(body: str) -> bool:
    """Dấu ngoặc mở ở đầu đoạn được đóng đúng ở ký tự cuối đoạn (một câu trích trọn đoạn)."""
    if body[0] == '"':
        return body.find('"', 1) == len(body) - 1
    depth = 0
    for i, ch in enumerate(body):
        if ch == "“":
            depth += 1
        elif ch == "”":
            depth -= 1
            if depth == 0:
                return i == len(body) - 1
    return False


def check_dialogue(text: str, quality: QualityConfig) -> list[QualityIssue]:
    """Kiểu dash (D-18): dòng thoại mở đầu bằng "— ". Ngoặc kép giữa đoạn là hợp lệ.

    Ngoại lệ (D-18): đoạn được ngoặc kép bao trọn, ngay sau đoạn kết thúc bằng ":", là trích
    nguyên văn (thư, chữ khắc). Hệ quả đã biết: lời thoại sai kiểu đứng trọn đoạn sau ":" bị lọt.
    """
    if quality.dialogue_style != "dash":
        raise ValueError(f"dialogue_style={quality.dialogue_style} chưa hỗ trợ (D-18)")
    text = _nfc(text)
    issues = []
    previous = ""
    for m in re.finditer(r"[^\n]+", text):
        line = m.group()
        body = line.strip()
        if not body:
            continue
        after_colon, previous = previous.endswith(":"), body
        start = m.start() + (len(line) - len(line.lstrip()))
        end = start + len(body)
        if _ONLY_DASHES.fullmatch(body):
            issues.append(_issue(text, IssueKind.DIALOGUE_FORMAT, start, end,
                                 "dòng chỉ có dấu gạch, không có lời thoại"))
        elif body[0] in _WRONG_DASHES:
            issues.append(_issue(text, IssueKind.DIALOGUE_FORMAT, start, end,
                                 f'mở đầu lời thoại bằng "{_EM_DASH} " (U+2014), '
                                 f'không dùng "{body[0]}"'))
        elif body[0] in "“\"" and not (after_colon and _quote_wraps_whole(body)):
            issues.append(_issue(text, IssueKind.DIALOGUE_FORMAT, start, end,
                                 f'lời thoại mở đầu bằng "{_EM_DASH} ", không dùng ngoặc kép'))
        for pos in _unclosed_quotes(line):
            issues.append(_issue(text, IssueKind.UNCLOSED_QUOTE, m.start() + pos, m.end(),
                                 "ngoặc kép mở nhưng không đóng trong cùng đoạn"))
    return issues


# --- gộp ----------------------------------------------------------------------------------


def check_scene(
    text: str,
    *,
    scenes_in_chapter: int,
    quality: QualityConfig,
    lengths: StoryLengthsConfig,
) -> list[QualityIssue]:
    """Chạy mọi bộ kiểm; trả danh sách lỗi xếp theo vị trí, để người canh gộp vào lượt viết lại."""
    issues = (
        check_length(text, scenes_in_chapter, lengths)
        + check_repetition(text, quality)
        + check_cliches(text, quality)
        + check_foreign_script(text, quality)
        + check_dialogue(text, quality)
    )
    return sorted(issues, key=lambda i: (i.start, i.end, i.kind))
