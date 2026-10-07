"""
Phase 2 — Vision extraction.

Sends every rendered slide image to Claude in a single call and asks
for structured claims back: team, market sizing, traction, competition,
the ask. This reads the deck the way an analyst would (visually) rather
than scraping a text layer — most pitch decks are mostly charts and
design, with little real text to scrape anyway.

Same grounding discipline as the PE screener's LLM synthesis module:
the model is instructed to only report what a slide actually shows, and
to explicitly flag slides with nothing extractable rather than invent
plausible-sounding content to fill the gap.

Cost note: every slide image counts toward the request's token usage,
so a longer deck costs more per run — this is exactly what
MAX_SLIDES_PER_DECK in config.py exists to cap.
"""

import base64
import json
import os
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a venture capital analyst assistant helping with \
first-pass triage of an inbound pitch deck.

You will be shown every slide of a pitch deck, in order, as images. Your \
job is to extract the claims the deck actually makes into structured data.

CRITICAL GROUNDING RULES:
- Only report what a slide literally shows. Do not use outside knowledge \
about the company, the market, or the sector, even if you recognise them.
- If a field isn't addressed anywhere in the deck, set it to null — do not \
infer or estimate a plausible-sounding value.
- Distinguish a SOURCED claim (the deck cites a source, a comparable, or \
real data) from an UNSOURCED claim (the deck just asserts a number). Note \
this explicitly for market-size and traction figures.
- If a slide is purely visual/design with no extractable claims (e.g. a \
logo slide, a section divider, a pure photo), list its number under \
slides_with_no_extractable_content rather than inventing content for it.
- Record which slide number each piece of information came from.

Respond with ONLY a JSON object (no markdown fences, no preamble), matching \
exactly this schema:
{
  "company_name": "string or null",
  "one_liner": "string or null — the core pitch in one sentence, if stated",
  "team": [
    {"name": "string", "background_claim": "string", "slide": int}
  ],
  "market": {
    "tam_claim": "string or null",
    "tam_sourced": true/false/null,
    "sam_claim": "string or null",
    "som_claim": "string or null",
    "slide": int or null
  },
  "traction": [
    {"metric": "string", "value": "string", "has_growth_rate": true/false, "slide": int}
  ],
  "competition": {
    "competitors_mentioned": ["string", ...],
    "slide": int or null
  },
  "ask": {
    "round_size": "string or null",
    "valuation": "string or null",
    "use_of_funds": "string or null",
    "slide": int or null
  },
  "slides_with_no_extractable_content": [int, ...]
}

team, traction, and competitors_mentioned should be empty lists (not null) \
if the deck doesn't address them."""

REQUIRED_KEYS = ("company_name", "one_liner", "team", "market", "traction", "competition", "ask",
                  "slides_with_no_extractable_content")


def _image_to_content_block(image_path: str) -> dict:
    """Reads a PNG file and returns it as an Anthropic API image content block."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": image_data},
    }


def _build_message_content(slide_image_paths: list[str]) -> list[dict]:
    """Interleaves a 'Slide N:' label before each image so the model can cite slide numbers correctly."""
    content = []
    for i, path in enumerate(slide_image_paths, start=1):
        content.append({"type": "text", "text": f"Slide {i}:"})
        content.append(_image_to_content_block(path))
    content.append(
        {"type": "text", "text": "Extract the structured claims from this deck, per the schema in your instructions."}
    )
    return content


def _strip_code_fences(text: str) -> str:
    """Claude sometimes wraps JSON in ```json fences despite instructions not to — strip them if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def extract_deck_claims(slide_image_paths: list[str]) -> dict:
    """
    Sends all slide images to Claude and returns the structured extraction
    as a dict matching the schema above, or {"error": str} on failure —
    never raises, so one bad deck doesn't crash a batch run.
    """
    if not slide_image_paths:
        return {"error": "No slide images provided."}

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not set — check your .env file."}

    try:
        client = Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_message_content(slide_image_paths)}],
        )
        raw_text = "".join(block.text for block in response.content if hasattr(block, "text"))
        cleaned = _strip_code_fences(raw_text)
        parsed = json.loads(cleaned)

        missing = [k for k in REQUIRED_KEYS if k not in parsed]
        if missing:
            return {"error": f"LLM response missing expected field(s) {missing}. Raw: {raw_text[:300]}"}

        return parsed

    except json.JSONDecodeError:
        return {"error": f"Could not parse LLM response as JSON. Raw: {raw_text[:300]}"}
    except Exception as e:
        return {"error": f"Vision extraction call failed: {e}"}


if __name__ == "__main__":
    # Manual test: python -m src.extraction.extract <deck_name>
    # (assumes src/rendering/render.py has already been run for that deck)
    import sys

    sys.path.insert(0, ".")
    from config import RENDERED_SLIDES_DIR

    deck_name = sys.argv[1] if len(sys.argv) > 1 else None
    if not deck_name:
        print("Usage: python -m src.extraction.extract <deck_name>")
        sys.exit(1)

    deck_dir = os.path.join(RENDERED_SLIDES_DIR, deck_name)
    image_paths = sorted(
        os.path.join(deck_dir, f) for f in os.listdir(deck_dir) if f.lower().endswith(".png")
    )
    print(f"Sending {len(image_paths)} slide(s) to Claude...")

    result = extract_deck_claims(image_paths)
    print(json.dumps(result, indent=2))
