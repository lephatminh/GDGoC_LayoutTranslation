# ─── Stage 1: Build PDFPigLayoutDetection (.NET 6 SDK) ──────
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS pdfpig-build
WORKDIR /src/PDFPigLayoutDetection
COPY PDFPigLayoutDetection/*.csproj ./
RUN dotnet restore
COPY PDFPigLayoutDetection/. ./
RUN dotnet publish -c Release -o /app/pdfpig

# ─── Stage 2: Install Python deps & copy pipeline ────────────
FROM python:3.11-slim AS py-build
WORKDIR /app
COPY translate-pdf-app_BACKEND/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY translate-pdf-app_BACKEND/main.py \
     translate-pdf-app_BACKEND/run_pipeline.sh \
     translate-pdf-app_BACKEND/config/ \
     translate-pdf-app_BACKEND/core/ ./
RUN chmod +x run_pipeline.sh

# ─── Final image: .NET Runtime + Python ────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:6.0 AS final
WORKDIR /app

# bring in the published PDFPig detector
COPY --from=pdfpig-build /app/pdfpig ./PDFPigLayoutDetection

# bring in the Python pipeline
COPY --from=py-build /app ./

# mount input/output so your FastAPI can read/write
VOLUME ["/app/input","/app/output"]
EXPOSE 8000

# start your FastAPI backend
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]