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

**Matt Smith** — 26-year-old founder and dad. Matt stepped back from running his own salon business because he sees AI transforming the industry and wants to be ahead of it. He now rents a chair while building Alloura, his vision for AI-assisted hair colour consultations. The core use case, the user journey, the test cases, and the domain expertise driving this prototype are all Matt's. He has real courage — he left the security of his own business to bet on a future he believes in.

## The Problem

Even experienced colourists regularly ask each other for second opinions on formulas, ratios, and techniques. Outcomes vary depending on who performs the service. When a client's regular stylist goes on leave or moves salons, the client can lose their colour result. The goal is to remove guesswork from colour formulation and produce consistent, repeatable results across different stylists.

## User Journey (Matt's Vision)

1. Client describes or references a desired colour look
2. System shows a visual approximation of that result
3. Stylist confirms the direction with the client
4. AI generates the recommended colour formulation based on the salon's product range, providing reasoning/colour theory

## additional steps (Geoff's Expertise)
5. Stylist rates the recommendation, including an honest question "are you interested in learning more about this product" (email or mobile capture). This provides feedback and the opportunity to improve through in context learning or other mechanisms. This also starts building a demand database.
6. (stretch) Client rates the outcome. Ideally a photo of the final look is provided. This provides further learning/improvement opportunities, especially if compared against #2.

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI API | Gemini (free credits) | Single API for vision, image gen, and formulation reasoning |
| Product range | Goldwell only (for now) | All 3 test cases use Goldwell; bake catalogue into system prompt |
| Image generation | Attempt it (risky) | If it works, it's the wow moment. Kill by 11:30am if it's not working |
| Deployment | TBD at 12pm check-in | Gradio+Modal is safe fallback; exploring Vercel/Next.js for better UX |
| Dev approach | Notebook-driven | Validate AI capabilities in Jupyter before building any UI |

Please reference the official google SDK documentation when prototyping - https://googleapis.github.io/python-genai/ and https://googleapis.github.io/js-genai/release_docs/index.html

## Project Structure

```
astroshade/
├── agents.md              # This file — project context and handover
├── .venv/                 # Python virtual environment
├── notebooks/             # Jupyter notebooks for testing and development
│   ├── 00_setup.ipynb          # confirm API readiness and structure test cases
│   ├── 01_formulation.ipynb    # Test formulation reasoning against known-good answers
│   ├── 02_image_gen.ipynb      # Test visual approximation generation
│   └── 03_vision_input.ipynb   # Test interpretation of reference photos
├── testcases/             # Client-provided test data (Matt's IP)
│   ├── matt-smith-testcases.pptx       # Original case studies deck
│   └── 3.5-colorcircle-topchic-big.jpg # GoldWell reference color circle
└── app/                   # Web application code and deployment config
    └── (TBD after 12pm)
```

## Test Cases (from Matt)

All cases use **Goldwell** products. Each includes a known-good formulation — the AI must get close to these or the demo fails.

### Case 1: "Scandi Blonde" — Global Lightening & Tone

- **Desired look:** Clean, icy, level 10 platinum blonde. Cool, reflective finish. No yellow.
- **Client language:** "I want to be super bright blonde all over, like an icy Scandi blonde. I hate seeing any yellow or gold."
- **Starting point:** Level 7 (Medium Blonde), virgin hair, healthy condition.
- **Complication:** Lifting from 7 to 10 exposes strong pale yellow underlying pigment requiring aggressive lifting and precise neutralisation.
- **Products:** Goldwell SilkLift (Lightener), Goldwell Colorance (Toner)
- **Known-good formulation:**
  - Lightener: SilkLift Strong + 6% (20 vol) developer + 3 pumps Intensive Conditioning Serum. Ratio 1:1 (35g powder : 35ml developer).
  - Toner: Colorance 10V + 10P (1:1). Developer: Colorance Lotion 2%. Ratio 2:1 (40ml lotion : 10ml 10V : 10ml 10P).
  - Processing: Lightener up to 45 min (visual check until pale yellow). Toner 15 min.
  - Application: 1cm off scalp through ends first, roots once mids reach level 9. Rinse, shampoo, towel dry, toner at basin.
- **Why it works:** 20 vol safely lifts virgin level 7 three levels. At level 10, underlying pigment is pale yellow. V (Violet) neutralises yellow. P (Pearl, blue-violet undertone) adds icy reflective finish.

### Case 2: Brassy Balayage Correction — Glaze/Toning

