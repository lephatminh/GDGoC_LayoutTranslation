from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4
import shutil, logging, os
from dotenv import load_dotenv

# Load env vars
load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5174")
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "https://fe-08u9.onrender.com")

print(f"Loaded FRONTEND_ORIGIN: {FRONTEND_ORIGIN}")
print(f"Loaded FRONTEND_HOST: {FRONTEND_HOST}")

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "storage" / "input"
OUTPUT_DIR = BASE_DIR / "storage" / "output"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(default_response_class=ORJSONResponse)

# CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		FRONTEND_ORIGIN,
		FRONTEND_HOST,
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


# Mount base directories (not subfolder)
app.mount("/files/input", StaticFiles(directory=INPUT_DIR), name="input")
app.mount("/files/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# Response model
class UploadResponse(BaseModel):
	original: str
	translated: str

@app.post("/upload-pdf/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
	if not file.filename.endswith(".pdf") or file.content_type != "application/pdf":
		logger.warning(f"Blocked non-PDF upload: {file.filename}")
		raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

	# Extract base filename without .pdf
	filename_stem = Path(file.filename).stem
	input_folder = INPUT_DIR / filename_stem
	output_folder = OUTPUT_DIR / filename_stem
	input_folder.mkdir(parents=True, exist_ok=True)
	output_folder.mkdir(parents=True, exist_ok=True)

	# Create full file paths
	original_path = input_folder / file.filename
	translated_path = output_folder / f"{filename_stem}_translated.pdf"

	# Save original
	with original_path.open("wb") as buffer:
		shutil.copyfileobj(file.file, buffer)

	# 🧠 Placeholder logic for translation
	shutil.copy(original_path, translated_path)

	logger.info(f"Stored original: {original_path}")
	logger.info(f"Stored translated: {translated_path}")

	return UploadResponse(
		original=f"/files/input/{filename_stem}/{file.filename}",
		translated=f"/files/output/{filename_stem}/{filename_stem}_translated.pdf"
	)
