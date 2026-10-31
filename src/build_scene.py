"""dogu-ghost: 展示室シーンを構築する。

  blender --background --factory-startup "D:/ToolProjects/dogu-articulated/out/dogu_assembly.blend" \
          --python src/build_scene.py

出力: scenes/scene.blend
"""
import bpy
import math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, "scenes")
os.makedirs(SCENES, exist_ok=True)

scn = bpy.context.scene

# ---------------------------------------------------------------- 既存の土偶
DOGU = ["head", "torso", "arm_L", "arm_R"]
for name in DOGU:
    ob = bpy.data.objects.get(name)
    assert ob is not None, "missing " + name
    # カメラ・ライトが混ざらないよう、元のコレクションを整理
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    scn.collection.objects.link(ob)
    ob.hide_render = False   # 元シーンで非表示になっていた
    ob.hide_set(False)
    ob.hide_viewport = False

# 土偶全体のバウンディング
mins = Vector((1e9,) * 3)
maxs = Vector((-1e9,) * 3)
for name in DOGU:
    ob = bpy.data.objects[name]
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        for i in range(3):
            mins[i] = min(mins[i], w[i])
            maxs[i] = max(maxs[i], w[i])
ctr = (mins + maxs) / 2
height = maxs.z - mins.z
print("DOGU height %.1fmm  floor z %.1f" % (height, mins.z))

# ---------------------------------------------------------------- マテリアル
def clay_material():
    m = bpy.data.materials.new("DoguClay")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.86
    bsdf.inputs["Specular IOR Level"].default_value = 0.25

    # 色ムラ: ノイズ → ColorRamp で土色の濃淡
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 0.045
    tex.inputs["Detail"].default_value = 8.0
    tex.inputs["Roughness"].default_value = 0.6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.196, 0.106, 0.063, 1)
    ramp.color_ramp.elements[1].position = 0.68
    ramp.color_ramp.elements[1].color = (0.427, 0.243, 0.145, 1)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # 細かい粒状の凹凸
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 0.55
    fine.inputs["Detail"].default_value = 12.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.6
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


# --- 法線を外側へ揃える（Tripo 由来メッシュは裏返っていることがある）
import bmesh
for name in DOGU:
    _ob = bpy.data.objects[name]
    _me = _ob.data
    _bm = bmesh.new()
    _bm.from_mesh(_me)
    bmesh.ops.recalc_face_normals(_bm, faces=_bm.faces)
    _bm.to_mesh(_me)
    _bm.free()
    _me.update()


def normal_report(ob):
    import mathutils
    me = ob.data
    ctr_local = sum((v.co for v in me.vertices), mathutils.Vector()) / len(me.vertices)
    out = 0
    inn = 0
    for poly in me.polygons[:400]:
        d = poly.center - ctr_local
        if d.dot(poly.normal) >= 0:
            out += 1
        else:
            inn += 1
    return out, inn


for name in DOGU:
    print("NORMALS", name, normal_report(bpy.data.objects[name]))


# ---------------------------------------------------------------- 腕を肩へ嵌める
# 元データでは腕が胴の約134mm下（床の上）に置かれている。肩ソケットの空洞中心を
# 実測し、球ジョイント中心の Z をそこへ合わせる（X は「ソケット中心＋球半径」で
# 既に正しい位置にあるため触らない）。
def _world_verts(ob):
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def _sphere_center(points):
    c = sum(points, Vector()) / len(points)
    for _ in range(30):
        r = sum((p - c).length for p in points) / len(points)
        g = Vector()
        for p in points:
            d = p - c
            if d.length > 1e-9:
                g += d.normalized() * ((d.length - r) / len(points))
        c = c + g * 0.5
    return c


_torso = bpy.data.objects["torso"]
_tv = _world_verts(_torso)
_tc = sum(_tv, Vector()) / len(_tv)
_inward = []
for _poly in _torso.data.polygons:
    _p = _torso.matrix_world @ _poly.center
    _n = (_torso.matrix_world.to_3x3() @ _poly.normal).normalized()
    _d = _p - _tc
    if _d.length > 1e-6 and _d.normalized().dot(_n) < -0.55 and 40 < _p.z < 100:
        _inward.append(_p)

