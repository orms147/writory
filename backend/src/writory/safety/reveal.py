"""Tự hé lộ nút có tên mà trang vừa nêu, và kiểm tên người chơi thấy có đúng nút không (D-62).

Bộ dò lộ (`leak.py`, D-61) chỉ cấm tên bí mật: tên thật bị giấu sau biệt danh và tên được kế hoạch
bảo vệ. Tên khác của lớp truth được phép xuất hiện trên trang; để sổ tay và bộ dò biết người chơi
đã thấy nó, sau bước trích của mỗi cảnh code thêm cạnh `REVEALED_TO_PLAYER` cho nút có tên mà tên
hay biệt danh xuất hiện nguyên văn trong chữ cảnh, chưa có trong player_view và bộ trích chưa hé lộ:
- `quote` là câu chứa tên, nguyên văn (G3); `known_as` đúng chuỗi đã khớp (D-17);
- `valid_from_chapter` là chương đang viết (D-21);
- không đụng nhân vật chính và nút có tên bị bảo vệ (`skip`), nút không có tên (Thread, Fact...:
  `names` chỉ có nút có tên).

Nút đã hé lộ chỉ được thêm TÊN CHÍNH lớp truth (`name`) mà người chơi chưa biết: biệt danh trước, tên
thật sau (D-17, D-136). Luật chung với bộ trích, `new_name_problem`: không nhận tên người chơi đã biết,
biệt danh hay chức danh (sổ tay sẽ đổi tên hiện theo từng cách gọi), nút trong `no_new_name` (tên đang
được bảo vệ ở đường người chơi, hay nút đã hé lộ ở chính chương này).

So khớp nghiêm hơn bộ dò lộ, vì khớp nhầm ở đây là hé lộ nhầm một nút: giữ dấu, phân biệt hoa
thường, theo ranh giới từ. Chỉ chữ cái đầu của tên nhiều từ được lệch hoa thường ("Kho kiếm cụ" khớp
"kho kiếm cụ"), vì tên đứng đầu câu thì viết hoa. Tên một từ phải viết hoa và khớp đúng ("Lan" không
khớp "hoa lan"). Tên phải có ít nhất một từ viết hoa. Nhờ vậy "Động Linh Mạch" không khớp "chấn động
linh mạch". Thêm hai luật để không gán tên cho nhầm nút:
- chuỗi khớp trùng tên hay biệt danh của nút khác (mơ hồ) thì bỏ (`known_as_conflicts`);
- lần khớp nằm gọn trong lần khớp dài hơn của nút khác thì bỏ ("Minh" trong "Phó Minh Nghi").
Mỗi nút một cạnh: ưu tiên khớp `name`, rồi chuỗi dài nhất, rồi chuỗi đứng trước.
"""

import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from writory.graph import EdgeSpec, PlayerView
from writory.safety.leak import name_key

_SENTENCE = re.compile(r"[^.!?…\n]+")
_QUOTE_MAX_CHARS = 200
_QUOTE_CONTEXT_CHARS = 90


def known_as_conflicts(
    known_as: str, node_id: str, names: Mapping[str, Sequence[str]]
) -> list[str]:
    """Id các nút KHÁC `node_id` có tên hay biệt danh lớp truth trùng `known_as` (cùng cách chuẩn
    hoá của bộ dò lộ: bỏ dấu, không phân biệt hoa thường). Khác rỗng: người chơi sẽ biết nút này
    dưới tên của nút kia (hồi quy tu-tien-1 chương 5: "Vạn Tinh Bách" gắn lên `doan_khac`)."""
    key = name_key(known_as)
    return sorted(
        other for other, forms in names.items()
        if other != node_id and any(name_key(f) == key for f in forms)
    )


def new_name_problem(
    known_as: str, node_id: str, *, names: Mapping[str, Sequence[str]], shown: Collection[str],
    locked: Collection[str],
) -> str | None:
    """Lý do không nhận `known_as` làm tên mới cho một nút ĐÃ có trong player_view (D-136); None là
    nhận. `names`: id → (name, *aliases) lớp truth. `shown`: các tên người chơi đang biết của nút.
    `locked`: nút có tên đang được kế hoạch bảo vệ ở đường người chơi (bí mật chưa có trong
    player_view, D-61): tên mới sẽ nối hai tên trong sổ tay, đúng điều bí mật giấu. So bằng
    `name_key` như bộ dò lộ. Chỉ tên chính: biệt danh hay chức danh làm tên hiện đổi theo từng cách gọi
    của trang (đếm trên các lượt đã lưu, D-136)."""
    key = name_key(known_as)
    if key in {name_key(s) for s in shown}:
        return "người chơi đã biết nút này dưới tên đó"
    forms = names.get(node_id) or ()
    if not forms or key != name_key(forms[0]):
        return "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)"
    if node_id in locked:
        return "tên mới của nút có tên đang được bảo vệ (D-61)"
    return None


