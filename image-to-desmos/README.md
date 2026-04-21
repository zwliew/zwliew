# image-to-desmos

Convert a rough image of a graph — hand-drawn sketch, screenshot of a digital
plot, or photo of a printed textbook page — into a shareable Desmos URL.

Claude's vision model reads the image, calibrates the axes, traces the curve
into 30–50 sample points, and (when the shape is recognizable) proposes a
closed-form fit. The CLI packs the result into a URL whose hash fragment is
read by a tiny static viewer hosted on GitHub Pages, which renders everything
in the Desmos Graphing Calculator.

## Install

```
cd image-to-desmos
pip install -e .
cp .env.example .env   # then put your key in .env
```

Requires Python 3.11+ and an `ANTHROPIC_API_KEY`.

## Usage

```
python -m image_to_desmos path/to/graph.jpg
python -m image_to_desmos graph.jpg --open           # also open in browser
python -m image_to_desmos graph.jpg --debug          # also write graph.extraction.json
python -m image_to_desmos graph.jpg --base-url http://localhost:8000/
```

The default viewer is published at
`https://zwliew.github.io/image-to-desmos/viewer/`. Override with `--base-url`
for local testing.

### Exit codes

- `0` — success
- `1` — missing API key or input file
- `2` — low-confidence extraction (URL is still printed; a warning is written to stderr)

## How it works

1. **Extract** (`extract.py`): a single `client.messages.parse()` call to
   `claude-opus-4-7` with adaptive thinking. Structured output is validated
   against a Pydantic schema. The system prompt is marked for prompt caching.
2. **Pack** (`url.py`): the extracted table + fit + viewport are JSON-encoded
   and base64url-packed into `#d=<payload>` on the viewer URL. Hash (not
   query) keeps the data client-side. Payloads above 6 KB are truncated to
   30 points.
3. **Render** (`viewer/index.html`): a 25-line static page that decodes the
   hash and feeds it to the Desmos Calculator JS API.

## Local viewer

```
cd viewer && python -m http.server 8000
# in another shell:
python -m image_to_desmos samples/screenshot.png --base-url http://localhost:8000/ --open
```

## Limits

- Hand-drawn sketches without tick labels will be flagged `confidence=low`.
- The fitted closed-form function is best-effort; the sample-point table always
  renders regardless.
- Input images must be ≤ 5 MB (Anthropic API limit). Add Pillow if you need
  to downscale.
