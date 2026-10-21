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
- **Hệ quả:** chưa có checkpointer, nên bấm thử lại sau `scene_blocked` sẽ viết lại cả chương. Chưa tạo thực thể mới (D-34). Chưa có tóm tắt chương trước, chưa có nhật ký người canh và nhật ký chi phí trong Postgres. Model viết chưa đặt `max_tokens` như bài D; `reasoning` của model viết: D-43.
- **Người quyết:** Claude (nhánh pipeline-chapter), điều phối duyệt (PR #18). Bỏ cạnh người canh báo sai khi giữ bản thứ hai: Chủ dự án đồng ý · 20/10/2026

## D-37 · Lựa chọn cuối chương: chỉ từ sổ tay, mã công khai; một chỗ lộ thì không hiện bộ nào
- **Bối cảnh:** design §6.2 bước 6, §6.3; G1, G2. Lựa chọn hiện cho người chơi và mang dữ liệu để ghi về sau.
- **Quyết định:**
  - `pipeline.choices.make_choices` nhận `PlayerView` của chương vừa ghi, dựng sổ tay bằng `narrator.render_notebook` (mã `public_entries`, D-40), và văn cảnh cuối đã hiện. Cả hai nằm trong khối dữ liệu. Hàm không nhận kế hoạch truyện hay ngữ cảnh model viết.
  - Đầu ra `ChoicesOutput` có đúng 3 lựa chọn, tối thiểu 2 loại (`action`/`dialogue`/`inner`). Lời thoại có `tone` (`truth`/`lie`/`silence`) và người nghe. Lựa chọn nói dối có `lie_content`; lựa chọn nội tâm có `feeling` và `about`. Sai một trong các điều này, mã lạ, hay người nghe không phải nhân vật đều tính là sai schema và được thử lại theo D-14.
  - Phía máy chủ, `Choice` đổi mã về id nút (`LieEffect`: nói dối X với Y). Người chơi nhận `PlayerChoice`: id mờ `choice-…`, loại, sắc thái, chữ.
  - `check_leaks` chạy trên chữ lựa chọn, `lie_content` và `feeling`. Trúng một chỗ thì không hiện bộ nào và báo mã mới `CHOICES_LEAK_BLOCKED` (502, câu trung tính), không tự gọi lại model. Chương đã ghi xong; gọi lại `make_choices` để tạo bộ mới.
- **Hệ quả:** dữ liệu của lựa chọn được ghi vào đồ thị khi người chơi chọn rồi chương sau được viết (Lie, FEELS; D-55). Văn cảnh cuối là chữ trên trang và đã qua bộ dò lộ, nhưng không nằm trong `player_view`.
- **Người quyết:** Claude (nhánh pipeline-chapter), điều phối duyệt (PR #18). Văn cảnh cuối vào context của model lựa chọn (G1): Chủ dự án đồng ý · 20/10/2026

## D-38 · Khởi tạo truyện: bốn bước, nhân vật chính do code dựng, chương 0 người chơi chưa biết gì
- **Bối cảnh:** design §4.1 cần 3 bối cảnh / 3 hướng / 3 nhân vật rồi bản kế hoạch và đồ thị ban đầu. Chương 0 là thế giới lúc khởi tạo (D-21). `KNOWS` của nhân vật chính là điều người chơi biết (D-16), mà ở chương 0 chưa có trang nào để trích câu (G3).
- **Quyết định:** `writory.pipeline.setup`:
  - `propose_settings`, `propose_plots`, `propose_characters`: đúng 3 lựa chọn, không trường rỗng. Prompt cấm viết bí mật vào lựa chọn, vì người chơi đọc chúng (G1). Đầu vào gom trong `StoryChoices` (tag, độ dài, góc nhìn, quy ước tên).
  - `build_story` trả `StoryPlan` + gói chương 0, kiểm bằng `initial_problems` (luật: graph-schema.md, mục Chương 0). Nhân vật chính do code dựng từ chữ người chơi, id `protagonist`, `user_authored: true`. Nhân vật chính không `KNOWS` gì, không có `REVEALED_TO_PLAYER`; `KNOWS` khác có `how: "tự biết"`. Mạch của kế hoạch là nút `Thread` có `planted_chapter: 0`.
  - Tag, bối cảnh và hướng đã chọn, nhân vật chính đã sửa đều bọc `UserAuthored`, vì trình duyệt gửi lại chúng (G4).
  - `Naming` chuyển từ bài đo D sang đây, dùng chung một chỗ. `default_naming` theo bảng design §4.1. Thể loại ngoài bảng dùng tên Việt, địa danh hư cấu.
- **Hệ quả:** chưa kiểm bằng code tên có đúng kiểu Hán Việt hay Việt; điều này chỉ nằm trong prompt. Chưa kiểm độ dài chữ người chơi sửa (`limits.input.*` đang null, chưa có khoá cho tính cách). Chưa lưu `StoryPlan` vào Postgres. `writer_context` chưa đọc `personality`/`backstory`.
- **Người quyết:** Claude (nhánh pipeline-setup), điều phối duyệt (PR #17) · 20/10/2026

## D-39 · Vai `setup`; JSON sai schema thì thử lại, sai quy tắc thì báo `STORY_SETUP_INVALID`
- **Bối cảnh:** bốn bước khởi tạo cần một model (D-3: các vai cố định nằm trong config) và một cách xử lý khi model trả sai.
- **Quyết định:**
  - Thêm `roles.setup` và `role_reasoning.setup` vào `config/models.yaml`, đều `null`. Gọi qua `require_model`, nên chưa chọn model thì báo `CONFIG_MODEL_NOT_SET`. `llm.role_extra` đổi `role_reasoning.<vai>` thành `extra`, dùng được cho mọi vai.
  - JSON sai schema thử lại theo `retries.extract_schema_retry`, lỗi mạng tạm thời theo `retries.llm_transient` (`with_json_retries`, D-14; lớp lỗi mạng: điều phối yêu cầu, nhánh story-run). Không thêm khoá riêng, vì G11 đã nói "thử lại 1 lần".
  - Sai quy tắc (số lựa chọn, kế hoạch, gói chương 0) báo ngay mã mới `STORY_SETUP_INVALID` (HTTP 502), không tự gọi lại model, để không trừ tiền key người chơi khi chưa hỏi. Câu báo không nói sai ở đâu, vì chi tiết có thể chạm bản kế hoạch ẩn; chi tiết vào log, chỉ ghi id và số chương. **Đã thay một phần (D-54):** ở `build_story`, sai quy tắc thì model được `retries.setup_repair` lượt sửa kèm danh sách lỗi; log chỉ ghi loại lỗi.
  - Không trả nửa vời: có một lỗi là không trả kế hoạch hay gói. Module không ghi gì.
- **Hệ quả:** người chơi phải bấm thử lại khi model sai quy tắc. Muốn tự thử lại thì đổi `retry_on`, cần chủ dự án đồng ý vì tốn tiền.
- **Người quyết:** Claude (nhánh pipeline-setup), điều phối duyệt (PR #17) · 20/10/2026

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
- **Người quyết:** điều phối (yêu cầu); mã công khai: Claude (Session narrator); câu "Bạn chưa biết điều này." vẫn tính một lượt: Chủ dự án đồng ý · 20/10/2026

## D-41 · Router `stories` chỉ mount khi bật cờ dev; dependency mặc định fail closed
- **Bối cảnh:** sổ tay và hỏi người kể cần API trước khi có đăng nhập (tuần 5), nên chưa kiểm được truyện thuộc ai (G10).
- **Quyết định:**
  - `Settings.enable_dev_routes` (`ENABLE_DEV_ROUTES`), mặc định `False`. `create_app` chỉ gắn router khi cờ bật; mỗi route còn kiểm `app.state.dev_routes_enabled`, nên gắn router vào app khác vẫn 404.
  - `GET /stories/{story_id}/notebook` → `NotebookOut` (danh sách trắng, mã công khai, D-40), đọc qua `committed_player_view`. `POST /stories/{story_id}/narrator` nhận `{question}`, trả `{answer}`.
  - Dependency nằm trong `api/deps.py`; test thay bằng `dependency_overrides`. Chưa có nơi lưu key người chơi → LLM mặc định báo `PLAYER_KEY_MISSING`, không bao giờ dùng key chủ dự án. Chưa có nơi lưu `story_plan` → lỗi, không trả lời. Nơi lưu key và kế hoạch: xem D-44.
  - `create_app` đọc `Settings()` và `load_config()` lúc gọi factory (trước đây `Settings()` đọc trong lifespan).
  - Thêm mã `WRITORY_RATE_LIMITED` (429) cho trần mỗi phút của WriTory (G8); bộ đếm: D-56.
- **Hệ quả:** máy chủ thật không có router này tới khi có đăng nhập và kiểm quyền (TODO G10 trong `api/stories.py`). Chi phí hỏi người kể chưa cộng vào trần truyện, vì chưa có nhật ký chi phí.
- **Người quyết:** điều phối (yêu cầu cờ dev, fail closed); cách làm: Claude (Session narrator) · 20/10/2026

## D-42 · Lệnh chạy cả truyện `writory.pipeline.bench_run`; file chung chỉ có chữ người chơi thấy
- **Bối cảnh:** mốc tuần 2 (design §12) là chạy liền nhiều chương từ dòng lệnh; trần chi phí D-47 là số tạm, cần chi phí đo theo vai. D-24 quy ước runner `bench_<x>`.
- **Quyết định:**
  - Tên `writory.pipeline.bench_run`, kết quả `evals/results/<ngày>-run-<nhãn>/` (`bench_run` ↔ `-run-`, như D-24). Giữ tiền tố `bench_` vì lệnh dùng key của chủ dự án và ghi vào `evals/results/`; code app không đọc key đó (D-2, D-41).
  - Đề khai trước ở `evals/scenarios/story_run/`. Mọi bước có 3 lựa chọn chọn bằng `random.Random(seed)`; lựa chọn cuối chương thành `player_action` của chương sau, đúng chữ trên nút. Thiết lập truyện cho mỗi chương: `setup.story_brief` (có quy ước tên, D-32).
  - Cảnh hay bộ lựa chọn bị chặn, model trả sai, mạng lỗi: tự "bấm thử lại" tối đa `player_retries` lần. Trần, key, cấu hình: dừng ngay.
  - Config còn null hay đề thiếu giá: liệt kê hết một lần, trước lời gọi đầu và trước khi kết nối kho (`chapter.config_problems`).
  - File chung (meta, setup, events, chapters, calls, report, summary) chỉ có chữ người chơi thấy, số đếm, mã và loại lỗi. `truth_dump.json` giữ kế hoạch, gói từng chương, đồ thị cuối, dàn ý, góp ý viết lại, chi tiết lỗi.
  - Kho: `GraphStore`, story_id mới mỗi lần chạy; dry-run xoá truyện khi xong, trừ khi có `--keep-story`. Kế hoạch và chi phí giữ trong bộ nhớ rồi ra file; không thêm migration.
- **Hệ quả:** dry-run vẫn cần Docker, vì `writer_context` chỉ có bản Neo4j. Lần chạy thật đầu dùng số chương của kế hoạch Truyện ngắn (4–8 chương), chưa tới mốc "10 chương"; đề Truyện vừa để sau. `--chapters` không vượt kế hoạch. Lựa chọn đã chọn chưa ghi dữ liệu có cấu trúc vào đồ thị (D-37).
- **Người quyết:** hướng đề (tu tiên, tên Hán Việt, địa danh hư cấu, Truyện ngắn, không dùng làng quê bình dị): Chủ dự án duyệt 20/10/2026. Phần còn lại, gồm các số trong đề và việc dùng số chương của kế hoạch: Claude (nhánh story-run), điều phối duyệt · 20/10/2026

## D-43 · Model viết `reasoning: none`; lần chạy giữ chỗ ngân sách bằng `max_tokens`; giữ mọi lượt soát
- **Bối cảnh:** bài D đo GPT-6 Luna với reasoning none, còn runtime dùng mặc định của model (D-36). Trần `--budget` cứng cần chi phí tối đa của từng lời gọi. Báo cáo cần lỗi của mọi lượt soát, kể cả lỗi đã sửa ở lượt viết lại.
- **Quyết định:**
  - `WriterTier.reasoning` (tuỳ chọn, kiểu `ReasoningEffort`, mặc định null); `chapter.py` gửi nó vào lời gọi model viết như `role_extra`. Mức `standard` đặt `none`.
  - `bench_run`: trước mỗi lời gọi giữ chỗ = token vào ước tính × giá vào + `max_tokens_per_call` × giá ra (giá trong đề), và gửi `max_tokens` đó kèm mọi lời gọi của lần chạy. Không giữ chỗ được thì dừng (`COST_LIMIT_STORY`), ghi phần đã có, mã thoát 2. Trần trong config vẫn áp như khi chơi.
  - `ChapterOutcome.reviews`: mọi lượt soát (loại lỗi, mức chặn, cạnh bị bỏ). `ChapterOutcome.error_detail`: chỉ cho log máy chủ.
  - Vai của lời gọi nhận ra qua schema JSON; cảnh nhận qua `CostTracker.start_scene()`.
- **Hệ quả:** lần chạy khác app ở `max_tokens`: app chưa đặt. Giá trong đề phải sửa khi giá OpenRouter đổi. Chưa đo được độ trễ tới chữ đầu, vì pipeline chưa stream.
- **Người quyết:** `reasoning: none` cho mức `standard`: Chủ dự án duyệt 20/10/2026. Phần còn lại, gồm `max_tokens_per_call: 16000` chỉ cho lần chạy: Claude (nhánh story-run), điều phối duyệt · 20/10/2026

## D-44 · Lưu trữ cho API truyện (migration 0003); người chơi dev; nhật ký chi phí theo vai
- **Bối cảnh:** D-41 để `get_story_plan`, `get_narrator_llm` fail closed: chưa có nơi lưu bản kế hoạch và key người chơi, chưa có nhật ký chi phí nên trần mỗi truyện không tính các lần gọi trước. Khởi tạo (design §4.1) cần máy chủ giữ 3 lựa chọn mỗi bước.
- **Quyết định:**
  - `0003_story_api.sql`: `story_plans` (ẩn, không ra API), `stories.brief` (thiết lập người chơi chọn, đề cho mọi chương), `player_keys` (chỉ bản mã hoá Fernet), `setup_sessions`, `llm_costs`, `chapter_choices`, `player_actions`. Hàm ở `db/plans.py`, `keys.py`, `setup.py`, `costs.py`, `choices.py`.
  - Chưa có tài khoản: mọi dòng mang `owner_id = "dev"` (`api/deps.get_owner_id`). Truyện, phiên khởi tạo và key đều đọc theo chủ; của người khác là 404. Tuần 5: tạo bảng tài khoản, đổi các dòng `dev`, thêm FOREIGN KEY từ `owner_id`, và `get_owner_id` đọc phiên đăng nhập.
  - Mỗi lời gọi model ghi một dòng `llm_costs` qua `llm.ledger.RecordingClient`, đặt dưới `MeteredClient`, kể cả khi thiếu `usage.cost`. Vai đoán theo schema JSON (`api/deps.ROLE_OF_SCHEMA`; không schema là `writer`). `CostTracker(story_spent_usd=...)` cộng từ nhật ký. Chi phí khởi tạo tính theo phiên, gắn vào truyện khi tạo xong.
  - `deps.PlayerLLM`: key chỉ được đọc và giải mã khi sắp gọi model, rồi đi thẳng vào client OpenRouter (một `httpx.AsyncClient` chung của app). Không có key thì `PLAYER_KEY_MISSING`, không bao giờ dùng key chủ dự án. Truyện không có kế hoạch: fail closed (500).
- **Hệ quả:** lời gọi lỗi và stream đứt không có dòng chi phí. Thêm schema mới mà quên bảng vai thì nhật ký ghi tên lớp. Cột `model` là model được yêu cầu, không phải model OpenRouter thật sự dùng. Truy vấn Postgres chạy đồng bộ.
- **Người quyết:** Claude (nhánh story-api), điều phối duyệt · 20/10/2026

## D-45 · API key người chơi và API khởi tạo; lỗi 422 không chép lại đầu vào
- **Bối cảnh:** design §4.1, §10; G7. Lỗi 422 mặc định của FastAPI trả `input` của từng lỗi, tức chép lại chữ người chơi gửi lên, kể cả key.
- **Quyết định:**
  - `GET/PUT/DELETE /player/key`: phản hồi chỉ có `has_key`, `last4` (tính sau khi giải mã, không lưu riêng). Key phải bắt đầu bằng `sk-or-` và được bộ lọc log nhận ra trọn vẹn (`safety.crypto.validate_player_key`); sai dạng: mã mới `PLAYER_KEY_INVALID` (422). Chưa gọi OpenRouter để thử key. Bật router dev thì `KeyCipher` dựng lúc tạo app: khoá sai thì app không khởi động (D-11).
  - Lỗi kiểm thân yêu cầu thành mã mới `REQUEST_INVALID` (422) cho mọi route, kèm `fields`: đường dẫn trường sai lấy từ `loc` (`["body","tags","genre"]` → `"tags.genre"`). Không bao giờ có `input`, `ctx` hay giá trị nào; đoạn đường dẫn không có dạng định danh (tên trường lạ, có thể chính là key) thành `"?"` (`api/errors.field_path`). `PLAYER_KEY_INVALID`, `CHARACTER_EDIT_INVALID` cũng kèm `fields`.
  - `/setup`: tạo phiên → POST một bước (trả bộ đã có; chưa có mới gọi model) → PUT `{index}` là số nguyên JSON 0–2 → `finalize`. Đổi lựa chọn bước trước thì xoá các bước sau. Sai thứ tự: mã mới `SETUP_STEP_NOT_READY` (409), không gọi model; phiên của người khác: `SETUP_NOT_FOUND` (404).
  - Sửa nhân vật chính: trường người chơi gửi lên kiểm theo `input.character_name_max_chars`, `personality_max_chars` (khoá mới, 300, số tạm như D-47), `backstory_max_chars`; rỗng hoặc quá dài: mã mới `CHARACTER_EDIT_INVALID` (422).
  - `finalize`: `build_story` → `db.start_story` (truyện + kế hoạch + chương 0; lỗi thì gỡ hết theo `story_id`) → gắn truyện vào phiên. Thiết lập truyện (`pipeline.setup.story_brief`, gồm tên, tính cách, quá khứ nhân vật chính, luôn bọc như dữ liệu) lưu ở `stories.brief`. Hai yêu cầu chốt cùng phiên cùng lúc: lần sau báo `STORY_BUSY` (khoá như D-46).
- **Hệ quả:** bối cảnh, hướng giờ do máy chủ giữ, không còn do trình duyệt gửi lại; vẫn bọc như dữ liệu như D-38. Key dạng khác bị từ chối tới khi sửa bộ lọc log.
- **Người quyết:** Claude (nhánh story-api), điều phối duyệt; tiền tố `sk-or-`, tính cách và quá khứ nhân vật chính trong thiết lập truyện: điều phối duyệt · 20/10/2026

## D-46 · Viết chương qua SSE; lựa chọn và hành động tự viết lưu phía máy chủ
- **Bối cảnh:** design §4.2, §6.2–6.4; D-1, D-6, D-36, D-37. Giao diện cần nhận từng cảnh đã kiểm, và gửi lại lựa chọn bằng id mờ.
- **Quyết định:**
  - `POST /stories/{id}/chapters/next` trả `text/event-stream` qua `fastapi.sse.EventSourceResponse` (FastAPI 0.148, đọc mã nguồn): mỗi sự kiện của `pipeline.events` là một SSE, `event:` là loại, `data:` là JSON; khi rảnh FastAPI gửi dòng chú thích `: ping`. Dùng POST, không GET: `EventSource` của trình duyệt tự nối lại, tức viết lại chương và tốn tiền hai lần; giao diện đọc stream bằng `fetch`.
  - Điều kiện kiểm được trước khi viết nằm trong dependency, trả JSON có status: truyện, chương `pending`, đã quá chương cuối của kế hoạch (mã mới `STORY_COMPLETE`, 409), chương ≥ 2 mà chưa có hành động dẫn tới (mã mới `CHOICE_REQUIRED`, 409), key, trần. Số cảnh lấy `scenes_per_chapter.min` (2); người có mặt đầu chương để dàn ý chọn.
  - Chống chạy đôi (G8): advisory lock mức phiên của Postgres (`db.job_lock`, `pg_try_advisory_lock`) theo `story_id` trên kết nối của yêu cầu, lấy trong dependency có `yield`, giữ tới khi yêu cầu kết thúc (stream xong, lỗi, hay ngắt kết nối). Lần thứ hai báo ngay mã mới `STORY_BUSY` (409), không chờ, không gọi model. Chọn khoá thay cho cột trạng thái vì kết nối đóng hay tiến trình chết thì Postgres tự nhả: không cần hạn giờ để gỡ kẹt.
  - `choices_ready` chỉ phát sau khi bộ lựa chọn đã lưu ở `chapter_choices`. Ngắt kết nối: FastAPI huỷ task chạy chương; pipeline không ghi gì trước `commit_chapter`, và bước đó chạy đồng bộ nên không bị cắt giữa chừng. Chương đã ghi mà chưa có lựa chọn: `POST /stories/{id}/choices` tạo lại (đã có thì trả lại).
  - `POST /stories/{id}/choice {choice_id}` lưu hành động cho chương sau (`player_actions`), kèm lời nói dối, cảm xúc dạng chữ (`api.play.action_text`). `POST /stories/{id}/action {text}` qua `classify_action` + `ensure_in_story` rồi mới lưu. Chọn lại được tới khi viết chương sau.
  - `GET /stories/{id}` (trạng thái để mở lại truyện), `GET /stories/{id}/chapters/{n}` (văn đã hiện). Mã mới `CHOICE_NOT_FOUND`, `CHAPTER_NOT_FOUND` (404).
- **Hệ quả:** `Lie`, `FEELS` của lựa chọn vào đồ thị ở gói chương sau (D-55); dữ liệu cũng vào đề chương sau dạng chữ. Khoá chỉ có tác dụng khi mỗi yêu cầu có kết nối Postgres riêng (khoá lồng được trên cùng kết nối); các đường gọi model còn lại cũng có khoá (D-56). Lời gọi bị huỷ giữa chừng không có dòng chi phí.
- **Người quyết:** Claude (nhánh story-api), điều phối duyệt; POST cho SSE, 2 cảnh mỗi chương, khoá chống chạy đôi: điều phối yêu cầu và duyệt · 20/10/2026

## D-47 · Số tạm cho lần chạy thật đầu: GPT-6 Luna cho mọi vai, trần và ngưỡng ban đầu
- **Bối cảnh:** pipeline (D-36..D-40) dừng ở lỗi cấu hình vì `roles.*`, trần chi phí và ngưỡng còn `null`. Chưa có bài đo riêng cho dàn ý, lựa chọn, người kể, phân loại, người canh, khởi tạo. Bài D đo riêng bước viết của Luna khoảng 0,001 USD một cảnh (`evals/results/2026-10-20-quality-r2/`); cả đường đi chưa đo.
- **Quyết định:**
  - Các vai `outline`, `guard`, `choices`, `narrator`, `classify`, `setup` dùng tạm `openai/gpt-6-luna`, `role_reasoning: low` như vai trích (D-35).
  - Trần chi phí, giới hạn người chơi, `writer_max_neighbors`, ngưỡng người canh: số trong `config/limits.yaml`, `config/guard.yaml`. Trần đặt rộng gấp nhiều lần ước tính, để lần chạy đầu đo được chi phí thật. Khoá `input.personality_max_chars` (D-45) thêm sau, cùng loại số tạm.
  - Ngưỡng kiểm văn (`config/quality.yaml`) lấy đúng số bài D đã dùng (`QualityParams`).
  - Test không còn dựa vào việc config thật để `null`: test "chưa đặt thì báo lỗi" dùng bản config có chỗ `null`.
- **Hệ quả:** mọi số trên là tạm. Sau lần chạy thật đầu (một truyện ngắn tu tiên, trần 0,30 USD), chỉnh theo chi phí và tỉ lệ lỗi đo được rồi ghi quyết định mới.
- **Người quyết:** Claude đề xuất số; Chủ dự án duyệt · 20/10/2026

## D-48 · Tên người chơi tự viết không phải bí mật đối với người chơi (bổ sung D-26)
- **Bối cảnh:** bộ dò lộ (D-26) cấm tên lớp truth mà `player_view` chưa có. Ở chương 0 người chơi chưa biết gì (D-38), nên cảnh chương 1 nêu tên nhân vật chính sẽ bị chặn nếu bộ trích quên hé lộ nhân vật chính, dù tên đó do người chơi chọn hoặc tự viết (lệnh chạy cả truyện, D-42, chỉ ra).
- **Quyết định:**
  - Bộ dò lộ không coi `name` của nút mang `user_authored: true` là tên bị cấm. `aliases` của nút đó vẫn bị dò, vì model có thể gán bí danh bí mật.
  - Quy tắc nằm một chỗ: `safety.leak.leak_names(state)`, đọc `GraphState.named_nodes()` và `nodes()`, nên đúng cho cả Neo4j lẫn `OverlayState`. Mọi nơi gọi bộ dò lộ lấy `truth_names` từ đó: soát cảnh và tạo lựa chọn (`pipeline/chapter.py`), tạo lại lựa chọn (`pipeline/bench_run.py`), hỏi người kể (`api/deps.get_truth_names`).
  - Tên đó không được tính là chữ người chơi đã thấy: tên lớp truth khác trùng một phần chữ vẫn bị cấm như cũ. **Đã thay một phần (D-52):** thiết lập truyện có tên nhân vật chính và được tính là chữ đã thấy.
- **Hệ quả:** nhân vật chính không cần hé lộ trên trang để được gọi tên. `named_nodes` vẫn trả đủ tên lớp truth cho chỗ khác dùng. Nếu bản 3 cho người chơi viết thêm nút (nhập nhân vật bằng đoạn văn), tên các nút đó cũng được miễn theo quy tắc này.
- **Người quyết:** điều phối (quyết định và phạm vi miễn); cách làm: Claude (nhánh story-run) · 20/10/2026

## D-49 · Kế hoạch định trước nhịp: mốc, khoảng gỡ mạch; mục tiêu mỗi chương; trễ hạn; tóm tắt chương trước
- **Bối cảnh:** lần chạy thật đầu (`evals/results/2026-10-20-run-tu-tien-1/notes.md`): hai bí mật chính hết truyện chưa lộ, 4 mạch phải gỡ mới gỡ 1, sáu chương quanh một tình huống. Đề dàn ý và đề viết chưa có mục tiêu của chương, cũng chưa có tóm tắt chương trước (design §6.2 bước 1); kế hoạch chưa định trước mạch nào gỡ ở chương nào.
- **Quyết định:**
  - `StoryPlan`: `must_resolve_threads` là `ThreadPlan` (id, khoảng phải gỡ); thêm `milestones` (bước ngoặt, cao trào, kết; khoảng chương; một câu mục tiêu). Validator: mọi khoảng nằm trong số chương, đúng một mốc kết ở chương cuối, mỗi hồi có mốc hết hạn trong hồi. Kế hoạch cũ (danh sách id, không mốc) vẫn đọc được; khoảng gỡ khi đó lấy trên nút `Thread`.
  - Nhịp theo độ dài: `story_lengths.levels.*.milestones` (min/max) và `max_due_per_chapter` (số bí mật, mạch, mốc có hạn ở cùng một chương), số tạm; `initial_problems` kiểm. **Đã thay một phần (D-54):** không tính chương cuối. Đề `build_story` (`setup-3`) nêu các số này, đặt trước bảng cạnh (`edge_rules`). Khoảng phải gỡ = khoảng dự kiến gỡ model khai cho mạch.
  - `pipeline/pacing.chapter_goals(plan, chapter, state)`: chỉ đọc; "đã lộ" theo player_view, "đã gỡ" theo RESOLVED_IN, hạn theo `guard/plan.py` (một định nghĩa chung với người canh). Tính đầu mỗi cảnh trên nền phủ các cảnh trước; vào đề dàn ý và đề viết, không vào vai phục vụ người chơi (G1). Dòng "trong khoảng lộ" của ngữ cảnh model viết trỏ về mục tiêu của chương. Có một câu chung: "đẩy truyện tới, không lặp tình huống của chương trước".
  - Người canh: `overdue_secret`, `overdue_thread`, chỉ ở cảnh cuối chương, mức viết lại, không bỏ cạnh nào. Bài B thêm ca cho hai loại này.
  - Vai mới `summary` (`pipeline/summary.py`; `roles.summary` GPT-6 Luna, suy luận thấp, tạm như D-47): sau khi ghi chương, một lời gọi JSON tóm tắt chữ đã hiện (bọc dữ liệu, G4), cắt ở cuối câu theo `limits.context.summary_max_chars`, lưu ở `chapter_summaries` (migration 0004), không ra API. Đề dàn ý và đề viết của chương N nhận tóm tắt N-2, N-1 trong khối dữ liệu (`outline-4`, `writer-4`). Lỗi khi tóm tắt chỉ ghi log; chương đã ghi giữ nguyên (D-6), chương sau chạy thiếu và `ChapterOutcome.summaries_missing` ghi lại. Chương cuối không tóm tắt.
- **Hệ quả:** viết lại tối đa 1 lần như D-36. Mốc không kiểm được bằng code. Kế hoạch hỏng nhịp thì `STORY_SETUP_INVALID` (D-39). Mỗi chương (trừ chương cuối) thêm một lời gọi model. Tạo lại lựa chọn qua API không tạo lại tóm tắt.
- **Người quyết:** Chủ dự án (yêu cầu kế hoạch định trước khoảng gỡ mạch và mốc, nhịp theo độ dài); tóm tắt chương trước và vai `summary`: điều phối yêu cầu; cách làm và số tạm: Claude (nhánh plan-pacing), điều phối duyệt · 20/10/2026

## D-50 · Chương cuối kết truyện, `story_finished`; bản viết lại không làm hỏng bản đầu (bổ sung D-36); report so kế hoạch với kết quả
- **Bối cảnh:** design §4.3. Ở lần chạy thật đầu, chương 6 (chương cuối) vẫn đưa ra 3 lựa chọn. Lệnh chạy cả truyện chưa cho biết bí mật lộ và mạch gỡ ở chương nào. Lượt viết lại (kể cả vì trễ hạn, D-49) có thể sinh lỗi chặn mà bản đầu không có.
- **Quyết định:**
  - `ChapterRun`: chương = `plan.total_chapters` thì ghi chương rồi phát `StoryFinished` (`story_finished`, chỉ có số chương), không gọi model lựa chọn; `ChapterOutcome.finished`. Chương sau đó báo `STORY_COMPLETE` trước lời gọi đầu.
  - Bổ sung D-36: bản cuối còn lỗi mức chặn mà một bản trước của cảnh chỉ có lỗi mức viết lại thì hiện bản trước đó (lượt soát ghi `fallback`, log ghi loại lỗi), không chặn người chơi. Không bản nào thoát lỗi chặn thì vẫn chặn.
  - API: truyện đã kết thì `POST .../choices` trả bộ rỗng, không gọi model; `POST .../choice` và `.../action` báo `STORY_COMPLETE` (không phân loại, G8). `GET /stories/{id}` tính `finished` từ kế hoạch như cũ.
  - `bench_run`: dừng sau chương cuối. `report.json`, `summary.md` thêm `story_finished`, `fallbacks`, `summaries` (tạo, lỗi, số chương chạy thiếu tóm tắt chương trước) và `plan_vs_result`: bí mật và mạch phải gỡ gọi bằng số thứ tự trong kế hoạch, kèm khoảng, chương lộ hay gỡ, đánh giá (`on_time`, `early`, `late`, `missed`, `pending`). Bản có id và chữ (gồm tóm tắt) ở `truth_dump.json`, như D-42.
- **Hệ quả:** khoảng chương và số bí mật, số mạch của kế hoạch có trong file chung (không id, không chữ). Chưa có trang kết (bản 2). Giao diện (tuần 4) phải xử lý `story_finished`.
- **Người quyết:** điều phối (yêu cầu chương cuối; duyệt hiện bản trước); cách làm: Claude (nhánh plan-pacing), điều phối duyệt · 20/10/2026

## D-51 · Kiểm văn sau lần chạy thật đầu: ngôi kể, tên trong kiểm lặp, dàn ý phải là tiếng Việt
- **Bối cảnh:** lần chạy `evals/results/2026-10-20-run-tu-tien-1/` (`notes.md` mục 2, 3, 5): chương 6 đổi sang ngôi thứ ba mà không phép kiểm nào bắt; một dàn ý viết tiếng Trung; kiểm lặp đếm cả tên đồ vật 4 từ. Chưa đề nào nói ngôi kể cho model viết: style guide chỉ dặn "ngôi thứ nhất thì xưng tôi", không chốt ngôi.
- **Quyết định:**
  - Ngôi đã chốt: `quality.narration.person` (`config/quality.yaml`), hiện `first`. Model viết nhận câu ngôi kể sinh từ cùng giá trị (`quality.narration_instruction`, nối sau style guide trong system prompt; `writer-2`).
  - `quality.check_narration` trong `check_scene`: đếm "tôi" trên 100 từ lời kể (bỏ dòng thoại "- " và chữ trong ngoặc kép); lệch ngưỡng là lỗi `narration_person`, mức viết lại. Ngưỡng tạm trong config, đặt giữa các cảnh ngôi thứ nhất (chương 1–5) và ngôi thứ ba (chương 6, truyện mẫu) của lần chạy trên. Chế độ `third` dùng cho truyện mẫu và văn thử.
  - `check_repetition(names=...)`: mỗi chỗ tên hay biệt danh thực thể (danh mục và player_view của chương đã commit, `chapter.entity_names`) tính là một từ.
  - Dàn ý có trường lẫn chữ khác hệ (`scene.outline_foreign_script`) là sai schema, thử lại theo D-14; đề dàn ý dặn viết tiếng Việt (`outline-2`).
- **Hệ quả:** đổi ngôi một đoạn ngắn giữa cảnh có thể lọt, vì đo trên cả cảnh. "ta" trong lời kể không tính là ngôi thứ nhất. Cụm lặp không phải tên ("trận quanh linh mạch") vẫn bị bắt. Config thử của test đặt `third` vì văn thử lấy từ truyện mẫu. Bài D không chạy ngôi kể (ngôi theo từng case).
- **Người quyết:** Claude (nhánh run1-fixes), điều phối duyệt (PR #23). Ngôi thứ nhất theo ghi chú chấm tay của chủ dự án (style guide v2); chốt cho cả bản 1: chờ chủ dự án xác nhận · 20/10/2026

## D-52 · Bộ dò lộ: thiết lập truyện người chơi đã đọc là chữ đã thấy (bổ sung D-26, thay một phần D-48)
- **Bối cảnh:** `notes.md` mục 4: chương 1 bị viết lại vì "Huyền Sát Tông", "Tín Vật Huyền Nguyệt", "động linh mạch". Bối cảnh, hướng truyện, nhân vật chính đã chọn là chữ người chơi đọc lúc khởi tạo (G1, D-37, D-45), nhưng bộ dò chỉ tính `player_view`.
- **Quyết định:**
  - `check_leaks`, `ensure_no_leak`, `make_choices`, `ask_narrator` nhận bắt buộc `story_brief` (`setup.story_brief`, lưu ở `stories.brief`). Một chỗ, `leak._seen_text`, cộng nó vào chữ đã thấy, chỉ cho phần tên; nhóm `leak_terms` không đổi.
  - Nơi gọi: soát cảnh và tạo lựa chọn (`chapter.py`, `ChapterRequest.story_brief`), tạo lại lựa chọn (`bench_run.py`, `api/play.py`), hỏi người kể (`api/stories.py`); API đọc qua `deps.get_story_brief`, truyện không có thì "" (chỉ chặt hơn).
- **Hệ quả:**
  - Đo lại: thiết lập thật của lần chạy không có ba tên trên (chỉ có "tín vật", "linh mạch" viết thường; tên tính theo từ viết hoa), nên sửa này không bỏ được ba lượt viết lại đó. Nguyên nhân thật: bộ trích không hé lộ thực thể ở lần đầu cảnh nêu tên (`test_leak.py::test_run1_names_absent_from_its_setup_text_still_leak`).
  - Từ trong tên nhân vật chính và chữ người chơi tự gõ (quá khứ, tính cách) giờ là chữ đã thấy: tên hay biệt danh chỉ gồm các từ đó không còn bị cấm theo tên.
  - Tên ghép từ từ thường ("Động Linh Mạch" trùng "chấn động linh mạch") chưa sửa: mọi cách gọn tìm được đều bỏ bắt một kiểu viết tên thật (chữ thường có dấu). Hướng đề xuất ở `docs/security.md`, mục Chưa giải quyết.
- **Người quyết:** Claude (nhánh run1-fixes), điều phối duyệt (PR #23) · 20/10/2026

## D-53 · Bài E: hỏi người kể không lộ; câu thô tách khỏi câu cuối, bộ chấm chặt hơn lớp chặn
- **Bối cảnh:** hỏi người kể có ba lớp chặn: context chỉ từ `player_view` với mã công khai (G1), kiểm `entry_ids`, bộ dò lộ (G2) (D-40). Chưa có bài đo nào cho biết các lớp đó chặn tới đâu trước câu hỏi cố moi bí mật.
- **Quyết định:**
  - Runner `writory.pipeline.bench_e` (D-24). Đề khai trước ở `evals/scenarios/narrator/`: câu hỏi sáu loại a–f theo chương truyện mẫu, kế hoạch và chuỗi cấm, tham số chạy và giám khảo.
  - `pipeline.narrator.ask_narrator_reply` chạy đúng các bước của `ask_narrator` và trả thêm câu thô (`NarratorOutput`) cùng lý do bị thay (`BlockReason`). `ask_narrator` chỉ lấy `answer` của nó. Câu thô không bao giờ tới người chơi hay vào log.
  - Bộ chấm chặt hơn lớp chặn đang đo: tên lớp truth đầy đủ (`named_nodes` của cả 5 chương, không dùng `leak_names`), kế hoạch cộng nhóm và bí mật chỉ của bộ chấm, tên thật của nút chưa hé lộ kể cả tên chữ thường. Lộ ở câu cuối khác 0 là lỗi nghiêm trọng (mã thoát 4).
  - Trạng thái truyện dựng bằng `OverlayState` từ gói dựng tay, không cần Neo4j. Không áp trần số câu mỗi chương (G8 có test riêng). Truyện mẫu không qua bước khởi tạo, nên `story_brief` khai rỗng.
  - Giám khảo Sonnet là tuỳ chọn và chỉ chấm câu cuối khác NOT_KNOWN. Nó thấy sổ tay và câu hỏi, không thấy lớp truth hay tên model. Mỗi lượt chấm một lần, không fallbacks.
- **Hệ quả:** kế hoạch của truyện mẫu là giả định (khi chơi, kế hoạch do bước khởi tạo sinh, D-38), nên số đo chỉ đúng cho kế hoạch kiểu đó. Bộ chấm có thể báo nhầm khi câu trả lời nhắc lại chữ của câu hỏi; lượt như vậy được đánh dấu `echo`. Chưa chạy thật.
- **Người quyết:** Claude (nhánh bench-e), điều phối duyệt (PR #24) · 20/10/2026

## D-54 · Khởi tạo: code chuẩn hoá id, một lượt sửa khi sai quy tắc, luật nhịp không tính chương cuối (thay một phần D-39 và D-49)
- **Bối cảnh:** lần chạy thật thứ 2 (`evals/results/2026-10-20-run-tu-tien-2/`, chỉ có trên máy chủ dự án, chưa commit) dừng ở `build_story`, cả hai lượt `STORY_SETUP_INVALID`: lượt 1 có id không khớp `ID_PATTERN` (`nodes.21.id`, `edges.37–40.from`, `edges.41.to`, `secrets.1.fact_id`; có lẽ chữ có dấu hoặc khoảng trắng), lượt 2 "chương 5 có 5 việc đến hạn, tối đa 3". Lần chạy 1 cũng hỏng 1/2 lượt khởi tạo. D-39 không cho tự gọi lại model khi sai quy tắc.
- **Quyết định:**
  - Id sai dạng thì code sửa, không gọi lại model: `setup.normalize_ids` chạy trên đầu ra model trước mọi phép kiểm. Id không khớp `ID_PATTERN` đổi bằng `normalize_id` (bỏ dấu, đ → d, chữ thường, khoảng trắng và ký tự lạ thành `_`, cắt còn `ID_MAX_LEN`), một ánh xạ cho chỗ khai và mọi chỗ nhắc tới. Id đã khớp giữ nguyên; `protagonist` không bao giờ đổi. Hai id khác nhau ra cùng một id thì không gộp, là lỗi loại `id`. Đề nêu dạng `SAFE_ID_PATTERN`, ví dụ sinh bằng cùng hàm (`setup-4`).
  - Thay một phần D-39: `build_story` sai quy tắc (pydantic sau chuẩn hoá, hoặc `initial_problems`) thì gọi model sửa tối đa `retries.setup_repair` lượt (`config/limits.yaml`). Vai user nhận thêm câu trả lời trước (khối `previous_answer`) và danh sách lỗi (`escape_text`); system không đổi. Thử lại JSON sai schema (D-14) vẫn tính riêng ở từng lời gọi. Vẫn sai thì `SetupInvalidError` (`STORY_SETUP_INVALID`): `detail`, phần vào log, chỉ có loại lỗi; danh sách có id ở `problems`. Ba bước đề xuất vẫn theo D-39.
  - Thay một phần D-49: luật `max_due_per_chapter` không tính chương cuối, vì chương kết gỡ nhiều mạch cùng lúc. Đề nêu số lấy từ config và câu "trừ chương cuối".
  - `bench_run`: report và summary có `setup_repairs` (số lượt sửa, số lỗi theo loại); danh sách lỗi có id chỉ ở truth_dump.
- **Hệ quả:** mỗi lượt sửa là một lời gọi `build_story` nữa trên key người chơi, đầu vào dài hơn (kèm câu trả lời trước), qua cùng `MeteredClient` nên tính vào trần như mọi lời gọi. Log API không còn id của lỗi khởi tạo. Chương cuối được dồn nhiều hạn. Chưa đo lượt sửa với model thật.
- **Người quyết:** Chủ dự án (lượt sửa, luật chương cuối); Claude (chuẩn hoá id) · 20/10/2026

## D-55 · Lựa chọn của người chơi có tác động vào đồ thị (bổ sung D-37 và D-46)
- **Bối cảnh:** D-37, D-46 ghi lựa chọn nói dối và nội tâm chưa vào đồ thị: chương sau chỉ nhận chữ của lựa chọn.
- **Quyết định:**
  - Người chơi chọn ở cuối chương N; tác động thuộc gói của chương N+1 (D-21) và được ghi cùng chương đó khi nó commit. Bấm chọn không ghi gì lên đồ thị, nên chọn lại trước khi viết là thay.
  - `pipeline.choices.choice_effects` (hàm thuần): nói dối → nút `Lie` (id `lie:<choice_id>`, `chapter` = N+1), cạnh `TOLD` (nhân vật chính → Lie), `TOLD_TO` (Lie → từng người nghe còn sống), `ABOUT` (Lie → mục nói tới); nội tâm → `FEELS` mang `feeling`, đóng `FEELS` cũ cùng đích. Nói thật, im lặng, hành động: graph-schema không có chỗ cho chúng nên không ghi, chỉ chữ vào đề chương.
  - Tác động là phần mở đầu của gói chương (`ChapterRequest.choice`): người canh, bộ trích và `OverlayState` thấy từ cảnh 1; danh mục thực thể có nút `Lie`, nên một cảnh ghi được "Lan biết đó là dối". `merge_scene_packages(prelude=…)` gộp nó với các cảnh.
  - Id lựa chọn nhắc tới mà đồ thị không có: dừng trước khi gọi model (`INTERNAL_ERROR`). Người nghe đã chết bị bỏ; không ai nghe được thì lời dối không ghi (ghi log id, không chữ).
- **Hệ quả:** lời dối vào sổ tay (`player_view.lies`) từ chương N+1, kể cả khi văn chương đó không tả lúc nói (người chơi đã chọn nói); chữ của nó đã qua `check_leaks` lúc tạo lựa chọn (D-37). `FEELS` chưa vào `player_view` (D-16). Ô tự viết không có dữ liệu có cấu trúc nên không tác động. `bench_run` truyền lựa chọn, nên chạy liền nhiều chương cũng ghi tác động.
- **Người quyết:** Claude (nhánh choice-effects), chờ điều phối duyệt · 20/10/2026

## D-56 · Khoá chống chạy đôi cho mọi đường gọi model; bộ đếm lời gọi mỗi phút (bổ sung D-46)
- **Bối cảnh:** D-46 chỉ khoá viết chương và chốt khởi tạo; hỏi người kể, tạo lại lựa chọn, ô tự viết và tạo lựa chọn khởi tạo gọi song song thì key người chơi bị trừ tiền hai lần. `WRITORY_RATE_LIMITED` (D-41) chưa có bộ đếm.
- **Quyết định:**
  - Khoá `story` (cùng khoá viết chương) cho `POST /stories/{id}/choices` và `/action`. Khoá `narrator` riêng cho hỏi người kể, vì hỏi người kể không mất lượt truyện (design §6.6): được hỏi khi chương đang viết, chỉ không được hỏi hai câu cùng lúc. Khoá `setup` cho ba bước tạo lựa chọn khởi tạo, chung với chốt. Lần hai: `STORY_BUSY`, không gọi model.
  - Bộ đếm: bảng `llm_call_windows` (migration 0005), `db.take_llm_call`, cửa sổ cố định một phút theo `owner_id`, một câu lệnh kiểm và tăng cùng lúc. Giới hạn `rate_limit.llm_calls_per_minute_per_user`; null → `CONFIG_LIMIT_NOT_SET`.
  - `llm.ratelimit.RateLimitedClient` bọc client thật trong `PlayerLLM.open`, nên mọi lời gọi của API, kể cả lần thử lại, xin một lượt trước khi tới model. Hết lượt: `WRITORY_RATE_LIMITED` (429), không thử lại, không tốn tiền, không có dòng nhật ký chi phí. Giờ qua `deps.get_clock` để test dùng đồng hồ giả.
- **Hệ quả:** cửa sổ cố định cho phép tới 2 × giới hạn quanh ranh giới phút. Một chương (trừ chương cuối) cần từ 11 lời gọi, gồm kiểm duyệt (D-58), thêm 3 mỗi lần viết lại cảnh; hết lượt giữa chương thì chương dừng như mọi lỗi trước bước ghi (G11) và phải viết lại từ đầu, các lời gọi đã chạy vẫn tốn tiền. Lượt đã giữ không trả lại khi lời gọi lỗi. Câu hỏi người kể bị từ chối vì bận không tốn lượt hỏi của chương.
- **Người quyết:** Claude (nhánh choice-effects), chờ điều phối duyệt · 20/10/2026

## D-57 · Kiểm duyệt nội dung (G9): danh mục trong config, model báo loại, code quyết định
- **Bối cảnh:** G9 chưa có lớp nào. Chưa xác nhận Llama Guard hay OpenAI moderation hỗ trợ tiếng Việt, G5 cấm regex cho ý định, và chủ dự án quan tâm cả nội dung chính trị nhạy cảm và tuyên truyền.
- **Quyết định:**
  - `config/moderation.yaml`, **BẢN NHÁP chờ chủ dự án duyệt**. Bảy loại cố định trong code (`safety/categories.py`), ba mức xử lý: `hard_block` (tình dục liên quan trẻ vị thành niên; config không hạ được, kiểm lúc nạp), `block` (hướng dẫn gây hại dùng được ngoài đời thật, kích động nhắm vào nhóm người thật, tuyên truyền hay xuyên tạc nhắm vào người hoặc tổ chức có thật), `darkness_limited` (bạo lực, máu me, tình dục giữa người trưởng thành) cho tới trần của mức u tối và một trần tuyệt đối. Chữ mô tả loại nằm trong config và đi vào prompt.
  - `safety.moderate.moderate`: một lời gọi `chat_json` (vai mới `moderate`, tạm GPT-6 Luna suy luận thấp theo D-47). Model chỉ báo `findings` (loại + mức độ miêu tả); `decide` quyết bằng code: chặn cứng > chặn > vượt trần u tối > cho qua. Chữ bọc thành dữ liệu (G4), kể cả cảnh do model viết. Fail closed như G5. Log chỉ ghi nguồn, kết luận và tên loại, không ghi chữ hay `reason`.
  - Đầu vào (ô tự viết, câu hỏi người kể, phần người chơi sửa của nhân vật chính, tag): chỉ kiểm `hard_block` và `block`, vì hành động người chơi viết là điều nhân vật làm, còn mức miêu tả do model viết. Bị chặn thì `INPUT_BLOCKED` (một câu trung tính, không nêu loại), không lưu, không gọi model nào khác, không mất lượt hỏi người kể. Chạy sau kiểm độ dài.
  - Đầu ra: xem D-58.
- **Hệ quả:** thêm một lời gọi cho mỗi đầu vào của người chơi. Nhãn `forbidden_content` của G5 (D-27) giữ nguyên; kiểm duyệt chạy trước nên G5 thành lớp thứ hai cho ô tự viết. Độ chính xác của model chưa đo (`writory.safety.bench_g9`). Nghị định 147/2024/NĐ-CP vẫn là câu hỏi mở (security.md), không kết luận ở đây.
- **Người quyết:** Claude (nhánh moderation-g9), điều phối duyệt; danh mục chờ Chủ dự án duyệt · 20/10/2026

## D-58 · Kiểm duyệt đầu ra: gắn vào lượt soát cảnh và bộ lựa chọn; mức u tối chưa đọc được từ tag
- **Bối cảnh:** D-36 cho viết lại cảnh một lần; D-37 không tự viết lại bộ lựa chọn bị dò lộ chặn. Tag "mức u tối" là chữ người chơi tự gõ (design §4.1), chưa có bước đổi nó thành một mức trong config.
- **Quyết định:**
  - Cảnh: sau dò lộ, cùng lượt soát, một lời gọi `moderate` trên đúng chữ sẽ hiện. Mỗi loại vi phạm là một lỗi mức chặn của lượt soát (nguồn `moderation`), đi cùng luồng D-36/D-50: viết lại một lần kèm lời nhắn nêu loại và trần (không trích lại chữ); còn vi phạm thì không hiện cảnh; có bản sạch trước đó thì hiện bản đó. Cảnh bị chặn dùng chung `SCENE_LEAK_BLOCKED` (câu trung tính, không nói lý do).
  - Bộ lựa chọn: `make_choices` nhận cổng `moderate` và kiểm mọi chữ người chơi thấy (chữ lựa chọn, nội dung lời nói dối, cảm xúc). Vi phạm thì không hiện bộ nào (`CHOICES_LEAK_BLOCKED`), không tự viết lại; người chơi bấm thử lại. Cả pipeline lẫn `POST /stories/{id}/choices` truyền cổng.
  - Mức u tối: `ChapterRequest.darkness_level` (khoá trong `moderation.darkness_levels`, None = `default_darkness_level`). Đường chơi chưa lưu mức theo truyện nên dùng mặc định.
  - Chi phí: thêm một lời gọi mỗi lượt soát cảnh và mỗi bộ lựa chọn. Cách rẻ hơn, chưa làm: gộp báo loại vào lời gọi của bộ trích (nó đã đọc đúng chữ cảnh); đánh đổi là đổi một prompt đã đo ở bài C.
- **Hệ quả:** lời gọi `moderate` tính vào trần cảnh/chương/truyện (G8), vào nhật ký chi phí với vai `moderate`, và vào bộ đếm lời gọi mỗi phút (D-56), vì nó tốn tiền key người chơi: mỗi đầu vào của người chơi tốn thêm một lượt đếm (ô tự viết: kiểm duyệt rồi phân loại là hai lượt), mỗi lượt soát cảnh và mỗi bộ lựa chọn thêm một lượt. **Chủ dự án cần quyết:** mức u tối là lựa chọn có sẵn ở bước khởi tạo (cần đổi design §4.1 và thêm cột lưu theo truyện), hay model đọc tag chữ tự do.
- **Người quyết:** Claude (nhánh moderation-g9), điều phối duyệt · 20/10/2026

## D-59 · Hỏi người kể: sổ tay lớn thì chỉ gửi phần liên quan tới câu hỏi
- **Bối cảnh:** `ask_narrator` đưa cả sổ tay vào context. Truyện tới 60 chương (`config/story_lengths.yaml`) có sổ tay hàng trăm mục: tốn token và loãng. Bài E lần 1 (`evals/results/2026-10-20-narrator-luna-1/`) chỉ có sổ tay vài chục mục.
- **Quyết định:**
  - `pipeline/notebook.py` (`select_notebook`): vượt `limits.narrator_notebook` (số mục hoặc số ký tự) thì chọn mục có chữ hiện hoặc biệt danh trùng câu hỏi (bỏ dấu, trọn từ), vài mục khớp từ khoá hiếm (điểm IDF), hàng xóm 1-2 bước theo `about` hai chiều, và luôn kèm các mục và lời nói dối gần đây nhất. Không vector DB.
  - G1 giữ nguyên: hàm chỉ nhận `PlayerView`, nên lọc theo `player_view` trước, truy hồi sau, không thể chạm lớp truth. Mã công khai lấy từ sổ tay đầy đủ nên ổn định; mã model dẫn mà không nằm trong phần đã gửi bị coi là mã sai (`unknown_ref`).
  - Số tạm trong `config/limits.yaml`: 80 mục, 16000 ký tự, 10 mục gần đây, 8 mục theo từ khoá. Dưới ngưỡng thì context y hệt trước đây.
- **Hệ quả:** mục tin cậy phụ thuộc truy hồi: câu hỏi dùng chữ khác sổ tay (ví dụ "thanh kiếm" so với "Thanh Sương") có thể không kéo được mục, khi đó người kể trả "Bạn chưa biết điều này." oan (an toàn, không lộ). Bài E bản 2 có nhóm câu trên sổ tay lớn để đo điều này (D-60). Embedding đáng làm khi đo cho thấy trượt vì từ vựng; chưa làm.
- **Người quyết:** Claude (nhánh narrator-retrieval), chờ điều phối duyệt · 20/10/2026

## D-60 · Bài E bản 2: đề mới không sửa đè, nhóm sổ tay lớn, truyện do pipeline viết
- **Bối cảnh:** bài E lần 1 (`evals/results/2026-10-20-narrator-luna-1/`) lộ 0/216, nhưng có một câu gán nhãn sai, chưa đủ câu khó loại c và e, sổ tay chỉ vài chục mục nên chưa đo truy hồi (D-59), và kế hoạch truyện mẫu viết tay nên chưa đo bộ dò lộ với `leak_terms` do model khởi tạo đặt.
- **Quyết định:**
  - Đề v2 là file mới `questions-v2.yaml` (chọn bằng `--questions-file`); v1 giữ nguyên, test kiểm hash khớp lần chạy đầu. Sửa nhãn `c2-d-lop-su-that` thành loại a. Thêm câu loại c, e khó hơn và nhóm `pad: true` chạy trên sổ tay cộng mục đệm sinh bằng code (tất định).
  - `bench_e` nhận truyện do `bench_run` viết: `plan-*.yaml` có `run_dir`, kế hoạch, gói và `story_brief` lấy từ thư mục đó (`pipeline/bench_e_story.py`). Đề cho `run-tu-tien-1` đã soạn trước khi chạy.
  - Bộ chấm: tên đã nằm trong chữ sổ tay không bị coi là lộ (như bộ dò lộ lúc chạy), vì truyện do model viết hay nhắc tên một nút chưa hé lộ ngay trong chữ của mục khác. Bí mật thêm của bộ chấm được có khoảng lộ sau chương cuối.
  - Model giả: `oracle` chỉ trả lời điều nó thấy; `leaker` lấy chữ từ `leak_terms` của kế hoạch khi truyện do pipeline viết.
- **Hệ quả:** bộ dò lộ lúc chạy (`safety/leak.py`) chỉ áp `leak_terms` khi chương < `reveal_from_chapter`. Ở tu-tien-1 hai bí mật có khoảng lộ 3-6 và 4-6 mà chưa hề hé lộ, nên từ chương 3-4 người kể có thể nói ra chúng mà không bị chặn theo cụm từ (chỉ còn quy tắc tên riêng). Đường người kể và lựa chọn chỉ dùng chữ của `player_view` nên có thể chặn mọi bí mật chưa hé lộ; cần chủ dự án quyết có đổi không. Chưa chạy thật.
- **Người quyết:** Claude (nhánh narrator-retrieval), chờ điều phối duyệt · 20/10/2026
