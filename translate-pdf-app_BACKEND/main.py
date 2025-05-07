from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid

app = FastAPI()

# CORS setup to allow frontend to communicate with backend
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Define permanent folders
BASE_DIR = Path("./mnt/data/server_files")
ORIGINAL_DIR = BASE_DIR / "originals"
TRANSLATED_DIR = BASE_DIR / "translateds"

# Ensure folders exist
ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
TRANSLATED_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
	# Generate unique name to avoid conflict
	uid = uuid.uuid4().hex
	original_filename = f"{uid}_{file.filename}"
	translated_filename = f"translated_{uid}_{file.filename}"

	# Save original
	original_path = ORIGINAL_DIR / original_filename
	with original_path.open("wb") as buffer:
		shutil.copyfileobj(file.file, buffer)

	# Simulate translation (copy file)
	translated_path = TRANSLATED_DIR / translated_filename
	shutil.copy(original_path, translated_path)

	# Return static-accessible paths to frontend
	return JSONResponse(content={
		"original": f"/files/originals/{original_filename}",
		"translated": f"/files/translateds/{translated_filename}"
	})

# Serve static files for original and translated PDFs
from fastapi.staticfiles import StaticFiles
app.mount("/files/originals", StaticFiles(directory=ORIGINAL_DIR), name="originals")
app.mount("/files/translateds", StaticFiles(directory=TRANSLATED_DIR), name="translateds")
