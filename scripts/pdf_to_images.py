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

def convert_pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 150):
    """
    Converts a PDF file to a sequence of images (one per page).
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(pdf_file)
        print(f"Opened PDF: {pdf_path} ({len(doc)} pages)")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            
            output_file = out_dir / f"{pdf_file.stem}_page_{page_num + 1:03d}.png"
            pix.save(str(output_file))
            print(f"Saved: {output_file}")

        print(f"Conversion complete. Images saved to {out_dir}")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    default_base = get_default_base_dir()
    parser = argparse.ArgumentParser(description="Convert PDF to images.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("output_dir", nargs="?", default=None, help=f"Directory to save the generated images (defaults to <base_dir>\\<note_name>\\slides\\)")
    parser.add_argument("--base-dir", "-b", default=default_base, help=f"Base folder for summaries (default: {default_base})")
    parser.add_argument("--note-name", "-n", default=None, help="Note / run name (defaults to PDF stem)")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for the output images")

    args = parser.parse_args()
    
    if args.output_dir:
        target_out_dir = args.output_dir
    else:
        note_name = args.note_name if args.note_name else Path(args.pdf_path).stem
        target_out_dir = os.path.join(args.base_dir, note_name, "slides")

    convert_pdf_to_images(args.pdf_path, target_out_dir, args.dpi)