def _has_proper_word(form: str) -> bool:
    return any(w[0].isupper() for w in form.split() if w[0].isalpha())


def _form_pattern(form: str) -> re.Pattern | None:
    words = unicodedata.normalize("NFC", form).split()
    if not words or not _has_proper_word(form):
        return None
    if len(words) == 1 and not words[0][0].isupper():
        return None
    first = words[0]
    if len(words) >= 2 and first[0].isalpha():
        head = f"[{re.escape(first[0].upper())}{re.escape(first[0].lower())}]" + re.escape(first[1:])
    else:
        head = re.escape(first)
    body = r"\s+".join([head, *(re.escape(w) for w in words[1:])])
    return re.compile(r"(?<!\w)" + body + r"(?!\w)")


def _quote_for(text: str, start: int, end: int) -> str:
    """Câu chứa [start, end), nguyên văn. Câu quá dài thì cắt quanh tên ở ranh giới từ."""
    lo, hi = start, end
    for m in _SENTENCE.finditer(text):
        if m.start() <= start < m.end():
            lo, hi = m.start(), max(m.end(), end)
            break
    if hi - lo > _QUOTE_MAX_CHARS:
        a = max(lo, start - _QUOTE_CONTEXT_CHARS)
        if a > lo:  # bắt đầu sau khoảng trắng đầu tiên, để không cắt giữa từ
            space = text.find(" ", a, start)
            a = space + 1 if space != -1 else start
        b = min(hi, end + _QUOTE_CONTEXT_CHARS)
        if b < hi:  # dừng ở khoảng trắng cuối cùng
            space = text.rfind(" ", end, b)
            b = space if space != -1 else end
        lo, hi = a, b
    return text[lo:hi].strip()


@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    node_id: str
    is_name: bool  # khớp `name` (phần tử đầu của `names[node_id]`), không phải biệt danh
    matched: str  # chuỗi trên trang, khoảng trắng gộp một

    def inside(self, other: "_Match") -> bool:
        return (other.node_id != self.node_id and other.start <= self.start
                and self.end <= other.end and other.end - other.start > self.end - self.start)

    def rank(self) -> tuple[bool, int, int]:
        return (not self.is_name, -(self.end - self.start), self.start)


def auto_reveals(
    text: str,
    *,
    chapter: int,
    chapter_id: str,
    names: Mapping[str, Sequence[str]],
    view: PlayerView,
    skip: Collection[str],
    no_new_name: Collection[str],
) -> list[EdgeSpec]:
    """Cạnh `REVEALED_TO_PLAYER` cho nút có tên mà chữ cảnh nêu (xem đầu file). `names`: id →
    (name, *aliases) lớp truth của MỌI nút có tên (`named_nodes`, không phải `leak_names`), để
    tìm được chuỗi mơ hồ và tên lồng nhau. `view`: player_view gồm cả các hé lộ bộ trích vừa ghi
    cho cảnh này. `skip`: nhân vật chính và nút có tên bị bảo vệ. `no_new_name`: nút đã hé lộ không
    được thêm tên (bắt buộc, không mặc định: nút đang được bảo vệ ở đường người chơi, và nút đã hé lộ
    ở chương này). Xếp theo vị trí trên trang."""
    text = unicodedata.normalize("NFC", text)
    matches: list[_Match] = []
    for node_id, forms in names.items():
        for i, form in enumerate(forms):
            pattern = _form_pattern(form)
            if pattern is None:
                continue
            matches += [_Match(m.start(), m.end(), node_id, i == 0, " ".join(m.group().split()))
                        for m in pattern.finditer(text)]
    shown = {e.id: (e.text, *e.aliases) for e in view.entries}
    best: dict[str, _Match] = {}
    for x in matches:
        if (x.node_id in skip or any(x.inside(y) for y in matches)
                or known_as_conflicts(x.matched, x.node_id, names)):
            continue
        if x.node_id in shown and new_name_problem(
                x.matched, x.node_id, names=names, shown=shown[x.node_id], locked=no_new_name):
            continue
        if x.node_id not in best or x.rank() < best[x.node_id].rank():
            best[x.node_id] = x
    return [
        EdgeSpec(type="REVEALED_TO_PLAYER", source=x.node_id, target=chapter_id,
                 valid_from_chapter=chapter,
                 props={"quote": _quote_for(text, x.start, x.end), "known_as": x.matched})
        for x in sorted(best.values(), key=lambda m: (m.start, m.node_id))
    ]
