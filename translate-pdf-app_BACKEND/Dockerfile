# ─── Stage: Final Backend Runtime ─────────────────────────────
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
		texlive-xetex \
		texlive-latex-base \
		texlive-extra-utils \
		fonts-dejavu \
		wget \
		curl \
		git \
		build-essential \
		libgl1 \
		libglib2.0-0 \
		poppler-utils \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# Copy code
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip && \
	pip install -r requirements.txt

# ─── Pre-download YOLO model to Hugging Face cache ────────────
ENV HF_HOME="/root/.cache/huggingface"
RUN mkdir -p $HF_HOME && \
	python3 -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='juliozhao/DocLayout-YOLO-DocStructBench', filename='doclayout_yolo_docstructbench_imgsz1024.pt')"

# ─── Set environment variables for runtime ─────────────────────
ENV PYTHONUNBUFFERED=1 \
	UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 8000"

# ─── Expose port & start server ───────────────────────────────
EXPOSE 8000
CMD ["sh", "-c", "$UVICORN_CMD"]
