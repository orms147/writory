# Schema đồ thị

Mô hình ý tưởng: design §7.2. Code: `backend/src/writory/graph/` (danh sách nhãn và kiểu cạnh nằm trong `schema.py`). Truyện mẫu dựng tay theo schema này: `data/sample-story/graph.yaml`.

## Quy tắc
- **Mọi nút và cạnh** mang `story_id` và `commit_id` (G10, D-6). Mọi hàm trong `graph/` nhận `story_id` và từ chối giá trị rỗng.
- **Thời gian theo chương.** Cạnh mang `valid_from_chapter` và `valid_to_chapter` (không có = còn hiệu lực). "Ở chương N" = trạng thái **cuối** chương N: cạnh có hiệu lực khi `valid_from_chapter <= N` và (`valid_to_chapter` rỗng hoặc `> N`). `valid_from_chapter = 0` nghĩa là đã đúng từ trước khi truyện bắt đầu. Thứ tự là số chương, không dùng giờ máy.
- **Không xoá sự thật cũ; đóng nó lại.** Đổi trạng thái = đóng cạnh cũ (đặt `valid_to_chapter`) + tạo cạnh mới.
- **Nút không bị sửa sau khi tạo** (D-15). Mọi trạng thái đổi theo thời gian là cạnh: chết là `DIED_IN`, lời nói dối bị phát hiện là `KNOWS` tới nút `Lie`, mạch được gỡ là `RESOLVED_IN`.
- **Bất biến "tối đa một":** ở mỗi chương, một đồ vật có tối đa một cạnh `HOLDS` hiệu lực; mỗi cặp A→B có tối đa một `RELATES_TO` hiệu lực. Truy vấn gặp hơn một thì báo `GraphIntegrityError`, không chọn đại.
- **Một mệnh đề một nút.** Chữ của một `Fact` hay `Event` chỉ chứa đúng một mệnh đề. Chi tiết bí mật về nó (ai làm, vì sao) phải là `Fact` riêng, vì khi nút được hé lộ thì người chơi thấy toàn bộ chữ của nó. Ví dụ trong truyện mẫu: `e_gu_death` ("Lão Gù chết sau miếu Bà") tách khỏi `f_lan_killed_gu`.
- **Hai lớp** trên cùng một đồ thị: `truth` là toàn bộ đồ thị; `player_view` định nghĩa ở mục riêng bên dưới, trong **một hàm duy nhất** (G1).
- **Nguồn gốc:** thuộc tính do người chơi viết mang `user_authored: true` (G4).
- **Định danh:** mỗi nút có `id` ổn định trong truyện; nhân vật có `name` và `aliases[]`. Gói thay đổi chỉ tham chiếu `id` đã có hoặc khai trong cùng gói (G11).
- **Nhánh:** sao chép đồ thị khi rẽ (D-5). Schema không có `branch_id`.

## Nút
Mọi nút có hai nhãn: `Entity` (nhãn chung, mang khoá) và một nhãn loại.

| Nhãn | Thuộc tính bắt buộc | Thuộc tính khác |
|---|---|---|
| `Character` | `name` | `aliases[]`, `is_protagonist` (đúng một nhân vật mỗi truyện), `personality`, `backstory` |
| `Location`, `Item`, `Faction` | `name` | `aliases[]`, `description` |
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
| `KNOWS` | Character → Fact/Lie/Event | `how`, `told_by`, `quote`, `known_as`, `by_choice` | biết từ `valid_from_chapter`. Tới `Lie` = biết đó là lời dối. `how` thuộc `KNOWS_HOW`; `được kể` bắt buộc có `told_by` (D-22) |
| `FEELS` | nhân vật chính → bất kỳ | `feeling` | cảm xúc thầm từ lựa chọn nội tâm (D-55). Cảm xúc mới về cùng đích đóng cạnh cũ |
| `TOLD` | Character → Lie | | người nói |
| `TOLD_TO` | Lie → Character | | người nghe |
| `ABOUT` | Fact/Event/Lie → bất kỳ | | mệnh đề, sự kiện hay lời nói dối nói về ai, cái gì |
| `RESOLVED_IN` | Thread → Chapter | `quote` | mạch được gỡ. Bộ trích chỉ ghi khi có `quote` nguyên văn trong chương; với mạch phải gỡ chưa tới khoảng gỡ thì code bỏ cạnh (D-84): câu trả lời câu hỏi chính của mạch hay câu nói ra quyết định mạch đòi (`to_package`, D-82). Gói dựng tay (truyện mẫu) có thể không có `quote` |
| `REVEALED_TO_PLAYER` | bất kỳ → Chapter | `quote` (bắt buộc, G3), `known_as`, `by_choice` | hé lộ trên trang ở chương đó. `by_choice`: id lựa chọn dẫn tới lần lộ (D-22) |

