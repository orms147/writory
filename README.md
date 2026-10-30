# WriTory

> **In short:** WriTory is an interactive fiction engine for Vietnamese. You live a story as its protagonist and shape it with choices (action, dialogue, inner thought). The world is remembered in a two-layer knowledge graph: a `truth` layer that only the AI sees, and a `player_view` layer with only what the page has revealed to you. Secrets and plot twists are enforced by code, not by prompts. It is a learning project about graph-based memory (GraphRAG); players bring their own OpenRouter key. Status: work in progress; playable through the web UI on a developer machine or with invite codes; a production stack (Docker Compose behind Cloudflare Tunnel) exists but is not live yet.

Truyện tương tác tiếng Việt. Bạn sống đời nhân vật chính qua từng lựa chọn: hành động, lời thoại, nội tâm. Truyện dài tới khoảng 100 trang ([docs/design.md](docs/design.md) mục 3); bản 1 mở cho người chơi truyện ngắn và truyện vừa, các mức dài hơn mở sau khi đã đo (mức nào mở: `player_selectable` trong `config/story_lengths.yaml`).

## Vì sao làm

Truyện do AI viết thường **mất context** khi dài ra: quên nhân vật, quên ai còn sống, viết ngược sự kiện cũ, hoặc lộ plot twist quá sớm. Đây là dự án học GraphRAG và bộ nhớ dạng đồ thị qua một sản phẩm thật, và để biết đồ thị có thực sự giúp hay không. Nếu không giúp thì kết quả đo sẽ ghi đúng như vậy.

## Cách hoạt động

- **Đồ thị hai lớp** (Neo4j, tự viết lớp truy cập). Một đồ thị duy nhất, hai cách đọc. Lớp sự thật (`truth`: ai còn sống, ai giữ gì, ai biết gì từ chương nào, bí mật nào) chỉ AI viết truyện thấy. Lớp người chơi biết (`player_view`) chỉ gồm điều đã hé lộ trên trang, kèm câu trích có thật. Mọi cạnh có hiệu lực theo chương, nên hỏi được "ở chương 8 thì thế nào".
- **Đường đi một chương** (LangGraph): lấy phần đồ thị liên quan → dàn ý → viết cảnh → trích thay đổi thành JSON → kiểm → ghi vào đồ thị → tạo lựa chọn. Một cảnh chỉ hiện ra sau khi đã kiểm.
- **Người canh** chỉ kiểm bằng code ở bản 1 (phần đọc văn bằng LLM để bản sau): người chết xuất hiện, đồ vật ở hai nơi, nhân vật biết điều chưa biết, quan hệ đổi đột ngột, lộ bí mật sớm, mạch quá hạn.
- **Bộ dò lộ và guardrail.** Sổ tay, người kể và lựa chọn chỉ nhận dữ liệu từ `player_view`, lọc bằng code. Chữ người chơi luôn bị bọc như dữ liệu, không phải lệnh. Có trần chi phí, kiểm duyệt nội dung, và ghi chương theo kiểu tất cả hoặc không gì. An toàn nằm trong code, không nằm trong prompt. Danh sách đầy đủ: [docs/security.md](docs/security.md).
- **Người chơi dùng key OpenRouter của chính mình.** Key được mã hoá khi lưu, không vào log hay API. Model viết hiện chỉ có một mức; các vai giữ trí nhớ dùng model cố định. Cấu hình ở `config/models.yaml` (`writer_tiers`, `roles`).

Stack: FastAPI · LangGraph · Neo4j · PostgreSQL · React/TypeScript · OpenRouter.

## Chạy máy local

Cần Docker, Python và uv. Các bước, biến môi trường, chạy API và chạy cả một truyện từ dòng lệnh: [docs/runbook.md](docs/runbook.md).

## Đã đo được gì

Bộ đo khai câu hỏi và cách chấm **trước** khi chạy ([docs/eval.md](docs/eval.md)). Mỗi dòng dưới đây chỉ nói điều kết quả nói; số liệu và giới hạn nằm trong thư mục kết quả.

