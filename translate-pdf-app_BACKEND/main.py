from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
import shutil, logging, os, subprocess
from pipeline import run_pipeline
import sys



# Load env vars
load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "https://fe-08u9.onrender.com")

print(f"Loaded FRONTEND_ORIGIN: {FRONTEND_ORIGIN}")
print(f"Loaded FRONTEND_HOST: {FRONTEND_HOST}")

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

# ✅ Folder setup
BASE_DIR = Path(__file__).resolve().parent
ORIGINAL_DIR = BASE_DIR / "input"
TRANSLATED_DIR = BASE_DIR / "output"

# Mount base directories (not subfolder)
app.mount("/files/input", StaticFiles(directory=ORIGINAL_DIR), name="input")
app.mount("/files/output", StaticFiles(directory=TRANSLATED_DIR), name="output")

# Health check
@app.get("/health")
def health():
	return {"status": "ok"}

# Response model
class UploadResponse(BaseModel):
	original: str
	translated: str

@app.post("/upload-pdf/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
	if not file.filename.endswith(".pdf") or file.content_type != "application/pdf":
		logger.warning(f"Blocked non-PDF upload: {file.filename}")
		raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

	filename_stem = Path(file.filename).stem
	input_folder = ORIGINAL_DIR / filename_stem
	output_folder = TRANSLATED_DIR
	original_path = input_folder / file.filename
	translated_path = output_folder

	for path in [input_folder, output_folder]:
		path.mkdir(parents=True, exist_ok=True)

	with original_path.open("wb") as buffer:
		shutil.copyfileobj(file.file, buffer)


	# NOTE: apply run_pipeline.sh here to get translated PDF 
	# shutil.copy(original_path, translated_path)
	if os.name == "nt":
		# Windows
		runner = [sys.executable, str(BASE_DIR / "pipeline.py"), str(original_path), str(translated_path)]

	else:
		# Unix-like (Linux, macOS)
		runner = [sys.executable, str(BASE_DIR / "pipeline.py"), str(original_path), str(translated_path)]

	# subprocess.run(
	# 	runner,
	# 	cwd=str(BASE_DIR),
	# 	check=True
	# )

	run_pipeline(original_path, output_folder)

	logger.info(f"Stored original: {original_path}")
	logger.info(f"Stored translated: {translated_path}")

	# NOTE: this is a temporary solution
	translated_path = shutil.copy(original_path, translated_path)
	
	return UploadResponse(
		original=f"/files/input/{filename_stem}/{file.filename}",
		translated=f"/files/output/{filename_stem}/{file.filename}"
	)