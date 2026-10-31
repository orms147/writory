# Backend của chồng prod (D-103): uvicorn một tiến trình, không --reload, user không phải root.
# Build từ gốc repo: docker compose -f docker-compose.prod.yml build (docs/runbook.md, mục Deploy).
# Giữ bố cục repo (/app/backend, /app/config, /app/evals/...) vì writory.config.REPO_ROOT tính từ
# vị trí mã nguồn: config/ và hướng dẫn văn phong đọc lúc chạy.
FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.12 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

# Phụ thuộc trước (lớp cache), mã sau. Không cài nhóm dev và eval (D-24).
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-default-groups --no-install-project

COPY backend/src ./src
RUN uv sync --locked --no-default-groups

# File app đọc lúc chạy, ngoài mã: config/ và hướng dẫn văn phong (system prompt của model viết).
COPY config /app/config
COPY evals/scenarios/quality/style_guide_vi.md /app/evals/scenarios/quality/style_guide_vi.md
COPY evals/scenarios/quality/style_guide_audio_vi.md /app/evals/scenarios/quality/style_guide_audio_vi.md

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin writory
USER writory

EXPOSE 8000
# --no-proxy-headers: app tự quyết tin header của proxy nào (TRUSTED_PROXIES, api/deps.py).
CMD ["uvicorn", "writory.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--no-proxy-headers", "--no-server-header", "--timeout-graceful-shutdown", "30"]