**`known_as` (D-17).** Cạnh `REVEALED_TO_PLAYER` từ một nút có tên (Character/Location/Item/Faction), và cạnh `KNOWS` từ nhân vật chính tới một nút có tên, **bắt buộc** có `known_as`: tên người chơi biết lúc đó, phải nằm trong `quote` (cùng cách chuẩn hoá với `quote_in_text`). Một nút có thể được hé lộ nhiều lần với tên khác nhau, ví dụ biệt danh trước, tên thật sau. Thiếu `known_as` thì `apply_package` báo `InvalidPackageError`. `known_as` trùng tên hay biệt danh lớp truth của một nút khác (bỏ dấu, không phân biệt hoa thường) thì bộ trích bỏ cạnh, vì người chơi sẽ biết nút này dưới tên nút kia (`safety.reveal.known_as_conflicts`, D-62).

Lời nói dối "đã bị phát hiện ở chương N" khi có nhân vật khác người nói `KNOWS` nút `Lie` từ chương ≤ N.

## `player_view`
Hàm `writory.graph.player_view(driver, story_id, chapter)` (D-16). Định nghĩa nằm trong một hàm thuần, `build_player_view`. `player_view` gom bản ghi từ Neo4j; `guard.state.player_view_of` gom từ GraphState (nền đã commit + gói chưa ghi). Test so hai đường ở mọi chương của truyện mẫu. Ở chương N, người chơi biết:
1. nút có `REVEALED_TO_PLAYER` tới chương ≤ N, kèm câu trích;
2. nút mà nhân vật chính `KNOWS` từ chương ≤ N;
3. lời nói dối do nhân vật chính nói (người chơi đã chọn nói), không kèm trạng thái bị phát hiện. Người nghe hiện bằng chữ hiện của họ trong cùng view (`known_as`); chưa có trong view thì hiện "(người chưa rõ tên)", không bỏ lời nói dối (D-17).

Chỉ trả trường trong danh sách trắng: id, loại, chữ hiện, biệt danh, chương biết lần đầu, câu trích lần đầu, mọi câu trích (`quotes`, đều là chữ đã có trên trang; bộ dò lộ G2 dùng, giao diện chỉ cần câu đầu), và `about` (chỉ gồm id cũng nằm trong `player_view`).
- Nút có tên: chữ hiện là `known_as` của cạnh hé lộ mới nhất tới chương N; biệt danh là các `known_as` khác đã hé lộ tới chương N. **Không bao giờ** hiện `name` hay `aliases` của lớp sự thật (D-17). Nút có tên mà không có `known_as` nào thì không hiện.
- `Fact`/`Event`/`Lie`: chữ hiện là `text`/`description`/`content` của nút.
 Không trả cạnh, quan hệ, vai trong sự kiện hay người giữ đồ vật. Nút `Thread` và `Chapter` không bao giờ vào `player_view`.

**Mã công khai (D-40).** `id` của mục là id lớp truth và có thể lộ bí mật (mục "gã lái đò mặt sẹo" có id `ly_that`), nên chỉ dùng bên trong backend, ví dụ cho bộ dò lộ. Mọi đường ra cho người chơi (sổ tay API) và context của model phục vụ người chơi (hỏi người kể) dùng mã do `public_entries(view)` (`m1`, `m2`…) và `public_lies(view)` (`l1`…) gắn, xếp theo chương, loại, chữ hiện, không theo id.

