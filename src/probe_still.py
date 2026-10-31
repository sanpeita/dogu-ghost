"""露出・ライト強度のプローブ。scene.blend を開いて1フレームだけ撮る。

  blender --background --factory-startup scenes/scene.blend \
          --python src/probe_still.py -- --k 1000 --expo 0.0 --frame 300 --out out/test/p_k1000.png

--k     : 全ライトのエネルギー倍率（mm スケール対策。1.0 で build_scene.py のまま）
--expo  : scene.view_settings.exposure（ストップ）
--frame : 撮るフレーム（目発光は 6s=144f で立ち上がり、9s=216f で全開）
コンポジタは必ず外す（診断は素の画像で）。
"""
import bpy
import sys
import os

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default


k = arg("--k", 1000.0)
expo = arg("--expo", 0.0)
frame = int(arg("--frame", 300))
out = arg("--out", "out/test/probe.png")
pct = int(arg("--pct", 40))
samples = int(arg("--samples", 12))
eye_y = float(arg("--eye-y", -20.5))       # 発光球の Y（遮光器の穴の底面は約 -22）
eye_strength = float(arg("--eye-strength", -1))
eye_scale = float(arg("--eye-scale", 0.0))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isabs(out):
    out = os.path.join(ROOT, out)

scn = bpy.context.scene

# 診断中はコンポジタを切る（半端なグラフは全黒の原因になる）
try:
    scn.compositing_node_group = None
except Exception as exc:
    print("compositor detach skipped:", exc)

# ライト倍率
total = 0.0
for ob in bpy.data.objects:
    if ob.type == 'LIGHT':
        ob.data.energy *= k
        total += ob.data.energy
print("LIGHT_TOTAL %.3f W (k=%s)" % (total, k))

# 目の発光はフレームで制御されているので、評価フレームを明示
scn.frame_set(frame)

# 目: 発光球が眼窩の奥に埋まると光が読めない。前面へ寄せ、強度・サイズを上書きする。
for ob in bpy.data.objects:
    if ob.name.startswith("eye_glow_"):
        if eye_y != -20.5:
            ob.location.y = eye_y
        if eye_scale > 0:
            ob.scale = (eye_scale, eye_scale, eye_scale)
        print("EYE %s y=%.2f scale=%.2f" % (ob.name, ob.location.y, ob.scale.x))
mat = bpy.data.materials.get("EyeGlow")
if mat is not None and eye_strength >= 0:
    node = mat.node_tree.nodes.get("Emission")
    if node is not None:
        node.inputs["Strength"].default_value = eye_strength
        print("EYE strength %.1f" % eye_strength)

scn.render.resolution_percentage = pct
try:
    scn.eevee.taa_render_samples = samples
except Exception:
    pass

scn.render.image_settings.file_format = 'PNG'
scn.render.filepath = out
scn.view_settings.exposure = expo

print("PROBE k=%s expo=%s frame=%s pct=%s samples=%s" % (k, expo, frame, pct, samples))
bpy.ops.render.render(write_still=True)
print("WROTE", out)
