"""Kiểm chất lượng văn bằng code (design §6.5 mục 5). Không gọi model.

Mọi hàm chuẩn hoá NFC trước khi kiểm; vị trí `start`/`end` tính trên chuỗi đã chuẩn hoá NFC.
Ngưỡng và danh sách lấy từ config/quality.yaml (D-19); độ dài từ config/story_lengths.yaml.
Regex ở đây chỉ kiểm định dạng chữ, không đọc ý định người dùng (G5).
"""

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
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
    META_LEAK = "meta_leak"
    NARRATION_PERSON = "narration_person"
    DIALOGUE_UNATTRIBUTED = "dialogue_unattributed"  # truyện audio: thoại liền nhau không rõ ai nói (D-156)


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


def _name_spans(text: str, names: Iterable[str]) -> list[tuple[int, int, str]]:
    """Chỗ các tên xuất hiện trong `text` (đã NFC): trọn từ, không phân biệt hoa thường. Tên dài
    được chọn trước; các chỗ không chồng lên nhau."""
    keys = sorted({" ".join(w.casefold() for w in _WORD.findall(_nfc(n))) for n in names} - {""},
                  key=lambda k: -len(k.split()))
    taken: list[tuple[int, int, str]] = []
    for key in keys:
        pattern = re.compile(r"(?<!\w)" + r"\W+".join(map(re.escape, key.split())) + r"(?!\w)",
                             re.IGNORECASE)  # \W+: "Sổ Trận Cô Phong", cả "Hạ-Trần"
        for m in pattern.finditer(text):
            if all(m.end() <= s or m.start() >= e for s, e, _ in taken):
                taken.append((m.start(), m.end(), key))
    return sorted(taken)


def _tokens(text: str, names: Iterable[str]) -> list[tuple[str, int, int]]:
    """Từ của `text` (đã NFC), chữ thường. Mỗi chỗ tên xuất hiện gộp thành MỘT từ (D-51): tên hay
    biệt danh của thực thể nhắc lại nhiều lần không phải cụm lặp, nhưng câu lặp quanh tên vẫn là."""
    spans = _name_spans(text, names)
    out: list[tuple[str, int, int]] = []
    i = 0
    for m in _WORD.finditer(text):
        while i < len(spans) and spans[i][1] <= m.start():
            i += 1
        if i < len(spans) and spans[i][0] <= m.start() < spans[i][1]:
            start, end, key = spans[i]
            if not out or out[-1][1] != start:
                out.append((f"<{key}>", start, end))
            continue
        out.append((m.group().casefold(), m.start(), m.end()))
    return out


def check_repetition(
    text: str, quality: QualityConfig, *, names: Iterable[str] = ()
) -> list[QualityIssue]:
    """Cụm `ngram_words` từ xuất hiện quá `max_repeats` lần. Báo ở các lần vượt; các lần vượt
    chồng lên nhau (một câu dài bị lặp) gộp thành một lỗi.

    `names`: tên và biệt danh của thực thể người chơi đã biết hay đang có trong ngữ cảnh. Mỗi chỗ
    tên xuất hiện tính là một từ, nên nhắc tên nhiều lần không bị coi là lặp (D-51)."""
    n = _require(quality.repetition, "ngram_words")
    max_repeats = _require(quality.repetition, "max_repeats")
    text = _nfc(text)
    words = _tokens(text, names)
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

_DIALOGUE_DASH = "-"  # D-31: dấu thoại là gạch ngang thường
_LONG_DASHES = re.compile("[—–]")  # em dash, en dash: backend đổi hết thành "-"
_LINE_START_DASH = re.compile(r"(?m)^([ \t]*)-[ \t]*(?=\S)")
_ONLY_DASHES = re.compile(r"[—–\-−\s]+")


