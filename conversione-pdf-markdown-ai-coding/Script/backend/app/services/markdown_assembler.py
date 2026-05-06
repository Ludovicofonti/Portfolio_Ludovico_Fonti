from __future__ import annotations

import re

from app.models.schemas import PageContent


def clean_page_text(text: str) -> str:
    """Apply cleanup rules to raw OCR text for a single page."""
    # Join hyphenated words split across lines
    text = re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)
    # Collapse multiple blank lines to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove stray isolated page numbers
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove extra spaces before punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    # Remove orphaned single characters on a line
    text = re.sub(r"^\s?[a-z]\s?$", "", text, flags=re.MULTILINE)
    # Final collapse of any remaining multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def assemble_markdown(page_texts: list[str]) -> tuple[str, list[PageContent]]:
    """Assemble cleaned page texts into a single Markdown document.

    Returns (full_content, page_contents).
    """
    page_contents: list[PageContent] = []
    cleaned_parts: list[str] = []

    for i, raw_text in enumerate(page_texts, start=1):
        cleaned = clean_page_text(raw_text)
        warning = None
        if not cleaned:
            warning = f"No text could be extracted from page {i}."
        page_contents.append(
            PageContent(page_number=i, text=cleaned, confidence_warning=warning)
        )
        cleaned_parts.append(cleaned)

    content = "\n\n---\n\n".join(cleaned_parts)
    return content, page_contents
