"""
Phase 3 — Consistency checks.

Pure rule-based logic over the Phase 2 extraction — no LLM call here.
Each check produces one specific, explainable flag tied to a slide
number, rather than a vague aggregate "risk score" that can't be traced
back to anything concrete in the deck.
"""

from typing import Optional


def _flag(message: str, slide: Optional[int] = None, severity: str = "caution") -> dict:
    return {"severity": severity, "message": message, "slide": slide}


def run_consistency_checks(claims: dict, total_slides: int) -> list[dict]:
    """
    Returns a list of flags, each {"severity": "caution"|"info", "message": str, "slide": int|None}.
    `total_slides` is the actual rendered slide count (from Phase 1), used
    to judge how much of the deck had any extractable content at all.
    """
    flags = []

    # --- Market sizing checks ---
    market = claims.get("market") or {}
    tam_claim = market.get("tam_claim")
    tam_sourced = market.get("tam_sourced")
    market_slide = market.get("slide")

    if tam_claim is None:
        flags.append(_flag("No market sizing (TAM/SAM/SOM) found anywhere in the deck.", severity="info"))
    elif tam_sourced is False or tam_sourced is None:
        flags.append(
            _flag(
                f"TAM claim ('{tam_claim}') is not tied to any cited source or comparable in the deck.",
                slide=market_slide,
            )
        )

    # --- Traction checks ---
    traction = claims.get("traction") or []
    if not traction:
        flags.append(_flag("No traction metrics found anywhere in the deck.", severity="info"))
    else:
        for item in traction:
            if not item.get("has_growth_rate"):
                metric = item.get("metric", "metric")
                value = item.get("value", "")
                flags.append(
                    _flag(
                        f"'{metric}: {value}' is reported as a snapshot with no growth rate or trend — "
                        f"hard to assess trajectory from this alone.",
                        slide=item.get("slide"),
                    )
                )

    # --- Competition checks ---
    competition = claims.get("competition") or {}
    competitors = competition.get("competitors_mentioned") or []
    if not competitors:
        flags.append(
            _flag(
                "No competitors mentioned anywhere in the deck — competitive landscape is unverifiable from this material alone.",
                severity="info",
            )
        )

    # --- Team checks ---
    team = claims.get("team") or []
    if not team:
        flags.append(_flag("No team information found anywhere in the deck.", severity="info"))

    # --- Ask checks ---
    ask = claims.get("ask") or {}
    if ask.get("round_size") and not ask.get("use_of_funds"):
        flags.append(
            _flag(
                f"Round size stated ('{ask.get('round_size')}') but no use-of-funds breakdown provided.",
                slide=ask.get("slide"),
            )
        )

    # --- Overall deck-quality check ---
    no_content_slides = claims.get("slides_with_no_extractable_content") or []
    if total_slides > 0:
        no_content_ratio = len(no_content_slides) / total_slides
        if no_content_ratio >= 0.4:
            flags.append(
                _flag(
                    f"{len(no_content_slides)} of {total_slides} slides had no extractable claims — "
                    f"this deck is largely visual/design-driven, which limits what this analysis can verify.",
                    severity="info",
                )
            )

    return flags


if __name__ == "__main__":
    # Manual test with a constructed example — no API call, no deck needed.
    example_claims = {
        "market": {"tam_claim": "$30B", "tam_sourced": False, "slide": 3},
        "traction": [
            {"metric": "ARR", "value": "$2M", "has_growth_rate": True, "slide": 4},
            {"metric": "Users", "value": "50,000", "has_growth_rate": False, "slide": 4},
        ],
        "competition": {"competitors_mentioned": [], "slide": None},
        "team": [{"name": "Jane Doe", "background_claim": "Ex-Google", "slide": 5}],
        "ask": {"round_size": "$8M", "use_of_funds": None, "slide": 7},
        "slides_with_no_extractable_content": [1, 2],
    }
    for flag in run_consistency_checks(example_claims, total_slides=7):
        print(f"[{flag['severity']}] (slide {flag['slide']}) {flag['message']}")
