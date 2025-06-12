**Star ⭐ this repository if VerbaDoc helps you translate documents efficiently!**

# 📄 VerbaDoc - AI-Powered PDF Translation with Layout Preservation

**Transform multilingual PDFs while preserving their exact layout, formatting, and mathematical expressions.**

VerbaDoc is a full-stack web application that intelligently detects document layout, extracts text and formulas, translates content using Google Gemini AI, and reconstructs PDFs with selectable text—all while maintaining the original visual structure.

---

## 🌟 Key Features

- **🎯 Layout-Aware Translation**: Preserves tables, paragraphs, titles, and mathematical formulas
- **🧠 AI-Powered OCR**: Uses Google Gemini 2.0 Flash for accurate text extraction and LaTeX conversion
- **📐 Mathematical Expression Support**: Handles complex formulas with XeLaTeX rendering
- **🔄 Side-by-Side Viewer**: Compare original and translated PDFs in real-time
- **⚡ High Performance**: Multi-threaded processing with API key load balancing
- **🐳 Docker Ready**: One-command deployment with isolated environments
- **🌐 Multi-Language Support**: Vietnamese, Chinese, Japanese, Korean, Arabic, and more

---

## 🏗️ Architecture Overview

| Component     | Technology Stack                                                                         |
| ------------- | ---------------------------------------------------------------------------------------- |
| **Frontend**  | React 18 + TypeScript + Vite + Bootstrap 5 + React Router + PDF.js viewer                |
| **Backend**   | Python 3.11 + FastAPI + PyMuPDF + DocLayout-YOLO + Google Gemini API + XeLaTeX + Poppler |
| **AI Models** | DocLayout-YOLO (layout detection) + Google Gemini 2.0 Flash (OCR & translation)          |

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Client  │───▶│  FastAPI Server  │───▶│  Gemini AI API  │
│                 │    │                  │    │                 │
│ • File Upload   │    │ • Layout Detection│    │ • Text Extract  │
│ • PDF Viewer    │    │ • OCR Processing  │    │ • Translation   │
│ • Side-by-side  │    │ • LaTeX Rendering │    │ • Math OCR      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

---

## 🗂️ Repository Structure

```
translate-pdf-app/
├── translate-pdf-app_BACKEND/          # Python FastAPI server
│   ├── core/                          # Core processing modules
│   │   ├── api_manager.py             # Multi-API key management
│   │   ├── detect_layout.py           # DocLayout-YOLO integration
│   │   ├── extract_info.py            # OCR & content extraction
│   │   ├── translate_text.py          # Gemini translation
│   │   ├── render_latex.py            # LaTeX PDF generation
│   │   └── pdf_utils.py               # PDF manipulation utilities
│   ├── pipeline.py                    # Main processing pipeline
│   ├── main.py                        # FastAPI application
│   ├── requirements.txt               # Python dependencies
│   └── Dockerfile                     # Backend container config
├── translate-pdf-app_FRONTEND/         # React TypeScript client
│   ├── src/
│   │   ├── components/                # Reusable UI components
│   │   ├── pages/                     # Application pages
│   │   │   ├── LandingPage.tsx        # Home page with features
│   │   │   ├── UploadPage.tsx         # PDF upload interface
│   │   │   └── ViewPage.tsx           # Side-by-side PDF viewer
│   │   └── main.tsx                   # Application entry point
│   ├── package.json                   # Node.js dependencies
│   └── Dockerfile                     # Frontend container config
├── docker-compose.yml                 # Multi-service orchestration
└── README.md                          # This comprehensive guide
```

---

## 🚀 Quick Start (Recommended)

### Prerequisites

