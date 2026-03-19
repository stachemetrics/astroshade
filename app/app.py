"""
Astroshade — Gradio multi-step hair colour consultation wizard.

Factory function ``create_demo`` returns a ``gr.Blocks`` app.
Modal's deploy.py calls it with a log directory for session persistence.
"""

import datetime
import json
import os
import shutil
import uuid

import gradio as gr

from inference import (
    DesiredStateAnalysis,
    HairFormulation,
    StartingStateAnalysis,
    analyse_desired_state,
    analyse_starting_state,
    generate_formulation,
    generate_preview,
)

# ---------------------------------------------------------------------------
# Theme & CSS
# ---------------------------------------------------------------------------

THEME = gr.themes.Monochrome()

CSS = """
.gradio-container { max-width: 480px !important; margin: auto !important; padding: 0.5rem !important; }
footer { display: none !important; }
.message-buttons { display: none !important; }
button { min-height: 48px !important; font-size: 1rem !important; }
input, textarea { font-size: 16px !important; }
.image-container { width: 100% !important; }
"""

# Default client description from Case 1
DEFAULT_CLIENT_DESC = (
    "I want to be super bright blonde all over, like an icy Scandi blonde. "
    "I hate seeing any yellow or gold."
)


# ---------------------------------------------------------------------------
# Helper: format formulation as readable Markdown
# ---------------------------------------------------------------------------

def _format_formulation_md(formulation: HairFormulation) -> str:
    """Render a HairFormulation as scannable Markdown for mobile viewing."""
    lines: list[str] = []
    for i, step in enumerate(formulation.steps, 1):
        lines.append(f"### Step {i}: {step.step_name}")
        lines.append(f"**Product:** {step.product}")
        lines.append(f"**Developer:** {step.developer}")
        lines.append(f"**Ratio:** {step.ratio}")
        lines.append(f"**Amounts:** {step.amounts}")
        lines.append(f"**Time:** {step.processing_time}")
        lines.append(f"**Application:** {step.application_notes}")
        lines.append("")

    lines.append("---")
    lines.append("### Colour Theory")
    lines.append(formulation.colour_theory)
    lines.append("")

    if formulation.warnings:
        lines.append("---")
        lines.append("### Warnings")
        lines.append(f"**{formulation.warnings}**")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: read image file to bytes
# ---------------------------------------------------------------------------

