import html as _html
import time
import gradio as gr
import traceback
from shared.utils.plugins import WAN2GPPlugin

PlugIn_Name = "Multi-Angle Prompt Helper"
PlugIn_Id = "MultiAnglePromptHelper"

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


_GIZMO_DOC = """<!DOCTYPE html><html><head>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;overflow:hidden;cursor:grab;touch-action:none}
canvas{position:absolute;top:0;left:0;width:100%;height:100%}
.hud{position:absolute;bottom:0;left:0;right:0;display:flex;justify-content:space-around;
  padding:8px 12px;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);border-top:1px solid #444;z-index:1}
.hl{font-size:10px;color:#888;font-family:monospace;text-align:center}
.hv{font-size:17px;font-weight:bold;font-family:monospace;text-align:center}
#rb{position:absolute;bottom:8px;right:12px;background:rgba(255,255,255,0.1);border:1px solid #555;
  color:#aaa;border-radius:50%;width:26px;height:26px;cursor:pointer;font-size:13px;
  display:flex;align-items:center;justify-content:center;z-index:2}
</style></head><body>
<canvas id="c"></canvas>
<div class="hud">
  <div><div class="hl">HORIZONTAL</div><div id="hv" class="hv" style="color:#ff4488">0\u00b0</div></div>
  <div><div class="hl">VERTICAL</div><div id="vv" class="hv" style="color:#44ddaa">0\u00b0</div></div>
  <div><div class="hl">ZOOM</div><div id="zv" class="hv" style="color:#6688ff">1.0</div></div>
</div>
<button id="rb" title="Reset">\u21ba</button>
<script>
(function(){
var SNAP_AZ=[0,45,90,135,180,225,270,315],SNAP_EL=[-30,0,30,60],SNAP_DIST=[0.6,1.0,1.8];
var AZ_NAMES=['front','front-right','right','back-right','back','back-left','left','front-left'];
var az=0,el=0,dist=1.0,dragging=false,dragType=null,lx=0,ly=0;
var canvas=document.getElementById('c'),ctx=canvas.getContext('2d');
var hVal=document.getElementById('hv'),vVal=document.getElementById('vv'),zVal=document.getElementById('zv');

function resize(){
  var r=devicePixelRatio||1,W=window.innerWidth,H=window.innerHeight;
  canvas.width=W*r;canvas.height=H*r;
  ctx.setTransform(r,0,0,r,0,0);draw();
}
function snap(v,arr){
  if(arr===SNAP_AZ){var v2=((v%360)+360)%360;return arr.reduce(function(b,a){return Math.min(Math.abs(v2-a),360-Math.abs(v2-a))<Math.min(Math.abs(v2-b),360-Math.abs(v2-b))?a:b;});}
  return arr.reduce(function(b,a){return Math.abs(v-a)<Math.abs(v-b)?a:b;});
}
function p3d(x,y,z,cx,cy,s){
  var ca=Math.cos(0.4),sa=Math.sin(0.4);
  var ry=y*ca-z*sa,rz=y*sa+z*ca,pr=4/(4+rz*0.3);
  return{x:cx+x*s*pr,y:cy-ry*s*pr};
}
function draw(){
  var W=window.innerWidth,H=window.innerHeight;
  var cx=W/2,cy=H*0.42,sc=W*0.2;
  ctx.clearRect(0,0,W,H);
  ctx.strokeStyle='rgba(255,255,255,0.03)';ctx.lineWidth=0.5;
  for(var i=-3;i<=3;i++){
    var a=p3d(i*.5,0,-1.5,cx,cy,sc),b=p3d(i*.5,0,1.5,cx,cy,sc);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    a=p3d(-1.5,0,i*.5,cx,cy,sc);b=p3d(1.5,0,i*.5,cx,cy,sc);
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
  }
  ctx.strokeStyle='rgba(255,68,136,0.45)';ctx.lineWidth=2.5;ctx.beginPath();
  for(var i=0;i<=64;i++){var a2=i/64*Math.PI*2,p=p3d(Math.sin(a2)*1.2,0,Math.cos(a2)*1.2,cx,cy,sc);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}
  ctx.closePath();ctx.stroke();
  var ar=az*Math.PI/180,er=el*Math.PI/180;
  ctx.strokeStyle='rgba(68,221,170,0.5)';ctx.lineWidth=2.5;ctx.beginPath();
  for(var i=0;i<=32;i++){var e=(-45+i/32*120)*Math.PI/180,r=1.2,p=p3d(Math.sin(ar)*Math.cos(e)*r,Math.sin(e)*r,Math.cos(ar)*Math.cos(e)*r,cx,cy,sc);i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y);}
  ctx.stroke();
  var sAz=snap(az,SNAP_AZ);
  for(var i=0;i<SNAP_AZ.length;i++){
    var a3=SNAP_AZ[i]*Math.PI/180,p=p3d(Math.sin(a3)*1.2,0,Math.cos(a3)*1.2,cx,cy,sc);
    var on=sAz===SNAP_AZ[i];
    ctx.fillStyle=on?'#ff4488':'rgba(255,68,136,0.25)';
    ctx.beginPath();ctx.arc(p.x,p.y,on?5:3,0,Math.PI*2);ctx.fill();
  }
  var arrLen=0.7,arrHead=0.18,shaftW=3,headW=8;
  var sa=Math.sin(ar),ca=Math.cos(ar),se=Math.sin(er),ce=Math.cos(er);
  var arrBase=p3d(0,0,0,cx,cy,sc);
  var arrTip=p3d(sa*ce*arrLen,se*arrLen,ca*ce*arrLen,cx,cy,sc);
  var arrNeck=p3d(sa*ce*(arrLen-arrHead),se*(arrLen-arrHead),ca*ce*(arrLen-arrHead),cx,cy,sc);
  var dx=arrTip.x-arrBase.x,dy=arrTip.y-arrBase.y;
  var len2d=Math.sqrt(dx*dx+dy*dy)||1;
  var px=-dy/len2d,py=dx/len2d;
  ctx.save();
  ctx.shadowColor='rgba(100,180,255,0.15)';ctx.shadowBlur=6;
  ctx.beginPath();
  ctx.moveTo(arrBase.x+px*shaftW*0.4,arrBase.y+py*shaftW*0.4);
  ctx.lineTo(arrNeck.x+px*shaftW*0.4,arrNeck.y+py*shaftW*0.4);
  ctx.lineTo(arrNeck.x-px*shaftW*0.4,arrNeck.y-py*shaftW*0.4);
  ctx.lineTo(arrBase.x-px*shaftW*0.4,arrBase.y-py*shaftW*0.4);
  ctx.closePath();
  var sg=ctx.createLinearGradient(arrBase.x+px*shaftW,arrBase.y+py*shaftW,arrBase.x-px*shaftW,arrBase.y-py*shaftW);
  sg.addColorStop(0,'rgba(190,210,245,0.55)');sg.addColorStop(0.45,'rgba(130,155,200,0.45)');sg.addColorStop(1,'rgba(60,75,110,0.3)');
  ctx.fillStyle=sg;ctx.fill();
  ctx.beginPath();
  ctx.moveTo(arrTip.x,arrTip.y);
  ctx.lineTo(arrNeck.x+px*headW,arrNeck.y+py*headW);
  ctx.lineTo(arrNeck.x,arrNeck.y);
  ctx.closePath();
  ctx.fillStyle='rgba(170,195,235,0.6)';ctx.fill();
  ctx.beginPath();
  ctx.moveTo(arrTip.x,arrTip.y);
  ctx.lineTo(arrNeck.x-px*headW,arrNeck.y-py*headW);
  ctx.lineTo(arrNeck.x,arrNeck.y);
  ctx.closePath();
  ctx.fillStyle='rgba(70,90,130,0.5)';ctx.fill();
  ctx.shadowBlur=0;
  ctx.strokeStyle='rgba(150,180,220,0.25)';ctx.lineWidth=0.5;
  ctx.beginPath();
  ctx.moveTo(arrNeck.x+px*headW,arrNeck.y+py*headW);
  ctx.lineTo(arrTip.x,arrTip.y);
  ctx.lineTo(arrNeck.x-px*headW,arrNeck.y-py*headW);
  ctx.stroke();
  ctx.restore();
  var cp=p3d(0,0.15,0,cx,cy,sc);
  var gd=ctx.createRadialGradient(cp.x-3,cp.y-3,2,cp.x,cp.y,12);
  gd.addColorStop(0,'#ffdd44');gd.addColorStop(1,'#aa8800');
  ctx.fillStyle=gd;ctx.beginPath();ctx.arc(cp.x,cp.y,11,0,Math.PI*2);ctx.fill();
  var ds=dist;
  var cam=p3d(Math.sin(ar)*Math.cos(er)*1.2*ds,Math.sin(er)*1.2*ds,Math.cos(ar)*Math.cos(er)*1.2*ds,cx,cy,sc);
  ctx.strokeStyle='rgba(255,200,50,0.25)';ctx.lineWidth=1;ctx.setLineDash([4,4]);
  ctx.beginPath();ctx.moveTo(cp.x,cp.y);ctx.lineTo(cam.x,cam.y);ctx.stroke();ctx.setLineDash([]);
  ctx.save();ctx.translate(cam.x,cam.y);
  ctx.shadowColor='#44aaff';ctx.shadowBlur=10;
  ctx.fillStyle='#445566';ctx.strokeStyle='#88bbdd';ctx.lineWidth=1.5;
  ctx.beginPath();if(ctx.roundRect){ctx.roundRect(-8,-7,16,13,3);}else{ctx.rect(-8,-7,16,13);}
  ctx.fill();ctx.stroke();
  ctx.shadowBlur=0;ctx.fillStyle='#223344';ctx.strokeStyle='#66aacc';ctx.lineWidth=1;
  ctx.beginPath();ctx.arc(0,-1,3.5,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.fillStyle='rgba(100,180,255,0.4)';ctx.beginPath();ctx.arc(-1,-2,1.5,0,Math.PI*2);ctx.fill();
  ctx.restore();
  var li=SNAP_AZ.indexOf(sAz);
  if(li>=0){ctx.font='10px monospace';ctx.fillStyle='rgba(255,255,255,0.4)';ctx.textAlign='center';ctx.fillText(AZ_NAMES[li],cam.x,cam.y+22);}
  var sEl=snap(el,SNAP_EL),sDist=snap(dist,SNAP_DIST);
  hVal.textContent=sAz+'\\u00b0';vVal.textContent=sEl+'\\u00b0';zVal.textContent=sDist.toFixed(1);
}
function pushToGradio(){
  var sAz=SNAP_AZ.indexOf(snap(az,SNAP_AZ)),sEl=SNAP_EL.indexOf(snap(el,SNAP_EL)),sDist=SNAP_DIST.indexOf(snap(dist,SNAP_DIST));
  try{var pd=parent.document;
    function setN(id,v){var e=pd.querySelector('#'+id+' input');if(e){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,String(v));e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));}}
    setN('maph-az-idx',sAz);setN('maph-el-idx',sEl);setN('maph-dist-idx',sDist);
  }catch(err){}
}
function gp(e){var r=canvas.getBoundingClientRect(),t=e.touches?e.touches[0]:e;return{x:t.clientX-r.left,y:t.clientY-r.top};}
canvas.addEventListener('mousedown',function(e){e.preventDefault();dragging=true;document.body.style.cursor='grabbing';var p=gp(e);lx=p.x;ly=p.y;dragType=e.shiftKey?'z':'o';});
canvas.addEventListener('touchstart',function(e){e.preventDefault();dragging=true;var p=gp(e);lx=p.x;ly=p.y;dragType='o';},{passive:false});
window.addEventListener('mousemove',function(e){if(!dragging)return;e.preventDefault();var p=gp(e),dx=p.x-lx,dy=p.y-ly;lx=p.x;ly=p.y;if(dragType==='z'){dist=Math.max(0.3,Math.min(2.5,dist-dy*0.012));}else{az=((az+dx*0.8)%360+360)%360;el=Math.max(-45,Math.min(75,el-dy*0.5));}draw();});
window.addEventListener('touchmove',function(e){if(!dragging)return;e.preventDefault();var p=gp(e),dx=p.x-lx,dy=p.y-ly;lx=p.x;ly=p.y;az=((az+dx*0.8)%360+360)%360;el=Math.max(-45,Math.min(75,el-dy*0.5));draw();},{passive:false});
function endDrag(){if(!dragging)return;dragging=false;document.body.style.cursor='grab';az=snap(az,SNAP_AZ);el=snap(el,SNAP_EL);dist=snap(dist,SNAP_DIST);draw();pushToGradio();}
window.addEventListener('mouseup',endDrag);window.addEventListener('touchend',endDrag);
document.getElementById('rb').addEventListener('click',function(e){e.stopPropagation();az=0;el=0;dist=1.0;draw();pushToGradio();});
try{parent.window._maphGizmoSet=function(a,e,d){az=SNAP_AZ[a]||0;el=SNAP_EL[e]||0;dist=SNAP_DIST[d]||1.0;draw();};}catch(err){}
window.addEventListener('resize',resize);
resize();
})();
</script></body></html>"""

