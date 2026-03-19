# Astroshade

What if AI could help hair stylists plan and deliver fantastic hair colour changes to their clients?

This is a partner project with Matt Smith. The name is inspired by the Jetsons and the Galaxy Salon, which dreamed first of a machine that could help you explore and change your hair easily - [link](https://share.google/6elZMp4LCZBwu1NOu).

[Prototype #3 of 42](https://mmetrics.ai) — mmetrics.ai

## The Hypothesis

Can foundation models reason about hair colour formulation — specifically **Goldwell** product lines — accurately enough that a professional colourist would trust the output mid-consultation?

This is a **tech readiness prototype**, not a final product. We're validating whether AI can map a client's desired look and starting point to a safe, chemically sound Goldwell formula with colour theory reasoning.

## How It Works

A guided 7-step consultation flow built for mobile use at the salon chair:

1. **Desired look** — Client describes what they want (text and/or reference photo)
2. **Confirm** — AI analyses the input, stylist confirms or corrects the structured description
3. **Starting state** — Stylist photographs the client's current hair
4. **Confirm** — AI analyses the photo, stylist confirms or corrects
5. **Preview** — AI generates a visual preview of the client with the new colour *(stretch — quality varies)*
6. **Formulation** — AI recommends a Goldwell formulation with colour theory reasoning. Stylist rates it and leaves feedback.
7. **Email capture** — Optional CTA for product updates

## Project Structure

```
astroshade/
├── app/
│   ├── app.py                   # Gradio UI — multi-step consultation wizard
│   ├── inference.py             # Gemini API calls: analyse, preview, formulate
│   ├── deploy.py                # Modal deployment harness
│   └── prompts/                 # System prompts + few-shot examples
│       ├── a_desired_state.txt / .json
│       ├── b_starting_state.txt / .json
│       ├── c_preview.txt / .json
│       └── d_formulation.txt / .json
│
├── notebooks/                   # Jupyter notebooks (validation, not deployed)
│   ├── 00_setup.ipynb           # API readiness
│   ├── 01_testcases_*.ipynb     # Formulation test cases
│   └── 02_user_journey.ipynb    # Step-by-step flow validation
│
├── testcases/                   # Matt's test data (not deployed)
│   └── structured/              # JSON + images per case
│
├── agents.md                    # Full project context and handover doc
├── todo.md                      # Build plan and progress
└── .env                         # GEMINI_API_KEY (gitignored)
```

## Local Development

### Prerequisites
- Python 3.12
- A Gemini API key (paid — free tier has no image generation quota)

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install python-dotenv google-genai Pillow pydantic "gradio~=5.7"

# Create .env with your API key
echo "GEMINI_API_KEY=your-key-here" > .env
```

### Run locally

```bash
source .venv/bin/activate
python app/app.py
```

Opens at `http://localhost:7860`. The app pre-fills with Case 1 (Scandi Blonde) for quick testing. Session logs save to `app/logs/`.

### Run notebooks

```bash
source .venv/bin/activate
jupyter notebook
```

Notebooks are in `notebooks/` — start with `00_setup.ipynb` to confirm API connectivity.

## Deployment (Modal)

### Prerequisites
- Modal account and CLI authenticated (`pip install modal && modal setup`)
- Gemini API key stored as a Modal secret

### Deploy

```bash
# Dev server with hot-reload
modal serve app/deploy.py

# Production deployment
modal deploy app/deploy.py
```

Session data (JSON + images with consent) persists to the `astroshade-logs` Modal Volume.

## Technical Stack

| Component | Choice |
|-----------|--------|
| AI API | Gemini (`gemini-2.5-flash` for text/vision, `gemini-2.5-flash-image` for preview) |
| Product range | Goldwell only — baked into system prompts with few-shot examples |
| UI | Gradio `gr.Blocks` — mobile-first, dark theme, guided wizard (not a chatbot) |
| Hosting | Modal — serverless, persistent volume for logs |
| Structured output | Pydantic schemas enforced via Gemini's `response_schema` |

## Known Limitations

- **Prototype quality** — Formulations are verbose compared to a real colourist's shorthand. Prompt engineering can tighten this.
- **No product catalogue validation** — Shade codes are guided by the system prompt but not validated against a real Goldwell database. A professional colourist should always verify.
- **Preview generation** — Image editing quality varies. Dark roots may persist on "global/all-over" looks. The preview is an approximation, not a guarantee.
- **Goldwell only** — The system prompts and few-shot examples are anchored to Goldwell products. Adapting to other brands requires new prompts and test cases.

## Credits

- **Matt Smith** — Domain expertise, test cases, user journey design
- **Geoff Pidcock** — AI engineering, prototype build ([mmetrics.ai](https://mmetrics.ai))
