import os
import argparse
import sys
from pathlib import Path

try:
    from .base_dir_helper import get_default_base_dir
except (ImportError, ValueError):
    from base_dir_helper import get_default_base_dir

DEFAULT_BASE_DIR = get_default_base_dir()

def convert_pdf_to_markdown(pdf_path: str, output_dir: str, engine: str = "pymupdf4llm", note_name: str = None):
    """
    Converts a PDF file to markdown using either pymupdf4llm or docling.
    Saves the output as <note_name>_source.md inside output_dir.
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    n_name = note_name if note_name else pdf_file.stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_file = out_dir / f"{n_name}_source.md"

    print(f"Converting PDF '{pdf_file.name}' to markdown using engine: '{engine}'...")

    try:
        if engine == "pymupdf4llm":
            try:
                import pymupdf4llm
            except ImportError:
                print("Error: pymupdf4llm is not installed. Please install it using: pip install pymupdf4llm", file=sys.stderr)
                sys.exit(1)
            
            md_text = pymupdf4llm.to_markdown(str(pdf_file))
            output_file.write_text(md_text, encoding="utf-8")

        elif engine == "docling":
            try:
                from docling.document_converter import DocumentConverter
            except ImportError:
                print("Error: docling is not installed. Please install it using: pip install docling", file=sys.stderr)
                sys.exit(1)

            converter = DocumentConverter()
            result = converter.convert(str(pdf_file))
            md_text = result.document.export_to_markdown()
            output_file.write_text(md_text, encoding="utf-8")

        else:
            print(f"Error: Unknown engine '{engine}'. Choose from 'pymupdf4llm', 'docling'.", file=sys.stderr)
            sys.exit(1)

        print(f"Successfully generated markdown source: {output_file}")
        return str(output_file)

    except Exception as e:
        print(f"Error during PDF to markdown conversion with {engine}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    default_base = get_default_base_dir()
    parser = argparse.ArgumentParser(description="Convert PDF to markdown using pymupdf4llm or docling.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("--engine", choices=["pymupdf4llm", "docling"], default="pymupdf4llm", help="Extraction engine (default: pymupdf4llm)")
    parser.add_argument("--base-dir", "-b", default=default_base, help=f"Base folder for summaries (default: {default_base})")
    parser.add_argument("--note-name", "-n", default=None, help="Note / run name (defaults to PDF stem)")
    parser.add_argument("--output-dir", default=None, help="Explicit output directory (overrides base-dir + note-name)")

    args = parser.parse_args()

    n_name = args.note_name if args.note_name else Path(args.pdf_path).stem
    if args.output_dir:
        target_out_dir = args.output_dir
    else:
        target_out_dir = os.path.join(args.base_dir, n_name)

    convert_pdf_to_markdown(args.pdf_path, target_out_dir, engine=args.engine, note_name=n_name)
