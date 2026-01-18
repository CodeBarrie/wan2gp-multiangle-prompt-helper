import gradio as gr
import traceback
from shared.utils.plugins import WAN2GPPlugin

PlugIn_Name = "Multi-Angle Prompt Helper"
PlugIn_Id = "MultiAnglePromptHelperInjected"

TRIGGER = "<sks>"

# IMPORTANT: These are now the canonical tokens we output.
# Based on your testing: degrees/factors must appear in the prompt text.
AZIMUTH = [
    "front view (0°)",
    "front-right quarter view (45°)",
    "right side view (90°)",
    "back-right quarter view (135°)",
    "back view (180°)",
    "back-left quarter view (225°)",
    "left side view (270°)",
    "front-left quarter view (315°)",
]

ELEVATION = [
    "low-angle shot (-30°)",
    "eye-level shot (0°)",
    "elevated shot (30°)",
    "high-angle shot (60°)",
]

DISTANCE = [
    "close-up (×0.6)",
    "medium shot (×1.0)",
    "wide shot (×1.8)",
]

# Now labels == tokens, so choices are directly these lists.
AZIMUTH_LABELS = AZIMUTH
ELEVATION_LABELS = ELEVATION
DISTANCE_LABELS = DISTANCE

# Official-style 96 list using degree/factor-inclusive tokens.
ALL_96_PROMPTS = [
    f"{TRIGGER} {az} {el} {dist}"
    for dist in DISTANCE
    for el in ELEVATION
    for az in AZIMUTH
]

CANONICAL_LOOKUP = {
    (az, el, dist): f"{TRIGGER} {az} {el} {dist}"
    for az in AZIMUTH
    for el in ELEVATION
    for dist in DISTANCE
}

REFERENCE_POSE = f"{TRIGGER} front view (0°) eye-level shot (0°) medium shot (×1.0)"


