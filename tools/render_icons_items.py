"""Item models for tools/render_icons.py (executed inside Blender by that script).

Every model is built from primitives, lathes, extruded outlines and curve tubes. The camera looks along +Y,
so the X/Z plane is the picture plane (Z up). Nothing is read from the game.
"""
import math

import bpy
import bmesh
from mathutils import Vector

# Names from render_icons.py that this file uses: bsdf_mat, gold, link, mesh_obj, smooth, extrude_profile,
# circle_pts, catmull, cylinder, torus, gem_mesh, gem_mat, JOBS.


# ----------------------------------------------------------------------------- materials
def _lin(c):
    """Colours in this file are written as screen (sRGB) colours; Blender wants linear values."""
    if c is None:
        return None
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def ibsdf(name, color, emission=None, **kw):
    return bsdf_mat(name, _lin(color), emission=_lin(emission), **kw)


def mat_wood(name="Wood", color=(0.42, 0.24, 0.10), rough=0.55, scale=18.0):
    m = ibsdf(name, color, rough=rough)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale * 0.15, scale * 0.15, scale)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 4.0
    nz.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (color[0] * 0.65, color[1] * 0.6, color[2] * 0.55, 1)
    ramp.color_ramp.elements[1].color = (min(1, color[0] * 1.35), min(1, color[1] * 1.35), min(1, color[2] * 1.3), 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    return m


def mat_steel(name="Steel", tint=(0.82, 0.84, 0.88), rough=0.22):
    return ibsdf(name, tint, metallic=1.0, rough=rough)


def mat_glass(name="Glass", tint=(0.97, 0.99, 1.0), alpha=0.04):
    """See-through glass (alpha, not refraction, so lights still reach what is inside) with a glossy coat."""
    m = ibsdf(name, tint, rough=0.02, coat=1.0)
    nt = m.node_tree
    p = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # Edges of the glass are more opaque than the middle (like real glass), so the outline reads.
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = alpha
    mr.inputs["To Max"].default_value = min(1.0, alpha + 0.65)
    nt.links.new(lw.outputs["Facing"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], p.inputs["Alpha"])
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"  # smooth transparency in EEVEE instead of dithered noise
    return m


def mat_liquid(name, color, glow=0.25):
    return ibsdf(name, color, rough=0.08, coat=1.0, emission=color, emit_strength=glow)


def mat_cloth(name, color, rough=0.85):
    m = ibsdf(name, color, rough=rough)
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for nm in ("Sheen Weight", "Sheen"):
        if nm in p.inputs:
            p.inputs[nm].default_value = 0.6
            break
    return m


def mat_plain(name, color, rough=0.45, coat=0.0, metallic=0.0):
    return ibsdf(name, color, metallic=metallic, rough=rough, coat=coat)


def mat_glow(name, color, strength=3.0):
    return ibsdf(name, color, rough=0.3, emission=color, emit_strength=strength)


# ----------------------------------------------------------------------------- geometry helpers
def lathe(name, profile, mat, segments=72, loc=(0, 0, 0), scale=(1, 1, 1), cap_bottom=True, cap_top=True):
    """Revolve a profile [(radius, z), ...] (bottom to top) around the Z axis."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-5:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
                      for i in range(segments)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(segments):
                bm.faces.new((a[0], b[i], b[(i + 1) % segments]))
        elif len(b) == 1:
            for i in range(segments):
                bm.faces.new((a[i], b[0], a[(i + 1) % segments]))
        else:
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap_bottom and len(rings[0]) > 1:
        bm.faces.new(list(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = mesh_obj(name, bm)
    obj.location = loc
    obj.scale = scale
    smooth(obj)
    sub = obj.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    obj.data.materials.append(mat)
    return obj


def sphere(name, r, mat, loc=(0, 0, 0), scale=(1, 1, 1), seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    smooth(o)
    o.data.materials.append(mat)
    return o


def box(name, size, mat, loc=(0, 0, 0), bevel=0.02, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        md = o.modifiers.new("Bevel", "BEVEL")
        md.width = bevel
        md.segments = 3
    o.data.materials.append(mat)
    return o


def tube(name, pts, radius, mat, closed=False, taper=None, res=4):
    """A round tube along 3D points (x, y, z)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")  # passes through every point, unlike NURBS
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = (p[0], p[1], p[2])
        bp.handle_left_type = bp.handle_right_type = "AUTO"
        if taper:
            bp.radius = taper[i]
    sp.use_cyclic_u = closed
    o = link(bpy.data.objects.new(name, cu))
    cu.materials.append(mat)
    return o


def flat(name, pts2d, depth, mat, y=0.0, bevel=0.012, holes=()):
    """Extruded outline in the picture plane, centred at depth y (negative = toward the camera)."""
    return extrude_profile(name, pts2d, depth, -y, mat, bevel, holes=holes)


def group_pose(rx=0.0, ry=0.0, rz=0.0):
    """Rotate everything in the scene about the origin (degrees): rz turns, ry rolls in the picture plane."""
    sc = bpy.context.scene
    empty = bpy.data.objects.new("Pose", None)
    sc.collection.objects.link(empty)
    for o in list(sc.objects):
        if o.type in {"MESH", "CURVE"} and o.parent is None:
            o.parent = empty
    empty.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))


def ellipse_pts(rx, ry, n=64, cx=0.0, cy=0.0):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def reg(name):
    def deco(fn):
        JOBS.append((name, fn))
        return fn
    return deco


# ----------------------------------------------------------------------------- bottles
BOTTLE_PROFILE = [(0.0, -0.80), (0.40, -0.80), (0.46, -0.72), (0.48, -0.30), (0.46, 0.05), (0.36, 0.30),
                  (0.20, 0.44), (0.17, 0.62), (0.21, 0.66), (0.21, 0.72), (0.15, 0.74)]


def bottle(contents=None):
    glass = mat_glass()
    b = lathe("Bottle", BOTTLE_PROFILE, glass, cap_top=False)
    cork = mat_wood("Cork", (0.62, 0.45, 0.28), 0.8, 30)
    lathe("Cork", [(0.0, 0.62), (0.15, 0.62), (0.17, 0.80), (0.0, 0.84)], cork)
    if contents:
        contents()
    return b


def liquid(color, level=0.0, glow=0.25):
    prof = [(0.0, -0.76), (0.40, -0.76), (0.44, -0.70), (0.45, -0.30), (0.43, min(level, 0.02))]
    if level > 0.05:
        prof.append((0.33, min(level, 0.28)))
    prof.append((0.0, prof[-1][1]))
    lathe("Liquid", prof, mat_liquid("Liq", color, glow))


for _n, _c in (("red", (0.85, 0.05, 0.05)), ("green", (0.10, 0.75, 0.15)), ("blue", (0.10, 0.30, 0.95))):
    reg(f"bottle_{_n}_potion")(lambda c=_c: bottle(lambda: liquid(c, 0.25, 0.08)))

reg("bottle_empty")(lambda: bottle())
reg("bottle_milk")(lambda: bottle(lambda: liquid((0.97, 0.96, 0.92), 0.25, 0.05)))
reg("bottle_half_milk")(lambda: bottle(lambda: liquid((0.97, 0.96, 0.92), -0.30, 0.05)))


@reg("bottle_fairy")
def _fairy():
    def c():
        sphere("Fairy", 0.16, mat_glow("FairyGlow", (1.0, 0.45, 0.80), 1.2), loc=(0, -0.05, -0.25))
        wing = mat_glass("Wing", (1.0, 0.85, 0.95))
        for s in (-1, 1):
            o = sphere(f"Wing{s}", 0.2, wing, loc=(s * 0.2, -0.05, -0.12), scale=(1.0, 0.08, 0.55))
            o.rotation_euler = (0, math.radians(s * 35), 0)
    bottle(c)


@reg("bottle_fish")
def _fish():
    def c():
        lathe("Water", [(0.0, -0.76), (0.40, -0.76), (0.44, -0.70), (0.45, -0.30), (0.43, 0.0), (0.0, 0.0)],
              mat_glass("Water", (0.45, 0.70, 0.95), 0.35))
        fish = mat_plain("Fish", (0.95, 0.55, 0.20), 0.35, coat=0.5)
        sphere("Body", 0.22, fish, loc=(0.03, -0.05, -0.35), scale=(1.3, 0.55, 0.65))
        flat("Tail", [(-0.22, -0.35), (-0.42, -0.22), (-0.42, -0.48)], 0.05, fish, y=-0.05)
        sphere("Eye", 0.03, mat_plain("Eye", (0.02, 0.02, 0.02), 0.1), loc=(0.22, -0.16, -0.31))
    bottle(c)


