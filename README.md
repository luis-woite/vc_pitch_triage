# VC Pitch Deck Triage Tool

Takes a founder's pitch deck (PDF), reads it slide by slide the way an analyst would (visually, not by scraping a text layer), and pulls out the claims it actually makes: team, market sizing, traction, competitors, the ask. Then it runs a set of rule-based checks to flag the claims that aren't backed up by anything in the deck itself.

Built to show I can build a tool that compresses a chunk of first-pass screening into minutes. It's an aid to an analyst's judgment, not a replacement for it.

This same approach adapts pretty naturally to other VC/PE workflows, comps screening, precedent transaction search, first-pass diligence on a data room. This is a deliberately simplified version.

Drop me a message on LinkedIn if you'd want something like this built into your firm's workflow.

## Where this actually stands

Working end to end, built to learn multimodal LLM extraction and rule-based grounding checks, not shipped as a product. Being upfront about its limits:

- Vision extraction quality depends on how a deck is designed. A dense, text-heavy slide or an unusual layout extracts less reliably than a clean one.
- The consistency checks are intentionally simple and rule-based (unsourced TAM, traction with no growth rate, missing competitors, etc.). They catch specific, explainable patterns, not everything a sharp human analyst would notice.
- Nothing in the memo is checked against outside reality yet. It only reflects what the deck itself claims, accurately, not whether those claims are true. An optional external-grounding step (cross-checking against something like GitHub for dev-tool startups) is sketched out but not built.
- Tested properly against one real deck so far, not a large benchmark set.
- Vision API cost scales with slide count, there's a cap in `config.py` to control this per run.

None of this is hidden in the code, the same caveats are in the module docstrings.

## Structure

```
vc_pitch_triage/
├── main.py              # runs the whole pipeline
├── config.py             # paths, render DPI, slide-count cap
├── requirements.txt
├── .env.example           # copy to .env, fill in your key
├── sample_decks/         # drop test .pdf decks here
└── src/
    ├── rendering/        # PDF -> slide images
    ├── extraction/       # the Claude vision extraction step
    ├── checks/           # rule-based consistency checks
    └── memo/             # builds the final .docx
```

## Running it

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `ANTHROPIC_API_KEY` — from console.anthropic.com/settings/keys
- `GITHUB_TOKEN` — optional, only needed if the external grounding step gets built out

Drop a pitch deck PDF into `sample_decks/`, then:
```bash
python main.py
```

### Why create this project folder somewhere simple

Use a plain path like `~/vc_pitch_triage`, avoid OneDrive-synced folders or anything with non-English characters in the path. A previous project of mine hit a real bug where a Cyrillic folder name crashed a networking library entirely. Learned that one the hard way, no need to repeat it.

## The actual interesting lesson from building this

The hard part wasn't getting Claude to read a slide. It was getting it to say "this isn't here" instead of inventing something plausible. A pitch deck is someone's best, most polished case for their company, so the risk isn't noise, it's confident-sounding claims with nothing behind them. The extraction prompt is built specifically to distinguish a sourced claim from an asserted one, and to mark a slide as having nothing extractable rather than filling the gap with a plausible guess. Same discipline as the PE screening tool, applied to a messier, more visual kind of document.

## What's next (not built yet)

- External grounding: cross-check a dev-tool startup's claims against its public GitHub repo (stars, contributors, release cadence) as an independent signal
- A simplified per-company ownership/cap-table snapshot, pre-filled with whatever the deck itself states (explicitly not a full legal cap table, that data doesn't exist in a deck)
- Testing against a proper benchmark set of varied real decks, not just one
