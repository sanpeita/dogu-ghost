"""腕の球ジョイントと胴のソケット位置を実測する（解析のみ、保存しない）。

  blender --background --factory-startup out/dogu_assembly.blend \
          --python src/analyze_joints.py
"""
import bpy
import bmesh
from mathutils import Vector

DOGU = ["head", "torso", "arm_L", "arm_R"]


def world_verts(ob):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices]


def sphere_fit(points):
    """最小二乗で球を当てる（付近の点群が球面である前提）。"""
    import mathutils
    n = len(points)
    c = sum(points, Vector()) / n
    # 反復: 中心を平均、半径は平均距離
    for _ in range(30):
        r = sum((p - c).length for p in points) / n
        # 勾配方向へ少し動かす
        grad = Vector()
        for p in points:
            d = (p - c)
            if d.length > 1e-9:
                grad += d.normalized() * ((d.length - r) / max(len(points), 1))
        c = c + grad * 0.5
    r = sum((p - c).length for p in points) / n
    dev = sum(abs((p - c).length - r) for p in points) / n
    return c, r, dev


torso = bpy.data.objects["torso"]
tv = world_verts(torso)
tc = sum(tv, Vector()) / len(tv)

for name in ["arm_L", "arm_R"]:
    ob = bpy.data.objects[name]
    vs = world_verts(ob)
    zs = [v.z for v in vs]
    zmin, zmax = min(zs), max(zs)
    # 上端（ジョイント側と想定）12mm の点群で球を当てる
    cap = [v for v in vs if v.z > zmax - 12.0]
    c, r, dev = sphere_fit(cap)
    print("ARM %s z=%.1f..%.1f  cap_center=(%.2f, %.2f, %.2f) r=%.2f dev=%.3f n=%d"
          % (name, zmin, zmax, c.x, c.y, c.z, r, dev, len(cap)))
    # 下端（手側）
    hand = [v for v in vs if v.z < zmin + 8.0]
    hc = sum(hand, Vector()) / len(hand)
    print("    hand_center=(%.2f, %.2f, %.2f)" % (hc.x, hc.y, hc.z))

# 胴の内側を向いた面（空洞＝ソケット）を探す
me = torso.data
inward = []
for poly in me.polygons:
    p = torso.matrix_world @ poly.center
    n = (torso.matrix_world.to_3x3() @ poly.normal).normalized()
    d = p - tc
    if d.length < 1e-6:
        continue
    if d.normalized().dot(n) < -0.55:  # 外向きベクトルと法線が逆＝内側を向く
        inward.append(p)

print("INWARD_COUNT", len(inward))
for side, cond in (("L", lambda p: p.x < -18), ("R", lambda p: p.x > 18)):
    pts = [p for p in inward if cond(p) and 40 < p.z < 100]
    if not pts:
        print("SOCKET_%s none" % side)
        continue
    # z でクラスタリング（肩は高い位置）
    pts.sort(key=lambda p: -p.z)
    top = [p for p in pts if p.z > pts[0].z - 22]
    c = sum(top, Vector()) / len(top)
    spread = max((p - c).length for p in top)
    print("SOCKET_%s n=%d center=(%.2f, %.2f, %.2f) spread=%.1f zrange=%.1f..%.1f"
          % (side, len(top), c.x, c.y, c.z, spread, min(p.z for p in top), max(p.z for p in top)))

# 参考: 胴の肩付近の外形（x が最も外に出ている高さ）
shoulder = [v for v in tv if v.z > 60]
if shoulder:
    outer = max(shoulder, key=lambda v: abs(v.x))
    print("TORSO outer_shoulder=(%.2f, %.2f, %.2f)" % (outer.x, outer.y, outer.z))
print("TORSO bbox_z %.1f..%.1f" % (min(v.z for v in tv), max(v.z for v in tv)))