- **Docker Desktop 24.0+** (includes Docker Compose v2)
- **Git** for cloning the repository
- **Google Gemini API Keys** (get from [Google AI Studio](https://aistudio.google.com/))

### 1-Command Launch

```bash
git clone <your-repository-url>
cd translate-pdf-app
cp translate-pdf-app_BACKEND/.env.example translate-pdf-app_BACKEND/.env
# Edit .env file with your API keys (see configuration section below)
docker compose up --build
```

🎉 **That's it!** Your application will be available at:

| Service  | URL                        | Purpose                           |
| -------- | -------------------------- | --------------------------------- |
| Frontend | http://localhost:5173      | Upload PDFs and view translations |
| Backend  | http://localhost:8000      | API endpoints                     |
| API Docs | http://localhost:8000/docs | Interactive Swagger documentation |

> **⏱️ First Launch**: Initial build takes ~10-15 minutes due to TeX packages and AI model downloads (~1GB)

---

## ⚙️ Configuration Guide

### Environment Variables Explained

#### Backend Configuration (`translate-pdf-app_BACKEND/.env`)

```env
# CORS Configuration - Critical for frontend-backend communication
FRONTEND_ORIGIN=http://localhost:5173              # Development frontend URL
FRONTEND_HOST=https://your-production-domain.com   # Production frontend URL

# File Storage
UPLOAD_FOLDER=storage                               # Local storage directory name

# Google Gemini API Keys - Multiple keys for load balancing and rate limit management
GEMINI_API_KEY_0=your_first_api_key_here           # Primary API key
GEMINI_API_KEY_1=your_second_api_key_here          # Secondary API key (optional)
GEMINI_API_KEY_2=your_third_api_key_here           # Tertiary API key (optional)
```

#### Variable Details

| Variable           | Required | Purpose                 | Example                    |
| ------------------ | -------- | ----------------------- | -------------------------- |
| `FRONTEND_ORIGIN`  | ✅ Yes   | Development CORS origin | `http://localhost:5173`    |
| `FRONTEND_HOST`    | ✅ Yes   | Production CORS origin  | `https://myapp.vercel.app` |
| `UPLOAD_FOLDER`    | ❌ No    | Storage directory name  | `storage` (default)        |
| `GEMINI_API_KEY_0` | ✅ Yes   | Primary Gemini API key  | `AIzaSy...`                |
| `GEMINI_API_KEY_1` | ❌ No    | Load balancing key #2   | `AIzaSy...`                |
| `GEMINI_API_KEY_2` | ❌ No    | Load balancing key #3   | `AIzaSy...`                |

> **🔑 Getting API Keys**: Visit [Google AI Studio](https://aistudio.google.com/) → Create API Key → Copy key value

#### Frontend Configuration (Optional)

Create `translate-pdf-app_FRONTEND/.env` for custom backend URL:

```env
VITE_BACKEND_URL=http://localhost:8000    # Backend API base URL
```

---

## 🛠️ Development Setup

### Backend Development (Without Docker)

#### System Dependencies (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y \
    texlive-xetex texlive-latex-base texlive-extra-utils \
    poppler-utils libgl1 libglib2.0-0 \
    build-essential wget curl git
```

#### Python Environment

```bash
cd translate-pdf-app_BACKEND

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Pre-download AI Models

```bash
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='juliozhao/DocLayout-YOLO-DocStructBench',
    filename='doclayout_yolo_docstructbench_imgsz1024.pt'
)
print('✅ DocLayout-YOLO model downloaded successfully')
"
```

#### Run Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd translate-pdf-app_FRONTEND

# Install dependencies
npm install
# or
pnpm install
# or
yarn install

# Start development server with hot reload
npm run dev
```

**Development URLs:**

- Frontend: http://localhost:5173 (auto-reload on changes)
- Backend: http://localhost:8000 (auto-reload on changes)

---

## 🧩 Production Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker compose -f docker-compose.yml up -d

# Check service health
docker compose ps
docker compose logs -f backend
```

### Individual Service Deployment

#### Backend Only

```bash
cd translate-pdf-app_BACKEND
docker build -t verbaDoc-backend:latest .
docker run -d \
    --name verbaDoc-backend \
    -p 8000:8000 \
    --env-file .env \
    verbaDoc-backend:latest
```

#### Frontend Only

```bash
cd translate-pdf-app_FRONTEND
docker build -t verbaDoc-frontend:latest .
docker run -d \
    --name verbaDoc-frontend \
    -p 80:80 \
    verbaDoc-frontend:latest
```

### Cloud Platform Deployment

#### Render.com

1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy backend as Web Service (port 8000)
4. Deploy frontend as Static Site

#### Vercel + Railway

1. Deploy frontend to Vercel
2. Deploy backend to Railway
3. Update CORS origins in environment variables

---

## 📊 Processing Pipeline Details

### 1. Layout Detection

- **Input**: PDF pages converted to high-resolution images (300 DPI)
- **Model**: DocLayout-YOLO trained on DocStructBench dataset
- **Output**: Bounding boxes for paragraphs, titles, tables, formulas, figures

### 2. Content Extraction

- **Text Regions**: Direct text extraction using PyMuPDF
- **Complex Regions**: Google Gemini 2.0 Flash OCR with LaTeX conversion
- **Mathematical Formulas**: Preserved as LaTeX markup

### 3. Translation

- **Engine**: Google Gemini 2.0 Flash with specialized prompts
- **Features**: Context-aware translation, mathematical expression preservation
- **Rate Limiting**: Intelligent API key rotation and request queuing

### 4. Reconstruction

- **Text**: Direct insertion with font matching
- **Formulas**: XeLaTeX compilation and PDF overlay
- **Layout**: Exact coordinate-based positioning

---

## 🔧 Troubleshooting

### Common Issues

| Problem                | Symptoms                          | Solutions                                                                                                      |
| ---------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **CORS Errors**        | Frontend can't reach backend      | • Check `FRONTEND_ORIGIN` in `.env`<br>• Verify URLs match exactly<br>• Restart backend service                |
| **API Key Issues**     | "No API key available" errors     | • Verify Gemini API keys are valid<br>• Check key quotas in Google Cloud<br>• Add more keys for load balancing |
| **Build Failures**     | Docker build timeouts             | • Increase Docker memory to 4GB+<br>• Use `--no-cache` flag<br>• Check internet connection                     |
| **Port Conflicts**     | "Port already in use"             | • Change ports in `docker-compose.yml`<br>• Kill existing processes<br>• Use different port mapping            |
| **Translation Errors** | Incomplete or failed translations | • Check API key quotas<br>• Verify PDF file integrity<br>• Check backend logs                                  |

### Debug Commands

```bash
# Check container status
docker compose ps

# View real-time logs
docker compose logs -f backend
docker compose logs -f frontend

# Enter container for debugging
docker compose exec backend bash
docker compose exec frontend sh

# Check API health
curl http://localhost:8000/health

# Test file upload
curl -X POST -F "file=@test.pdf" http://localhost:8000/upload-pdf/
```

### Performance Optimization

#### For High-Volume Usage

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
    environment:
      - GEMINI_API_KEY_0=key1
      - GEMINI_API_KEY_1=key2
      - GEMINI_API_KEY_2=key3
      # Add more API keys for better rate limiting
```

#### Memory Usage

- **Minimum**: 4GB RAM for basic operation
- **Recommended**: 8GB RAM for production
- **Storage**: 2GB for AI models + user files

---

## 🧪 Testing

### Manual Testing

1. Upload a multi-language PDF with tables and formulas
2. Verify layout detection visualization
3. Check translation accuracy
4. Confirm PDF output maintains formatting

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Upload test
curl -X POST \
  -F "file=@sample.pdf" \
  http://localhost:8000/upload-pdf/ \
  -H "Content-Type: multipart/form-data"
```

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

### Development Guidelines

- Follow TypeScript best practices for frontend
- Use Python type hints for backend
- Add comprehensive error handling
- Update documentation for new features


---

## 🙏 Acknowledgments

- **DocLayout-YOLO**: Document layout detection model
- **Google Gemini**: AI-powered OCR and translation
- **PyMuPDF**: PDF processing and manipulation
- **React & FastAPI**: Modern web framework foundation

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: This README + inline code comments