Câu trích của `REVEALED_TO_PLAYER` và của `KNOWS` từ nhân vật chính phải có nguyên văn trong chương (`quote_in_text`, chuẩn hoá NFC và khoảng trắng). Truyện mẫu được kiểm điều này trong `validate_sample`.

## Ghi theo `commit_id` (D-6)
**Một chương = một gói.** Gói của chương N chỉ mở cạnh với `valid_from_chapter = N`, không đặt sẵn `valid_to_chapter`, và chỉ đóng cạnh ở chương N (`chapter_rule_problems`, D-21). Chương 0 là thế giới lúc khởi tạo (design §4.1): sự thật "đã đúng từ trước trang đầu" mở ở chương 0. Nhờ quy tắc này, đọc ở chương N−1 không thấy gì của chương N, kể cả khi chương N đã áp vào Neo4j mà còn `pending` trong Postgres.

**Luồng ghi** (`writory.db.commit_chapter`): kiểm quy tắc → Postgres ghi chương `pending` kèm gói (bảng `change_packages`, outbox) → `apply_package` → Postgres đặt `committed` và tăng `stories.committed_chapter`. Neo4j từ chối gói thì `delete_commit` rồi đặt `failed`; lý do lưu ở `chapters.error` sau khi qua `redact()`. Neo4j không trả lời hoặc tiến trình chết thì chương ở lại `pending`, và `reconcile_pending` áp lại sau. Truyện còn chương `pending` không ghi được chương mới.

**Đọc chỉ thấy chương đã commit.** Mọi truy vấn cho người chơi và cho pipeline lấy số chương từ `writory.db.current_chapter` (hàm duy nhất), không tự đoán chương mới nhất trong Neo4j. Đường người chơi: `writory.db.committed_player_view`.

Phần Neo4j:
- `apply_package(driver, story_id, ChangePackage)`: một transaction. Nút `MERGE` theo `(story_id, id)`; cạnh `MERGE` theo `(story_id, id)`; đóng cạnh ghi `closed_by_commit`. Áp lại cùng gói không đổi gì. Tham chiếu id không có → `MissingEntityError`; đụng nút/cạnh của commit khác → `CommitConflictError`; cả hai đều rollback toàn bộ.
- `delete_commit(driver, story_id, commit_id)`: xoá nút/cạnh commit đó tạo, mở lại cạnh nó đóng. Có commit sau dựa vào thì từ chối.

