# Quyết định

Mỗi mục ≤ 15 dòng: bối cảnh / quyết định / hệ quả / người quyết. Quyết định bị thay thì thêm mục mới ghi "thay thế D-n" và sửa trạng thái mục cũ thành **Đã thay**. Không xoá mục cũ.

Người quyết: **Chủ dự án** (người dùng đã nói rõ) hoặc **Claude** (đề xuất, chủ dự án đồng ý hướng chung).

---

## D-1 · Hiện chương theo từng cảnh đã kiểm
- **Bối cảnh:** bản thiết kế đầu vừa stream chữ, vừa cho người canh bắt viết lại sau khi viết xong, nên người chơi có thể đã đọc bản lỗi.
- **Quyết định:** chương chia 2–3 cảnh; mỗi cảnh viết → trích → canh → mới hiện. Cảnh sau viết trong lúc người chơi đọc cảnh trước. Ghi đồ thị một lần sau cảnh cuối.
- **Hệ quả:** chờ lâu hơn ở cảnh đầu; pipeline phải chạy nền song song với việc đọc. Lỗi lộ bí mật thì không hiện cảnh.
- **Người quyết:** Chủ dự án · 19/10/2026

## D-2 · Người chơi trả bằng key OpenRouter của họ
- **Bối cảnh:** cho người khác chơi thì phải có người trả tiền gọi model.
- **Quyết định:** BYOK. Chủ dự án chỉ trả máy chủ và bộ đo.
- **Hệ quả:** mã hoá key khi lưu, không log, không gửi về trình duyệt; vẫn cần trần chi phí và giới hạn tần suất; cần lớp chất lượng (D-3) vì người chơi trả tiền cho model.
- **Người quyết:** Chủ dự án · 19/10/2026

## D-3 · Lớp chất lượng: danh sách model đã thử, tách vai
- **Bối cảnh:** với BYOK, chất lượng truyện phụ thuộc model người chơi chọn.
- **Quyết định:** người chơi chọn mức trong danh sách đã qua bài đo D; mức chỉ đổi model viết; các vai giữ trí nhớ dùng model cố định. Thêm dàn ý trước khi viết và kiểm văn bằng code (design §6.5).
- **Hệ quả:** phải chạy bài D trước khi mở cho người khác; danh sách model nằm trong `config/models.yaml`.
- **Người quyết:** Chủ dự án nêu vấn đề, Claude đề xuất cách · 19/10/2026

## D-4 · Tự viết lớp truy cập Neo4j, không dùng Graphiti
- **Bối cảnh:** Graphiti (Apache-2.0) có cạnh có hiệu lực theo thời gian, nhưng nó tự trích bằng LLM từ "episode" và không có mô hình "ai biết gì từ chương nào", lời nói dối, hay hai lớp sự thật/người chơi biết.
- **Quyết định:** tự viết Cypher. Mượn ý tưởng của Graphiti: đóng sự thật cũ bằng thời điểm hết hiệu lực thay vì xoá. Đọc mã nguồn Graphiti để tham khảo.
- **Hệ quả:** nhiều code hơn, nhưng đúng mục đích học, và kiểm soát được việc lọc bí mật.
- **Người quyết:** Claude · 19/10/2026

## D-5 · Rẽ nhánh bằng sao chép đồ thị
- **Bối cảnh:** bản đầu định gắn `branch_id` lên mọi cạnh rồi đi ngược chuỗi nhánh tổ tiên. Cách đó làm mọi truy vấn phức tạp, và việc đóng một cạnh của nhánh cha bên trong nhánh con rất dễ sai.
- **Quyết định:** rẽ nhánh = sao chép đồ thị truyện tại chương rẽ thành truyện mới (`story_id` mới). Bản 1 không làm gì thêm.
- **Hệ quả:** tốn chỗ hơn, nhưng đồ thị một truyện chỉ cỡ vài nghìn nút. Truy vấn luôn là truy vấn một nhánh.
- **Người quyết:** Claude · 19/10/2026

## D-6 · Ghi một chương: Postgres là nguồn gốc, Neo4j áp dụng có định danh
- **Bối cảnh:** không có transaction chung giữa Postgres và Neo4j.
- **Quyết định:**
  1. Trong một transaction Postgres: lưu chương trạng thái `pending` kèm gói thay đổi đồ thị.
  2. Áp gói vào Neo4j trong một transaction; mọi nút/cạnh mang `commit_id`, `MERGE` theo khoá nên chạy lại an toàn.
  3. Thành công thì đặt `committed`.
  4. Lỗi hẳn thì xoá theo `commit_id` và đặt `failed`.
  5. Mọi lần đọc chỉ thấy dữ liệu của chương `committed`.
- **Hệ quả:** không có trạng thái nửa vời; trạng thái phiên chỉ đổi sau khi ghi thành công.
- **Người quyết:** Claude · 19/10/2026

## D-7 · Bộ đo tách bốn bài A/B/C/D
- **Bối cảnh:** bản đầu định cho mọi đối thủ sinh truyện từ cùng kịch bản lựa chọn. Nhưng mỗi hệ thống viết ra truyện khác nhau, nên câu hỏi không còn khớp với truyện.
- **Quyết định:**
  - A: QA trên bộ chương cố định, chia theo khoảng cách.
  - B: người canh trên lỗi cài sẵn.
  - C: trích thực thể tiếng Việt.
  - D: chất lượng văn theo model.
  - Bản 1 chạy A (3 đối thủ), B và D.
- **Hệ quả:** biết lỗi nằm ở tầng nào; giảm việc chấm tay.
- **Người quyết:** Claude · 19/10/2026

## D-8 · Giữ LangGraph
- **Bối cảnh:** pipeline gần như thẳng, viết bằng Python thường cũng được.
- **Quyết định:** dùng LangGraph, vì học nó là một mục tiêu và vì nó lưu được trạng thái để chạy tiếp sau khi hỏng giữa chừng. Toàn bộ đồ thị LangGraph nằm trong một module.
- **Người quyết:** Claude · 19/10/2026

## D-9 · Tên sản phẩm là WriTory
- **Bối cảnh:** bản thiết kế đầu dùng tên tạm "Mạch Truyện".
- **Quyết định:** tên sản phẩm là **WriTory**, trùng tên repo và tên package `writory`. Bỏ mục "tên chính thức" khỏi danh sách còn mở (design §14).
- **Hệ quả:** giao diện, tài liệu và nhận diện đều dùng "WriTory". Không dùng tên cũ ở bất kỳ đâu.
- **Người quyết:** Chủ dự án · 19/10/2026

