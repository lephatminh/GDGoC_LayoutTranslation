import fitz
from pathlib import Path

def split_pdf_to_pages(input_pdf_path: Path, output_root: Path) -> None:
    file_id = input_pdf_path.stem
    target_dir = output_root / file_id
    target_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(input_pdf_path))
    for i in range(doc.page_count):
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=i, to_page=i)
        out_pdf = target_dir / f"{file_id}_page_{i+1}.pdf"
        new_doc.save(str(out_pdf))
        new_doc.close()
    doc.close()