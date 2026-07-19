# ── Frontend (Next.js static export) ─────────────────────────────
FROM node:20-bookworm-slim AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build && FRONTEND_OUT=/frontend node scripts/copy-out.mjs

# ── API + static UI ──────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=web-build /frontend /app/frontend

RUN mkdir -p /app/data/uploads /app/data/indexes /app/logs \
    && chmod +x /app/backend/scripts/start.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend
ENV FRONTEND_DIR=/app/frontend
ENV ENVIRONMENT=production
ENV DATABASE_URL=sqlite:///./data/app.db

WORKDIR /app
EXPOSE 8000

CMD ["bash", "backend/scripts/start.sh"]