## D-10 · Trần chi phí: kiểm trước mỗi lời gọi, không rõ chi phí thì dừng
- **Bối cảnh:** G8 cần trần theo cảnh, chương, truyện. OpenRouter trả `usage.cost` tính bằng credit, có thể thiếu.
- **Quyết định:**
  - `CostTracker` kiểm cả ba trần **trước** mỗi lời gọi. Trần `null` gây lỗi `CONFIG_LIMIT_NOT_SET`, không coi là vô hạn.
  - Phản hồi thiếu `usage.cost` gây lỗi `LLM_COST_UNKNOWN` và dừng. Coi 1 credit = 1 USD.
  - Thử lại: xem D-14.
- **Hệ quả:** lời gọi cuối có thể vượt trần đúng bằng chi phí của chính nó. Stream đứt giữa chừng thì chưa ghi được chi phí.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-11 · Mã hoá key người chơi bằng Fernet
- **Bối cảnh:** G7 yêu cầu mã hoá key khi lưu, khoá lấy từ biến môi trường.
- **Quyết định:** dùng Fernet của thư viện `cryptography`. Khoá đặt trong `PLAYER_KEY_ENCRYPTION_KEY`. Khoá sai định dạng thì báo lỗi lúc khởi động. Giải mã hỏng gây lỗi `PLAYER_KEY_UNREADABLE`.
- **Hệ quả:** bản 1 chưa xoay khoá (cần thì dùng `MultiFernet`). Mất khoá thì người chơi phải nhập lại key.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-12 · Bọc chữ người chơi bằng khối `<player_data>` có escape
- **Bối cảnh:** G4 yêu cầu chữ người chơi luôn là dữ liệu, kể cả câu cố tình đóng khối hoặc giả thẻ system.
- **Quyết định:**
  - Chữ người chơi đi vào prompt qua `UserAuthored`; `str()` luôn trả khối đã bọc.
  - Escape `&`, `<`, `>` bên trong khối.
  - `system_message` từ chối `UserAuthored` và mọi chuỗi chứa khối.
- **Hệ quả:** model thấy `&lt;` thay cho `<`. Chữ hiện cho người chơi lấy từ dữ liệu gốc, không lấy từ prompt.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-13 · `config.py` và `errors.py` đặt ở gốc gói `writory`
- **Bối cảnh:** CLAUDE.md §3 yêu cầu ghi lý do khi thêm module mới.
- **Quyết định:** cấu hình và mã lỗi dùng chung cho mọi module, nên đặt ở gốc gói. Đặt trong một module con sẽ tạo phụ thuộc ngược. `safety/redact.py` không import gì của `writory`, để `errors.py` dùng được mà không bị vòng import.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-14 · Mỗi loại lỗi có số lần thử lại riêng (thay thế phần thử lại của D-10)
- **Bối cảnh:** `with_retries` gộp lỗi mạng với JSON sai schema. Nếu nơi gọi truyền số lần dành cho lỗi mạng vào một lời gọi trích JSON, JSON hỏng sẽ được thử lại nhiều lần, trái G11.
- **Quyết định:**
  - `with_retries(op, *, max_retries, retry_on)`, bắt buộc truyền `retry_on`. Lỗi có mã ngoài `retry_on` ném ra ngay.
  - Lỗi mạng tạm thời: `retry_on=RETRY_TRANSIENT` (`LLM_UNAVAILABLE`), số lần `retries.llm_transient` trong `config/limits.yaml`.
  - JSON sai schema: `retry_on=RETRY_SCHEMA` (`LLM_BAD_RESPONSE`), số lần `retries.extract_schema_retry`.
  - Không chờ giữa các lần thử; lỗi 429 không được thử lại.
- **Hệ quả:** một lời gọi trích JSON cần hai lớp `with_retries` lồng nhau nếu muốn chịu cả hai loại lỗi.
- **Người quyết:** Claude (điều phối) · 19/10/2026

## D-15 · Nút không sửa sau khi tạo; trạng thái đổi bằng cạnh
- **Bối cảnh:** D-6 cần gỡ được một commit theo `commit_id`. Nếu commit sửa thuộc tính của nút có sẵn (ví dụ `alive = false`) thì gỡ không khôi phục được giá trị cũ.
- **Quyết định:** nút chỉ được tạo, không được sửa. Trạng thái đổi theo chương là cạnh có `valid_from_chapter`/`valid_to_chapter`: chết là `DIED_IN`, lời nói dối bị phát hiện là `KNOWS` tới `Lie`, mạch gỡ là `RESOLVED_IN`. Đóng cạnh ghi `closed_by_commit` để gỡ commit thì mở lại được. "Ở chương N" = cuối chương N; chương 0 = trước khi truyện bắt đầu.
- **Hệ quả:** áp lại và gỡ commit đơn giản, có test. Nút đổi tên (bản 3) sẽ cần cách riêng, ví dụ thêm `aliases` bằng cạnh.
- **Người quyết:** Claude (Session 1) · 19/10/2026

## D-16 · Định nghĩa `player_view`
- **Bối cảnh:** `graph-schema.md` nói `player_view` = nhân vật chính `KNOWS` + `REVEALED_TO_PLAYER`, nhưng chưa nói trả những trường nào.
- **Quyết định:** một hàm `graph.player_view` trả: nút đã `REVEALED_TO_PLAYER` hoặc được nhân vật chính `KNOWS` tới chương N, cộng lời nói dối do nhân vật chính nói. Chỉ trả trường trong danh sách trắng (id, loại, chữ hiện, biệt danh, chương, câu trích, `about` trong phạm vi view). Không trả quan hệ, người giữ đồ vật, vai trong sự kiện, trạng thái bị phát hiện của lời nói dối. `KNOWS` của nhân vật chính cũng phải kèm câu trích như G3.
- **Hệ quả:** sổ tay bản 1 chưa hiện "ai đang giữ gì" hay quan hệ hiện tại; muốn hiện thì phải mở rộng hàm này và thêm test G1.
- **Người quyết:** Claude (Session 1) · 19/10/2026

