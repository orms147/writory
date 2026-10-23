# Proxy của chồng prod (D-103): bản build tĩnh của frontend + Caddy (deploy/Caddyfile).
# Build từ gốc repo: docker compose -f docker-compose.prod.yml build.
FROM node:20-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Bản build thường: không có máy chủ giả, API ở /api (frontend/src/api/client.ts).
RUN npm run build

FROM caddy:2.10-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
