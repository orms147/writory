# CLAUDE.md — WriTory

Truyện tương tác tiếng Việt có trí nhớ thế giới dạng đồ thị. Thiết kế: `docs/design.md`. File này chỉ chứa **quy tắc làm việc** và **sự thật hiện hành**, không chứa lịch sử. Tài liệu viết tiếng Việt; tên trong code viết tiếng Anh theo bảng thuật ngữ (§8).

## 1. Cách làm việc của agent
- **Đọc file thật trước khi khẳng định** điều gì về code, trích `file:dòng`. Không dựa vào trí nhớ.
- Trong câu trả lời, tách rõ điều **đọc được** (có nguồn) với điều **suy luận**. Không chắc thì ghi "chưa kiểm".
- **Không bịa** số liệu, tên hàm, API, giá model hay kết quả test. Kết quả test chỉ báo sau khi đã chạy, kèm lệnh đã chạy.
- Thư viện đổi nhanh (LangGraph, neo4j driver, OpenRouter): tra tài liệu hiện hành qua context7 trước khi viết code gọi API của chúng.
- **Tài liệu mâu thuẫn với code hoặc với nhau → chỉ ra và hỏi**, không âm thầm chọn một bên.
- **Không tự mở rộng phạm vi.** Chỉ làm tính năng của bản hiện tại (design §5). Thứ ngoài danh sách thì hỏi trước.
- **Ghi đúng người quyết định** (Chủ dự án / Claude) trong `docs/decisions.md`.
- Không gọi model thật ngoài trần trong `config/limits.yaml`. Không in, log hay commit key.

## 2. Tài liệu: quy tắc cứng
**Bản đồ tài liệu.** Chỉ có các file sau; muốn thêm file tài liệu thì phải hỏi.

| File | Chứa | Không chứa |
|---|---|---|
| `CLAUDE.md` | quy tắc + sự thật hiện hành, < 200 dòng | lịch sử, nhật ký |
| `docs/design.md` | sản phẩm: làm gì, vì sao, theo bản | chi tiết cài đặt đổi theo tuần |
| `docs/decisions.md` | quyết định, mỗi mục ≤ 15 dòng | thảo luận dài |
| `docs/graph-schema.md` | nút, cạnh, ràng buộc, quy tắc hai lớp, Cypher mẫu | |
| `docs/security.md` | mối đe doạ, guardrail, test tương ứng | |
| `docs/eval.md` | bộ đo: bài, dữ liệu, cách chấm, lệnh chạy | con số kết quả |
| `docs/runbook.md` | chạy local, deploy, biến môi trường | |
| `README.md` | cho người ngoài: là gì, chạy thế nào, kết quả chính | |

1. **Một sự thật, một chỗ.** Con số (trần chi phí, độ dài, tên model, ngưỡng) nằm trong `config/` hoặc code. Tài liệu trỏ tới đó, không chép số.
2. **Không ghi số đếm test, số dòng hay % coverage** vào tài liệu. Ghi lệnh để chạy ra số đó.
3. **Kết quả đo** nằm trong `evals/results/<ngày>-<tên>/`, kèm commit SHA, hash của config và tên model. Tài liệu chỉ link tới đó.
4. **Quyết định bị thay:** sửa tài liệu thành trạng thái mới, thêm mục mới trong `decisions.md` ghi "thay thế D-n". Không để lại câu cũ kèm chữ "SAI, đã sửa".
5. **Sửa tài liệu trong cùng commit với code** làm nó thay đổi. Commit đổi hành vi mà không sửa tài liệu liên quan là chưa xong.
6. **Không có bản sao** của tài liệu. Không có nhật ký phiên, worklog hay journal trong repo.
7. **Một hệ tên duy nhất** theo §8. Không đặt mã màn hình hay mã tính năng song song.

## 3. Cấu trúc thư mục
```
CLAUDE.md  README.md  docker-compose.yml  .env.example
config/            số và lựa chọn runtime: models.yaml, limits.yaml, story_lengths.yaml, quality.yaml
docs/              tài liệu ở §2
backend/
  src/writory/
    api/           FastAPI routers, SSE; schema phản hồi cho người chơi (không lộ truth)
    graph/         lớp truy cập Neo4j DUY NHẤT: Cypher, ràng buộc, hàm player_view
    pipeline/      LangGraph: dàn ý → viết → trích → canh → ghi → lựa chọn (một module)
    guard/         người canh: kiểm bằng code + phần LLM
    quality/       kiểm văn bằng code: độ dài, lặp, sáo ngữ, lẫn chữ khác hệ
    llm/           client OpenRouter, ghi chi phí, model giả cho test
    safety/        phân loại đầu vào, bọc chữ người chơi, dò lộ bí mật, kiểm duyệt
    db/            Postgres: tài khoản, truyện, chương, key (mã hoá), nhật ký
  tests/
    unit/          test nhanh, không mạng
    graph/         cần Neo4j Docker (marker `graph`)
    fixtures/      câu trả lời LLM ghi sẵn
frontend/          (tạo ở tuần 4) React + TS + Tailwind
data/sample-story/ truyện mẫu 5 chương viết tay + đồ thị dựng tay (tuần 1)
evals/
  scenarios/       câu hỏi + đáp án khai TRƯỚC khi chạy
  redteam/         câu tấn công, kèm kết quả mong đợi
  results/         kết quả đo, mỗi lần chạy một thư mục
```
Đặt code mới vào đúng module trên. Một module mới cần lý do ghi vào `decisions.md`.

