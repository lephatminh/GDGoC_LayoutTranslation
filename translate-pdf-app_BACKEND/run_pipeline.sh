#!/usr/bin/env bash
set -euo pipefail

# $1 == full path to input PDF, e.g. …/input/{fileId}/{fileId}.pdf
file_id=$(basename "$(dirname "$1")")

echo "1) Running PDFPigLayoutDetection for ${file_id}..."
pushd PDFPigLayoutDetection >/dev/null
if ! dotnet run --project PDFPigLayoutDetection.csproj -- "$file_id"; then
  echo "[ERROR] PDFPigLayoutDetection failed" >&2
  exit 1
fi
popd >/dev/null

echo "2) Running Python translation & visualization..."
if ! python main_pipe.py --input "$1" --output "$2"; then
  echo "[ERROR] Python pipeline failed" >&2
  exit 2
fi

echo "All done!"