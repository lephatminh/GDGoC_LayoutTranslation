# 📄 Translate‑PDF App

A full‑stack project that **takes a PDF in one language and returns a translated, selectable‑text PDF**.  
Everything runs in Docker—no local Python, Node, .NET, Ghostscript, or Tesseract installs required.

---

## 🗂️ Repository Layout

```
translate-pdf-app/
│
├── translate-pdf-app_BACKEND/   # FastAPI + PDFPig + Tesseract + Ghostscript
├── translate-pdf-app_FRONTEND/  # React + Bootstrap, served by Nginx in production
├── shared_pipeline/             # OCR / translation helpers (mounted into backend)
├── docker-compose.yml           # Brings up backend + frontend together
└── README.md                    # You are here
```

---

## 🚀 Quick Start (Everything with Docker)

> **Prerequisites**: Docker Desktop 23 + (includes Compose v2).  
> Copy‑paste in PowerShell / Bash / Zsh:

```bash
git clone https://github.com/YOUR‑ORG/translate-pdf-app.git
cd translate-pdf-app
docker compose up --build
```

| URL | What you’ll see |
|-----|-----------------|
| <http://localhost:8000/docs> | Interactive Swagger for backend |
| <http://localhost:5173>      | Frontend viewer (upload + side‑by‑side PDFs) |

The first build compiles Ghostscript (~10 min). Subsequent runs are instant.

---

## ⚙️ Environment Variables

### Backend (`translate-pdf-app_BACKEND/.env`)

```
# CORS origin the frontend uses
FRONTEND_ORIGIN=http://localhost:5173
# If you deploy the frontend elsewhere, set the public host here
FRONTEND_HOST=http://localhost:5173
# Optional: your OpenAI / Gemini keys, etc.
# OPENAI_API_KEY=xxx
```

### Frontend (`translate-pdf-app_FRONTEND/.env`)

```
# Where the backend lives
VITE_BACKEND_URL=http://localhost:8000
```

> **Tip:** Samples named `.env.example` are provided; copy → rename to `.env` and edit.

---

## 🛠️ Backend Server (Standalone Dev Mode)

1. **Create venv & install deps**

   ```bash
   cd translate-pdf-app_BACKEND
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install system tools** (Debian/Ubuntu):

   ```bash
   sudo apt update && sudo apt install tesseract-ocr poppler-utils ghostscript
   ```

3. **Run**:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

   Browse <http://localhost:8000/docs> to test.

---

## 💻 Frontend Server (Standalone Dev Mode)

1. ```bash
   cd translate-pdf-app_FRONTEND
   npm install          # or pnpm / yarn
   npm run dev          # Vite dev server, defaults to port 5173
   ```

2. Open <http://localhost:5173> – hot‑reload will pick up any code change.

### Production Build

```bash
npm run build   # outputs static files to dist/
```

These static files are copied into the Nginx image during `docker compose up --build`.

---

## 📂 Persisting PDFs (Optional)

Edit **`docker-compose.yml`** to map local folders:

```yaml
services:
  backend:
    volumes:
      - ./input:/app/input      # drop PDFs here
      - ./output:/app/output    # translated files appear here
```

---

## 🐳 Docker Cheat‑Sheet

| Action | Command |
|--------|---------|
| Rebuild without cache | `docker compose build --no-cache` |
| View logs | `docker compose logs -f backend` |
| Enter container shell | `docker compose exec backend bash` |
| Stop containers | `docker compose down` |

---

## 🧩 Deployment Notes

* **Reverse proxy** – point Nginx / Caddy / Traefik at port 8000 (backend) and 80 (frontend container).  
* **CI/CD** – push images:

  ```bash
  docker tag translate-pdf-backend yourhub/translate-pdf:backend
  docker tag translate-pdf-frontend yourhub/translate-pdf:frontend
  docker push yourhub/translate-pdf:*        # push both tags
  ```

* **Scaling** – the backend is stateless; run multiple replicas behind a load balancer.

---

## 🆘 Troubleshooting

| Symptom | Fix |
|---------|-----|
| **“Cannot connect to Docker daemon”** | Start Docker Desktop OR add user to `docker` group (`sudo usermod -aG docker $USER`). |
| **Port 8000/5173 in use** | Change the left side of `ports:` in `docker-compose.yml`. |
| **Build fails compiling Ghostscript** | Give Docker more CPU/RAM (Settings → Resources). |
| **Frontend shows CORS error** | Backend’s `.env` → set `FRONTEND_ORIGIN` to the URL you open in the browser. |

---

## 📜 License

MIT © 2025 Bao Dinh & Contributors
