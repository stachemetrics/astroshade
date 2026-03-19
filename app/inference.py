"""
Astroshade — Gemini inference module.

Four inference functions for the hair colour consultation flow:
  1. analyse_desired_state  — vision/text analysis of the client's desired look
  2. analyse_starting_state — vision analysis of the client's current hair
  3. generate_preview       — image generation showing the desired result
  4. generate_formulation   — structured Goldwell formulation recommendation
"""

import json
import os
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"

_client = None


def _get_client() -> genai.Client:
    """Lazy-init Gemini client so the module can be imported without an API key."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    return _client

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROMPT_DIR = os.path.join(_HERE, "prompts")
if not os.path.isdir(_PROMPT_DIR):
    _PROMPT_DIR = "/root/prompts"


def _load_prompt(name: str) -> str:
    """Read a prompt template from ``{name}.txt``."""
    with open(os.path.join(_PROMPT_DIR, f"{name}.txt")) as f:
        return f.read()


def _load_examples(name: str) -> str:
    """Read ``{name}_examples.json`` and format into a readable text block.

    Returns a string suitable for injection into a prompt via the
    ``{examples}`` placeholder.
    """
    path = os.path.join(_PROMPT_DIR, f"{name}_examples.json")
    with open(path) as f:
        data = json.load(f)

    lines: list[str] = ["## Examples", ""]

    # --- positive examples ---
    for ex in data.get("positive", []):
        lines.append(f"### Good example — {ex['label']}")

        # Build input description
        inp = ex.get("input", {})
        input_parts: list[str] = []
        if inp.get("client_notes"):
            input_parts.append(f'Client says "{inp["client_notes"]}"')
        if inp.get("stylist_notes"):
            input_parts.append(f'Stylist notes: "{inp["stylist_notes"]}"')
        if inp.get("has_image") or inp.get("image_path"):
            input_parts.append("(with reference image)")
        if inp.get("image_description"):
            input_parts.append(f'Image shows: {inp["image_description"]}')
        # For formulation / preview examples the input is structured
        if inp.get("desired"):
            input_parts.append(f"Desired: {json.dumps(inp['desired'])}")
        if inp.get("starting"):
            input_parts.append(f"Starting: {json.dumps(inp['starting'])}")
        if inp.get("description"):
            input_parts.append(f"Description: {inp['description']}")
        if inp.get("target_level"):
            input_parts.append(f"Target level: {inp['target_level']}")
        if inp.get("tone"):
            input_parts.append(f"Tone: {inp['tone']}")
        if inp.get("technique"):
            input_parts.append(f"Technique: {inp['technique']}")

        lines.append(f"Input: {' | '.join(input_parts) if input_parts else '(see structured input)'}")

        if "expected_output" in ex:
            lines.append(f"Output: {json.dumps(ex['expected_output'])}")
        if "guidance" in ex:
            lines.append(f"Guidance: {ex['guidance']}")
        if "why" in ex:
            lines.append(f"Why: {ex['why']}")
        lines.append("")

    # --- negative examples ---
    for ex in data.get("negative", []):
        lines.append(f"### Bad example — {ex['label']}")

        inp = ex.get("input", {})
        input_parts = []
        if inp.get("client_notes"):
            input_parts.append(f'Client says "{inp["client_notes"]}"')
        if inp.get("stylist_notes"):
            input_parts.append(f'Stylist notes: "{inp["stylist_notes"]}"')
        if inp.get("has_image") or inp.get("image_path"):
            input_parts.append("(with reference image)")
        if inp.get("image_description"):
            input_parts.append(f'Image shows: {inp["image_description"]}')
        if inp.get("desired"):
            input_parts.append(f"Desired: {json.dumps(inp['desired'])}")
        if inp.get("starting"):
            input_parts.append(f"Starting: {json.dumps(inp['starting'])}")
        if inp.get("description"):
            input_parts.append(f"Description: {inp['description']}")
        if inp.get("target_level"):
            input_parts.append(f"Target level: {inp['target_level']}")
        if inp.get("tone"):
            input_parts.append(f"Tone: {inp['tone']}")
        if inp.get("technique"):
            input_parts.append(f"Technique: {inp['technique']}")

        lines.append(f"Input: {' | '.join(input_parts) if input_parts else '(see structured input)'}")

        if "bad_output" in ex:
            lines.append(f"Bad output: {json.dumps(ex['bad_output'])}")
        if "problem" in ex:
            lines.append(f"Problem: {ex['problem']}")
        if "correction" in ex:
            lines.append(f"Correction: {ex['correction']}")
        lines.append("")

    return "\n".join(lines)


def _load_example_images(name: str) -> list[bytes]:
    """Return image bytes from ``image_path`` fields in the examples JSON.

    Only includes entries where the file actually exists on disk.
    """
    path = os.path.join(_PROMPT_DIR, f"{name}_examples.json")
    with open(path) as f:
        data = json.load(f)

    images: list[bytes] = []
    # Walk both positive and negative examples
    for section in ("positive", "negative"):
        for ex in data.get(section, []):
            img_path = ex.get("input", {}).get("image_path")
            if not img_path:
                continue
            # Resolve relative to project root (one level above _HERE)
            full = os.path.join(os.path.dirname(_HERE), img_path)
            if not os.path.isfile(full):
                # Try relative to _PROMPT_DIR parent as fallback
                full = os.path.join(_PROMPT_DIR, "..", "..", img_path)
            if os.path.isfile(full):
                with open(full, "rb") as fimg:
                    images.append(fimg.read())
    return images


def _build_prompt(name: str, include_example_images: bool = False, **kwargs) -> str | tuple[str, list[bytes]]:
    """Load prompt template + examples, format with *kwargs*, return final string.

    If *include_example_images* is True, also return a list of image bytes
    extracted from ``image_path`` fields in the examples JSON.  The return
    type becomes ``(str, list[bytes])`` in that case.
    """
    examples_text = _load_examples(name)
    template = _load_prompt(name)
    prompt = template.format(examples=examples_text, **kwargs)

    if include_example_images:
        images = _load_example_images(name)
        return prompt, images
    return prompt


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class DesiredStateAnalysis(BaseModel):
    target_level: int = Field(description="Target colour level (1=black, 10=lightest blonde)")
    tone: str = Field(description="Target tone, e.g. 'violet/pearl', 'ash', 'beige/gold', 'natural', 'copper'")
    technique: str = Field(description="e.g. 'global lightening + tone', 'balayage', 'root retouch', 'glaze/toning'")
    description: str = Field(description="Short professional description of the desired result, e.g. 'Clean, icy, level 10 platinum blonde. Cool, reflective finish. No yellow.'")


class StartingStateAnalysis(BaseModel):
    current_level: int = Field(description="Assessed natural/current level (1=black, 10=lightest blonde)")
    description: str = Field(description="Short professional description, e.g. 'Medium Blonde, virgin hair, healthy condition'")
    grey_percentage: int = Field(description="Estimated percentage of grey/white hair visible (0 if none)")
    condition: str = Field(description="Hair condition: healthy, slightly porous, damaged, dry, etc.")
    previous_colour: str = Field(description="Any visible signs of previous colour work, or 'none'")


class FormulationStep(BaseModel):
    step_name: str = Field(description="e.g. 'Lightener', 'Toner', 'Highlift'")
    product: str = Field(description="Exact product and shade codes, e.g. 'Colorance 10V + 10P (1:1)'")
    developer: str = Field(description="Developer used, e.g. '6% (20 vol)', 'Colorance Lotion 2%'")
    ratio: str = Field(description="Developer to colour ratio, e.g. '1:1', '2:1', '1:2'")
    amounts: str = Field(description="Exact amounts, e.g. '35g powder : 35ml developer'")
    processing_time: str = Field(description="Time with any visual checkpoints")
    application_notes: str = Field(description="Where to apply, order, what to avoid")


class HairFormulation(BaseModel):
    steps: list[FormulationStep] = Field(description="Ordered formulation steps")
    colour_theory: str = Field(description="Explain WHY this formulation works — reference underlying pigment, neutralisation, and product choices")
    warnings: str = Field(description="Any risks or things the stylist must watch for")


# ---------------------------------------------------------------------------
# Inference functions
# ---------------------------------------------------------------------------

def analyse_desired_state(
    client_notes: str,
    image_bytes: bytes = None,
) -> DesiredStateAnalysis:
    """Analyse a client's desired hair colour from notes and/or a reference image.

    Returns a structured ``DesiredStateAnalysis``.
    """
    system_prompt = _build_prompt("a_desired_state")

    contents: list = [f'CLIENT SAYS: "{client_notes}"']
    if image_bytes:
        contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_schema": DesiredStateAnalysis,
            "temperature": 0.1,
        },
    )
    return DesiredStateAnalysis.model_validate_json(response.text)


def analyse_starting_state(
    image_bytes: bytes,
    stylist_notes: str = None,
) -> StartingStateAnalysis:
    """Analyse a photo of the client's current hair state.

    Returns a structured ``StartingStateAnalysis``.
    """
    system_prompt = _build_prompt("b_starting_state")

    contents: list = [types.Part.from_bytes(data=image_bytes, mime_type="image/png")]
    if stylist_notes:
        contents.append(f'STYLIST NOTES: "{stylist_notes}"')

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_schema": StartingStateAnalysis,
            "temperature": 0.1,
        },
    )
    return StartingStateAnalysis.model_validate_json(response.text)


def generate_preview(
    image_bytes: bytes,
    desired: DesiredStateAnalysis,
    style_notes: str = "none",
) -> Image.Image | None:
    """Generate a preview image showing the client with their desired hair colour.

    Uses ``gemini-2.5-flash-image`` with ``response_modalities=['IMAGE', 'TEXT']``.
    Returns a ``PIL.Image`` on success, or ``None`` if generation fails (the app
    should fall back to a text description in that case).
    """
    try:
        prompt = _build_prompt(
            "c_preview",
            description=desired.description,
            target_level=desired.target_level,
            tone=desired.tone,
            technique=desired.technique,
            style_notes=style_notes,
        )

        response = _get_client().models.generate_content(
            model=IMAGE_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                return Image.open(BytesIO(part.inline_data.data))

        return None
    except Exception:
        return None


def generate_formulation(
    desired: DesiredStateAnalysis,
    starting: StartingStateAnalysis,
) -> HairFormulation:
    """Generate a Goldwell colour formulation given confirmed desired and starting states.

    Returns a structured ``HairFormulation`` with steps, colour theory, and warnings.
    """
    system_prompt = _build_prompt("d_formulation")

    user_message = f"""\
DESIRED RESULT:
  Target level: {desired.target_level}
  Tone: {desired.tone}
  Technique: {desired.technique}
  Description: {desired.description}

STARTING STATE:
  Current level: {starting.current_level}
  Description: {starting.description}
  Grey %: {starting.grey_percentage}
  Condition: {starting.condition}
  Previous colour: {starting.previous_colour}

Please provide your recommended Goldwell formulation."""

    response = _get_client().models.generate_content(
        model=MODEL,
        contents=user_message,
        config={
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_schema": HairFormulation,
            "temperature": 0.1,
        },
    )
    return HairFormulation.model_validate_json(response.text)
