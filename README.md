# AI Legal Copilot

Understand contracts. Detect risks. Walk into legal conversations prepared.

Full-stack RAG app: upload legal docs → cited Q&A, explain, risks, consultation prep, expert category.  
**Live:** [https://legal-rag-t4gw.onrender.com](https://legal-rag-t4gw.onrender.com)

> Legal information, not legal advice.

## Stack

- **`web/`** — Next.js + TypeScript + Tailwind (UI source)
- **`backend/`** — FastAPI + LangChain + OpenAI + FAISS + SQLite
- **Docker / Render** — builds UI into the image and serves it from the API

## Local

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # set OPENAI_API_KEY + SECRET_KEY

# API (terminal 1)
export PYTHONPATH=$PWD/backend
bash backend/scripts/start.sh
# → http://127.0.0.1:8000

# UI (terminal 2)
cd web && npm install && npm run dev
# → http://127.0.0.1:3000
# web/.env.local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Optional: build static UI for same-origin serving by FastAPI:

```bash
cd web && npm run build:static   # writes ./frontend (gitignored)
```

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`) on every PR and push to `main`:

1. **Frontend** — `npm ci`, lint, build  
2. **Backend** — install deps, route smoke, pytest  
3. **Docker** — build the production image  
4. **Deploy** (push to `main` only) — calls the Render deploy hook after CI passes

### One-time Render hook setup

1. Render dashboard → your service → **Settings** → **Deploy Hook** → copy URL  
2. GitHub repo → **Settings** → **Secrets and variables** → **Actions**  
3. Add secret `RENDER_DEPLOY_HOOK` = that URL  

Recommended: turn **off** Render auto-deploy so production only updates after CI is green.

## Deploy

Render uses `Dockerfile` + `render.yaml`. Set `OPENAI_API_KEY` and `SECRET_KEY` in the service env.

## Layout

```
web/                      UI source (edit here)
backend/                  API + RAG (edit here)
.github/workflows/        CI/CD
Dockerfile                production image
render.yaml               Render config
```