@reg("bottle_bug")
def _bug():
    def c():
        shell = mat_plain("Shell", (0.15, 0.55, 0.20), 0.2, coat=1.0, metallic=0.3)
        for i, (x, z) in enumerate(((-0.12, -0.55), (0.14, -0.42), (-0.02, -0.25))):
            sphere(f"Bug{i}", 0.09, shell, loc=(x, -0.05, z), scale=(1.0, 0.8, 1.35))
            sphere(f"Head{i}", 0.045, mat_plain("Head", (0.02, 0.02, 0.02), 0.3), loc=(x, -0.05, z + 0.12))
    bottle(c)


@reg("bottle_blue_fire")
def _bluefire():
    def c():
        fire = mat_glow("BlueFire", (0.25, 0.55, 1.0), 10.0)
        for i, (x, h, s) in enumerate(((0.0, 0.55, 0.22), (-0.13, 0.35, 0.14), (0.14, 0.40, 0.15))):
            lathe(f"Flame{i}", [(0.0, -0.72), (s, -0.65), (s * 0.85, -0.45), (s * 0.4, -0.72 + h * 0.85), (0.0, -0.72 + h)],
                  fire, loc=(x, -0.02, 0))
    bottle(c)


def _poe(color, big=False):
    def c():
        glow = mat_glow("PoeGlow", color, 1.0)
        r = 0.24 if big else 0.18
        sphere("Poe", r, glow, loc=(0, -0.05, -0.30), scale=(1.0, 1.0, 1.25))
        eye = mat_plain("PoeEye", (0.02, 0.0, 0.05), 0.4)
        for s in (-1, 1):
            sphere(f"Eye{s}", r * 0.18, eye, loc=(s * r * 0.35, -0.05 - r * 0.92, -0.26))
    bottle(c)


reg("bottle_poe")(lambda: _poe((0.55, 0.25, 0.95)))
reg("bottle_big_poe")(lambda: _poe((0.35, 0.95, 0.75), True))


@reg("bottle_rutos_letter")
def _letter():
    def c():
        paper = mat_plain("Paper", (0.95, 0.92, 0.82), 0.7)
        o = cylinder("Scroll", 0.12, 0.70, z=0.0, mat=paper, rot_x=0)
        o.rotation_euler = (0, math.radians(25), 0)
        o.location = (0.0, 0.0, -0.30)
        ribbon = mat_cloth("Ribbon", (0.15, 0.35, 0.85))
        t = torus("Ribbon", 0.13, 0.025, mat=ribbon)
        t.rotation_euler = (0, math.radians(25 + 90), 0)
        t.location = (0.0, 0.0, -0.30)
    bottle(c)


# ----------------------------------------------------------------------------- weapons
def blade(name, length, width, mat, tip=0.18, y=0.0, fuller=None):
    pts = [(-width / 2, 0), (width / 2, 0), (width / 2, length - tip), (0, length), (-width / 2, length - tip)]
    o = flat(name, pts, 0.05, mat, y=y, bevel=0.012)
    return o


def sword(kind):
    steel = mat_steel()
    g = gold()
    if kind == "kokiri":
        blade("Blade", 1.15, 0.16, steel)
        guard = mat_plain("Guard", (0.55, 0.35, 0.18), 0.4, metallic=0.6)
        flat("Guard", catmull([(-0.32, -0.02), (-0.12, 0.06), (0.0, 0.10), (0.12, 0.06), (0.32, -0.02), (0.0, -0.10)], 6), 0.12, guard)
        grip = mat_wood("Grip", (0.35, 0.20, 0.10))
        cylinder("Grip", 0.055, 0.40, rot_x=0, mat=grip).location = (0, 0, -0.30)
        sphere("Pommel", 0.08, guard, loc=(0, 0, -0.52))
        sphere("Gem", 0.045, gem_mat("RedGem", (0.9, 0.1, 0.1)), loc=(0, -0.08, 0.0))
    elif kind == "master":
        blade("Blade", 1.55, 0.17, steel)
        purple = mat_plain("Hilt", (0.25, 0.20, 0.65), 0.35, metallic=0.5, coat=0.6)
        flat("Guard", catmull([(-0.40, 0.10), (-0.18, 0.0), (0.0, 0.05), (0.18, 0.0), (0.40, 0.10), (0.25, -0.08),
                               (0.0, -0.12), (-0.25, -0.08)], 6), 0.12, purple)
        sphere("Gem", 0.05, gem_mat("YellowGem", (1.0, 0.85, 0.2)), loc=(0, -0.08, -0.02))
        cylinder("Grip", 0.06, 0.45, rot_x=0, mat=purple).location = (0, 0, -0.33)
        sphere("Pommel", 0.09, purple, loc=(0, 0, -0.58), scale=(1, 1, 0.8))
        flat("Mark", [(-0.05, 0.25), (0.05, 0.25), (0.0, 0.34)], 0.06, g, y=-0.01)
    else:  # biggoron / giant's knife
        blade("Blade", 1.90, 0.26, steel, tip=0.30)
        dark = mat_plain("Hilt", (0.15, 0.12, 0.10), 0.4, metallic=0.6)
        flat("Guard", [(-0.42, 0.04), (0.42, 0.04), (0.36, -0.10), (-0.36, -0.10)], 0.14, g)
        cylinder("Grip", 0.065, 0.65, rot_x=0, mat=dark).location = (0, 0, -0.42)
        sphere("Pommel", 0.10, g, loc=(0, 0, -0.78))
    group_pose(ry=-40)


reg("sword_kokiri")(lambda: sword("kokiri"))
reg("sword_master")(lambda: sword("master"))
reg("sword_biggoron")(lambda: sword("biggoron"))


@reg("item_broken_sword")
def _broken():
    steel = mat_steel()
    flat("Blade", [(-0.13, 0), (0.13, 0), (0.13, 0.55), (0.04, 0.62), (-0.02, 0.54), (-0.13, 0.66)], 0.05, steel)
    flat("Guard", [(-0.42, 0.04), (0.42, 0.04), (0.36, -0.10), (-0.36, -0.10)], 0.14, gold())
    cylinder("Grip", 0.065, 0.60, rot_x=0, mat=mat_plain("Hilt", (0.15, 0.12, 0.10), 0.4, metallic=0.6)).location = (0, 0, -0.40)
    flat("Shard", [(-0.10, 0.85), (0.08, 0.80), (0.10, 1.25), (0.0, 1.38), (-0.10, 1.22)], 0.05, steel)
    group_pose(ry=-35)


