"""確定シーンをレンダする（解像度・サンプル数・範囲を引数で上書き）。

  blender --background --factory-startup scenes/scene.blend --python src/render.py -- \
      --w 1280 --h 720 --samples 24 --out out/frames720/f_#### --start 1 --end 960

コンポジタ（グレア）は保存済みの設定をそのまま使う。
"""
import bpy
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default


w = int(arg("--w", 1280))
h = int(arg("--h", 720))
samples = int(arg("--samples", 24))
out = arg("--out", "out/frames/f_####")
start = int(arg("--start", 1))
end = int(arg("--end", 0))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isabs(out):
    out = os.path.join(ROOT, out)

scn = bpy.context.scene
scn.render.resolution_x = w
scn.render.resolution_y = h
scn.render.resolution_percentage = 100
try:
    scn.eevee.taa_render_samples = samples
except Exception:
    pass
scn.frame_start = start
if end:
    scn.frame_end = end
scn.render.image_settings.file_format = 'PNG'
scn.render.filepath = out
scn.render.use_overwrite = False   # 途中再開できるように
scn.render.use_placeholder = True
print("RENDER %dx%d samples=%d frames=%d..%d -> %s" % (w, h, samples, scn.frame_start, scn.frame_end, out))
bpy.ops.render.render(animation=True)
print("RENDER_DONE")
