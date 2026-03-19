# agents.md — Astroshade

**A technical readiness prototype validating AI reasoning for professional hair colour formulation.**

<p align="center">
  <img src="assets/astro_cool_hair.jpg" alt="Astroshade Logo" width="350"/>
</p>

## Project Name & Origin

**Astroshade** — named after the Galaxie Hair Salon in *The Jetsons*, where a machine can instantaneously change Judy Jetson's hairstyle. In the same episode, she meets Astro, the space pup. We like dogs.

## The Hypothesis

> Can AI perform well enough — particularly on photos of people — to convince a working stylist to use its recommendations?

This is a tech readiness test, not a product build. We're validating whether foundation models (specifically Gemini) can reason about hair colour formulation accurately enough that a professional colourist would trust the output mid-consultation. If the answer is yes, there's a product here. If no, we've saved months of building the wrong thing.

## Collaborator & Attribution

**Matt Smith** — 26-year-old founder and dad. Matt stepped back from running his own salon business because he sees AI transforming the industry and wants to be ahead of it. He now rents a chair while building Alloura, his vision for AI-assisted hair colour consultations. The core use case, the user journey, the test cases, and the domain expertise driving this prototype are all Matt's.

## The Problem

Even experienced colourists regularly ask each other for second opinions on formulas, ratios, and techniques. Outcomes vary depending on who performs the service. When a client's regular stylist goes on leave or moves salons, the client can lose their colour result. The goal is to remove guesswork from colour formulation and produce consistent, repeatable results across different stylists.

## User Journey (7 Steps)

1. Client describes or uploads a desired colour look
2. AI analyses and returns structured description — stylist confirms or corrects
3. Stylist uploads photo of client's current hair (+ consent toggle)
4. AI analyses starting state — stylist confirms or corrects
5. System shows visual preview of the desired result on the client *(image gen)*
6. AI generates formulation recommendation with colour theory reasoning — stylist rates and gives feedback
7. CTA — "interested in learning more?" — email/mobile capture

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI API | Gemini (paid API key) | Single API for vision, image gen, and formulation reasoning. Free tier has zero quota for image gen — paid key unlocks it |
| Model (text/vision) | `gemini-2.5-flash` | Fast structured JSON output with Pydantic schemas |
| Model (image gen) | `gemini-2.5-flash-image` | Native image editing via `response_modalities=['IMAGE', 'TEXT']` |
| Product range | Goldwell only (for now) | All 3 test cases use Goldwell; baked into system prompt |
| Deployment | Gradio + Modal | Proven pattern from TenderTrawl. Public URL, mobile-first |
| Logging | Modal Volume | Persistent session logs, feedback, email captures |
| Dev approach | Notebook → app extraction | AI pipeline validated in Jupyter, now packaging for Gradio |

Please reference the official Google SDK documentation when prototyping:
- Python: https://googleapis.github.io/python-genai/
- JS: https://googleapis.github.io/js-genai/release_docs/index.html
- Codegen instructions (for AI assistants): https://github.com/googleapis/python-genai/blob/main/codegen_instructions.md

---

## Project Structure (App Build Phase)

```
astroshade/
├── agents.md                    # This file — project context and handover
├── .env                         # GEMINI_API_KEY=... (gitignored)
├── .env.example                 # Template
├── .gitignore
├── .python-version
│
├── app/
│   ├── app.py                   # Gradio UI — multi-step consultation flow
│   ├── deploy.py                # Modal deployment harness
│   ├── inference.py             # Gemini API calls: analyse, preview, formulate
│   └── prompts/                 # System prompts as separate .txt files
│       ├── desired_state.txt    # Step 1-2: analyse desired look
│       ├── starting_state.txt   # Step 3-4: analyse current hair
│       ├── preview.txt          # Step 5: image gen / hair colour edit
│       └── formulation.txt      # Step 6: colour formulation recommendation
│
├── notebooks/                   # Jupyter notebooks (validation, not deployed)
│   ├── 00_setup.ipynb
│   ├── 01_formulation.ipynb
│   └── 02_user_journey.ipynb
│
├── testcases/                   # Matt's test data (not deployed)
│   ├── structured/              # JSON + image assets per case
│   └── matt-smith-testcases.pptx
│
└── assets/                      # Logo, branding
```

