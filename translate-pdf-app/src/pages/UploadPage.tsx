import React, { useRef, useState } from "react";
import { FaFilePdf, FaUpload, FaTrashAlt } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

const UploadPage: React.FC = () => {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const navigate = useNavigate();

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.type === "application/pdf") {
      setFile(dropped);
    } else {
      alert("Only PDF files are allowed.");
    }
  };

  const handleBrowse = () => {
    fileRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
    } else {
      alert("Only PDF files are allowed.");
    }
  };

  const handleRemove = () => {
    setFile(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const backendUrl = "http://localhost:8000";
      console.log("📡 Uploading to backend:", `${backendUrl}/upload-pdf/`);

      const response = await fetch(`${backendUrl}/upload-pdf/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const { original, translated } = await response.json();

      console.log("✅ Response received:", { original, translated });

      sessionStorage.setItem("originalUrl", `${backendUrl}${original}`);
      sessionStorage.setItem("translatedUrl", `${backendUrl}${translated}`);

      navigate("/viewer");
    } catch (error) {
      alert("Upload failed. Check backend connection.");
      console.error("❌ Upload error:", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      className="d-flex justify-content-center align-items-center vh-100"
      style={{ backgroundColor: "#1a1d23" }}
    >
      <div
        className="bg-white p-5 rounded shadow text-dark"
        style={{ width: "600px", border: "3px dashed red", cursor: "pointer" }}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={handleBrowse}
      >
        <h4 className="fw-bold">Upload PDF</h4>
        <p className="text-muted mb-4">
          Drag and drop a PDF here, or click this box to select a PDF to upload.
        </p>
        {file && (
          <div className="d-flex justify-content-between align-items-start">
            <div style={{ maxWidth: "90%", wordBreak: "break-word" }}>
              <FaFilePdf className="me-2 text-danger" />
              <p className="fw-bold text-break mb-1">{file.name}</p>
              <small className="text-muted">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </small>
            </div>
            <button
              className="btn btn-outline-danger btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                handleRemove();
              }}
            >
              <FaTrashAlt />
            </button>
          </div>
        )}
        <div className="mt-4 d-flex gap-3">
          <button
            className="btn btn-primary"
            onClick={(e) => {
              e.stopPropagation();
              handleBrowse();
            }}
          >
            Select PDF
          </button>
          <button
            className="btn btn-danger"
            onClick={(e) => {
              e.stopPropagation();
              handleUpload();
            }}
            disabled={!file || isUploading}
          >
            <FaUpload className="me-2" />
            {isUploading ? "Uploading..." : "Upload"}
          </button>
        </div>
        <input
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          ref={fileRef}
          onChange={handleFileChange}
        />
      </div>
    </div>
  );
};

export default UploadPage;