def shield(kind):
    if kind == "deku":
        wood = mat_wood("DekuWood", (0.50, 0.32, 0.16), 0.6)
        flat("Board", catmull([(0.0, 0.72), (0.52, 0.55), (0.55, -0.05), (0.30, -0.55), (0.0, -0.72), (-0.30, -0.55),
                               (-0.55, -0.05), (-0.52, 0.55)], 8), 0.12, wood, bevel=0.03)
        red = mat_plain("Paint", (0.75, 0.15, 0.10), 0.5)
        pts = []
        for i in range(90):
            a = i / 89.0 * 4 * math.pi
            r = 0.04 + 0.30 * i / 89.0
            pts.append((r * math.cos(a), -0.08, r * math.sin(a)))
        tube("Spiral", pts, 0.035, red)
    elif kind == "hylian":
        steel = mat_steel("ShieldSteel", (0.70, 0.72, 0.78), 0.3)
        blue = mat_plain("Blue", (0.10, 0.20, 0.65), 0.35, coat=0.6)
        outline = catmull([(0.0, 0.80), (0.55, 0.70), (0.62, 0.10), (0.42, -0.45), (0.0, -0.85), (-0.42, -0.45),
                           (-0.62, 0.10), (-0.55, 0.70)], 8)
        flat("Rim", outline, 0.12, steel, bevel=0.03)
        inner = [(x * 0.86, y * 0.86 - 0.02) for x, y in outline]
        flat("Face", inner, 0.06, blue, y=-0.05)
        red = mat_plain("Red", (0.75, 0.10, 0.10), 0.4, coat=0.5)
        flat("Bird", [(0.0, -0.05), (0.32, 0.12), (0.12, -0.08), (0.20, -0.40), (0.0, -0.20), (-0.20, -0.40),
                      (-0.12, -0.08), (-0.32, 0.12)], 0.05, red, y=-0.09)
        g = gold()
        for i, (cx, cy) in enumerate(((0.0, 0.45), (-0.13, 0.25), (0.13, 0.25))):
            flat(f"Tri{i}", [(cx - 0.12, cy - 0.10), (cx + 0.12, cy - 0.10), (cx, cy + 0.10)], 0.05, g, y=-0.09)
    else:  # mirror
        steel = mat_steel("Mirror", (0.95, 0.96, 0.98), 0.03)
        red = mat_plain("Frame", (0.70, 0.12, 0.12), 0.35, coat=0.7)
        outline = catmull([(0.0, 0.85), (0.58, 0.62), (0.58, -0.05), (0.30, -0.55), (0.0, -0.80), (-0.30, -0.55),
                           (-0.58, -0.05), (-0.58, 0.62)], 8)
        flat("Frame", outline, 0.12, red, bevel=0.03)
        flat("Face", [(x * 0.80, y * 0.80) for x, y in outline], 0.06, steel, y=-0.05)
        g = gold()
        flat("Sun", [(0.0, 0.20), (0.10, 0.0), (0.0, -0.20), (-0.10, 0.0)], 0.05, g, y=-0.09)
    group_pose(rz=-18)


for _k in ("deku", "hylian", "mirror"):
    reg(f"shield_{_k}")(lambda k=_k: shield(k))


@reg("item_slingshot")
def _slingshot():
    wood = mat_wood()
    tube("Fork", [(-0.35, 0, 0.55), (-0.30, 0, 0.20), (0.0, 0, -0.05), (0.30, 0, 0.20), (0.35, 0, 0.55)], 0.06, wood)
    tube("Handle", [(0, 0, -0.05), (0, 0, -0.35), (0, 0, -0.70)], 0.075, wood)
    band = mat_plain("Band", (0.55, 0.12, 0.10), 0.6)
    tube("Band", [(-0.35, -0.03, 0.55), (-0.10, -0.12, 0.32), (0.0, -0.15, 0.28), (0.10, -0.12, 0.32), (0.35, -0.03, 0.55)],
         0.02, band)
    sphere("Pouch", 0.07, mat_plain("Leather", (0.40, 0.25, 0.12), 0.7), loc=(0, -0.16, 0.27), scale=(1.3, 0.6, 0.8))
    group_pose(ry=-15)


@reg("item_bow")
def _bow():
    wood = mat_wood("BowWood", (0.48, 0.28, 0.12))
    pts = []
    for i in range(13):
        t = -1 + 2 * i / 12.0
        pts.append((0.38 * (1 - t * t) - 0.06 * (t ** 4), 0, 1.0 * t))
    tube("Limb", pts, 0.05, wood, taper=[1.4 - 0.7 * abs(-1 + 2 * i / 12.0) for i in range(13)])
    tube("String", [(-0.07, 0, -1.0), (-0.07, 0, 1.0)], 0.008, mat_plain("String", (0.9, 0.88, 0.8), 0.6))
    cylinder("Grip", 0.075, 0.30, rot_x=0, mat=mat_plain("Wrap", (0.55, 0.10, 0.10), 0.7)).location = (0.38, 0, 0)
    group_pose(ry=-38)


def arrow(tip_kind=None):
    wood = mat_wood("Shaft", (0.62, 0.45, 0.25))
    tube("Shaft", [(0, 0, -0.95), (0, 0, 0.75)], 0.03, wood)
    fe = mat_plain("Fletch", (0.92, 0.90, 0.85), 0.8)
    for s in (-1, 1):
        flat(f"Fl{s}", [(0, -0.90), (s * 0.12, -0.80), (s * 0.12, -0.55), (0, -0.62)], 0.01, fe)
    if tip_kind is None:
        lathe("Tip", [(0.0, 0.72), (0.08, 0.76), (0.0, 1.0)], mat_steel())
    else:
        col = {"fire": (1.0, 0.35, 0.05), "ice": (0.45, 0.85, 1.0), "light": (1.0, 0.92, 0.45)}[tip_kind]
        lathe("Tip", [(0.0, 0.72), (0.08, 0.76), (0.0, 1.0)], mat_glow("TipGlow", col, 6.0))
        sphere("Aura", 0.17, ibsdf("Aura", col, rough=0.3, transmission=0.8, emission=col, emit_strength=2.0),
               loc=(0, 0, 0.86), scale=(1, 1, 1.4))
    group_pose(ry=-40)


reg("arrow_normal")(lambda: arrow())
reg("arrow_fire")(lambda: arrow("fire"))
reg("arrow_ice")(lambda: arrow("ice"))
reg("arrow_light")(lambda: arrow("light"))


def hookshot(long=False):
    steel = mat_steel()
    dark = mat_plain("Body", (0.18, 0.22, 0.45) if not long else (0.45, 0.12, 0.12), 0.3, metallic=0.6)
    lathe("Barrel", [(0.0, -0.55), (0.13, -0.55), (0.15, -0.30), (0.15, 0.25), (0.11, 0.35), (0.0, 0.35)], dark)
    lathe("Tip", [(0.0, 0.35), (0.14, 0.40), (0.0, 0.85 if long else 0.70)], steel)
    for s in (-1, 1):
        flat(f"Prong{s}", [(s * 0.05, 0.42), (s * 0.28, 0.40), (s * 0.12, 0.62)], 0.05, steel)
    tube("Handle", [(0, 0, -0.30), (0.10, 0, -0.55), (0.18, 0, -0.80)], 0.07, mat_plain("Grip", (0.35, 0.20, 0.10), 0.6))
    torus("Ring", 0.15, 0.03, mat=gold()).location = (0, 0, 0.05)
    group_pose(ry=-40)


reg("item_hookshot")(lambda: hookshot())
reg("item_longshot")(lambda: hookshot(True))


@reg("item_hammer")
def _hammer():
    steel = mat_steel("Head", (0.55, 0.57, 0.62), 0.35)
    g = gold()
    lathe("HeadL", [(0.0, -0.45), (0.28, -0.45), (0.32, -0.38), (0.32, 0.38), (0.28, 0.45), (0.0, 0.45)], steel,
          loc=(0, 0, 0.55)).rotation_euler = (0, math.radians(90), 0)
    for s in (-1, 1):
        t = torus(f"Band{s}", 0.33, 0.04, mat=g)
        t.rotation_euler = (0, math.radians(90), 0)
        t.location = (s * 0.30, 0, 0.55)
    tube("Handle", [(0, 0, 0.30), (0, 0, -0.95)], 0.07, mat_wood("Haft", (0.40, 0.24, 0.12)))
    sphere("Knob", 0.10, g, loc=(0, 0, -0.98))
    group_pose(ry=-30)


@reg("item_boomerang")
def _boomerang():
    wood = mat_wood("BoomWood", (0.58, 0.38, 0.18))
    pts = catmull([(-0.75, 0.45), (-0.55, 0.52), (0.0, 0.05), (0.55, 0.52), (0.75, 0.45), (0.0, -0.25)], 10, sharp=(0, 4))
    flat("Body", pts, 0.08, wood, bevel=0.03)
    red = mat_plain("Red", (0.80, 0.10, 0.10), 0.4, coat=0.5)
    sphere("Gem", 0.07, red, loc=(0, -0.06, -0.05), scale=(1, 0.5, 1))
    green = mat_plain("Green", (0.10, 0.55, 0.20), 0.5)
    for s in (-1, 1):
        flat(f"Wrap{s}", [(s * 0.40, 0.25), (s * 0.48, 0.35), (s * 0.43, 0.39), (s * 0.35, 0.29)], 0.10, green, y=0.0)


