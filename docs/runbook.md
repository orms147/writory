# Runbook

## Yêu cầu
- Docker (có Compose)
- Python ≥ 3.12 và [uv](https://docs.astral.sh/uv/)
- Node 20.19+ và npm (cho frontend, mục Frontend)

## Chạy máy local
**Nhanh:** `make run` ở gốc repo (GNU Make; công thức chạy bằng PowerShell 7 `pwsh`, file `makefile`). Lệnh kiểm `.env` (chưa có thì chép từ `.env.example` rồi dừng để bạn điền), `uv sync` cho backend, `npm ci` cho frontend lần đầu, `docker compose up -d`, chạy migration (thử lại tới khi Postgres nhận kết nối), rồi chạy backend `127.0.0.1:8000` với `ENABLE_DEV_ROUTES=true` và giao diện `http://localhost:5173` cùng lúc; Ctrl+C dừng cả hai. `make mock` chỉ chạy giao diện với máy chủ giả, `make test` chạy test nhanh, `make stop` tắt Docker (giữ dữ liệu), `make help` xem hết. Các bước tay bên dưới làm đúng những việc đó.
```bash
cp .env.example .env          # điền mật khẩu local và key OpenRouter của bạn
docker compose up -d          # Neo4j (http://localhost:7474) + Postgres
cd backend
uv sync
uv run pytest -m "not graph"  # test nhanh: không mạng, không gọi model thật
uv run pytest -m graph        # test cần Neo4j + Postgres ở trên; Postgres dùng database riêng <tên>_test (tự tạo, hoặc POSTGRES_TEST_DSN), không đụng dữ liệu app (D-75); Neo4j: mỗi test một story_id riêng
```
Test `-m graph` đọc `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `POSTGRES_DSN`, `POSTGRES_TEST_DSN` từ biến môi trường, **không đọc `.env`** (`backend/tests/graph/conftest.py`); biến nào không đặt thì lấy giá trị mặc định giống `.env.example`. Đã đổi mật khẩu trong `.env` thì đặt các biến đó trong shell trước khi chạy test.

Chạy cả một truyện từ dòng lệnh (`writory.pipeline.bench_run`; lệnh, đề và kết quả: `docs/eval.md`, mục "Chạy cả truyện"). Lệnh đọc `NEO4J_*`, `POSTGRES_DSN` và, khi chạy thật, `OPENROUTER_API_KEY` từ biến môi trường hoặc `.env`; tự chạy migration và tạo ràng buộc Neo4j. Mỗi lần chạy dùng một story_id mới `run-<ngày>-<nhãn>-<mã>`, ghi trong `meta.json`. Truyện của lần chạy thật được giữ lại trong Neo4j + Postgres, nhưng API và giao diện không mở được nó: truyện không có chủ (`owner_id` rỗng, còn ở `AUTH_MODE=dev` API chỉ cho người chơi `dev` thấy truyện của mình) và kế hoạch ẩn không được lưu vào Postgres. Đọc lại bằng các file trong thư mục kết quả; lệnh xuất kịch bản video đọc được truyện này (mục Xuất kịch bản video); xoá bằng `delete_story_record` và `graph.delete_story`.

Chạy API ở máy (đọc biến môi trường từ `.env` ở gốc repo):
```bash
cd backend
uv run uvicorn writory.api:create_app --factory --reload
curl http://127.0.0.1:8000/health   # {"neo4j": "ok"|"down", "postgres": "ok"|"down"}; 503 nếu có phần down
```
App tạo bằng factory (`--factory`), nên import `writory.api` không cần biến môi trường.

API truyện (`/stories/...`), khởi tạo (`/setup/...`), key và chi phí người chơi (`/player/...`), đăng nhập (`/auth/...`) và cấu hình công khai (`/config/public`) theo `AUTH_MODE` (D-89):
- `AUTH_MODE=dev` (mặc định): không có đăng nhập, mọi người là người chơi dev `dev`. Router chỉ được gắn khi đặt `ENABLE_DEV_ROUTES=true` (D-41). Chỉ dùng trên máy dev. Các lệnh `curl` dưới đây chạy ở chế độ này.
- `AUTH_MODE=invite`: đăng nhập bằng mã mời (mục Đăng nhập bằng mã mời), router luôn được gắn, không cần `ENABLE_DEV_ROUTES`.

Ở cả hai chế độ, mọi yêu cầu ghi (POST, PUT, DELETE) phải có `content-type: application/json`, kể cả khi không có thân, và không được đến từ trang khác origin (chống CSRF, D-89, docs/security.md); thiếu thì `403 REQUEST_ORIGIN_INVALID`. Các lệnh `curl` dưới đây đều gửi header đó.

Chạy migration trước (mục Migration Postgres).
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
# kiểu truyện (D-153): thêm "style": "audio" để viết theo giọng kịch bản audio; bỏ trống là truyện chữ.
# truyện audio chỉ nhận mức độ dài audio_30, audio_45, audio_60 (D-155), ví dụ "length_level": "audio_30"
curl -X POST http://127.0.0.1:8000/setup/<session_id>/settings -H 'content-type: application/json'
curl -X PUT  http://127.0.0.1:8000/setup/<session_id>/settings -H 'content-type: application/json' -d '{"index": 0}'
# tương tự với plots, characters (PUT characters nhận thêm name, personality, backstory), rồi:
curl -X POST http://127.0.0.1:8000/setup/<session_id>/finalize -H 'content-type: application/json'   # trả story_id
```
Viết chương (SSE, D-46) rồi chọn hành động cho chương sau:
```bash
curl -N -X POST http://127.0.0.1:8000/stories/<story_id>/chapters/next -H 'content-type: application/json'   # event: stage | scene_ready | … | choices_ready
curl -N -X POST 'http://127.0.0.1:8000/stories/<story_id>/chapters/next?auto=true' -H 'content-type: application/json'   # tự viết (D-154): không cần lựa chọn, không tạo bộ lựa chọn
curl -X POST http://127.0.0.1:8000/stories/<story_id>/choice -H 'content-type: application/json' -d '{"choice_id": "choice-…"}'
curl -X POST http://127.0.0.1:8000/stories/<story_id>/action -H 'content-type: application/json' -d '{"text": "Tôi xuống bến hỏi chuyện."}'
curl http://127.0.0.1:8000/stories/<story_id>   # trạng thái để mở lại truyện
curl -O -J http://127.0.0.1:8000/stories/<story_id>/script.txt   # kịch bản các chương đã ghi, dán vào TTS (D-153)
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
4. Proxy của Vite chỉ chuyển `/api/*` tới backend (mặc định `http://localhost:8000`) và bỏ tiền tố `/api` (`frontend/vite.config.ts`; đổi đích, đổi tiền tố: mục Frontend). Đường của trang (`/truyen/...`, `/moi`, `/khoa`) không bắt đầu bằng `/api`.
5. Viết chương là SSE trên `POST` (D-46): đọc stream bằng `fetch`, không dùng `EventSource`. SSE qua proxy của Vite đã chạy được trong lần chạy thử đầu cuối với model thật (21/10/2026, CLAUDE.md §9); chưa đo riêng proxy có giữ sự kiện lại lâu hơn không.

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
- Đăng nhập (D-89): backend ở `AUTH_MODE=invite` thì chưa đăng nhập là về `/dang-nhap`, nhập mã mời; nút "Đăng xuất" ở thanh trên. Ở `AUTH_MODE=dev` màn này chỉ báo không cần đăng nhập. Máy chủ giả: thêm `?auth=invite` vào URL lúc mở trang, mã thử là `MOCK_INVITE_CODE` trong `frontend/src/mock/server.ts`.

## Đăng nhập bằng mã mời
Cho bạn bè chơi (D-89). Chủ dự án tạo một mã cho mỗi người; mỗi mã là một người chơi riêng (`owner_id` riêng: truyện, key, chi phí riêng). Mã chỉ in ra **một lần** lúc tạo; Postgres chỉ giữ băm, nên mất mã thì thu hồi và tạo mã mới. Gửi mã cho bạn qua kênh riêng.
```bash
cd backend   # đọc POSTGRES_DSN từ .env; chạy migration trước
uv run python -m writory.db.invites create --name "Tên bạn"   # in id inv-... và mã wt-...
uv run python -m writory.db.invites list                       # id, tên, owner_id, lần đăng nhập gần nhất; không in mã
uv run python -m writory.db.invites revoke inv-...             # thu hồi; các phiên của mã bị xoá ngay
```
Chạy backend ở chế độ này:
```bash
AUTH_MODE=invite uv run uvicorn writory.api:create_app --factory --host 127.0.0.1 --port 8000
```
- Cookie phiên `writory_session`: `HttpOnly`, `SameSite=Lax`, `Secure` trừ khi truy cập bằng http qua `localhost`/`127.0.0.1`. Sau proxy thì proxy phải giữ nguyên header `Host` (Caddy và cloudflared giữ, mục Deploy).
- Gọi bằng `curl` ở chế độ này thì ngoài `-H 'content-type: application/json'` (mọi chế độ, mục trên) còn phải gửi cookie phiên (`-b`).
- Giới hạn lần nhập mã tính theo địa chỉ máy: chạy thẳng uvicorn là địa chỉ uvicorn thấy; sau proxy là địa chỉ proxy tin cậy báo (`TRUSTED_PROXIES`, mục Deploy, D-103).
- Dữ liệu cũ của người chơi dev `dev` không thuộc mã nào, nên không thấy được ở chế độ `invite`.

## CI
GitHub Actions, file `.github/workflows/ci.yml`. Chạy trên mỗi PR và mỗi lần push lên `main`.

| Job | Làm gì |
|---|---|
| `fast` | `uv sync --locked`, `uv run ruff check .`, `uv run pytest -m "not graph"` trong `backend/` |
| `graph` | dựng service container `neo4j:5.26-community` và `postgres:16`, chờ cổng 7474 của Neo4j (Postgres chờ bằng health check), rồi `uv run pytest -m graph` |
| `frontend` | Node 20, `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build` trong `frontend/` |

- Marker `graph` đánh dấu mọi test cần dịch vụ Docker: Neo4j, và Postgres cho luồng ghi chương. Test nhanh (`-m "not graph"`) không cần Docker.
- Job `graph` đặt `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` và `POSTGRES_DSN` qua biến môi trường của job; mật khẩu chỉ dùng cho container CI. Test đọc kết nối từ các biến này (không đọc `.env`); không đặt thì lấy giá trị mặc định giống `.env.example`.
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
Test `-m graph` tự chạy migration trên database test riêng (tên database của `POSTGRES_DSN` thêm `_test`, hoặc `POSTGRES_TEST_DSN`), không bao giờ trên database của app (`backend/tests/graph/conftest.py`, D-75).

Sau khi kéo code có migration mới thì chạy lệnh trên trước khi mở app. Ví dụ `0004_chapter_summaries` thêm bảng `chapter_summaries` (tóm tắt chương, D-49); chưa chạy thì viết chương báo `INTERNAL_ERROR` vì không đọc được bảng này. `0005_llm_call_windows` thêm bảng đếm lời gọi model mỗi phút (D-56); chưa chạy thì mọi lời gọi model của API báo `INTERNAL_ERROR`. `0008_story_darkness_level` thêm cột `stories.darkness_level` (mức u tối theo truyện, D-67); chưa chạy thì mọi route đọc truyện báo `INTERNAL_ERROR`. `0009_invite_login` thêm bảng mã mời, phiên đăng nhập và bộ đếm lần nhập mã (D-89); chưa chạy thì ở `AUTH_MODE=invite` đăng nhập và mọi route cần đăng nhập báo `INTERNAL_ERROR`, ở `AUTH_MODE=dev` không ảnh hưởng. `bench_run` tự chạy migration.

## Ghi chương bị kẹt `pending`
Chương ở lại `pending` khi Neo4j không trả lời hoặc tiến trình chết giữa chừng (D-6). Truyện đó không ghi được chương mới cho tới khi reconcile. Ở `APP_ENV=prod`, backend tự làm việc này mỗi lần khởi động (D-105); kết quả từng chương nằm trong log (`áp lại chương pending: ...`). Ở dev, hoặc khi log báo lỗi, chạy tay:
```bash
uv run python -c "from neo4j import GraphDatabase; from writory.config import Settings; from writory.db import connect, reconcile_idle_stories; s = Settings(); d = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password.get_secret_value())); print(reconcile_idle_stories(connect(s), d))"
```
Lệnh này bỏ qua truyện đang có người viết (khoá chạy đôi D-46, kết quả `busy`), nên chạy khi app đang mở cũng được. `failed`: Neo4j từ chối gói, truyện giữ nguyên chương trước và viết lại được. `pending`: Neo4j vẫn chưa trả lời, hoặc lỗi khác (tên lỗi kèm theo).

## Xuất kịch bản video (admin, D-125)
Chỉ chạy được trên máy có `POSTGRES_DSN` và `NEO4J_*` (Docker đang chạy). Bản xuất có lộ bí mật: không đưa cho người chơi. Chỉ đọc, không ghi DB.
```bash
cd backend
# không tốn tiền: chỉ bảng nhân vật, bảng nơi chốn, sơ đồ tuyến theo chương
uv run python -m writory.export.video --story <id> --sheets-only --out ../exports/thu
# model giả, không mạng, không key: xem cấu trúc file
uv run python -m writory.export.video --story <id> --dry-run --dialogue-lang zh
# chạy thật: key của chủ dự án trong OPENROUTER_API_KEY (môi trường hoặc --env-file), bắt buộc --budget
uv run python -m writory.export.video --story <id> --dialogue-lang zh --chapters 1-3 --budget 0.10
```
`--chapters` nhận `N` hoặc `A-B` (mặc định cả truyện). `--dialogue-lang` là thẻ ngôn ngữ của lời thoại (zh, vi, en…). `--budget` không được vượt `limits.video_export.max_budget_usd`. Lời thoại của mỗi shot bị kiểm nhịp theo ngôn ngữ (`limits.video_export.dialogue_max_per_second`): quá dày thì model làm lại, vẫn dày thì code tách shot theo lượt thoại và đánh dấu `split_by_code` (D-127); lượt thoại quá dài cho mọi shot được đánh dấu `pace_over`. Kiểm duyệt G9 trên prompt cuối bật mặc định; `--no-moderate` tắt và in cảnh báo. Mặc định ghi `exports/<story>-<ngày>/` (git bỏ qua): `script.md` (đọc), `script.json` (máy đọc), `prompts.txt` (mỗi shot một prompt, dán thẳng vào app video), `calls.jsonl` (số liệu từng lời gọi, không có chữ truyện). Thư mục `--out` đã có kết quả thì lệnh từ chối ngay (đổi `--out` hay xoá thư mục), không đè bản trả tiền cũ. Cảnh có mức kiểm duyệt BLOCKED hay HARD_BLOCKED (`withheld_moderation`), hoặc không kiểm duyệt được (`withheld_unmoderated`), bị giữ lại hoàn toàn trong `script.json`; chỉ mức OVER_DARKNESS thì cảnh vẫn có và được đánh dấu để admin quyết. Mã thoát: 0 xong; 1 sai tham số, cấu hình hay dữ liệu (`EXPORT_STORY_NOT_FOUND`, `EXPORT_DB_UNAVAILABLE`, `EXPORT_ENV_MISSING`); 2 dừng vì chạm `--budget` (phần đã xong vẫn được ghi); 3 có cảnh lỗi hay có cảnh bị giữ vì không kiểm duyệt được. Truyện cũ không có ngoại hình: mô tả được sinh bù lúc xuất và đánh dấu `inferred`.

## Viết kịch bản audio (admin, D-151)
Công cụ của admin, không cần Docker hay DB: chỉ cần key của chủ dự án (`OPENROUTER_API_KEY` trong môi trường hoặc `--env-file`). Ghi vào `exports/` (git bỏ qua).
```bash
cd backend
# 1. nhờ model đề xuất vài hướng đi từ tag: ideas.md để đọc, ideas.yaml để sửa và chọn
uv run python -m writory.audio.script propose --tags "thiếu gia bị hoán đổi thân phận, tiểu thư giả, trà xanh" --count 5 --budget 0.05
# 2. viết kịch bản từ hướng đi đã chọn (hay tự viết: --premise "...", lặp --premise để viết nhiều kịch bản)
uv run python -m writory.audio.script write --premise-file ../exports/audio-ideas-<ngày>/ideas.yaml --pick i2 --minutes 30 --budget 0.30
# chạy khô: model giả, không mạng, không key, không tốn tiền
uv run python -m writory.audio.script write --premise "Thiếu gia thật bị tráo lúc sinh..." --minutes 30 --dry-run
```
- `--minutes` nằm trong `limits.audio_script.minutes_min`..`minutes_max`; số chữ cần = phút × `words_per_minute`, chia đều thành các đoạn không quá `segment_words` chữ, mỗi đoạn một lời gọi. Đo tốc độ đọc của TTS đang dùng (số chữ của `tts.txt` chia số phút của file audio) rồi chạy lại với `--wpm`.
- File hướng đi: YAML là danh sách chữ hay `{id, premise, minutes}` (`ideas.yaml` của `propose` dùng được luôn); file chữ thì mỗi khối cách nhau một dòng trống. `minutes` của từng hướng đi đè `--minutes`; `--pick` chọn theo id.
- `--budget` là trần của cả lệnh, không vượt `limits.audio_script.max_budget_usd`. Chạy bằng model của bộ đo (Muse, key Meta) thì thêm `--config-dir ../evals/config/meta`.
- Mỗi hướng đi một thư mục `exports/audio-<ngày>/<id>/`: `tts.txt` (chữ đọc liền, dán thẳng vào TTS một giọng: không tên người nói, không âm thanh, không tiêu đề), `script.md` (kịch bản đọc được: nhân vật, giọng gợi ý, bí mật, từng đoạn có người nói, cách đọc, âm thanh), `script.json` (cho TTS nhiều giọng), `calls.jsonl` (số liệu từng lời gọi). Thư mục đã có kết quả thì lệnh từ chối ngay.
- Mỗi đoạn được hỏi lại tối đa `limits.audio_script.schema_retries` lần khi code trả về. Đoạn lệch số chữ sau mọi lượt vẫn được giữ, đánh dấu `length_off`; đoạn không lộ bí mật đến hạn vẫn được giữ, bí mật dời sang đoạn sau (`reveal_slipped`). Đoạn bị kiểm duyệt chặn ở mức BLOCKED được viết lại tối đa `limits.audio_script.moderation_rewrites` lần (`moderation_rewrites` trong `script.json`). Đoạn lỗi khác (`error`, lý do trong `script.json`), vẫn bị kiểm duyệt chặn (`withheld_moderation`), không kiểm được (`withheld_unmoderated`) hay chạm trần (`skipped_budget`) không có chữ nào trong ba file, và kịch bản dừng ở đó. `--no-moderate` tắt kiểm duyệt và in cảnh báo.
- Mã thoát: 0 xong; 1 sai tham số hay cấu hình, kể cả thư mục `--out` đã có file; 2 dừng vì chạm `--budget` (phần đã xong vẫn được ghi; hướng đi chưa bắt đầu thì không có thư mục); 3 có đoạn lỗi hay bị giữ lại (ưu tiên hơn 2), hay `AUDIO_WRITE_FAILED`.

## Biến môi trường
`.env.example` có các biến thường dùng của chồng dev, chưa phải mọi biến: mục này ghi thêm `APP_ENV`, `TRUSTED_PROXIES`, `POSTGRES_TEST_DSN`; biến của chồng prod ở `.env.prod.example` (mục Deploy); biến của frontend (`WRITORY_API_URL`, `VITE_API_BASE`, `VITE_MOCK`) ở mục Frontend. Không commit `.env`.

- `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `META_API_KEY`: key của chủ dự án, chỉ cho bộ đo, lệnh chạy cả truyện (`bench_run`, chỉ cần `OPENROUTER_API_KEY`) và lệnh xuất kịch bản video của admin (chỉ cần `OPENROUTER_API_KEY`, mục Xuất kịch bản video). `META_API_KEY` cho giám khảo thứ hai của bài F (D-108) và cho bộ đo chạy bằng model Meta qua `--config-dir evals/config/meta` (D-140); `ANTHROPIC_API_KEY` còn cho bộ đo chạy bằng Claude qua `--config-dir evals/config/anthropic` (D-145). Xem `docs/eval.md`. App không dùng các key này: lời gọi của người chơi trả bằng key của họ (D-2). Lệnh chỉ đọc đúng các tên này; thiếu thì báo lỗi và không gọi model.
- `ANTHROPIC_WORKSPACE_ID` (tuỳ chọn): cần khi key Anthropic không gắn với workspace. Lệnh: `docs/eval.md`.
- `POSTGRES_TEST_DSN` (tuỳ chọn, không có trong `.env.example`): database Postgres cho test `-m graph`; không đặt thì là tên database của `POSTGRES_DSN` thêm `_test`, tự tạo (D-75).

- `PLAYER_KEY_ENCRYPTION_KEY`: khoá Fernet mã hoá key OpenRouter của người chơi (G7, D-11). Tạo bằng lệnh sau, chạy trong `backend/`:
  ```bash
  uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  Mất hoặc đổi khoá thì key đã lưu không giải mã được nữa, và người chơi phải nhập lại. Khi router người chơi được gắn (`AUTH_MODE=invite`, hoặc `ENABLE_DEV_ROUTES=true` ở `AUTH_MODE=dev`), khoá sai định dạng thì app không khởi động (`api/app.py` `create_app`; D-11, D-45).
- `ENABLE_DEV_ROUTES` (mặc định `false`): ở `AUTH_MODE=dev`, gắn router của người chơi (truyện, khởi tạo, key và chi phí người chơi, cấu hình công khai, đăng nhập; D-41, D-66), mọi người là người chơi dev. Chỉ bật trên máy dev.
- `AUTH_MODE` (mặc định `dev`): `dev` hoặc `invite` (D-89). `invite`: đăng nhập bằng mã mời, router luôn được gắn. Thời hạn phiên và số lần nhập mã mỗi máy: `config/limits.yaml`, mục `auth`.
- `APP_ENV` (mặc định `dev`): `prod` cho chồng prod (D-103): bắt buộc `AUTH_MODE=invite` và mật khẩu Neo4j, Postgres mạnh, tự chạy migration lúc khởi động, không có trang OpenAPI. Biến của chồng prod: `.env.prod.example`, mục Deploy.
- `TRUSTED_PROXIES` (mặc định rỗng): IP hoặc mạng của reverse proxy, cách nhau dấu phẩy; chỉ yêu cầu từ đó mới được đọc `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` (D-103). Chạy thẳng uvicorn thì để trống.
- Cấu hình runtime nằm trong `config/*.yaml`, được nạp và kiểm schema bằng `writory.config.load_config()`. Giá trị `null` nghĩa là chưa đặt; code nào cần giá trị đó sẽ báo lỗi.

## Deploy
Bản 1 chạy trên máy nhà của chủ dự án (Windows 11 + Docker Desktop), ra ngoài qua Cloudflare Tunnel; chủ dự án tự bật khi có người chơi và tắt khi xong (D-103). Chồng prod chạy được trên mọi máy có Docker; script bật, tắt viết cho PowerShell.

**Chồng prod** (`docker-compose.prod.yml`, project `writory-prod`): `cloudflared` → `proxy` (Caddy, `deploy/Caddyfile`: bản build tĩnh của frontend và `/api/*` tới backend, bỏ tiền tố `/api` như proxy Vite; SSE không đệm) → `backend` (`deploy/backend.Dockerfile`, uvicorn một tiến trình, user không phải root) → `neo4j`, `postgres`. Không service nào mở cổng ra máy: đường vào duy nhất là tunnel, HTTPS kết thúc ở Cloudflare. Neo4j và Postgres nằm trong mạng `data` nội bộ, proxy và cloudflared không tới được. Dữ liệu nằm trong volume của project (`writory-prod_neo4j-data`, `writory-prod_postgres-data`, `writory-prod_caddy-*`).

**Chạy chung máy với chồng dev.** Hai chồng không dùng chung project, mạng, volume hay cổng: chồng dev (`docker-compose.yml`) giữ 7474, 7687, 5432, app dev giữ 8000, 5173; chồng prod không mở cổng nào. RAM: hai Neo4j có thể chạy cùng lúc. Neo4j prod có heap và pagecache nhỏ hơn Neo4j dev (mặc định trong `docker-compose.prod.yml`, đổi bằng `NEO4J_HEAP`, `NEO4J_PAGECACHE` trong `.env.prod`), vì đồ thị của vài người bạn chỉ vài nghìn nút; Neo4j dev giữ số của `docker-compose.yml`. Không đặt `.wslconfig` thì Docker Desktop cấp cho máy ảo WSL tối đa một nửa RAM của máy. Không cần bật chồng dev lúc mở server.

### Lần đầu, từng bước (chủ dự án tự làm)
Tóm tắt cả quy trình; chi tiết ở các mục bên dưới. Chồng prod chưa chạy với tunnel thật lần nào (CLAUDE.md §9), nên lần đầu nên thử với chính mình trước khi gửi link.
1. **Tên miền.** Mua ở Cloudflare (bảng điều khiển → Domain Registration → Register Domains), hoặc mua nơi khác rồi thêm vào Cloudflare (Domains → Onboard a domain) và đổi nameserver ở nơi bán; đợi tên miền báo Active. Không có tên miền thì không chơi được: Quick Tunnel (trycloudflare) không chạy SSE nên không viết được chương (phụ lục cuối mục).
2. **Tunnel.** Zero Trust → Networks → Tunnels → Create a tunnel → Cloudflared, đặt tên `writory`, chép token (chuỗi sau `--token`). Thêm Public Hostname `writory.<tên miền>`, Service `HTTP`, URL `proxy:80`. Claude Code có plugin Cloudflare thì nhờ được việc tạo tunnel và hostname; token thì tự chép.
3. **`.env.prod`.** Theo bước 2 của "Chuẩn bị một lần": token, mật khẩu Neo4j và Postgres, khoá mã hoá key người chơi, `PUBLIC_URL`. Cất một bản ở ngoài máy.
4. **Bật.** Mở Docker Desktop, chạy `powershell -ExecutionPolicy Bypass -File deploy\prod-up.ps1 -Build`, đợi script báo app trả lời, tunnel đã nối và in link.
5. **Thử với chính mình.** Tạo một mã mời (mục Mã mời), mở link trên điện thoại dùng 4G (ngoài mạng nhà), nhập mã, khởi tạo một truyện Ngắn và viết một chương: chữ hiện dần là SSE qua tunnel chạy được.
6. **Mở cho bạn.** Gửi link và mỗi người một mã. Xem tình trạng bằng `prod-status.ps1`; xong thì `prod-down.ps1`.
7. **Giữ dữ liệu.** Sao lưu trước khi cập nhật code (mục Sao lưu và khôi phục, Cập nhật phiên bản).

### Chuẩn bị một lần
1. **Cloudflare:** tài khoản Cloudflare và một tên miền đã thêm vào Cloudflare (nameserver trỏ về Cloudflare). Bảng Zero Trust → Networks → Tunnels → Create a tunnel → Cloudflared, đặt tên (ví dụ `writory`), chép **token** ở bước cài đặt (chuỗi sau `--token`; không cần cài cloudflared lên máy, container dùng token). Thêm Public Hostname: tên miền con (ví dụ `writory.<tên miền>`), Service `HTTP`, URL `proxy:80`. Chưa có tên miền thì xem phụ lục "Thử nhanh bằng trycloudflare".
2. **`.env.prod`** ở gốc repo (không commit; `.gitignore` đã chặn): chép `.env.prod.example` thành `.env.prod`, rồi điền
   - `CLOUDFLARE_TUNNEL_TOKEN`: token ở bước 1;
   - `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`: mỗi cái một chuỗi chữ và số ngẫu nhiên, tạo bằng `cd backend && uv run python -c "import secrets; print(secrets.token_hex(24))"`. Mật khẩu Postgres nằm trong URL kết nối nên chỉ dùng chữ và số;
   - `PLAYER_KEY_ENCRYPTION_KEY`: cách tạo ở mục Biến môi trường. Lưu thêm một bản `.env.prod` ở chỗ an toàn ngoài máy: mất khoá thì key người chơi đã lưu không đọc được;
   - `PUBLIC_URL` (tuỳ chọn): `https://writory.<tên miền>`, để `prod-up` in ra.

   Backend ở `APP_ENV=prod` không khởi động nếu `AUTH_MODE` khác `invite`, hoặc mật khẩu Neo4j, Postgres ngắn hay là mật khẩu mẫu (`config.prod_problems`); compose dừng ngay nếu thiếu biến bắt buộc.
3. Script PowerShell chạy bằng `powershell -ExecutionPolicy Bypass -File deploy\<tên>.ps1` từ gốc repo (không cần đổi chính sách của máy).

### Bật server khi có người chơi, tắt khi xong
1. Mở Docker Desktop, đợi nó báo "Engine running".
2. Bật: `powershell -ExecutionPolicy Bypass -File deploy\prod-up.ps1`. Script kiểm Docker, kiểm `.env.prod` đủ biến, bật các container, chờ `/api/health` qua proxy trong mạng docker, báo tunnel đã nối chưa và in link. Lần đầu, và sau khi kéo code mới, thêm `-Build` để dựng lại image.
3. Gửi link và mã mời cho bạn (mục Mã mời dưới đây).
4. Xem: `powershell -ExecutionPolicy Bypass -File deploy\prod-status.ps1`: trạng thái container, app có trả lời không, số việc đang gọi model (khoá chạy đôi D-46 trong Postgres: viết chương, hỏi người kể, khởi tạo...), log gần nhất (`-Lines 100` để xem nhiều hơn).
5. Tắt: `powershell -ExecutionPolicy Bypass -File deploy\prod-down.ps1`. Đang có việc gọi model thì script hỏi lại (chương đang viết sẽ không được ghi, người chơi bấm viết lại); `-Force` để tắt luôn. Script dùng `docker compose stop`: dữ liệu giữ nguyên. Không bao giờ dùng `down -v` với project `writory-prod`: lệnh đó xoá dữ liệu.

**Khi nào server tự lên lại.** Mọi container có `restart: unless-stopped`. Đã kiểm trên máy này (Docker Desktop, engine 29.6.2, project thử): backend chết giữa chừng thì Docker tự bật lại; sau `prod-down` rồi khởi động lại Docker Desktop thì không container nào tự lên. Container còn chạy lúc `docker desktop restart` cũng không tự lên lại. Chưa kiểm khi Windows tắt đột ngột (mất điện, tự khởi động lại để cập nhật): khi đó chồng prod có thể tự lên lúc Docker Desktop mở lần sau. Muốn chắc thì chạy `prod-down` trước khi tắt máy, và sau khi mở máy chạy `prod-status` để xem.

### Mã mời
Chạy khi server đang bật. Mã in một lần (mục Đăng nhập bằng mã mời):
```bash
docker compose -p writory-prod -f docker-compose.prod.yml --env-file .env.prod exec backend python -m writory.db.invites create --name "Tên bạn"
docker compose -p writory-prod -f docker-compose.prod.yml --env-file .env.prod exec backend python -m writory.db.invites list
docker compose -p writory-prod -f docker-compose.prod.yml --env-file .env.prod exec backend python -m writory.db.invites revoke inv-...
```
Luôn kèm `--env-file .env.prod`: thiếu thì compose đọc `.env` của máy dev và dừng vì thiếu biến.

### Khởi động, migration, chi phí
- Lúc khởi động ở `APP_ENV=prod`, backend chạy migration Postgres, tạo ràng buộc Neo4j (`graph.ensure_schema`) và đọc thử hướng dẫn văn phong (`api/app.prepare_storage`); lỗi thì backend không lên và compose thử lại, xem log bằng `prod-status`. Sau đó backend áp lại chương kẹt `pending` (D-105); bước này lỗi thì chỉ ghi log, backend vẫn lên. Chồng dev vẫn chạy migration và áp lại bằng tay (mục Migration Postgres, mục Ghi chương bị kẹt `pending`).
- Ở prod không có trang OpenAPI (`/docs`).
- Chi phí (G8): người chơi dùng key OpenRouter của chính họ (D-2). Trần mỗi cảnh, chương, truyện và số lời gọi mỗi phút của từng người chơi (`config/limits.yaml`) chạy như ở dev: tính theo `owner_id` của phiên đăng nhập, không phụ thuộc chế độ chạy. Không có trần tổng theo người chơi (mỗi truyện có trần riêng), nên khuyên bạn bè đặt hạn mức chi tiêu cho key ở trang OpenRouter.
- Chương kẹt `pending` mà lần khởi động chưa áp được (log báo `pending` hoặc lỗi): chạy đúng câu lệnh reconcile ở mục trên bằng `docker compose -p writory-prod -f docker-compose.prod.yml --env-file .env.prod exec backend python -c "..."`.

### Địa chỉ người dùng sau tunnel
Bộ đếm lần nhập mã (D-89) tính theo địa chỉ người dùng. Chuỗi tin: Cloudflare → `cloudflared` (IP cố định `TUNNEL_IP`) → Caddy (`PROXY_IP`) → backend. Caddy chỉ đọc `CF-Connecting-IP` khi yêu cầu đến từ `cloudflared` (`trusted_proxies`), rồi đặt lại `X-Real-IP`. Backend chỉ đọc `X-Real-IP` (không có thì phần tử cuối của `X-Forwarded-For`) và `X-Forwarded-Proto` khi yêu cầu đến từ proxy (`TRUSTED_PROXIES`; `api/deps.client_address`, `forwarded_https`). Header giả từ nơi khác bị bỏ qua. Cookie phiên `Secure` vì `Host` là tên miền thật; trên `localhost`/`127.0.0.1` thì theo `X-Forwarded-Proto` tin được. Mạng `edge` có subnet cố định (`EDGE_SUBNET`); trùng mạng khác trên máy thì đổi `EDGE_SUBNET`, `PROXY_IP`, `TUNNEL_IP` cùng lúc.

### Sao lưu và khôi phục
- Sao lưu: `powershell -ExecutionPolicy Bypass -File deploy\prod-backup.ps1` (`-OutDir D:\writory-backups` để ghi chỗ khác; `-Force` để không hỏi khi đang có việc chạy). Ghi `backups\<ngày-giờ>\postgres.dump` (`pg_dump -Fc`) và `neo4j.dump` (`neo4j-admin database dump`; Neo4j Community chỉ dump được khi database dừng). Server tắt khoảng một phút để hai kho khớp nhau (một chương ghi vào cả hai, D-6); đang bật thì bật lại sau. Chép thư mục `backups\` ra ổ khác hoặc lên mây; giữ `.env.prod` ở chỗ riêng.
- Khôi phục: `powershell -ExecutionPolicy Bypass -File deploy\prod-restore.ps1 -From backups\<ngày-giờ>`: **xoá** dữ liệu Postgres và Neo4j hiện có của `writory-prod` rồi nạp bản sao lưu (gõ `khoi-phuc` để xác nhận, hoặc `-Force`). Cần đúng `PLAYER_KEY_ENCRYPTION_KEY` lúc sao lưu; khác thì người chơi nhập lại key, truyện vẫn còn.
- Không có PowerShell: làm tay đúng các bước trong hai script (dừng `cloudflared proxy backend neo4j`; `pg_dump`/`pg_restore` qua `exec postgres`; `run --rm --no-deps -v <thư mục>:/backups neo4j neo4j-admin database dump|load neo4j ...`).

### Cập nhật phiên bản
```bash
git pull
powershell -ExecutionPolicy Bypass -File deploy\prod-backup.ps1     # trước mỗi lần cập nhật
powershell -ExecutionPolicy Bypass -File deploy\prod-up.ps1 -Build  # dựng lại image; migration tự chạy
```
Đọc log: `prod-status.ps1`, hoặc `docker compose -p writory-prod -f docker-compose.prod.yml --env-file .env.prod logs -f backend`.

### Thử chồng prod trên máy, không tunnel
`deploy/docker-compose.localtest.yml` tắt `cloudflared` và mở proxy chỉ ở `127.0.0.1:<LOCALTEST_PORT>` (cổng không trùng chồng dev). Dùng project và file env thử riêng, xong thì xoá đúng project đó:
```bash
docker compose -p writory-prodtest -f docker-compose.prod.yml -f deploy/docker-compose.localtest.yml --env-file <env thử> up -d --build
curl http://127.0.0.1:<cổng>/api/health
docker compose -p writory-prodtest -f docker-compose.prod.yml -f deploy/docker-compose.localtest.yml --env-file <env thử> down -v
```
File env thử cần đủ biến bắt buộc (token để chữ bất kỳ, vì cloudflared không chạy), và nên đổi `EDGE_SUBNET`, `PROXY_IP`, `TUNNEL_IP` để không trùng mạng của `writory-prod`. Các script đọc `WRITORY_PROD_PROJECT`, `WRITORY_PROD_ENV_FILE`, `WRITORY_PROD_EXTRA_COMPOSE` để chạy trên project thử; đừng đặt các biến này khi chạy thật. Trên Windows, gọi `127.0.0.1` thay vì `localhost`: cổng chỉ mở trên IPv4, và `localhost` có thể thử `::1` trước rồi treo.

### Phụ lục: thử nhanh bằng trycloudflare
Chưa có tên miền: khi chồng prod đang bật, `docker run --rm --network writory-prod_edge cloudflare/cloudflared:2025.10.0 tunnel --no-autoupdate --url http://proxy:80` in ra một URL `https://<ngẫu nhiên>.trycloudflare.com`. URL đổi mỗi lần chạy và không có bảo đảm hoạt động, chỉ để thử. Tunnel tạm này không có IP cố định nên Caddy không tin `CF-Connecting-IP` của nó: mọi người chung một bộ đếm lần nhập mã. Quick Tunnel không hỗ trợ SSE (tài liệu Cloudflare, Tunnel → Quick Tunnels, mục Limitations): viết chương qua SSE (D-46) không chạy qua đường này, nên không chơi được, chỉ thử được đăng nhập, khởi tạo, sổ tay. Chưa kiểm trên WriTory.

### Phụ lục: máy có IP công khai (VPS), không dùng tunnel
Đặt `SITE_ADDRESS=<tên miền>` trong `.env.prod` để Caddy tự lấy chứng chỉ HTTPS, mở cổng `80:80`, `443:443` cho `proxy` bằng một file override như `deploy/docker-compose.localtest.yml` (không kèm `127.0.0.1`), trỏ bản ghi DNS A của tên miền về IP máy, và tắt `cloudflared` (`profiles`). Khi đó Caddy không tin header của ai, `{client_ip}` là địa chỉ nối tới. Chưa kiểm.