## D-17 · `player_view` hiện tên người chơi biết (`known_as`), không hiện `name`
- **Bối cảnh:** theo D-16, `player_view` hiện `name` và mọi `aliases` của lớp sự thật. Một nhân vật ra mắt bằng biệt danh ("người đàn ông áo đen") sẽ lộ tên thật ngay trong sổ tay; đồ vật cũng vậy ("thanh kiếm cũ" lộ thành "Thanh Sương").
- **Quyết định:** cạnh `REVEALED_TO_PLAYER` và `KNOWS` (của nhân vật chính) tới Character/Item/Location/Faction bắt buộc có `known_as`, và code kiểm `known_as` nằm trong `quote`. `player_view` chỉ hiện `known_as` đã hé lộ tới chương N, không bao giờ hiện `name` hay `aliases`. Chữ của `Fact`/`Event` chỉ chứa một mệnh đề; chi tiết bí mật là `Fact` riêng. Bổ sung D-16 về trường hiện cho nút có tên.
- **Hệ quả:** bước trích thay đổi (tuần 2) phải xuất `known_as` cho mỗi lần hé lộ. Truyện mẫu có thêm Lý Thất, ra mắt bằng biệt danh ở chương 4, lộ tên thật ở chương 5.
- **Người quyết:** Claude (điều phối) · 19/10/2026

## D-18 · Lời thoại theo kiểu gạch đầu dòng
- **Bối cảnh:** design §6.5 cần kiểm "định dạng lời thoại" nhưng chưa nói kiểu nào. Truyện mẫu `data/sample-story/` dùng kiểu gạch đầu dòng.
- **Quyết định:** dòng thoại mở đầu bằng "— " (U+2014 + khoảng trắng); config `dialogue_style: dash`. Giá trị `quotes` để dành, gặp thì báo "chưa hỗ trợ". Kiểm văn báo lỗi khi:
  - dòng mở đầu bằng "–" hoặc "-";
  - đoạn mở đầu bằng ngoặc kép;
  - dòng chỉ có dấu gạch;
  - ngoặc kép không đóng (mọi chế độ).
- **Ngoại lệ:** đoạn được ngoặc kép bao trọn, ngay sau đoạn kết thúc bằng ":", là trích nguyên văn (thư, chữ khắc), không báo.
- **Hệ quả:** ngoặc kép giữa đoạn (chữ khắc, tên sách, câu trích) là hợp lệ. Lời thoại sai kiểu đứng trọn một đoạn ngay sau ":" bị lọt (chấp nhận: báo nhầm tốn một lượt viết lại, để lọt chỉ là lỗi thẩm mỹ). Kiểm văn chỉ báo lỗi, không tự sửa.
- **Người quyết:** Claude (điều phối) · 19/10/2026

## D-19 · Ngưỡng kiểm văn nằm trong `config/quality.yaml`
- **Bối cảnh:** kiểm văn (design §6.5 mục 5) cần ngưỡng và danh sách sáo ngữ. Ba file config sẵn có không hợp chỗ.
- **Quyết định:**
  - Thêm `config/quality.yaml`. Ngưỡng chưa đo để `null`; code dùng tới thì báo `CONFIG_LIMIT_NOT_SET`.
  - Danh sách sáo ngữ là bản nháp chờ chủ dự án duyệt (`draft: true`).
  - "Tỉ lệ lặp" kiểm theo từng cụm: một cụm `ngram_words` từ xuất hiện quá `max_repeats` lần thì báo tại chỗ lặp. Không dùng một tỉ lệ cho cả cảnh, vì lỗi phải có vị trí.
  - Chữ Latin chỉ bị đếm khi không phải âm tiết tiếng Việt viết không dấu và không nằm trong danh sách từ mượn.
- **Hệ quả:** văn tiếng Việt bỏ dấu cả câu không bị bắt; chữ Cyrillic, Thái chưa kiểm. Hai việc này để tuần 2.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-20 · Migration Postgres bằng SQL thuần và một runner nhỏ
- **Bối cảnh:** cần bảng `stories`, `chapters`, `change_packages` cho D-6. Alembic kéo theo SQLAlchemy, trong khi code chỉ dùng psycopg.
- **Quyết định:** file `.sql` trong `backend/src/writory/db/migrations/`, chạy theo thứ tự tên bằng `writory.db.migrate`. Tên đã chạy ghi vào `schema_migrations`. Tất cả chạy trong một transaction, có khoá advisory. Không có migration ngược; đổi schema thì thêm file mới.
- **Hệ quả:** không thêm phụ thuộc. Không tự sinh migration từ model; viết SQL tay.
- **Người quyết:** Claude (Session 1) · 19/10/2026

## D-21 · Gói của chương N chỉ mở và đóng cạnh ở chương N; chương 0 là thế giới lúc khởi tạo
- **Bối cảnh:** D-6 cần "chỉ đọc chương đã commit". Đọc ở chương đã commit chỉ loại được dữ liệu của chương `pending` khi mọi cạnh của chương đó có `valid_from_chapter` bằng số chương. Truyện mẫu cũ có cạnh `valid_from_chapter: 0` nằm trong gói chương 1 và chương 4.
- **Quyết định:** `commit_chapter` từ chối gói có cạnh mở ở chương khác, cạnh đặt sẵn ngày đóng, hoặc `close` ở chương khác (`chapter_rule_problems`). Sự thật có từ trước trang đầu nằm trong gói chương 0 (đồ thị ban đầu, design §4.1). Truyện mẫu đã chuyển các sự thật đó sang chương 0; đáp án §7.3 không đổi. Số chương hiện hành chỉ lấy từ `writory.db.current_chapter`.
- **Hệ quả:** một sự thật chỉ phát hiện ra ở chương N (ví dụ "hoá ra Lan là người của Hội từ trước") được ghi là đúng từ chương N, không ghi lùi về trước. Chi tiết quá khứ mới do model nghĩ ra ở chương N cũng mang `valid_from_chapter = N`, nghĩa là "đồ thị biết từ chương N". Muốn hỏi "thật ra từ khi nào" thì phải thêm thuộc tính riêng.
- **Người quyết:** Claude (Session 1), điều phối đã duyệt · 19/10/2026

## D-22 · `KNOWS.how` là danh sách đóng; "được kể" phải có người kể
- **Bối cảnh:** người canh (design §8 mục 1) cần kiểm "người kể có biết điều đó không". Trước đây `how` là chuỗi tự do ("được Lão Gù kể"), nên phép kiểm có thể bị bỏ qua.
- **Quyết định:**
  - `how` chỉ nhận một trong `chứng kiến`, `được kể`, `suy ra`, `tự biết`, `tự làm` (`KNOWS_HOW`, chuẩn hoá NFC).
  - `được kể` bắt buộc có `told_by` là id người kể; `told_by` chỉ dùng với `được kể`.
  - `by_choice` (id lựa chọn dẫn tới lần lộ, design §6.1) chỉ đặt trên KNOWS/REVEALED_TO_PLAYER.
  - Truyện mẫu sửa theo văn (sửa dữ liệu gốc bài A): Minh được Lão Gù kể (`told_by: gu`, thêm `gu KNOWS f_gu_old_hac_ky` ở chương 0); Lan biết lời nói dối của Minh là `suy ra`. Đáp án `answers.yaml` không đổi.