## Chương 0 (khởi tạo, D-38)
Gói chương 0 là thế giới trước trang đầu, do `writory.pipeline.setup.build_story` dựng cùng `story_plan`, rồi ghi như mọi chương (`commit_chapter(..., 0, ...)`). Code chuẩn hoá id rồi kiểm bằng `initial_problems`; sai thì model được `retries.setup_repair` lượt sửa kèm danh sách lỗi, vẫn sai một điều thì không trả gì (`STORY_SETUP_INVALID`, D-39, D-54).
- **Id:** đề yêu cầu dạng `SAFE_ID_PATTERN` (`pipeline/setup.py`: chữ ASCII thường không dấu, chữ số, `_`). Id không khớp `ID_PATTERN` thì code đổi (`normalize_id`: bỏ dấu, đ → d, chữ thường, khoảng trắng và ký tự lạ thành `_`, cắt còn `ID_MAX_LEN`), cùng một cách ở chỗ khai và mọi chỗ nhắc tới (cạnh, `about`, `known_by`, bí mật, mạch). Hai id khác nhau ra cùng một id, kể cả trùng `protagonist`, thì không gộp: đó là lỗi (D-54).
- **Nút:** chỉ `Character`, `Location`, `Item`, `Faction`, `Fact`, `Thread`, và đúng một `Chapter` là `ch0` (`number: 0`), đích của hé lộ nhân vật chính (D-74). Không có `Event`, `Lie`. Nút có tên phải có `name`, không trùng tên trong cùng nhãn.
- **Nhân vật chính:** đúng một, id `protagonist` (`PROTAGONIST_ID`), do code dựng từ chữ người chơi (tên, tính cách, quá khứ), mang `user_authored: true` (G4). Model chỉ nhắc tới nó qua id.
- **Cạnh:** `RELATES_TO` (bắt buộc `kind`, `score` −100…100), `LOCATED_AT` (mỗi thứ một nơi), `HOLDS` (mỗi đồ vật một người giữ), `MEMBER_OF`, `ABOUT`, `KNOWS`. Hai đầu đúng nhãn như bảng Cạnh, và đều là nút trong gói.
- **`KNOWS` ở chương 0** luôn có `how: "tự biết"`. **Nhân vật chính không `KNOWS` gì.** Model ghi `protagonist` vào `known_by` thì code bỏ cạnh đó sau khi chuẩn hoá id, trước mọi phép kiểm, không tính là lỗi (`drop_protagonist_knows`, D-76); `initial_problems` vẫn bắt `KNOWS` của nhân vật chính trong gói không đi qua bước đó. `REVEALED_TO_PLAYER` ở chương 0 chỉ có một cạnh, từ nhân vật chính tới `ch0` (D-74): người chơi đã chọn và có thể đã sửa nhân vật này, nên biết tên nó. `known_as` là tên đó, `quote` là dòng "Nhân vật chính: <tên>" của thiết lập truyện (`story_brief`, chữ người chơi đã thấy, nên G3 vẫn đúng). Mọi hé lộ khác ở chương 0 là lỗi; `player_view` ở chương 0 chỉ có mục nhân vật chính (code kiểm lại bằng `player_view_of`). Mục đó mang `is_protagonist`, để sổ tay cho model ghi nó là chính người chơi, và để API sổ tay cùng giao diện đánh dấu nó (D-76). Điều nhân vật chính biết từ quá khứ được ghi khi trang kể tới, kèm câu trích (G3).
- **Bí mật** trong `story_plan` trỏ tới `Fact` có trong gói; khoảng lộ nằm trong số chương của kế hoạch; mỗi bí mật có `leak_terms`, mỗi nhóm có ít nhất `LEAK_GROUP_MIN_PHRASES` cụm (D-26). `protects`: id các nút có tên (Character/Location/Item/Faction có trong gói, không phải nhân vật chính) mà bí mật giấu danh tính; tên và biệt danh lớp truth của chúng bị bộ dò lộ cấm khi bí mật còn hiệu lực; bí mật khác để rỗng, kế hoạch cũ không có trường này (D-61).
- **Mạch** của kế hoạch là nút `Thread` có `planted_chapter: 0`, khoảng gỡ nằm trong số chương; `must_resolve_threads` trỏ tới các nút đó, kèm khoảng phải gỡ bằng đúng khoảng dự kiến gỡ của nút (D-49). Kế hoạch cũ chỉ có id; khi đó khoảng lấy trên nút.
- **Hồi** phủ liền từ chương 1; chương cuối nằm trong khoảng `chapters` của mức độ dài (`config/story_lengths.yaml`).
- **Mốc và nhịp** (D-49): số mốc trong khoảng `milestones` của mức độ dài, mỗi hồi có mốc, mốc kết ở chương cuối; mỗi chương, trừ chương cuối, không quá `max_due_per_chapter` việc đến hạn (chương kết gỡ nhiều mạch cùng lúc, D-54). Luật luôn đúng nằm trong validator của `StoryPlan`, luật theo mức độ dài trong `initial_problems`.