class MultiAnglePromptHelperInjected(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PlugIn_Name
        self.version = "1.4.0"
        self.description = "Injects a prompt helper into the Video Generator UI. Outputs degree/factor text."

    def setup_ui(self):
        # In your build, post_ui_setup gets only requested components.
        for cid in [
            "loras_choices",
            "loras_multipliers",
            "loras",
            "lora",
            "prompts",
            "prompt",
            "prompt_lines",
            "prompts_box",
            "positive_prompt",
            "prompt_text",
            "prompt_box",
            "advanced_settings",
            "generation_settings",
            "model_settings",
            "resolution",
        ]:
            try:
                self.request_component(cid)
            except Exception:
                pass
        return None

    def post_ui_setup(self, components: dict) -> dict:
        try:
            anchor_candidates = [
                "loras_multipliers",
                "loras_choices",
                "loras",
                "lora",
                "advanced_settings",
                "generation_settings",
                "model_settings",
                "resolution",
                "prompts",
                "prompt",
            ]
            anchor_id = next((k for k in anchor_candidates if k in components), None)
            if anchor_id is None:
                print("[MultiAngleInjected] No anchor found. Skipping injection.")
                return {}

            prompt_candidates = [
                "prompts",
                "prompt_lines",
                "prompts_box",
                "prompt",
                "positive_prompt",
                "prompt_text",
                "prompt_box",
            ]
            prompt_id = next((k for k in prompt_candidates if k in components), None)
            prompt_comp = components.get(prompt_id) if prompt_id else None

            def strip_trigger(s: str) -> str:
                s = (s or "").strip()
                if s.startswith(f"{TRIGGER} "):
                    return s.replace(f"{TRIGGER} ", "", 1)
                if s == TRIGGER:
                    return ""
                return s

            def canonical_from_parts(az: str, el: str, dist: str, include_trigger: bool) -> str:
                az = (az or "").strip()
                el = (el or "").strip()
                dist = (dist or "").strip()
                canonical = CANONICAL_LOOKUP.get((az, el, dist), f"{TRIGGER} {az} {el} {dist}".strip())
                return canonical if include_trigger else strip_trigger(canonical)

            def build_batch(mode: str, az: str, el: str, dist: str, include_trigger: bool) -> str:
                mode = (mode or "Single").strip()

                if mode == "Single":
                    return canonical_from_parts(az, el, dist, include_trigger)

                if mode == "8-view sweep (same elevation + distance)":
                    return "\n".join([canonical_from_parts(a, el, dist, include_trigger) for a in AZIMUTH])

                if mode == "4-elevation sweep (same azimuth + distance)":
                    return "\n".join([canonical_from_parts(az, e, dist, include_trigger) for e in ELEVATION])

                if mode == "3-distance sweep (same azimuth + elevation)":
                    return "\n".join([canonical_from_parts(az, el, d, include_trigger) for d in DISTANCE])

                if mode == "All 96 prompts":
                    if include_trigger:
                        return "\n".join(ALL_96_PROMPTS)
                    return "\n".join([strip_trigger(p) for p in ALL_96_PROMPTS])

                return canonical_from_parts(az, el, dist, include_trigger)

            def format_as_prompt_blocks(text: str, blank_lines_between: int) -> str:
                raw = (text or "").strip()
                if not raw:
                    return ""
                lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
                if not lines:
                    return ""
                gap = "\n" * (int(blank_lines_between) + 1)  # 1 -> "\n\n"
                return gap.join(lines)

            def apply_to_prompts_box(existing_prompt: str, new_text: str, mode: str, blank_lines_between: int) -> str:
                existing_prompt = existing_prompt or ""
                new_text = format_as_prompt_blocks(new_text, blank_lines_between)
                if not new_text:
                    return existing_prompt

                mode = (mode or "Append").strip()
                if mode == "Replace":
                    return new_text

                if not existing_prompt.strip():
                    return new_text

                gap = "\n" * (int(blank_lines_between) + 1)
                return existing_prompt.rstrip() + gap + new_text

            def create_ui():
                with gr.Accordion("Multi-Angle Prompt Helper", open=False) as acc:
                    gr.Markdown(
                        "Outputs angle/elevation/distance with degrees and factors included.\n\n"
                        f"Reference pose: `{REFERENCE_POSE}`"
                    )

                    include_trigger = gr.Checkbox(label=f"Include {TRIGGER} trigger token", value=True)

                    with gr.Tab("Builder"):
                        with gr.Row():
                            az = gr.Dropdown(label="Azimuth", choices=AZIMUTH_LABELS, value=AZIMUTH_LABELS[0])
                            el = gr.Dropdown(label="Elevation", choices=ELEVATION_LABELS, value=ELEVATION_LABELS[1])
                            dist = gr.Dropdown(label="Distance", choices=DISTANCE_LABELS, value=DISTANCE_LABELS[1])

                        builder_out = gr.Textbox(label="Builder output", lines=8, show_copy_button=True, value=REFERENCE_POSE)

                        def builder_make(a, e, d, trig):
                            return canonical_from_parts(a, e, d, trig)

                        for comp in (az, el, dist, include_trigger):
                            comp.change(builder_make, inputs=[az, el, dist, include_trigger], outputs=[builder_out])

                        def set_reference(trig):
                            base = REFERENCE_POSE if trig else strip_trigger(REFERENCE_POSE)
                            return AZIMUTH_LABELS[0], ELEVATION_LABELS[1], DISTANCE_LABELS[1], base

                        with gr.Row():
                            gr.Button("Set reference pose").click(set_reference, inputs=[include_trigger], outputs=[az, el, dist, builder_out])
                            gr.Button("Clear").click(lambda: "", outputs=[builder_out])

                    with gr.Tab("Presets (96)"):
                        preset = gr.Dropdown(label="Pick a preset (type to search)", choices=ALL_96_PROMPTS, value=REFERENCE_POSE)
                        preset_out = gr.Textbox(label="Preset output", lines=8, show_copy_button=True, value=REFERENCE_POSE)

                        def preset_fmt(p, trig):
                            p = (p or "").strip()
                            if not p:
                                return ""
                            return p if trig else strip_trigger(p)

                        preset.change(preset_fmt, inputs=[preset, include_trigger], outputs=[preset_out])
                        include_trigger.change(preset_fmt, inputs=[preset, include_trigger], outputs=[preset_out])

                    with gr.Tab("Batch"):
                        batch_mode = gr.Radio(
                            label="Batch mode",
                            choices=[
                                "Single",
                                "8-view sweep (same elevation + distance)",
                                "4-elevation sweep (same azimuth + distance)",
                                "3-distance sweep (same azimuth + elevation)",
                                "All 96 prompts",
                            ],
                            value="8-view sweep (same elevation + distance)",
                        )

                        batch_out = gr.Textbox(label="Batch output", lines=12, show_copy_button=True)

                        with gr.Row():
                            baz = gr.Dropdown(label="Azimuth base", choices=AZIMUTH_LABELS, value=AZIMUTH_LABELS[0])
                            bel = gr.Dropdown(label="Elevation base", choices=ELEVATION_LABELS, value=ELEVATION_LABELS[1])
                            bdi = gr.Dropdown(label="Distance base", choices=DISTANCE_LABELS, value=DISTANCE_LABELS[1])

                        def batch_make(mode, a, e, d, trig):
                            return build_batch(mode, a, e, d, trig)

                        for comp in (batch_mode, baz, bel, bdi, include_trigger):
                            comp.change(batch_make, inputs=[batch_mode, baz, bel, bdi, include_trigger], outputs=[batch_out])

                        gr.Button("Generate now").click(batch_make, inputs=[batch_mode, baz, bel, bdi, include_trigger], outputs=[batch_out])

                    gr.Markdown("Apply to main Prompts box")
                    apply_mode = gr.Radio(label="Apply mode", choices=["Append", "Replace"], value="Append")
                    blank_lines_between = gr.Slider(label="Blank lines between prompts", minimum=1, maximum=3, value=1, step=1)
                    apply_source = gr.Radio(label="Apply which output?", choices=["Builder", "Preset", "Batch"], value="Batch")

                    preview = gr.Textbox(label="Preview (this is what will be inserted)", lines=10, show_copy_button=True)

                    def pick_text(src, b, p, ba, blanks):
                        raw = b
                        if src == "Preset":
                            raw = p
                        elif src == "Batch":
                            raw = ba
                        return format_as_prompt_blocks(raw, int(blanks))

                    for comp in (apply_source, blank_lines_between,):
                        comp.change(pick_text, inputs=[apply_source, builder_out, preset_out, batch_out, blank_lines_between], outputs=[preview])
                    for comp in (builder_out, preset_out, batch_out):
                        comp.change(pick_text, inputs=[apply_source, builder_out, preset_out, batch_out, blank_lines_between], outputs=[preview])

                    if prompt_comp is not None:
                        gr.Button("Apply to Prompts box").click(
                            apply_to_prompts_box,
                            inputs=[prompt_comp, preview, apply_mode, blank_lines_between],
                            outputs=[prompt_comp],
                        )
                    else:
                        gr.Markdown("Prompts box not found. Copy from Preview and paste manually.")

                return acc

            self.insert_after(target_component_id=anchor_id, new_component_constructor=create_ui)
            print(f"[MultiAngleInjected] Injected after '{anchor_id}'. Prompts id: '{prompt_id}'")

        except Exception:
            print("[MultiAngleInjected] ERROR during post_ui_setup:")
            traceback.print_exc()

        return {}


Plugin = MultiAnglePromptHelperInjected