- **Hệ quả:** extractor (tuần 2) phải xuất `how` theo danh sách này. Chưa kiểm được `by_choice` trỏ tới lựa chọn có thật (chưa có nút Choice).
- **Người quyết:** Claude (Session 2), điều phối đã duyệt · 19/10/2026

## D-23 · Người canh kiểm bằng code trước khi ghi; ngưỡng trong `config/guard.yaml`
- **Bối cảnh:** design §8 yêu cầu phần nào kiểm được bằng code thì kiểm bằng code. Gói của các cảnh trước trong chương chưa nằm trong Neo4j.
- **Quyết định:**
  - `writory.guard.check_scene_package` đọc trạng thái phủ: nền đã commit + gói các cảnh trước + gói cảnh này (`OverlayState`).
  - Các phép kiểm: quy tắc D-21; người chết hành động, kể cả làm người kể (`told_by`) (chết ở chương trước hoặc ở cảnh trước, chết trong chính cảnh này thì không tính); "tối đa một" cho HOLDS theo đồ vật, LOCATED_AT của Item, RELATES_TO theo cặp; người kể không biết; lộ sớm so với `story_plan` (mức `block`, trừ khi có `by_choice`); quan hệ đổi quá ngưỡng mà chương không có Event liên quan.
  - Ngưỡng nằm trong file mới `config/guard.yaml`, để `null` tới khi đo.
- **Hệ quả:** phép kiểm tất định, đo bằng bài B. Lỗi của gói (D-21) cũng xếp mức `rewrite`, dù sửa gói có thể chỉ cần trích lại.
- **Người quyết:** Claude (Session 2), điều phối đã duyệt · 19/10/2026

## D-24 · Runner bài đo nằm trong module được đo
- **Bối cảnh:** bài đo cần import code của gói (client LLM, kiểm văn). CLAUDE.md §3 chưa nói runner đặt ở đâu.
- **Quyết định:**
  - Runner của bài X nằm trong module được đo, tên `writory.<module>.bench_<x>`, chạy bằng `cd backend && uv run python -m writory.<module>.bench_<x>`. Bài D: `writory.quality.bench_d`; bài B: `writory.guard.bench_b`.
  - Dữ liệu khai trước ở `evals/scenarios/<bài>/`. Kết quả ở `evals/results/<ngày>-<bài>-<nhãn>/`, kèm `meta.json` (commit SHA, sha256 dữ liệu, tên model).
  - Thư viện chỉ bộ đo cần (`anthropic`) nằm trong nhóm phụ thuộc `eval` và được import muộn, nên gói chính không phụ thuộc nó. `default-groups` gồm `eval`, để test của runner chạy được trong CI.
- **Hệ quả:** không có thư mục code riêng cho bộ đo. Kết quả dry-run (`*-dryrun/`) không commit.
- **Người quyết:** Claude (điều phối); nhóm `eval` mặc định: Claude (Session 3) · 19/10/2026

## D-25 · Bài D: Sonnet chấm tuyệt đối theo rubric
- **Bối cảnh:** design §9 cũ ghi người chấm là chính, LLM chấm so cặp chỉ để sàng lọc, chấm ≥ 3 lần, dùng 3 cảnh mẫu.
- **Quyết định:**
  - Giám khảo `claude-sonnet-5-5`, effort high, thinking adaptive, structured output. Không temperature, không fallbacks: giám khảo phải cố định.
  - Chấm tuyệt đối theo `rubric.yaml`, mỗi tiêu chí kèm câu trích. Giám khảo không biết model nào viết. Bài viết là dữ liệu, được bọc trong khối `<scene>`.
  - Chấm 2 lần mỗi bài. Lần 3 chỉ chạy khi một tiêu chí thang 1–5 lệch ≥ 2 điểm, hoặc `giu_bi_mat` bất đồng. Điểm cuối là trung vị các lần chấm.
  - Dùng 10 dàn ý, vì độ biến thiên giữa các đề lớn hơn giữa các lần sinh. Khoảng tin cậy 95% tính theo t trên số case, sau khi gộp mẫu và lần chấm trong case.
  - Model viết họ `anthropic/` bị từ chối. Chủ dự án chấm tay 15 cảnh để hiệu chỉnh giám khảo.
- **Hệ quả:** chi phí giám khảo lớn hơn chi phí viết. Bài bị cắt, bị từ chối hoặc gặp lỗi được ghi riêng, không thành điểm 0. Thay phần chấm của bài D trong design §9 cũ.
- **Người quyết:** Chủ dự án (yêu cầu Sonnet chấm theo rubric); cách làm do điều phối chốt · 19/10/2026

## D-26 · Bộ dò lộ (G2): chuỗi cấm tạo bằng code ở từng chương
- **Bối cảnh:** G2 cần chặn chữ để lộ bí mật trước khi hiện. Đo trên truyện mẫu: nếu cấm mọi tên và biệt danh lớp truth chưa có trong `known_as`, văn sạch của cả 5 chương đều bị báo. Có hai loại báo nhầm: tên thật được nói ngay trong câu trích hé lộ ("Tên thật của lão là Hồ Sĩ Bằng"), và biệt danh là danh từ chung ("thanh kiếm", "quán trà đầu bến").
- **Quyết định:**
  - "Người chơi đã thấy gì" lấy duy nhất từ `PlayerView` (D-16): chữ hiện, biệt danh, mọi câu trích (`quotes`), lời nói dối của nhân vật chính. Định nghĩa nằm trong hàm thuần `graph.build_player_view`, dùng chung cho Neo4j và GraphState.
  - Tên chỉ bị cấm khi có từ viết hoa (tên riêng) mà người chơi chưa thấy trong `PlayerView`.
  - Bí mật của `story_plan` chưa tới khoảng lộ và chưa được hé lộ (kể cả lộ sớm do lựa chọn): nhóm `leak_terms` trúng khi mọi cụm cùng nằm trong một câu. Bí mật không có `leak_terms` thì ghi cảnh báo.
  - So sau NFC và bỏ dấu, trọn từ. Cụm một từ phân biệt hoa thường; cụm nhiều từ thì không.
  - Trúng thì báo `SCENE_LEAK_BLOCKED`, câu báo trung tính (design §6.6). Log chỉ ghi loại và vị trí, không ghi chữ bị lộ.
  - Sửa `told_to` của lời nói dối trong `player_view` theo đúng D-17: tên người chơi biết, hoặc "(người chưa rõ tên)", không bao giờ là `name`.
