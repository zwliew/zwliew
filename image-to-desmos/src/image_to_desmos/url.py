"""Pack a GraphExtraction into a shareable Desmos viewer URL."""

from __future__ import annotations

import base64
import json
from urllib.parse import urljoin

from .extract import GraphExtraction

DEFAULT_BASE_URL = "https://zwliew.github.io/image-to-desmos/viewer/"
MAX_PAYLOAD_BYTES = 6144
TRUNCATED_POINTS = 30


def _format_number(value: float) -> str:
    """Render a float compactly while preserving enough precision for Desmos."""
    if value == int(value):
        return str(int(value))
    return f"{value:.6g}"


def _viewport_bounds(extraction: GraphExtraction) -> dict[str, float]:
    x_min = extraction.axes.x_min
    x_max = extraction.axes.x_max
    y_min = extraction.axes.y_min
    y_max = extraction.axes.y_max
    x_pad = max((x_max - x_min) * 0.05, 0.1)
    y_pad = max((y_max - y_min) * 0.05, 0.1)
    return {
        "left": x_min - x_pad,
        "right": x_max + x_pad,
        "bottom": y_min - y_pad,
        "top": y_max + y_pad,
    }


def _build_expressions(points: list, fitted_function: str | None) -> list[dict]:
    expressions: list[dict] = [
        {
            "id": "t1",
            "type": "table",
            "columns": [
                {"latex": "x", "values": [_format_number(p.x) for p in points]},
                {"latex": "y", "values": [_format_number(p.y) for p in points]},
            ],
        }
    ]
    if fitted_function:
        expressions.append({"id": "f1", "latex": fitted_function})
    return expressions


def extraction_to_payload(extraction: GraphExtraction) -> dict:
    """Build the JSON payload consumed by viewer/index.html.

    If the packed payload would exceed ~6 KB, drop to 30 evenly spaced points.
    """
    points = list(extraction.points)
    payload = {
        "expressions": _build_expressions(points, extraction.fitted_function),
        "bounds": _viewport_bounds(extraction),
    }
    if len(_encode_payload(payload)) > MAX_PAYLOAD_BYTES and len(points) > TRUNCATED_POINTS:
        step = len(points) / TRUNCATED_POINTS
        kept = [points[min(int(i * step), len(points) - 1)] for i in range(TRUNCATED_POINTS)]
        payload["expressions"] = _build_expressions(kept, extraction.fitted_function)
    return payload


def _encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def build_viewer_url(extraction: GraphExtraction, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return a full viewer URL with the extraction packed into #d=..."""
    payload = extraction_to_payload(extraction)
    encoded = _encode_payload(payload)
    base = base_url if base_url.endswith("/") else base_url + "/"
    return urljoin(base, "") + f"#d={encoded}"