@reg("item_bomb")
def _bomb():
    body = mat_plain("BombBody", (0.10, 0.12, 0.35), 0.3, coat=0.8)
    sphere("Bomb", 0.55, body, loc=(0, 0, -0.12))
    lathe("Cap", [(0.0, 0.38), (0.16, 0.38), (0.16, 0.50), (0.0, 0.50)], gold())
    tube("Fuse", [(0, 0, 0.48), (0.05, 0, 0.62), (0.14, 0, 0.70)], 0.03, mat_plain("Fuse", (0.85, 0.80, 0.70), 0.8))
    sphere("Spark", 0.06, mat_glow("Spark", (1.0, 0.7, 0.2), 15.0), loc=(0.16, 0, 0.72))


@reg("item_bombchu")
def _bombchu():
    body = mat_plain("ChuBody", (0.12, 0.15, 0.45), 0.3, coat=0.7)
    sphere("Body", 0.45, body, scale=(1.35, 0.9, 0.75))
    yellow = mat_plain("Yellow", (0.95, 0.75, 0.10), 0.4)
    flat("Face", [(0.30, -0.05), (0.62, 0.10), (0.62, -0.18)], 0.12, yellow, y=-0.25)
    for s in (-1, 1):
        sphere(f"Ear{s}", 0.13, body, loc=(0.25, s * 0.25, 0.30), scale=(0.6, 0.3, 1.0))
        sphere(f"Eye{s}", 0.06, mat_plain("Eye", (0.95, 0.85, 0.2), 0.2), loc=(0.42, s * 0.18 - 0.30, 0.10))
    tube("Tail", [(-0.60, 0, 0), (-0.80, 0, 0.10), (-0.85, 0, 0.30)], 0.03, yellow)
    tube("Key", [(-0.05, 0, 0.32), (-0.05, 0, 0.45)], 0.03, mat_steel())
    torus("KeyRing", 0.08, 0.025, mat=mat_steel()).location = (-0.05, 0, 0.55)
    group_pose(rz=-25)


@reg("item_deku_nut")
def _nut():
    shell = mat_wood("Shell", (0.70, 0.48, 0.24), 0.45, 25)
    lathe("Nut", [(0.0, -0.62), (0.12, -0.58), (0.36, -0.38), (0.46, -0.05), (0.44, 0.20), (0.0, 0.22)], shell)
    cap = mat_wood("Cap", (0.42, 0.26, 0.12), 0.7, 40)
    lathe("Cap", [(0.0, 0.10), (0.50, 0.10), (0.52, 0.22), (0.42, 0.38), (0.20, 0.48), (0.0, 0.50)], cap)
    tube("Stalk", [(0, 0, 0.48), (0.04, 0, 0.62), (0.10, 0, 0.70)], 0.04, cap)
    group_pose(rz=-15, ry=-10)


@reg("item_deku_stick")
def _stick():
    wood = mat_wood("Stick", (0.48, 0.32, 0.16))
    tube("Stick", [(0, 0, -1.0), (0.04, 0, -0.3), (-0.03, 0, 0.4), (0.05, 0, 1.0)], 0.10, wood, taper=[1.15, 1.0, 0.9, 0.75])
    tube("Twig", [(0.0, 0, 0.40), (0.18, 0, 0.58), (0.30, 0, 0.70)], 0.04, wood, taper=[1.0, 0.8, 0.6])
    leaf = mat_plain("Leaf", (0.30, 0.68, 0.18), 0.45)
    o = sphere("Leaf", 0.16, leaf, loc=(0.40, -0.02, 0.84), scale=(0.55, 0.12, 1.0))
    o.rotation_euler = (0, math.radians(35), 0)
    group_pose(ry=-30)


@reg("item_scrub_seed")
def _seed():
    for i, (x, z) in enumerate(((-0.20, -0.10), (0.20, -0.12), (0.0, 0.18))):
        sphere(f"Seed{i}", 0.24, mat_plain(f"Seed{i}", (0.80, 0.70, 0.25), 0.45, coat=0.4), loc=(x, 0, z))


@reg("item_magic_beans")
def _beans():
    pod = mat_plain("Pod", (0.30, 0.65, 0.18), 0.45, coat=0.3)
    sphere("Pod", 0.32, pod, scale=(2.2, 0.6, 0.7))
    cols = [(0.85, 0.15, 0.15), (0.95, 0.80, 0.15), (0.15, 0.45, 0.90)]
    for i, x in enumerate((-0.38, 0.0, 0.38)):
        sphere(f"Bean{i}", 0.13, mat_plain(f"Bean{i}", cols[i], 0.25, coat=0.8), loc=(x, -0.14, 0.03))
    tube("Stem", [(0.68, 0, 0.0), (0.82, 0, 0.12), (0.88, 0, 0.30)], 0.03, pod)
    group_pose(ry=-20)


def crystal(color, inner):
    glass = ibsdf("Crystal", color, rough=0.02, transmission=0.9, ior=1.6, emission=color, emit_strength=0.4)
    gem_mesh("Gem", 0.55, 0.30, 0.65, 8, glass, loc=(0, 0, 0.05), rot=(0, 0, 0))
    inner()


@reg("spell_dins_fire")
def _din():
    crystal((0.95, 0.25, 0.10), lambda: lathe("Flame", [(0.0, -0.35), (0.16, -0.25), (0.10, 0.0), (0.0, 0.25)],
                                              mat_glow("F", (1.0, 0.6, 0.1), 8.0)))


@reg("spell_farores_wind")
def _farore():
    def inner():
        pts = [(0.18 * math.cos(t * 0.35) * (1 - t / 30.0), -0.0, -0.25 + t / 60.0 + 0.0) for t in range(0, 31)]
        pts = [((0.05 + 0.20 * (1 - i / 30.0)) * math.cos(i * 0.6), (0.05 + 0.20 * (1 - i / 30.0)) * math.sin(i * 0.6),
                -0.25 + i * 0.016) for i in range(31)]
        tube("Swirl", pts, 0.025, mat_glow("W", (0.4, 1.0, 0.4), 6.0))
    crystal((0.15, 0.80, 0.25), inner)


@reg("spell_nayrus_love")
def _nayru():
    crystal((0.15, 0.40, 0.95), lambda: gem_mesh("Inner", 0.18, 0.10, 0.25, 4, mat_glow("N", (0.6, 0.8, 1.0), 6.0),
                                               loc=(0, 0, 0.05), rot=(0, 0, 45)))


@reg("item_lens_of_truth")
def _lens():
    g = gold()
    torus("Frame", 0.45, 0.06, mat=g)
    cylinder("Glass", 0.43, 0.04, mat=ibsdf("Lens", (0.85, 0.55, 0.95), rough=0.02, transmission=0.9, ior=1.5))
    eye = mat_plain("EyeRed", (0.75, 0.08, 0.10), 0.4)
    flat("Eye", ellipse_pts(0.22, 0.11), 0.03, eye, y=-0.05)
    sphere("Pupil", 0.07, mat_plain("Pupil", (0.05, 0.02, 0.02), 0.2), loc=(0, -0.08, 0), scale=(1, 0.4, 1))
    tube("Handle", [(0.32, 0, -0.32), (0.55, 0, -0.55), (0.75, 0, -0.75)], 0.06, g)


def ocarina(color, glaze=False):
    m = mat_plain("Ocarina", color, 0.25 if glaze else 0.6, coat=0.8 if glaze else 0.0)
    sphere("Body", 0.45, m, scale=(1.5, 0.85, 0.80))
    mp = cylinder("Mouth", 0.12, 0.50, mat=m, rot_x=0)
    mp.rotation_euler = (0, math.radians(55), 0)
    mp.location = (0.62, 0, 0.30)
    sphere("MouthEnd", 0.12, m, loc=(0.82, 0, 0.44))
    hole = mat_plain("Hole", (0.05, 0.03, 0.02), 0.6)
    for i, (x, z) in enumerate(((-0.40, 0.18), (-0.15, 0.24), (0.10, 0.24), (-0.30, -0.05), (0.0, 0.0))):
        sphere(f"Hole{i}", 0.05, hole, loc=(x, -0.36, z), scale=(1, 0.3, 1))
    if glaze:
        g = gold()
        for i, x in enumerate((0.42, 0.52)):
            flat(f"Mark{i}", [(x - 0.05, 0.08), (x + 0.05, 0.08), (x, 0.18)], 0.05, g, y=-0.32)
    group_pose(ry=12)


reg("item_ocarina_fairy")(lambda: ocarina((0.62, 0.45, 0.25)))
reg("item_ocarina_of_time")(lambda: ocarina((0.12, 0.30, 0.80), True))