for _name in ("arm_L", "arm_R"):
    _ob = bpy.data.objects[_name]
    _vs = _world_verts(_ob)
    _zmax = max(v.z for v in _vs)
    _ball = _sphere_center([v for v in _vs if v.z > _zmax - 12.0])
    _side = -1 if _name.endswith("L") else 1
    _cand = [p for p in _inward if (p.x * _side) > 0]
    if not _cand:
        print("ARM_FIT skip", _name)
        continue
    _top = max(p.z for p in _cand)
    _shoulder = [p for p in _cand if p.z > _top - 22]
    _c = sum(_shoulder, Vector()) / len(_shoulder)
    _delta = Vector((0.0, _c.y - _ball.y, _c.z - _ball.z))
    _ob.location += _delta
    print("ARM_FIT %s ball=(%.1f,%.1f,%.1f) socket=(%.1f,%.1f,%.1f) moved_z=%.1f"
          % (_name, _ball.x, _ball.y, _ball.z, _c.x, _c.y, _c.z, _delta.z))

# 腕を嵌めた後のバウンディングで台座・花・カメラを決め直す
# （location を変えただけでは matrix_world が古いままなので必ず更新する）
bpy.context.view_layer.update()
mins = Vector((1e9,) * 3)
maxs = Vector((-1e9,) * 3)
for name in DOGU:
    ob = bpy.data.objects[name]
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        for i in range(3):
            mins[i] = min(mins[i], w[i])
            maxs[i] = max(maxs[i], w[i])
ctr = (mins + maxs) / 2
height = maxs.z - mins.z
print("DOGU after fit: height %.1fmm  z %.1f..%.1f" % (height, mins.z, maxs.z))


clay = clay_material()
for name in DOGU:
    ob = bpy.data.objects[name]
    ob.data.materials.clear()
    ob.data.materials.append(clay)
    for p in ob.data.polygons:
        p.use_smooth = True

# ---------------------------------------------------------------- 台座
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=155.0, depth=44.0,
                                    location=(0, 0, mins.z - 22.0))
base = bpy.context.object
base.name = "pedestal"
mb = bpy.data.materials.new("Pedestal")
mb.use_nodes = True
pb = mb.node_tree.nodes["Principled BSDF"]
pb.inputs["Base Color"].default_value = (0.028, 0.030, 0.036, 1)
pb.inputs["Roughness"].default_value = 0.58
pb.inputs["Metallic"].default_value = 0.0
base.data.materials.append(mb)
for p in base.data.polygons:
    p.use_smooth = True

# ---------------------------------------------------------------- 床
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, mins.z - 44.0))
floor = bpy.context.object
floor.name = "floor"
mf = bpy.data.materials.new("Floor")
mf.use_nodes = True
fb = mf.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.016, 0.017, 0.020, 1)
fb.inputs["Roughness"].default_value = 0.30
floor.data.materials.append(mf)

# ---------------------------------------------------------------- 目の発光
EYE = [Vector((14.5, -23.0, 129.0)), Vector((-14.5, -23.0, 129.0))]
me = bpy.data.materials.new("EyeGlow")
me.use_nodes = True
nt = me.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (1.0, 0.52, 0.14, 1)
em.inputs["Strength"].default_value = 60.0
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])

eyes = []
for i, p in enumerate(EYE):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=3.0, location=p)
    e = bpy.context.object
    e.name = "eye_glow_%d" % i
    e.data.materials.append(me)
    for poly in e.data.polygons:
        poly.use_smooth = True
    eyes.append(e)

# ---------------------------------------------------------------- マリーゴールド
def marigold(loc, scale=1.0, name="marigold"):
    """花びらの塊で作る簡易マリーゴールド。1オブジェクトに結合する。"""
    parts = []
    for k in range(9):
        a = k * (2 * math.pi / 9)
        r = 4.0 * scale
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=10, ring_count=6, radius=3.2 * scale,
            location=(loc[0] + math.cos(a) * r, loc[1] + math.sin(a) * r * 0.55,
                      loc[2] + math.sin(a) * 1.2 * scale))
        parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8,
                                        radius=3.4 * scale,
                                        location=(loc[0], loc[1], loc[2] + 1.0 * scale))
    parts.append(bpy.context.object)
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    ob = bpy.context.object
    ob.name = name
    return ob