- **Hệ quả:** biệt danh toàn chữ thường không được bảo vệ ("người đàn ông áo đen" lộ thì không bắt được). Tên nhiều từ viết thường, bỏ dấu ("ly that") vẫn bắt được. Tên một từ viết thường thì lọt, vì cụm một từ so có phân biệt hoa thường.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-27 · Phân loại ô tự viết: một lời gọi enum, fail closed
- **Bối cảnh:** G5 yêu cầu đọc ý định của ô tự viết bằng LLM có đầu ra enum, không dùng regex. Câu phủ định, câu dài và tấn công đội lốt hành động phải ra đúng.
- **Quyết định:**
  - `safety.classify_action`: một lời gọi `chat_json` với schema `Classification` (`label` thuộc 4 nhãn, `reason` ngắn chỉ để log), model `models.roles.classify`. Chữ người chơi bọc `UserAuthored` trong vai user (G4).
  - Trước khi gọi model, code kiểm chữ rỗng và độ dài theo `input.custom_action_max_chars` (`require()`). Giới hạn chưa đặt thì báo `CONFIG_LIMIT_NOT_SET`. Vai `roles.*` chưa chọn model thì báo `CONFIG_MODEL_NOT_SET` (`llm.require_model`, dùng cho mọi vai).
  - JSON sai schema thử lại theo `extract_schema_retry` (`RETRY_SCHEMA`); vẫn sai hoặc model lỗi thì ném lỗi, không mặc định là hợp lệ.
  - Hành động bất khả hay bạo lực trong truyện vẫn là `in_story_action`; hậu quả do pipeline xử lý (G6). `ensure_in_story` map 3 nhãn bị chặn sang `ACTION_OUT_OF_STORY`, `ACTION_FORBIDDEN`, `ACTION_UNCLEAR`, câu trung tính, không kèm lý do.
- **Hệ quả:** mỗi lần gửi ô tự viết tốn thêm một lời gọi model. `forbidden_content` chỉ gồm chặn cứng G9; trần mức u tối theo từng truyện để sau, khi pipeline có thiết lập truyện. Lỗi model tạm thời (`LLM_UNAVAILABLE`) do pipeline bọc `RETRY_TRANSIENT` ở ngoài. Độ chính xác với model thật chưa đo.
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-28 · Ngữ cảnh đồ thị cho model viết
- **Bối cảnh:** design §6.2 bước 1 cần lấy phần đồ thị liên quan cho model viết. Design §13 khuyên tách "sự thật cần tôn trọng" khỏi "gợi ý" để văn không khô.
- **Quyết định:**
  - `graph/context.py` đọc lớp `truth` ở chương đã commit (`as_of_chapter`) để viết chương kế tiếp. Ngữ cảnh gồm: người có mặt, quan hệ giữa họ, `Fact` họ biết, lời dối chưa bị phát hiện, bí mật trong `story_plan` kèm trạng thái lộ, nút cách 1–2 bước, và mạch đang mở.
  - Nút lân cận không đi qua `REVEALED_TO_PLAYER` hay `Chapter`, không lặp lại nút đã ở phần sự thật. Số nút tối đa nằm ở `limits.context.writer_max_neighbors`, đang `null` cho tới khi đo; hàm nhận giới hạn qua tham số.
  - Render chia hai phần; người liên quan đã chết thuộc phần sự thật. Chữ của nút `user_authored` đi qua `UserAuthored`.
  - `plan` nhận qua một Protocol (chỉ cần `secrets`), để khỏi phụ thuộc nhánh chứa `StoryPlan`.
- **Hệ quả:** trên truyện mẫu, chương 4 với Minh và Lan có mặt, bản render khoảng 2.500 ký tự (in ra trong test, không khẳng định con số). Chưa chạy trên `GraphState` (graph-schema.md, mục Chưa làm).
- **Người quyết:** Claude (Session 1) · 19/10/2026

## D-29 · Khung API: factory, một bảng mã lỗi → HTTP, lỗi lạ không lộ gì
- **Bối cảnh:** cần app FastAPI trước các endpoint truyện. G12 cấm trả lỗi chung chung kèm chi tiết kỹ thuật; G7 cần redaction cả ở logger của uvicorn.
- **Quyết định:**
  - `writory.api.create_app(settings, health_checks=None)` là factory; không tạo app lúc import. Chạy: `uvicorn writory.api:create_app --factory`.
  - Lúc khởi động gắn `install_log_redaction` cho root và `uvicorn`, `uvicorn.error`, `uvicorn.access`. Bộ lọc giữ nguyên `record.args`, chỉ redact từng arg, vì `AccessFormatter` của uvicorn đọc args.
  - `WritoryError` → `player_payload()` với status trong bảng duy nhất `api/errors.HTTP_STATUS`; test bắt mọi mã phải có status. Exception khác → `INTERNAL_ERROR` (500), câu cố định; traceback chỉ vào log, đã redact.
  - `GET /health`: `ok`/`down` cho Neo4j và Postgres, 503 nếu có phần down; lỗi chỉ vào log.
- **Hệ quả:** nhánh nào thêm mã lỗi phải thêm status vào bảng. Lỗi 404/422 của FastAPI vẫn theo mặc định, chưa theo G12. Chưa gọi `reconcile_pending` lúc khởi động (TODO).
- **Người quyết:** Claude (Session 2) · 19/10/2026

## D-30 · Kiểm văn bắt suy luận và chữ của prompt lọt vào cảnh
- **Bối cảnh:** ở pilot bài D, một model viết đã đặt `reasoning: none` mà vẫn để ghi chú kế hoạch cùng thẻ `</think…>` lọt vào đầu cảnh. Ghi chú đó nhắc tới cách giữ bí mật. Giám khảo thấy nhưng vẫn cho 4; kiểm văn chỉ bắt được tình cờ qua luật chữ Latin.
- **Quyết định:**
  - Thêm hàm thuần `check_meta_leak` trong `writory/quality/checks.py`, loại lỗi `meta_leak`, không cần config.
  - Hàm bắt thẻ suy luận (`<think`, `</think…>`, `thinking`, `reasoning`) và một danh sách hẹp các cụm chỉ có trong đề bài hoặc hướng dẫn văn phong (`_META_PHRASES`).
  - Có test cho ca lọt thật lấy từ pilot, cho các ca gần giống mà sạch, và cho toàn bộ văn sạch có sẵn.
  - Bài D tính cột "Lọt suy luận" từ văn bản đã lưu khi dựng `summary.md`, không gọi lại model.