@reg("item_amiibo")
def _amiibo():
    base = mat_plain("Base", (0.15, 0.15, 0.18), 0.4, coat=0.5)
    lathe("Base", [(0.0, -0.55), (0.55, -0.55), (0.55, -0.42), (0.0, -0.42)], base)
    lathe("Figure", [(0.0, -0.42), (0.20, -0.42), (0.16, 0.0), (0.22, 0.25), (0.0, 0.70)],
          mat_plain("Fig", (0.30, 0.65, 0.35), 0.4, coat=0.4))
    sphere("Head", 0.17, mat_plain("Skin", (0.95, 0.80, 0.65), 0.5), loc=(0, 0, 0.60))


# ----------------------------------------------------------------------------- trade items
def egg(color, spots=None, scale=1.0):
    shell = mat_plain("Egg", color, 0.35, coat=0.4)
    lathe("Egg", [(0.0, -0.60 * scale), (0.30 * scale, -0.52 * scale), (0.44 * scale, -0.20 * scale),
                  (0.40 * scale, 0.20 * scale), (0.24 * scale, 0.52 * scale), (0.0, 0.66 * scale)], shell)
    if spots:
        sp = mat_plain("Spot", spots, 0.4)
        for i, (x, z) in enumerate(((-0.18, 0.10), (0.15, 0.25), (0.05, -0.20), (-0.20, -0.30), (0.25, -0.05))):
            sphere(f"Spot{i}", 0.06 * scale, sp, loc=(x * scale, -0.38 * scale, z * scale), scale=(1, 0.3, 1))


reg("item_weird_egg")(lambda: egg((0.96, 0.92, 0.82), (0.60, 0.25, 0.20)))
reg("item_pocket_egg")(lambda: egg((0.98, 0.96, 0.90), None, 0.8))


def bird(body_col, comb=(0.85, 0.10, 0.10)):
    body = mat_plain("Bird", body_col, 0.6)
    sphere("Body", 0.45, body, loc=(0, 0, -0.15), scale=(1.15, 0.85, 0.85))
    sphere("Head", 0.25, body, loc=(0.38, 0, 0.35))
    sphere("Tail", 0.22, body, loc=(-0.48, 0, 0.12), scale=(0.6, 0.5, 1.2))
    lathe("Beak", [(0.0, 0.0), (0.07, 0.0), (0.0, 0.18)], mat_plain("Beak", (0.95, 0.65, 0.10), 0.4),
          loc=(0.60, 0, 0.33)).rotation_euler = (0, math.radians(90), 0)
    c = mat_plain("Comb", comb, 0.5)
    for i, x in enumerate((0.30, 0.38, 0.46)):
        sphere(f"Comb{i}", 0.07, c, loc=(x, 0, 0.60))
    sphere("Eye", 0.04, mat_plain("Eye", (0.02, 0.02, 0.02), 0.2), loc=(0.50, -0.20, 0.40))
    for s in (-1, 1):
        tube(f"Leg{s}", [(s * 0.10, 0, -0.50), (s * 0.12, 0, -0.75)], 0.03, mat_plain("Leg", (0.95, 0.65, 0.10), 0.5))
    group_pose(rz=-20)


reg("item_cucco")(lambda: bird((0.97, 0.95, 0.90)))
reg("item_cojiro")(lambda: bird((0.30, 0.45, 0.85)))


@reg("item_zeldas_letter")
def _zletter():
    paper = mat_plain("Envelope", (0.96, 0.93, 0.85), 0.7)
    box("Env", (1.3, 0.04, 0.85), paper, bevel=0.01)
    flat("Flap", [(-0.65, 0.42), (0.65, 0.42), (0.0, -0.05)], 0.02, mat_plain("Flap", (0.92, 0.88, 0.78), 0.7), y=-0.03)
    lathe("Seal", [(0.0, 0.0), (0.16, 0.0), (0.16, 0.05), (0.0, 0.06)], mat_plain("Wax", (0.75, 0.10, 0.15), 0.3, coat=0.6),
          loc=(0, -0.06, -0.05)).rotation_euler = (math.radians(90), 0, 0)
    group_pose(ry=-10, rz=-15)


@reg("item_odd_mushroom")
def _mushroom():
    lathe("Stem", [(0.0, -0.55), (0.18, -0.55), (0.14, 0.0), (0.0, 0.05)], mat_plain("Stem", (0.92, 0.88, 0.78), 0.6))
    cap = mat_plain("Cap", (0.45, 0.20, 0.55), 0.4, coat=0.5)
    lathe("Cap", [(0.0, -0.05), (0.55, -0.05), (0.50, 0.15), (0.30, 0.38), (0.0, 0.45)], cap)
    for i, (x, z) in enumerate(((-0.25, 0.18), (0.20, 0.25), (0.02, 0.38), (0.38, 0.05))):
        sphere(f"Dot{i}", 0.06, mat_plain("Dot", (0.95, 0.95, 0.75), 0.4), loc=(x, -0.30, z), scale=(1, 0.4, 1))


@reg("item_odd_potion")
def _oddpotion():
    glass = mat_glass()
    lathe("Flask", [(0.0, -0.60), (0.35, -0.60), (0.48, -0.30), (0.45, 0.0), (0.15, 0.30), (0.13, 0.55), (0.16, 0.60)],
          glass, cap_top=False)
    lathe("Liquid", [(0.0, -0.56), (0.33, -0.56), (0.44, -0.30), (0.40, -0.05), (0.0, -0.05)],
          mat_liquid("Odd", (0.35, 0.65, 0.15), 0.4))
    lathe("Stopper", [(0.0, 0.50), (0.13, 0.50), (0.15, 0.72), (0.0, 0.75)], mat_wood("Stop", (0.45, 0.28, 0.12)))


@reg("item_poachers_saw")
def _saw():
    steel = mat_steel()
    teeth = [(-0.85, -0.10)]
    for i in range(15):
        x = -0.85 + i * 0.11
        teeth += [(x + 0.055, -0.20), (x + 0.11, -0.10)]
    pts = teeth + [(0.85, 0.22), (-0.85, 0.12)]
    flat("Blade", pts, 0.03, steel, bevel=0.005)
    wood = mat_wood("SawGrip", (0.50, 0.30, 0.14))
    flat("Handle", catmull([(0.80, 0.30), (1.15, 0.38), (1.20, 0.0), (1.10, -0.20), (0.80, -0.10)], 6), 0.12, wood, bevel=0.03)
    group_pose(ry=-20)


@reg("item_prescription")
def _prescription():
    paper = mat_plain("Paper", (0.95, 0.92, 0.82), 0.7)
    box("Sheet", (0.95, 0.03, 1.15), paper, bevel=0.005)
    for s, z in ((-1, 0.58), (1, -0.58)):
        o = cylinder(f"Roll{s}", 0.07, 1.0, mat=paper, rot_x=0)
        o.rotation_euler = (0, math.radians(90), 0)
        o.location = (0, 0, z)
    ink = mat_plain("Ink", (0.15, 0.15, 0.30), 0.6)
    for i in range(5):
        box(f"Line{i}", (0.65 - 0.1 * (i % 2), 0.01, 0.035), ink, loc=(0, -0.03, 0.30 - i * 0.15), bevel=0.0)
    group_pose(ry=-10, rz=-15)


@reg("item_eyeball_frog")
def _frog():
    skin = mat_plain("Frog", (0.30, 0.65, 0.20), 0.4, coat=0.5)
    sphere("Body", 0.45, skin, scale=(1.2, 0.95, 0.75))
    eyew = mat_plain("EyeW", (0.97, 0.97, 0.95), 0.2, coat=0.6)
    pupil = mat_plain("Pupil", (0.05, 0.05, 0.05), 0.2)
    for s in (-1, 1):
        sphere(f"Eye{s}", 0.22, eyew, loc=(s * 0.25, -0.15, 0.32))
        sphere(f"Pupil{s}", 0.09, pupil, loc=(s * 0.25, -0.35, 0.34))
        sphere(f"Foot{s}", 0.15, skin, loc=(s * 0.45, -0.10, -0.32), scale=(1.4, 1.0, 0.4))