mflow = bpy.data.materials.new("Marigold")
mflow.use_nodes = True
fl = mflow.node_tree.nodes["Principled BSDF"]
fl.inputs["Base Color"].default_value = (0.86, 0.34, 0.02, 1)
fl.inputs["Roughness"].default_value = 0.55
fl.inputs["Emission Color"].default_value = (0.9, 0.38, 0.03, 1)
fl.inputs["Emission Strength"].default_value = 0.35

FLOWERS = [
    ((-55, -125, mins.z + 4), 3.4),
    ((45, -130, mins.z + 4), 3.0),
    ((-25, -140, mins.z + 4), 2.6),
]
for i, (loc, s) in enumerate(FLOWERS):
    f = marigold(loc, s, "marigold_%d" % i)
    f.data.materials.append(mflow)
    for p in f.data.polygons:
        p.use_smooth = True

# ---------------------------------------------------------------- ライティング
world = bpy.data.worlds.new("DoguWorld")
scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.030, 0.036, 0.055, 1)
bg.inputs["Strength"].default_value = 1.0  # world color 側で調整


LIGHT_SCALE = 1000.0  # プローブ実測: mm スケールでは x1000 が適正露出（x100 は真っ暗, x20000 は白飛び）


def add_light(name, kind, loc, energy, color, size=200.0, target=(0, 0, 30), spot_size=None):
    ld = bpy.data.lights.new(name, kind)
    # Blender は 1 unit = 1m として逆二乗減衰する。このシーンは mm スケール
    # （土偶250unit≒250m相当、ライトまで400m）なので、素の W では真っ暗になる。
    ld.energy = energy * LIGHT_SCALE
    ld.color = color
    if kind == 'AREA':
        ld.size = size
    if kind == 'SPOT':
        ld.spot_size = spot_size or math.radians(45)
        ld.spot_blend = 0.45
    ob = bpy.data.objects.new(name, ld)
    scn.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


# キー: 左前上から暖色。土偶の右半分を落とす
add_light("key", 'AREA', (-330, -420, 300), 4200, (1.0, 0.80, 0.58), size=260)
# リム: 右後ろから青白（台座が白飛びするので弱めに）
add_light("rim", 'AREA', (300, 320, 210), 500, (0.52, 0.70, 1.0), size=200)
# トップ: 頭部へ細いスポット
add_light("top", 'SPOT', (10, -40, 420), 3600, (1.0, 0.92, 0.80),
          size=1, spot_size=math.radians(38), target=(0, 0, 120))
# 花をほんのり拾うアンダーライト
add_light("under", 'AREA', (0, -240, mins.z - 60), 900, (1.0, 0.55, 0.22), size=220,
          target=(0, 0, mins.z - 25))

# ---------------------------------------------------------------- カメラ
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 50.0
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = 760.0
cam_d.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new("Cam", cam_d)
scn.collection.objects.link(cam)
scn.camera = cam

TARGET = Vector((0, 0, 77.0))
RADIUS = 780.0
cam_z = 150.0


def place_cam(deg):
    a = math.radians(deg)
    cam.location = (math.sin(a) * RADIUS, -math.cos(a) * RADIUS, cam_z)
    d = TARGET - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- アニメーション
FPS = 24
DURATION = 40
scn.render.fps = FPS
scn.frame_start = 1
scn.frame_end = FPS * DURATION

# カメラ: 正面から緩やかに回り込む（0deg → 20deg）
place_cam(0.0)
cam.keyframe_insert("location", frame=1)
cam.rotation_euler  # noqa
cam.keyframe_insert("rotation_euler", frame=1)
place_cam(20.0)
cam.keyframe_insert("location", frame=scn.frame_end)
cam.keyframe_insert("rotation_euler", frame=scn.frame_end)

# 土偶: 逆方向にわずかに回す（立体感を出す）
for name in DOGU:
    ob = bpy.data.objects[name]
    ob.rotation_mode = 'XYZ'

