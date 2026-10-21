# Runbook

## Yêu cầu
- Docker (có Compose)
- Python ≥ 3.12 và [uv](https://docs.astral.sh/uv/)
- Node 20.19+ và npm (cho frontend, mục Frontend)

## Chạy máy local
```bash
cp .env.example .env          # điền mật khẩu local và key OpenRouter của bạn
docker compose up -d          # Neo4j (http://localhost:7474) + Postgres
cd backend
uv sync
uv run pytest -m "not graph"  # test nhanh: không mạng, không gọi model thật
uv run pytest -m graph        # test cần Neo4j + Postgres ở trên; Postgres dùng database riêng <tên>_test (tự tạo, hoặc POSTGRES_TEST_DSN), không đụng dữ liệu app (D-75); Neo4j: mỗi test một story_id riêng
```

Chạy cả một truyện từ dòng lệnh (`writory.pipeline.bench_run`; lệnh, đề và kết quả: `docs/eval.md`, mục "Chạy cả truyện"). Lệnh đọc `NEO4J_*`, `POSTGRES_DSN` và, khi chạy thật, `OPENROUTER_API_KEY` từ biến môi trường hoặc `.env`; tự chạy migration và tạo ràng buộc Neo4j. Mỗi lần chạy dùng một story_id mới `run-<ngày>-<nhãn>-<mã>`, ghi trong `meta.json`. Truyện của lần chạy thật được giữ lại trong Neo4j + Postgres; xem bằng sổ tay (`ENABLE_DEV_ROUTES`, bên dưới) hoặc xoá bằng `delete_story_record` và `graph.delete_story`.

Chạy API ở máy (đọc biến môi trường từ `.env` ở gốc repo):
```bash
cd backend
uv run uvicorn writory.api:create_app --factory --reload
curl http://127.0.0.1:8000/health   # {"neo4j": "ok"|"down", "postgres": "ok"|"down"}; 503 nếu có phần down
```
App tạo bằng factory (`--factory`), nên import `writory.api` không cần biến môi trường.

API truyện (`/stories/...`), khởi tạo (`/setup/...`), key và chi phí người chơi (`/player/...`) và cấu hình công khai (`/config/public`) chưa có đăng nhập, nên mọi người đều là người chơi dev `dev` và chưa kiểm được truyện thuộc ai (G10). Các router này chỉ được gắn khi đặt `ENABLE_DEV_ROUTES=true` (D-41). Chỉ bật trên máy dev, không bật trên máy chủ thật. Chạy migration trước (mục Migration Postgres).
```bash
ENABLE_DEV_ROUTES=true uv run uvicorn writory.api:create_app --factory --reload
curl -X PUT http://127.0.0.1:8000/player/key -H 'content-type: application/json' -d '{"api_key": "sk-or-v1-..."}'
curl http://127.0.0.1:8000/stories/<story_id>/notebook
```
Cho giao diện (D-66): tủ truyện, các con số lấy từ `config/` (giới hạn ký tự, số câu hỏi người kể, trần chi phí, độ dài, mức u tối), chi phí đã dùng (tháng theo UTC), số câu hỏi người kể còn lại:
```bash
curl http://127.0.0.1:8000/stories              # {"stories": [...]}, mới nhất trước
curl http://127.0.0.1:8000/config/public
curl http://127.0.0.1:8000/player/costs         # {"total_usd", "this_month_usd", "stories"}
curl http://127.0.0.1:8000/stories/<story_id>/narrator   # {"remaining"}
curl -X POST http://127.0.0.1:8000/stories/<story_id>/narrator -H 'content-type: application/json' -d '{"question": "Lan là ai?"}'   # {"answer", "remaining", "source_chapters"}
```
Tạo truyện (design §4.1, D-45). POST một bước trả 3 lựa chọn đã có, hoặc gọi model để tạo nếu chưa có; PUT chọn theo số thứ tự 0–2. `darkness_level` là một khoá của `config/moderation.yaml` `darkness_levels`, bỏ trống thì dùng mức mặc định (D-67):
```bash
curl -X POST http://127.0.0.1:8000/setup -H 'content-type: application/json' -d '{"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "darkness_level": "moderate"}'
curl -X POST http://127.0.0.1:8000/setup/<session_id>/settings
curl -X PUT  http://127.0.0.1:8000/setup/<session_id>/settings -H 'content-type: application/json' -d '{"index": 0}'
# tương tự với plots, characters (PUT characters nhận thêm name, personality, backstory), rồi:
curl -X POST http://127.0.0.1:8000/setup/<session_id>/finalize   # trả story_id
```
Viết chương (SSE, D-46) rồi chọn hành động cho chương sau:
```bash
curl -N -X POST http://127.0.0.1:8000/stories/<story_id>/chapters/next   # event: stage | scene_ready | … | choices_ready
curl -X POST http://127.0.0.1:8000/stories/<story_id>/choice -H 'content-type: application/json' -d '{"choice_id": "choice-…"}'
curl -X POST http://127.0.0.1:8000/stories/<story_id>/action -H 'content-type: application/json' -d '{"text": "Tôi xuống bến hỏi chuyện."}'
curl http://127.0.0.1:8000/stories/<story_id>   # trạng thái để mở lại truyện
```
Một truyện chỉ viết một chương một lúc, một phiên chỉ chốt một lần một lúc: lần gọi thứ hai trả 409 `STORY_BUSY` (D-46). Khoá giữ trên kết nối Postgres của yêu cầu, nên tự nhả khi yêu cầu kết thúc hay tiến trình chết. Người chơi ngắt kết nối giữa stream thì chương không ghi, lời gọi model đang chờ bị huỷ, và khoá chỉ nhả sau khi đường đi đã dừng hẳn (D-63): gọi lại ngay trong khoảng đó có thể nhận `STORY_BUSY`, thử lại sau.
Danh sách route và schema: `http://127.0.0.1:8000/docs` (OpenAPI của FastAPI).

Lời gọi model trả bằng key người chơi đã lưu qua `/player/key`, không bao giờ bằng `OPENROUTER_API_KEY`, và có trần trong `config/limits.yaml`. Mọi lời gọi gửi kèm `max_tokens` (`limits.llm_call`); model nào được dùng ở `roles` hay `writer_tiers` phải có giá ở `config/models.yaml` `prices`, không thì lời gọi bị từ chối trước khi gửi (`CONFIG_LIMIT_NOT_SET`). Lời gọi bị huỷ hay đứt được ghi chi phí tối đa, đánh dấu ước tính, và tra lại theo id generation ở lần gọi sau của cùng truyện (D-64). Truyện phải có `story_plan` trong Postgres: truyện tạo qua `/setup` có; truyện mẫu nạp tay thì không, nên hỏi người kể trên nó báo lỗi (fail closed, D-44).

### Chạy backend cho frontend dev
Frontend (Vite, `http://localhost:5173`) gọi API qua proxy của Vite, nên trình duyệt chỉ thấy một origin. Backend **không bật CORS** (D-66): trang ở origin khác không đọc được phản hồi, kể cả `localhost:5173` khi gọi thẳng cổng 8000.
1. `docker compose up -d`, rồi chạy migration (mục Migration Postgres).
2. Trong `.env` ở gốc repo (hoặc biến môi trường): `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `POSTGRES_DSN`, `PLAYER_KEY_ENCRYPTION_KEY` (cách tạo: mục Biến môi trường), `ENABLE_DEV_ROUTES=true`.
3. Chạy backend ở `127.0.0.1:8000`:
   ```bash
   cd backend
   ENABLE_DEV_ROUTES=true uv run uvicorn writory.api:create_app --factory --reload --host 127.0.0.1 --port 8000
   ```
4. Proxy của Vite chuyển các đường của API tới `http://127.0.0.1:8000`: `/stories`, `/setup`, `/player`, `/config`, `/health` (hoặc một tiền tố chung, ví dụ `/api`, kèm rewrite bỏ tiền tố). Đường của trang (`/truyen/...`, `/moi`, `/khoa`) không trùng đường của API.
5. Viết chương là SSE trên `POST` (D-46): đọc stream bằng `fetch`, không dùng `EventSource`. Chưa kiểm SSE đi qua proxy của Vite có bị đệm hay không.

## Frontend
React + TypeScript + Tailwind, dựng bằng Vite, trong `frontend/` (D-68). Cần Node 20.19+ và npm (lockfile `package-lock.json`).
```bash
cd frontend
npm ci                 # cài đúng theo lockfile
npm run dev:mock       # chạy với máy chủ giả trong trình duyệt, không cần backend, không gọi model
npm run dev            # chạy với backend thật qua proxy (bên dưới)
npm run lint           # ESLint
npm run typecheck      # tsc strict
npm test               # Vitest + Testing Library, không mạng
npm run build          # bản build vào frontend/dist/
```
- **Proxy:** `npm run dev` chuyển `/api/*` tới `http://localhost:8000/*` (bỏ tiền tố `/api`, vì app FastAPI không có tiền tố). Đổi đích bằng `WRITORY_API_URL`; đổi tiền tố phía trình duyệt bằng `VITE_API_BASE`. Backend phải chạy với `ENABLE_DEV_ROUTES=true` (mục trên). Luồng SSE `POST /stories/{id}/chapters/next` đi qua proxy này.
- **Mock (D-69):** `npm run dev:mock` (hoặc `VITE_MOCK=1 npm run dev`) thay `fetch` bằng máy chủ giả `frontend/src/mock/`: truyện bịa, mọi endpoint giao diện dùng, luồng SSE có `: ping` và sự kiện bị cắt đôi. Trạng thái nằm trong bộ nhớ, tải lại trang là về đầu. Thêm `?mock=rong` vào URL để mở tủ trống chưa có khoá; `?loi=<MÃ>` để giả một lỗi, ví dụ `/truyen/s-chuong?loi=COST_LIMIT_CHAPTER`, `?loi=SCENE_LEAK_BLOCKED`, `?loi=ACTION_UNCLEAR`. Bản build thường không chứa lớp mock.
- Chưa có đăng nhập: màn `/dang-nhap` chỉ là giao diện, không gửi gì đi (D-44).

## CI
GitHub Actions, file `.github/workflows/ci.yml`. Chạy trên mỗi PR và mỗi lần push lên `main`.

| Job | Làm gì |
|---|---|
| `fast` | `uv sync --locked`, `uv run ruff check .`, `uv run pytest -m "not graph"` trong `backend/` |
| `graph` | dựng service container `neo4j:5.26-community` và `postgres:16`, chờ cổng 7474 của Neo4j (Postgres chờ bằng health check), rồi `uv run pytest -m graph` |
| `frontend` | Node 20, `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` trong `frontend/` |

- Marker `graph` đánh dấu mọi test cần dịch vụ Docker: Neo4j, và Postgres cho luồng ghi chương. Test nhanh (`-m "not graph"`) không cần Docker.
- Job `graph` đặt `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` và `POSTGRES_DSN` qua biến môi trường của job; mật khẩu chỉ dùng cho container CI. Test đọc kết nối từ các biến này, mặc định theo `.env.example` khi chạy local.
- Không có test nào mang marker `graph` chạy (pytest trả mã 5) thì job `graph` đỏ.
- `uv sync --locked` báo lỗi nếu `uv.lock` lệch `pyproject.toml`: chạy `uv lock` ở máy rồi commit lại.
- Chạy giống CI ở máy: các lệnh `ruff`/`pytest` ở mục trên, và các lệnh `npm` ở mục Frontend.
- `npm ci` báo lỗi nếu `package-lock.json` lệch `package.json`: chạy `npm install` ở máy rồi commit lại lockfile.

## Migration Postgres
SQL thuần trong `backend/src/writory/db/migrations/`, chạy theo thứ tự tên file, mỗi file một lần (D-20). Muốn đổi schema thì thêm file mới, không sửa file đã chạy.
```bash
cd backend
uv run python -c "from writory.config import Settings; from writory.db import connect, migrate; print(migrate(connect(Settings())))"
```
Test `-m graph` tự chạy migration trên database trong `POSTGRES_DSN`.

Sau khi kéo code có migration mới thì chạy lệnh trên trước khi mở app. Ví dụ `0004_chapter_summaries` thêm bảng `chapter_summaries` (tóm tắt chương, D-49); chưa chạy thì viết chương báo `INTERNAL_ERROR` vì không đọc được bảng này. `0005_llm_call_windows` thêm bảng đếm lời gọi model mỗi phút (D-56); chưa chạy thì mọi lời gọi model của API báo `INTERNAL_ERROR`. `0008_story_darkness_level` thêm cột `stories.darkness_level` (mức u tối theo truyện, D-67); chưa chạy thì mọi route đọc truyện báo `INTERNAL_ERROR`. `bench_run` tự chạy migration.

## Ghi chương bị kẹt `pending`
Chương ở lại `pending` khi Neo4j không trả lời hoặc tiến trình chết giữa chừng (D-6). Truyện đó không ghi được chương mới cho tới khi reconcile:
```bash
uv run python -c "from neo4j import GraphDatabase; from writory.config import Settings; from writory.db import connect, reconcile_pending; s = Settings(); d = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password.get_secret_value())); print(reconcile_pending(connect(s), d))"
```

## Biến môi trường
Danh sách đầy đủ: `.env.example`. Không commit `.env`.

- `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`: key của chủ dự án, chỉ cho bộ đo và lệnh chạy cả truyện (`bench_run`, chỉ cần `OPENROUTER_API_KEY`). Runner chỉ đọc đúng các tên này; thiếu thì báo lỗi và không gọi model.
- `ANTHROPIC_WORKSPACE_ID` (tuỳ chọn): cần khi key Anthropic không gắn với workspace. Lệnh: `docs/eval.md`.

- `PLAYER_KEY_ENCRYPTION_KEY`: khoá Fernet mã hoá key OpenRouter của người chơi (G7, D-11). Tạo bằng lệnh sau, chạy trong `backend/`:
  ```bash
  uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  Mất hoặc đổi khoá thì key đã lưu không giải mã được nữa, và người chơi phải nhập lại. Khi `ENABLE_DEV_ROUTES=true`, khoá sai định dạng thì app không khởi động (D-11, D-45).
- `ENABLE_DEV_ROUTES` (mặc định `false`): gắn router chưa có đăng nhập (truyện, khởi tạo, key và chi phí người chơi, cấu hình công khai; D-41, D-66). Chỉ bật trên máy dev.
- Cấu hình runtime nằm trong `config/*.yaml`, được nạp và kiểm schema bằng `writory.config.load_config()`. Giá trị `null` nghĩa là chưa đặt; code nào cần giá trị đó sẽ báo lỗi.

## Deploy
*(chưa có. Lưu ý: AuraDB Free tự tạm dừng sau 3 ngày không dùng, nên không hợp cho người chơi thật. Xem design §11.)*
