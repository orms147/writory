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