## Chương 1 trở đi (pipeline, D-36)
Gói chương N do `writory.pipeline.chapter` dựng rồi ghi bằng `commit_chapter`:
- **Nút:** chỉ nút `Chapter` id `ch<N>` (`number: N`), đích của `REVEALED_TO_PLAYER` và `RESOLVED_IN`. Id này phải chưa có trong truyện; pipeline kiểm và dừng nếu đã có. Chưa có nút mới nào khác, vì bộ trích chỉ tham chiếu id có sẵn (D-34).
- **Cạnh:** của bộ trích, từng cảnh một, cộng cạnh tự hé lộ, đã qua người canh. Cạnh người canh báo sai không vào gói, kèm `close` của cạnh cũ mà nó thay (cùng chỗ), nếu không cạnh cũ biến mất mà không có cạnh mới (D-92). `KNOWS` "được kể" mà người kể là nhân vật chưa `KNOWS` tới đích và điều kể nói về chính họ (có `ABOUT` tới họ, hay họ tham gia sự kiện đó) thì code thêm `KNOWS` người kể, `how` "tự biết": tự thú trên trang thì trang chứng minh họ biết. Người thứ ba kể bí mật của người khác thì người canh vẫn bắt `teller_does_not_know` (D-92). Gộp các cảnh theo trạng thái cuối chương: cùng id thì lấy cảnh sau; cạnh cảnh trước mở mà cảnh sau đóng thì không vào gói.
- **Tự hé lộ (D-62):** sau bước trích, code thêm `REVEALED_TO_PLAYER` (tới `ch<N>`, `valid_from_chapter: N`) cho nút có tên mà tên hay biệt danh lớp truth có nguyên văn trong chữ cảnh, chưa có trong `player_view` (kể cả hé lộ bộ trích vừa ghi), không phải nhân vật chính, không nằm trong `protects` của bí mật còn hiệu lực. `quote` là câu chứa tên, `known_as` là chuỗi khớp trên trang. So khớp nghiêm (giữ dấu, trọn từ, chỉ chữ cái đầu tên nhiều từ được lệch hoa thường, tên phải có từ viết hoa); bỏ lần khớp nằm trong tên dài hơn của nút khác và chuỗi cũng là tên của nút khác (`safety/reveal.py`).

## Tác động của lựa chọn (D-55)
Người chơi chọn ở cuối chương N; tác động nằm trong gói của chương N+1 (mọi cạnh mở ở N+1, D-21), do `writory.pipeline.choices.choice_effects` dựng:
- **Nói dối:** nút `Lie` (id `lie:<choice_id>`, `chapter` = N+1, `content`), `TOLD` từ nhân vật chính, `TOLD_TO` tới từng người nghe còn sống (không gồm chính nhân vật chính), `ABOUT` tới các mục nó nói tới. Không ai nghe được thì không ghi. Hiện trong `player_view.lies` từ chương N+1.
- **Nội tâm:** `FEELS` từ nhân vật chính tới từng mục, mang `feeling`; `FEELS` cũ cùng đích bị đóng ở chương N+1. Chưa vào `player_view` (D-16).
- **Nói thật, im lặng, hành động:** không ghi gì; chỉ chữ của lựa chọn vào đề chương sau.
Người canh, bộ trích và lớp phủ `OverlayState` thấy các cạnh này từ cảnh 1 của chương N+1.

## Ngữ cảnh cho model viết (D-28)
`writory.graph.context.writer_context(driver, story_id, as_of_chapter, present_ids, plan, max_neighbors=...)` đọc lớp `truth` ở cuối chương `as_of_chapter` (chương đã commit, lấy từ `writory.db.current_chapter`) để viết chương kế tiếp. Ngữ cảnh gồm:
- nhân vật có mặt: còn sống, nơi đang ở, đồ vật đang giữ;
- quan hệ hiện tại giữa người có mặt (cả hai chiều);
- `Fact` mà người có mặt biết, kèm danh sách mọi người biết;
- lời nói dối chưa bị phát hiện, mà người nói hoặc người nghe đang có mặt;
- bí mật trong `story_plan`, kèm trạng thái `not_yet` / `in_window` / `overdue` / `revealed` so với chương đang viết;
- nút cách người có mặt 1–2 bước, theo cạnh còn hiệu lực. Không đi qua `REVEALED_TO_PLAYER` hay nút `Chapter`, không lặp lại nút đã nằm ở các mục trên, và giới hạn số nút bằng `limits.context.writer_max_neighbors`;
- mạch đang mở, kèm cờ quá hạn.

