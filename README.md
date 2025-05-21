# 📄 Translate‑PDF App

Full‑stack web app that **accepts a PDF, detects its layout, translates text, and returns a new selectable‑text PDF**.  
The project ships with two Dockerised services:

| Service      | Tech                                                                                    |
| ------------ | --------------------------------------------------------------------------------------- |
| **Backend**  | Python 3.11 (FastAPI) · Tesseract OCR · DocLayout‑YOLO (pre‑cached) · XeLaTeX · Poppler |
| **Frontend** | React 18 (Vite) · Bootstrap 5 · pdf.js viewer                                           |

Everything is isolated—no local Python, Node, Tex or model downloads if you run via Docker Compose.

---

## 🗂️ Repository Layout

```
translate-pdf-app/
│
├── translate-pdf-app_BACKEND/     # FastAPI server (Dockerfile inside)
├── translate-pdf-app_FRONTEND/    # React client
├── shared_pipeline/               # Optional shared scripts
├── docker-compose.yml             # Spins up both services together
└── README.md                      # You are here
```

---

## 🚀 1‑Command Quick Start (Docker Compose)

> **Prerequisites**  
> • Docker Desktop 23 + (includes Compose v2)  
> • Git

```bash
git clone https://github.com/YOUR‑ORG/translate-pdf-app.git
cd translate-pdf-app
docker compose up --build          # first run ~10 min (Tex + model download)
```

| URL                          | What you get                            |
| ---------------------------- | --------------------------------------- |
| <http://localhost:8000/docs> | Interactive Swagger / Redoc for backend |
| <http://localhost:5173>      | Frontend upload & side‑by‑side viewer   |

---

## ⚙️ Environment Variables

| File                                  | Purpose                          | Example                                  |
| ------------------------------------- | -------------------------------- | ---------------------------------------- |
| **`translate-pdf-app_BACKEND/.env`**  | Secrets, CORS domains            | `GEMINI_API_KEY_0=sk‑xxx`                |
| **`translate-pdf-app_FRONTEND/.env`** | Public vars (exposed to browser) | `VITE_BACKEND_URL=http://localhost:8000` |

### 📌 Developer Notice

Please open the file `translate-pdf-app_BACKEND/.env` and **fill in your real Gemini API keys** like this:

```env
GEMINI_API_KEY_0=sk-your-key-1
GEMINI_API_KEY_1=sk-your-key-2
GEMINI_API_KEY_2=sk-your-key-3
```

> **Security**: Do **not** commit backend `.env`. Inject secrets in production via your hosting provider or CI pipeline.

---

## 🛠️ Backend – Stand‑Alone Dev (No Docker)

### 1. System packages (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y   texlive-xetex texlive-latex-base texlive-extra-utils   poppler-utils tesseract-ocr libgl1 libglib2.0-0
```

### 2. Python env

```bash
cd translate-pdf-app_BACKEND
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Download YOLO weights once (≈1 GB)

```bash
python - <<'PY'
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id="juliozhao/DocLayout-YOLO-DocStructBench",
                filename="doclayout_yolo_docstructbench_imgsz1024.pt")
PY
```

### 4. Run server

```bash
uvicorn main:app --reload --port 8000
```

Browse <http://localhost:8000/docs>.

---

## 💻 Frontend – Local Dev

```bash
cd translate-pdf-app_FRONTEND
npm install           # or pnpm / yarn
npm run dev           # Vite dev server on :5173
```

Open <http://localhost:5173>. Hot reload works out of the box.

### Production build

```bash
npm run build         # writes static files to dist/
```

The Dockerfile for `frontend` copies the `dist/` output into an Nginx image.

---

## 🐳 Running Services Individually with Docker

### Build & run backend only

```bash
docker build -t translate-pdf-backend ./translate-pdf-app_BACKEND
docker run -p 8000:8000 --env-file ./translate-pdf-app_BACKEND/.env translate-pdf-backend
```

### Build & run frontend only

```bash
docker build -t translate-pdf-frontend ./translate-pdf-app_FRONTEND
docker run -p 5173:80 translate-pdf-frontend
```

---

## 📂 Persisting PDFs (Optional)

Edit `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      - ./input:/app/input # drop PDFs here
      - ./output:/app/output # translated PDFs appear here
```

---

## 🧩 Deployment Notes

1. **Set secrets** (`GEMINI_API_KEY`, etc.) in your host’s environment panel.
2. Use the same `docker compose up -d` workflow or build & push images to your registry.
3. Point your domain / reverse proxy to:
   - port 80 (frontend)
   - port 8000 (backend API for internal calls)

The backend is stateless; scale multiple replicas behind a load balancer.

---

## 🆘 Troubleshooting

| Symptom                     | Remedy                                                          |
| --------------------------- | --------------------------------------------------------------- |
| Build fails on TeX packages | Increase Docker memory / retry (network).                       |
| CORS error in browser       | Check `VITE_BACKEND_URL` and backend `FRONTEND_ORIGIN`.         |
| Ports already in use        | Adjust host port numbers in `docker-compose.yml`.               |
| Large model download slow   | Pre‑download on host and mount into `/root/.cache/huggingface`. |

---

## 📜 License

MIT © 2025 STMT & Contributors
