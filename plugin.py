import gradio as gr
import traceback
from shared.utils.plugins import WAN2GPPlugin

PlugIn_Name = "Multi-Angle Prompt Helper"
PlugIn_Id = "MultiAnglePromptHelperInjected"

TRIGGER = "<sks>"

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

AZIMUTH_DEGREES = [0, 45, 90, 135, 180, 225, 270, 315]
ELEVATION_DEGREES = [-30, 0, 30, 60]
DISTANCE_FACTORS = [0.6, 1.0, 1.8]

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


GIZMO_HTML = """
<div id="maph-gizmo-wrap" style="width:100%;aspect-ratio:1/1;max-width:400px;margin:0 auto;position:relative;background:#0a0a0f;border-radius:12px;overflow:hidden;cursor:grab;touch-action:none;border:1px solid #333;">
<canvas id="maph-gizmo-canvas" style="width:100%;height:100%;display:block;"></canvas>
<div style="position:absolute;bottom:0;left:0;right:0;display:flex;justify-content:space-around;padding:8px 12px;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);border-top:1px solid #444;">
  <div style="text-align:center"><div style="font-size:10px;color:#888;font-family:monospace;">HORIZONTAL</div><div id="maph-h-val" style="font-size:17px;font-weight:bold;color:#ff4488;font-family:monospace;">0°</div></div>
  <div style="text-align:center"><div style="font-size:10px;color:#888;font-family:monospace;">VERTICAL</div><div id="maph-v-val" style="font-size:17px;font-weight:bold;color:#44ddaa;font-family:monospace;">0°</div></div>
  <div style="text-align:center"><div style="font-size:10px;color:#888;font-family:monospace;">ZOOM</div><div id="maph-z-val" style="font-size:17px;font-weight:bold;color:#6688ff;font-family:monospace;">1.0</div></div>
</div>
<button id="maph-gizmo-reset" style="position:absolute;bottom:8px;right:12px;background:rgba(255,255,255,0.1);border:1px solid #555;color:#aaa;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;" title="Reset">↺</button>
</div>
<script>
(function(){
const SNAP_AZ=[0,45,90,135,180,225,270,315],SNAP_EL=[-30,0,30,60],SNAP_DIST=[0.6,1.0,1.8];
const AZ_NAMES=["front","front-right","right","back-right","back","back-left","left","front-left"];
let az=0,el=0,dist=1.0,dragging=false,dragType=null,lx=0,ly=0;
const wrap=document.getElementById('maph-gizmo-wrap');
const canvas=document.getElementById('maph-gizmo-canvas');
const ctx=canvas.getContext('2d');

function resize(){
  const r=devicePixelRatio||1,rect=canvas.getBoundingClientRect();
  canvas.width=rect.width*r;canvas.height=rect.height*r;
  ctx.setTransform(r,0,0,r,0,0);draw();
}

function snap(v,arr){
  if(arr===SNAP_AZ){let v2=((v%360)+360)%360;return arr.reduce((b,a)=>Math.min(Math.abs(v2-a),360-Math.abs(v2-a))<Math.min(Math.abs(v2-b),360-Math.abs(v2-b))?a:b);}
  return arr.reduce((b,a)=>Math.abs(v-a)<Math.abs(v-b)?a:b);
}

function p3d(x,y,z,cx,cy,s){
  const ca=Math.cos(0.4),sa=Math.sin(0.4);
  const ry=y*ca-z*sa,rz=y*sa+z*ca,pr=4/(4+rz*0.3);
  return{x:cx+x*s*pr,y:cy-ry*s*pr};
}

function draw(){
  const W=canvas.getBoundingClientRect().width,H=canvas.getBoundingClientRect().height;
  const cx=W/2,cy=H*0.42,sc=W*0.28;
  ctx.clearRect(0,0,W,H);

  // grid
  ctx.strokeStyle='rgba(255,255,255,0.03)';ctx.lineWidth=0.5;
  for(let i=-3;i<=3;i++){
    let a=p3d(i*.5,0,-1.5,cx,cy,sc),b=p3d(i*.5,0,1.5,cx,cy,sc);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    a=p3d(-1.5,0,i*.5,cx,cy,sc);b=p3d(1.5,0,i*.5,cx,cy,sc);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
  }

  // orbit ring
  ctx.strokeStyle='rgba(255,68,136,0.45)';ctx.lineWidth=2.5;ctx.beginPath();
  for(let i=0;i<=64;i++){const a=i/64*Math.PI*2,p=p3d(Math.sin(a)*1.2,0,Math.cos(a)*1.2,cx,cy,sc);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}
  ctx.closePath();ctx.stroke();

  // elevation arc
  const ar=az*Math.PI/180;
  ctx.strokeStyle='rgba(68,221,170,0.5)';ctx.lineWidth=2.5;ctx.beginPath();
  for(let i=0;i<=32;i++){const e=(-45+i/32*120)*Math.PI/180,r=1.2,p=p3d(Math.sin(ar)*Math.cos(e)*r,Math.sin(e)*r,Math.cos(ar)*Math.cos(e)*r,cx,cy,sc);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}
  ctx.stroke();

  // snap dots
  const sAz=snap(az,SNAP_AZ);
  for(let i=0;i<SNAP_AZ.length;i++){
    const a=SNAP_AZ[i]*Math.PI/180,p=p3d(Math.sin(a)*1.2,0,Math.cos(a)*1.2,cx,cy,sc);
    const on=sAz===SNAP_AZ[i];
    ctx.fillStyle=on?'#ff4488':'rgba(255,68,136,0.25)';
    ctx.beginPath();ctx.arc(p.x,p.y,on?5:3,0,Math.PI*2);ctx.fill();
  }

  // subject
  const cp=p3d(0,0.15,0,cx,cy,sc);
  const gd=ctx.createRadialGradient(cp.x-3,cp.y-3,2,cp.x,cp.y,12);
  gd.addColorStop(0,'#ffdd44');gd.addColorStop(1,'#aa8800');
  ctx.fillStyle=gd;ctx.beginPath();ctx.arc(cp.x,cp.y,11,0,Math.PI*2);ctx.fill();

  // camera
  const er=el*Math.PI/180,ds=dist;
  const cam=p3d(Math.sin(ar)*Math.cos(er)*1.2*ds,Math.sin(er)*1.2*ds,Math.cos(ar)*Math.cos(er)*1.2*ds,cx,cy,sc);
  ctx.strokeStyle='rgba(255,200,50,0.25)';ctx.lineWidth=1;ctx.setLineDash([4,4]);
  ctx.beginPath();ctx.moveTo(cp.x,cp.y);ctx.lineTo(cam.x,cam.y);ctx.stroke();ctx.setLineDash([]);

  ctx.save();ctx.translate(cam.x,cam.y);
  ctx.shadowColor='#44aaff';ctx.shadowBlur=10;
  ctx.fillStyle='#445566';ctx.strokeStyle='#88bbdd';ctx.lineWidth=1.5;
  ctx.beginPath();ctx.roundRect(-8,-7,16,13,3);ctx.fill();ctx.stroke();
  ctx.shadowBlur=0;ctx.fillStyle='#223344';ctx.strokeStyle='#66aacc';ctx.lineWidth=1;
  ctx.beginPath();ctx.arc(0,-1,3.5,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle='rgba(100,180,255,0.4)';ctx.beginPath();ctx.arc(-1,-2,1.5,0,Math.PI*2);ctx.fill();
  ctx.restore();

  // label
  const li=SNAP_AZ.indexOf(sAz);
  if(li>=0){ctx.font='10px monospace';ctx.fillStyle='rgba(255,255,255,0.4)';ctx.textAlign='center';ctx.fillText(AZ_NAMES[li],cam.x,cam.y+22);}

  // readout
  const sEl=snap(el,SNAP_EL),sDist=snap(dist,SNAP_DIST);
  document.getElementById('maph-h-val').textContent=sAz+'°';
  document.getElementById('maph-v-val').textContent=sEl+'°';
  document.getElementById('maph-z-val').textContent=sDist.toFixed(1);
}

function pushToGradio(){
  const sAz=SNAP_AZ.indexOf(snap(az,SNAP_AZ)),sEl=SNAP_EL.indexOf(snap(el,SNAP_EL)),sDist=SNAP_DIST.indexOf(snap(dist,SNAP_DIST));
  function setN(id,v){const e=document.querySelector('#'+id+' input');if(e){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}}
  setN('maph-az-idx',sAz);setN('maph-el-idx',sEl);setN('maph-dist-idx',sDist);
}

function gp(e){const r=canvas.getBoundingClientRect(),t=e.touches?e.touches[0]:e;return{x:t.clientX-r.left,y:t.clientY-r.top};}

canvas.addEventListener('mousedown',e=>{e.preventDefault();dragging=true;wrap.style.cursor='grabbing';const p=gp(e);lx=p.x;ly=p.y;dragType=e.shiftKey?'z':'o';});
canvas.addEventListener('touchstart',e=>{e.preventDefault();dragging=true;const p=gp(e);lx=p.x;ly=p.y;dragType='o';},{passive:false});
window.addEventListener('mousemove',e=>{if(!dragging)return;e.preventDefault();const p=gp(e),dx=p.x-lx,dy=p.y-ly;lx=p.x;ly=p.y;if(dragType==='z'){dist=Math.max(0.3,Math.min(2.5,dist-dy*0.012));}else{az=((az+dx*0.8)%360+360)%360;el=Math.max(-45,Math.min(75,el-dy*0.5));}draw();});
window.addEventListener('touchmove',e=>{if(!dragging)return;e.preventDefault();const p=gp(e),dx=p.x-lx,dy=p.y-ly;lx=p.x;ly=p.y;az=((az+dx*0.8)%360+360)%360;el=Math.max(-45,Math.min(75,el-dy*0.5));draw();},{passive:false});
function endDrag(){if(!dragging)return;dragging=false;wrap.style.cursor='grab';az=snap(az,SNAP_AZ);el=snap(el,SNAP_EL);dist=snap(dist,SNAP_DIST);draw();pushToGradio();}
window.addEventListener('mouseup',endDrag);window.addEventListener('touchend',endDrag);
canvas.addEventListener('wheel',e=>{e.preventDefault();dist=Math.max(0.3,Math.min(2.5,dist+e.deltaY*0.003));dist=snap(dist,SNAP_DIST);draw();pushToGradio();},{passive:false});
document.getElementById('maph-gizmo-reset').addEventListener('click',e=>{e.stopPropagation();az=0;el=0;dist=1.0;draw();pushToGradio();});

window._maphGizmoSet=function(a,e,d){az=SNAP_AZ[a]||0;el=SNAP_EL[e]||0;dist=SNAP_DIST[d]||1.0;draw();};

new ResizeObserver(resize).observe(wrap);
setTimeout(resize,100);
})();
</script>
"""