# 目: 3秒でゆっくり点灯、以後ちらつかない程度に保持
for e in eyes:
    e.scale = (1, 1, 1)
    e.keyframe_insert("scale", frame=1)
    e.scale = (0.02, 0.02, 0.02)
    e.keyframe_insert("scale", frame=FPS * 6)
    e.scale = (1.0, 1.0, 1.0)
    e.keyframe_insert("scale", frame=FPS * 9)
    e.scale = (1.0, 1.0, 1.0)
    e.keyframe_insert("scale", frame=scn.frame_end)

# 発光強度のランプ（マテリアルの emission strength はノードでキーフレーム）
em_node = bpy.data.materials["EyeGlow"].node_tree.nodes["Emission"]
em_node.inputs["Strength"].default_value = 0.0
em_node.inputs["Strength"].keyframe_insert("default_value", frame=1)
em_node.inputs["Strength"].default_value = 0.0
em_node.inputs["Strength"].keyframe_insert("default_value", frame=FPS * 6)
em_node.inputs["Strength"].default_value = 60.0
em_node.inputs["Strength"].keyframe_insert("default_value", frame=FPS * 9)

# 花: ゆっくり咲く（スケール 0 → 1）
for i, (loc, s) in enumerate(FLOWERS):
    f = bpy.data.objects["marigold_%d" % i]
    f.scale = (0.001, 0.001, 0.001)
    f.keyframe_insert("scale", frame=1)
    f.keyframe_insert("scale", frame=FPS * 22)
    f.scale = (1, 1, 1)
    f.keyframe_insert("scale", frame=FPS * 30)

# ---------------------------------------------------------------- レンダ設定
scn.render.engine = 'BLENDER_EEVEE'
scn.render.resolution_x = 1920
scn.render.resolution_y = 1080
scn.render.resolution_percentage = 100
scn.render.image_settings.file_format = 'PNG'
scn.render.film_transparent = False
try:
    scn.eevee.taa_render_samples = 64
    scn.eevee.use_raytracing = True
except Exception as exc:  # バージョン差の吸収
    print("eevee opt skipped:", exc)
scn.view_settings.view_transform = 'AgX'
scn.view_settings.look = 'AgX - Medium High Contrast'
scn.view_settings.exposure = 0.3

# コンポジタ: グレア（目の発光をにじませる）
# Blender 5.x はコンポジタがノードグループ化されている。失敗したら
# ノードグループを丸ごと外す（半端な設定はレンダを黒くする）
try:
    ng = bpy.data.node_groups.new("DoguComp", "CompositorNodeTree")
    ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    gout = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], gout.inputs["Image"])
    # 5.2 の Glare は設定が「入力ソケット」に移っている（プロパティ指定は無視される）。
    # 既定は Streaks（十字の光芒）なので、必ず Fog Glow に切り替える。
    def _set_input(node, name, value):
        for sock in node.inputs:
            if sock.name == name:
                try:
                    sock.default_value = value
                    return True
                except Exception as exc:
                    print("glare input skip", name, exc)
                    return False
        return False

    _set_input(glare, "Type", "Fog Glow")
    _set_input(glare, "Quality", "High")
    _set_input(glare, "Threshold", 1.0)
    _set_input(glare, "Size", 0.55)
    _set_input(glare, "Strength", 0.55)
    print("GLARE type=%s size=%s strength=%s" % (
        glare.inputs["Type"].default_value, glare.inputs["Size"].default_value,
        glare.inputs["Strength"].default_value))
    scn.compositing_node_group = ng
    print("COMPOSITOR ok; glare attrs:",
          [p.identifier for p in glare.bl_rna.properties if not p.is_readonly][:20])
except Exception as exc:
    print("compositor skipped:", exc)
    try:
        scn.compositing_node_group = None
    except Exception:
        pass

scn.render.filepath = os.path.join(ROOT, "out", "frames", "f_")

# ---------------------------------------------------------------- 保存
blend_path = os.path.join(SCENES, "scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("SAVED", blend_path)
print("DOGU_BBOX", [round(v, 2) for v in mins], [round(v, 2) for v in maxs])
