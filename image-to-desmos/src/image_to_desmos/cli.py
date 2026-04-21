"""Command-line entry point for image-to-desmos."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from .extract import extract_graph
from .url import DEFAULT_BASE_URL, build_viewer_url

EXIT_OK = 0
EXIT_MISSING = 1
EXIT_LOW_CONFIDENCE = 2


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="image-to-desmos",
        description="Convert an image of a graph into a shareable Desmos URL.",
    )
    p.add_argument("image", type=Path, help="Path to the graph image (jpg/png/webp/gif).")
    p.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Viewer base URL (default: {DEFAULT_BASE_URL}).",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Also write <image>.extraction.json next to the input.",
    )
    p.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="Open the resulting URL in the default browser.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return EXIT_MISSING

    if not args.image.is_file():
        print(f"error: image not found: {args.image}", file=sys.stderr)
        return EXIT_MISSING

    extraction = extract_graph(args.image)

    if args.debug:
        debug_path = args.image.with_suffix(args.image.suffix + ".extraction.json")
        debug_path.write_text(extraction.model_dump_json(indent=2))
        print(f"debug: wrote {debug_path}", file=sys.stderr)

    url = build_viewer_url(extraction, base_url=args.base_url)
    print(url)

    if args.open_browser:
        webbrowser.open(url)

    if extraction.confidence == "low":
        print(
            f"warning: low-confidence extraction ({extraction.notes})",
            file=sys.stderr,
        )
        return EXIT_LOW_CONFIDENCE

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
