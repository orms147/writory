# Schema đồ thị

Mô hình ý tưởng: design §7.2. Code: `backend/src/writory/graph/` (danh sách nhãn và kiểu cạnh nằm trong `schema.py`). Truyện mẫu dựng tay theo schema này: `data/sample-story/graph.yaml`.

## Quy tắc
- **Mọi nút và cạnh** mang `story_id` và `commit_id` (G10, D-6). Mọi hàm trong `graph/` nhận `story_id` và từ chối giá trị rỗng.
- **Thời gian theo chương.** Cạnh mang `valid_from_chapter` và `valid_to_chapter` (không có = còn hiệu lực). "Ở chương N" = trạng thái **cuối** chương N: cạnh có hiệu lực khi `valid_from_chapter <= N` và (`valid_to_chapter` rỗng hoặc `> N`). `valid_from_chapter = 0` nghĩa là đã đúng từ trước khi truyện bắt đầu. Thứ tự là số chương, không dùng giờ máy.
- **Không xoá sự thật cũ; đóng nó lại.** Đổi trạng thái = đóng cạnh cũ (đặt `valid_to_chapter`) + tạo cạnh mới.
- **Nút không bị sửa sau khi tạo** (D-15). Mọi trạng thái đổi theo thời gian là cạnh: chết là `DIED_IN`, lời nói dối bị phát hiện là `KNOWS` tới nút `Lie`, mạch được gỡ là `RESOLVED_IN`.
- **Bất biến "tối đa một":** ở mỗi chương, một đồ vật có tối đa một cạnh `HOLDS` hiệu lực; mỗi cặp A→B có tối đa một `RELATES_TO` hiệu lực. Truy vấn gặp hơn một thì báo `GraphIntegrityError`, không chọn đại.
- **Hai lớp** trên cùng một đồ thị: `truth` là toàn bộ đồ thị; `player_view` định nghĩa ở mục riêng bên dưới, trong **một hàm duy nhất** (G1).
- **Nguồn gốc:** thuộc tính do người chơi viết mang `user_authored: true` (G4).
- **Định danh:** mỗi nút có `id` ổn định trong truyện; nhân vật có `name` và `aliases[]`. Gói thay đổi chỉ tham chiếu `id` đã có hoặc khai trong cùng gói (G11).
- **Nhánh:** sao chép đồ thị khi rẽ (D-5). Schema không có `branch_id`.

## Nút
Mọi nút có hai nhãn: `Entity` (nhãn chung, mang khoá) và một nhãn loại.

| Nhãn | Thuộc tính bắt buộc | Thuộc tính khác |
|---|---|---|
| `Character` | `name` | `aliases[]`, `is_protagonist` (đúng một nhân vật mỗi truyện) |
| `Location`, `Item`, `Faction` | `name` | `aliases[]` |
| `Event` | `chapter`, `description` | |
| `Fact` | `text` | |
| `Lie` | `chapter`, `content` | |
| `Thread` | `description`, `planted_chapter`, `due_from_chapter`, `due_to_chapter` | |
| `Chapter` | `number` | `title` |

Thuộc tính do lớp `graph/` tự đặt, đầu vào không được ghi: `story_id`, `id`, `commit_id`, `closed_by_commit`, `valid_from_chapter`, `valid_to_chapter`.

## Cạnh
Mọi cạnh có `story_id`, `id` (tự sinh `KIỂU:từ>tới@chương` nếu không khai), `commit_id`, `valid_from_chapter`, và có thể có `valid_to_chapter`, `closed_by_commit`.

| Kiểu | Từ → tới | Thuộc tính | Nghĩa |
|---|---|---|---|
| `RELATES_TO` | Character → Character | `kind`, `score` (−100…100) | B là gì của A; có hướng |
| `LOCATED_AT` | Character/Item → Location | | |
| `HOLDS` | Character → Item | | đang giữ |
| `MEMBER_OF` | Character → Faction | | |
| `PARTICIPATED_IN` | Character → Event | `role` | |
| `DIED_IN` | Character → Event | | chết trong sự kiện |
| `KNOWS` | Character → Fact/Lie/Event | `how`, `quote` | biết từ `valid_from_chapter`. Tới `Lie` = biết đó là lời dối |
| `FEELS` | nhân vật chính → bất kỳ | | từ lựa chọn nội tâm (chưa dùng ở tuần 1) |
| `TOLD` | Character → Lie | | người nói |
| `TOLD_TO` | Lie → Character | | người nghe |
| `ABOUT` | Fact/Event → bất kỳ | | mệnh đề/sự kiện nói về ai, cái gì |
| `RESOLVED_IN` | Thread → Chapter | | mạch được gỡ |
| `REVEALED_TO_PLAYER` | bất kỳ → Chapter | `quote` (bắt buộc, G3) | hé lộ trên trang ở chương đó |

