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
- **Hệ quả:** ngoặc kép giữa đoạn (chữ khắc, tên sách, câu trích) là hợp lệ. Kiểm văn chỉ báo lỗi, không tự sửa.
- **Người quyết:** Claude (điều phối) · 19/10/2026

## D-19 · Ngưỡng kiểm văn nằm trong `config/quality.yaml`
- **Bối cảnh:** kiểm văn (design §6.5 mục 5) cần ngưỡng và danh sách sáo ngữ. Ba file config sẵn có không hợp chỗ.
- **Quyết định:**
  - Thêm `config/quality.yaml`. Ngưỡng chưa đo để `null`; code dùng tới thì báo `CONFIG_LIMIT_NOT_SET`.
  - Danh sách sáo ngữ là bản nháp chờ chủ dự án duyệt (`draft: true`).
  - "Tỉ lệ lặp" kiểm theo từng cụm: một cụm `ngram_words` từ xuất hiện quá `max_repeats` lần thì báo tại chỗ lặp. Không dùng một tỉ lệ cho cả cảnh, vì lỗi phải có vị trí.
  - Chữ Latin chỉ bị đếm khi không phải âm tiết tiếng Việt viết không dấu và không nằm trong danh sách từ mượn.
- **Hệ quả:** văn tiếng Việt viết thiếu dấu không bị bắt (cần bộ kiểm khác nếu muốn).
- **Người quyết:** Claude (Session 2) · 19/10/2026
