"""Tủ truyện của một người chơi: mỗi truyện một dòng cho `GET /stories` (D-66).

Chỉ đọc những gì người chơi đã thấy, cộng số chương của kế hoạch để biết truyện đã kết:
- tên truyện: tên hướng truyện đã chọn ở phiên khởi tạo (không có thì tên bối cảnh đã chọn); truyện
  không tạo qua phiên khởi tạo thì không có tên;
- cảnh cuối: cảnh cuối của chương đã commit cuối (D-6), đúng chữ đã hiện; chương `pending` hay
  `failed` không bao giờ được đọc;
- bản kế hoạch ẩn chỉ cho ra `total_chapters` (một số), không có chữ nào của nó rời khỏi hàm này.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg

from writory.pipeline.story_plan import StoryPlan


@dataclass(frozen=True)
class StorySummaryRecord:
    id: str
    length_level: str
    committed_chapter: int | None
    updated_at: datetime  # stories.updated_at: lúc tạo truyện hoặc lúc commit chương cuối
    title: str | None
    total_chapters: int | None  # theo kế hoạch ẩn; None khi truyện không có kế hoạch
    last_scene: str | None  # cảnh cuối của chương đã commit cuối; None ở chương 0


_SELECT = """
SELECT s.id, s.length_level, s.committed_chapter, s.updated_at,
       COALESCE((ss.plots -> ss.plot_index) ->> 'title',
                (ss.settings -> ss.setting_index) ->> 'title'),
       p.plan,
       c.scenes ->> -1
FROM stories s
LEFT JOIN setup_sessions ss ON ss.story_id = s.id AND ss.owner_id = s.owner_id
LEFT JOIN story_plans p ON p.story_id = s.id
LEFT JOIN chapters c ON c.story_id = s.id AND c.number = s.committed_chapter
                    AND c.number >= 1 AND c.status = 'committed'
WHERE s.owner_id = %s
ORDER BY s.updated_at DESC, s.id
"""


def owned_story_summaries(conn: psycopg.Connection, owner_id: str) -> list[StorySummaryRecord]:
    """Truyện của `owner_id`, mới nhất trước (G10: chỉ của người này)."""
    out = []
    for sid, level, chapter, updated, title, plan, last_scene in conn.execute(
            _SELECT, (owner_id,)).fetchall():
        total = None if plan is None else StoryPlan.model_validate(plan).total_chapters
        out.append(StorySummaryRecord(sid, level, chapter, updated, title, total, last_scene))
    return out