@reg("item_eye_drops")
def _eyedrops():
    glass = mat_glass()
    lathe("Vial", [(0.0, -0.60), (0.25, -0.60), (0.28, -0.50), (0.28, 0.20), (0.12, 0.35), (0.12, 0.50)], glass, cap_top=False)
    lathe("Drops", [(0.0, -0.56), (0.25, -0.56), (0.26, 0.10), (0.0, 0.10)], mat_liquid("Drops", (0.30, 0.75, 0.95), 0.4))
    lathe("Bulb", [(0.0, 0.45), (0.15, 0.45), (0.17, 0.62), (0.12, 0.80), (0.0, 0.85)],
          mat_plain("Rubber", (0.80, 0.15, 0.15), 0.45, coat=0.4))


@reg("item_claim_check")
def _claim():
    paper = mat_plain("Ticket", (0.93, 0.85, 0.60), 0.6)
    pts = [(-0.75, -0.40), (0.75, -0.40), (0.75, -0.10), (0.65, 0.0), (0.75, 0.10), (0.75, 0.40), (-0.75, 0.40),
           (-0.75, 0.10), (-0.65, 0.0), (-0.75, -0.10)]
    flat("Ticket", pts, 0.03, paper, bevel=0.005)
    red = mat_plain("Stamp", (0.70, 0.12, 0.10), 0.5)
    flat("Stamp", ellipse_pts(0.17, 0.17, 40, 0.35, 0.0), 0.02, red, y=-0.02, holes=(ellipse_pts(0.12, 0.12, 40, 0.35, 0.0),))
    ink = mat_plain("Ink", (0.20, 0.15, 0.10), 0.6)
    for i in range(3):
        box(f"Line{i}", (0.65, 0.01, 0.04), ink, loc=(-0.25, -0.03, 0.18 - i * 0.16), bevel=0.0)
    group_pose(ry=-12, rz=-15)


# ----------------------------------------------------------------------------- equipment: tunics, boots, masks
def tunic(color):
    cloth = mat_cloth("Tunic", color)
    outline = catmull([(-0.20, 0.78), (-0.48, 0.70), (-0.66, 0.50), (-0.60, 0.30), (-0.42, 0.34), (-0.40, -0.10),
                       (-0.58, -0.80), (-0.30, -0.86), (0.0, -0.82), (0.30, -0.86), (0.58, -0.80), (0.40, -0.10),
                       (0.42, 0.34), (0.60, 0.30), (0.66, 0.50), (0.48, 0.70), (0.20, 0.78), (0.0, 0.48)], 6,
                      sharp=(4, 6, 10, 12, 17))
    flat("Body", outline, 0.30, cloth, bevel=0.08)
    dark = mat_cloth("Trim", tuple(c * 0.6 for c in color))
    flat("Collar", [(-0.20, 0.80), (0.0, 0.46), (0.20, 0.80), (0.12, 0.82), (0.0, 0.60), (-0.12, 0.82)], 0.34, dark, bevel=0.02)
    belt = mat_plain("Belt", (0.38, 0.22, 0.10), 0.5)
    box("Belt", (0.92, 0.36, 0.14), belt, loc=(0, 0, -0.14), bevel=0.03)
    box("Buckle", (0.18, 0.06, 0.18), gold(), loc=(0, -0.20, -0.14), bevel=0.02)
    box("Strap", (0.10, 0.36, 0.95), belt, loc=(0.0, 0.0, 0.30), rot=(0, 30, 0), bevel=0.02)
    group_pose(rz=-12)


reg("tunic_kokiri")(lambda: tunic((0.15, 0.50, 0.15)))
reg("tunic_goron")(lambda: tunic((0.65, 0.10, 0.08)))
reg("tunic_zora")(lambda: tunic((0.10, 0.25, 0.70)))


def boot(kind):
    if kind == "kokiri":
        m = mat_plain("Leather", (0.40, 0.24, 0.12), 0.6)
    elif kind == "iron":
        m = mat_steel("Iron", (0.45, 0.47, 0.52), 0.4)
    else:
        m = mat_plain("Hover", (0.72, 0.60, 0.30), 0.35, metallic=0.6)
    outline = catmull([(-0.32, 0.62), (0.16, 0.62), (0.18, 0.10), (0.24, -0.18), (0.55, -0.28), (0.72, -0.45),
                       (0.68, -0.62), (0.10, -0.64), (-0.34, -0.62), (-0.36, -0.20)], 8, sharp=(0, 1, 8))
    flat("Boot", outline, 0.36, m, bevel=0.09)
    cuff_col = (0.55, 0.38, 0.22) if kind == "kokiri" else ((0.35, 0.36, 0.40) if kind == "iron" else (0.95, 0.90, 0.80))
    flat("Cuff", catmull([(-0.40, 0.80), (0.22, 0.80), (0.24, 0.58), (-0.42, 0.58)], 4), 0.42, mat_plain("Cuff", cuff_col, 0.6), bevel=0.05)
    flat("Sole", catmull([(-0.38, -0.60), (0.70, -0.58), (0.76, -0.70), (-0.40, -0.74)], 4), 0.40, mat_plain("Sole", (0.15, 0.10, 0.08), 0.6), bevel=0.02)
    if kind == "iron":
        for i, z in enumerate((0.45, 0.15)):
            box(f"Band{i}", (0.55, 0.36, 0.06), mat_steel("Band", (0.30, 0.32, 0.36), 0.3), loc=(-0.07, 0, z), bevel=0.01)
    if kind == "hover":
        wing = mat_plain("Wing", (0.95, 0.95, 0.98), 0.4)
        flat("Wing", catmull([(-0.30, 0.40), (-0.75, 0.70), (-0.65, 0.45), (-0.85, 0.35), (-0.60, 0.20), (-0.30, 0.15)], 6,
                             sharp=(1, 3)), 0.05, wing, y=-0.18)
    group_pose(rz=-20)


for _k in ("kokiri", "iron", "hover"):
    reg(f"boots_{_k}")(lambda k=_k: boot(k))


def mask_face(color, rough=0.45):
    m = mat_plain("Mask", color, rough, coat=0.3)
    o = sphere("Face", 0.62, m, scale=(1.0, 0.45, 1.15))
    return m


def eye_holes(xs=(-0.22, 0.22), z=0.15, rx=0.10, rz=0.08, color=(0.05, 0.04, 0.03)):
    m = mat_plain("Hole", color, 0.6)
    for i, x in enumerate(xs):
        sphere(f"EyeHole{i}", 1.0, m, loc=(x, -0.27, z), scale=(rx, 0.03, rz))


@reg("mask_keaton")
def _keaton():
    m = mask_face((0.95, 0.70, 0.20))
    for s in (-1, 1):
        lathe(f"Ear{s}", [(0.0, 0.0), (0.22, 0.0), (0.0, 0.55)], m, loc=(s * 0.38, 0.0, 0.48)).rotation_euler = (0, math.radians(s * -20), 0)
    white = mat_plain("White", (0.97, 0.95, 0.90), 0.5)
    sphere("Muzzle", 0.30, white, loc=(0, -0.22, -0.28), scale=(1.0, 0.6, 0.7))
    sphere("Nose", 0.07, mat_plain("Nose", (0.1, 0.06, 0.04), 0.3), loc=(0, -0.42, -0.18))
    eye_holes(rx=0.12, rz=0.05)


@reg("mask_skull")
def _skull():
    bone = (0.92, 0.90, 0.82)
    m = mask_face(bone, 0.6)
    for s in (-1, 1):
        tube(f"Horn{s}", [(s * 0.40, 0, 0.45), (s * 0.70, 0, 0.75), (s * 0.70, 0, 1.05)], 0.09, m, taper=[1.0, 0.7, 0.2])
    eye_holes(rx=0.15, rz=0.12)
    teeth = mat_plain("Teeth", (0.97, 0.96, 0.92), 0.5)
    for i in range(5):
        box(f"Tooth{i}", (0.08, 0.05, 0.14), teeth, loc=(-0.24 + i * 0.12, -0.26, -0.45), bevel=0.01)


@reg("mask_spooky")
def _spooky():
    m = mask_face((0.55, 0.45, 0.30), 0.7)
    eye_holes(rx=0.13, rz=0.17, z=0.12)
    mouth = mat_plain("Mouth", (0.05, 0.03, 0.02), 0.6)
    sphere("Mouth", 1.0, mouth, loc=(0, -0.27, -0.35), scale=(0.12, 0.03, 0.18))


