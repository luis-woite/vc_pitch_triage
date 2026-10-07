"""
Central config for the pitch deck triage tool.
"""

# --- Where to find input pitch decks (Phase 0 decision) ---
# Drop sample .pdf pitch decks into this folder to test against.
SAMPLE_DECKS_DIR = "sample_decks"

# --- Where rendered slide images get written (temporary, per-run) ---
RENDERED_SLIDES_DIR = "rendered_slides"

# --- Output location for generated triage memos ---
OUTPUT_DIR = "output"

# --- Image rendering resolution (DPI) for slide-to-image conversion ---
# Higher = better text legibility for the vision model, but larger file size
# and more tokens per API call. 150 is a reasonable starting point.
RENDER_DPI = 150

# --- Safety cap on deck length (slides) to control API cost per run ---
MAX_SLIDES_PER_DECK = 25