def normalize_dashes(text: str) -> str:
    """D-31: thay mọi em/en dash bằng "-", và dòng thoại thành "- " (gạch ngang + một khoảng trắng).
    Gạch nối trong từ ghép hay khoảng số giữ nguyên dạng "-". Chạy lại không đổi gì."""
    text = _LONG_DASHES.sub(_DIALOGUE_DASH, text)
    return _LINE_START_DASH.sub(rf"\1{_DIALOGUE_DASH} ", text)


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
    """Kiểu dash (D-18): dòng thoại mở đầu bằng "- " (D-31). Ngoặc kép giữa đoạn là hợp lệ.

    Văn bản được chuẩn hoá dấu gạch trước (`normalize_dashes`), nên dòng mở bằng em/en dash hay
    gạch nối không cách đều hợp lệ; vị trí lỗi tính trên văn bản đã chuẩn hoá.
    Ngoại lệ (D-18): đoạn được ngoặc kép bao trọn, ngay sau đoạn kết thúc bằng ":", là trích
    nguyên văn (thư, chữ khắc). Hệ quả đã biết: lời thoại sai kiểu đứng trọn đoạn sau ":" bị lọt.
    """
    if quality.dialogue_style != "dash":
        raise ValueError(f"dialogue_style={quality.dialogue_style} chưa hỗ trợ (D-18)")
    text = normalize_dashes(_nfc(text))
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
        elif body[0] in "“\"" and not (after_colon and _quote_wraps_whole(body)):
            issues.append(_issue(text, IssueKind.DIALOGUE_FORMAT, start, end,
                                 f'lời thoại mở đầu bằng "{_DIALOGUE_DASH} ", không dùng ngoặc kép'))
        for pos in _unclosed_quotes(line):
            issues.append(_issue(text, IssueKind.UNCLOSED_QUOTE, m.start() + pos, m.end(),
                                 "ngoặc kép mở nhưng không đóng trong cùng đoạn"))
    return issues


def check_dialogue_attribution(text: str, max_run: int) -> list[QualityIssue]:
    """Truyện audio (D-156): giọng đọc máy một giọng không cho người nghe biết ai nói, nên quá `max_run` dòng thoại
    ("- ...") liền nhau, không có dòng kể nào xen giữa, là một lỗi cho mỗi chuỗi như vậy. Dòng trống không cắt chuỗi.
    Chỉ bước soát cảnh của truyện audio gọi; truyện chữ không kiểm."""
    text = normalize_dashes(_nfc(text))
    issues: list[QualityIssue] = []
    run: list[re.Match[str]] = []

    def close() -> None:
        if len(run) > max_run:
            start = run[0].start() + (len(run[0].group()) - len(run[0].group().lstrip()))
            issues.append(_issue(text, IssueKind.DIALOGUE_UNATTRIBUTED, start, run[-1].end(),
                                 f"{len(run)} lượt thoại liền nhau không có câu dẫn ai nói (tối đa {max_run})"))
        run.clear()

    for m in re.finditer(r"[^\n]+", text):
        body = m.group().strip()
        if not body:
            continue
        if body.startswith(_DIALOGUE_DASH + " "):
            run.append(m)
        else:
            close()
    close()
    return issues


# --- lọt suy luận / chữ của prompt ----------------------------------------------------------

# Thẻ suy luận, kể cả thẻ có hậu tố ("</think_36a8…>") hay bị cắt mất ">".
_REASONING_TAG = re.compile(r"</?(?:thinking|reasoning|think)\w*(?:[^<>\n]{0,200}>)?",
                            re.IGNORECASE)
# Cụm chỉ có trong đề bài và hướng dẫn văn phong, gần như không gặp trong văn truyện (D-30).
# Cố ý hẹp: "dàn ý" hay "lộ bí mật" đứng riêng vẫn có thể là văn truyện.
_META_PHRASES = (
    "theo dàn ý",
    "không lộ bí mật",
    "ngôi thứ ba",
    "ngôi thứ nhất",
    "bảng xưng hô",
    "người viết được biết",
)


def check_meta_leak(text: str) -> list[QualityIssue]:
    """Thẻ suy luận hoặc chữ của prompt (đề bài, hướng dẫn văn phong) lọt vào văn bản cảnh.
    Ghi chú kế hoạch của model có thể nhắc tới bí mật, nên lỗi này liên quan G2. Không cần config."""
    text = _nfc(text)
    issues = [
        _issue(text, IssueKind.META_LEAK, m.start(), m.end(), "thẻ suy luận lọt vào văn bản")
        for m in _REASONING_TAG.finditer(text)
    ]
    for phrase in _META_PHRASES:
        pattern = re.compile(
            r"(?<!\w)" + r"\s+".join(map(re.escape, phrase.split())) + r"(?!\w)", re.IGNORECASE
        )
        issues += [
            _issue(text, IssueKind.META_LEAK, m.start(), m.end(),
                   f'cụm của prompt lọt vào văn bản: "{phrase}"')
            for m in pattern.finditer(text)
        ]
    return sorted(issues, key=lambda i: (i.start, i.end))


