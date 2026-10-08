import os
import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is not installed. Please install it using: pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)

try:
    from .base_dir_helper import get_default_base_dir
except (ImportError, ValueError):
    from base_dir_helper import get_default_base_dir

DEFAULT_BASE_DIR = get_default_base_dir()

def triage_pdf(pdf_path: str):
    """
    Inspects a PDF and determines its document type (slides, academic_text, complex_layout)
    and recommends the best extraction engine / pipeline.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    try:
        doc = fitz.open(pdf_file)
        page_count = len(doc)
        total_chars = 0
        landscape_pages = 0

        for page_num in range(page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            total_chars += len(text.strip())
            
            rect = page.rect
            if rect.width > rect.height:
                landscape_pages += 1

        avg_chars_per_page = total_chars / page_count if page_count > 0 else 0
        is_landscape_dominant = landscape_pages > (page_count / 2)

        print(f"=== PDF Triage Report: {pdf_file.name} ===")
        print(f"Total Pages: {page_count}")
        print(f"Average Characters / Page: {avg_chars_per_page:.1f}")
        print(f"Landscape Pages: {landscape_pages}/{page_count}")

        # Triage logic
        if is_landscape_dominant or avg_chars_per_page < 200:
            doc_type = "slides_or_flowcharts"
            recommended_engine = "slides"
            reason = "Document is landscape-dominant and/or has low text density per page. Recommended workflow: Image extraction (`pdf_to_images.py` -> `slides/`) for vision-based synthesis."
        elif avg_chars_per_page > 1500:
            doc_type = "academic_or_text_heavy"
            recommended_engine = "pymupdf4llm"
            reason = "Document is text-dense. Recommended engine: `pymupdf4llm` (fast, lightweight default markdown extraction)."
        else:
            doc_type = "complex_mixed_or_math"
            recommended_engine = "docling"
            reason = "Document has mixed layout / potential math or tables. Recommended engine: `docling` (high-fidelity LaTeX / math / table engine via `--engine docling`)."

        print(f"\nDetected Document Type: {doc_type}")
        print(f"Recommended Engine / Workflow: {recommended_engine}")
        print(f"Reasoning: {reason}")
        print("===========================================")

        return {
            "file": str(pdf_file),
            "page_count": page_count,
            "avg_chars_per_page": avg_chars_per_page,
            "is_landscape": is_landscape_dominant,
            "doc_type": doc_type,
            "recommended_engine": recommended_engine,
            "reason": reason
        }

    except Exception as e:
        print(f"Error during PDF triage: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    default_base = get_default_base_dir()
    parser = argparse.ArgumentParser(description="Triage a PDF to recommend the optimal extraction engine.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")

    args = parser.parse_args()
    triage_pdf(args.pdf_path)
