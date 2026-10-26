import fitz  # PyMuPDF

def extract_pdf_text(path):
    parts = []
    with fitz.open(path) as document:
        for page in document:
            parts.append(page.get_text("text"))
    return "\n".join(parts).strip()