- **Hệ quả:** chưa đưa vào `check_scene`, nên chưa làm pipeline viết lại cảnh. Đưa vào lúc nào sẽ quyết khi làm pipeline (tuần 2); khi đó cảnh có lỗi này phải bị chặn trước khi hiện (G2). Danh sách cụm hẹp, nên có thể bỏ sót ghi chú viết bằng chữ khác.
- **Người quyết:** điều phối (yêu cầu hàm và cột); danh sách mẫu: Claude (Session 3) · 19/10/2026

## D-31 · Dấu thoại là "- "; backend thay mọi "—" bằng "-" (thay thế phần ký tự gạch của D-18)
- **Bối cảnh:** D-18 chọn em dash "— " cho dòng thoại. Chấm tay bài D, chủ dự án yêu cầu "backend thay toàn bộ ' — ' bằng ' - '". Model cũng trộn em dash, en dash và gạch nối.
- **Quyết định:** `writory.quality.normalize_dashes` đổi mọi em/en dash thành "-" và dòng thoại thành "- ". `check_scene`/`check_dialogue` chuẩn hoá trước rồi mới kiểm; bài đo D chuẩn hoá trước khi đưa giám khảo. Kiểu gạch đầu dòng và ngoại lệ trích sau ":" của D-18 giữ nguyên.
- **Hệ quả:** dòng mở bằng gạch bất kỳ đều hợp lệ; dòng chỉ có gạch và dòng mở bằng ngoặc kép vẫn là lỗi. Vị trí lỗi tính trên văn bản đã chuẩn hoá. Đường hiện chữ cho người chơi (pipeline) phải gọi cùng hàm này.
- **Người quyết:** Chủ dự án · 20/10/2026

## D-32 · Quy ước tên và địa danh do người chơi chọn, mặc định theo thể loại
- **Bối cảnh:** chấm tay bài D, chủ dự án ghi: truyện giả tưởng mà dùng tên Việt và địa danh thật thì lạc chất; truyện tu tiên, kiếm hiệp cần tên kiểu Hán Việt.
- **Quyết định:** lúc khởi tạo có tag quy ước tên (Hán Việt / Việt) và địa danh (thật / hư cấu). Người chơi chọn; mặc định theo thể loại như design §4.1. Prompt mọi bước sinh nội dung nhận quy ước này.
- **Hệ quả:** bộ đề bài D có trường `naming` (cases.yaml v2); rubric v2 thêm tiêu chí `quy_uoc_the_loai`. Đề cũ có địa danh thật trong truyện giả tưởng là lỗi của đề, không phải của model.
- **Người quyết:** Chủ dự án · 20/10/2026

## D-33 · Model viết: GPT-6 Luna, một mức duy nhất
- **Bối cảnh:** bài D hai lượt (`evals/results/2026-10-19-quality-full/`, `evals/results/2026-10-20-quality-r2/`): GPT-6 Luna điểm sát mốc GPT-6.1 Sol, rẻ nhất trong nhóm (khoảng 1/23 chi phí Sol, rẻ hơn DeepSeek V4.1 Flash sau khi DeepSeek tăng giá), nhanh nhất, không lộ bí mật. Chấm tay lượt 1: Luna là cảnh duy nhất người và giám khảo cho điểm như nhau.
- **Quyết định:** `writer_tiers` chỉ có mức "Tiêu chuẩn" = `openai/gpt-6-luna` (`config/models.yaml`). Không có mức GPT-6.1 Sol vì giá.
- **Hệ quả:** design §6.5 mục 1 (nhiều mức) tạm chỉ còn một mức; thêm mức mới phải qua bài D. Điểm yếu cần cải thiện bằng prompt: trình bày lời thoại (rubric v2). Các vai giữ trí nhớ (`roles.*`) chưa chọn model; chọn khi có bài đo cho từng vai.
- **Người quyết:** Chủ dự án · 20/10/2026

## D-34 · Bài C v1: chọn model cho vai trích bằng cách chấm bằng code trên truyện mẫu
- **Bối cảnh:** vai `extract` ghi thẳng vào đồ thị; cần chọn model. Đáp án có sẵn: đồ thị dựng tay của truyện mẫu.
- **Quyết định:** bộ trích `pipeline/extract.py` (prompt `extract-1`, đầu ra JSON mọi trường bắt buộc, cạnh sai quy tắc bị bỏ từng cái). Bài C v1 cho sẵn danh mục thực thể, chấm bằng code; chỉ số chính là F1 lớp người chơi biết và số lần hé lộ sai. Runner `writory.pipeline.bench_c` (D-24). Bộ trích nhận cả `RESOLVED_IN` (oracle phát hiện thiếu).
- **Hệ quả:** chưa đo phát hiện thực thể mới; pipeline phải tạo nút mới ở bước khác (dàn ý/lựa chọn) trước khi trích. `chat_json` nhận `extra` (tham số riêng theo model).
- **Người quyết:** Claude (điều phối); chủ dự án đồng ý làm bài đo này · 20/10/2026

## D-35 · Vai trích dùng GPT-6 Luna, suy luận mức thấp
- **Bối cảnh:** bài C (`evals/results/2026-10-20-extract-v1/`, `-v2/`, `-v2-qwen/`, `-v2-luna-reasoning/`). Prompt `extract-2` kèm sửa G3 đưa số lần hé lộ sai của Luna từ 4 về 0. Bật suy luận thấp tăng F1 lớp người chơi biết từ 0,63 lên 0,78, vẫn 0 hé lộ sai, chưa tới 0,001 USD/chương. DeepSeek V4.1 Flash thấp hơn hẳn (0,35). Qwen 3.8 Flash bị giới hạn tần suất 60% lời gọi.
- **Quyết định:** `roles.extract = openai/gpt-6-luna`, `role_reasoning.extract = low` (`config/models.yaml`). Thêm mục `role_reasoning` vào config.
- **Hệ quả:** F1 0,78 trên 5 chương mẫu, dữ liệu nhỏ và prompt đã chỉnh theo chính bộ này, nên con số có thể lạc quan. Cần đo lại khi có bài C đầy đủ và truyện thứ hai. Các vai khác chưa chọn.
- **Người quyết:** Claude (điều phối), theo kết quả đo; chủ dự án đồng ý cách chọn · 20/10/2026

