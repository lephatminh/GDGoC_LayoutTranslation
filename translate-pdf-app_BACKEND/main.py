from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil

app = FastAPI()

# ✅ Allow requests from your frontend (Vite/React at port 5173)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173"],  # your React frontend origin
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

UPLOAD_DIR = Path("uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
	# Save the uploaded file
	original_path = UPLOAD_DIR / file.filename
	with original_path.open("wb") as buffer:
		shutil.copyfileobj(file.file, buffer)

	# Simulate translated version
	translated_filename = f"translated_{file.filename}"
	translated_path = UPLOAD_DIR / translated_filename
	shutil.copy(original_path, translated_path)

	# Return the translated file
	return FileResponse(
		path=translated_path,
		media_type="application/pdf",
		filename=translated_filename
	)