- **Desired look:** Creamy, cool-toned level 8/9 lived-in blonde. Expensive-looking.
- **Client language:** "My balayage has gone super brassy and orange from the sun and washing. I want it cooler, creamy, and expensive-looking, but I don't want to lose my natural root."
- **Starting point:** Level 6 (Dark Blonde) roots. Grown-out balayage, mids/ends faded to uneven level 8/9 with heavy gold and slight copper (orange). Slightly porous ends.
- **Complication:** Neutralise orange/yellow on mid-lengths without hot root or shifting the natural level 6 base.
- **Products:** Goldwell Colorance (Demi-permanent)
- **Known-good formulation:**
  - Toner: Colorance 8BA + 9NA (1:1). Developer: Colorance Lotion 2%. Ratio 2:1 (60ml lotion : 15ml 8BA : 15ml 9NA).
  - Processing: 15–20 min.
  - Application: Global on damp hair at basin, focus on brassiest transition bands first, pull through porous ends for final 5–10 min to prevent over-toning.
- **Why it works:** Colorance is acidic demi-permanent — won't lift natural hair, so level 6 roots stay untouched (no hot roots). 8BA (Smoky Beige) contains Blue/Ash to neutralise orange/copper. 9NA (Natural Ash) neutralises yellow and provides natural balance so hair doesn't grab grey or muddy.

### Case 3: Grey Blending with Highlift — Root Retouch

- **Desired look:** Clean, bright, neutral-cool blonde at root, blending with existing lightened ends.
- **Client language:** "I need my roots done. I want to stay really bright blonde, cover these greys coming through, but I don't want bleach on my scalp. Keep it as cool as possible."
- **Starting point:** Level 7 (Medium Blonde) with 40% scattered grey. Mids/ends previously coloured to level 10 neutral blonde. Normal at root, slightly dry on ends.
- **Complication:** Maximum lift to match level 10 ends + opacity to blend 40% grey, without using lightener.
- **Products:** Goldwell Topchic (Highlift 11 Series)
- **Known-good formulation:**
  - Highlift: Topchic 11N + 11A (1:1). Developer: Topchic 12% (40 vol). Ratio 1:2 (30g 11N + 30g 11A : 120ml 12% developer).
  - Processing: 45 min strictly (do not cut short).
  - Application: Regrowth only, cross-check sections. Do NOT overlap onto level 10 ends (breakage risk).
- **Why it works:** Highlift requires 12% and 1:2 ratio to maximise lifting curve and minimise deposit. At level 7, underlying pigment is yellow-orange. 11A (Ash) neutralises warmth. 11N (Natural) provides background dye required to cover unpigmented hair — highlift ash alone lacks opacity for grey blending.

## Sprint Schedule — Build Day

_COMMENT:_ some ideas, in reality we have two sprints, with the first wiring things together, and the second building a tablet ready demo flow.
| Time | Activity | Success Criteria |
|------|----------|-----------------|
| 09:30-12:00 | **Formulation engine** — system prompt + Gemini, validate against all 3 test cases | AI output matches known-good formulations closely enough that Matt would say "yeah, that's right" |
| 9:30–11:30 | **Image generation** — visual approximation of target colour result | Produces something a colourist would show a client. Kill by 11:30 if not working |
| 11:30–12:00 | **Wire together** — end-to-end flow even if rough | Describe look → see visual → get formulation, running in notebook |
| 12:00 | **Check-in with Matt** (WhatsApp) + framework decision | Confirm test cases, show progress, decide on UI stack |
| 12:00–15:00 | **UI and deployment** | Working web app on a public URL, tablet-friendly |
| 15:00–16:00 | **Buffer** — end-to-end test with all 3 cases | Everything works, URL is shareable |
| 16:00 | **Demo with Matt** (video call) | |

## Post-Demo Questions

- How long to keep the demo live (target: 1 week minimum)
- Is this compelling enough to attract investment?
- What's the realistic path to market — iOS app? Web app? Salon software integration?
- What (if anything) Geoff could honestly help with beyond this prototype

## Builder Context

**Geoff Pidcock** — AI operations consultant (MMetrics.ai), ex-Atlassian, ex-Salesforce, MBA. This is the first "partner" prototype under a "42 prototypes in 2026" commitment. Moderate Python programmer. Primary dev environment today: WSL. Prefers notebook-driven, baby-steps development.

## Key Learnings & Principles

- Working prototypes beat wireframes for surfacing UX gaps and testing model capabilities
- Demo UX matters: bots that ask clarifying questions instead of immediately delivering results kill momentum
- The formulation output must include colour theory reasoning ("why this works"), not just shade numbers — that's what builds trust with a professional
- The visual approximation should show "what the target colour looks like" (generic/reference), NOT "what this specific client would look like with new hair" (too hard, too risky) - *comment* I think we should still try the specific client hair representation as it's fun. let's try for both?
- Goldwell shade numbers must be real. If the AI hallucinates shades that don't exist, the demo is dead on arrival with a professional colourist