## 4. Quy trình mỗi việc
1. Viết 3–5 dòng: việc gì, thuộc tính năng nào trong design §5, xong khi nào (phải kiểm chứng được).
2. **Test đỏ trước** cho logic: đồ thị, lọc `player_view`, người canh, kiểm văn, chi phí, trích JSON, guardrail.
3. Viết code tối thiểu cho test xanh. Giao diện chỉ cần test nhẹ.
4. Chạy test nhanh (§6), cập nhật tài liệu liên quan, rồi commit.
5. Mỗi tính năng một nhánh `feature/<tên>`; `main` luôn chạy được; gộp qua PR.
6. **Việc nhỏ commit thẳng lên `main`**, không cần nhánh: đổi tên, sửa chữ hoặc liên kết trong tài liệu, cập nhật §9. Vẫn phải chạy test nhanh trước khi push. Có đổi hành vi code thì không còn là việc nhỏ.

**Thứ tự bản 1** theo design §12. Tuần 1 dựng đồ thị **bằng tay** trên truyện mẫu, trước mọi lời gọi LLM.

## 5. Guardrail: bản rút gọn
Bản đầy đủ, kèm test cho từng mục: `docs/security.md`. **An toàn nằm trong code, không nằm trong prompt.**

- **G1** Sổ tay, người kể, lựa chọn chỉ nhận dữ liệu từ `player_view` và chữ đã hiện trên trang, lọc bằng code; model ở các đường đó không bao giờ thấy `truth`.
- **G2** Dò lộ bí mật trên mọi chữ trả về người chơi trước khi hiện.
- **G3** Đánh dấu "đã hé lộ" phải kèm câu trích có thật trong cảnh.
- **G4** Chữ người chơi là **dữ liệu, không phải lệnh**: không vào vai system, luôn được bọc, kể cả khi đọc lại từ đồ thị (`user_authored`).
- **G5** Đọc ý định người dùng bằng phân loại LLM có enum. **Không dùng regex** cho ý định; câu phủ định và câu dài phải ra đúng.
- **G6** Hành động vượt luật: truyện viết thất bại hoặc cái giá, không chiều theo.
- **G7** Key người chơi mã hoá khi lưu; không vào log, lỗi hay API.
- **G8** Trần chi phí và giới hạn tần suất trong `config/limits.yaml`; lượt viết lại có giới hạn cứng.
- **G9** Chặn cứng nội dung tình dục liên quan trẻ vị thành niên; mức u tối có trần.
- **G10** Mọi Cypher đi qua lớp `graph/`, bắt buộc có `story_id`.
- **G11** Trích JSON qua pydantic; ghi chương theo kiểu tất cả hoặc không gì (D-6). **Không đổi trạng thái phiên trước khi thao tác thành công.**
- **G12** Lỗi trả người chơi có mã riêng và câu tiếng Việt nói rõ chuyện gì xảy ra và làm gì tiếp. Không trả lỗi chung chung; chi tiết chỉ vào log.

Mỗi lỗi tìm được thêm thành **test hồi quy** trước khi sửa. Bài học được giữ bằng test, không bằng chữ trong file này.

## 6. Test
- **Test nhanh** (mỗi commit): `cd backend && uv run pytest -m "not graph"`. Không mạng, không model thật; LLM thay bằng model giả (`llm/fake.py`) trả câu ghi sẵn trong `tests/fixtures/`. Test G1 kiểm **context mà model nhận được** (`FakeLLM.calls`), để lọc sai là test đỏ ngay; chế độ echo dùng cho đường trả chữ. Mục tiêu dưới 2 phút.
- **Test tích hợp (Neo4j + Postgres):** `docker compose up -d` rồi `uv run pytest -m graph`, trên dữ liệu truyện mẫu. Marker `graph` dùng cho mọi test cần Docker.
- **Bộ đo** (`docs/eval.md`): lệnh riêng, có gọi model, có trần chi phí, không chạy trong CI mặc định.
- **Không viết test phụ thuộc thời gian chạy hoặc tốc độ máy** (sleep, timeout sát). Dùng đồng hồ giả.
- Lint: `uv run ruff check .`