@reg("mask_bunny")
def _bunny():
    fur = mat_cloth("Fur", (0.80, 0.55, 0.30))
    pink = mat_cloth("Pink", (0.95, 0.65, 0.70))
    sphere("Cap", 0.55, fur, scale=(1.0, 0.8, 0.7))
    for s in (-1, 1):
        e = sphere(f"Ear{s}", 0.20, fur, loc=(s * 0.26, 0, 0.70), scale=(0.65, 0.35, 2.0))
        e.rotation_euler = (0, math.radians(s * 12), 0)
        i = sphere(f"Inner{s}", 0.13, pink, loc=(s * 0.27, -0.07, 0.70), scale=(0.6, 0.2, 1.9))
        i.rotation_euler = (0, math.radians(s * 12), 0)


@reg("mask_goron")
def _goron():
    m = mask_face((0.65, 0.48, 0.30), 0.7)
    hair = mat_plain("Hair", (0.95, 0.92, 0.85), 0.8)
    sphere("Brow", 0.18, hair, loc=(0, -0.22, 0.35), scale=(2.6, 0.6, 0.6))
    eye_holes(z=0.12, rx=0.08, rz=0.07)
    sphere("Nose", 0.12, m, loc=(0, -0.30, -0.05), scale=(1.4, 1.0, 1.0))
    sphere("Beard", 0.25, hair, loc=(0, -0.20, -0.45), scale=(1.6, 0.6, 0.6))


@reg("mask_zora")
def _zora():
    m = mask_face((0.45, 0.70, 0.90), 0.35)
    fin = mat_plain("Fin", (0.85, 0.90, 0.95), 0.3, coat=0.4)
    lathe("Fin", [(0.0, 0.0), (0.18, 0.0), (0.0, 0.85)], fin, loc=(0, 0.20, 0.45)).rotation_euler = (math.radians(-35), 0, 0)
    eye_holes(rx=0.12, rz=0.10, color=(0.6, 0.1, 0.4))
    sphere("Lips", 0.10, mat_plain("Lips", (0.30, 0.45, 0.70), 0.4), loc=(0, -0.26, -0.35), scale=(1.8, 0.5, 0.6))


@reg("mask_gerudo")
def _gerudo():
    m = mask_face((0.70, 0.45, 0.28), 0.45)
    hair = mat_plain("Hair", (0.85, 0.15, 0.08), 0.6)
    sphere("Hair", 0.62, hair, loc=(0, 0.05, 0.35), scale=(1.05, 0.55, 0.65))
    sphere("Tail", 0.18, hair, loc=(0, 0.05, 0.95), scale=(0.8, 0.8, 1.4))
    lathe("Jewel", [(0.0, 0.0), (0.08, 0.0), (0.0, 0.05)], gem_mat("J", (0.2, 0.9, 0.4)), loc=(0, -0.27, 0.32)).rotation_euler = (math.radians(90), 0, 0)
    eye_holes(rx=0.11, rz=0.06)
    sphere("Lips", 0.08, mat_plain("Lips", (0.75, 0.15, 0.20), 0.3), loc=(0, -0.27, -0.38), scale=(1.8, 0.5, 0.6))


@reg("mask_truth")
def _truth():
    m = mask_face((0.97, 0.95, 0.90), 0.4)
    red = mat_plain("Red", (0.80, 0.08, 0.10), 0.4)
    flat("EyeRing", ellipse_pts(0.30, 0.18), 0.02, red, y=-0.28, holes=(ellipse_pts(0.24, 0.13),))
    sphere("Pupil", 0.10, red, loc=(0, -0.28, 0.0), scale=(1, 0.3, 1))
    for i, x in enumerate((-0.30, 0.0, 0.30)):
        flat(f"Tri{i}", [(x - 0.08, 0.38), (x + 0.08, 0.38), (x, 0.52)], 0.02, red, y=-0.24)
    flat("Mouth", [(-0.20, -0.40), (0.20, -0.40), (0.0, -0.52)], 0.02, red, y=-0.26)


@reg("mask_bonus")
def _bonusmask():
    m = mask_face((0.80, 0.80, 0.85), 0.3)
    eye_holes(rx=0.10, rz=0.10)
    flat("Star", [(0.0, 0.62), (0.07, 0.48), (0.22, 0.47), (0.10, 0.38), (0.15, 0.24), (0.0, 0.33), (-0.15, 0.24),
                  (-0.10, 0.38), (-0.22, 0.47), (-0.07, 0.48)], 0.03, gold(), y=-0.20)


@reg("stone_of_agony")
def _agony():
    stone = mat_plain("Stone", (0.45, 0.45, 0.50), 0.75)
    gem_mesh("Stone", 0.55, 0.35, 0.55, 7, stone, rot=(90, 0, 15))
    g = gold()
    flat("Eye", ellipse_pts(0.22, 0.12), 0.03, g, y=-0.36, holes=(ellipse_pts(0.17, 0.08),))
    sphere("Pupil", 0.06, mat_glow("Pupil", (0.9, 0.2, 0.2), 4.0), loc=(0, -0.38, 0), scale=(1, 0.4, 1))


# ----------------------------------------------------------------------------- collection page
@reg("token_skulltula")
def _token():
    g = gold("TokenGold", (1.0, 0.80, 0.30), 0.25)
    sphere("Skull", 0.50, g, scale=(1.0, 0.5, 0.95))
    sphere("Jaw", 0.30, g, loc=(0, 0, -0.42), scale=(1.0, 0.5, 0.55))
    hole = mat_plain("Socket", (0.25, 0.18, 0.10), 0.5)
    for s in (-1, 1):
        sphere(f"Eye{s}", 0.13, hole, loc=(s * 0.20, -0.22, -0.02), scale=(1.0, 0.3, 1.1))
    sphere("Nose", 0.05, hole, loc=(0, -0.24, -0.22), scale=(1.0, 0.3, 1.3))


def heart_pts(scale=1.0):
    pts = []
    for i in range(80):
        t = 2 * math.pi * i / 80
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 17.0 * 0.62 * scale, y / 17.0 * 0.62 * scale + 0.05))
    return pts


def heart_solid(m, scale=1.0, y=0.0):
    """A puffy 3D heart: two lobes and a rounded point."""
    s = scale
    for side in (-1, 1):
        sphere(f"Lobe{side}", 0.36 * s, m, loc=(side * 0.27 * s, y, 0.18 * s), scale=(1.0, 0.75, 1.0))
    return lathe("Point", [(0.0, -0.62 * s), (0.10 * s, -0.55 * s), (0.42 * s, -0.10 * s), (0.50 * s, 0.10 * s), (0.0, 0.16 * s)], m,
                 loc=(0, y, 0), scale=(1.15, 0.72, 1.0))


@reg("heart_full")
def _heart():
    m = ibsdf("Heart", (0.92, 0.10, 0.18), rough=0.12, coat=1.0, emission=(0.9, 0.1, 0.2), emit_strength=0.15)
    heart_solid(m)


@reg("heart_full_dd")
def _heart_dd():
    m = ibsdf("Heart", (0.92, 0.10, 0.18), rough=0.12, coat=1.0, emission=(0.9, 0.1, 0.2), emit_strength=0.15)
    heart_solid(m, 0.82, y=-0.05)
    rim = ibsdf("Ward", (0.97, 0.97, 1.0), rough=0.15, coat=1.0, emission=(1, 1, 1), emit_strength=0.3)
    heart_solid(rim, 1.0, y=0.12)


def magic_jar(double=False):
    glass = mat_glass()
    lathe("Jar", [(0.0, -0.55), (0.40, -0.55), (0.45, -0.30), (0.40, 0.20), (0.22, 0.38), (0.22, 0.50)], glass, cap_top=False)
    lathe("Magic", [(0.0, -0.51), (0.40, -0.51), (0.43, -0.30), (0.38, 0.15), (0.0, 0.15)],
          mat_liquid("Magic", (0.15, 0.85, 0.25), 0.8))
    lathe("Lid", [(0.0, 0.45), (0.26, 0.45), (0.26, 0.58), (0.0, 0.62)], gold())
    if double:
        glass2 = mat_glass()
        for o in list(bpy.context.scene.objects):
            if o.type == "MESH":
                o.location.x -= 0.28
        lathe("Jar2", [(0.0, -0.55), (0.40, -0.55), (0.45, -0.30), (0.40, 0.20), (0.22, 0.38), (0.22, 0.50)], glass2,
              cap_top=False, loc=(0.32, 0.25, 0))
        lathe("Magic2", [(0.0, -0.51), (0.40, -0.51), (0.43, -0.30), (0.38, 0.15), (0.0, 0.15)],
              mat_liquid("Magic2", (0.15, 0.85, 0.25), 0.8), loc=(0.32, 0.25, 0))
        lathe("Lid2", [(0.0, 0.45), (0.26, 0.45), (0.26, 0.58), (0.0, 0.62)], gold(), loc=(0.32, 0.25, 0))


