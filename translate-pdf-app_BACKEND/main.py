# ✅ Imports
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4
import shutil, logging, os
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "https://fe-08u9.onrender.com")
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", "storage"))

# ✅ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"FRONTEND_ORIGIN loaded: {FRONTEND_ORIGIN}")
logger.info(f"FRONTEND_HOST loaded: {FRONTEND_HOST}")
# ✅ FastAPI App (using ORJSON)
app = FastAPI(default_response_class=ORJSONResponse)

# ✅ CORS config
app.add_middleware(
	CORSMiddleware,
	allow_origins=[FRONTEND_ORIGIN,FRONTEND_HOST],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# ✅ Folder setup
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR / UPLOAD_FOLDER
ORIGINAL_DIR = UPLOAD_ROOT / "originals"
TRANSLATED_DIR = UPLOAD_ROOT / "translateds"
for path in [ORIGINAL_DIR, TRANSLATED_DIR]:
	path.mkdir(parents=True, exist_ok=True)

# ✅ Pydantic V2 response model
class UploadResponse(BaseModel):
	original: str
	translated: str

# ✅ Route using Pydantic model
@app.post("/upload-pdf/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
	if not file.filename.endswith(".pdf") or file.content_type != "application/pdf":
		logger.warning(f"Blocked non-PDF upload: {file.filename}")
		raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

	uid = uuid4().hex
	original_filename = f"{uid}_{file.filename}"
	translated_filename = f"translated_{uid}_{file.filename}"
	original_path = ORIGINAL_DIR / original_filename
	translated_path = TRANSLATED_DIR / translated_filename

	with original_path.open("wb") as buffer:
		shutil.copyfileobj(file.file, buffer)

	shutil.copy(original_path, translated_path)
	logger.info(f"Stored: {original_filename}, Translated: {translated_filename}")

	return UploadResponse(
		original=f"/files/originals/{original_filename}",
		translated=f"/files/translateds/{translated_filename}"
	)

# ✅ Static file routes
app.mount("/files/originals", StaticFiles(directory=ORIGINAL_DIR), name="originals")
app.mount("/files/translateds", StaticFiles(directory=TRANSLATED_DIR), name="translateds")