def _read_image(filepath: str | None) -> bytes | None:
    if not filepath:
        return None
    with open(filepath, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------

def _save_session(
    log_dir: str | None,
    desired: dict,
    starting: dict,
    preview_generated: bool,
    formulation: dict,
    rating: str | None,
    stylist_notes: str,
    email: str,
    consent: bool,
    desired_image_path: str | None,
    starting_image_path: str | None,
    preview_image,
):
    """Persist session JSON and images (if consent given) to log_dir."""
    if not log_dir:
        return

    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "desired_state": desired,
        "starting_state": starting,
        "preview_generated": preview_generated,
        "formulation": formulation,
        "rating": rating,
        "stylist_notes": stylist_notes,
        "email": email,
        "consent_to_save_photo": consent,
    }

    sessions_dir = os.path.join(log_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    with open(os.path.join(sessions_dir, f"{session_id}.json"), "w") as f:
        json.dump(session, f, indent=2)

    # Save images if consent given
    if consent:
        images_dir = os.path.join(log_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        if desired_image_path and os.path.isfile(desired_image_path):
            ext = os.path.splitext(desired_image_path)[1] or ".png"
            shutil.copy2(desired_image_path, os.path.join(images_dir, f"{session_id}_desired{ext}"))
        if starting_image_path and os.path.isfile(starting_image_path):
            ext = os.path.splitext(starting_image_path)[1] or ".png"
            shutil.copy2(starting_image_path, os.path.join(images_dir, f"{session_id}_start{ext}"))
        if preview_image is not None:
            try:
                preview_image.save(os.path.join(images_dir, f"{session_id}_preview.png"))
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Callback functions
# ---------------------------------------------------------------------------

def _on_analyse_desired(client_desc, ref_image_path):
    """Step 1 submit: analyse the desired look."""
    if not client_desc.strip():
        gr.Warning("Please describe the desired look.")
        return [gr.update()] * 5  # no changes

    image_bytes = _read_image(ref_image_path)
    try:
        result = analyse_desired_state(client_notes=client_desc, image_bytes=image_bytes)
    except Exception as e:
        gr.Warning(f"Analysis failed: {e}")
        return [gr.update()] * 5

    return [
        gr.update(visible=True),   # desired_results_col
        result.target_level,
        result.tone,
        result.technique,
        result.description,
    ]


def _on_confirm_desired(target_level, tone, technique, description, ref_image_path, state):
    """Step 2 confirm: store DesiredStateAnalysis and show step 3-4."""
    desired = DesiredStateAnalysis(
        target_level=int(target_level),
        tone=tone,
        technique=technique,
        description=description,
    )
    state["desired"] = desired.model_dump()
    state["desired_obj"] = desired
    state["desired_image_path"] = ref_image_path
    return [
        state,
        gr.update(visible=False),  # hide step 1-2
        gr.update(visible=True),   # show step 3-4
    ]


def _on_analyse_starting(client_photo_path, stylist_notes):
    """Step 3 submit: analyse the starting state."""
    if not client_photo_path:
        gr.Warning("Please upload or take a photo of the client's current hair.")
        return [gr.update()] * 6

    image_bytes = _read_image(client_photo_path)
    try:
        result = analyse_starting_state(image_bytes=image_bytes, stylist_notes=stylist_notes or None)
    except Exception as e:
        gr.Warning(f"Analysis failed: {e}")
        return [gr.update()] * 6

    return [
        gr.update(visible=True),   # starting_results_col
        result.current_level,
        result.description,
        result.condition,
        result.previous_colour,
        result.grey_percentage,
    ]


def _on_confirm_starting(
    current_level, s_description, s_condition, s_previous, s_grey, consent, client_photo_path, state
):
    """Step 4 confirm: store StartingStateAnalysis, trigger preview."""
    starting = StartingStateAnalysis(
        current_level=int(current_level),
        description=s_description,
        grey_percentage=int(s_grey),
        condition=s_condition,
        previous_colour=s_previous,
    )
    state["starting"] = starting.model_dump()
    state["starting_obj"] = starting
    state["starting_image_path"] = client_photo_path
    state["consent"] = consent

    # Generate preview
    image_bytes = _read_image(client_photo_path)
    desired_obj = state.get("desired_obj")
    preview_img = None
    fallback_text = ""
    if image_bytes and desired_obj:
        preview_img = generate_preview(image_bytes=image_bytes, desired=desired_obj)
    if preview_img is None:
        fallback_text = "Preview generation unavailable. Proceeding with formulation."

    state["preview_image"] = preview_img

    return [
        state,
        gr.update(visible=False),  # hide step 3-4
        gr.update(visible=True),   # show step 5
        preview_img,
        fallback_text,
    ]


def _on_preview_retry(state):
    """Re-run preview generation."""
    image_bytes = _read_image(state.get("starting_image_path"))
    desired_obj = state.get("desired_obj")
    preview_img = None
    fallback_text = ""
    if image_bytes and desired_obj:
        preview_img = generate_preview(image_bytes=image_bytes, desired=desired_obj)
    if preview_img is None:
        fallback_text = "Preview generation unavailable. Proceeding with formulation."
    state["preview_image"] = preview_img
    return [state, preview_img, fallback_text]


def _on_preview_accept(state):
    """Step 5 accept: generate formulation."""
    desired_obj = state.get("desired_obj")
    starting_obj = state.get("starting_obj")
    try:
        formulation = generate_formulation(desired=desired_obj, starting=starting_obj)
    except Exception as e:
        gr.Warning(f"Formulation generation failed: {e}")
        return [state, gr.update(), gr.update(), gr.update()]

    state["formulation"] = formulation.model_dump()
    md = _format_formulation_md(formulation)

    return [
        state,
        gr.update(visible=False),  # hide step 5
        gr.update(visible=True),   # show step 6
        md,
    ]


def _on_change_desired(state):
    """Go back to step 1 from preview."""
    return [
        gr.update(visible=False),  # hide step 5
        gr.update(visible=True),   # show step 1-2
    ]


def _on_submit_rating(rating, feedback_notes, state):
    """Step 6 submit: store rating and show step 7."""
    state["rating"] = rating
    state["stylist_notes"] = feedback_notes
    return [
        state,
        gr.update(visible=False),  # hide step 6
        gr.update(visible=True),   # show step 7
    ]


def _on_submit_email(email, state, log_dir_state):
    """Step 7 submit: save session and show thank-you."""
    state["email"] = email
    log_dir = log_dir_state

    _save_session(
        log_dir=log_dir,
        desired=state.get("desired", {}),
        starting=state.get("starting", {}),
        preview_generated=state.get("preview_image") is not None,
        formulation=state.get("formulation", {}),
        rating=state.get("rating"),
        stylist_notes=state.get("stylist_notes", ""),
        email=email or "",
        consent=state.get("consent", False),
        desired_image_path=state.get("desired_image_path"),
        starting_image_path=state.get("starting_image_path"),
        preview_image=state.get("preview_image"),
    )

    return [
        state,
        gr.update(visible=False),  # hide step 7 form
        gr.update(visible=True),   # show thank-you
    ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_demo(log_dir: str = None) -> gr.Blocks:
    """Build and return the Gradio consultation wizard."""

    with gr.Blocks(theme=THEME, css=CSS, title="Astroshade") as demo:

        # Persistent state
        session_state = gr.State(value={})
        log_dir_state = gr.State(value=log_dir)

        gr.Markdown("# Astroshade\n**AI Hair Colour Consultation**")

        # ==================================================================
        # Steps 1-2: Desired Look
        # ==================================================================
        with gr.Column(visible=True) as step12_col:
            gr.Markdown("## What does the client want?")
            client_desc = gr.Textbox(
                label="Describe the desired look",
                value=DEFAULT_CLIENT_DESC,
                lines=3,
            )
            ref_image = gr.Image(
                label="Reference photo (optional)",
                type="filepath",
                sources=["upload", "webcam"],
            )
            analyse_desired_btn = gr.Button("Analyse desired look", variant="primary")

            with gr.Column(visible=False) as desired_results_col:
                gr.Markdown("### AI Analysis — edit if needed")
                d_target_level = gr.Number(label="Target level (1-10)", precision=0)
                d_tone = gr.Textbox(label="Tone")
                d_technique = gr.Textbox(label="Technique")
                d_description = gr.Textbox(label="Description", lines=2)
                confirm_desired_btn = gr.Button("Confirm desired look", variant="primary")

        # ==================================================================
        # Steps 3-4: Starting State
        # ==================================================================
        with gr.Column(visible=False) as step34_col:
            gr.Markdown("## Current hair state")
            client_photo = gr.Image(
                label="Photo of client's current hair",
                type="filepath",
                sources=["upload", "webcam"],
            )
            stylist_notes = gr.Textbox(label="Stylist notes (optional)", lines=2)
            consent_cb = gr.Checkbox(
                label="Client consents to photo being saved for training",
                value=False,
            )
            analyse_starting_btn = gr.Button("Analyse current hair", variant="primary")

            with gr.Column(visible=False) as starting_results_col:
                gr.Markdown("### AI Analysis — edit if needed")
                s_current_level = gr.Number(label="Current level (1-10)", precision=0)
                s_description = gr.Textbox(label="Description")
                s_condition = gr.Textbox(label="Condition")
                s_previous = gr.Textbox(label="Previous colour")
                s_grey = gr.Number(label="Grey %", precision=0)
                confirm_starting_btn = gr.Button("Confirm & generate preview", variant="primary")

        # ==================================================================
        # Step 5: Preview
        # ==================================================================
        with gr.Column(visible=False) as step5_col:
            gr.Markdown("## Preview")
            preview_image = gr.Image(label="Predicted result", interactive=False)
            preview_fallback = gr.Textbox(
                label="",
                interactive=False,
                visible=True,
            )
            gr.Markdown(
                "*This is an approximation only. Your actual results may vary.*"
            )
            with gr.Row():
                preview_accept_btn = gr.Button("Looks good — get formulation", variant="primary")
                preview_retry_btn = gr.Button("Try again")
            change_desired_btn = gr.Button("Change desired look", variant="secondary")

        # ==================================================================
        # Step 6: Formulation + Rating
        # ==================================================================
        with gr.Column(visible=False) as step6_col:
            gr.Markdown("## Formulation")
            formulation_md = gr.Markdown("")
            gr.Markdown("---")
            gr.Markdown("### Rate this recommendation")
            rating_radio = gr.Radio(
                choices=["👍", "👎"],
                label="How was this formulation?",
            )
            feedback_notes = gr.Textbox(label="Feedback / notes (optional)", lines=2)
            submit_rating_btn = gr.Button("Submit rating", variant="primary")

        # ==================================================================
        # Step 7: CTA + Save
        # ==================================================================
        with gr.Column(visible=False) as step7_col:
            with gr.Column(visible=True) as step7_form:
                gr.Markdown("## Stay in the loop")
                gr.Markdown("Would you like to hear about product updates?")
                email_input = gr.Textbox(label="Email (optional)")
                submit_email_btn = gr.Button("Finish", variant="primary")
            with gr.Column(visible=False) as step7_thanks:
                gr.Markdown("## Thank you!")
                gr.Markdown(
                    "Your consultation has been saved. "
                    "We appreciate your feedback."
                )
                new_consultation_btn = gr.Button("Start new consultation", variant="primary")

        # ==================================================================
        # Event wiring
        # ==================================================================

        # Step 1: analyse desired
        analyse_desired_btn.click(
            fn=_on_analyse_desired,
            inputs=[client_desc, ref_image],
            outputs=[desired_results_col, d_target_level, d_tone, d_technique, d_description],
        )

        # Step 2: confirm desired
        confirm_desired_btn.click(
            fn=_on_confirm_desired,
            inputs=[d_target_level, d_tone, d_technique, d_description, ref_image, session_state],
            outputs=[session_state, step12_col, step34_col],
        )

        # Step 3: analyse starting
        analyse_starting_btn.click(
            fn=_on_analyse_starting,
            inputs=[client_photo, stylist_notes],
            outputs=[starting_results_col, s_current_level, s_description, s_condition, s_previous, s_grey],
        )

        # Step 4: confirm starting + auto-trigger preview
        confirm_starting_btn.click(
            fn=_on_confirm_starting,
            inputs=[
                s_current_level, s_description, s_condition, s_previous, s_grey,
                consent_cb, client_photo, session_state,
            ],
            outputs=[session_state, step34_col, step5_col, preview_image, preview_fallback],
        )

        # Step 5: preview actions
        preview_retry_btn.click(
            fn=_on_preview_retry,
            inputs=[session_state],
            outputs=[session_state, preview_image, preview_fallback],
        )

        preview_accept_btn.click(
            fn=_on_preview_accept,
            inputs=[session_state],
            outputs=[session_state, step5_col, step6_col, formulation_md],
        )

        change_desired_btn.click(
            fn=_on_change_desired,
            inputs=[session_state],
            outputs=[step5_col, step12_col],
        )

        # Step 6: submit rating
        submit_rating_btn.click(
            fn=_on_submit_rating,
            inputs=[rating_radio, feedback_notes, session_state],
            outputs=[session_state, step6_col, step7_col],
        )

        # Step 7: submit email / finish
        submit_email_btn.click(
            fn=_on_submit_email,
            inputs=[email_input, session_state, log_dir_state],
            outputs=[session_state, step7_form, step7_thanks],
        )

        # Reset: start new consultation
        def _reset():
            return [
                {},                          # session_state
                gr.update(visible=True),     # step12_col
                gr.update(visible=False),    # step34_col
                gr.update(visible=False),    # step5_col
                gr.update(visible=False),    # step6_col
                gr.update(visible=False),    # step7_col
                gr.update(visible=True),     # step7_form
                gr.update(visible=False),    # step7_thanks
                gr.update(visible=False),    # desired_results_col
                gr.update(visible=False),    # starting_results_col
                DEFAULT_CLIENT_DESC,         # client_desc
                None,                        # ref_image
                None,                        # client_photo
                "",                          # stylist_notes
                False,                       # consent_cb
                None,                        # preview_image
                "",                          # preview_fallback
                "",                          # formulation_md
                None,                        # rating_radio
                "",                          # feedback_notes
                "",                          # email_input
                None,                        # d_target_level
                "",                          # d_tone
                "",                          # d_technique
                "",                          # d_description
                None,                        # s_current_level
                "",                          # s_description
                "",                          # s_condition
                "",                          # s_previous
                None,                        # s_grey
            ]

        new_consultation_btn.click(
            fn=_reset,
            inputs=[],
            outputs=[
                session_state,
                step12_col, step34_col, step5_col, step6_col, step7_col,
                step7_form, step7_thanks,
                desired_results_col, starting_results_col,
                client_desc, ref_image, client_photo, stylist_notes, consent_cb,
                preview_image, preview_fallback, formulation_md,
                rating_radio, feedback_notes, email_input,
                d_target_level, d_tone, d_technique, d_description,
                s_current_level, s_description, s_condition, s_previous, s_grey,
            ],
        )

    return demo


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
