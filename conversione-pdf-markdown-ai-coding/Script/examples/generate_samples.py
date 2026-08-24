"""Generate synthetic, non-sensitive PDFs for local conversion tests."""

from pathlib import Path

import pymupdf as fitz


EXAMPLES_DIR = Path(__file__).resolve().parent


def _add_test_content(page: fitz.Page) -> None:
    page.insert_text((72, 84), "Privacy-first PDF conversion", fontsize=20)
    page.insert_textbox(
        fitz.Rect(72, 120, 520, 420),
        (
            "Synthetic test document\n\n"
            "This PDF contains no personal or confidential data.\n"
            "- The input remains in process memory.\n"
            "- Native text is extracted without AI.\n"
            "- Scanned pages use local-only OCR.\n\n"
            "Reference value: LOCAL-TEST-2026"
        ),
        fontsize=12,
        lineheight=1.4,
    )


def create_text_pdf(path: Path) -> None:
    doc = fitz.open()
    try:
        _add_test_content(doc.new_page(width=595, height=842))
        doc.save(path)
    finally:
        doc.close()


def create_scanned_pdf(path: Path) -> None:
    source = fitz.open()
    output = fitz.open()
    try:
        page = source.new_page(width=595, height=842)
        _add_test_content(page)
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("jpeg")
        scan_page = output.new_page(width=595, height=842)
        scan_page.insert_image(scan_page.rect, stream=image)
        output.save(path)
    finally:
        source.close()
        output.close()


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    create_text_pdf(EXAMPLES_DIR / "sample_text.pdf")
    create_scanned_pdf(EXAMPLES_DIR / "sample_scanned.pdf")
    print(f"Created synthetic samples in {EXAMPLES_DIR}")


if __name__ == "__main__":
    main()