- **Bài A, đồ thị có giúp hơn các cách không dùng đồ thị không:** chưa, và phụ thuộc truyện. Trên truyện mẫu 5 chương (đồ thị dựng tay), đồ thị đứng một mình ngang RAG và nhét cả truyện; hệ lai (đồ thị cộng vài đoạn chữ trang tìm bằng BM25) cao nhất. Trên truyện 10 chương do pipeline viết, đồ thị đứng một mình thua RAG, tóm tắt cuộn và nhét cả truyện; khi bộ trích có đáp án trong đồ thị thì đồ thị trả lời gần như đúng hết, còn khi thiếu thì sai nhiều. Nút thắt là độ phủ của bộ trích (D-92), không phải phần đọc đồ thị. Một truyện, một lần chạy, khoảng tin cậy rộng. [năm hệ, truyện mẫu](evals/results/2026-10-21-memory-lan-1/notes.md), [hệ lai](evals/results/2026-10-21-memory-lai-1/notes.md), [truyện 10 chương](evals/results/2026-10-22-memory-ky-ao-vua-1/notes.md)
- **Bài B, người canh:** trên bộ ca lỗi cài sẵn dựng tay, mọi lỗi được bắt và không ca sạch nào bị báo nhầm. Bản 1 người canh không có phần dùng LLM. [kết quả](evals/results/2026-10-20-guard-b-r3/README.md)
- **Bài C, trích thay đổi từ văn bản:** trong ba model thử trên truyện mẫu 5 chương, GPT-6 Luna với suy luận mức thấp cho kết quả tốt nhất ở lớp người chơi biết và không hé lộ sai. Dữ liệu nhỏ và prompt đã chỉnh theo chính bộ này, nên có thể lạc quan. [kết quả](evals/results/2026-10-20-extract-v2-luna-reasoning/summary.md)
- **Bài D, chất lượng văn theo model:** GPT-6 Luna có điểm sát model đắt hơn nhiều dùng làm mốc, rẻ nhất nhóm, không lộ bí mật trên bộ đề; được chọn làm model viết; bài F sau đó so với DeepSeek V4 Flash trên cùng một thế giới và vẫn chọn Luna (D-102). [bài D](evals/results/2026-10-20-quality-r2/summary.md), [bài F](evals/results/2026-10-22-model-bakeoff-1/notes.md)
- **Bài E, hỏi người kể có lộ bí mật không:** bản đề 2 (nhiều câu khó hơn) trên truyện mẫu đã chạy với giám khảo Claude: không câu trả lời nào lộ bí mật, và giám khảo không còn đánh dấu câu úp mở sau khi người kể được sửa (D-78). Còn vài lượt nhỏ: sổ tay truyện mẫu ghi quá ít về thanh kiếm nên người kể nối thêm, và vài lượt chèn lệnh đáp bằng điều có trong sổ tay; đọc trong nhận xét. [kết quả có giám khảo](evals/results/2026-10-21-narrator-v2-d78-judge/notes.md), [bản đề đầu](evals/results/2026-10-20-narrator-luna-1/notes.md)
- **Chạy cả truyện từ dòng lệnh:** truyện ngắn đã chạy hết các chương của kế hoạch và có kết truyện; truyện vừa đã chạy đủ 10 chương. Nhận xét đọc tay ghi những lỗi còn lại, chủ yếu ở truyện dài: gỡ mạch còn sớm hay một phần, lặp nhịp ở bí mật đã lộ. [truyện ngắn](evals/results/2026-10-21-run-tu-tien-4/notes.md), [truyện vừa lần 1](evals/results/2026-10-21-run-ky-ao-vua-1/notes.md), [lần 2](evals/results/2026-10-21-run-ky-ao-vua-2/notes.md); lần đầu và các lỗi đã sửa: [tu-tien-1](evals/results/2026-10-20-run-tu-tien-1/notes.md)
- **Kiểm duyệt nội dung (G9):** lần đo đầu có câu bỏ sót và câu chặn nhầm; thang mức độ được chỉnh bằng chính các câu trong bộ đo nên cần bộ giữ riêng. Bộ giữ riêng v2 đã chạy: không chặn nhầm câu truyện u tối hợp lệ, còn bỏ sót vài câu ở ranh giới mức độ và câu mô tả trong ngoặc. Việc bắt chữ tấn công thật chưa đo được. [lần chỉnh thang](evals/results/2026-10-21-g9-luna-2/notes.md), [bộ giữ riêng v2](evals/results/2026-10-21-g9-holdout-v2-1/notes.md)

## Trạng thái

**Bản 1, đang làm** (kế hoạch: [docs/design.md](docs/design.md) mục 12). Đã chạy thử app đầu cuối qua API và giao diện dev với model thật (CLAUDE.md mục 9). Đăng nhập bằng mã mời cho bạn bè đã có (D-89, cách tạo mã: [docs/runbook.md](docs/runbook.md)); chồng prod chạy trên máy nhà qua Cloudflare Tunnel đã có, chưa mở cho người chơi ([docs/runbook.md](docs/runbook.md), mục Deploy; D-103). Hiện trạng chi tiết: [CLAUDE.md](CLAUDE.md) mục 9; các quyết định và người quyết: [docs/decisions.md](docs/decisions.md).

## Tài liệu

- [docs/design.md](docs/design.md): sản phẩm làm gì, vì sao, theo bản
- [docs/graph-schema.md](docs/graph-schema.md): nút, cạnh, quy tắc hai lớp
- [docs/security.md](docs/security.md): mối đe doạ và guardrail
- [docs/eval.md](docs/eval.md): bộ đo
- [docs/decisions.md](docs/decisions.md): các quyết định
- [docs/runbook.md](docs/runbook.md): chạy local
