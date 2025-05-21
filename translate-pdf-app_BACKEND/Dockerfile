# ─── Stage 1: Build PDFPig (.NET SDK) ───────────────────────
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS pdfpig-build
WORKDIR /src/PDFPigLayoutDetection

# Copy project files and DLLs
COPY PDFPigLayoutDetection/*.csproj ./
COPY bin ../bin
COPY PDFPigLayoutDetection/. ./

# Restore NuGet dependencies
RUN dotnet restore

# ─── Stage 2: Final Python + OCR + .NET SDK Image ───────────
FROM python:3.11-slim AS final
WORKDIR /app

# Install OS dependencies and .NET SDK
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        gnupg \
        curl \
        wget \
        bash \
		gcc \
        make \
        build-essential \
        software-properties-common \
        tesseract-ocr \
        poppler-utils \
        fontconfig \
        libglib2.0-0 \
        libgl1 && \
    # Add Microsoft feed for .NET SDK
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg && \
    echo "deb [arch=amd64] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/microsoft.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends dotnet-sdk-6.0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Ghostscript 10.05.1
RUN wget -q https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10051/ghostscript-10.05.1.tar.gz && \
    tar -xzf ghostscript-10.05.1.tar.gz && \
    cd ghostscript-10.05.1 && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ghostscript-10.05.1 ghostscript-10.05.1.tar.gz

# Download Tesseract language data
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata && \
    cd /usr/share/tesseract-ocr/4.00/tessdata && \
    for lang in rus spa deu fra kor jpn vie eng chi_sim chi_tra chi_tra_vert chi_sim_vert; do \
        wget -q https://github.com/tesseract-ocr/tessdata/raw/main/${lang}.traineddata; \
    done

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Copy .NET build source and binaries
COPY --from=pdfpig-build /src /src

# Make shell script executable
RUN chmod +x run_pipeline.sh

# Create directories and set proper permissions
RUN mkdir -p /app/input /app/output && \
    chmod 777 /app/input /app/output

# Entrypoint
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