reg("magic_meter")(lambda: magic_jar())
reg("magic_double")(lambda: magic_jar(True))


def gauntlet(kind):
    if kind == "goron":
        m = mat_plain("Bracelet", (0.75, 0.55, 0.20), 0.3, metallic=0.9)
        t = torus("Band", 0.45, 0.13, mat=m)
        t.rotation_euler = (math.radians(70), 0, 0)
        sphere("Gem", 0.13, gem_mat("Ruby", (0.9, 0.1, 0.1)), loc=(0, -0.45, 0.0), scale=(1, 0.6, 1))
        return
    col = (0.80, 0.82, 0.88) if kind == "silver" else (1.0, 0.78, 0.30)
    m = ibsdf("Metal", col, metallic=1.0, rough=0.2)
    lathe("Cuff", [(0.0, -0.95), (0.42, -0.95), (0.46, -0.85), (0.40, -0.30), (0.0, -0.28)], m, scale=(1.0, 0.75, 1.0))
    sphere("Hand", 0.42, m, loc=(0, 0, 0.0), scale=(0.95, 0.55, 0.85))
    for i, (x, h) in enumerate(((-0.27, 0.62), (-0.09, 0.72), (0.09, 0.70), (0.27, 0.58))):
        tube(f"Finger{i}", [(x, 0.0, 0.20), (x, -0.06, h - 0.10), (x, -0.16, h)], 0.095, m)
        sphere(f"Tip{i}", 0.095, m, loc=(x, -0.16, h))
    tube("Thumb", [(-0.30, 0.0, -0.10), (-0.48, -0.06, 0.08), (-0.55, -0.14, 0.26)], 0.10, m)
    sphere("ThumbTip", 0.10, m, loc=(-0.55, -0.14, 0.26))
    trim = mat_plain("Trim", (0.30, 0.20, 0.10), 0.5)
    t = torus("Band", 0.43, 0.05, mat=trim)
    t.rotation_euler = (0, 0, 0)
    t.scale = (1.0, 0.75, 1.0)
    t.location = (0, 0, -0.32)
    sphere("Gem", 0.10, gem_mat("Gem", (0.2, 0.5, 1.0) if kind == "silver" else (0.9, 0.15, 0.15)), loc=(0, -0.34, -0.62))
    group_pose(rz=-15)


reg("gear_goron_bracelet")(lambda: gauntlet("goron"))
reg("gear_silver_gauntlets")(lambda: gauntlet("silver"))
reg("gear_golden_gauntlets")(lambda: gauntlet("golden"))


def scale_item(col):
    m = ibsdf("Scale", col, metallic=0.9, rough=0.15, coat=0.6)
    flat("Scale", catmull([(0.0, 0.75), (0.45, 0.35), (0.40, -0.25), (0.0, -0.70), (-0.40, -0.25), (-0.45, 0.35)], 8,
                          sharp=(0, 3)), 0.12, m, bevel=0.05)
    for i in range(4):
        z = 0.40 - i * 0.28
        tube(f"Ridge{i}", [(-0.30 + 0.05 * i, -0.08, z), (0.0, -0.10, z - 0.10), (0.30 - 0.05 * i, -0.08, z)], 0.02, m)


reg("scale_silver")(lambda: scale_item((0.82, 0.85, 0.92)))
reg("scale_golden")(lambda: scale_item((1.0, 0.78, 0.30)))


@reg("item_gerudo_card")
def _card():
    card = mat_plain("Card", (0.88, 0.70, 0.30), 0.35, metallic=0.5, coat=0.6)
    box("Card", (1.30, 0.05, 0.85), card, bevel=0.03)
    purple = mat_plain("Emblem", (0.45, 0.15, 0.55), 0.4)
    flat("Emblem", [(0.0, 0.28), (0.24, 0.0), (0.0, -0.28), (-0.24, 0.0)], 0.03, purple, y=-0.04)
    flat("Moon", catmull([(-0.06, 0.12), (0.10, 0.06), (0.10, -0.06), (-0.06, -0.12), (0.02, 0.0)], 6), 0.03, gold(), y=-0.06)
    group_pose(ry=-8, rz=-15)


def wallet(col, size=1.0):
    leather = mat_plain("Wallet", col, 0.6)
    sphere("Bag", 0.55 * size, leather, loc=(0, 0, -0.10), scale=(1.0, 0.85, 0.95))
    lathe("Neck", [(0.0, 0.30), (0.22, 0.30), (0.16, 0.42), (0.26, 0.58), (0.0, 0.60)], leather)
    tube("Cord", [(-0.22, -0.05, 0.40), (0.0, -0.20, 0.38), (0.22, -0.05, 0.40)], 0.035, mat_plain("Cord", (0.85, 0.75, 0.30), 0.5))
    gem_mesh("Rupee", 0.14, 0.06, 0.06, 6, gem_mat("Rupee", (0.1, 0.85, 0.2)), loc=(0, -0.50 * size, -0.10), rot=(90, 0, 90))


reg("wallet_adults")(lambda: wallet((0.55, 0.30, 0.15)))
reg("wallet_giants")(lambda: wallet((0.70, 0.20, 0.25), 1.08))
reg("wallet_tycoons")(lambda: wallet((0.40, 0.15, 0.55), 1.15))


def bag(kind):
    if kind == "bomb":
        m = mat_plain("BombBag", (0.55, 0.35, 0.20), 0.6)
        sphere("Bag", 0.55, m, scale=(1.0, 0.8, 0.9))
        face = mat_plain("Face", (0.15, 0.15, 0.20), 0.4)
        for s in (-1, 1):
            sphere(f"Eye{s}", 0.07, face, loc=(s * 0.18, -0.43, 0.10))
        sphere("Mouth", 0.10, face, loc=(0, -0.43, -0.15), scale=(1.5, 0.4, 0.6))
        tube("Strap", [(-0.50, 0, 0.20), (0, -0.05, 0.75), (0.50, 0, 0.20)], 0.04, mat_plain("Strap", (0.35, 0.20, 0.10), 0.5))
    elif kind == "bullet":
        m = mat_plain("SeedBag", (0.45, 0.60, 0.25), 0.7)
        sphere("Bag", 0.50, m, loc=(0, 0, -0.10), scale=(1.0, 0.8, 1.0))
        lathe("Neck", [(0.0, 0.30), (0.20, 0.30), (0.14, 0.45), (0.28, 0.60), (0.0, 0.62)], m)
        for i, (x, z) in enumerate(((-0.12, 0.62), (0.08, 0.66), (0.0, 0.70))):
            sphere(f"Seed{i}", 0.08, mat_plain("Seed", (0.85, 0.75, 0.30), 0.4), loc=(x, 0, z))
    else:
        leather = mat_plain("Quiver", (0.45, 0.25, 0.12), 0.6)
        lathe("Quiver", [(0.0, -0.80), (0.22, -0.80), (0.26, -0.50), (0.28, 0.40), (0.0, 0.40)], leather, cap_top=False)
        wood = mat_wood("Shaft", (0.62, 0.45, 0.25))
        fe = mat_plain("Fletch", (0.85, 0.20, 0.15), 0.7)
        for i, x in enumerate((-0.12, 0.0, 0.12)):
            tube(f"Shaft{i}", [(x, 0, 0.0), (x * 1.5, 0, 0.75)], 0.025, wood)
            sphere(f"Fl{i}", 0.06, fe, loc=(x * 1.5, 0, 0.78), scale=(0.6, 0.6, 1.6))
        torus("Rim", 0.27, 0.035, mat=gold()).location = (0, 0, 0.40)
        group_pose(ry=-25)


for _k in ("bomb", "bullet", "quiver"):
    reg(f"bag_{_k}")(lambda k=_k: bag(k))