Lời nói dối "đã bị phát hiện ở chương N" khi có nhân vật khác người nói `KNOWS` nút `Lie` từ chương ≤ N.

## `player_view`
Hàm `writory.graph.player_view(driver, story_id, chapter)` (D-16). Ở chương N, người chơi biết:
1. nút có `REVEALED_TO_PLAYER` tới chương ≤ N, kèm câu trích;
2. nút mà nhân vật chính `KNOWS` từ chương ≤ N;
3. lời nói dối do nhân vật chính nói (người chơi đã chọn nói), không kèm trạng thái bị phát hiện.

Chỉ trả trường trong danh sách trắng: id, loại, chữ hiện (`name`/`text`/`description`/`content`), biệt danh của nhân vật, chương biết, câu trích, và `about` (chỉ gồm id cũng nằm trong `player_view`). Không trả cạnh, quan hệ, vai trong sự kiện hay người giữ đồ vật. Nút `Thread` và `Chapter` không bao giờ vào `player_view`.

Câu trích của `REVEALED_TO_PLAYER` và của `KNOWS` từ nhân vật chính phải có nguyên văn trong chương (`quote_in_text`, chuẩn hoá NFC và khoảng trắng). Truyện mẫu được kiểm điều này trong `validate_sample`.

## Ghi theo `commit_id` (D-6, phần Neo4j)
- `apply_package(driver, story_id, ChangePackage)`: một transaction. Nút `MERGE` theo `(story_id, id)`; cạnh `MERGE` theo `(story_id, id)`; đóng cạnh ghi `closed_by_commit`. Áp lại cùng gói không đổi gì. Tham chiếu id không có → `MissingEntityError`; đụng nút/cạnh của commit khác → `CommitConflictError`; cả hai đều rollback toàn bộ.
- `delete_commit(driver, story_id, commit_id)`: xoá nút/cạnh commit đó tạo, mở lại cạnh nó đóng. Có commit sau dựa vào thì từ chối.
- Phần Postgres (trạng thái `pending`/`committed`/`failed`, chỉ đọc chương `committed`) chưa làm.

## Ràng buộc và index
Tạo bằng `ensure_schema(driver)` (chạy lại an toàn). Câu lệnh đầy đủ: `schema_statements()` trong `schema.py`.
- `entity_key`: `(n:Entity)` `REQUIRE (n.story_id, n.id) IS UNIQUE`.
- `entity_story`, `entity_commit`: index trên `Entity(story_id)` và `Entity(story_id, commit_id)`.
- `rel_<kiểu>_key`: mỗi kiểu cạnh `REQUIRE (r.story_id, r.id) IS UNIQUE` (Neo4j 5.26 Community có hỗ trợ).
- Neo4j Community không có ràng buộc NOT NULL, nên thuộc tính bắt buộc được kiểm bằng pydantic (`graph/package.py`) trước khi ghi.

## Truy vấn mẫu phải trả lời được
Câu hỏi design §7.3, mỗi câu một hàm trong `graph/queries.py` hoặc `graph/player_view.py`, nhận tham số chương:

| Câu hỏi | Hàm |
|---|---|
| Ai đang giữ thanh kiếm ở chương N? | `item_holder` |
| Minh có biết Lan là gián điệp không, từ chương nào, biết bằng cách nào? | `knows` |
| Người chơi đã được biết điều gì về Lan? | `player_knowledge_about` (lọc trên `player_view`) |
| Lời nói dối nào của nhân vật chính chưa bị phát hiện, đã nói với ai? | `undiscovered_lies` |
| Mạch nào đang mở và đã quá khoảng chương dự kiến gỡ? | `overdue_threads` |

Thêm: `relationship`, `is_alive`, `find_characters` (tên hoặc biệt danh, khớp nguyên cụm), `protagonist_id`.

Cypher mẫu (người giữ đồ vật ở chương N):
```cypher
MATCH (c:Entity:Character {story_id: $story_id})-[r:HOLDS]->
      (:Entity:Item {story_id: $story_id, id: $item_id})
WHERE r.valid_from_chapter <= $chapter
  AND (r.valid_to_chapter IS NULL OR r.valid_to_chapter > $chapter)
RETURN c.id, c.name
```

Đáp án viết tay cho từng câu trên truyện mẫu: `data/sample-story/answers.yaml`. Test: `cd backend && uv run pytest -m graph`.
