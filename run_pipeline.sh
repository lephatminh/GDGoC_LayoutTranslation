#!/bin/bash
set -euo pipefail

echo "1) Running PDFPigLayoutDetection..."
pushd PDFPigLayoutDetection
if ! dotnet run; then
  echo "[ERROR] PDFPigLayoutDetection failed" >&2
  exit 1
fi
popd

echo "2) Running Python translation & visualization..."
if ! python main.py; then
  echo "[ERROR] Python pipeline failed" >&2
  exit 2
fi

echo "All done!"