GIZMO_HTML = (
    '<iframe id="maph-gizmo-frame" srcdoc="'
    + _html.escape(_GIZMO_DOC, quote=True)
    + '" style="width:100%;aspect-ratio:4/3;max-width:600px;margin:0 auto;'
    + 'display:block;border:none;border-radius:12px;overflow:hidden;"></iframe>'
)


def _strip_trigger(s):
    s = (s or "").strip()
    if s.startswith(f"{TRIGGER} "):
        return s.replace(f"{TRIGGER} ", "", 1)
    return "" if s == TRIGGER else s


def _canonical(az, el, dist, trig):
    az, el, dist = (az or "").strip(), (el or "").strip(), (dist or "").strip()
    c = CANONICAL_LOOKUP.get((az, el, dist), f"{TRIGGER} {az} {el} {dist}".strip())
    return c if trig else _strip_trigger(c)


def _build_batch(mode, az, el, dist, trig):
    mode = (mode or "Single").strip()
    if mode == "Single":
        return _canonical(az, el, dist, trig)
    if mode == "8-view sweep (same elevation + distance)":
        return "\n".join(_canonical(a, el, dist, trig) for a in AZIMUTH)
    if mode == "4-elevation sweep (same azimuth + distance)":
        return "\n".join(_canonical(az, e, dist, trig) for e in ELEVATION)
    if mode == "3-distance sweep (same azimuth + elevation)":
        return "\n".join(_canonical(az, el, d, trig) for d in DISTANCE)
    if mode == "All 96 prompts":
        return "\n".join(ALL_96_PROMPTS if trig else [_strip_trigger(p) for p in ALL_96_PROMPTS])
    return _canonical(az, el, dist, trig)


