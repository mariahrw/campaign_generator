# CLAUDE.md

Conventions for working in this repo. See [README.md](README.md) for the full project description and input format.

## Setup & running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`GEMINI_API_KEY` must be set in `.env` (never print its value or suggest committing `.env`).

## Testing

No test suite exists yet — don't assume a pytest config or similar. Adding coverage is a known gap (see README's Next Steps).

## Architecture

- `main.py` — entry point, points at a brief JSON
- `campaign/generate.py` — orchestrates the full brief-to-creatives pipeline
- `models.py` — the brief/product/market schema (pydantic)
- `generation/google_genai/service.py` — all Gemini calls (localization, cutout/background generation)
- `layout/` — SVG layout parsing, masking, compositing, cropping
- `plugins/illustrator/TrueFrame.jsx` — Illustrator-side export/validation script

## Comments & docstrings

- Docstrings (module, class, or function) are **one short sentence** — never multi-line explanations of rationale, edge cases, or history.
- If a non-obvious "why" needs preserving (a hidden constraint, a workaround, a subtle invariant), use a short inline `#`/`//` comment at the relevant line instead of expanding the docstring.
- Every script (e.g. `.jsx`/`.py` entry points, standalone tools) starts with a one-sentence description of what it does, at the top of the file.

## Attribution

- Never name the AI or tool (Claude, AI-generated, etc.) in comments, docstrings, or docs. "Generated code" / "not hand-audited" is fine when the caveat is useful — just leave out which tool wrote it.
