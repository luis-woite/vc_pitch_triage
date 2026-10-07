"""
Entry point for the pitch deck triage pipeline.

Status:
  Phase 1 (rendering)   -> DONE, see src/rendering
  Phase 2 (extraction)  -> DONE, see src/extraction (vision LLM structured extraction)
  Phase 3 (checks)      -> DONE, see src/checks (consistency / unsourced-claim checks)
  Phase 4 (grounding)   -> TODO, see src/grounding (optional external verification, e.g. GitHub)
  Phase 5 (memo)        -> DONE, see src/memo (assemble the triage memo)
"""

import os
import sys

from config import SAMPLE_DECKS_DIR, OUTPUT_DIR, RENDERED_SLIDES_DIR, RENDER_DPI, MAX_SLIDES_PER_DECK
from src.rendering.render import render_deck_to_images
from src.extraction.extract import extract_deck_claims
from src.checks.consistency import run_consistency_checks
from src.memo.generate import generate_triage_memo


def run_pipeline(deck_path: str) -> None:
    deck_name = os.path.splitext(os.path.basename(deck_path))[0]
    print(f"\n--- Running triage pipeline for: {deck_name} ---")

    print("[1/5] Rendering slides to images...")
    try:
        slide_images = render_deck_to_images(
            deck_path, RENDERED_SLIDES_DIR, dpi=RENDER_DPI, max_slides=MAX_SLIDES_PER_DECK
        )
        print(f"   Rendered {len(slide_images)} slide(s) to {RENDERED_SLIDES_DIR}/{deck_name}/")
    except (FileNotFoundError, ValueError) as e:
        print(f"   Rendering failed: {e}")
        print(f"--- Aborted for {deck_name} ---\n")
        return

    print("[2/5] Extracting structured claims (vision)...")
    claims = extract_deck_claims(slide_images)
    if "error" in claims:
        print(f"   Extraction failed: {claims['error']}")
        print(f"--- Aborted for {deck_name} ---\n")
        return

    print(f"   Company: {claims.get('company_name')}")
    print(f"   One-liner: {claims.get('one_liner')}")
    print(f"   Team members found: {len(claims.get('team', []))}")
    print(f"   Traction metrics found: {len(claims.get('traction', []))}")
    market = claims.get("market", {})
    print(f"   TAM claim: {market.get('tam_claim')} (sourced: {market.get('tam_sourced')})")
    no_content = claims.get("slides_with_no_extractable_content", [])
    if no_content:
        print(f"   Slides with no extractable content: {no_content}")
    print("[3/5] Running consistency checks...")
    flags = run_consistency_checks(claims, total_slides=len(slide_images))
    if not flags:
        print("   No flags — deck's claims are well-sourced and complete by these checks.")
    else:
        for flag in flags:
            slide_str = f" (slide {flag['slide']})" if flag["slide"] is not None else ""
            print(f"   [{flag['severity']}]{slide_str} {flag['message']}")
    print("[4/5] External grounding (optional)...          (TODO: Phase 4)")

    print("[5/5] Generating triage memo...")
    try:
        memo_path = generate_triage_memo(deck_name, claims, flags, output_dir=OUTPUT_DIR)
        print(f"   Memo saved to: {memo_path}")
    except Exception as e:
        print(f"   Memo generation failed: {e}")

    print(f"--- Done for {deck_name} ---\n")


if __name__ == "__main__":
    os.makedirs(SAMPLE_DECKS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if len(sys.argv) > 1:
        run_pipeline(sys.argv[1])
    else:
        decks = [f for f in os.listdir(SAMPLE_DECKS_DIR) if f.lower().endswith(".pdf")]
        if not decks:
            print(
                f"No sample decks found in '{SAMPLE_DECKS_DIR}/'. "
                f"Add a .pdf pitch deck there, or run: python main.py path\\to\\deck.pdf"
            )
        else:
            for deck in decks:
                run_pipeline(os.path.join(SAMPLE_DECKS_DIR, deck))
