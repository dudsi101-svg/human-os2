# Dzik OS — obraz produkcyjny (backend + zbudowany frontend PWA).
# Kontekst budowania: KORZEŃ repozytorium (potrzebny pakiet hos_engine):
#   docker build -f apps/dzik-os/Dockerfile -t dzik-os .

FROM node:22-alpine AS frontend
WORKDIR /build
COPY apps/dzik-os/frontend/package.json apps/dzik-os/frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY apps/dzik-os/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Human OS Core (hos_engine) + backend Dzik OS
COPY pyproject.toml README.md LICENSE ./
COPY hos_engine/ ./hos_engine/
RUN pip install .
COPY apps/dzik-os/backend/ ./apps/dzik-os/backend/
RUN pip install ./apps/dzik-os/backend[postgres]

# Zbudowany frontend serwowany przez FastAPI (main.py wykrywa dist/)
COPY --from=frontend /build/dist/ ./apps/dzik-os/frontend/dist/

RUN useradd --create-home dzik && mkdir -p /data && chown -R dzik /data /app
USER dzik
ENV DZIK_DATABASE_URL=sqlite:////data/dzik.db \
    DZIK_AUDIT_DB=/data/audit.db \
    DZIK_UPLOAD_DIR=/data/uploads \
    DZIK_FRONTEND_DIST=/app/apps/dzik-os/frontend/dist \
    DZIK_ENV=production
EXPOSE 8000
CMD ["uvicorn", "dzik_os.main:app", "--host", "0.0.0.0", "--port", "8000"]