### Why separate prompt files?

System prompts are the most-tweaked part of the codebase. Keeping them in `.txt` files means:
- Edit and re-test without touching Python code
- Diff changes clearly in git
- Load at runtime so Modal redeploys pick up changes without code edits
- Easy to add few-shot examples inline

In `inference.py`, load them like:

```python
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROMPT_DIR = os.path.join(_HERE, 'prompts')
if not os.path.isdir(_PROMPT_DIR):
    _PROMPT_DIR = '/root/prompts'  # Modal layout

def _load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPT_DIR, f'{name}.txt')) as f:
        return f.read()
```

---

## System Prompts — Design Notes

### General principles
- Be concise. Tight instructions outperform walls of text.
- Include 1-2 concrete examples of good output (from Matt's known-good formulations).
- State what NOT to do explicitly (negative examples from testing).
- Every prompt should state: "You are assisting a professional colourist. Be precise."

### `desired_state.txt` — Steps 1-2

Analyses a reference image and/or client description. Returns structured JSON.

Key fields: `target_level` (1-10), `tone`, `technique`, `description`.

No major issues from testing — works well with image+text and text-only.

### `starting_state.txt` — Steps 3-4

Analyses a photo of the client's current hair. Returns structured JSON.

Key fields: `current_level`, `description`, `grey_percentage`, `condition`, `previous_colour`.

Works well. Correctly identified level 7, virgin hair, 0% grey on case 1.

### `preview.txt` — Step 5 (IMAGE GEN — NEEDS MOST WORK)

**Known issue: dark roots persist in generated images.**

During testing, the model consistently kept dark roots visible even when the desired look was global/all-over colour. This is the #1 thing to fix.

The prompt must be explicit:

```
CRITICAL: If the technique is "global lightening" or "all-over colour", the ENTIRE head of
hair must be the target colour — including the roots, the crown, and the hairline.
Do NOT leave any darker roots, shadow root, or root smudge unless the stylist
specifically requested it. "Global" means every strand from root to tip is the same level and tone.
```

Other guidelines:
- Keep the person's face, skin, clothing, background identical
- Only change the hair colour — not style, length, cut, or texture
- Result must look photorealistic and natural
- Use `response_modalities=['IMAGE', 'TEXT']`
- Model: `gemini-2.5-flash-image`

**Fallback:** If image gen fails or looks bad, show a text description of the target. Don't block the flow.

### `formulation.txt` — Step 6 (MOST IMPORTANT)

This is the core value proposition. The prompt should:

1. State the role: expert Goldwell formulator, second-opinion tool for professionals
2. Include colour theory principles (concise)
3. Include 1-2 known-good examples as few-shot demonstrations
4. Require structured output: product, developer, ratio, amounts, time, application
5. Require colour theory reasoning explaining WHY
6. Include warnings about common risks

**Few-shot example to embed (Case 1 — abbreviated):**

```
EXAMPLE — Scandi Blonde (Level 7 virgin → Level 10 icy platinum):

Step 1 — Lightener:
  Product: SilkLift Strong
  Developer: 6% (20 vol)
  Ratio: 1:1
  Amounts: 35g powder : 35ml developer
  Additives: 3 pumps Intensive Conditioning Serum
  Time: Up to 45 min (visual check until pale yellow)
  Application: 1cm off scalp through ends first, roots once mids reach level 9

Step 2 — Toner:
  Product: Colorance 10V + 10P (1:1)
  Developer: Colorance Lotion 2%
  Ratio: 2:1
  Amounts: 40ml lotion : 10ml 10V : 10ml 10P
  Time: 15 min
  Application: Rinse lightener, shampoo, towel dry, apply at basin

Why: 20 vol lifts virgin level 7 three levels. At level 10, underlying pigment is pale yellow.
V (Violet) neutralises yellow. P (Pearl) adds icy reflective finish.
```

**Known AI divergences from Matt's formulations:**
- AI returned 1:2 ratio for SilkLift lightener where known-good is 1:1. Include as negative example. <--GP this is for case 1 - so you want a combination of inputs and outputs in your prompt -->
- AI processing times are sometimes wider than needed ("15-25 min" vs Matt's "15 min"). Encourage precision.

---

## Pydantic Schemas (carry into `inference.py`)

```python
class DesiredStateAnalysis(BaseModel):
    target_level: int = Field(description="Target colour level (1=black, 10=lightest blonde)")
    tone: str = Field(description="Target tone, e.g. 'violet/pearl', 'ash', 'beige/gold'")
    technique: str = Field(description="e.g. 'global lightening + tone', 'balayage', 'root retouch'")
    description: str = Field(description="Short professional description of the desired result")

class StartingStateAnalysis(BaseModel):
    current_level: int = Field(description="Assessed natural/current level (1=black, 10=lightest blonde)")
    description: str = Field(description="Short professional description")
    grey_percentage: int = Field(description="Estimated percentage of grey/white hair (0 if none)")
    condition: str = Field(description="healthy, slightly porous, damaged, dry, etc.")
    previous_colour: str = Field(description="Visible signs of previous colour work, or 'none'")

class FormulationStep(BaseModel):
    step_name: str = Field(description="e.g. 'Lightener', 'Toner', 'Highlift'")
    product: str = Field(description="Exact product and shade codes")
    developer: str = Field(description="Developer used with volume")
    ratio: str = Field(description="Developer to colour ratio")
    amounts: str = Field(description="Exact amounts in g/ml")
    processing_time: str = Field(description="Time with visual checkpoints")
    application_notes: str = Field(description="Where to apply, order, what to avoid")

class HairFormulation(BaseModel):
    steps: list[FormulationStep]
    colour_theory: str = Field(description="WHY this works — underlying pigment + neutralisation")
    warnings: str = Field(description="Risks or things the stylist must watch for")
```

---

## Gradio App Architecture

### Flow

Multi-step wizard, not a chat. Each step maps to a UI state.

```
[Step 1-2: Desired Look]  →  [Step 3-4: Starting State]  →  [Step 5: Preview]  →  [Step 6: Formulation + Rating]  →  [Step 7: CTA]
```

Use `gr.Blocks` with `gr.State` to carry the session through steps. Hide/show sections as user progresses.

### Key UI components per step

**Steps 1-2 — Desired Look:**
- `gr.Textbox` for client description (required)
- `gr.Image` upload for reference photo (optional)
- Submit → shows AI analysis → stylist confirms or edits
- Editable output fields: `gr.Number` (level), `gr.Textbox` (tone, technique, description)

**Steps 3-4 — Starting State:**
- `gr.Image` upload for client photo (required)
- `gr.Textbox` for stylist notes (optional)
- `gr.Checkbox` for photo consent
- Submit → shows AI analysis → stylist confirms or edits

**Step 5 — Preview:**
- Auto-triggered once steps 1-4 confirmed
- Shows generated image (or fallback text if gen fails)
- Disclaimer: "This is an approximation only."
- Confirm → proceed. Reject → back to step 1.

**Step 6 — Formulation:**
- Auto-triggered once preview confirmed
- Formulation steps in readable layout (not raw JSON)
- Colour theory reasoning displayed prominently
- Thumbs up / thumbs down
- `gr.Textbox` for stylist feedback notes

**Step 7 — CTA:**
- "Would you like to hear about product updates?"
- `gr.Textbox` for email or mobile
- Submit → save session → thank you / reset

### Gradio UX guidelines
- **Mobile-first** — colourists will use this on their phone at the basin or chair. Single-column layout. Large touch targets (minimum 44px). No horizontal scrolling. Inputs and buttons must be thumb-reachable.
- **Vertical flow** — stack everything. No side-by-side columns that break on narrow screens. Image uploads should be full-width.
- **Guided flow** — not a chatbot. Don't use `gr.ChatInterface`.
- **Immediate results** — show spinner during API calls, no unnecessary delays.
- **Dark theme** — `gr.themes.Monochrome()` as per TenderTrawl.
- **Hide footer** — same CSS trick as TenderTrawl.
- **Minimal text** — colourists are standing, glancing at a phone. Labels should be short. Formulation output should be scannable (bold product names, clear step numbers), not paragraphs.
- **Camera access** — `gr.Image(sources=["webcam", "upload"])` so the stylist can snap a photo directly from the phone camera, not just upload from gallery.

### Mobile-first CSS (extend TenderTrawl's CSS)

```python
CSS = """
.gradio-container { max-width: 480px !important; margin: auto !important; padding: 0.5rem !important; }
footer { display: none !important; }
.message-buttons { display: none !important; }
/* Large touch targets */
button { min-height: 48px !important; font-size: 1rem !important; }
input, textarea { font-size: 16px !important; }  /* prevents iOS zoom on focus */
/* Full-width images */
.image-container { width: 100% !important; }
"""
```

---

## Logging & Persistent Storage

### Per-session data to capture

```python
session = {
    'session_id': str(uuid4()),
    'timestamp': datetime.utcnow().isoformat(),
    'desired_state': desired.model_dump(),
    'starting_state': starting.model_dump(),
    'preview_generated': True | False,
    'formulation': formulation.model_dump(),
    'rating': 'thumbs_up' | 'thumbs_down',
    'stylist_notes': '...',
    'email': '...',
    'consent_to_save_photo': True | False,
}
```

### Storage — Modal Volume (`astroshade-logs`)

Same pattern as TenderTrawl:
- Session JSON: `/logs/sessions/{session_id}.json`
- Uploaded images (if consent given): `/logs/images/{session_id}_desired.png`, `_start.png`
- Generated previews: `/logs/images/{session_id}_preview.png`

```python
volume = modal.Volume.from_name("astroshade-logs", create_if_missing=True)
```

### Why this matters
- **Demand signal:** Captured emails = people who want more
- **Evaluation:** Ratings + notes = how good/bad are the formulations
- **Training data:** Confirmed states + corrections = future fine-tuning (with consent)

---

## Modal Deployment

### `deploy.py` — adapted from TenderTrawl

```python
import modal

app = modal.App("astroshade")

volume = modal.Volume.from_name("astroshade-logs", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "fastapi[standard]",
        "gradio~=5.7",
        "requests",
        "google-genai",
        "Pillow",
        "pydantic",
        "python-dotenv",
    )
    .add_local_file("app/app.py", "/root/app.py")
    .add_local_file("app/inference.py", "/root/inference.py")
    .add_local_dir("app/prompts", "/root/prompts")
)


@app.function(
    image=image,
    max_containers=1,
    volumes={"/root/logs": volume},
    secrets=[modal.Secret.from_name("gemini-secret")],
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    import sys
    sys.path.insert(0, "/root")
    from fastapi import FastAPI
    from gradio.routes import mount_gradio_app
    from app import create_demo
    demo = create_demo(log_dir="/root/logs")
    return mount_gradio_app(app=FastAPI(), blocks=demo, path="/")
```

### Deployment notes (lessons from TenderTrawl)
- Always include `requests` in pip_install — undeclared Gradio dependency
- `max_containers=1` for Gradio sticky sessions
- `modal.Volume` for persistent logging across restarts
- Modal doesn't see local filesystem — use `add_local_file` / `add_local_dir`
- Prompts go via `add_local_dir("app/prompts", "/root/prompts")`
- The Modal secret `gemini-secret` must have `GEMINI_API_KEY` set
- `modal serve app/deploy.py` for dev with hot-reload
- `modal deploy app/deploy.py` for production
- Run from project root (not from `app/`)

---

## Test Cases (from Matt)

All cases use **Goldwell** products. Each includes a known-good formulation.

### Case 1: "Scandi Blonde" — Global Lightening & Tone

- **Desired:** Clean, icy, level 10 platinum blonde. No yellow.
- **Client says:** "I want to be super bright blonde all over, like an icy Scandi blonde. I hate seeing any yellow or gold."
- **Starting:** Level 7, virgin, healthy.
- **Known-good:**
  - Lightener: SilkLift Strong + 6% (20 vol) + 3 pumps Conditioning Serum. 1:1 (35g:35ml). Up to 45 min.
  - Toner: Colorance 10V + 10P (1:1). Lotion 2%. 2:1 (40ml:10ml:10ml). 15 min.
- **Why:** 20 vol lifts level 7 three levels. Pale yellow at 10. V neutralises yellow. P adds icy finish.
- **AI divergence:** Returned 1:2 ratio for lightener (should be 1:1). Toner was correct.

### Case 2: Brassy Balayage Correction — Glaze/Toning

- **Desired:** Creamy, cool-toned level 8/9 lived-in blonde.
- **Client says:** "My balayage has gone super brassy and orange. I want it cooler, creamy, expensive-looking, but keep my natural root."
- **Starting:** Level 6 roots. Grown-out balayage, mids/ends level 8/9, gold/copper. Porous ends.
- **Known-good:**
  - Toner: Colorance 8BA + 9NA (1:1). Lotion 2%. 2:1 (60ml:15ml:15ml). 15-20 min.
- **Why:** Colorance won't lift — roots untouched. 8BA neutralises orange. 9NA neutralises yellow.

### Case 3: Grey Blending with Highlift — Root Retouch

- **Desired:** Clean, bright, neutral-cool blonde at root, blending with level 10 ends.
- **Client says:** "Cover the greys, stay bright blonde, no bleach on scalp. As cool as possible."
- **Starting:** Level 7, 40% grey. Ends previously level 10. Slightly dry.
- **Known-good:**
  - Highlift: Topchic 11N + 11A (1:1). 12% (40 vol). 1:2 (30g+30g:120ml). 45 min strict.
  - Regrowth only. Do NOT overlap onto level 10 ends.
- **Why:** Highlift needs 12% and 1:2 for max lift. 11A neutralises warmth. 11N provides grey opacity.

---

## Sprint Plan — Tonight's Build

### Goal
Working Gradio app deployed on Modal. Public URL. Matt can use it on his phone for a week.

### Build order

1. **`app/prompts/`** — 4 prompt text files. Formulation first (most important), then image gen (most broken), then desired/starting state (already working).
2. **`app/inference.py`** — Extract notebook functions. Load prompts from files. Gemini client init from env var.
3. **`app/app.py`** — Gradio `gr.Blocks` multi-step wizard. Dark theme. Mobile-first single-column layout. Session state + logging.
4. **Test locally** — `python app/app.py` — case 1 end-to-end.
5. **`app/deploy.py`** — Modal deployment. TenderTrawl pattern. `astroshade-logs` volume.
6. **`modal serve app/deploy.py`** — Test on Modal.
7. **`modal deploy app/deploy.py`** — Ship it.

### Definition of done
- Public URL works on a phone browser (mobile-first)
- All 7 steps functional
- Image gen produces a preview (even if imperfect)
- Formulation includes colour theory reasoning
- Stylist can rate and leave feedback
- Email capture works
- Sessions logged to Modal Volume

---

## Builder Context

**Geoff Pidcock** — AI operations consultant (MMetrics.ai), ex-Atlassian, ex-Salesforce, MBA. Moderate Python programmer. Dev environment: WSL on local machine with Claude Code CLI as primary IDE workflow, GitHub Codespaces on Samsung Galaxy Tab S9 for mobile dev, exploring Codex for async tasks. Prefers copy-pasteable code blocks over downloadable files. This is prototype #3 of 42 in 2026.

## Key Learnings

- Working prototypes beat wireframes for surfacing UX gaps
- Guided flows beat chatbots for structured tasks — don't use `gr.ChatInterface`
- **Mobile-first, not tablet-first** — colourists use their phones at the chair, not an iPad on a stand. Single-column, vertical scroll, camera-first image input.
- Formulation output must include colour theory reasoning — builds professional trust
- Image gen prompt must explicitly state "global" = root-to-tip, same level everywhere — dark roots persist otherwise
- Few-shot examples from known-good formulations dramatically improve output quality
- System prompts in separate `.txt` files = faster iteration
- Goldwell shade numbers must be real — hallucinated shades kill credibility instantly
- TenderTrawl's Modal deployment pattern works — reuse it
- Claude Code CLI on WSL is the fastest dev loop for this kind of build; Codex useful for async refactoring tasks