## D-36 · Đường đi một chương: LangGraph một module; lỗi mức chặn còn sau lượt viết lại thì không hiện cảnh
- **Bối cảnh:** design §6.2, D-1, D-6, D-8. Mỗi cảnh cần dàn ý → viết → kiểm văn → trích → người canh → dò lộ, rồi gộp gói, ghi, tạo lựa chọn. Gói của các cảnh trước chưa nằm trong Neo4j.
- **Quyết định:**
  - Đồ thị LangGraph trong `pipeline/chapter.py` (phụ thuộc qua runtime context, sự kiện qua custom stream). Đề dàn ý và đề viết ở `scene.py`; giao thức kho ở `store.py` (`GraphStore` = Neo4j + Postgres). Sự kiện cho giao diện ở `events.py`: `stage`, `scene_ready`, `scene_blocked`, `chapter_committed`, `choices_ready`, `error`.
  - Ngữ cảnh mỗi cảnh: `writer_context` ở chương đã commit, theo người có mặt của dàn ý, cộng văn và thay đổi đã trích của các cảnh trước. Bộ trích, người canh và bộ dò lộ đọc nền đã commit phủ gói các cảnh trước (`OverlayState`). Bộ dò lộ tính cả hé lộ của chính cảnh đó.
  - Soát trên chữ đã chuẩn hoá (D-31), tức đúng chữ sẽ hiện. Mọi loại lỗi đều được viết lại tối đa `retries.rewrite_per_scene` lần, kèm danh sách lỗi. Nếu bản cuối còn lỗi mức chặn (bộ dò lộ, `meta_leak` D-30, người canh báo lộ sớm) thì phát `scene_blocked`, dừng chương, không ghi gì. Nếu chỉ còn lỗi mức viết lại thì hiện bản cuối, log chỉ ghi loại lỗi, và bỏ khỏi gói các cạnh người canh báo.
  - Gói chương gồm nút `Chapter` (id `ch<N>`) và cạnh của các cảnh. Hai cảnh cùng id thì lấy cảnh sau; cạnh mở rồi đóng trong cùng chương thì bỏ. Ghi bằng `commit_chapter`.
  - Kiểm config trước lời gọi đầu: model các vai, trần chi phí, ngưỡng kiểm văn và người canh, `writer_max_neighbors`. Chương trước còn `pending` thì báo `CHAPTER_PENDING`. Mọi lời gọi đi qua `MeteredClient`; JSON qua `with_json_retries` (D-14). Chữ model đặt ngoài khối dữ liệu đều qua `escape_text` (G4).
- **Hệ quả:** chưa có checkpointer, nên bấm thử lại sau `scene_blocked` sẽ viết lại cả chương. Chưa tạo thực thể mới (D-34). Chưa có tóm tắt chương trước, chưa có nhật ký người canh và nhật ký chi phí trong Postgres. Model viết chưa đặt `reasoning`/`max_tokens` như bài D.
- **Người quyết:** Claude (nhánh pipeline-chapter), chờ điều phối duyệt · 20/10/2026

## D-37 · Lựa chọn cuối chương: chỉ từ sổ tay, mã công khai; một chỗ lộ thì không hiện bộ nào
- **Bối cảnh:** design §6.2 bước 6, §6.3; G1, G2. Lựa chọn hiện cho người chơi và mang dữ liệu để ghi về sau.
- **Quyết định:**
  - `pipeline.choices.make_choices` nhận `PlayerView` của chương vừa ghi, dựng sổ tay bằng `narrator.render_notebook` (mã `public_entries`, D-40), và văn cảnh cuối đã hiện. Cả hai nằm trong khối dữ liệu. Hàm không nhận kế hoạch truyện hay ngữ cảnh model viết.
  - Đầu ra `ChoicesOutput` có đúng 3 lựa chọn, tối thiểu 2 loại (`action`/`dialogue`/`inner`). Lời thoại có `tone` (`truth`/`lie`/`silence`) và người nghe. Lựa chọn nói dối có `lie_content`; lựa chọn nội tâm có `feeling` và `about`. Sai một trong các điều này, mã lạ, hay người nghe không phải nhân vật đều tính là sai schema và được thử lại theo D-14.
  - Phía máy chủ, `Choice` đổi mã về id nút (`LieEffect`: nói dối X với Y). Người chơi nhận `PlayerChoice`: id mờ `choice-…`, loại, sắc thái, chữ.
  - `check_leaks` chạy trên chữ lựa chọn, `lie_content` và `feeling`. Trúng một chỗ thì không hiện bộ nào và báo mã mới `CHOICES_LEAK_BLOCKED` (502, câu trung tính), không tự gọi lại model. Chương đã ghi xong; gọi lại `make_choices` để tạo bộ mới.
- **Hệ quả:** chưa ghi dữ liệu của lựa chọn vào đồ thị khi người chơi chọn (Lie, FEELS ở chương sau). Văn cảnh cuối là chữ trên trang và đã qua bộ dò lộ, nhưng không nằm trong `player_view`.
- **Người quyết:** Claude (nhánh pipeline-chapter), chờ điều phối duyệt · 20/10/2026

## D-38 · Khởi tạo truyện: bốn bước, nhân vật chính do code dựng, chương 0 người chơi chưa biết gì
- **Bối cảnh:** design §4.1 cần 3 bối cảnh / 3 hướng / 3 nhân vật rồi bản kế hoạch và đồ thị ban đầu. Chương 0 là thế giới lúc khởi tạo (D-21). `KNOWS` của nhân vật chính là điều người chơi biết (D-16), mà ở chương 0 chưa có trang nào để trích câu (G3).
- **Quyết định:** `writory.pipeline.setup`:
  - `propose_settings`, `propose_plots`, `propose_characters`: đúng 3 lựa chọn, không trường rỗng. Prompt cấm viết bí mật vào lựa chọn, vì người chơi đọc chúng (G1). Đầu vào gom trong `StoryChoices` (tag, độ dài, góc nhìn, quy ước tên).
  - `build_story` trả `StoryPlan` + gói chương 0, kiểm bằng `initial_problems` (luật: graph-schema.md, mục Chương 0). Nhân vật chính do code dựng từ chữ người chơi, id `protagonist`, `user_authored: true`. Nhân vật chính không `KNOWS` gì, không có `REVEALED_TO_PLAYER`; `KNOWS` khác có `how: "tự biết"`. Mạch của kế hoạch là nút `Thread` có `planted_chapter: 0`.
  - Tag, bối cảnh và hướng đã chọn, nhân vật chính đã sửa đều bọc `UserAuthored`, vì trình duyệt gửi lại chúng (G4).
  - `Naming` chuyển từ bài đo D sang đây, dùng chung một chỗ. `default_naming` theo bảng design §4.1. Thể loại ngoài bảng dùng tên Việt, địa danh hư cấu.
