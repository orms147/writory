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
- **Bối cảnh:** bản thiết kế đầu dùng một tên tạm.
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
  - Tên chỉ bị cấm khi có từ viết hoa (tên riêng) mà người chơi chưa thấy trong `PlayerView`. **Đã thay một phần (D-61):** chỉ tên bí mật (tên thật bị giấu sau biệt danh, tên trong `Secret.protects`) bị cấm; tên khác trang nêu thì code tự hé lộ (D-62).
  - Bí mật của `story_plan` chưa tới khoảng lộ và chưa được hé lộ (kể cả lộ sớm do lựa chọn): nhóm `leak_terms` trúng khi mọi cụm cùng nằm trong một câu. Bí mật không có `leak_terms` thì ghi cảnh báo. **Đã thay một phần (D-61):** chỉ văn cảnh (`scope="scene"`) xét khoảng lộ; người kể và lựa chọn dò mọi bí mật chưa có trong `player_view`.
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
  - `build_story` trả `StoryPlan` + gói chương 0, kiểm bằng `initial_problems` (luật: graph-schema.md, mục Chương 0). Nhân vật chính do code dựng từ chữ người chơi, id `protagonist`, `user_authored: true`. Nhân vật chính không `KNOWS` gì, chỉ có một `REVEALED_TO_PLAYER` của chính nó tới `ch0` (D-74); `KNOWS` khác có `how: "tự biết"`. Mạch của kế hoạch là nút `Thread` có `planted_chapter: 0`. **Đã thay một phần (D-76):** model ghi `protagonist` vào `known_by` thì code bỏ cạnh đó, không còn là lỗi.
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
  - `choices_ready` chỉ phát sau khi bộ lựa chọn đã lưu ở `chapter_choices`. Ngắt kết nối: FastAPI huỷ stream, đường đi chạy trong task riêng bị huỷ và được chờ dừng hẳn trước khi nhả khoá (D-63); pipeline không ghi gì trước `commit_chapter`, và bước đó chạy đồng bộ nên không bị cắt giữa chừng. Chương đã ghi mà chưa có lựa chọn: `POST /stories/{id}/choices` tạo lại (đã có thì trả lại).
  - `POST /stories/{id}/choice {choice_id}` lưu hành động cho chương sau (`player_actions`), kèm lời nói dối, cảm xúc dạng chữ (`api.play.action_text`). `POST /stories/{id}/action {text}` qua `classify_action` + `ensure_in_story` rồi mới lưu. Chọn lại được tới khi viết chương sau.
  - `GET /stories/{id}` (trạng thái để mở lại truyện), `GET /stories/{id}/chapters/{n}` (văn đã hiện). Mã mới `CHOICE_NOT_FOUND`, `CHAPTER_NOT_FOUND` (404).
