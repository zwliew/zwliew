"""Claude vision call that turns a graph image into structured data."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000

SYSTEM_PROMPT = """You are a graph-digitizing assistant. Given an image of a 2D \
mathematical graph, extract the curve into structured data.

Work in this order:

1. Classify the image as one of: hand_drawn (sketch on paper or whiteboard), \
digital_plot (screenshot of Desmos/GeoGebra/matplotlib/etc.), or \
printed_textbook (photo or scan of a printed page).

2. Calibrate the axes. Find the tick marks and labels on both axes and work out \
the mapping from pixels to data coordinates. Report the visible data range as \
x_min, x_max, y_min, y_max. If no labels are visible, make a reasonable guess \
(default to a symmetric range around any visible origin) and set confidence to \
\"low\" with a short explanation in the notes field.

3. Trace the curve and emit 30 to 50 sample points in DATA coordinates (not \
pixels), spaced roughly evenly across the visible x-range. If the curve has \
multiple branches or is not a function of x, sample enough points to capture \
the shape. Keep all x values within [x_min, x_max].

4. If the curve clearly matches one of \
{linear, quadratic, cubic, exponential, sine, cosine, logistic}, propose a \
closed-form fit as a Desmos-compatible LaTeX string assigning to y. Examples: \
\"y=0.5x^{2}-3\", \"y=2\\\\sin(x)+1\", \"y=\\\\frac{5}{1+e^{-x}}\". Use \
x^{2} not x^2, and \\\\sin / \\\\cos / \\\\log for functions. If the shape \
isn't clearly one of these families, set fitted_function to null.

5. Set confidence to \"high\" when axes are labeled and the curve is crisp, \
\"medium\" for readable but noisy plots, \"low\" for unlabeled sketches or \
heavy occlusion. Put anything the reader should know in notes (e.g. \"axis \
labels not visible, assumed -10..10\").

Return only the structured object."""

USER_INSTRUCTION = (
    "Extract this graph. Classify the image, calibrate the axes, sample 30–50 "
    "points along the curve in data coordinates, and propose a closed-form fit "
    "if the shape is clearly recognizable."
)


class Point(BaseModel):
    x: float
    y: float


class AxisCalibration(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class GraphExtraction(BaseModel):
    image_type: Literal["hand_drawn", "digital_plot", "printed_textbook"]
    axes: AxisCalibration
    points: list[Point] = Field(..., min_length=2, max_length=80)
    fitted_function: str | None = Field(
        None,
        description="Desmos LaTeX assigning to y, or null if shape isn't recognizable.",
    )
    confidence: Literal["low", "medium", "high"]
    notes: str


_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _media_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in _MEDIA_TYPES:
        raise ValueError(
            f"Unsupported image extension: {suffix!r}. "
            f"Use one of: {sorted(_MEDIA_TYPES)}."
        )
    return _MEDIA_TYPES[suffix]


def extract_graph(image_path: Path, client: anthropic.Anthropic | None = None) -> GraphExtraction:
    """Send the image to Claude and return a validated GraphExtraction."""
    client = client or anthropic.Anthropic()
    media_type = _media_type_for(image_path)
    data = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")

    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": data,
                        },
                    },
                    {"type": "text", "text": USER_INSTRUCTION},
                ],
            }
        ],
        output_format=GraphExtraction,
    )
    return response.parsed_output