- **Hệ quả:** chưa kiểm bằng code tên có đúng kiểu Hán Việt hay Việt; điều này chỉ nằm trong prompt. Chưa kiểm độ dài chữ người chơi sửa (`limits.input.*` đang null, chưa có khoá cho tính cách). Chưa lưu `StoryPlan` vào Postgres. `writer_context` chưa đọc `personality`/`backstory`.
- **Người quyết:** Claude (nhánh pipeline-setup), chờ điều phối duyệt · 20/10/2026

## D-39 · Vai `setup`; JSON sai schema thì thử lại, sai quy tắc thì báo `STORY_SETUP_INVALID`
- **Bối cảnh:** bốn bước khởi tạo cần một model (D-3: các vai cố định nằm trong config) và một cách xử lý khi model trả sai.
- **Quyết định:**
  - Thêm `roles.setup` và `role_reasoning.setup` vào `config/models.yaml`, đều `null`. Gọi qua `require_model`, nên chưa chọn model thì báo `CONFIG_MODEL_NOT_SET`. `llm.role_extra` đổi `role_reasoning.<vai>` thành `extra`, dùng được cho mọi vai.
  - JSON sai schema thử lại theo `retries.extract_schema_retry` (`RETRY_SCHEMA`, D-14). Không thêm khoá riêng, vì G11 đã nói "thử lại 1 lần".
  - Sai quy tắc (số lựa chọn, kế hoạch, gói chương 0) báo ngay mã mới `STORY_SETUP_INVALID` (HTTP 502), không tự gọi lại model, để không trừ tiền key người chơi khi chưa hỏi. Câu báo không nói sai ở đâu, vì chi tiết có thể chạm bản kế hoạch ẩn; chi tiết vào log, chỉ ghi id và số chương.
  - Không trả nửa vời: có một lỗi là không trả kế hoạch hay gói. Module không ghi gì.
- **Hệ quả:** người chơi phải bấm thử lại khi model sai quy tắc. Muốn tự thử lại thì đổi `retry_on`, cần chủ dự án đồng ý vì tốn tiền.
- **Người quyết:** Claude (nhánh pipeline-setup), chờ điều phối duyệt · 20/10/2026

## D-40 · Hỏi người kể: context chỉ từ `player_view`, mã công khai thay id, không biết thì một câu
- **Bối cảnh:** design §6.6 và G1/G2/G4/G8. `PlayerEntry.id` là id lớp truth, có thể lộ bí mật: ở chương 4 truyện mẫu, mục "gã lái đò mặt sẹo" có id `ly_that`.
- **Quyết định:**
  - `pipeline.narrator.ask_narrator` dựng context chỉ từ `PlayerView`. Mục mang mã `m1`…, lời nói dối mang `l1`… (`graph.public_entries`/`public_lies`, xếp theo chương, loại, chữ hiện, không theo id). Sổ tay API dùng cùng mã.
  - Câu hỏi vào khối `player_data`; cả sổ tay cũng vậy, vì `PlayerEntry` không mang cờ `user_authored`.
  - Đầu ra `NarratorOutput` (`known`, `answer`, `entry_ids`, đều bắt buộc). `known` sai, câu rỗng, `entry_ids` rỗng hoặc có mã ngoài sổ tay, hoặc `check_leaks` trúng → đúng câu "Bạn chưa biết điều này.". Log chỉ ghi số mã, loại và vị trí.
  - Gọi model bắt buộc qua `MeteredClient`; thử lại `extract_schema_retry` lồng trong `llm_transient` (D-14).
  - Trần `rate_limit.narrator_questions_per_chapter` và `input.narrator_question_max_chars` (mới), đều `null` tới khi chủ dự án đặt. Lượt giữ trong Postgres (`narrator_questions`) bằng một câu lệnh, trước khi gọi model, không trả lại khi lỗi. Câu hỏi rỗng, quá dài, hoặc sổ tay trống: không mất lượt, không gọi model.
  - Mã mới: `NARRATOR_QUESTION_EMPTY`, `NARRATOR_QUESTION_TOO_LONG` (422), `NARRATOR_LIMIT_REACHED` (429).
- **Hệ quả:** câu trả "Bạn chưa biết điều này." vẫn tính một lượt. Sổ tay không qua bộ dò lộ: chữ của nó chính là định nghĩa "người chơi đã thấy". Chưa có trần độ dài câu trả lời hay token đầu ra.
- **Người quyết:** điều phối (yêu cầu); mã công khai, cách đếm lượt: Claude (Session narrator) · 20/10/2026

## D-41 · Router `stories` chỉ mount khi bật cờ dev; dependency mặc định fail closed
- **Bối cảnh:** sổ tay và hỏi người kể cần API trước khi có đăng nhập (tuần 5), nên chưa kiểm được truyện thuộc ai (G10).
- **Quyết định:**
  - `Settings.enable_dev_routes` (`ENABLE_DEV_ROUTES`), mặc định `False`. `create_app` chỉ gắn router khi cờ bật; mỗi route còn kiểm `app.state.dev_routes_enabled`, nên gắn router vào app khác vẫn 404.
  - `GET /stories/{story_id}/notebook` → `NotebookOut` (danh sách trắng, mã công khai, D-40), đọc qua `committed_player_view`. `POST /stories/{story_id}/narrator` nhận `{question}`, trả `{answer}`.
  - Dependency nằm trong `api/deps.py`; test thay bằng `dependency_overrides`. Chưa có nơi lưu key người chơi → LLM mặc định báo `PLAYER_KEY_MISSING`, không bao giờ dùng key chủ dự án. Chưa có nơi lưu `story_plan` → lỗi, không trả lời.
  - `create_app` đọc `Settings()` và `load_config()` lúc gọi factory (trước đây `Settings()` đọc trong lifespan).
  - Thêm mã `WRITORY_RATE_LIMITED` (429) cho trần mỗi phút của WriTory (G8); chưa có bộ đếm vì chưa có tài khoản.
- **Hệ quả:** máy chủ thật không có router này tới khi có đăng nhập và kiểm quyền (TODO G10 trong `api/stories.py`). Chi phí hỏi người kể chưa cộng vào trần truyện, vì chưa có nhật ký chi phí.
- **Người quyết:** điều phối (yêu cầu cờ dev, fail closed); cách làm: Claude (Session narrator) · 20/10/2026

