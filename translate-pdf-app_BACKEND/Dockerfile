# ─── Stage 1: Base image with Python ───────────────────────
FROM python:3.11-slim AS backend

# ─── Set working directory ──────────────────────────────────
WORKDIR /app

# ─── Install dependencies ───────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Copy source code ───────────────────────────────────────
COPY . .

# Create folders
RUN mkdir -p /app/storage/originals /app/storage/translateds

# 🔥 Fix permission issue
RUN chmod -R 777 /app/storage

# Switch to non-root
USER 1001

# Start the app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--http", "httptools", "--limit-concurrency", "100", "--backlog", "2048"]