- **Hệ quả:** `Lie`, `FEELS` của lựa chọn vào đồ thị ở gói chương sau (D-55); dữ liệu cũng vào đề chương sau dạng chữ. Khoá chỉ có tác dụng khi mỗi yêu cầu có kết nối Postgres riêng (khoá lồng được trên cùng kết nối); các đường gọi model còn lại cũng có khoá (D-56). Lời gọi bị huỷ giữa chừng ghi chi phí tối đa, đánh dấu ước tính (D-64).
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
  - Bộ dò lộ không coi `name` của nút mang `user_authored: true` là tên bị cấm. `aliases` của nút đó vẫn bị dò, vì model có thể gán bí danh bí mật. **Đã thay một phần (D-61):** biệt danh đó chỉ bị cấm khi là tên bí mật (nút nằm trong `Secret.protects`, hoặc tên bị giấu sau biệt danh).
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
- **Người quyết:** Claude (nhánh run1-fixes), điều phối duyệt (PR #23). Ngôi thứ nhất theo ghi chú chấm tay của chủ dự án (style guide v2); chốt cho cả bản 1: Claude chọn, chủ dự án uỷ quyền (21/10/2026) · 20/10/2026

## D-52 · Bộ dò lộ: thiết lập truyện người chơi đã đọc là chữ đã thấy (bổ sung D-26, thay một phần D-48)
- **Bối cảnh:** `notes.md` mục 4: chương 1 bị viết lại vì "Huyền Sát Tông", "Tín Vật Huyền Nguyệt", "động linh mạch". Bối cảnh, hướng truyện, nhân vật chính đã chọn là chữ người chơi đọc lúc khởi tạo (G1, D-37, D-45), nhưng bộ dò chỉ tính `player_view`.
- **Quyết định:**
  - `check_leaks`, `ensure_no_leak`, `make_choices`, `ask_narrator` nhận bắt buộc `story_brief` (`setup.story_brief`, lưu ở `stories.brief`). Một chỗ, `leak._seen_text`, cộng nó vào chữ đã thấy, chỉ cho phần tên; nhóm `leak_terms` không đổi.
  - Nơi gọi: soát cảnh và tạo lựa chọn (`chapter.py`, `ChapterRequest.story_brief`), tạo lại lựa chọn (`bench_run.py`, `api/play.py`), hỏi người kể (`api/stories.py`); API đọc qua `deps.get_story_brief`, truyện không có thì "" (chỉ chặt hơn).
- **Hệ quả:**
  - Đo lại: thiết lập thật của lần chạy không có ba tên trên (chỉ có "tín vật", "linh mạch" viết thường; tên tính theo từ viết hoa), nên sửa này không bỏ được ba lượt viết lại đó. Nguyên nhân thật: bộ trích không hé lộ thực thể ở lần đầu cảnh nêu tên (`test_leak.py::test_run1_names_are_not_secret_with_or_without_setup_text`, hành vi đổi theo D-61).
  - Từ trong tên nhân vật chính và chữ người chơi tự gõ (quá khứ, tính cách) giờ là chữ đã thấy: tên hay biệt danh chỉ gồm các từ đó không còn bị cấm theo tên.
  - Tên ghép từ từ thường ("Động Linh Mạch" trùng "chấn động linh mạch") chưa sửa: mọi cách gọn tìm được đều bỏ bắt một kiểu viết tên thật (chữ thường có dấu). Hướng đề xuất ở `docs/security.md`, mục Chưa giải quyết. **Đã thay một phần (D-61):** tên không bí mật không còn bị cấm, nên báo nhầm này chỉ còn với tên bí mật.
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
  - Thay một phần D-39: `build_story` sai quy tắc (pydantic sau chuẩn hoá, hoặc `initial_problems`) thì gọi model sửa tối đa `retries.setup_repair` lượt (`config/limits.yaml`). Vai user nhận thêm câu trả lời trước (khối `previous_answer`) và danh sách lỗi (`escape_text`); system không đổi. Thử lại JSON sai schema (D-14) vẫn tính riêng ở từng lời gọi. Vẫn sai thì `SetupInvalidError` (`STORY_SETUP_INVALID`): `detail`, phần vào log, chỉ có loại lỗi; danh sách có id ở `problems`. Ba bước đề xuất vẫn theo D-39. **Đã thay một phần (D-76):** `KNOWS` của nhân vật chính ở chương 0 không còn là lỗi quy tắc: code bỏ sau chuẩn hoá id, không tốn lượt sửa.
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
  - `config/moderation.yaml` (chủ dự án duyệt danh mục 21/10/2026). Bảy loại cố định trong code (`safety/categories.py`), ba mức xử lý: `hard_block` (tình dục liên quan trẻ vị thành niên; config không hạ được, kiểm lúc nạp), `block` (hướng dẫn gây hại dùng được ngoài đời thật, kích động nhắm vào nhóm người thật, tuyên truyền hay xuyên tạc nhắm vào người hoặc tổ chức có thật), `darkness_limited` (bạo lực, máu me, tình dục giữa người trưởng thành) cho tới trần của mức u tối và một trần tuyệt đối. Chữ mô tả loại nằm trong config và đi vào prompt.
  - `safety.moderate.moderate`: một lời gọi `chat_json` (vai mới `moderate`, tạm GPT-6 Luna suy luận thấp theo D-47). Model chỉ báo `findings` (loại + mức độ miêu tả); `decide` quyết bằng code: chặn cứng > chặn > vượt trần u tối > cho qua. Chữ bọc thành dữ liệu (G4), kể cả cảnh do model viết. Fail closed như G5. Log chỉ ghi nguồn, kết luận và tên loại, không ghi chữ hay `reason`. **Đã thay một phần (D-79):** đầu vào kiểm `moderation.input_votes` lần, bộ lựa chọn chấm từng dòng.
  - Đầu vào (ô tự viết, câu hỏi người kể, phần người chơi sửa của nhân vật chính, tag): chỉ kiểm `hard_block` và `block`, vì hành động người chơi viết là điều nhân vật làm, còn mức miêu tả do model viết. Bị chặn thì `INPUT_BLOCKED` (một câu trung tính, không nêu loại), không lưu, không gọi model nào khác, không mất lượt hỏi người kể. Chạy sau kiểm độ dài.
  - Đầu ra: xem D-58.
- **Hệ quả:** thêm một lời gọi cho mỗi đầu vào của người chơi. Nhãn `forbidden_content` của G5 (D-27) giữ nguyên; kiểm duyệt chạy trước nên G5 thành lớp thứ hai cho ô tự viết. Độ chính xác của model chưa đo (`writory.safety.bench_g9`). Nghị định 147/2024/NĐ-CP vẫn là câu hỏi mở (security.md), không kết luận ở đây.
- **Người quyết:** Claude (nhánh moderation-g9), điều phối duyệt; danh mục: Chủ dự án duyệt 21/10/2026 · 20/10/2026

## D-58 · Kiểm duyệt đầu ra: gắn vào lượt soát cảnh và bộ lựa chọn; mức u tối chưa đọc được từ tag
- **Bối cảnh:** D-36 cho viết lại cảnh một lần; D-37 không tự viết lại bộ lựa chọn bị dò lộ chặn. Tag "mức u tối" là chữ người chơi tự gõ (design §4.1), chưa có bước đổi nó thành một mức trong config.
- **Quyết định:**
  - Cảnh: sau dò lộ, cùng lượt soát, một lời gọi `moderate` trên đúng chữ sẽ hiện. Mỗi loại vi phạm là một lỗi mức chặn của lượt soát (nguồn `moderation`), đi cùng luồng D-36/D-50: viết lại một lần kèm lời nhắn nêu loại và trần (không trích lại chữ); còn vi phạm thì không hiện cảnh; có bản sạch trước đó thì hiện bản đó. Cảnh bị chặn dùng chung `SCENE_LEAK_BLOCKED` (câu trung tính, không nói lý do).
  - Bộ lựa chọn: `make_choices` nhận cổng `moderate` và kiểm mọi chữ người chơi thấy (chữ lựa chọn, nội dung lời nói dối, cảm xúc). Vi phạm thì không hiện bộ nào (`CHOICES_LEAK_BLOCKED`), không tự viết lại; người chơi bấm thử lại. Cả pipeline lẫn `POST /stories/{id}/choices` truyền cổng. **Đã thay một phần (D-79):** mỗi chuỗi một dòng đánh số, chấm từng dòng trong cùng một lời gọi.
  - Mức u tối: `ChapterRequest.darkness_level` (khoá trong `moderation.darkness_levels`, None = `default_darkness_level`). Đường chơi chưa lưu mức theo truyện nên dùng mặc định. **Đã thay một phần (D-67):** người chơi chọn sẵn mức lúc khởi tạo, mức lưu theo truyện và đi vào kiểm duyệt mỗi chương.
  - Chi phí: thêm một lời gọi mỗi lượt soát cảnh và mỗi bộ lựa chọn. Cách rẻ hơn (gộp báo loại vào lời gọi của bộ trích) chưa làm: Claude chọn giữ lời gọi riêng (chủ dự án uỷ quyền, 21/10/2026), vì gộp phải đổi prompt trích đã đo ở bài C; xem lại khi có số chi phí thật.
- **Hệ quả:** lời gọi `moderate` tính vào trần cảnh/chương/truyện (G8), vào nhật ký chi phí với vai `moderate`, và vào bộ đếm lời gọi mỗi phút (D-56), vì nó tốn tiền key người chơi: mỗi đầu vào của người chơi tốn thêm một lượt đếm (ô tự viết: kiểm duyệt rồi phân loại là hai lượt; **đã thay một phần (D-79):** đầu vào tốn tới `input_votes` lượt), mỗi lượt soát cảnh và mỗi bộ lựa chọn thêm một lượt. **Chủ dự án cần quyết:** mức u tối là lựa chọn có sẵn ở bước khởi tạo (cần đổi design §4.1 và thêm cột lưu theo truyện), hay model đọc tag chữ tự do.
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
- **Hệ quả:** bộ dò lộ lúc chạy (`safety/leak.py`) chỉ áp `leak_terms` khi chương < `reveal_from_chapter`. Ở tu-tien-1 hai bí mật có khoảng lộ 3-6 và 4-6 mà chưa hề hé lộ, nên từ chương 3-4 người kể có thể nói ra chúng mà không bị chặn theo cụm từ (chỉ còn quy tắc tên riêng). Đường người kể và lựa chọn chỉ dùng chữ của `player_view` nên có thể chặn mọi bí mật chưa hé lộ; cần chủ dự án quyết có đổi không. Chưa chạy thật. **Đã thay một phần (D-61):** chủ dự án chọn đổi; người kể và lựa chọn dò mọi bí mật chưa có trong `player_view`.
- **Người quyết:** Claude (nhánh narrator-retrieval), chờ điều phối duyệt · 20/10/2026

## D-61 · Bộ dò lộ chỉ cấm tên bí mật; `scope` bắt buộc (thay một phần D-26, D-48, D-52)
- **Bối cảnh:** lần chạy tu-tien-3 (`evals/results/2026-10-20-run-tu-tien-3/`) dừng ở chương 1: cảnh bị chặn cả hai lần bấm thử lại chỉ vì tên giới thiệu bình thường ("Đoàn Khương", "kho kiếm cụ"...), vì D-26 cấm mọi tên lớp truth chưa có trong `player_view` mà bộ trích hay quên hé lộ ở lần đầu. D-60 ghi lỗ ngược lại: người kể nói được bí mật đã tới khoảng lộ mà chưa hé lộ.
- **Quyết định:**
  - Chỉ hai loại tên bị cấm, vẫn chỉ khi có từ viết hoa người chơi chưa thấy (D-26, D-52): (a) tên thật bị giấu sau biệt danh: nút đã có trong `player_view` mà tên lớp truth không chứa trọn tên đã hé lộ và không chung từ viết hoa nào với nó ("Lý Thất" sau "gã lái đò mặt sẹo" bị cấm; "Đoàn Khương" sau "Đoàn sư huynh" thì không); (b) tên và biệt danh của nút trong `Secret.protects` của bí mật còn hiệu lực. `name` của nút `user_authored` vẫn không bao giờ bị cấm (D-48). `leak_terms` giữ nguyên.
  - `Secret.protects`: id nút có tên mà bí mật giấu danh tính, mặc định rỗng nên kế hoạch cũ vẫn đọc được. Đề `build_story` (`setup-5`) yêu cầu điền cho bí mật về danh tính; `initial_problems` kiểm id là nút có tên trong gói, không phải nhân vật chính (lúc khởi tạo nó chưa có biệt danh nào để giữ kín); id qua `normalize_ids` như mọi chỗ nhắc tới.
  - `check_leaks`, `ensure_no_leak` nhận `scope` bắt buộc, không mặc định: `scene` (văn cảnh) xét khoảng lộ như cũ; `player_path` (người kể, chữ lựa chọn, lời nói dối, cảm xúc) dò mọi bí mật chưa có trong `player_view`, bất kể khoảng lộ. `make_choices` và `ask_narrator_reply` gọi với `player_path`, nên mọi nơi tạo lựa chọn hay hỏi người kể (chương, `bench_run`, `api/play.py`, `api/stories.py`, `bench_e`) đi qua đúng phạm vi.
  - Bộ chấm bài E dùng `player_path` và giữ luật tên cũ (mọi tên riêng lớp truth chưa thấy), để vẫn chặt hơn lớp chạy thật (D-53).
- **Hệ quả:** tên không bí mật được nêu trên trang; code tự hé lộ nó (D-62). Tên bí mật ghép từ từ thường vẫn trúng cả chữ thường ("động linh mạch"). Chưa đo với model thật: model khởi tạo có điền `protects` đúng không, cảnh có hay bị chặn vì tên được bảo vệ không.
- **Người quyết:** Chủ dự án duyệt hướng (21/10/2026); cách làm: Claude · 21/10/2026

## D-62 · Tự hé lộ tên trang vừa nêu; từ chối `known_as` trùng tên nút khác
- **Bối cảnh:** D-61 cho trang nêu tên không bí mật, nhưng sổ tay và bộ dò chỉ biết điều có trong `player_view`, mà bộ trích hay quên hé lộ thực thể ở lần đầu (D-52, tu-tien-3). Lần chạy tu-tien-1 chương 5 (`truth_dump.json`): bộ trích gắn `known_as: "Vạn Tinh Bách"` lên nút `doan_khac`, nên sổ tay hiện kẻ phản bội dưới tên người khác.
- **Quyết định:**
  - Sau bước trích của mỗi cảnh (`pipeline/chapter.py`), `safety.reveal.auto_reveals` thêm `REVEALED_TO_PLAYER` cho nút có tên mà tên hay biệt danh có trong chữ cảnh, chưa có trong `player_view` (kể cả hé lộ bộ trích vừa ghi), không phải nhân vật chính, không bị bảo vệ (D-61): `quote` là câu nguyên văn chứa tên (G3), `known_as` đúng chuỗi trên trang (D-17), `valid_from_chapter` là chương đang viết (D-21). Cạnh qua người canh như cạnh của bộ trích.
  - So khớp nghiêm: giữ dấu, trọn từ, phân biệt hoa thường trừ chữ cái đầu của tên nhiều từ, tên phải có từ viết hoa ("Động Linh Mạch" không khớp "chấn động linh mạch", "Lan" không khớp "hoa lan"). Bỏ lần khớp nằm trong tên dài hơn của nút khác, và chuỗi khớp cũng là tên của nút khác. Mỗi nút một cạnh, ưu tiên `name`.
  - Bộ dò lộ của chính cảnh đó không tính các hé lộ tự động này, để câu trích không biến tên khác trong cùng câu thành "đã thấy".
  - `extract.to_package` từ chối cạnh có `known_as` trùng tên hay biệt danh lớp truth của một nút khác (`known_as_conflicts`, cùng cách chuẩn hoá của bộ dò lộ), lý do "known_as là tên của nút khác"; tự hé lộ cũng không dùng chuỗi đó.
- **Hệ quả:** sổ tay có thêm mục cho nơi chốn, phe, đồ vật trang chỉ nhắc qua. Nút chỉ được nêu bằng biệt danh viết thường thì vẫn chờ bộ trích. Tên nằm trong tên dài hơn ("Lão Gù" trong "lò rèn của Lão Gù") không hé lộ nút ngắn. Biệt danh chung của hai nút không bao giờ được hé lộ. Log chỉ ghi số nút tự hé lộ. Chưa đo trên truyện thật.
- **Người quyết:** Chủ dự án duyệt hướng (21/10/2026); cách làm: Claude · 21/10/2026

## D-63 · SSE qua uvicorn thật: đồ thị chạy trong task riêng, chờ dừng hẳn trước khi nhả khoá (bổ sung D-46)
- **Bối cảnh:** D-46 chỉ kiểm ngắt kết nối bằng ASGI gọi thẳng. Test mới chạy app bằng uvicorn 0.54 trong một thread, cổng ngẫu nhiên, httpx đọc stream qua TCP (`tests/graph/test_play_api.py`, mục uvicorn; `tests/api_fixtures.live_server`).
- **Phát hiện** (đọc mã nguồn uvicorn 0.54, Starlette 1.9, FastAPI 0.148, LangGraph 1.2.16, và test):
  - uvicorn báo ASGI `spec_version` 2.3, nên `StreamingResponse` chạy song song một vòng chờ `http.disconnect`. Người chơi đóng socket là uvicorn biết ngay (`connection_lost`), kể cả khi máy chủ đang chờ model; FastAPI huỷ task phát sự kiện bằng cancel scope của anyio. `send` của uvicorn sau khi ngắt thì im lặng bỏ qua, không báo lỗi: nếu một bản uvicorn sau báo 2.4, Starlette thôi chờ ngắt và chương sẽ viết tiếp tới hết; test sẽ đỏ.
  - **Lỗi thật:** huỷ kiểu anyio rơi vào lúc LangGraph đang chờ node thì task dọn dẹp của LangGraph (`AsyncPregelLoop.__aexit__` chạy `exit_task`) bị huỷ trước khi chạy. Node đang chạy thành mồ côi: lời gọi model chạy tiếp sau khi yêu cầu đã xong, khoá đã nhả, kết nối Postgres đã đóng, và không có dòng chi phí. Test ASGI cũ không thấy vì huỷ rơi vào lúc đẩy sự kiện.
  - Ping: `fastapi.routing` đọc `_PING_INTERVAL` (15 giây) lúc chạy; rút ngắn ở `fastapi.routing`, không phải `fastapi.sse`.
- **Quyết định:**
  - `ChapterRun.events()` chạy đồ thị trong task riêng, chuyển sự kiện qua hàng đợi một chỗ; người đọc dừng thì task đó nhận đúng một lần huỷ kiểu asyncio, LangGraph huỷ được node đang chạy. `aclose()` chờ nó dừng hẳn.
  - `api/play.get_running_chapter` (dependency có `yield`) gọi `aclose()` trước khi `get_chapter_job` nhả khoá và kết nối Postgres đóng. Hồi quy: `tests/unit/test_pipeline_chapter.py::test_reader_cancelled_by_anyio_does_not_orphan_the_model_call` và test uvicorn.
- **Hệ quả:** khoá nhả sau khi lời gọi bị huỷ đã ghi chi phí ước tính (D-64). Nối lại ngay trong khoảng đó nhận `STORY_BUSY`. Bản chạy bằng uvicorn nhiều worker hay sau proxy chưa kiểm.
- **Người quyết:** Claude (nhánh sse-cost-hardening), chờ điều phối duyệt · 21/10/2026

## D-64 · Lời gọi không có usage: ghi chi phí tối đa, đánh dấu ước tính, tra lại theo id generation (bổ sung D-10, D-44)
- **Bối cảnh:** lời gọi bị huỷ (D-46, D-63) hay đứt giữa chừng không có `usage`, nên không có dòng chi phí và trần mỗi truyện bị hụt (docs/security.md). Tài liệu OpenRouter, tra 21/10/2026: https://openrouter.ai/docs/api-reference/get-a-generation (`GET /api/v1/generation?id=`, `data.total_cost` USD, `tokens_prompt`, `tokens_completion`), https://openrouter.ai/docs/api-reference/streaming (header `X-Generation-Id` ở mọi endpoint; stream bị huỷ chỉ dừng tính tiền với một số nhà cung cấp; lời gọi không stream bị huỷ vẫn bị tính đủ), https://openrouter.ai/docs/api-reference/errors (status và header gửi ngay khi nhà cung cấp nhận yêu cầu), https://openrouter.ai/docs/use-cases/usage-accounting (`id` của phản hồi dùng để tra). Docs không nói generation có sau bao lâu.
- **Quyết định:**
  - `llm/openrouter.py`: `chat` đọc header trước thân, báo `sent` và id generation qua `CallTrace` (`llm/base.py`); `generation_cost(id)` gọi endpoint trên, 404 là chưa có.
  - Mọi lời gọi bằng key người chơi gửi `max_tokens` = `limits.llm_call.max_output_tokens` (như D-43). Chi phí tối đa = token vào ước tính từ số ký tự (`EST_CHARS_PER_TOKEN`) × giá vào + trần đó × giá ra (`llm/cost.CostEstimator`); giá ở `config/models.yaml` `prices`, model không có giá thì từ chối trước khi gửi.
  - `llm/ledger.RecordingClient`: phản hồi thiếu `usage.cost`, lời gọi bị huỷ, đứt mạng sau khi gửi, hay lỗi đã có id generation thì ghi chi phí tối đa, `estimated` (migration 0007). Lỗi kết nối, lỗi HTTP chưa có generation, `WRITORY_RATE_LIMITED` không ghi (`llm/cost.maybe_billed`). Mọi vai đều qua đây, kể cả `moderate` (D-57).
  - Trước lời gọi đầu của mỗi nhóm (`api/deps.PlayerLLM.open`), tra lại tối đa `SETTLE_LOOKUPS_PER_OPEN` dòng ước tính có id của cùng truyện hay phiên, bằng client của chính key người chơi, không xin lượt tần suất; tra được thì thay bằng số thật.
- **Hệ quả:** trần mỗi truyện cộng cả số ước tính, rộng tay hơn nhiều so với chi phí thật của một lời gọi thường. Trần cảnh và chương trong cùng yêu cầu chưa cộng lời gọi lỗi; D-10 giữ nguyên (thiếu `usage.cost` vẫn dừng). Dòng ước tính không có id thì giữ mãi. Chưa kiểm với lời gọi thật; ước tính token vào chưa chắc là chặn trên; `stream` không gửi được `max_tokens`.
- **Người quyết:** Claude (nhánh sse-cost-hardening), chờ điều phối duyệt; gửi `max_tokens` trên đường người chơi cần điều phối duyệt · 21/10/2026

## D-65 · Giao diện bản 1: theo bàn giao thiết kế; sắc thái theo máy chủ, bỏ ô thời đại, người kể có số câu còn lại và nguồn
- **Bối cảnh:** bàn giao thiết kế (`frontend/design-handoff/`, README mục 8) có các chỗ chưa khớp với code và design.
- **Quyết định:**
  - Sắc thái lời thoại theo máy chủ: mỗi lựa chọn mang một `tone` cố định, giao diện hiện nhãn, không có bộ chọn sắc thái.
  - Bỏ ô thời đại: thể loại chính đã gồm thời đại. API giữ `tags.era` tuỳ chọn; giao diện không gửi.
  - Người kể trả thêm số câu hỏi còn lại của chương và nguồn (chương của các mục sổ tay câu trả lời dẫn), tính bằng code từ `player_view`.
  - Bàn giao thiết kế được commit làm đầu vào cho frontend, trừ ảnh chụp màn và file zip (giữ trên máy, `.gitignore`). Khi frontend xong, chuyển quy tắc còn dùng vào `docs/design.md` rồi xoá thư mục.
- **Hệ quả:** cần thêm trường cho `NarratorAnswerOut`. Các điểm còn lại của README mục 8 (endpoint danh sách truyện, chi phí đã dùng, giới hạn công khai, câu lỗi trần chi phí) làm cùng phần backend cho giao diện.
- **Người quyết:** Chủ dự án · 21/10/2026

## D-66 · Endpoint cho giao diện: tủ truyện, cấu hình công khai, chi phí theo tháng UTC, nguồn của người kể
- **Bối cảnh:** README bàn giao thiết kế mục 8 (điểm 2, 5, 6) và D-65: giao diện cần danh sách truyện, số giới hạn để không tự đặt số, chi phí đã dùng, số câu hỏi người kể còn lại và nguồn.
- **Quyết định:** mọi route sau `ENABLE_DEV_ROUTES` (D-41), theo `owner_id` (D-44); schema là danh sách trắng (`api/schemas.py`).
  - `GET /stories`: truyện của người đang dùng, `stories.updated_at` giảm dần. `title` là tên hướng truyện đã chọn ở phiên khởi tạo (không có thì tên bối cảnh; truyện không qua `/setup` thì null). `last_excerpt` là câu cuối, nguyên văn, của dòng chữ cuối trong cảnh cuối của chương đã commit (bỏ dấu thoại "- "), null ở chương 0. `finished` tính từ kế hoạch, không trả số chương của kế hoạch (`db/library.py`).
  - `GET /config/public`: số lấy từ `config/`, null là chưa đặt; không model id, giá, trần nội bộ. Nhãn mức viết là mức đường chơi dùng (`writer_tier(config, None)`).
  - `GET /player/costs`: cộng `llm_costs` theo `owner_id`, kể cả phiên khởi tạo bỏ dở. Tháng là tháng dương lịch theo **UTC** (`db.utc_month`), giờ lấy từ `deps.get_clock`. Theo truyện: truyện tiêu gần nhất trước. Dòng thiếu `cost_usd` không cộng được (D-10); dòng ước tính (D-64) cộng như số thật tới khi tra lại.
  - Người kể (D-65): `remaining` là trần trừ số lượt đã giữ ở `narrator_questions`, ở chương của câu hỏi. `source_chapters` lấy từ `entry_ids` chỉ khi câu trả lời là chữ của model đã qua mọi phép kiểm: `since_chapter` của mục, chương được nói của lời nói dối (`pipeline/narrator.source_chapters`). Thêm `GET /stories/{id}/narrator` trả `{remaining}`.
  - Câu lỗi `COST_LIMIT_SCENE`, `COST_LIMIT_CHAPTER` bỏ "chọn mức model rẻ hơn" (một mức viết, D-33): nói phần đã hiện và đã lưu vẫn còn, rồi bấm thử lại.
  - Không bật CORS: frontend dev gọi API qua proxy của Vite, cùng origin (`docs/runbook.md`).
- **Hệ quả:** tủ truyện chưa có tên nhân vật chính và thể loại như ảnh mẫu (ngoài hợp đồng). Chọn lựa chọn không đổi `updated_at`, nên không đẩy truyện lên đầu. Câu trích chưa có trần độ dài. Ước tính chi phí chương tới: D-87.
- **Người quyết:** hợp đồng endpoint, tháng theo UTC: điều phối yêu cầu; tên truyện, câu trích, thứ tự, không CORS: Claude (nhánh ui-backend), chờ điều phối duyệt · 21/10/2026

## D-67 · Mức u tối chọn sẵn lúc khởi tạo, lưu theo truyện (thay một phần D-58)
- **Bối cảnh:** D-58 để mức u tối là chữ tự do (`tags.darkness`), nên đường chơi luôn kiểm duyệt ở mức mặc định.
- **Quyết định:**
  - `POST /setup` nhận `darkness_level`, khoá trong `moderation.darkness_levels`; bỏ trống thì `default_darkness_level`, ghi hẳn khoá vào phiên; khoá lạ thì `REQUEST_INVALID` kèm `fields`. API bỏ `tags.darkness` (gửi lên là `REQUEST_INVALID`); `StoryTags.darkness` chỉ còn để đọc phiên và đề cũ. `SetupOut` có `darkness_level`.
  - Lưu theo truyện: cột `stories.darkness_level` (migration 0008; NULL là mức mặc định, cho truyện cũ). `ChapterRequest.darkness_level` và cổng kiểm duyệt của `POST /stories/{id}/choices` lấy từ cột này.
  - Đề: `safety.moderate.darkness_brief` (nhãn và trần từng loại, cùng nguồn với `decide`) vào khối dữ liệu `darkness_level` ở mọi bước khởi tạo, và vào `story_brief` cho đề dàn ý và đề viết mỗi chương.
  - `bench_run`: đề khai được `darkness_level` (null là mặc định), khoá lạ báo trước lời gọi đầu; lưu theo truyện và vào `ChapterRequest` như đường chơi. Bài E dựng lại thiết lập của lần chạy trước D-67 không có dòng mức u tối.
  - `GET /config/public` có `darkness_levels` (`key`, `label`, theo thứ tự config) và `default_darkness_level`; không có trần.
- **Hệ quả:** truyện tạo trước D-67 chạy ở mức mặc định, và thiết lập đã lưu của chúng không có dòng mức u tối. Đề khởi tạo dài thêm, chưa đo lại. Chữ mức u tối của bài E lấy từ config hiện hành, vì lần chạy không lưu chữ thiết lập.
- **Người quyết:** chọn sẵn mức thay chữ tự do: Chủ dự án duyệt 21/10/2026; cách làm: Claude (nhánh ui-backend), chờ điều phối duyệt · 21/10/2026

## D-68 · Frontend bản 1: Vite + React + TS strict + Tailwind; số và chữ từ máy chủ; luật hiển thị có test
- **Bối cảnh:** design §11 chọn React/TS/Tailwind; bàn giao thiết kế (D-65) cho màn, token, luật hiển thị. Một số trường trong ảnh chưa có ở API.
- **Quyết định:**
  - `frontend/`: Vite 7, React 19, react-router 7, TypeScript strict, Tailwind 3 (dùng theme v3 của bàn giao). Token, hiệu ứng, SVG chép vào `src/styles/` làm nguồn của app; thư mục bàn giao chỉ là đầu vào (D-65).
  - Font tự host từ @fontsource, chỉ subset latin + vietnamese, chỉ woff2 (`src/styles/fonts.css`).
  - Route theo README bàn giao mục 3, thêm `/truyen/:id/chuong/:n` để đọc lại. Proxy `/api` → `:8000`, bỏ tiền tố (app FastAPI không có tiền tố).
  - Giới hạn, trần, nhãn độ dài, mức u tối chỉ lấy từ `GET /config/public`; ước tính chưa có thì ghi "chưa có ước tính". Lỗi hiện nguyên văn `message`, bố cục theo `code` (`src/lib/errorGroups.ts`).
  - Khuôn truyện không chọn sẵn thể loại, độ dài; mức u tối chọn sẵn mặc định của máy chủ; quy ước tên mặc định gửi `naming: null`.
  - Test nhẹ bằng Vitest + Testing Library; mỗi luật quan trọng một test (`src/test/rules.test.tsx`).
- **Hệ quả:** lệch ảnh vì API chưa có trường: không tên nhân vật chính và bối cảnh ở thanh trên, không tên chương, không "thân phận", tính cách là ô chữ thay vì nhãn, không "~N trang", không tag phụ, không "Ba bối cảnh khác", không "ngã rẽ đã chọn" ở màn kết, không ngày lưu khoá. Nút `Lie` đã hé lộ để ở tab riêng "Lời nói dối đã biết". Câu hỏi mở cho chủ dự án: thể loại "Kỳ ảo · tu tiên" gửi nguyên chữ nên không khớp `DEFAULT_NAMING` của máy chủ (rơi về mặc định ngoài bảng); chỗ hiện nút `Lie`.
- **Người quyết:** Claude (nhánh frontend-v1), chờ điều phối duyệt · 21/10/2026

## D-69 · Đọc SSE bằng fetch; lần viết sống ngoài React; lớp mock là máy chủ giả trả Response thật
- **Bối cảnh:** `POST /stories/{id}/chapters/next` là SSE qua POST (D-46), EventSource không gửi được. Lời gọi model trừ tiền key người chơi; StrictMode chạy effect hai lần; máy chủ huỷ lần viết khi mất kết nối.
- **Quyết định:**
  - Đọc bằng `fetch` + ReadableStream + TextDecoder luồng (`src/api/sse.ts`): tách theo chuẩn text/event-stream, bỏ chú thích `: ping`, ghép chuỗi bị cắt giữa dòng, giữa CRLF, giữa ký tự UTF-8. Lỗi trước luồng là JSON có status, thành ApiError.
  - Lần viết nằm trong store ngoài React (`src/state/chapterRun.ts`): mỗi truyện một lần viết; rời trang đọc sang trang khác trong app thì luồng vẫn chạy, đóng thẻ thì dừng. Chỉ tự viết ngay sau thao tác của người chơi (chốt khởi tạo, chọn hướng); mở lại chương chưa viết thì có nút "Viết chương N". Lời gọi khởi tạo trùng nhau được gộp (`src/lib/inflight.ts`).
  - Thử lại: chương chưa ghi thì viết lại từ đầu; đã ghi thì lấy lại trạng thái (lựa chọn tạo lại bằng `POST /choices`); mất mạng thì hỏi lại máy chủ trước và giữ chữ đã hiện.
  - Chữ chạy dần là hoạt cảnh phía client trên trọn chữ cảnh; chạm vào trang hoặc giảm chuyển động thì hiện đủ ngay.
  - Mock: máy chủ giả trong trình duyệt thay `fetch` (`src/mock/`), không dùng MSW; trả `Response` thật nên đi qua đúng client và bộ đọc SSE; test dùng chính nó. Truyện bịa; `?mock=rong`, `?loi=<MÃ>`.
- **Hệ quả:** thêm hay đổi endpoint thì sửa mock cùng commit. Lỗi phía trình duyệt (mất mạng, phản hồi sai dạng) có mã `CLIENT_*` và câu của giao diện, không giả làm mã máy chủ.
- **Người quyết:** Claude (nhánh frontend-v1), chờ điều phối duyệt · 21/10/2026

## D-70 · Thang mức độ kiểm duyệt: tả lướt là `mild`; ám chỉ cảnh tình dục cũng tính
- **Bối cảnh:** bài đo G9 lần 1 (`evals/results/2026-10-21-g9-luna-1/`) có 2 câu chặn nhầm cảnh đánh nhau bình thường ở mức Vừa. Nguyên nhân: thang mức độ trong config lấy "máu loang trên áo" làm ví dụ `strong`, lệch với bộ câu. Có thêm 1 câu bỏ sót: ám chỉ qua đêm ở mức Nhẹ.
- **Quyết định:** `intensity_scale.mild` gồm cả tả lướt trong một câu; `strong` là miêu tả có chi tiết. Chữ mô tả `adult_sexual` nói rõ ám chỉ cũng tính. Danh sách loại và các trần không đổi.
- **Hệ quả:** lần đo lại (`evals/results/2026-10-21-g9-luna-2/`) đúng 44/44, nhưng lạc quan vì ví dụ lấy từ chính bộ đo. Cần một bộ câu giữ riêng.
- **Người quyết:** Claude, chủ dự án uỷ quyền chọn (21/10/2026) · 21/10/2026

## D-71 · Bộ câu kiểm duyệt giữ riêng và chạy lặp (bổ sung D-70)
- **Bối cảnh:** lần đo G9 thứ hai đúng 44/44 nhưng lạc quan: thang mức độ trong config lấy ví dụ từ chính bộ đo, và mỗi câu mới chạy một lần (`evals/results/2026-10-21-g9-luna-2/notes.md`).
- **Quyết định:**
  - Thêm `evals/redteam/g9_moderation_holdout.yaml` (version 1, khai trước 21/10/2026), cùng định dạng với bộ cũ. Không chép và không diễn đạt lại câu nào của bộ cũ hay của ví dụ trong config; test kiểm độ trùng cụm bốn từ. Nội dung thuộc loại cấm chỉ ở dạng mô tả trong ngoặc vuông.
  - Phủ mọi loại ở cả đầu vào lẫn đầu ra, ba mức u tối, chữ có dấu, không dấu, teencode, tiếng Anh, phủ định, câu dài, câu đội lốt, và nhiều câu truyện u tối hợp lệ để đo chặn nhầm.
  - Quy ước dùng: không chỉnh prompt hay config theo từng câu của bộ này. Khi kết quả của nó đã được dùng để sửa config, nó thành bộ chỉnh và phải làm bộ giữ riêng mới (ghi vào decisions.md). **Đã áp (D-79):** kết quả của bộ v1 đã được dùng để đổi cách gọi, nên v1 là bộ chỉnh.
  - `bench_g9` thêm `--cases` (mặc định bộ cũ), `--repeat N` (báo `unstable` và `stable_rate`) và `--budget` (trần chi phí của lần chạy; chạm trần thì dừng và ghi `stopped_by_budget`). `result.json` ghi tên file, hash, version và số câu của bộ câu.
- **Hệ quả:** chạy lặp chỉ lộ sự không ổn định của model (suy luận thấp, lấy mẫu); nó không chứng minh một câu ổn định là đúng. Con số trên bộ giữ riêng là ước lượng độ chính xác trung thực hơn, nhưng bộ chỉ vài chục câu nên khoảng tin cậy rộng. Lần chạy thật do điều phối làm.
- **Người quyết:** Claude (nhánh g9-holdout), điều phối giao việc, chờ duyệt · 21/10/2026

## D-72 · Bài A (bộ nhớ): năm hệ trả lời cùng một model, câu hỏi chỉ về điều có trên trang, chấm bằng code
- **Bối cảnh:** design §9 A đặt năm đối thủ và hẹn bản 1 chạy ba (tóm tắt, nhét cả truyện, đồ thị). Điều phối giao dựng khung đủ năm hệ; chưa có bộ câu hỏi nào, chỉ có truyện mẫu và `graph.yaml` dựng tay chờ duyệt.
- **Quyết định:**
  - Năm hệ (`pipeline/bench_a_systems.py`) cùng một model trả lời (vai `narrator` của `config/models.yaml`), khác ở ngữ cảnh. Mọi hệ trừ nhét cả truyện được xem thêm **chương N** (chương vừa viết xong), để bài đo là bộ nhớ về chương cũ chứ không phải đọc chương hiện tại; `run.yaml` có cờ cho hệ đồ thị. Hệ tóm tắt dùng tóm tắt từng chương của vai `summary` có sẵn (D-49) nối lại, không gấp dần một bản; chi phí dựng tính cho hệ này. Hệ đồ thị đọc chỉ qua `GraphState` (G10), nền Neo4j khi chạy thật, nền gói trong bộ nhớ khi chạy khô; test so hai nền ra cùng ngữ cảnh. **Đã bổ sung (D-81):** hệ thứ sáu `graph_quotes` (đồ thị + câu trích), tuỳ chọn trong `run.yaml`.
  - Câu hỏi (`evals/scenarios/memory/questions.yaml`): năm nhóm, mỗi câu khai chương hỏi, chương của sự thật, đáp án gốc kèm `derive` (tính lại từ đồ thị) và `evidence` (câu trích có trên trang). Điều chỉ có ở lớp sự thật mà trang chưa nói (Lan là gián điệp từ đầu, Lan giữ kiếm ở chương 4, ai giết Lão Gù) không hỏi, vì hệ đồ thị thấy được còn các hệ khác không thể đúng.
  - Chấm bằng code: tập thực thể, có/không, chọn một, nhóm từ khoá; "Không biết" tính riêng; lượt lỗi hay thiếu tính chưa đúng; Wilson cho khoảng tin cậy. Không giám khảo LLM ở v1.
  - Khung kiểm: `FakeAnswerer` oracle chỉ đúng khi ngữ cảnh đủ chứng cứ; null; wrong.
- **Hệ quả:** hệ đồ thị dùng đồ thị dựng tay nên đo **trần của phần đọc**; chất lượng bộ trích đo ở bài C, không ở đây. Hệ đồ thị thấy một ít lớp sự thật ngoài trang (người liên quan trong sự kiện, cạnh mở ở chương N chưa hé lộ); ghi nhận, vì trong sản phẩm người viết cũng thấy. Câu "quan hệ" chủ quan nhất (bạn hay yêu ở chương 2–3). Design §9 để `none` và `rag` cho bản 2: khung có sẵn, chạy cả năm hay chỉ ba do chủ dự án quyết (`--systems`). Chưa chạy thật; `bench_a plan` in chi phí ước tính.
- **Người quyết:** Claude (nhánh bench-a-memory), điều phối duyệt; đề và cách chấm: Chủ dự án duyệt 21/10/2026 (thêm: câu quan hệ theo chiều của Minh, `inference` báo riêng) · 21/10/2026

## D-73 · Hệ RAG của bài A dùng BM25, không dùng embedding
- **Bối cảnh:** design §9 A ghi "RAG vector thường". Embedding qua OpenRouter cần chọn model và giá, thêm lời gọi và chi phí; truyện mẫu chỉ vài chục đoạn.
- **Quyết định:** truy hồi bằng BM25 thuần Python (`bench_a_systems.Bm25Index`), không thêm phụ thuộc: đoạn văn gộp tới cỡ trong `run.yaml`; token là âm tiết (giữ dấu, bỏ vài từ chức năng) cộng cặp âm tiết liền nhau; lấy `top_k` đoạn của chương 1..N-1, sắp theo thứ tự truyện, cộng chương N nguyên văn. Tất định, không tốn tiền, không cần key.
- **Hệ quả:** BM25 khớp từ chứ không khớp nghĩa, nên đây là bản RAG **yếu hơn** RAG vector thật; kết luận "đồ thị hơn RAG" chỉ đúng với RAG từ vựng. Chạy khô với oracle (`--dry-run`) cho biết miễn phí phần chứng cứ mà truy hồi tìm lại được, trước khi tốn tiền. Muốn đối thủ mạnh hơn thì thêm hệ thứ sáu dùng embedding (cần chủ dự án chọn model, giá, trần chi phí) thay vì sửa hệ này.
- **Người quyết:** Claude (nhánh bench-a-memory), điều phối duyệt; đề và cách chấm: Chủ dự án duyệt 21/10/2026 (thêm: câu quan hệ theo chiều của Minh, `inference` báo riêng) · 21/10/2026

## D-74 · Nhân vật chính có mục trong sổ tay từ chương 0 (thay một phần D-38)
- **Bối cảnh:** bài E trên `tu-tien-1` (`evals/results/2026-10-21-narrator-tu-tien-1/`): "Tôi tên là gì?" luôn nhận "Bạn chưa biết điều này.". Đọc lại dữ liệu thấy hai nguyên nhân. (1) D-38 giữ `player_view` chương 0 rỗng và D-62 bỏ qua nhân vật chính khi tự hé lộ, nên tên chỉ vào sổ tay khi bộ trích tình cờ hé lộ (ở `tu-tien-1` có, từ chương 1). (2) Dù có mục, sổ tay không nói mục đó là người chơi nên model không nối "tôi" với nó.
- **Quyết định:**
  - Gói chương 0 có nút `ch0` và đúng một `REVEALED_TO_PLAYER` từ `protagonist`: `known_as` là tên người chơi đã chọn, `quote` là dòng "Nhân vật chính: <tên>" của `story_brief` (chữ đã thấy, D-52), nên G3 vẫn đúng. `initial_problems` chỉ cho đúng cạnh này; `KNOWS` của nhân vật chính và mọi hé lộ khác ở chương 0 vẫn là lỗi. **Đã thay một phần (D-76):** `KNOWS` của nhân vật chính do model ghi trong `known_by` thì code bỏ trước khi kiểm.
  - `PlayerEntry.is_protagonist` (từ `is_protagonist` của nút). Sổ tay cho model ghi mục đó là "Nhân vật chính (chính là người chơi, "tôi")", prompt người kể thêm một luật, và truy hồi (D-59) luôn kèm nó. API sổ tay (`NotebookEntryOut`) chưa thêm trường này. **Đã bổ sung (D-76):** `NotebookEntryOut.is_protagonist`, thẻ sổ tay trên giao diện ghi nhãn "Bạn".
  - G1, G4: chỉ tên và câu trích đã hiện; tên là chữ người chơi nên nằm trong khối dữ liệu của sổ tay.
- **Hệ quả:** sổ tay chương 0 có một mục, nên hỏi người kể ở chương 0 gọi model thay vì trả ngay. Truyện tạo trước D-74 không có mục này ở chương 0. Prompt người kể đổi, nên kết quả bài E trước đó không so trực tiếp được. Chưa đo lại với model thật.
- **Người quyết:** Claude (nhánh protagonist-notebook), điều phối giao việc, chờ duyệt · 21/10/2026

## D-75 · Test graph chạy trên database Postgres riêng; thể loại ghép lấy phần đầu có trong bảng quy ước tên
- **Bối cảnh:** trước khi chủ dự án chạy app trên máy (21/10/2026). Test graph và app dùng chung database `writory`, nên test xoá và ghi đè key của người chơi dev, kéo theo key người chơi dán vào app bị mất. Các session chạy test song song cũng làm nhau đỏ (`PLAYER_KEY_UNREADABLE`). Giao diện gửi thể loại "Kỳ ảo · tu tiên", không khớp bảng `DEFAULT_NAMING` (D-32), nên rơi về tên Việt.
- **Quyết định:**
  - `tests/graph/conftest.py`: fixture phiên `isolated_postgres` đặt `POSTGRES_DSN` sang `<tên>_test` (hoặc `POSTGRES_TEST_DSN`), tự tạo database nếu chưa có. Mọi test graph, dependency của app và tiến trình con đọc biến này.
  - `setup.default_naming`: nhãn ghép (`·`, `/`, `,`, `|`) lấy phần đầu tiên có trong bảng.
- **Hệ quả:** Neo4j Community chỉ có một database, nên test vẫn tách theo `story_id`. Các phiên test chạy song song vẫn dùng chung `<tên>_test` với nhau.
- **Người quyết:** Claude · 21/10/2026

## D-76 · Khởi tạo: code bỏ `KNOWS` của nhân vật chính ở chương 0; sổ tay API và giao diện đánh dấu nhân vật chính (thay một phần D-38 và D-54)
- **Bối cảnh:** lần chạy `evals/results/2026-10-21-run-tu-tien-4/` (notes.md mục 1): lượt khởi tạo thứ hai tốn một lượt sửa, trong đó có năm cạnh `KNOWS` từ `protagonist` ở chương 0. Model ghi `protagonist` vào `known_by` của các fact bối cảnh ("ba tông môn tranh quyền") dù đề cấm. D-38 và D-54 coi đó là lỗi quy tắc, nên mỗi lần như vậy tốn một lượt sửa trên key người chơi. D-74 chưa đưa cờ nhân vật chính ra API sổ tay.
- **Quyết định:**
  - `setup.drop_protagonist_knows`: sau `normalize_ids`, trước mọi phép kiểm, code bỏ `protagonist` khỏi `known_by` của mọi fact, ở cả `build_story` và `to_story_setup`. Không còn là lỗi, không tốn lượt sửa. Fact vẫn còn, nhân vật khác vẫn biết nó. Khi có lỗi khác, câu trả lời trước gửi cho lượt sửa là bản đã bỏ. Log chỉ có số cạnh bị bỏ, không id hay chữ.
  - `initial_problems` giữ luật nhân vật chính không `KNOWS` gì ở chương 0, làm lưới cuối cho gói không đi qua `build_story`. Các luật khác không đổi.
  - Đề `build_story` (`setup-6`): `known_by` chỉ gồm nhân vật khác, kể cả bối cảnh chung mà nhân vật chính hẳn đã biết, kèm lý do (người chơi chưa đọc trang nào).
  - `NotebookEntryOut.is_protagonist` lấy từ `PlayerEntry.is_protagonist` (D-74). Thẻ sổ tay của mục đó có nhãn "Bạn" (`frontend/src/screens/story/NotebookPanel.tsx`).
- **Hệ quả:** điều nhân vật chính biết từ trước chỉ vào sổ tay khi trang kể tới (G3), như D-38. Đề đổi nhưng chưa đo lại tỉ lệ khởi tạo hỏng với model thật. Cờ mới trên API không lộ lớp truth, vì chính người chơi đã chọn nhân vật này.
- **Người quyết:** Claude (nhánh fix/run4-followups), điều phối giao việc, chờ duyệt · 21/10/2026

## D-77 · Người kể được nối câu hỏi với mục nói về cùng một thứ dù khác chữ, được tóm tắt và trả lời một phần (bổ sung D-40)
- **Bối cảnh:** bài E v2 (`evals/results/2026-10-21-narrator-v2/`) lộ 0, nhưng 10/105 lượt hỏi điều đã mở khoá bị model tự từ chối (`known = false`). Trong đó 7 lượt có mục căn cứ trong phần sổ tay đã gửi; 3 lượt còn lại là truy hồi trượt (D-59). Trên tu-tien-1 (`evals/results/2026-10-21-narrator-tu-tien-1/`) cũng vậy với "Đường Hầm Sương tôi thấy ở đâu?". Ví dụ: "Cai Khải là người thế nào?" khi sổ tay ghi "Trần Văn Khải" (câu trích "cai Trần Văn Khải"); "Thanh Sương đâu rồi?" khi sổ tay chỉ ghi nó biến mất. Không lượt nào bị code chặn oan. Đề cũ cấm "suy ra điều sổ tay không nói", nên model không dám nối chữ khác hay trả lời một phần.
- **Quyết định:** đề người kể `narrator-2` (`pipeline/narrator.py`, `PROMPT_VERSION`). **Đã thay một phần (D-78):** đề `narrator-3` đặt `known = false` cho câu sổ tay không trả lời thẳng được, và code đổi câu nói về việc thiếu thông tin thành NOT_KNOWN.
  - Được làm: nhận ra mục nói về cùng một thứ dù câu hỏi gọi khác chữ (tên ngắn, chức danh kèm tên, cách gọi trong mục hay câu trích, cách gọi chung khi sổ tay chỉ có một thứ như vậy, thiếu dấu). Được tóm tắt các mục liên quan, kể lại câu trên trang, và nói điều mới nhất khi hỏi "đâu rồi". Có điều liên quan thì `known = true`, dù chỉ trả lời được một phần.
  - Vẫn cấm: thêm điều sổ tay không nói, đoán, suy ra kết luận mới (ai làm, vì sao, ai là ai), tự coi hai mục khác nhau là một. Cũng cấm gợi ý, úp mở, hay bàn về phần sổ tay không có. Câu bắt đoán, bắt ghép manh mối, hay hỏi về chính truyện thì `known = false`.
  - Lớp chặn bằng code không đổi: context chỉ từ `PlayerView` (G1), `check_leaks` với `scope="player_path"` (G2), kiểm `entry_ids`. Bài E ghi `narrator_prompt` trong `meta.json` và `summary.md`.
- **Hệ quả:** kết quả bài E trước đó dùng đề cũ, không so trực tiếp được. Đề cho tóm tắt nên có thể tăng `vuot_so_tay` hoặc lộ ở câu thô. Chưa chạy thật; lệnh chạy lại ở `docs/eval.md`. Câu hỏi khác chữ mà truy hồi (D-59) không gửi mục căn cứ thì vẫn nhận "Bạn chưa biết điều này.".
- **Người quyết:** Claude (nhánh fix/run4-followups), điều phối giao việc, chờ duyệt · 21/10/2026

## D-78 · Người kể không úp mở: đề `narrator-3` và lưới bằng code cho câu nói về việc thiếu thông tin (thay một phần D-77)
- **Bối cảnh:** bài E với đề `narrator-2` (`evals/results/2026-10-21-narrator-v2-d77/notes.md`, `2026-10-21-narrator-tu-tien-1-d77/notes.md`): loại a đạt nhiều hơn, nhưng giám khảo đánh `goi_y_an` 7 lượt (trước đó 0). Câu kiểu "chưa có nội dung được ghi lại", "không có thông tin về việc…", "sổ tay chỉ ghi…" ngầm báo còn điều chưa kể (design §6.6). Câu hỏi thẳng bí mật ("Lan có giết Lão Gù không?") được đáp bằng mục lân cận.
- **Quyết định:**
  - Đề `narrator-3` (`pipeline/narrator.py`, `PROMPT_VERSION`): câu sổ tay không trả lời thẳng được (có phải hay không, ai đã làm, nội dung là gì, vì sao) thì `known = false`; cấm thuật mục lân cận thay câu trả lời; cấm nói về việc thiếu hay chưa biết thông tin. Giữ phần của D-77: nối cùng một thứ dù khác chữ, tóm tắt và trả lời một phần khi câu hỏi hỏi về chính thứ có trong sổ tay.
  - Lưới bằng code, sau bộ dò lộ: câu trả lời có cụm nói về việc thiếu thông tin hay về chính sổ tay (`META_HEDGE_PATTERNS`, `meta_hedge`) thành "Bạn chưa biết điều này.", lý do `meta_hedge` (`BlockReason`). Mỗi cụm phải có một danh từ hay động từ về thông tin, ghi chép, sổ tay; "chưa", "không" đứng riêng không bắt ("Lan chưa trở về"), sổ sách có thật trong truyện cũng không ("Bản ghi không có nội dung bàn giao"). Log chỉ ghi tên cụm.
  - Không vi phạm G5: đây là kiểm chữ đầu ra của model, như bộ dò lộ, không đọc ý định người chơi.
  - Test (`tests/unit/test_narrator.py`): mọi câu giám khảo đánh `goi_y_an` (đọc nguyên văn từ `judge.jsonl`) bị đổi; mọi câu đúng loại a của các lần chạy bài E không bị đổi; không câu văn nào của truyện mẫu và các truyện do pipeline viết trong `evals/results/` bị bắt; kẻ lộ và oracle chạy khô như cũ.
- **Hệ quả:** lưới chỉ bắt cụm đã liệt kê; cách nói khác vẫn lọt, và câu thuật mục lân cận (không có cụm nào) chỉ do đề chặn. Câu trả lời đúng mà kèm một vế "không có thông tin…" bị đổi cả câu, nên loại a có thể giảm. Câu trên trang tự nói "chưa có ghi chép…" thì kể lại bị chặn oan. Chưa chạy bài E với đề `narrator-3`.
- **Người quyết:** Claude (nhánh fix/narrator-hint-moderation), điều phối giao việc, chờ duyệt · 21/10/2026

## D-79 · Kiểm duyệt: đầu vào kiểm `input_votes` lần, bộ lựa chọn chấm từng dòng; bộ giữ riêng v1 thành bộ chỉnh (thay một phần D-57, D-58)
- **Bối cảnh:** bộ giữ riêng v1 (`evals/results/2026-10-21-g9-holdout-1/notes.md`): 215/225, 0 chặn nhầm. Nhưng hai yêu cầu gây hại ở đầu vào lọt 1/3 lượt (model nhận ra được, không ổn định), và 4 câu bộ lựa chọn vượt mức hay gây hại lọt: ba dòng ngắn bị chấm nhẹ tay hơn văn cảnh. D-71 cấm chỉnh config hay prompt theo từng câu của bộ này, nên chỉ đổi cách gọi.
- **Quyết định** (`safety/moderate.py`, `PROMPT_VERSION = "moderate-2"`; cùng hàm `moderate` cho sản phẩm và `bench_g9`):
  - Đầu vào: `moderation.input_votes` lời gọi độc lập, cùng câu hỏi, lần lượt (`config/moderation.yaml`, tạm 2, từ 1 tới 5). Một lần báo loại chặn cứng hay loại chặn là chặn, và dừng, không gọi tiếp. Lỗi một lần là fail closed như cũ. Lần lượt, không song song: trần chi phí kiểm đúng trước mỗi lời gọi, và bộ đếm lời gọi mỗi phút (D-56) dùng một kết nối Postgres.
  - Bộ lựa chọn: vẫn một lời gọi. Mỗi chuỗi người chơi thấy (chữ, lời nói dối, cảm xúc) là một dòng đánh số; số dòng ghi ngoài khối dữ liệu. Đề dặn chấm từng dòng như một hành động sẽ xảy ra trong cảnh, không theo độ dài dòng. Model trả đúng một mục cho mỗi dòng (`ChoicesModerationOutput`; thiếu, thừa hay trùng dòng là sai schema, thử lại); code `decide` từng dòng theo trần u tối của truyện, dòng nặng nhất quyết định.
  - Vì sao cách này: N lời gọi riêng tốn N lần đề hệ thống và mất ngữ cảnh các dòng khác; một lời gọi mà không trả theo dòng thì không buộc model xét từng dòng, và code không kiểm được dòng nào đã được chấm.
  - Chi phí: `holdout-1` tốn 0,0243 USD cho 225 lời gọi, khoảng 0,0001 USD mỗi lời gọi. Mỗi đầu vào sạch thêm chừng ấy, thêm một lượt đếm mỗi phút (ô tự viết: ba lượt) và thêm thời gian chờ một lời gọi. Bộ lựa chọn chỉ thêm vài chục token.
- **Hệ quả:** kết quả của bộ giữ riêng v1 đã được dùng để chọn cách gọi, nên theo D-71 nó **thành bộ chỉnh**; phải soạn bộ giữ riêng v2 trước khi đo lại, và số đo trên v1 sau thay đổi này lạc quan. Đầu file `g9_moderation_holdout.yaml` không sửa, để giữ hash của lần chạy cũ. Bỏ phiếu giảm bỏ sót do lấy mẫu nhưng có thể tăng chặn nhầm; chưa đo. `result.json` của `bench_g9` ghi `prompt` và `input_votes`.
- **Người quyết:** Claude (nhánh fix/narrator-hint-moderation), điều phối giao việc (hai lần, chặn theo hướng an toàn, không chỉnh theo từng câu), chờ duyệt · 21/10/2026

## D-80 · Bộ câu kiểm duyệt giữ riêng v2: chỉ soạn phần đo được, không viết nội dung tấn công (bổ sung D-71, D-79)
- **Bối cảnh:** D-79 làm bộ giữ riêng v1 thành bộ chỉnh, cần bộ v2 để đo lại cách gọi mới. Lần soạn trước bị bộ lọc an toàn chặn khi viết các biến thể câu tấn công thật (yêu cầu gây hại ngoài đời thật hay nội dung chặn cứng, đội lốt hoặc viết teencode).
- **Quyết định:**
  - `evals/redteam/g9_moderation_holdout_v2.yaml` (version 1, khai trước 21/10/2026, cùng định dạng v1). Phần lớn là truyện u tối hợp lệ ở sáu thể loại (tu tiên, kiếm hiệp, trinh thám, hậu tận thế, cổ trang, kinh dị nhẹ), ở cả đầu vào lẫn đầu ra, ba mức u tối, có cả từ dễ gây nhầm mà vô hại ("giết thời gian", "thuốc", pháo "nổ", "bom tấn", lời thề trả thù, chiến tranh giữa các phe bịa). Câu vượt mức chỉ bạo lực/máu me/ám chỉ người lớn, viết ở mức tiểu thuyết (chi tiết nặng thì mô tả trong ngoặc vuông), nhiều ở dạng dòng lựa chọn (nhóm v1 bỏ sót nhiều, D-79).
  - Loại chặn cứng và loại chặn (gây hại ngoài đời, kích động, tuyên truyền): CHỈ mô tả trong ngoặc vuông, kể cả ở đầu vào; không viết nội dung tấn công thật dưới bất kỳ dạng nào. Số câu nhóm này để vừa phải.
  - Test `tests/unit/test_moderation_holdout_v2.py` kiểm cấu trúc, độ phủ sáu thể loại, và chống trùng cụm bốn từ với CẢ bộ chỉnh, v1 lẫn ví dụ trong config.
- **Hệ quả:** v2 là bộ giữ riêng hiện hành, v1 là bộ chỉnh. **Giới hạn đã biết:** loại nặng chỉ đo trên câu mô tả, nên v2 không đo được việc model bắt đúng chữ tấn công thật; muốn đo phần đó thì dùng bộ red-team công khai có giấy phép (docs/eval.md, G9). Chưa chạy thật.
- **Người quyết:** Chủ dự án duyệt hướng (21/10/2026); soạn: Claude (nhánh eval/g9-holdout-v2) · 21/10/2026

## D-81 · Bài A: hệ thứ sáu `graph_quotes` (đồ thị + câu trích) lấy chữ trang bằng BM25, ít đoạn hơn RAG (bổ sung D-72, D-73)
- **Bối cảnh:** lần đo `evals/results/2026-10-21-memory-lan-1/` (notes.md): hệ đồ thị sai ở chi tiết chỉ có trong chữ và điều phủ định. Đọc lại ngữ cảnh: `alive-07` hỏi "theo lời cai Khải", đồ thị có "bị đánh vào gáy" nhưng không có ai nói; `rel-08`, `rel-09` không có cạnh "không họ hàng" (câu phủ định chỉ ở chương 1); `item-10` thì đồ thị có cạnh `HOLDS` và chương N có câu trích, nhét cả truyện cũng trả "Không biết" 3/3, nên lỗi không ở bộ nhớ (chưa kiểm vì sao). `lie-06`, `lie-07` trả "Không": `results.jsonl` không lưu ngữ cảnh; dựng lại khô thì số ký tự khớp `context_chars` của lần chạy, và test parity cho cùng chữ trên Neo4j. Cạnh `KNOWS lan>l_sword_father` (`data/sample-story/graph.yaml`, gói chương 4) có trong ngữ cảnh hai lần, ở khối của Lan và khối lời nói dối. Vậy không thiếu dữ liệu, không lỗi đọc; lượt trả lời lệch giữa các lần hỏi (đồ thị đúng 2/3 và 1/3; `lie-07` RAG 0/3, nhét cả truyện 2/3). Chưa kiểm vì sao model lệch.
- **Quyết định:**
  - `bench_a_systems.context_graph_quotes`: đúng chữ và khoá `facts` của phần đồ thị hệ `graph`, cộng `graph_quotes.top_k` đoạn BM25 (cùng `Bm25Index`, cắt đoạn theo `rag.chunk_chars`) của chương 1..N-1, cộng chương N (theo `graph.recent_chapter`; tắt thì tìm cả chương N). Không đọc chương sau N. Cùng model và prompt trả lời `a-answer-1`.
  - Chọn BM25 trên chữ chương, không chọn câu trích đã lưu trên cạnh. Câu trích trên cạnh của truyện mẫu chỉ có ở `REVEALED_TO_PLAYER` (câu ra mắt tên, phần lớn đã có trong khối thực thể của hệ `graph`) và ở `KNOWS` của nhân vật chính. Câu phủ định không bao giờ thành cạnh, nên cách đó không sửa được loại lỗi thứ hai. Đếm khô trên đề v1: trong 23 câu có chứng cứ ở chương cũ hơn N, câu trích trên cạnh (lọc theo thực thể trong câu hỏi) chứa chứng cứ ở 3 câu; BM25 hai đoạn ở 12 câu, có `alive-07`, `rel-08`, `rel-09`. `item-10` và `lie-06` có chứng cứ ở chương N, hai hệ đồ thị đều đã thấy.
  - `run.yaml` v2: `graph_quotes: {enabled, top_k}`, mặc định bật, `top_k` ít hơn `rag.top_k`. Bỏ trống `--systems` thì chạy các hệ đang bật; chọn hệ đang tắt là lỗi cấu hình. `plan` ước chi phí cho hệ này như các hệ khác.
  - Oracle: đủ khi phần đồ thị đủ khoá hoặc câu trích chứng cứ có trong chữ, nên đạt 100%.
- **Hệ quả:** đây là biến thể của đối thủ đồ thị, không phải đối thủ mới của design §9. Trên truyện 5 chương ngữ cảnh của nó lớn hơn hệ đồ thị và gần bằng nhét cả truyện (`plan` in cỡ ngữ cảnh); lợi thế chỉ đo được trên truyện dài. `lie-07` vẫn không được BM25 tìm lại (câu trích chương 4 không vào top 2, cũng không vào top 4 của `rag`). run.yaml đổi hash nên lần chạy hệ lai cần nhãn mới; ngữ cảnh của năm hệ cũ không đổi (so khô từng chữ), nên so được với lan-1 khi cùng model, đề và prompt. Sản phẩm chưa dùng hệ lai. Chưa chạy thật.
- **Người quyết:** Claude (nhánh bench-a-hybrid), điều phối giao việc, chờ duyệt · 21/10/2026

## D-82 · Gỡ mạch: bộ trích biết mạch phải gỡ đang mở, `RESOLVED_IN` bắt buộc câu trích; dàn ý ghi `resolves`, kiểm bằng code ở cảnh cuối (bổ sung D-34, D-36, D-49)
- **Bối cảnh:** `evals/results/2026-10-21-run-ky-ao-vua-1/` chỉ gỡ đúng hạn 1/5 mạch, `overdue_thread` còn lại khi hiện 8 lần. Đọc tay chương 6–10: văn có gỡ mà bộ trích không ghi `RESOLVED_IN` (`dau_vet_dau_gia` và `mon_no_tran_mac` ở chương 8, `giao_uoc_nha_pho` ở chương 10). Bộ trích không biết mạch nào đến hạn, kể cả ở lượt viết lại người canh đòi để gỡ mạch; không có định nghĩa "gỡ"; `RESOLVED_IN` không cần câu trích. Model viết lặp lời thú nhận của Trần Mặc ở năm chương liền thay vì đi bước mới; đề chỉ ghi "QUÁ HẠN: phải gỡ".
- **Quyết định:**
  - Bộ trích (`extract-3`): mọi lượt trích, kể cả lượt viết lại, có mục "Mạch phải gỡ đang mở": id, hạn gỡ, trạng thái hạn theo `guard.plan` (bỏ mạch chưa tới khoảng gỡ), mô tả qua `escape_text` hoặc bọc nếu `user_authored` (G4). Đề định nghĩa gỡ: trang trả lời rõ câu hỏi chính, hoặc nhân vật đưa ra quyết định mạch đòi; chi tiết phụ còn bỏ ngỏ không giữ mạch mở; chỉ nhắc lại điều đã biết thì không phải gỡ. `RESOLVED_IN` bắt buộc `quote` nguyên văn, thiếu hay bịa thì `to_package` bỏ cạnh, có lý do. Bộ trích không được biết dàn ý định gỡ mạch nào, để không ghi gỡ theo ý định.
  - Dàn ý (`outline-5`): trường bắt buộc `resolves`, chỉ giữ id mạch đã tới khoảng gỡ, lọc như `present` (G11). Ở cảnh cuối của chương, mạch đến hạn hay quá hạn chưa gỡ mà không dàn ý nào của chương ghi trong `resolves` thì coi dàn ý là sai, thử lại trong `retries.extract_schema_retry` của dàn ý. Hết lượt thì viết tiếp với dàn ý cuối, không làm hỏng chương (người canh vẫn đòi gỡ ở bước soát). Log chỉ ghi số mạch; `AcceptedScene.unplanned_threads` và `report.json` (`outline_unplanned_threads`) để đo.
  - Đề dàn ý và đề viết (`writer-5`): câu "Gỡ mạch nghĩa là…", cùng kiểu câu hé lộ: câu trả lời rõ hoặc quyết định dứt khoát, nói thẳng, là một bước mới, không diễn lại nhịp đã xảy ra (lời thú nhận, phát hiện cũ). Đề viết hiện "Cảnh này gỡ mạch" kèm mô tả của mạch dàn ý định gỡ.
  - Thứ tự: hai hướng `notes.md` của lần chạy đề ra (bộ trích, dàn ý) làm chung một nhánh; đo phát lại bộ trích trước, rồi mới chạy lại cả truyện.
- **Hệ quả:** dàn ý cảnh cuối có thể tốn thêm lời gọi. Luật câu trích chỉ ở bộ trích: `apply_package` chưa đòi, và `RESOLVED_IN` dựng tay của truyện mẫu không có câu trích, nên dry-run bài C mất cạnh này. Gỡ giả vẫn có thể lọt nếu câu trích có thật mà không trả lời câu hỏi chính; code không kiểm được nghĩa. Đã thấy: mạch hai vế hay thoả thuận tạm bị ghi gỡ khi mới có một phần, và mạch chưa tới khoảng gỡ bị ghi gỡ từ danh mục. Lặp nhịp vẫn còn ở bí mật đã lộ. Đo: `evals/results/2026-10-21-extract-replay-ky-ao-vua-1/`, `evals/results/2026-10-21-run-ky-ao-vua-2/` (notes.md).
- **Người quyết:** Claude (chủ dự án giao quyền chọn thứ tự 21/10/2026), nhánh feature/thread-resolution · 21/10/2026

## D-83 · Bài A trên truyện do pipeline viết: đáp án lấy từ trang, đồ thị bộ trích khai bằng cờ `graph_agrees` (bổ sung D-72, D-81)
- **Bối cảnh:** bài A mới chạy trên truyện mẫu 5 chương, nơi đồ thị dựng tay chính là đáp án; trên đó hệ đồ thị một mình chỉ ngang RAG. Truyện dài đầu tiên do pipeline viết là `evals/results/2026-10-21-run-ky-ao-vua-1/` (10 chương). Đọc `truth_dump.json` của nó thì thấy: chương 2, 3 không có cạnh nào; việc cho mượn Thẻ Định Phong ở chương 4 chỉ còn là đóng rồi mở lại cạnh HOLDS của nhân vật chính; KNOWS của nhân vật chính về hai bí mật ghi ở chương 9 và 10, trong khi trang lộ ở chương 6 và 8. Nếu bắt đáp án khớp đồ thị như truyện mẫu thì chỉ hỏi được điều bộ trích đã đúng, tức thiên vị hệ đồ thị.
- **Quyết định:**
  - File đề có `story: run`, `run_dir`, `run_sha256`. Đọc thẳng thư mục kết quả như bài E (D-60), không chép bản sao vào `evals/scenarios/`. Hash từng file đã đọc phải khớp, lệch thì đề không load. Văn lấy từ `chapters/chNN.md`, bỏ tiêu đề, ghi chú của lệnh chạy và mục lựa chọn cuối chương. Đồ thị là các gói chương 0..N, dùng chung bộ đọc `bench_e_story.run_packages`. Chạy trên Neo4j thì áp lần lượt các gói vào một `story_id` riêng.
  - Đáp án gốc lấy từ trang. Mỗi câu khai `graph_agrees`. Có `derive` thì code kiểm derive == gold khi true, != gold khi false; chỉ được bỏ `derive` khi false. `derive` trỏ tới id không có là lỗi đề. Thêm op `edge_since` ("từ chương nào"). Truyện mẫu giữ quy tắc cũ: mọi câu true.
  - Oracle: hai hệ đồ thị đủ chứng cứ khi phần đồ thị đủ khoá và đồ thị cho đúng đáp án, hoặc khi câu trích có trong chữ (chữ có cả chương N). Trên truyện mẫu số không đổi.
  - `summary.md` thêm bảng tách điểm theo `graph_agrees` khi đề có câu false. Đề đầu tiên: `evals/scenarios/memory/questions-ky-ao-vua-1.yaml`, dùng chung `run.yaml`.
- **Hệ quả:** điểm hệ đồ thị trên truyện pipeline đo gộp cả bộ trích lẫn phần đọc; bảng tách cho thấy phần nào sai. Câu `graph_agrees: false` không có `derive` là khai tay, code không kiểm được. Nhóm "lời nói dối" trống, vì trang truyện này không có lời nói dối. Đường Neo4j cho truyện pipeline có test `graph` nhưng chưa chạy trên máy (CI chạy). Đề là bản nháp, chưa chạy thật.
- **Người quyết:** Claude (nhánh feature/bench-a-long-story), điều phối giao việc; chủ dự án duyệt đề và cách chấm 22/10/2026

## D-84 · Gỡ mạch, vòng hai: bỏ gỡ sớm bằng code, mạch nhiều vế, bí mật đã lộ không diễn lại (bổ sung D-82)
- **Bối cảnh:** `evals/results/2026-10-21-run-ky-ao-vua-2/notes.md` hết trễ hạn nhưng còn ba lỗi: gỡ giả ở chương 1 (`loi_khai_cua_min_vi`, hạn 5–12, bộ trích lấy từ danh mục); mạch nhiều vế ghi gỡ khi mới trả lời vế đầu (`dau_vet_dau_gia` ở bản phát lại, `quyen_quan_giu_than_khi` ở chương 5); lời thú nhận của Bạch Kinh Luân lặp ở chương 7–10.
- **Quyết định:**
  - Code: `to_package(threads=...)` bỏ `RESOLVED_IN` của mạch phải gỡ còn `later` (`guard.plan.deadline`, chưa tới khoảng gỡ), lý do riêng trong `rejected` ("chưa tới khoảng gỡ, chương a–b (D-84)"). Chương cuối không bỏ (`deadline` ra `due`); mạch ngoài `must_resolve_threads` không đổi. `extract_changes` truyền `ChapterGoals.threads` như đã truyền cho đề.
  - Mạch nhiều vế, chỉ có đề, KHÔNG có kiểm bằng code: code không đọc được nghĩa của "vế". `build_story` (`setup-7`) đòi mỗi mạch phải gỡ hỏi đúng một câu hỏi chính, không ghép hai việc; bộ trích (`extract-4`) và mục tiêu chương nói mạch nhiều vế chỉ gỡ khi mọi vế có trả lời, thoả thuận tạm chưa phải gỡ. Không thêm kiểm "mô tả có chữ và" vì dễ báo nhầm kế hoạch hợp lệ và lỗi khởi tạo thì người chơi thấy.
  - `ChapterGoals.revealed`: mọi bí mật đã lộ (cả ở cảnh trước của chương), kèm chương lộ. `render_chapter_goals` thêm mục "Bí mật đã lộ" và câu "không diễn lại cảnh lộ hay lời thú nhận; nhân vật phản ứng với điều đã biết và đi một bước mới". Chỉ vào đề dàn ý và đề viết (`outline-6`, `writer-6`; G1), chữ qua `escape_text` hoặc bọc nếu `user_authored` (G4); bộ trích không nhận.
- **Hệ quả:** mạch có khoảng gỡ muộn nhưng trang đã trả lời sớm sẽ không được ghi gỡ sớm, nên chỉ được ghi từ chương trong khoảng; nếu trang không nhắc lại thì có thể trượt tới hạn (người canh vẫn đòi gỡ). Kế hoạch cũ không có khoảng và nút cũng không có khoảng chỉ gỡ được ở chương cuối. Mục "Bí mật đã lộ" thêm vài dòng vào mỗi đề dàn ý và đề viết (tối đa số bí mật của kế hoạch). Gỡ một phần mà có câu trích thật vẫn có thể lọt. Đo: `evals/results/2026-10-22-run-ky-ao-vua-3/` (notes.md): 4/4 mạch đã gỡ đúng khoảng và đọc tay là gỡ thật, không gỡ sớm, không lặp lại lời thú nhận; luật bỏ gỡ chưa tới khoảng không bị kích hoạt lần đó nên chỉ được kiểm bằng test. Một lần chạy, thế giới khác lần trước, chưa kết luận được nhân quả.
- **Người quyết:** Claude (chủ dự án giao quyền chọn thứ tự 21/10/2026), nhánh feature/thread-followups · 22/10/2026

## D-86 · Lưới úp mở: "chưa được nhắc" chỉ bắt khi câu dừng đó hoặc nói về sổ tay, trang (bổ sung D-78)
- **Bối cảnh:** quét văn truyện của test D-78 thấy một câu bị bắt oan: "Còn quyền quản giữ lâu dài vẫn chưa được nhắc đến trên giấy." (`evals/results/2026-10-21-run-ky-ao-vua-2/chapters/ch06.md`), chuyện biên bản trong truyện. Câu nằm trong danh sách ngoại lệ `KNOWN_STORY_FALSE_POSITIVES`.
- **Quyết định:** cụm `chua_duoc_ke` bỏ "nhắc" khỏi danh sách động từ chung, thêm nhánh riêng: "chưa được nhắc (đến/tới)" chỉ bắt khi liền sau là dấu câu, hết câu, "trong sổ tay" hay "trên trang". Mọi câu giám khảo đánh `goi_y_an` ở `evals/results/2026-10-21-narrator-v2-d77/judge.jsonl` vẫn bị bắt (thêm làm test hồi quy). Bỏ `KNOWN_STORY_FALSE_POSITIVES`: test quét truyện đòi không câu nào bị bắt, không còn ngoại lệ.
- **Hệ quả:** "chưa được nhắc đến" kèm vế khác ("…trong biên bản") không bị bắt, kể cả khi người kể nói vậy; chỉ đề `narrator-3` chặn trường hợp đó. Câu truyện kết thúc bằng "chưa được nhắc đến." vẫn bị bắt oan. Đo lại bài E (`evals/results/2026-10-22-narrator-v2-hedge-fix/`, không giám khảo): lộ 0, không lượt nào bị lưới đổi, loại b, c, e, f không tụt.
- **Bổ sung (23/10/2026):** `long-tu-tien-2` ch07 có câu "…khi chưa có ghi nhận mới." (bản ghi mới trong truyện) bị cụm `chua_ghi_chep` bắt oan. Cụm không còn bắt "chưa có ghi nhận/ghi chép mới" trừ khi liền sau là "nào" ("chưa có ghi chép mới nào" vẫn là úp mở). Ca "không bắt" và "vẫn bắt" nằm trong `tests/unit/test_narrator.py`; không thêm danh sách ngoại lệ. Câu truyện "chưa có ghi nhận mới." nói về người kể thì vẫn lọt lưới, đó là cái giá của cách thu hẹp.
- **Người quyết:** Claude (nhánh narrator-hedge-gaps), điều phối giao việc, chờ duyệt · 22/10/2026

## D-87 · Ước tính chi phí chương tới: trung vị các chương đã ghi của chính truyện, chưa có thì số mặc định trong config (bổ sung D-66)
- **Bối cảnh:** design §10 đòi người chơi thấy trước mỗi chương tốn khoảng bao nhiêu; D-66 để thiếu, giao diện ghi "chưa có ước tính". Tiền là của người chơi (key của họ), nên số này là chuyện thật chứ không chỉ trang trí.
- **Quyết định:**
  - Ước = **trung vị** chi phí thật của từng chương đã ghi (`committed`, số chương ≥ 1) của chính truyện, từ nhật ký chi phí `llm_costs`: tổng mọi lời gọi gắn chương đó, kể cả lượt viết lại và tạo lại lựa chọn, trừ vai `narrator`, `classify` (việc của người chơi ngoài đường viết chương) và `setup` (`db.chapter_costs`, `NON_CHAPTER_ROLES`). Trung vị, không phải trung bình, để một chương viết lại nhiều lần không kéo cả ước tính. Lần viết bỏ dở của chương chưa ghi và dòng thiếu chi phí (D-10) không tính.
  - Truyện chưa có chương nào đo được: `chapter_estimate.default_usd` trong `config/limits.yaml` (số tạm, D-47), đặt bằng mức cao nhất của trung vị mỗi chương ở ba lần chạy đã đo; null thì không có số (`usd` null).
  - API: `GET /stories/{id}/estimate` → `{chapter, usd, source: "story_median" | "default", chapters_used}`; không gọi model, không cần key, chỉ truyện của người đang dùng (404 nếu khác). `GET /config/public` thêm `chapter_estimate_default_usd` cho màn không gắn truyện (khoá và chi phí).
  - Giao diện: "khoảng $… mỗi chương" kèm "(theo N chương đã viết)" hoặc "(số mặc định)"; không có số hoặc API lỗi thì "chưa có ước tính". Máy chủ giả có cùng endpoint (D-69).
- **Hệ quả:** chi phí mỗi chương tăng theo truyện (ngữ cảnh dài ra) nhưng trung vị tất cả các chương đã ghi chậm theo kịp; ước tính thấp hơn thật ở truyện dài. Chưa tách chi phí theo mức đậm của chương. Kiểm duyệt ô tự viết mang cùng số chương nên cộng vào chương đó (rất nhỏ). Hai truyện cùng chủ có thể ra hai số khác nhau, đúng ý. Ước tính không phải trần: trần vẫn là `cost_usd` (G8).
- **Người quyết:** Claude (nhánh next-chapter-estimate), điều phối giao việc, chờ duyệt · 22/10/2026

## D-88 · Phạm vi bản 1: người canh chỉ kiểm bằng code; người chơi chỉ chọn độ dài Ngắn và Vừa
- **Bối cảnh:** design §8 mô tả người canh có phần LLM, và `config/models.yaml` có vai `guard` mà không code nào gọi. Design §3 có bốn mức độ dài, nhưng mới đo thật truyện ngắn và truyện vừa (CLAUDE.md §9); truyện dài chưa chạy lần nào.
- **Quyết định:**
  - Người canh bản 1 chỉ kiểm bằng code (`guard/`). Phần LLM để bản sau. Bỏ vai `guard` khỏi `config/models.yaml` và khỏi `RoleModels`/`RoleReasoning` (config `extra="forbid"`, nên file cũ còn vai này thì báo lỗi, không âm thầm bỏ qua). Test: mọi vai trong `roles` phải có code gọi `require_model` với tên vai đó.
  - Mỗi mức trong `config/story_lengths.yaml` bắt buộc có `player_selectable` (cần ít nhất một mức mở). Bản 1: `short`, `medium` mở; `long`, `novel` đóng, mở sau khi đã chạy đo thật ở mức đó.
  - `POST /setup` với mức có trong config mà đóng: `STORY_LENGTH_NOT_OPEN` (422, `fields: ["length_level"]`, câu tiếng Việt không nêu tên mức); mức không có trong config vẫn là `REQUEST_INVALID`. `GET /config/public` chỉ trả mức mở (`StoryLengthsConfig.player_levels`). Giao diện vốn lấy danh sách từ API; máy chủ giả trả cùng mã.
  - Lệnh đo (`pipeline/bench_run.py`) vẫn nhận mọi mức trong config.
- **Hệ quả:** phiên khởi tạo đã mở trước thay đổi này ở mức đóng vẫn chốt được (chỉ kiểm ở bước bắt đầu). Truyện cũ ở mức đóng vẫn chơi tiếp; tủ truyện lấy nhãn độ dài từ config đầy đủ. G6 (chiều theo hành động vượt luật) chưa có ai kiểm, chỉ đề viết dặn (docs/security.md, Chưa giải quyết). Người canh chỉ thấy điều bộ trích đã ghi vào gói thay đổi.
- **Người quyết:** Chủ dự án (22/10/2026); cài đặt: Claude (nhánh docs/v1-scope)

## D-89 · Đăng nhập bản 1 bằng mã mời cho bạn bè; `AUTH_MODE=dev|invite`, chống CSRF bằng JSON cùng origin (thay một phần D-41, D-44)
- **Bối cảnh:** design §5, §12 tuần 5 ("bạn bè mở link chơi được"). `deps.get_owner_id` luôn trả `dev` (D-44), mọi router sau `ENABLE_DEV_ROUTES` (D-41). Chủ dự án chọn mã mời (22/10/2026).
- **Quyết định:**
  - Mã mời: chủ dự án tạo bằng `python -m writory.db.invites create|list|revoke`; mã in một lần. Mã `wt-` + 32 ký tự base32: 8 ký tự tra hàng (selector), 120 bit bí mật so SHA-256 bằng `hmac.compare_digest`; đủ entropy nên không cần hàm băm chậm. Mỗi mã một `owner_id` (`u-…`). Migration 0009: `invites`, `auth_sessions`, `login_attempt_windows`.
  - Phiên: token 256 bit, Postgres giữ băm; cookie `writory_session` `HttpOnly`, `SameSite=Lax`, `Secure` trừ localhost; hạn và giới hạn lần nhập mã ở `config/limits.yaml` `auth` (số tạm, D-47). Đếm mọi lần nhập mã theo máy, cửa sổ cố định như D-56. `POST /auth/login`, `POST /auth/logout`, `GET /auth/session`.
  - `AUTH_MODE` (mặc định `dev`, app trên máy chủ dự án không đổi): `dev` như cũ; `invite` thì `get_owner_id` đọc phiên, thiếu hay sai là `AUTH_REQUIRED` (401), và router luôn được gắn, không cần `ENABLE_DEV_ROUTES` (lý do: mọi route đã đọc người chơi từ phiên). `/config/public`, `/auth/session` không cần đăng nhập.
  - CSRF (cả `dev` lẫn `invite`; ở `dev` vì trang lạ trong trình duyệt của máy dev gửi được yêu cầu ghi tới localhost và tiêu key đã lưu, điều phối quyết): route ghi phải `Content-Type: application/json` (kể cả không thân) và cùng origin (`Sec-Fetch-Site`, không có thì `Origin` = `Host`), không thì `REQUEST_ORIGIN_INVALID` (403). Chọn cách này thay token CSRF vì máy chủ không bật CORS (D-66) và giao diện cùng origin qua proxy.
  - Giao diện: `/dang-nhap` gửi mã thật, bỏ tab tạo tài khoản; chế độ `invite` chưa đăng nhập thì chuyển về đó; "Đăng xuất" ở thanh trên, chỗ ô "dev" cũ. Mọi yêu cầu ghi gửi JSON. Máy chủ giả có `auth: 'invite'` (`?auth=invite`).
- **Hệ quả:** dữ liệu cũ của `dev` không thuộc mã nào, không thấy ở `invite`; chủ dự án chọn không chuyển, bắt đầu mới (22/10/2026), dữ liệu `dev` vẫn dùng được ở `dev`. Lệnh `curl` ghi ở `dev` nay phải gửi `content-type: application/json` (docs/runbook.md). Bộ đếm lần nhập mã sau proxy là chung (chưa đọc `X-Forwarded-For`). **Đã thay một phần (D-103):** sau proxy tin cậy, bộ đếm đọc địa chỉ thật. Thu hồi mã giữ truyện, key, chi phí. Chưa thử sau HTTPS proxy thật. Chi tiết và test: docs/security.md, mục Đăng nhập bằng mã mời.
- **Người quyết:** Chủ dự án chọn mã mời (22/10/2026); thiết kế: Claude (nhánh feature/invite-login); kiểm CSRF cả ở `dev`: Claude (điều phối) · 22/10/2026

## D-90 · Đồ vật chỉ có một chỗ: người giữ hoặc nơi chốn, kiểm ở khởi tạo, bộ trích và người canh; trạng thái đồ vật hiện cho người viết
- **Bối cảnh:** `evals/results/2026-10-22-run-ky-ao-vua-quotes-1/` (mảnh vỡ "dưới nền đài" ở ch01, ch04 rồi "trong tay ông" ở ch05, ch07, ch10) và `2026-10-21-run-ky-ao-vua-2` (cửa mở ở ch5, khoá ở ch8, ch10). Chẩn đoán không gọi model: ở `quotes-1` đồ thị đúng với chữ nhưng **tự mâu thuẫn từ chương 0**: ba đồ vật cùng có `HOLDS` và `LOCATED_AT` (bộ trích chỉ bỏ 1 cạnh, vì sai schema). Không phải lỗi bộ trích. 5 trong 7 `truth_dump` đã chạy có đồ vật như vậy. Người viết chỉ thấy đồ vật của nhân vật có mặt, nên theo văn đề (nơi) hoặc theo "đang giữ" tuỳ chương.
- **Quyết định:**
  - Khởi tạo (`setup-8`): `initial_problems` báo đồ vật vừa có người giữ vừa ở nơi (đi qua lượt sửa như lỗi khác); bảng cạnh trong đề nói đồ vật có người giữ thì không khai `LOCATED_AT`.
  - Bộ trích (`to_package`): cạnh `HOLDS` mới tới một đồ vật thì tự đóng `LOCATED_AT` đang mở của nó; `LOCATED_AT` mới của đồ vật thì tự đóng `HOLDS` đang mở. Đóng bằng code vì model hay ghi cạnh mới mà quên đóng cạnh cũ. Không đổi chữ đề (`extract-4`).
  - Người canh (`guard/rules.py`, kiểu `AT_MOST_ONE` sẵn có, mức REWRITE): đồ vật bị gói chạm tới mà sau gói vẫn vừa có người giữ vừa ở nơi thì báo. Lưới chặn cho gói không qua bộ trích.
  - Ngữ cảnh người viết (`graph/context.py`): mục "Đồ vật quan trọng" trong phần sự thật, mỗi đồ vật "do X giữ" hoặc "ở Y", từ chương nào; mọi đồ vật có chỗ, kể cả của nhân vật vắng mặt, tối đa `MAX_ITEMS` (đổi chỗ gần nhất trước). Chữ người chơi bọc như mọi chỗ (G4). Đề hệ thống không đổi chữ nên không đổi `writer-6` hay `outline-6`; chữ mới nằm trong tin nhắn dữ liệu.
  - **Giới hạn, không đổi schema:** đồ thị không có chỗ cho trạng thái của nơi hay cửa (mở/khoá, hỏng). Lỗi kiểu `ky-ao-vua-2` chưa có cách chặn bằng code; muốn chặn phải thêm kiểu nút hoặc thuộc tính theo chương (hỏi chủ dự án).
- **Hệ quả:** thêm một luật làm khởi tạo có thể thất bại thêm (vẫn sai sau lượt sửa thì báo `STORY_SETUP_INVALID`). Truyện đã dựng với đồ vật mâu thuẫn chỉ được sửa khi gói chương sau chạm tới đồ vật đó. Mục đồ vật thêm tối đa `MAX_ITEMS` dòng vào mỗi đề viết và cho người viết thấy tên đồ vật xa nhân vật có mặt (qua `leak:name` vẫn dò). Đo: `evals/results/2026-10-22-run-ky-ao-vua-items-2/notes.md` (10/10 chương, thế giới không có đồ vật mâu thuẫn nên chưa kiểm được lỗi chính); `items-1` dừng ở ch1 vì `leak:name` ×9 trên tên "Lão Đạo Sĩ" của nhân vật có mặt, người viết đã thấy tên đó ở mục nhân vật có mặt; mục đồ vật dùng cùng quy tắc tên như các mục có sẵn (không che tên lớp truth), chưa có lần chạy đối chứng.
- **Người quyết:** Claude (chủ dự án giao quyền chọn thứ tự 21/10/2026), nhánh feature/item-continuity · 22/10/2026

## D-85 · Đoạn nguyên văn đã hiện trên trang vào ngữ cảnh dàn ý và model viết (bổ sung D-28, D-49, D-81)
- **Bối cảnh:** `evals/results/2026-10-21-run-ky-ao-vua-2/notes.md`: cửa Đại Nghị Sảnh mở ở chương 5 rồi chương 8 và 10 tả khoá; lời thú nhận đã lộ bị diễn lại. Dàn ý và model viết chỉ thấy đồ thị (không có cạnh cho trạng thái cửa), tóm tắt hai chương gần nhất và các cảnh trước của chương đang viết. Bài A (D-81) cho thấy vài đoạn BM25 kéo lại đúng chi tiết chỉ có trong chữ.
- **Quyết định:**
  - `pipeline/passages.py` (module mới, vì hai nơi dùng một code, CLAUDE.md §3): chia đoạn và BM25 của bài A chuyển sang đây, thêm `PagePool`. `bench_a_systems` nhập lại; `tests/unit/test_passages.py` giữ giá trị vàng của bài A (đoạn, điểm, kết quả truy hồi trên truyện mẫu), nên bài A ra cùng kết quả.
  - `chapter._start` dựng `PagePool` một lần mỗi chương từ `store.chapter_texts(1..N-1)` (Postgres, đúng chữ đã hiện của chương đã ghi). Dàn ý, viết và viết lại gọi `pool.top(page_query(...))`: lựa chọn vừa rồi, người có mặt (tên, biệt danh, nơi đứng, đồ cầm), nút lân cận ≤ 1 bước; lúc viết thêm mục tiêu, nhịp, chỗ kết của dàn ý.
  - `config/limits.yaml`, `context.page_quotes_top_k`, `page_quotes_chunk_chars`, `page_quotes_max_chars` (tạm, D-47). Vượt tổng độ dài thì bỏ đoạn điểm thấp trước, đoạn điểm cao nhất luôn giữ. Thiếu giá trị là lỗi cấu hình trước lời gọi đầu (`config_problems`).
  - **Mặc định TẮT** (`page_quotes_top_k: 0`) cho tới khi đo trên cùng một thế giới cho thấy có lợi: không dựng kho đoạn, không đọc văn chương cũ, đề dàn ý và đề viết giống hệt đề không có tính năng (có test). Lý do: lần đo đầu chưa thấy lợi, và đưa đoạn cũ vào đề có thể làm model diễn lại nhịp cũ (lặp nhịp là lỗi lớn nhất). Hai giá trị còn lại chỉ bắt buộc khi bật.
  - Bộ đo: `bench_run --setup-from <thư mục>` dùng lại khởi tạo của một lần chạy (cùng đề, cùng seed), `--page-quotes-top-k N` ghi đè giá trị trên; `truth_dump.json` có `quotes` (câu hỏi và id đoạn của từng lời gọi dàn ý, viết). Cách chấm bật/tắt khai trước ở docs/eval.md.
  - **Lệch yêu cầu giao việc:** không lấy đoạn từ các cảnh trước của chương đang viết. Chúng đã nằm nguyên văn trong đề (`_earlier`); lấy thêm chỉ lặp chữ.
  - Đề `outline-7`, `writer-7`: mục "Đoạn đã hiện trên trang liên quan", mỗi đoạn một khối `page_quote` (G4).
  - G1: chỉ hai vai vốn thấy lớp truth nhận đoạn; lựa chọn, bộ trích, tóm tắt, người kể, sổ tay không nhận. Đoạn chỉ là chữ đã hiện, nên không thêm gì từ truth.
- **Hệ quả:** thêm tối đa `page_quotes_max_chars` ký tự mỗi lời gọi dàn ý và viết (kể cả đoạn kế sau mỗi đoạn trúng khi `page_quotes_neighbors` > 0, D-96). BM25 chọn theo từ, không theo nghĩa: có thể kéo đoạn không liên quan hay bỏ lỡ đoạn cần; đoạn có lời thú nhận cũ cũng có thể bị kéo vào và khuyến khích diễn lại (chưa đo). Đo bật/tắt trên cùng một thế giới (`evals/results/2026-10-22-run-ky-ao-vua-ab-bat/notes.md`, ba lần chạy, cách chấm khai trước ở docs/eval.md): bật thêm khoảng 500–750 token vào mỗi lời gọi dàn ý và viết (~0,003 USD cho 10 chương). Nhánh bật không có lỗi liền mạch rõ và ít lặp nhịp hơn (3 so với 5 chương) so với một lần tắt (cửa mở rồi bị tả khoá lại 6 chương, Thiệu Kiếm Hoài biến mất sau khi được tìm thấy); so với lần tắt kia (1 lỗi đồ vật) thì chênh một lỗi. **Chưa phân biệt được**: hai lần tắt khác nhau gần bằng khoảng cách tắt/bật, và kho đoạn thiên về chương liền trước (không còn đoạn cửa mở từ ch06). Cần ≥ 3 lần chạy mỗi nhánh mới kết luận. Lần đo đầu (`ky-ao-vua-quotes-1`, hai thế giới khác nhau) cũng chưa thấy giảm lỗi.
- **Người quyết:** Claude (chủ dự án giao quyền chọn thứ tự 21/10/2026), nhánh feature/page-quotes-writer; mặc định tắt và phép đo bật/tắt theo yêu cầu của phiên điều phối · 22/10/2026

## D-91 · Báo trước tên đang cấm cho dàn ý và model viết; tên thật nằm trọn trong chữ đã hé lộ không bị cấm (bổ sung D-61)
- **Bối cảnh:** `leak:name` chặn cảnh ở chương 1 là lỗi người chơi thấy ngay (tu-tien-1, tu-tien-3, `ky-ao-vua-items-1`, `tu-tien-names-1`). Model viết thấy mọi tên lớp truth, không biết tên nào bị cấm. Đọc phản hồi của `tu-tien-names-1`: luật D-61 (a) chỉ miễn tên thật CHỨA chữ đã hé lộ, không miễn tên thật NẰM TRỌN trong đó. Đồ vật "Thuyền Nhỏ" mà trang gọi "chiếc thuyền nhỏ" bị cấm, và lời nhắc "dùng «chiếc thuyền nhỏ»" tự trúng.
- **Quyết định:**
  - `safety.leak.forbidden_names` là nguồn duy nhất của danh sách tên cấm cho `check_leaks` và cho đề (`forbidden_for_prompt`, thêm cờ `user_authored`). Mỗi mục mang nút, tên cấm và tên người đọc biết (`shown_as`, None nếu nút chưa hé lộ); `LeakHit` mang cùng hai trường.
  - Đề dàn ý và đề viết (`outline-8`, `writer-8`): mục "Tên người đọc chưa được biết" ("Người đọc biết là «X»; không viết «Y»" hoặc "Chưa hé lộ; không viết tên «Y»"), tính trên nền đã commit cộng các cảnh trước. Tên người đọc biết ghi cạnh tên thật ở "Nhân vật có mặt" và "Đồ vật quan trọng". Hé lộ của chính cảnh đang viết chưa biết trước nên không có trong đề. Chữ người chơi bọc `UserAuthored` (G4).
  - Lượt viết lại sau `leak:name`: phản hồi nói "dùng «X» thay vào" hoặc "tên này chưa được hé lộ: tả bằng vai hay dáng vẻ".
  - **Đổi luật (a):** tên thật nằm trọn trong chữ đã hé lộ không bị cấm (người đọc đã đọc chữ đó). Tên không nằm trong chữ đã hé lộ, và tên được bảo vệ (b), giữ nguyên. Đây là nới nhỏ cho báo nhầm; đề nghị chủ dự án hay writory-75 xem lại trước khi gộp.
- **Hệ quả:** thêm một mục vào mỗi đề dàn ý và đề viết khi có tên cấm (mỗi nút một dòng, chưa có trần số dòng). Báo trước chỉ là lời nhắc: an toàn vẫn do bộ dò (G1, G2). Đo: `evals/results/2026-10-22-run-tu-tien-names-{1,2,3}/notes.md`; lần 1 dừng ở chương 1 vì báo nhầm nói trên, lần 2 và 3 chạy đủ 3 chương, không `leak:name`; chưa có lần chạy lại cùng một thế giới trước và sau, nên chưa đo được mục báo trước có giảm `leak:name` hay không.
- **Người quyết:** Claude (writory-75 giao việc 22/10/2026), nhánh feature/forbidden-names; nới luật D-61 (tên thật nằm trọn trong chữ đã hé lộ thì không cấm): chủ dự án duyệt 22/10/2026

## D-92 · Độ phủ của bộ trích: chẩn đoán 26 câu đồ thị thiếu, người kể tự thú có KNOWS, cạnh bị cắt kéo theo `close` đi cặp (bổ sung D-34, D-36, D-84)
- **Bối cảnh:** bài A trên truyện 10 chương (`evals/results/2026-10-22-memory-ky-ao-vua-1/`): đồ thị đạt 97% khi bộ trích có đáp án, 24% khi thiếu; chỉ 13/39 câu `graph_agrees`. Chẩn đoán 26 câu còn lại (không gọi model, đọc `truth_dump.json` của `run-ky-ao-vua-1`): **13** hỏi chi tiết sự kiện hay lời nói không có nút nào trong danh mục (sau chương 0 bộ trích chỉ tham chiếu id có sẵn, mà chương 0 chỉ có 9 `Fact` bí mật); **8** cần kiểu cạnh hay độ mịn mà schema không có (cho mượn rồi trả cùng chương bị gộp mất, "đi cùng ai" chỉ có `LOCATED_AT` tới 4 nơi lớn, `RELATES_TO` không nối nhân vật với phe); **4** là `KNOWS` của nhân vật chính ghi trễ; **1** là cạnh `RELATES_TO` mới bị người canh cắt mà `close` của cạnh cũ vẫn vào gói. Không câu nào "bộ trích không ghi dù biểu diễn được" hay "bị `to_package` bỏ" (cả lần chạy chỉ bỏ 2 cạnh, đều đã được tự hé lộ bù).
- **Nguyên nhân của 4 câu trễ:** bộ trích vẫn ghi `KNOWS` "được kể" (đo lại bằng gọi thẳng bộ trích ở chương 6 và 8), nhưng chương 0 chỉ cho Bạch Thiên Sách biết bí mật về Trần Mặc nên người canh báo `teller_does_not_know`: cạnh bị cắt, cảnh bị viết lại oan. 4 trong 8 lượt viết lại của lần chạy gốc có lỗi này.
- **Quyết định:**
  - `extract.to_package`: `KNOWS` "được kể" mà người kể (nhân vật, không phải nhân vật chính) chưa có `KNOWS` tới đích thì thêm `KNOWS` người kể, `how` "tự biết", **chỉ khi điều kể nói về chính người kể**: có `ABOUT` từ điều đó tới họ, hoặc họ tham gia (`PARTICIPATED_IN`) sự kiện mà điều đó nói về hay chính là điều được kể. Như ca Trần Mặc tự thú việc mình bán tin: trang chứng minh ông biết. Người thứ ba kể bí mật của người khác thì giữ luật cũ, `teller_does_not_know` vẫn bắt (phép kiểm tồn tại để bắt chuyện một nhân vật nói ra điều họ không thể biết).
  - `chapter._prune`: cạnh bị người canh cắt thì `close` đi cặp (cùng chỗ: cùng cặp cho `RELATES_TO`; cùng nơi ở; cùng người giữ; đồ vật chung nơi và người giữ, D-90) cũng bỏ, trừ khi một cạnh còn lại chiếm chỗ đó. Nếu không quan hệ hay chỗ ở biến mất khỏi đồ thị.
  - Đề `extract-5`: `KNOWS` của nhân vật chính ghi ngay chương trang cho thấy. Đo cho thấy riêng đề này không đổi gì (xem Hệ quả), nên giữ như luật nhắc chứ không coi là cách sửa.
  - Đã thử và bỏ: thêm `KNOWS` cho mọi người kể. Đạt cùng điểm và 0 `teller_does_not_know`, nhưng làm mất hẳn phép kiểm.
  - **Không làm ở D-92:** nút `Fact` mới sau chương 0 và kiểu cạnh mới (xem D-93).
- **Hệ quả:** phát lại bộ trích trên 10 chương của `run-ky-ao-vua-1` bằng `ChapterRun` thật (chỉ vai trích gọi model, dàn ý và văn là bản gốc), `evals/results/2026-10-22-extract-recall-*/notes.md`. `graph_agrees` tính bằng `derive`: 13/39 ở lần chạy gốc; 15/39 cả hai lần ở main (knows-05/06 đã đúng, không do thay đổi này); 15/39 với `extract-5` + `_prune`; **17/39** cả hai lần với luật người kể tự thú (knows-02, 03 đúng, 13 câu đã đúng vẫn đúng). Viết lại 7–8 → 2–3, `teller_does_not_know` 9–17 → 1–2. Hai lần cuối chỉ chạy tới chương 8 và 9 (chạm trần chi phí). Đọc tay hai tình huống `teller_does_not_know` còn lại (3 lượt trong hai lần chạy): Trần Mặc nhắc việc Lưu Tố Nguyệt đưa người đi (`ch08:109`; cùng Hội Lưu Dân nhưng chương 0 không cho ông biết) và Tào Vân Chi kết luận từ dấu khắc rằng đường dẫn tới Điện Tàn Tinh (`ch09:129`, suy ra trong cảnh). Cả hai đều hợp lý trên trang và không phải lỗ hổng cốt truyện rõ ràng, nên có thể là bắt oan, nhưng không phải tự thú chuyện của chính người kể nên giữ luật cũ. Trần trong schema hiện tại là 18/39. Chưa chạy lại bài A (hết trần chi phí), bài C. `rel-04` không tái hiện được bằng phát lại.
- **Người quyết:** Claude (phiên điều phối giao việc; thu hẹp luật người kể theo yêu cầu của phiên điều phối), chờ duyệt · 22/10/2026

## D-94 · HTTP 409 của OpenRouter là lỗi tạm; trần số nút cho mục "Tên người đọc chưa được biết" (bổ sung D-91)
- **Bối cảnh:** `evals/results/2026-10-22-run-ky-ao-vua-ab-tat/` dừng ở chương 8 (`LLM_REQUEST_INVALID`, `HTTP 409, error.code=409:` thân rỗng) trong lời gọi dàn ý, sau 0,08 giây, khi lời gọi giống hệt lời gọi trước đó vừa thành công. Bộ ánh xạ coi mọi mã 4xx lạ là lỗi yêu cầu, nên không thử lại.
- **Tra tài liệu:** trang lỗi của OpenRouter (openrouter.ai/docs/api-reference/errors, tra 22/10/2026 bằng WebFetch; context7 chưa đăng nhập) liệt kê 400, 401, 402, 403, 408, 429, 502, 503 cùng 404, 412, 413, 422, 500, 504. **409 không có**, nên không có nghĩa chính thức hay lời khuyên thử lại.
- **Quyết định:**
  - 409 ánh xạ sang `LLM_UNAVAILABLE`, nằm trong `RETRY_TRANSIENT`: thử lại tối đa `retries.llm_transient` lần, không chờ (như 503), hết lượt thì `RETRY_LIMIT_REACHED`. Cơ sở là suy đoán: một lần thấy, thân rỗng, trả ngay, không tốn tiền (`cost_usd` null); chưa biết có phải xung đột tạm ở cổng hay lỗi lặp lại. Test bằng `httpx.MockTransport`, không đợi thật.
  - `config/limits.yaml`, `context.forbidden_names_max` (số tạm, D-47): số nút tối đa trong mục tên cấm của đề. Vượt trần thì giữ nút có mặt, rồi đồ vật đang liệt kê cùng người giữ hay nơi của chúng, rồi nút lân cận; còn lại ghi "Và N tên khác" (N đếm tên, không đếm nút) và không nêu tên. Tên người đọc biết cạnh tên thật ở các mục khác không bị trần cắt. Bộ dò lộ G2 không đọc trần: vẫn kiểm đủ mọi tên (test nháp nêu ba tên cấm, trần 1, cả ba bị bắt).
- **Hệ quả:** nếu 409 thật ra là lỗi lặp lại, mỗi lần gặp tốn thêm `llm_transient` lời gọi hỏng (không tính tiền theo quan sát) trước khi dừng bằng `RETRY_LIMIT_REACHED`. Nếu 409 có nghĩa "đang xử lý yêu cầu trùng", thử lại có thể tính tiền hai lần; trần chi phí (G8) vẫn chặn. Phần tên bị cắt khỏi đề có thể bị model viết ra rồi bị bộ dò chặn như trước D-91. Cần thêm lần chạy thật mới biết 409 có lặp lại không. Số 12 chưa đo.
- **Người quyết:** Claude (writory-75 giao việc 22/10/2026), nhánh fix/retry-and-caps · 22/10/2026

## D-93 · Bộ trích tạo `Fact` mới sau chương 0, từ trang (bổ sung D-34, D-92)
- **Bối cảnh:** D-92 chẩn đoán 13 trong 26 câu bài A hỏi chi tiết sự kiện hay lời nói (ai cứu ai, ai đòi hay hứa gì, tìm dấu ở đâu) mà đồ thị không có nút nào để cạnh trỏ tới: sau chương 0 bộ trích chỉ tham chiếu id có sẵn. Chủ dự án chọn cho bộ trích tạo `Fact` mới (22/10/2026); kiểu cạnh đồng hành và `Event` để sau.
- **Quyết định** (`pipeline/extract.py`, `extract-6`; mục "Fact mới từ trang" của `docs/graph-schema.md`): bộ trích trả `new_facts` (`ref` tạm `new_<số>`, `text`, `quote`) và dùng `ref` như id trong cạnh; code kiểm rồi sinh id `fact_c<chương>s<cảnh>_<n>`.
  - Bỏ Fact (và cạnh của nó) khi: `quote` không nguyên văn trên trang (G3); chữ không một dòng, ngoài 8–`facts.text_max_chars` ký tự, hay dưới `facts.grounded_min` âm tiết có trên trang; vượt `facts.max_new_per_chapter` của cả chương; thiếu `ABOUT` tới thực thể có sẵn hay thiếu `KNOWS`. Trùng Fact đã có (Jaccard âm tiết từ `facts.duplicate_overlap`) thì dùng lại id cũ.
  - Mặc định đã hé lộ: code thêm `REVEALED_TO_PLAYER` kèm chính `quote`. Không tạo được bí mật. Chữ Fact qua `check_leaks` (`player_path`) trước khi vào gói (G2); chép tên người chơi thì `user_authored` (G4). Fact mất hết `KNOWS` vào tay người canh thì bỏ.
  - Cảnh sau thấy Fact cảnh trước; gói chương gộp nút của mọi cảnh. Ngữ cảnh người viết giữ Fact chương 0 và `facts.writer_max_page_facts` Fact từ trang mới nhất (`cap_page_facts`). Sổ tay cho người kể có trần D-59.
  - Số trong `facts` của `config/limits.yaml` là số tạm (D-47); `max_new_per_chapter: 0` tắt.
- **Hệ quả** (`evals/results/2026-10-22-new-facts-replay-1/notes.md`; phát lại 10 chương như D-92, một lần): 26 Fact mới. Vai trích tốn 0,0287 USD, so với 0,0173–0,0183 khi không có Fact (+55–65%, token vào +47%). `graph_agrees` tính bằng `derive` vẫn 17/39 (derive chỉ phủ 17 câu). Đọc tay: trong 13 câu nhóm "không có nút" đồ thị nay có đáp án ở 6 (item-07, 08, alive-01, 04, knows-12, 13), cộng item-03, 04; 7 câu vẫn thiếu. Bài A (đề dẫn xuất `questions-ky-ao-vua-1-facts.yaml`, chủ dự án duyệt 22/10/2026, 1 lần hỏi): đồ thị 49% → 74%, đồ thị + câu trích 79% → 82%; 6 câu có đáp án: 0/18 → 6/6 ở hệ đồ thị. Đọc 26 Fact: 17 cụ thể và trung tính, 9 là quyết định hay nhận xét của nhân vật chính (4 ít giá trị), vài Fact gần trùng nhau hay trùng một bí mật đã lộ mà ngưỡng 0,7 không bắt. Đo lại 3 lần hỏi (`evals/results/2026-10-22-memory-ky-ao-vua-1-facts-s3/notes.md`): đồ thị 71%, đồ thị + câu trích 84%, cùng hướng và cỡ với một lần hỏi; còn câu đồ thị có chữ mà model đọc sai (`knows-05`). Chưa kiểm: một truyện, một lần phát lại (khoảng tin cậy rộng); đề đồ thị-có-Fact khai sau khi thấy đồ thị; chữ Fact trong sổ tay trên giao diện; luật mồ côi chưa đo lại.
- **Người quyết:** Chủ dự án (22/10/2026) chọn cho tạo Fact mới; thiết kế: Claude


## D-95 · Siết Fact mới: chỉ điều xảy ra, chống trùng theo thực thể, không ghi `KNOWS` hai lần (bổ sung D-93)
- **Bối cảnh:** đọc 26 Fact mới của D-93 (`evals/results/2026-10-22-new-facts-replay-1/notes.md`): 9 là quyết định hay nhận xét của nhân vật chính (4 ít giá trị), vài Fact gần trùng nhau hay gần trùng một bí mật đã lộ mà Jaccard 0,7 không bắt.
- **Quyết định:**
  - `extract-7`: Fact mới chỉ là điều ĐÃ XẢY RA hay ĐÚNG trong thế giới, trang nêu cụ thể (ai làm gì, vật ở đâu, ai hứa hay đòi gì, ai nói gì). KHÔNG ý định, quyết định, cảm nghĩ, nhận xét, suy đoán; không ghi lại điều danh mục đã có, kể cả bí mật đã lộ, dù diễn đạt khác. Có ví dụ đúng và sai, lấy từ truyện mẫu chứ không từ truyện đang đo.
  - Chống trùng thêm (`facts.related_overlap`): Fact mới trùng khi từ ngưỡng này của âm tiết của chính nó nằm trong một Fact cũ (kể cả bí mật đã lộ) hay một Fact mới khác của chương, VÀ cùng `ABOUT` một thực thể. Một chiều có chủ đích: Fact cụ thể hơn, chứa trọn Fact cũ cộng chi tiết, được giữ. Ngưỡng 0,65 chọn từ các cặp của D-93 (bản nói lại thật 0,71; Fact thêm điều khoản 0,62; các cặp khác ≤ 0,56): chỉ vài điểm dữ liệu, bag-of-words không tách hơn được.
  - Không ghi `KNOWS` tới nút mà chính nhân vật đó đã có `KNOWS` đang hiệu lực. Bản remap Fact trùng sang id cũ sinh `KNOWS` thứ hai cùng cặp, làm truy vấn một-cạnh (`derive`) hỏng.
- **Hệ quả** (mã cuối, hai lần phát lại: `evals/results/2026-10-22-new-facts-replay-4/notes.md`, replay-3 và replay-4; replay-2 là bản đầu, trước hai sửa cuối): 21 Fact mới mỗi lần, **0 quyết định hay ý định thuần** (D-93: 9/26), `derive` 17/39 cả hai (bằng D-93), vai trích 0,0286 và 0,0276 USD (D-93: 0,0287). Độ phủ nhóm 13 câu hỏi chi tiết dao động 2–6/13 giữa các lần (**6/13 và 2/13**), chưa phân biệt được với D-93 (một lần 6/13). Nguồn dao động đã thấy: thử riêng một cảnh ba lần, cùng đề cùng mã, Fact "mượn thẻ" khi có khi không vì model đổi chữ trong câu trích ("Ta" thành "Tôi") nên G3 bỏ. Không nới G3 và không nới đề. Việc mở: nhắc đề "chép nguyên văn, giữ nguyên đại từ". Mã còn thêm: id nội bộ `protagonist` được thay bằng "nhân vật chính" trong chữ Fact (`_human_protagonist`). Bài A chưa chạy lại.
- **Người quyết:** Claude; chủ dự án duyệt việc (22/10/2026)

## D-96 · Truy hồi đoạn kèm đoạn kế sau mỗi đoạn trúng; token cache của OpenRouter vào nhật ký chi phí (bổ sung D-81, D-85, D-87)
- **Bối cảnh:** chẩn đoán `memory-ky-ao-vua-1-facts-s3` (D-93): đoạn trúng từ khoá thường là lời hẹn, còn đoạn xảy ra việc nằm ngay sau (`item-06`: thẻ trả ở đoạn kế, không khớp chữ). Chi phí mỗi lời gọi lệch 10 lần giữa các lần chạy, ngờ cache prompt, nhưng nhật ký không có số token cache.
- **Quyết định:**
  - `PagePool.top(..., neighbors=N)`: mỗi đoạn trúng kéo theo N đoạn liền sau trong CÙNG chương; đoạn kế chỉ vào khi còn chỗ trong `max_chars`, đoạn trúng không bao giờ bị đẩy ra. `limits.context.page_quotes_neighbors` (tạm, D-47) = 1; D-85 vẫn mặc định tắt (`page_quotes_top_k: 0`), số này chỉ có tác dụng khi bật.
  - Bài A đọc cùng `page_quotes_neighbors` và `page_quotes_max_chars` cho hệ `graph_quotes`; `--page-neighbors` ghi đè; ghi `page_quotes` vào meta và dấu vân tay. `rag` không đổi (đối chứng). `top_k` giữ 2 trong `run.yaml` để so được với các lần trước. `bench_a retrieval` là phép kiểm tái lập chọn số (đếm câu có câu trích bằng chứng trong đoạn lấy về): trên đề `questions-ky-ao-vua-1-facts.yaml`, trần 2400 ký tự, top_k 2: 16/27 → 19/27 với một đoạn kế (TB 1139 → 2082 ký tự); top_k 3 chỉ thêm 1 câu (20/27), không đổi top_k.
  - Cache: `Usage.cached_tokens` đọc từ `usage.prompt_tokens_details.cached_tokens` (null = phản hồi không báo, 0 = đã báo không có cache); vào `CallCost`, cột `llm_costs.cached_tokens` (migration 0010) và `calls` của bộ đo. Báo cáo bài A tách lời gọi lạnh khỏi lời gọi có cache. Không đổi cách tính tiền: trần G8 vẫn theo `usage.cost` OpenRouter trả, giữ chỗ ngân sách vẫn theo giá lạnh (cận trên).
- **Tra tài liệu (22/10/2026, WebFetch; context7 chưa đăng nhập):** openrouter.ai/docs/use-cases/usage-accounting: `usage.prompt_tokens_details.cached_tokens` = số token đọc từ cache, `cache_write_tokens` chỉ có ở model cache tường minh; openrouter.ai/docs/features/prompt-caching: đọc cache tính 0,25 hoặc 0,5 lần giá vào tuỳ model, `cache_discount` là trường của thân phản hồi (không nằm trong `usage`, chưa ghi), cache tự động không nêu thời hạn, định tuyến theo nhà cung cấp hết hiệu lực sau 10 phút không hoạt động. Đo thực: giá mỗi lời gọi có cache khoảng 1/10 lời gọi lạnh với GPT-6 Luna (docs không nói riêng model này), và prompt chạy lại sau ~20 phút vẫn có cache: hai điều này lệch docs, chưa rõ vì sao.
- **Hệ quả:** hệ lai cũ và mới không cùng điều kiện ở phần đoạn trích; kết quả: `evals/results/2026-10-22-memory-ky-ao-vua-1-facts-nb1/notes.md`. Chỉ ghi `cached_tokens`, không ghi `cache_write_tokens`. USD mỗi lời gọi giữa các lần chạy không so được nếu khác tỉ lệ cache.
- **Người quyết:** Claude (nhánh retrieval-and-cache), điều phối giao việc, chờ duyệt · 22/10/2026

## D-97 · Lỗi TLS và lỗi socket tầng thấp là lỗi tạm, thử lại có giới hạn (bổ sung D-94)
- **Bối cảnh:** `evals/results/2026-10-22-run-long-tu-tien-1/` dừng ở chương 16 (`INTERNAL_ERROR`, 0,1565 USD): `ssl.SSLError` (`SSLV3_ALERT_BAD_RECORD_MAC`) trong lời gọi trích. Lỗi này đi qua anyio, httpx không bọc thành `httpx.HTTPError`, nên `except httpx.HTTPError` ở `llm/openrouter.py` không bắt; ra `INTERNAL_ERROR` và không được thử lại.
- **Quyết định:** ba chỗ bắt lỗi của `OpenRouterClient` (`chat`, `stream`, `generation_cost`) bắt `(httpx.HTTPError, OSError)` (`_NETWORK_ERRORS`). `ssl.SSLError`, `ConnectionResetError`, `BrokenPipeError`, `TimeoutError` đều là `OSError`. Ánh xạ sang `LLM_UNAVAILABLE`, nhóm `RETRY_TRANSIENT`: thử lại tối đa `retries.llm_transient` lần không chờ, hết lượt thì `RETRY_LIMIT_REACHED`. Người chơi thấy câu của `LLM_UNAVAILABLE` ("Model đang không phản hồi hoặc mạng tới OpenRouter bị gián đoạn", G12). `detail` chỉ có tên kiểu lỗi, không có thông điệp.
- **Lỗi giữa chừng khi stream:** theo luật hiện có cho lỗi httpx, cũng `LLM_UNAVAILABLE`; người gọi (`ChapterRun`) quyết có dùng phần đã nhận hay không. Không đổi luật đó.
- **Test:** `tests/unit/test_llm_openrouter.py` (transport giả ném lỗi, không đợi thật): bốn loại lỗi, một lỗi rồi thành công (2 yêu cầu), lỗi mãi (đúng 3 yêu cầu), lỗi trước và giữa stream, tra chi phí, và lỗi lập trình (`ValueError`) vẫn nổi lên.
- **Hệ quả:** `OSError` rộng hơn lỗi mạng; trong ba chỗ bắt chỉ có lời gọi httpx, nên không nuốt lỗi khác. Lỗi TLS lặp lại mãi tốn thêm `llm_transient` lời gọi hỏng (không tính tiền) trước khi dừng.
- **Người quyết:** Claude (writory-2a giao việc 22/10/2026), nhánh feature/long-pacing · 22/10/2026

## D-98 · Truyện đứng yên: mục tiêu chương và đề tạo lựa chọn đòi đổi tình thế khi nhân vật chính ở một nơi từ `standstill_chapters` chương
- **Bối cảnh:** `long-tu-tien-1`: chương 10–15 cùng một cảnh dò đường ở Cốc Đèn (đếm từ "dò" mỗi chương 11–21), ba lựa chọn cuối chương 10, 14, 15 đều "giữ yên, dò thêm" (`notes.md` của lần chạy).
- **Chẩn đoán, không gọi model:** *kế hoạch* (24 chương: 8 mốc, 2 bí mật, 4 mạch): chương 10 không có mốc, mạch hay bí mật nào mở; chương 13–14 không mục nào bắt đầu hay đến hạn; mốc ch5–6, 11–12, 15–16 và mạch "tìm lối xuống" (11–18) là cùng một cuộc vượt. *Bộ tạo lựa chọn*: đề chỉ đòi "mỗi lựa chọn một hướng khác nhau", không gì buộc một lựa chọn đổi tình thế. *Model viết*: mục tiêu chương đã đòi "kết chương ở một tình thế mới, không lặp lại" (`pacing.py`) mà vẫn lặp. Không tách được phần của từng bên bằng một lần chạy.
- **Tín hiệu đứng yên (đã thử trên dữ liệu có sẵn):** độ giống chữ giữa hai chương liền (Jaccard bigram, cosine TF-IDF) và số cạnh đổi mỗi chương KHÔNG tách được chương lặp khỏi chương thường (long-tu-tien-1 ch11–15: Jaccard 0,10–0,13, cosine 0,31–0,41; `ky-ao-vua-3` chạy tốt: 0,08–0,13 và 0,13–0,60; ch10–15 vẫn thêm 2–3 Fact mới mỗi chương). **Nơi ở của nhân vật chính tách được:** `LOCATED_AT` mở ở chương 6 và không đổi tới chương 15; các chương trước đổi nơi mỗi 2 chương.
- **Quyết định:** `pipeline/pacing.py` `standstill(state, chapter, threshold)`: cạnh `LOCATED_AT` mới nhất của nhân vật chính còn hiệu lực ở cuối chương trước; từ `limits.context.standstill_chapters` chương trở lên (số tạm, D-47; bằng 4) thì (1) `ChapterGoals.standstill` thêm dòng "Chương này PHẢI đổi tình thế… không lặp lại cảnh dò xét, chờ đợi hay thương lượng" vào đề dàn ý và đề viết (`outline-9`, `writer-9`), trừ chương cuối; (2) đề tạo lựa chọn (`choices-3`) thêm `STALLED_NOTE`, chữ cố định đòi ít nhất một lựa chọn vượt khỏi thế giằng co. Cờ chỉ đúng/sai, không mang tên nơi chốn (G1). Cùng cờ ở ba nơi tạo lựa chọn (`chapter.py`, `api/play.py`, `bench_run.py`).
- **Chưa làm:** mật độ bí mật/mạch/mốc theo số chương (đề xuất: `secrets` theo mức trong `story_lengths.yaml`, hiện cố định 1–3 cho mọi mức); luật "không quá N chương liền cùng một mốc". **Lỗi xưng hô** ("ông"/"anh" cho cùng một nhân vật, `long-tu-tien-1` ch7, 10–14): vấn đề đã biết, chưa sửa (đồ thị không có giới tính hay tuổi).
- **Hệ quả:** truyện hợp lệ ở một nơi nhiều chương (vây thành, giam cầm) cũng bị giục đổi tình thế; nơi ở là cạnh do bộ trích ghi, bộ trích quên mở hoặc đóng cạnh thì cờ sai (long-tu-tien-1 có hai cạnh cùng mở). Đo lần đầu (`evals/results/2026-10-22-run-long-tu-tien-2/notes.md`, 24/24 chương, Luna): cờ bật ở ba chương nhưng bộ trích đóng cạnh nơi ở ở ch7 và chỉ mở lại ở ch18, nên cờ mù đúng đoạn lặp ch8–17.
- **Người quyết:** Claude (writory-2a giao việc 22/10/2026), nhánh feature/long-pacing · 22/10/2026


## D-99 · Ba cách trình bày khối đồ thị của bài A: không biến thể nào đạt luật, giữ nền
- **Bối cảnh:** `knows-05` có dòng đúng trong ngữ cảnh đồ thị ("Đã biết: …; cách biết: suy ra") mà model đáp "Không" 3/3. Ba giả thuyết: H1 "suy ra" bị coi là chưa chắc, H2 dòng vị trí đồ vật nghe mâu thuẫn, H3 dòng chìm trong danh sách dài sắp theo thời gian (`evals/results/2026-10-22-memory-ky-ao-vua-1-facts-nb1/notes.md`).
- **Làm gì:** cờ `--graph-style` của `bench_a run`, mặc định `base`: `natural` (cách biết bằng câu thường), `relevance` (tối đa 4 dòng "Đã biết" khớp câu hỏi lên đầu nhóm, chỉ đổi thứ tự), `no_item_place` (bỏ dòng vị trí đồ vật đã có Fact). Luật quyết định khai và commit trước khi chạy (`docs/eval.md`, commit `3754252`): giữ khi đúng tổng ≥ 89/117 (nền cộng 5 điểm) và không nhóm nào tụt quá 10 điểm.
- **Kết quả** (`evals/results/2026-10-23-memory-ky-ao-vua-1-facts-natural/notes.md`, hệ `graph`, 39 câu × 3 lần, Luna low, Neo4j): nền 83/117; `natural` 85, `relevance` 86, `no_item_place` 86. Không nhóm nào tụt quá 10 điểm, nhưng cả ba trượt điều kiện tổng. Mỗi biến thể đổi 5–6 câu cả hai chiều, chênh ròng +2 đến +3 lượt, nằm trong nhiễu.
- **Quyết định:** BỎ cả ba; cách trình bày nền giữ nguyên, không đổi `graph/context.py` (không biến thể nào thắng nên không có đề xuất cho ngữ cảnh người viết). Cờ và ba kiểu giữ trong mã (mặc định `base`, có test) để lặp lại phép đo; sản phẩm không dùng.
- **Không kết luận được về H1–H3:** `knows-05` lật từ 0/3 sang 2/3, 3/3, 2/3 ở cả ba biến thể dù mỗi biến thể sửa một thứ khác nhau, nên không tách được giả thuyết nào; câu này nhạy với mọi đổi ngữ cảnh (hay nhiễu của model).
- **Sự cố:** lượt đầu bị nhiễu vì tôi khởi động hai chuỗi đo chồng nhau trên cùng truyện `bench-a-run` (0,0518 USD bỏ đi); số trong kết quả là của các lượt chạy lại sạch, chi tổng khoảng 0,0925 USD (trần được duyệt 0,11). Chi tiết ở notes.
- **Chưa kiểm:** nền không chạy lại cùng ngày; không thử tổ hợp; không đo `graph_quotes`; một truyện.
- **Người quyết:** Claude (writory-6f giao việc 22/10/2026), nhánh eval/graph-presentation-ab · 23/10/2026

## D-100 · Đổi model: bỏ GPT-6 Luna, mọi vai và mức model viết dùng DeepSeek V4 Flash (thay một phần D-33, D-35, D-43, D-47)
- **Bối cảnh:** chủ dự án bỏ Luna vì chi phí và chọn DeepSeek hoặc model Trung Quốc (22/10/2026). Mọi số đo trước (bài A, C, D, E, các lần chạy truyện) là của Luna.
- **Quyết định:**
  - `config/models.yaml`: `deepseek/deepseek-v4-flash` cho mọi `roles` và mức `standard`; dự phòng `qwen/qwen3.7-flash`, chưa thử. Giữ mức suy luận cũ (viết none, các vai khác low). Giá vào, ra niêm yết 0,091 và 0,182 USD/1M (openrouter.ai/api/v1/models, tra 22/10/2026 16:39); `prices` của các đề đo thêm model mới, giữ giá Luna cho lần đo cũ.
  - OpenRouter xếp model này cho 15 nhà cung cấp (`/models/<id>/endpoints`): giá vào 0,05 đến 0,70 và ra 0,14 đến 1,32, một số không niêm yết `structured_outputs`. `OpenRouterClient` đòi `provider.require_parameters` khi có schema. `provider_ignore` (config) loại DigitalOcean cho mọi lời gọi có vai: nó niêm yết `structured_outputs` nhưng trả JSON hỏng ở 5/6 lời gọi thăm dò (8/8 hợp lệ khi bỏ). Phân loại ô tự viết và người kể đi qua cùng đường (trước đó người kể tự dựng `extra`).
  - Qwen3.7 Flash chỉ có `response_format`, không có `structured_outputs` và `reasoning_effort` trong danh sách tham số.
- **Kết quả** (trần 0,15 USD, đã tiêu khoảng 0,146): truyện ngắn `evals/results/2026-10-22-run-deepseek-1/` **dở** (tiến trình biến mất sau chương 3, chương 4 dở): 2/4 lượt viết chương phải bấm thử lại (kiểm duyệt `json_invalid`, lựa chọn `value_error`), chi phí mỗi chương 1,5 đến 3,5 lần Luna, không chữ Hán, văn chương 3 có câu vô nghĩa. Bài E (`2026-10-22-narrator-deepseek-1/`): lộ 0, loại a 32/35. Bài A (`2026-10-22-memory-deepseek-1/`): trần cắt, trên 24–26 câu đã chạy ngang Luna.
- **Hệ quả:** model rẻ về giá niêm yết nhưng **không rẻ hơn Luna mỗi chương** vì token suy luận (vai trích và dàn ý nhiều nhất); `reasoning none` và `minimal` không giảm đều giữa các nhà cung cấp (thăm dò). Giá thật đổi theo nhà cung cấp, chưa chọn theo giá. Chưa kiểm: kết truyện, quality, `leak:name` ở model mới; bài D chưa đo; `qwen/qwen3.7-flash` chưa thử.
- **Người quyết:** Chủ dự án (22/10/2026) bỏ Luna, chọn DeepSeek hoặc model Trung Quốc; model cụ thể: Claude (nhánh model-deepseek), chờ điều phối duyệt · 22/10/2026

## D-101 · So 3 model viết trên cùng một thế giới, giám khảo là Claude (bài F)
- **Bối cảnh:** chủ dự án (22/10/2026) muốn biết model viết nào đáng tiền cho bản 1, khi D-100 đã đưa các vai trí nhớ sang DeepSeek. Bài D chấm từng cảnh rời, không thấy được liền mạch, nhịp, lựa chọn qua nhiều chương và không tính chi phí thật của đường chạy.
- **Quyết định:**
  - Ba model: `deepseek/deepseek-v4-flash`, `tencent/hy3`, `openai/gpt-6-luna`. `tencent/hy-mt2-30b-a3b` bị loại TRƯỚC khi chạy: là model dịch, ngữ cảnh 8.192 token, nhỏ hơn đề viết (vài nghìn token vào, cộng phần ra). Thay bằng Hy3 theo chủ dự án; giá và thông số tra từ `openrouter.ai/api/v1/models` lúc 2026-10-22T10:16Z, ghi ở `prices` của đề.
  - Biến duy nhất là model viết (mức model viết của đề) và model dàn ý. Cờ `--writer-model`, `--outline-model`, `--writer-reasoning`, `--outline-reasoning` của `bench_run` ghi đè rồi ghi vào `meta.json` (`overrides`); vai trí nhớ (trích, tóm tắt, lựa chọn, kiểm duyệt) giữ model của `main` cho cả ba lượt. Mức suy luận giữ như config; cờ `--*-reasoning` chỉ để dùng khi model từ chối mức đã cấu hình.
  - Cùng thế giới: khởi tạo MỘT lần bằng `--setup-only`, ba lượt `--setup-from` thư mục đó, 6 chương, cùng đề `story_run/model-bakeoff.yaml` (lệnh đòi cùng sha256 và seed, nên không dùng chung file với đề khác).
  - Chấm (`quality/bench_bakeoff.py`, dùng lại hạ tầng bài D): Sonnet 5.5 qua Anthropic API. Bước 1 mù: nhãn A/B/C xáo theo seed, khoá ở `key.json`; mỗi truyện chấm riêng một lượt, rồi so sánh trực tiếp cả ba hai lần với thứ tự trình bày đảo; câu trích kiểm bằng code (G3). Bước 2 đưa chi phí thật và hỏi khuyến nghị "đáng tiền", sau khi điểm bước 1 đã khoá bằng sha256 (`value_lock.json`): điểm đổi thì bước 2 từ chối.
  - Trần giao: OpenRouter ≤ 0,15 USD mỗi lượt viết và ≤ 0,50 tổng (nâng từ 0,10 và 0,30 vì DeepSeek tốn 1,5–3,5 lần Luna mỗi chương, `evals/results/2026-10-22-run-deepseek-1/notes.md`); Anthropic ≤ 1,25 USD (nâng từ 1,00 vì mỗi lượt giữ chỗ tối đa 0,2–0,3; `max_tokens` và `effort` của giám khảo giữ như bài D). Chạy thật sau khi D-100 gộp.
- **Hy3 bị loại giữa chừng (chủ dự án, 22/10/2026):** lượt `tencent/hy3` bị dừng ở chương 1 (0 chương ghi, 0,0097 USD; cảnh 1 bị chặn `guard:early_reveal`), không chấm. `bench_bakeoff` nhận hai hoặc ba lần chạy (nhãn A, B hay A, B, C ghi ở `pack_meta.json`; `judge.yaml` v2 không nêu số truyện); bài này chạy với DeepSeek và Luna.
- **Giới hạn đã biết:** một thế giới, 6 chương, một giám khảo, thang chưa hiệu chuẩn với người đọc; thiên lệch vị trí chỉ phát hiện (hai thứ tự), không loại; truyện dừng sớm ngắn hơn, giám khảo được dặn không thưởng độ dài.
- **Người quyết:** Chủ dự án (22/10/2026) yêu cầu so ba model và đổi Hy-MT2 sang Hy3; thiết kế: Claude

## D-102 · Quay lại GPT-6 Luna cho mọi vai và mức model viết (thay thế D-100)
- **Bối cảnh:** D-100 (22/10/2026) bỏ Luna vì chi phí và chuyển mọi vai sang DeepSeek V4 Flash. Sau đó bài F (D-101, `evals/results/2026-10-22-model-bakeoff-1/`) so DeepSeek với Luna trên cùng một thế giới, 6 chương: giám khảo Claude chọn Luna (hạng 1,0 so với 2,0; điểm 3,00 so với 2,71; hai thứ tự trình bày đồng ý), và phần model viết cộng dàn ý gần ngang giá (0,0045 và 0,0046 USD/chương), còn tổng mỗi chương Luna thấp hơn (0,0112 so với 0,0136 USD) vì DeepSeek dùng nhiều token ở vai trích; DeepSeek cần nhiều lần viết lại hơn (7 so với 4) và 24 lỗi định dạng lời thoại so với 0. Hy3 bị loại giữa chừng (D-101).
- **Quyết định:**
  - `config/models.yaml`: mọi `roles` và mức `standard` về `openai/gpt-6-luna`; `role_reasoning` giữ đúng mức đã đo với Luna (các vai trả JSON `low`, viết `none`); `eval_result` của mức `standard` trỏ lại `evals/results/2026-10-20-quality-r2/` (bài D). Giá DeepSeek và Hy3 nằm ở `prices` của các đề đo, không ở config.
  - Giữ hạ tầng của D-100: `OpenRouterClient` đòi `provider.require_parameters` khi có schema, `provider_ignore` trong config gửi `provider.ignore` qua `role_extra`/`provider_extra`. Với Luna `provider_ignore` rỗng, nên không gửi gì thêm.
  - D-33, D-35, D-43 và D-47 đúng trở lại (số đo của chúng là của Luna). Các đề đo (`evals/scenarios/`) vốn đã có giá của Luna; không đổi đề, nên sha256 của các đề đã chạy không đổi. Test về nhà cung cấp bị loại tự đặt một tên thay vì đọc config thật.
- **Hệ quả:** chi phí Luna mỗi chương cao hơn giá niêm yết của DeepSeek nhưng thấp hơn tổng thật của DeepSeek trong bài F. Các điểm yếu của Luna còn nguyên (lặp nhịp ở truyện dài, D-98). Bài F chỉ một thế giới, một seed, một giám khảo, điểm toàn 2 đến 3; chênh "lỗi" bị khuếch đại bởi lựa chọn hỏng chữ của vai dùng chung (`notes.md` của bài F).
- **Người quyết:** Chủ dự án (22/10/2026), căn cứ `evals/results/2026-10-22-model-bakeoff-1/`; cài đặt: Claude (nhánh model-luna), writory-6f giao việc · 22/10/2026

## D-103 · Deploy bản 1: máy nhà qua Cloudflare Tunnel, chồng prod riêng, chủ dự án tự bật tắt (thay một phần D-89)
- **Bối cảnh:** design §12 tuần 5 ("bạn bè mở link chơi được"). Chủ dự án chọn deploy trước, giữ độ dài Ngắn và Vừa (D-88, `config/story_lengths.yaml` vốn chỉ mở hai mức đó); máy chủ là chính máy nhà (Windows 11 + Docker Desktop), ra ngoài qua Cloudflare Tunnel; tự bật khi có người chơi, không tự chạy khi mở máy (23/10/2026).
- **Quyết định:**
  - `docker-compose.prod.yml`, project `writory-prod`: `cloudflared` → Caddy (giao diện tĩnh + `/api/*` bỏ tiền tố như proxy Vite, một origin cho cookie và CSRF của D-89; SSE `flush_interval -1`) → backend → Neo4j 5 Community, Postgres 16. Không service nào mở cổng ra máy; kho ở mạng `internal`; volume, mạng riêng nên chạy song song chồng dev. Mọi service `restart: unless-stopped`: tự hồi phục khi chết, còn sau `prod-down` (`compose stop`) thì không tự lên.
  - `APP_ENV=prod` (`Settings.app_env`): `config.prod_problems` chặn khởi động khi `AUTH_MODE` khác `invite` hoặc mật khẩu Neo4j, Postgres ngắn hay là mật khẩu mẫu (lỗi chỉ nêu tên biến); lúc khởi động chạy migration, `ensure_schema`, đọc thử hướng dẫn văn phong (`api/app.prepare_storage`); tắt trang OpenAPI. Chọn biến riêng thay vì suy từ `AUTH_MODE` để máy dev chạy `invite` với mật khẩu mẫu vẫn được.
  - Proxy tin cậy (`TRUSTED_PROXIES`, D-89 để ngỏ): backend chỉ đọc `X-Real-IP`/`X-Forwarded-For`/`X-Forwarded-Proto` từ IP cố định của proxy; Caddy chỉ đọc `CF-Connecting-IP` từ IP cố định của `cloudflared`; uvicorn `--no-proxy-headers` để một chỗ quyết. `Secure` giữ theo `Host`, thêm scheme tin được trên localhost. Bộ đếm lần nhập mã tính IPv6 theo dải /64 (`deps.rate_limit_key`; rà bảo mật 23/10/2026).
  - Thư mục mới `deploy/` (CLAUDE.md §3): Dockerfile, Caddyfile, override thử trên máy, và script PowerShell `prod-up`, `prod-down`, `prod-status`, `prod-backup`, `prod-restore` cho người không quen docker; `prod-down` và sao lưu hỏi lại khi còn khoá chạy đôi (`db.locks.held_job_locks`). Sao lưu dừng server để Postgres và Neo4j khớp nhau (D-6).
- **Hệ quả:** server chỉ chạy khi máy và Docker Desktop đang mở. Chưa thử qua Cloudflare thật (chưa có token); chưa kiểm Windows tắt đột ngột khi chồng prod đang chạy. Mạng `edge` cố định subnet, trùng mạng khác thì phải đổi ba biến. Bộ đếm lần nhập mã vẫn chung khi thử bằng trycloudflare. Cách chạy: docs/runbook.md, mục Deploy; bảo mật: docs/security.md.
- **Người quyết:** Chủ dự án (23/10/2026) chọn deploy trước, giữ độ dài Ngắn và Vừa, chạy máy nhà qua Cloudflare Tunnel và tự bật tắt; thiết kế: Claude (nhánh feature/deploy)

## D-104 · Thêm `docs/architecture.md`: bản đồ kiến trúc bằng sơ đồ Mermaid
- **Bối cảnh:** repo public; người ngoài và agent mới phải đọc nhiều file mới thấy được thành phần nào nối với thành phần nào. Bản đồ tài liệu (CLAUDE.md §2) chưa có chỗ cho cái nhìn tổng thể.
- **Quyết định:**
  - Thêm `docs/architecture.md` vào bản đồ tài liệu. File chứa ngữ cảnh hệ thống, thành phần runtime dev và prod, module backend, khởi tạo, đường đi một chương, đường ghi, ranh giới G1 theo vai, truy hồi, LLM client và chi phí, API và SSE, Postgres, bộ đo, hạn chế đã biết. Mỗi mục có một sơ đồ Mermaid, để GitHub vẽ thẳng từ markdown.
  - File không chép chi tiết của tài liệu khác: schema đồ thị trỏ `docs/graph-schema.md`, guardrail trỏ `docs/security.md`, lệnh trỏ `docs/runbook.md`, bộ đo trỏ `docs/eval.md`, lý do trỏ `D-n`. Không chép số của `config/`. Nguồn dẫn bằng file và tên hàm, không dẫn số dòng.
  - Mục "Hạn chế" chỉ liệt kê điều đọc được trong code. Sửa chúng cần quyết định riêng.
- **Hệ quả:** sửa luồng, module hay router thì phải sửa sơ đồ trong cùng commit (CLAUDE.md §2.5). Viết file này đã làm lộ vài chỗ `docs/graph-schema.md` lệch code; các chỗ đó được sửa cùng commit.
- **Người quyết:** Chủ dự án (26/10/2026) duyệt thêm file; nội dung: Claude

## D-105 · Áp lại chương `pending` lúc khởi động; thử lại mạng ở khởi tạo; khoá khởi tạo sau khi kiểm chủ
- **Bối cảnh:** hai mục trong `docs/architecture.md`, mục 13 (`TODO(D-6)` trong `lifespan`; thử lại mạng hai lớp ở `api/setup.py`), và nghi vấn `lock_setup` giữ khoá trước khi kiểm chủ phiên (D-89).
- **Áp lại lúc khởi động (D-6):** ở `APP_ENV=prod`, `prepare_storage` gọi `reconcile_at_startup` sau migration và `ensure_schema`. Hàm `db.reconcile_idle_stories` giữ khoá `story` (D-46) của từng truyện rồi mới gọi `reconcile_pending`; không giữ được thì bỏ qua (`busy`). Mọi đường ghi chương giữ khoá này, nên `start_story` nay cũng giữ khoá của truyện mới khi ghi chương 0. Khoá của tiến trình đã chết được Postgres nhả, nên chương kẹt thật luôn áp được. Lỗi khi áp lại chỉ vào log (đã `redact`), app vẫn lên: kho đã qua migration và ràng buộc, lỗi chỉ để vài truyện còn `CHAPTER_PENDING`; làm app chết thì chặn mọi người chơi và compose khởi động lại mãi. Dev không tự áp lại, như migration; lệnh tay đổi sang `reconcile_idle_stories` (`docs/runbook.md`).
- **Thử lại mạng ở khởi tạo:** mục 13 đoán sai một nửa. Lớp ngoài ở `_propose` và `finalize` không bao giờ thử lại: lớp mạng của `_ask` hết lượt thì ném `RETRY_LIMIT_REACHED`, không phải `LLM_UNAVAILABLE`, nên số lời gọi không nhân lên và `build_story` không chạy lại (test mới xanh ngay trên code cũ). Vẫn bỏ lớp ngoài: nó là code chết, và nếu có lỗi mạng lọt ra thì nó chạy lại cả các lời gọi đã xong. Thử lại nay chỉ ở từng lời gọi model.
- **Khoá khởi tạo (D-89):** là lỗi thật. `lock_setup` chạy trước endpoint nên giữ khoá `setup` trước khi kiểm chủ: người khác biết `session_id` thì nhận 409 `STORY_BUSY` khi phiên đang chạy (lộ việc phiên tồn tại) và làm chủ phiên bị báo bận. `session_id` ngẫu nhiên 64 bit và không lộ ra ngoài, nên khó khai thác (suy luận). Nay `lock_setup` kiểm chủ trước, như `deps.lock_story`: người khác luôn 404 `SETUP_NOT_FOUND`.
- **Hệ quả:** ở dev, chương kẹt vẫn phải áp lại bằng tay. Lệnh chạy cả truyện (`pipeline/bench_run.py`) ghi chương không qua khoá `story`; nó chạy trên kho dev, không chung kho với chồng prod (suy luận). Áp lại chạy đồng bộ trước yêu cầu đầu; Neo4j chậm thì app lên chậm theo.
- **Người quyết:** Chủ dự án (26/10/2026) đồng ý sửa; cách sửa: Claude (nhánh fix/startup-and-setup)

## D-106 · Sửa ba chỗ lệch: mức suy luận của vai phân loại, G3 ở bước ghi, test quét Cypher (G10)
- **Bối cảnh:** `docs/architecture.md` mục 13 (D-104) ghi ba chỗ code lệch luật: `classify_action` gửi `provider_extra` nên `role_reasoning.classify` không tới model; `apply_package` không đối chiếu `quote` với văn, nên G3 chỉ được bảo đảm ở bộ trích, tự hé lộ và truyện mẫu; G10 không có test quét Cypher ngoài `graph/`.
- **Quyết định:**
  - Phân loại ô tự viết dùng `role_extra(models, "classify")` như mọi vai. Đã rà các vai khác: người kể, kiểm duyệt, khởi tạo, dàn ý, trích, tóm tắt, lựa chọn đều qua `role_extra`. Model viết (`_write`) dựng `extra` riêng, không mang `provider_ignore`; không phải vai trong `roles` nên chưa sửa, ghi ở mục 13.
  - `commit_chapter` từ chương 1 gọi `graph.quote_problems` trước mọi lần ghi: câu trích của `REVEALED_TO_PLAYER`, của `KNOWS` từ nhân vật chính (bắt buộc có) và của `RESOLVED_IN` có `quote` phải nằm trọn trong văn một cảnh. Sai thì lỗi mới `CHAPTER_QUOTE_NOT_IN_TEXT` (G12), chi tiết vào log, không ghi gì. Chương 0 bỏ qua (câu trích là dòng của `story_brief`, D-74). Tự hé lộ (D-62) và Fact mới (D-93) lấy câu trích từ chữ cảnh nên qua được. Nhân vật chính lấy từ nút của gói (truyện mẫu khai ở chương 1), không có thì đọc đồ thị. Kho trong bộ nhớ của test chạy cùng phép kiểm.
  - `tests/unit/test_cypher_boundary.py` quét `src/writory/**/*.py` ngoài `graph/`. Mẫu chọn để ít báo oan; lý do ghi trong file. Hiện không có chỗ nào phải chuyển, nên danh sách ngoại lệ rỗng.
- **Hệ quả:** phân loại giờ chạy với mức suy luận của config (`low`), chưa đo lại bằng `writory.safety.bench_g5`; `evals/results/` chưa có kết quả G5 nào. Gọi thẳng `apply_package` (nạp truyện mẫu, bài A) vẫn không qua kiểm G3 ở bước ghi.
- **Người quyết:** Chủ dự án (26/10/2026) đồng ý sửa; cách sửa: Claude (nhánh fix/guards-and-tests)

## D-107 · Xuất kịch bản để làm video AI xếp vào bản 3
- **Bối cảnh:** chủ dự án muốn sau khi app hoàn thành có tính năng gửi kịch bản từ truyện sang app tạo video (Seedance hoặc tương tự), kèm sơ đồ tuyến nhân vật.
- **Quyết định:** ghi vào design §5 bản 3. Bản 1 chưa làm. Việc nền (ngoại hình nhân vật, cảnh sắc nơi chốn, thời điểm cảnh lúc khởi tạo) có thể làm sớm hơn nếu chủ dự án yêu cầu.
- **Hệ quả:** khi làm cần quyết bản xuất có dùng lớp `truth` hay chỉ `player_view` (G1).
- **Người quyết:** Chủ dự án (28/10/2026)

## D-108 · Giám khảo thứ hai cho bài F: Meta Muse Wonder, chấm cùng thang (bổ sung D-101)
- **Bối cảnh:** bài F chỉ có giám khảo Claude Sonnet 5.5. Chủ dự án muốn thêm một giám khảo khác hãng để bớt thiên lệch của một nhà cung cấp.
- **Quyết định:**
  - `judge.yaml` (version 3) khai `judge` (id `sonnet`) và `extra_judges` (id `muse`: `muse-wonder-1.0`, API tương thích OpenAI `https://api.meta.ai/v1`, `reasoning_effort: high`, giá niêm yết 4 / 0,20 / 20 USD mỗi 1M token vào / cache / ra). Thang, tiêu chí, ba bản hướng dẫn, bọc và escape truyện, kiểm câu trích có thật: không đổi, dùng chung với Sonnet. KHÔNG dùng bản `-contributor` (Meta huấn luyện bằng dữ liệu của bản đó).
  - Mỗi thư mục kết quả dành cho đúng một giám khảo (`pack --judge`); trần riêng `--budget-meta`; khoá chỉ đọc tên `META_API_KEY`, lỗi của Meta qua `scrub` (G7). `summary --with` thêm bảng điểm từng giám khảo, độ đồng thuận và điểm gộp: trung bình cộng điểm TB solo, trọng số bằng nhau, không chuẩn hoá thang.
  - Qua thăm dò (khoảng 0,03 USD): `reasoning_effort: none` bị từ chối (HTTP 400); `json_schema` strict dùng được còn `json_object` bỏ qua schema; token suy luận nằm trong `completion_tokens` và tính giá ra.
- **Kết quả** (`evals/results/2026-10-28-model-bakeoff-muse-1/notes.md`, cùng hai truyện DeepSeek và Luna của `2026-10-22-model-bakeoff-1`, 0,65 USD): cả hai giám khảo khuyến nghị Luna, nhưng điểm chênh nhỏ và đảo chiều (Sonnet xếp Luna trên, Muse xếp DeepSeek trên), và hạng so sánh của Muse đảo theo thứ tự trình bày (truyện trình bày sau luôn nhất) nên không dùng được cho cặp này. Trích không có thật: Muse 1/19, Sonnet 3/28.
- **Chưa kiểm:** một cặp truyện, một lần chạy mỗi giám khảo, chưa đo nhiễu; hai giám khảo chưa có đa số; chưa thử `effort` khác.
- **Người quyết:** Chủ dự án (28/10/2026) thêm key Meta, trần tổng 130 USD, dùng model mạnh nhất; cách làm: Claude


## D-109 · So hai bản đề viết trên cùng một thế giới: `--style-guide`, `--prompt-variant`, pack nhận cùng model khác đề
- **Bối cảnh:** sắp sửa đề viết (`evals/scenarios/quality/style_guide_vi.md`), đề dàn ý, mục tiêu chương và đề lựa chọn; cần so bản cũ và bản mới trên cùng thế giới, chấm bằng bài F (D-101). Bài F so MODEL: mỗi lượt khác model, đề lấy từ mã.
- **Quyết định:**
  - `bench_run --style-guide <file>` thay hướng dẫn văn phong (system prompt của vai viết; câu ngôi kể của config vẫn được nối vào cuối như cũ). `--prompt-variant <tên>` đọc thư mục `evals/scenarios/prompts/<tên>/`: `outline_system.md` (đề dàn ý), `choices_system.md` (đề lựa chọn), `goals.yaml` (ánh xạ khoá → câu, thay các câu cố định của mục tiêu chương: `push_forward`, `standstill`, `secret_note`, `revealed_note`, `thread_note`; `standstill` có chỗ điền `{place}` và `{chapters}`). Thiếu file hay khoá thì dùng đề của mã. File lạ, khoá lạ, file rỗng, thiếu chỗ điền: lỗi cấu hình trước lời gọi đầu.
  - Cách chọn: thư mục file, không phải tham số dài hay ghi đè mã; mỗi đề một file nên diff giữa hai biến thể đọc được, và hash từng file ghi vào `meta.json` (`prompt_variant.files`, `style_guide_sha256`, `style_guide_path`, `prompt_versions_overridden`). Phiên bản đề trong mã (`OUTLINE_PROMPT_VERSION`…) giữ nguyên trong `prompt_versions`; `prompt_versions_overridden` nói đề nào KHÁC mã.
  - Sản phẩm không đọc cờ này: `pipeline/prompt_variants.py` (module mới, chỉ bộ đo import; lý do ghi ở đây theo CLAUDE.md §3) tạo `PromptTexts` (chuỗi thuần) và `ChapterRun(prompts=...)` mặc định None; `api/` không biết biến thể (test quét mã). Ba nơi sản phẩm gọi model đọc `prompts` chỉ qua tham số tùy chọn.
  - G4: đề ghi đè là chữ nhà phát triển, chỉ vào vai system (`system_message` vẫn từ chối khối `player_data`) hoặc là câu cố định của mục tiêu chương; chữ người chơi (đề bài, hành động, tên nơi chốn của `standstill`) vẫn đi đúng đường bọc cũ. Test: tin nhắn user không đổi một chữ khi chỉ đổi system.
  - Bài F `pack`: danh tính một lượt là (model viết, model dàn ý, `style_guide_sha256`, hash các file biến thể), không còn chỉ model; hai lượt giống hệt vẫn bị từ chối. Cùng model thì `key.json` ghi tên có hậu tố `[style:<8 hex>; variant:<tên>]` (model khác nhau giữ tên model); `writer_model` ghi riêng. Nhãn mù A/B giữ nguyên; không đụng phần giám khảo.
- **Hệ quả:** meta cũ chưa có hai trường mới được coi là đề mặc định. Mục tiêu chương chỉ thay được năm câu liệt kê, không phải cấu trúc mục (mốc, bí mật, mạch). Biến thể đổi cả vai dàn ý lẫn vai lựa chọn thì hai vai cùng đổi một lúc: so được "bản đề cũ với mới", không tách tác dụng từng vai (chạy riêng từng file nếu cần). Hai lượt A/B chung một thế giới nhưng lựa chọn cuối chương do vai lựa chọn tạo theo văn nên cốt truyện vẫn rẽ nhánh (bài F, `notes.md`).
- **Người quyết:** Claude; chủ dự án chọn làm giọng văn và tuyến truyện 28/10/2026 · 28/10/2026

## D-110 · Đề "v3": tính cách NPC, mốc trống và câu mở vào ngữ cảnh sau ba cờ; đề v3 để A/B (bật mặc định ở D-111)
- **Bối cảnh:** chẩn đoán 22 chương GPT-6 Luna (Ngắn và Vừa; đọc tay, đo bằng script, Muse Wonder làm góc nhìn thứ hai: `evals/results/2026-10-28-prose-diagnosis/notes.md`). Nguyên nhân tìm được: model dàn ý và viết không nhận `personality` của nhân vật phụ (`CharacterInfo` chỉ có tên, sống/chết, nơi ở, đồ giữ), chương không có mốc chỉ được dặn "chuẩn bị dần" (ba chương trống mốc của `ky-ao-3` đều kết bằng chờ), `ends_at` là một vị trí chứ không phải biến cố, và model không thấy câu mở chương trước (hai chương mở trùng nguyên văn).
- **Quyết định:**
  - Ba cờ ở `limits.context` (bật từ D-111): `character_personality_max_chars` (0 = tắt; tính cách của người có mặt và nhân vật lân cận còn sống vào đề dàn ý và đề viết, cắt theo trần; không đưa `backstory` vì có thể chứa bí mật; nhân vật `user_authored` bọc `UserAuthored`, G4; chỉ hai vai thấy lớp truth, G1), `unplanned_chapter_goal` (chương không có mốc nào đang diễn ra thêm câu `milestone_gap`), `previous_openings` + `previous_opening_max_chars` (câu mở của N chương gần nhất, chữ đã hiện trên trang, vào đề viết ở cảnh 1 với nhãn "đừng lặp").
  - Mốc trống: chọn cách nhỏ nhất, chỉ đổi chữ mục tiêu chương, không đổi khởi tạo hay `story_plan` (bắt mọi chương có mốc phải đổi prompt khởi tạo, bước dễ hỏng nhất, D-54). `pacing.GOAL_DEFAULTS` thêm `milestone_next` (câu hiện hành) và `milestone_gap`, ghi đè được bằng `goals.yaml` (D-109).
  - Đề `v3`: đề dàn ý, đề lựa chọn, hai câu mục tiêu chương và hướng dẫn văn phong (rút gọn từ bản dự thảo, giữ mọi luật an toàn của v2). Lúc A/B nằm ở biến thể `prompts/v3/` và `style_guide_vi_v3.md`; từ D-111 là đề mặc định của mã. `meta.json` ghi `context_flags`.
- **Hệ quả:** kết quả A/B và việc bật mặc định: D-111. Danh tính lượt của `pack` tính theo style guide và file biến thể, không theo cờ ngữ cảnh. Câu của chương cuối chưa ghi đè được bằng `goals.yaml`. Bảng số đo cần so (cử chỉ lặp, kết cảnh đứng yên, lời thoại thủ tục, lựa chọn nói dối) ở mục 6 của ghi chú chẩn đoán.
- **Người quyết:** Claude; chủ dự án chọn làm giọng văn và tuyến truyện 28/10/2026 · 28/10/2026


## D-111 · Bật đề v3 làm mặc định của app, dù luật A/B ra "chưa phân biệt được" (thay phần "mặc định tắt" của D-110)
- **Bối cảnh:** A/B cũ/v3 trên ba thế giới, hai cặp mỗi thế giới, hai giám khảo (D-108), theo luật khai và commit trước khi chấm (`docs/eval.md`, "Luật quyết định cũ/v3"). Kết quả `evals/results/2026-10-29-ab-v3/notes.md`: chênh trung bình v3 − cũ của Sonnet chưa tới ngưỡng +0,50 và của Muse chưa tới +0,71, không tiêu chí nào tụt quá 1 điểm ở từ hai thế giới trở lên, nên luật ra **chưa phân biệt được**, không phải "v3 thắng". Số đo bằng code (chỉ báo cáo): chương kết đứng yên 12/30 → 4/30, chi phí mỗi chương tăng khoảng 2,5%. So trực tiếp của Sonnet chọn bản cũ ở 4/6 cặp, ngược với điểm solo.
- **Quyết định:** bật v3 làm mặc định. Căn cứ chủ dự án chọn: chiều chênh dương ở cả hai giám khảo, chương kết đứng yên giảm, chi phí gần như không đổi, không tiêu chí nào tụt. Đây là quyết định của chủ dự án với bằng chứng chưa đủ sức thống kê, không phải kết luận của bộ đo.
  - Chữ của v3 vào thẳng mã: `scene.OUTLINE_SYSTEM_PROMPT`, `choices.SYSTEM_PROMPT` (và `TONE_GUIDANCE`), `pacing.GOAL_DEFAULTS` (`push_forward`, `milestone_next`), `evals/scenarios/quality/style_guide_vi.md`. Bỏ `style_guide_vi_v3.md` và thư mục `prompts/v3/`. Phiên bản đề tăng: `outline-10`, `writer-10`, `choices-4`.
  - Ba cờ ngữ cảnh bật ở `config/limits.yaml` (số tạm, D-47). Giá trị mặc định trong pydantic (`config.py`) giữ tắt: một sự thật ở `limits.yaml`; config thử của test tắt ba cờ để test của vai khác không đổi. Bỏ `bench_run --prose-v3`; `--style-guide` và `--prompt-variant` giữ cho lần A/B sau.
- **Hệ quả:** bài D đọc `style_guide_vi.md`, nên hash dữ liệu bài D đổi và kết quả bài D cũ không so thẳng với đề mới. Đề cũ nằm ở mã tại commit `41ed852` (trước D-111): lần A/B sau dựng biến thể từ commit đó (`git show 41ed852:<file>`). Chưa đo trên người chơi thật; chi phí thật của đề mới chưa vào trần (số tạm, D-47).
- **Người quyết:** Chủ dự án, 29/10/2026; Claude thực hiện.

## D-112 · Truyện dài: nhân vật chính luôn có một nơi ở, tín hiệu "chương liền không đổi trạng thái", tóm tắt gọi đúng tên nhân vật chính
- **Bối cảnh:** `evals/results/2026-10-22-run-long-tu-tien-2/notes.md`: bộ trích đóng cạnh `LOCATED_AT` của nhân vật chính ở ch7 mà không mở cạnh mới, 11 chương không có nơi ở nên cờ `standstill` (D-98) mù đúng đoạn lặp ch8–17; tóm tắt chương gọi nhân vật chính là "Diệp", "Chi Ninh", "nhân vật chính" trong khi văn gọi "Chiêu Ninh". Phần mốc giữa truyện của `story_plan` chờ chẩn đoán riêng, không đổi ở đây.
- **Quyết định:**
  - Nơi ở (`extract.to_package`, như D-90 cho đồ vật, bằng code vì model hay ghi cạnh mới mà quên đóng cạnh cũ và ngược lại): nơi mới đóng nơi cũ; hai nơi mới trong một gói thì giữ nơi ghi sau cùng; đóng nơi cũ mà không mở nơi mới thì giữ nơi cũ (bỏ lệnh đóng); nói lại nơi đang ở thì bỏ cạnh mới, vì cạnh mới đặt lại `valid_from_chapter` và cờ đếm lại từ đầu. Mỗi lần bỏ ghi vào `rejected`. Chỉ nhân vật chính; nhân vật khác giữ luật cũ.
  - Tín hiệu mới `pacing.idle_chapters`: từ `limits.context.idle_chapters` (tạm, D-47; bằng 4; null = tắt) chương liền không có biến cố đổi nơi ở hay chỗ của ai/vật nào, đổi chủ đồ vật, cái chết thì mục tiêu chương thêm câu `idle` (khoá mới của `GOAL_DEFAULTS`, ghi đè được bằng `goals.yaml`, có chỗ điền `{chapters}`) và đề tạo lựa chọn nhận `STALLED_NOTE` như D-98. Không đặt cùng `standstill` (một lời giục là đủ), không ở chương cuối. Đọc trên đồ thị, không dựa vào một cạnh.
  - **Mạch gỡ và bí mật lộ KHÔNG tính là biến cố** (lệch đề giao việc, có căn cứ): chúng xảy ra đúng lịch của kế hoạch dù chương là thủ tục. Phát lại trên bốn lượt (`evals/results/2026-10-29-idle-replay/`): tính chúng thì dãy rỗng dài nhất của `long-tu-tien-2` ở ch8–17 chỉ là 2 và cờ không bao giờ bật; bỏ chúng thì cờ bật 7–18, `standstill` chỉ bật 4 chương. Mốc kế hoạch không đo được từ đồ thị nên không tính.
  - Tóm tắt (`summary-2`): đề nhận tên chuẩn của nhân vật chính từ đồ thị (cạnh `protagonist`) ở tin nhắn dữ liệu, bọc `UserAuthored` khi nút `user_authored` (G4, tên không vào system), và đòi tóm tắt ngôi thứ ba luôn gọi đúng tên đó, đủ họ tên. Bài A dùng tóm tắt không có tên (`bench_a`).
- **Hệ quả:** truyện hợp lệ ở một nơi hay ít biến cố nhưng có tiến triển thật (vây thành, đàm phán dài) cũng bị giục; chưa có truyện "tốt mà chậm" để đối chứng. Số liệu phát lại lấy từ lượt trước D-112. Chưa đo ảnh hưởng lên văn bằng model (không gọi model ở đợt này); cần lượt dài mới để so. Đề cũ của bộ đo tóm tắt đổi `summary-1` thành `summary-2`.
- **Người quyết:** Claude; chủ dự án chọn làm truyện dài 29/10/2026 · 29/10/2026

## D-113 · Hạn tổng mỗi lời gọi model: quá hạn thì LLM_TIMEOUT, lỗi tạm, tính tiền như lời gọi bị huỷ
- **Bối cảnh:** `evals/results/2026-10-29-run-long-tu-tien-3/calls.jsonl` (đọc tại worktree của session 1): 214 lời gọi xong với p50 9,8 s, p99 16,7 s, lâu nhất 111,5 s (dàn ý); MỘT lời gọi dàn ý ở ch18 treo 13121 giây rồi mới `LLM_UNAVAILABLE`, năm lần thử sau đều lỗi trong 0,05 giây (mạng đã mất). `DEFAULT_TIMEOUT = httpx.Timeout(120.0, connect=10.0)` là hạn từng lần đọc/ghi, không phải hạn tổng. Ở app thật người chơi sẽ ngồi chờ hàng giờ và khoá chống chạy đôi (D-46) giữ suốt thời gian đó.
- **Nguyên nhân khả dĩ (đọc code và docs, chưa tái hiện): hai cái, không phân biệt được bằng dữ liệu có sẵn.** (1) Máy chủ giữ kết nối bằng byte nhỏ giọt: mỗi lần đọc làm lại hạn 120 s. Docs OpenRouter chỉ nói có dòng chú thích giữ kết nối cho stream (`: OPENROUTER PROCESSING`), im lặng về lời gọi không stream; `chat` của ta đọc cả thân bằng `aread()`. (2) Máy ngủ hoặc mạng rớt làm kết nối chết không RST: hạn đọc lẽ ra bắt sau khi thức nếu đồng hồ đơn điệu chạy tiếp, nhưng chưa kiểm đồng hồ ấy có tính lúc ngủ trên Windows không; mạng đã mất lúc lời gọi kết thúc (năm lỗi tức thì) hợp với cách giải thích này.
- **Quyết định:**
  - `limits.llm_call.deadline_seconds` (300, tạm D-47; khoá chưa đặt là `CONFIG_LIMIT_NOT_SET`, không phải vô hạn; `llm.openrouter.call_deadline(config)`): hạn TỔNG của một lời gọi, gồm `chat`, `stream` (mỗi lần chờ một dòng dùng chung một thời điểm hết hạn, và không bao giờ huỷ mã của nơi dùng stream giữa hai `yield`) và `generation_cost`. Dựng bằng `asyncio.timeout_at`. 300 s bằng hơn 2,5 lần lời gọi lâu nhất đã đo.
  - Quá hạn: `WritoryError(LLM_TIMEOUT)` có câu G12 (`errors.MESSAGES`), HTTP 504; vào `RETRY_TRANSIENT` nên lớp thử lại (`retries.llm_transient`) xử như lỗi mạng, hết lượt thì `RETRY_LIMIT_REACHED`. `maybe_billed`: sau khi gửi thì có thể đã bị tính tiền như lời gọi bị huỷ (docs: lời gọi không stream vẫn tính đủ), nên `RecordingClient` ghi chi phí tối đa ước tính, tra lại theo id generation nếu có. `TimeoutError` cũng là lớp con của `OSError`: chỉ hạn của chính ta (`Timeout.expired()`) mới thành `LLM_TIMEOUT`.
  - Nối dây: `api/deps.get_llm_factory` (app), `bench_run`, `bench_a`, `bench_e`. Các bộ đo còn lại (`bench_c`, `bench_d`, `bench_g5`, `bench_g9`, bài F) chưa nối: `deadline_s=None` giữ hành vi cũ.
- **Hệ quả:** một lời gọi hợp lệ nhưng chậm quá 300 s (model suy luận nặng) bị cắt và tính tiền ước tính tối đa, rồi thử lại tối đa `retries.llm_transient` lần: chờ xấu nhất khoảng 15 phút thay vì vô hạn. Không sửa được nguyên nhân (2) nếu mạng mất khi máy ngủ: hạn tổng chỉ giúp sau khi máy thức. Số 300 chọn theo một lượt Luna (suy luận `low`); model hay mức suy luận khác cần đo lại. Test không chờ thời gian thật: đồng hồ vòng lặp nhảy, cầu chì thật nằm ở luồng riêng.
- **Người quyết:** Claude (writory-28 giao việc 29/10/2026), nhánh fix/llm-call-deadline · 29/10/2026

## D-114 · Bộ lựa chọn: tham chiếu ngoài sổ tay thì bỏ riêng tham chiếu đó, không bỏ cả bộ
- **Bối cảnh:** `evals/results/2026-10-29-run-long-ky-ao-hanh-trinh-1/` (PR #91): truyện dừng hẳn ở ch14 vì bước tạo lựa chọn bị từ chối 2 lượt × 2 lần thử. `truth_dump.json` (errors): lỗi cuối của lượt đầu "listeners có mục không phải nhân vật", của lượt sau "ref không có trong danh sách: ['mã người dẫn đầu chưa có trong sổ tay']". Model muốn nhắc "người dẫn đầu", một người không có mục trong sổ tay, nên viết một mô tả vào chỗ mã. `_resolve` ném `LLM_BAD_RESPONSE` cho cả bộ; lần thử lại gửi y nguyên đề nên dễ lặp lại. Ở app thật người chơi kẹt cuối chương.
- **Quyết định (`choices._resolve`):** ref ngoài sổ tay, hoặc người nghe không phải nhân vật, thì bỏ RIÊNG tham chiếu đó (G1: bỏ là đúng hướng, không đoán thêm; chữ lựa chọn giữ nguyên, dò lộ G2 và kiểm duyệt G9 vẫn chạy trên chữ đó). Lựa chọn mất thứ bắt buộc thì bỏ riêng lựa chọn đó: nội tâm không còn `about` (không có đích cho `FEELS`), lời nói dối không còn người nghe (không ai nghe thì không phải lời dối). Lời thoại nói thật hay im lặng mất hết người nghe vẫn giữ. Còn dưới `MIN_CHOICES` (2) lựa chọn hay dưới `MIN_KINDS` loại thì không cứu được: vẫn `LLM_BAD_RESPONSE` và thử lại như cũ (`retries.extract_schema_retry`), nhưng lần thử sau thêm một tin nhắn cố định `REF_NOTE` (đề `choices-5`), không nhắc lại chữ model đã trả (G4). Hết lượt vẫn lỗi thì giữ mã G12 hiện có. Log chỉ ghi số tham chiếu và lựa chọn đã bỏ, không ghi chữ.
- **Hệ quả:** người chơi có thể nhận 2 lựa chọn thay vì 3 (sau khi bỏ); ô tự viết hành động (G5) vẫn luôn có. Một lời thoại không còn người nghe mất `listeners` nên không ghi được gì vào đồ thị (nói thật không ghi gì sẵn). **Fixture dựng lại, không phải thân trả lời thật:** `calls.jsonl` không lưu thân trả lời, chỉ có chuỗi ref sai trong lỗi; `tests/fixtures/llm/choices_unknown_ref_run_long_ky_ao_hanh_trinh_1.json` ghi rõ điều đó. Hai test cũ đã đổi (ref lạ và người nghe không phải nhân vật không còn là lỗi chặn cả bộ).
- **Người quyết:** Claude (writory-28 giao việc 29/10/2026), nhánh fix/choices-unknown-ref · 29/10/2026