`render_writer_context` trả các phần để đưa vào `user_message`, chia hai mục: "Sự thật cần tôn trọng" (gồm cả người liên quan đã chết) và "Gợi ý có thể nhắc tới". Mọi chữ lấy từ một nút mang `user_authored: true` đều được bọc bằng `UserAuthored` (G4), ở bất kỳ vị trí nào: tên, biệt danh, nơi ở, đồ vật, người biết, người nói, người nghe, bí mật, mạch. Mỗi vị trí có test hồi quy. Ngữ cảnh này chứa bí mật, nên không bao giờ được đi ra đường của người chơi.

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

Thêm: `relationship`, `is_alive`, `find_characters` (tên hoặc biệt danh, khớp nguyên cụm), `protagonist_id`. Cho người canh: `edges_at` (cạnh một kiểu còn hiệu lực ở chương N, kèm id) và `node_labels`. Cho bộ dò lộ (G2): `named_nodes` (tên và biệt danh lớp truth; không bao giờ trả cho người chơi). Bộ dò lộ đọc qua `safety.leak.leak_names`, bỏ `name` của nút `user_authored` (D-48). Cho bộ trích của pipeline (D-36): `story_nodes` (mọi nút của truyện, kể cả nút chưa có cạnh, làm danh mục thực thể; lớp truth).

Cypher mẫu (người giữ đồ vật ở chương N):
```cypher
MATCH (c:Entity:Character {story_id: $story_id})-[r:HOLDS]->
      (:Entity:Item {story_id: $story_id, id: $item_id})
WHERE r.valid_from_chapter <= $chapter
  AND (r.valid_to_chapter IS NULL OR r.valid_to_chapter > $chapter)
RETURN c.id, c.name
```

Truyện mẫu có chương 0 (gói khởi tạo, không có văn bản) và chương 1–5. Đáp án viết tay cho từng câu trên truyện mẫu: `data/sample-story/answers.yaml`. Test: `cd backend && uv run pytest -m graph`.

## Chưa làm
- **Lời người chơi đã nghe.** Người chơi đã nghe lời nói dối của nhân vật khác (ví dụ `l_lan_cover`, `TOLD_TO` nhân vật chính), nhưng `player_view` chưa có gì về chuyện đó. Vì vậy sổ tay thiếu "Lan kể rằng cô trốn hôn nhân". Cần hiện dưới dạng **lời kể** ("Lan kể: …") và **không** được gắn nhãn `Lie`, vì gắn nhãn là lộ. Làm cùng sổ tay ở tuần 5, kèm test G1.
- `player_view` chưa có quan hệ và người giữ đồ vật cho sổ tay (D-16).
- G3 ở `apply_package` chỉ kiểm có `quote` và `known_as` nằm trong `quote`. Đối chiếu câu trích với văn bản nằm ở `validate_sample` (truyện mẫu) và ở bộ trích (`to_package` gọi `quote_in_text` trên đúng chữ cảnh sẽ hiện, D-36; với `RESOLVED_IN` thì bắt buộc có câu trích, D-82); gói do nơi khác dựng thì chưa được đối chiếu. `apply_package` chưa đòi `quote` ở `RESOLVED_IN`.
- **Tự reconcile lúc khởi động app.** Hiện `reconcile_pending` chỉ chạy tay (lệnh trong `docs/runbook.md`). App FastAPI đã có nhưng chưa gọi nó lúc khởi động (TODO ở `backend/src/writory/api/app.py:81`); cần nối để truyện không kẹt `pending` sau khi máy chủ chết giữa chừng.
- **`writer_context` chạy trên `GraphState`.** Hiện chỉ đọc từ Neo4j ở chương đã commit. Pipeline (D-36) bù bằng cách đưa thêm văn và thay đổi đã trích của các cảnh trước vào đề, nhưng các mục của ngữ cảnh (người có mặt đang ở đâu, giữ gì, biết gì) chưa tính các gói chưa ghi đó.