class MultiAnglePromptHelperInjected(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PlugIn_Name
        self.version = "2.0.0"
        self.description = "Injects a prompt helper with 3D orbit gizmo into the Video Generator UI."

    def setup_ui(self):
        for cid in [
            "loras_choices", "loras_multipliers", "loras", "lora",
            "prompts", "prompt", "prompt_lines", "prompts_box",
            "positive_prompt", "prompt_text", "prompt_box",
            "advanced_settings", "generation_settings", "model_settings", "resolution",
        ]:
            try:
                self.request_component(cid)
            except Exception:
                pass
        return None

    def post_ui_setup(self, components: dict) -> dict:
        try:
            anchor_candidates = [
                "loras_multipliers", "loras_choices", "loras", "lora",
                "advanced_settings", "generation_settings", "model_settings",
                "resolution", "prompts", "prompt",
            ]
            anchor_id = next((k for k in anchor_candidates if k in components), None)
            if anchor_id is None:
                print("[MultiAngleInjected] No anchor found. Skipping injection.")
                return {}

            prompt_candidates = [
                "prompts", "prompt_lines", "prompts_box", "prompt",
                "positive_prompt", "prompt_text", "prompt_box",
            ]
            prompt_id = next((k for k in prompt_candidates if k in components), None)
            prompt_comp = components.get(prompt_id) if prompt_id else None

            def strip_trigger(s):
                s = (s or "").strip()
                if s.startswith(f"{TRIGGER} "):
                    return s.replace(f"{TRIGGER} ", "", 1)
                return "" if s == TRIGGER else s

            def canonical(az, el, dist, trig):
                az, el, dist = (az or "").strip(), (el or "").strip(), (dist or "").strip()
                c = CANONICAL_LOOKUP.get((az, el, dist), f"{TRIGGER} {az} {el} {dist}".strip())
                return c if trig else strip_trigger(c)

            def build_batch(mode, az, el, dist, trig):
                mode = (mode or "Single").strip()
                if mode == "Single":
                    return canonical(az, el, dist, trig)
                if mode == "8-view sweep (same elevation + distance)":
                    return "\n".join(canonical(a, el, dist, trig) for a in AZIMUTH)
                if mode == "4-elevation sweep (same azimuth + distance)":
                    return "\n".join(canonical(az, e, dist, trig) for e in ELEVATION)
                if mode == "3-distance sweep (same azimuth + elevation)":
                    return "\n".join(canonical(az, el, d, trig) for d in DISTANCE)
                if mode == "All 96 prompts":
                    return "\n".join(ALL_96_PROMPTS if trig else [strip_trigger(p) for p in ALL_96_PROMPTS])
                return canonical(az, el, dist, trig)

            def fmt_blocks(text, gap_n):
                lines = [ln.strip() for ln in (text or "").strip().splitlines() if ln.strip()]
                return ("\n" * (int(gap_n) + 1)).join(lines) if lines else ""

            def apply_prompt(existing, new_text, mode, gap_n):
                new_text = fmt_blocks(new_text, gap_n)
                if not new_text:
                    return existing or ""
                if (mode or "").strip() == "Replace" or not (existing or "").strip():
                    return new_text
                return (existing or "").rstrip() + "\n" * (int(gap_n) + 1) + new_text

            def gizmo_changed(az_idx, el_idx, dist_idx, trig):
                ai = max(0, min(len(AZIMUTH)-1, int(az_idx or 0)))
                ei = max(0, min(len(ELEVATION)-1, int(el_idx or 1)))
                di = max(0, min(len(DISTANCE)-1, int(dist_idx or 1)))
                out = canonical(AZIMUTH[ai], ELEVATION[ei], DISTANCE[di], trig)
                return AZIMUTH[ai], ELEVATION[ei], DISTANCE[di], out

            def sync_gizmo_js(az, el, dist):
                ai = AZIMUTH.index(az) if az in AZIMUTH else 0
                ei = ELEVATION.index(el) if el in ELEVATION else 1
                di = DISTANCE.index(dist) if dist in DISTANCE else 1
                return f"<script>if(window._maphGizmoSet)window._maphGizmoSet({ai},{ei},{di});</script>"

            def create_ui():
                with gr.Accordion("Multi-Angle Prompt Helper", open=False) as acc:

                    include_trigger = gr.Checkbox(label=f"Include {TRIGGER} trigger token", value=True)

                    # Hidden gizmo→Gradio bridge
                    with gr.Row(visible=False):
                        g_az = gr.Number(value=0, elem_id="maph-az-idx")
                        g_el = gr.Number(value=1, elem_id="maph-el-idx")
                        g_dist = gr.Number(value=1, elem_id="maph-dist-idx")

                    # --- Gizmo + dropdowns (main interface) ---
                    gr.HTML(GIZMO_HTML)
                    gr.Markdown("*Drag* to orbit · *Shift+drag* or *scroll* for zoom · Snaps on release")

                    with gr.Row():
                        az = gr.Dropdown(label="H", choices=AZIMUTH, value=AZIMUTH[0])
                        el = gr.Dropdown(label="V", choices=ELEVATION, value=ELEVATION[1])
                        dist = gr.Dropdown(label="Z", choices=DISTANCE, value=DISTANCE[1])

                    output = gr.Textbox(label="Output", lines=2, show_copy_button=True, value=REFERENCE_POSE)

                    # Hidden element to push JS back to gizmo canvas
                    gizmo_sync = gr.HTML(visible=False)

                    # Gizmo → dropdowns + output
                    for g in (g_az, g_el, g_dist):
                        g.change(gizmo_changed, inputs=[g_az, g_el, g_dist, include_trigger], outputs=[az, el, dist, output])

                    # Dropdowns → output + gizmo visual
                    def dropdown_update(a, e, d, trig):
                        return canonical(a, e, d, trig)

                    for c in (az, el, dist, include_trigger):
                        c.change(dropdown_update, inputs=[az, el, dist, include_trigger], outputs=[output])
                    for c in (az, el, dist):
                        c.change(sync_gizmo_js, inputs=[az, el, dist], outputs=[gizmo_sync])

                    # --- Batch (collapsible) ---
                    with gr.Accordion("Batch Generation", open=False):
                        batch_mode = gr.Radio(
                            label="Mode",
                            choices=[
                                "Single",
                                "8-view sweep (same elevation + distance)",
                                "4-elevation sweep (same azimuth + distance)",
                                "3-distance sweep (same azimuth + elevation)",
                                "All 96 prompts",
                            ],
                            value="8-view sweep (same elevation + distance)",
                        )
                        batch_out = gr.Textbox(label="Batch output", lines=10, show_copy_button=True)

                        def batch_go(mode, trig):
                            # Use current dropdown values via closure? No — need inputs.
                            # We'll wire the main dropdowns in.
                            pass

                        def batch_make(mode, a, e, d, trig):
                            return build_batch(mode, a, e, d, trig)

                        for c in (batch_mode, az, el, dist, include_trigger):
                            c.change(batch_make, inputs=[batch_mode, az, el, dist, include_trigger], outputs=[batch_out])

                        gr.Button("Generate batch").click(batch_make, inputs=[batch_mode, az, el, dist, include_trigger], outputs=[batch_out])

                    # --- Apply to prompts box ---
                    with gr.Accordion("Apply to Prompts Box", open=False):
                        apply_mode = gr.Radio(label="Mode", choices=["Append", "Replace"], value="Append")
                        blank_lines = gr.Slider(label="Blank lines between", minimum=1, maximum=3, value=1, step=1)
                        apply_src = gr.Radio(label="Source", choices=["Output", "Batch"], value="Output")

                        preview = gr.Textbox(label="Preview", lines=6, show_copy_button=True)

                        def pick(src, o, b, gap):
                            return fmt_blocks(o if src == "Output" else b, int(gap))

                        for c in (apply_src, blank_lines):
                            c.change(pick, inputs=[apply_src, output, batch_out, blank_lines], outputs=[preview])
                        for c in (output, batch_out):
                            c.change(pick, inputs=[apply_src, output, batch_out, blank_lines], outputs=[preview])

                        if prompt_comp is not None:
                            gr.Button("Apply").click(
                                apply_prompt,
                                inputs=[prompt_comp, preview, apply_mode, blank_lines],
                                outputs=[prompt_comp],
                            )
                        else:
                            gr.Markdown("Prompts box not found — copy from Preview manually.")

                return acc

            self.insert_after(target_component_id=anchor_id, new_component_constructor=create_ui)
            print(f"[MultiAngleInjected] Injected after '{anchor_id}'. Prompts id: '{prompt_id}'")

        except Exception:
            print("[MultiAngleInjected] ERROR during post_ui_setup:")
            traceback.print_exc()

        return {}


Plugin = MultiAnglePromptHelperInjected
