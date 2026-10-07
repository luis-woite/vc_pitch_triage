"""
Phase 1 — PDF rendering.

Converts a pitch deck PDF into one image per slide, so Phase 2 can read
it the way an analyst would — visually — rather than scraping whatever
text layer happens to exist (pitch decks are often mostly charts and
images with little real text to scrape anyway).
"""

import os
import shutil
from typing import Optional

import pymupdf  # PyMuPDF — imported under its non-deprecated name (the old `fitz` alias is being phased out)


def get_page_count(pdf_path: str) -> int:
    """Returns the number of pages/slides in the PDF without rendering anything."""
    with pymupdf.open(pdf_path) as doc:
        return doc.page_count


def render_deck_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 150,
    max_slides: Optional[int] = None,
) -> list[str]:
    """
    Renders each page of the PDF to a PNG image, saved as
    <output_dir>/<deck_name>/slide_001.png, slide_002.png, ...

    Returns the list of saved image paths, in slide order. If the deck
    has more pages than max_slides, only the first max_slides are
    rendered and a warning is printed — this is a deliberate cost
    control, not a silent truncation.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Pitch deck not found: {pdf_path}")

    deck_name = os.path.splitext(os.path.basename(pdf_path))[0]
    deck_output_dir = os.path.join(output_dir, deck_name)

    # Clear any stale images from a previous run of this same deck, so we
    # never accidentally mix old and new renders if slide count changed.
    if os.path.exists(deck_output_dir):
        shutil.rmtree(deck_output_dir)
    os.makedirs(deck_output_dir, exist_ok=True)

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        raise ValueError(f"Could not open '{pdf_path}' as a PDF: {e}")

    total_pages = doc.page_count
    pages_to_render = total_pages
    if max_slides is not None and total_pages > max_slides:
        print(
            f"  Note: deck has {total_pages} slides, rendering only the first "
            f"{max_slides} (set max_slides higher in config.py to change this)."
        )
        pages_to_render = max_slides

    zoom = dpi / 72  # PDF's native resolution is 72 DPI; scale from there
    matrix = pymupdf.Matrix(zoom, zoom)

    image_paths = []
    for page_num in range(pages_to_render):
        page = doc.load_page(page_num)
        pixmap = page.get_pixmap(matrix=matrix)
        image_path = os.path.join(deck_output_dir, f"slide_{page_num + 1:03d}.png")
        pixmap.save(image_path)
        image_paths.append(image_path)

    doc.close()
    return image_paths


if __name__ == "__main__":
    # Manual test: python -m src.rendering.render path/to/deck.pdf
    import sys

    sys.path.insert(0, ".")
    from config import RENDERED_SLIDES_DIR, RENDER_DPI, MAX_SLIDES_PER_DECK

    if len(sys.argv) < 2:
        print("Usage: python -m src.rendering.render <path_to_pdf>")
        sys.exit(1)

    paths = render_deck_to_images(
        sys.argv[1], RENDERED_SLIDES_DIR, dpi=RENDER_DPI, max_slides=MAX_SLIDES_PER_DECK
    )
    print(f"Rendered {len(paths)} slide(s):")
    for p in paths:
        print(f"  {p}")