def _fmt_blocks(text, gap_n):
    lines = [ln.strip() for ln in (text or "").strip().splitlines() if ln.strip()]
    return ("\n" * (int(gap_n) + 1)).join(lines) if lines else ""


class MultiAnglePromptHelper(WAN2GPPlugin):
    def __init__(self):
        super().__init__()
        self.name = PlugIn_Name
        self.version = "2.1.0"
        self.description = "3D orbit gizmo for multi-angle prompt generation."

    def setup_ui(self):
        self.request_global("get_current_model_settings")
        self.request_component("refresh_form_trigger")
        self.request_component("state")
        self.request_component("main_tabs")

        self.add_tab(
            tab_id=PlugIn_Id,
            label=PlugIn_Name,
            component_constructor=self.create_tab_ui,
        )

    def create_tab_ui(self):
        state = self.state

        def gizmo_changed(az_idx, el_idx, dist_idx, trig):
            ai = max(0, min(len(AZIMUTH) - 1, int(az_idx or 0)))
            ei = max(0, min(len(ELEVATION) - 1, int(el_idx or 1)))
            di = max(0, min(len(DISTANCE) - 1, int(dist_idx or 1)))
            out = _canonical(AZIMUTH[ai], ELEVATION[ei], DISTANCE[di], trig)
            return AZIMUTH[ai], ELEVATION[ei], DISTANCE[di], out

        def sync_gizmo_js(az_val, el_val, dist_val):
            ai = AZIMUTH.index(az_val) if az_val in AZIMUTH else 0
            ei = ELEVATION.index(el_val) if el_val in ELEVATION else 1
            di = DISTANCE.index(dist_val) if dist_val in DISTANCE else 1
            inner = f"<script>try{{parent.window._maphGizmoSet({ai},{ei},{di});}}catch(e){{}}</script>"
            return f'<iframe srcdoc="{_html.escape(inner, quote=True)}" style="display:none;width:0;height:0;border:none;position:absolute;"></iframe>'

        def apply_to_prompt(state, new_text, mode, gap_n):
            new_text = _fmt_blocks(new_text, gap_n)
            if not new_text:
                return time.time()
            settings = self.get_current_model_settings(state)
            existing = settings.get("prompt", "")
            if (mode or "").strip() == "Replace" or not (existing or "").strip():
                settings["prompt"] = new_text
            else:
                settings["prompt"] = (existing or "").rstrip() + "\n" * (int(gap_n) + 1) + new_text
            return time.time()

        def apply_and_goto(state, new_text, mode, gap_n):
            ts = apply_to_prompt(state, new_text, mode, gap_n)
            return self.goto_video_tab(state), ts

        with gr.Column():
            include_trigger = gr.Checkbox(label=f"Include {TRIGGER} trigger token", value=True)

            # Hidden gizmo→Gradio bridge
            with gr.Row(visible=False):
                g_az = gr.Number(value=0, elem_id="maph-az-idx")
                g_el = gr.Number(value=1, elem_id="maph-el-idx")
                g_dist = gr.Number(value=1, elem_id="maph-dist-idx")

            # --- Gizmo ---
            gr.HTML(GIZMO_HTML)
            gr.Markdown("*Drag* to orbit · Snaps on release")

            with gr.Row():
                az = gr.Dropdown(label="Horizontal", choices=AZIMUTH, value=AZIMUTH[0], scale=1)
                el = gr.Dropdown(label="Vertical", choices=ELEVATION, value=ELEVATION[1], scale=1)
                dist = gr.Radio(label="Distance", choices=DISTANCE, value=DISTANCE[1], scale=1)

            output = gr.Textbox(label="Output", lines=2, show_copy_button=True, value=REFERENCE_POSE)

            # Hidden element for gizmo sync
            gizmo_sync = gr.HTML(visible=False)

            # Gizmo → dropdowns + output
            for g in (g_az, g_el, g_dist):
                g.change(gizmo_changed, inputs=[g_az, g_el, g_dist, include_trigger], outputs=[az, el, dist, output])

            # Dropdowns → output + gizmo visual
            def dropdown_update(a, e, d, trig):
                return _canonical(a, e, d, trig)

            for c in (az, el, dist, include_trigger):
                c.change(dropdown_update, inputs=[az, el, dist, include_trigger], outputs=[output])
            for c in (az, el, dist):
                c.change(sync_gizmo_js, inputs=[az, el, dist], outputs=[gizmo_sync])

            # --- Batch Generation (collapsible) ---
            gr.Markdown("---")
            with gr.Accordion("Batch Generation", open=False, elem_id="maph-batch"):
                gr.HTML('<style>#maph-batch>.label-wrap>span{font-weight:700!important;}</style>')
                gr.Markdown('*Enable "Each New Line Will Add A New Video Request" at bottom of General Tab (in Video Generator Tab)*')
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

                def batch_make(mode, a, e, d, trig):
                    return _build_batch(mode, a, e, d, trig)

                for c in (batch_mode, az, el, dist, include_trigger):
                    c.change(batch_make, inputs=[batch_mode, az, el, dist, include_trigger], outputs=[batch_out])

                gr.Button("Generate batch").click(batch_make, inputs=[batch_mode, az, el, dist, include_trigger], outputs=[batch_out])

            # --- Apply to Prompts ---
            gr.Markdown("---")
            gr.Markdown("**Apply to Prompts Box**")
            with gr.Row():
                apply_mode = gr.Radio(label="Mode", choices=["Append", "Replace"], value="Append", scale=1)
                apply_src = gr.Radio(label="Source", choices=["Output", "Batch"], value="Output", scale=1)
            blank_lines = gr.Slider(label="Blank lines between", minimum=1, maximum=3, value=1, step=1)

            preview = gr.Textbox(label="Preview", lines=4, show_copy_button=True)

            def pick(src, o, b, gap):
                return _fmt_blocks(o if src == "Output" else b, int(gap))

            for c in (apply_src, blank_lines):
                c.change(pick, inputs=[apply_src, output, batch_out, blank_lines], outputs=[preview])
            for c in (output, batch_out):
                c.change(pick, inputs=[apply_src, output, batch_out, blank_lines], outputs=[preview])

            gr.Button("Apply to Prompts & Go to Video Tab", variant="primary").click(
                fn=apply_and_goto,
                inputs=[state, preview, apply_mode, blank_lines],
                outputs=[self.main_tabs, self.refresh_form_trigger],
            )


Plugin = MultiAnglePromptHelper