## 7. Lệnh thường dùng
```bash
docker compose up -d                 # Neo4j :7474/:7687, Postgres :5432
cd backend && uv sync                # cài phụ thuộc
uv run pytest -m "not graph"         # test nhanh
uv add <gói>                         # thêm phụ thuộc (không sửa tay pyproject)
```

## 8. Thuật ngữ (dùng đúng tên này trong code và tài liệu)
| Tiếng Việt | Trong code | Nghĩa |
|---|---|---|
| Lớp sự thật | `truth` | toàn bộ sự thật thế giới, chỉ AI thấy |
| Lớp người chơi biết | `player_view` | điều đã hé lộ trên trang |
| Bản kế hoạch truyện | `story_plan` | hồi, bí mật, khoảng chương lộ; ẩn với người chơi |
| Cảnh | `Scene` | đơn vị viết–canh–hiện; 2–3 cảnh một chương |
| Dàn ý cảnh | `outline` | nhịp của cảnh, viết trước văn |
| Người canh | `guard` | kiểm mâu thuẫn và lộ sớm sau mỗi cảnh |
| Kiểm văn | `quality` | kiểm chất lượng văn bằng code |
| Mức model viết | `writer_tier` | người chơi chọn; chỉ đổi model viết |
| Mạch / cài cắm | `Thread` | chi tiết đã gieo, chờ gỡ |
| Lời nói dối | `Lie` | |
| Sự thật / mệnh đề | `Fact` | |
| Sổ tay | `notebook` | giao diện xem `player_view` |
| Hỏi người kể | `ask_narrator` | |
| Gói thay đổi | `commit_id` | định danh một lần ghi chương (D-6) |

## 9. Sự thật hiện hành
*Chỉ ghi trạng thái hiện tại, kèm link tới quyết định. Cập nhật khi có thay đổi.*

- Bản đang làm: **Bản 1, tuần 2**. Mốc "chạy liền 10 chương từ dòng lệnh" (design §12) chưa đạt: đã có lệnh `pipeline/bench_run.py` (D-42), mới chạy với model giả; trần còn là số tạm (D-47).
- Đã có trên `main`: lớp nền (`config.py`, `errors.py`, `llm/`), `safety/` (bọc chữ G4, mã hoá key G7, lọc log, phân loại hành động G5, dò lộ bí mật G2), lõi đồ thị (`graph/`: `player_view` một định nghĩa thuần, ngữ cảnh model viết `context.py`; truyện mẫu `data/sample-story/`), người canh bằng code (`guard/`), kiểm văn (`quality/`, chuẩn hoá dấu gạch D-31), ghi chương phía Postgres (`db/`), khung FastAPI (`api/`), bài đo B, C và D (`evals/results/`). Pipeline: khởi tạo truyện và chương 0 `pipeline/setup.py` (D-38, D-39), bản kế hoạch `story_plan.py`, bộ trích `extract.py` (D-34), đường đi một chương `chapter.py` (dàn ý → viết → soát → ghi → lựa chọn; D-36, D-37), hỏi người kể `narrator.py` (D-40). API chỉ bật bằng `ENABLE_DEV_ROUTES` (D-41): sổ tay, người kể; key người chơi `/player/key` và khởi tạo `/setup` (D-45); viết chương qua SSE, lựa chọn, hành động tự viết, đọc lại truyện (`api/play.py`, D-46). Postgres lưu kế hoạch ẩn, key đã mã hoá, phiên khởi tạo, nhật ký chi phí theo vai (migration 0003, D-44).
- CI: `.github/workflows/ci.yml` (job `fast` và `graph`, chạy trên mỗi PR và mỗi lần push lên `main`).
- Stack: FastAPI + LangGraph + Neo4j 5 Community + PostgreSQL + React/TS/Tailwind + OpenRouter (design §11).
- Quyết định đang hiệu lực: D-1 đến D-48 (`docs/decisions.md`).
- Model viết: GPT-6 Luna, một mức, suy luận none (D-33, D-43). Vai trích: GPT-6 Luna, suy luận thấp (D-35). Các vai khác: GPT-6 Luna tạm, suy luận thấp (D-47, `config/models.yaml`).
- Trần chi phí, ngưỡng kiểm văn và người canh, giới hạn người chơi: số tạm (D-47), chỉnh lại sau lần chạy thật đầu.
- Chưa có: đăng nhập (G10; mọi người là người chơi dev `dev`, D-44); ghi `Lie`/`FEELS` vào đồ thị khi chọn (D-46); frontend (tuần 4).
- Plugin của project: `.claude/settings.json` (context7, pyright-lsp, security-guidance, superpowers).