# --- ngôi kể --------------------------------------------------------------------------------
# D-51. Lời kể = mọi dòng không phải dòng thoại "- " (D-31), bỏ chữ trong ngoặc kép (thư, chữ
# khắc, lời trích). Đo bằng số lần "tôi" trên 100 từ lời kể: đây là đếm đại từ trong văn, không
# phải đọc ý định người dùng (G5). Đề của model viết lấy câu ngôi kể từ `narration_instruction`,
# cùng một nguồn `quality.narration.person` với phép kiểm.

_FIRST_PERSON = frozenset({"tôi"})  # style guide: người kể ngôi thứ nhất xưng "tôi"
_QUOTED = re.compile(r"“[^”\n]*”|\"[^\"\n]*\"")

NARRATION_INSTRUCTIONS = {
    "first": 'Ngôi kể: ngôi thứ nhất. Người kể là nhân vật chính, xưng "tôi" trong lời kể ở mọi '
             'cảnh, mọi chương. Lời kể không gọi nhân vật chính bằng tên hay bằng "chàng", "nàng", '
             '"hắn", "anh", "cô"; tên nhân vật chính chỉ có khi người khác gọi trong lời thoại.',
    "third": 'Ngôi kể: ngôi thứ ba, bám sát nhân vật chính. Lời kể gọi nhân vật chính bằng tên '
             'hoặc đại từ ngôi thứ ba, không xưng "tôi"; "tôi" chỉ có trong lời thoại.',
}


def narration_instruction(quality: QualityConfig) -> str:
    """Câu ngôi kể cho đề của model viết, đúng ngôi mà `check_narration` đòi."""
    return NARRATION_INSTRUCTIONS[quality.narration.person]


def _narration_words(text: str) -> list[str]:
    words: list[str] = []
    for line in normalize_dashes(text).split("\n"):
        body = line.strip()
        if not body or body.startswith(_DIALOGUE_DASH):
            continue
        words += [w.casefold() for w in _WORD.findall(_QUOTED.sub(" ", body))]
    return words


def check_narration(text: str, quality: QualityConfig) -> list[QualityIssue]:
    """Lời kể lệch ngôi đã chốt (`quality.narration.person`). Một lỗi cho cả cảnh, mức viết lại.
    Lời kể ngắn hơn `min_words` từ thì không kết luận."""
    cfg = quality.narration
    min_words = _require(cfg, "min_words")
    text = _nfc(text)
    words = _narration_words(text)
    if len(words) < min_words:
        return []
    count = sum(w in _FIRST_PERSON for w in words)
    rate = 100 * count / len(words)
    measured = f'cảnh có {count} lần "tôi" trên {len(words)} từ lời kể ({rate:.1f} trên 100 từ'
    if cfg.person == "first":
        limit = _require(cfg, "first_person_min_per_100_words")
        if rate >= limit:
            return []
        detail = (f'lời kể phải do nhân vật chính kể, xưng "tôi"; {measured}, cần từ {limit}), '
                  'như đang kể về nhân vật chính từ bên ngoài. Viết lại lời kể xưng "tôi", '
                  'giữ nguyên lời thoại')
    else:
        limit = _require(cfg, "first_person_max_per_100_words")
        if rate <= limit:
            return []
        detail = (f'lời kể không được xưng "tôi", truyện kể về nhân vật chính từ bên ngoài; '
                  f'{measured}, tối đa {limit}). Viết lại lời kể không xưng "tôi", giữ nguyên '
                  'lời thoại')
    return [_issue(text, IssueKind.NARRATION_PERSON, 0, len(text), detail)]


# --- gộp ----------------------------------------------------------------------------------


def check_scene(
    text: str,
    *,
    scenes_in_chapter: int,
    quality: QualityConfig,
    lengths: StoryLengthsConfig,
    names: Iterable[str] = (),
) -> list[QualityIssue]:
    """Chạy mọi bộ kiểm; trả danh sách lỗi xếp theo vị trí, để người canh gộp vào lượt viết lại.
    Văn bản được chuẩn hoá NFC và dấu gạch (D-31) một lần ở đây, nên mọi vị trí lỗi cùng tính trên
    văn bản đã chuẩn hoá: đó cũng là chữ người chơi sẽ thấy. `names`: tên thực thể cho bộ kiểm lặp
    (`check_repetition`)."""
    text = normalize_dashes(_nfc(text))
    issues = (
        check_length(text, scenes_in_chapter, lengths)
        + check_repetition(text, quality, names=names)
        + check_cliches(text, quality)
        + check_foreign_script(text, quality)
        + check_dialogue(text, quality)
        + check_narration(text, quality)
    )
    return sorted(issues, key=lambda i: (i.start, i.end, i.kind))
