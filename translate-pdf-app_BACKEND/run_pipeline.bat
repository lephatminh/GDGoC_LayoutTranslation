:: filepath: translate-pdf-app_BACKEND\run_pipeline.bat
@echo off
chcp 65001 >nul

REM %1 = full path to input PDF, %2 = output directory
if "%~1"=="" (
  echo Usage: %~nx0 "input_pdf" "output_dir"
  exit /B 1
)
if "%~2"=="" (
  echo Usage: %~nx0 "input_pdf" "output_dir"
  exit /B 1
)

REM extract file_id from parent folder name of the PDF
set "inputPath=%~1"
for %%F in ("%~1") do set "fileId=%%~nxF"

echo 1) Running PDFPigLayoutDetection for %fileId%...
pushd "%~dp0%\PDFPigLayoutDetection"
dotnet run --project PDFPigLayoutDetection.csproj -- "%fileId%"
if errorlevel 1 (
  echo [ERROR] PDFPigLayoutDetection failed
  popd
  exit /B 1
)
popd

echo 2) Running Python translation & visualization...
pushd "%~dp0%"
python main_pipe.py --input "%inputPath%" --output "%~2"
if errorlevel 1 (
  echo [ERROR] Python pipeline failed
  popd
  exit /B 2
)
popd

echo All done!
exit /B 0