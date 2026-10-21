# WriTory

> **In short:** WriTory is an interactive fiction engine for Vietnamese. You live a story as its protagonist and shape it with choices (action, dialogue, inner thought). The world is remembered in a two-layer knowledge graph: a `truth` layer that only the AI sees, and a `player_view` layer with only what the page has revealed to you. Secrets and plot twists are enforced by code, not by prompts. It is a learning project about graph-based memory (GraphRAG); players bring their own OpenRouter key. Status: work in progress, not playable from a UI yet.

Truyện tương tác tiếng Việt. Bạn sống đời nhân vật chính qua từng lựa chọn: hành động, lời thoại, nội tâm. Truyện dài tới khoảng 100 trang.

## Vì sao làm

Truyện do AI viết thường **mất context** khi dài ra: quên nhân vật, quên ai còn sống, viết ngược sự kiện cũ, hoặc lộ plot twist quá sớm. Đây là dự án học GraphRAG và bộ nhớ dạng đồ thị qua một sản phẩm thật, và để biết đồ thị có thực sự giúp hay không. Nếu không giúp thì kết quả đo sẽ ghi đúng như vậy.

## Cách hoạt động

- **Đồ thị hai lớp** (Neo4j, tự viết lớp truy cập). Một đồ thị duy nhất, hai cách đọc. Lớp sự thật (`truth`: ai còn sống, ai giữ gì, ai biết gì từ chương nào, bí mật nào) chỉ AI viết truyện thấy. Lớp người chơi biết (`player_view`) chỉ gồm điều đã hé lộ trên trang, kèm câu trích có thật. Mọi cạnh có hiệu lực theo chương, nên hỏi được "ở chương 8 thì thế nào".
- **Đường đi một chương** (LangGraph): lấy phần đồ thị liên quan → dàn ý → viết cảnh → trích thay đổi thành JSON → kiểm → ghi vào đồ thị → tạo lựa chọn. Một cảnh chỉ hiện ra sau khi đã kiểm.
- **Người canh** kiểm bằng code: người chết xuất hiện, đồ vật ở hai nơi, nhân vật biết điều chưa biết, quan hệ đổi đột ngột, lộ bí mật sớm, mạch quá hạn.
- **Bộ dò lộ và guardrail.** Sổ tay, người kể và lựa chọn chỉ nhận dữ liệu từ `player_view`, lọc bằng code. Chữ người chơi luôn bị bọc như dữ liệu, không phải lệnh. Có trần chi phí, kiểm duyệt nội dung, và ghi chương theo kiểu tất cả hoặc không gì. An toàn nằm trong code, không nằm trong prompt. Danh sách đầy đủ: [docs/security.md](docs/security.md).
- **Người chơi dùng key OpenRouter của chính mình.** Key được mã hoá khi lưu, không vào log hay API. Model viết hiện chỉ có một mức; các vai giữ trí nhớ dùng model cố định. Cấu hình ở `config/`.

Stack: FastAPI · LangGraph · Neo4j · PostgreSQL · React/TypeScript · OpenRouter.

## Chạy máy local

Cần Docker, Python và uv. Các bước, biến môi trường, chạy API và chạy cả một truyện từ dòng lệnh: [docs/runbook.md](docs/runbook.md).

## Đã đo được gì

Bộ đo khai câu hỏi và cách chấm **trước** khi chạy ([docs/eval.md](docs/eval.md)). Mỗi dòng dưới đây chỉ nói điều kết quả nói; số liệu và giới hạn nằm trong thư mục kết quả.

- **Bài A, đồ thị có giúp hơn các cách không dùng đồ thị không:** chưa có bộ đo, nên **chưa có kết quả**. Hiện chưa thể nói đồ thị thắng.
- **Bài B, người canh:** trên bộ ca lỗi cài sẵn dựng tay, mọi lỗi được bắt và không ca sạch nào bị báo nhầm. Phần người canh dùng LLM chưa có. [kết quả](evals/results/2026-10-20-guard-b-r3/README.md)
- **Bài C, trích thay đổi từ văn bản:** trong ba model thử trên truyện mẫu 5 chương, GPT-6 Luna với suy luận mức thấp cho kết quả tốt nhất ở lớp người chơi biết và không hé lộ sai. Dữ liệu nhỏ và prompt đã chỉnh theo chính bộ này, nên có thể lạc quan. [kết quả](evals/results/2026-10-20-extract-v2-luna-reasoning/summary.md)
- **Bài D, chất lượng văn theo model:** GPT-6 Luna có điểm sát model đắt hơn nhiều dùng làm mốc, rẻ nhất nhóm, không lộ bí mật trên bộ đề; được chọn làm model viết. [kết quả](evals/results/2026-10-20-quality-r2/summary.md)
- **Bài E, hỏi người kể có lộ bí mật không:** ở bản đề đầu trên truyện mẫu, không câu trả lời nào lộ bí mật, kể cả với câu cố moi và chèn lệnh. Đề có một câu gán nhãn sai và chưa đủ câu khó; bản đề 2 và bản chạy trên truyện do pipeline viết đã soạn, chưa chạy. [tóm tắt](evals/results/2026-10-20-narrator-luna-1/summary.md), [nhận xét đọc tay](evals/results/2026-10-20-narrator-luna-1/notes.md)
- **Chạy cả truyện từ dòng lệnh:** một truyện ngắn đã chạy hết các chương của kế hoạch, nhưng nhận xét đọc tay ghi nhiều lỗi: cốt truyện lệch kế hoạch, đổi ngôi kể giữa chừng, bộ dò lộ buộc viết lại vì tên thường. Hai lần chạy sau dừng sớm vì lỗi khởi tạo và luật tên; đã sửa, chưa chạy lại. [lần 1](evals/results/2026-10-20-run-tu-tien-1/notes.md), [lần 2](evals/results/2026-10-20-run-tu-tien-2/notes.md), [lần 3](evals/results/2026-10-20-run-tu-tien-3/notes.md)
- **Kiểm duyệt nội dung (G9):** lần đo đầu có câu bỏ sót và câu chặn nhầm; sau khi chỉnh thang mức độ thì đạt hết, nhưng thang được chỉnh bằng chính các câu trong bộ đo, nên kết quả lạc quan và cần bộ câu giữ riêng. [nhận xét](evals/results/2026-10-21-g9-luna-2/notes.md)

## Trạng thái

**Bản 1, đang làm** (kế hoạch: [docs/design.md](docs/design.md) mục 12). Chưa chơi được từ giao diện: chưa có đăng nhập (API truyện và key người chơi chỉ bật được ở máy dev), giao diện web đang dựng, chưa có deploy. Hiện trạng chi tiết: [CLAUDE.md](CLAUDE.md) mục 9; các quyết định và người quyết: [docs/decisions.md](docs/decisions.md).

## Tài liệu

- [docs/design.md](docs/design.md): sản phẩm làm gì, vì sao, theo bản
- [docs/graph-schema.md](docs/graph-schema.md): nút, cạnh, quy tắc hai lớp
- [docs/security.md](docs/security.md): mối đe doạ và guardrail
- [docs/eval.md](docs/eval.md): bộ đo
- [docs/decisions.md](docs/decisions.md): các quyết định
- [docs/runbook.md](docs/runbook.md): chạy local
