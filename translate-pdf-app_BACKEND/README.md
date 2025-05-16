# Multi-Lingual-Document-Translation

## Set up:
1. Download and Install GhostScript, then Add to PATH
- Link: https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10030/gs10030w64.exe
- After installation, add the path to the bin folder to your system PATH environment variable. (Example: C:\Program Files\gs\gs10.01.2\bin)


2. Download and Install Tesseract OCR, then Add to PATH
- Link: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe
- Add the installation folder (e.g., D:\APCS\Tesseract-OCR\) to your system PATH environment variable.
- Install it in a custom folder (preferably not on drive C, use drive D instead).


3. Download Language Data Files into Tesseract-OCR\tessdata
- rus.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/rus.traineddata
- spa.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata
- deu.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/deu.traineddata
- fra.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata
- kor.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata
- jpn.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata
- vie.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/vie.traineddata
- eng.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
- chi_sim.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim.traineddata
- chi_tra.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/chi_tra.traineddata
- chi_tra_vert.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/chi_tra_vert.traineddata
- chi_sim_vert.traineddata: https://github.com/tesseract-ocr/tessdata/raw/main/chi_sim_vert.traineddata


## Non Deeplearning solution

### Steps to Translate a Document

Follow these steps to translate a PDF document using the script:

---

#### 1. Prepare Your PDF

- Place the PDF file you want to translate in the same directory as the script, or provide the full path to the PDF when running the script.
- Ensure the PDF file is named appropriately, as the script uses the file name (without the `.pdf` extension) as the `file_id`.

---

#### 2. Run the Translation Function

- Open a Python environment (e.g., a terminal, IDE, or Jupyter Notebook) and execute the `document_translation` function with the appropriate parameters:

  - `file_id`: The name of your PDF file without the `.pdf` extension.
  - `rescale`: An optional boolean parameter. Set to `True` if you want the output PDF to be rescaled to the original dimensions after translation; otherwise, set to `False` (default).

- Example command:

  ```python
  document_translation('your_file_id', rescale=True)

- Replace `your_file_id` with the actual name of your PDF (e.g., `example_document` if your file is `example_document.pdf`).

---

#### 3. Wait for Processing

- The script performs the following operations automatically:

  - ***Temporary Folder Creation***: Creates a temporary working folder named after the ```file_id``` (e.g., ```./your_file_id/```).

  - ***PDF Scaling***: Scales the PDF to a standard size of 1025x1025 pixels for consistent processing.

  - ***OCR Application***: Applies OCR using ```ocrmypdf``` to recognize text, supporting multiple languages (e.g., Chinese, Vietnamese, English, Japanese, Korean, French, German, Spanish, Russian).

  - ***Text Extraction and Translation***: Extracts text and formatting information using ```PyMuPDF```, translates the text to Vietnamese using ```GoogleTranslator```, and saves the data in a CSV file (e.g., ```./your_file_id/your_file_id.csv```).

  - ***Text Replacement***: Opens the OCR-processed PDF, covers the original text with white rectangles, and inserts the translated text using the ```Roboto.ttf``` font.

  - ***Output Saving***: Saves the translated PDF with the prefix ```translation_``` (e.g., ```translation_your_file_id.pdf```) in the same directory as the original PDF.

- This process may take some time depending on the size of the PDF and the amount of text to translate.

---

***Result***:

|Original Document|Translation Document|
|-|-|
|***Sample 1***: ![Alt text](imgs/Sample_1.jpg)|***Translation Sample 1***: ![Alt text](imgs/translation_Sample_1.jpg)|
|***Sample 2***: ![Alt text](imgs/Sample_2.jpg)|***Translation Sample 2***: ![Alt text](imgs/translation_Sample_2.jpg)|
|***Sample 3***: ![Alt text](imgs/Sample_3.jpg)|***Translation Sample 3***: ![Alt text](imgs/translation_Sample_3.jpg)|

- Currently, we detect the box and the text inside these box, then do the translate, insert the white background rectangle to that respective box and insert the translation text. Thus, we are not fully kept the format but try to remain the format as much as possible.

- The translation result is not as good as expect as we break the paragraph into many many lines and let's the GoogleTranslator to do the translate on these lines thus we may lost the paragraph context.

- The font we use default font Roboto as some of the font used in the pdf not actually good with Vietnamese (e.g the CMR12 not fully supported the Vietnamese character).

- Some of the math, image notation, reference (in paper or documentation) that should be kept reamin but current model do the translate on them (e.g 'α' is translated to 'một').

***Further work***:

- Use deeplearning to detect the paragraph instead of line by line detecting.

- Detect what should (e.g plain text, paragraph, etc) and should not (e.g math, image notation, etc) translate.
