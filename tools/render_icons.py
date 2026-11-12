"""Render all of the pause menu's item icons in Blender (headless), modelled from primitives.

usage: blender -b --factory-startup --python tools/render_icons.py -- <out_dir> [size] [only_name ...]

Everything here is modelled from primitives: gold coins with enamel inlays and simple elemental emblems,
cut gems in gold settings, and extruded music notes. No game files are read.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.getcwd(), "renders")
SIZE = int(argv[1]) if len(argv) > 1 else 512
ONLY = set(argv[2:])
os.makedirs(OUT, exist_ok=True)


# ----------------------------------------------------------------------------- scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    engines = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "CYCLES" if "CYCLES" in engines else engines[0]
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = 192
        sc.cycles.transmission_bounces = 16
        sc.cycles.max_bounces = 16
        sc.cycles.transparent_max_bounces = 16
        sc.cycles.use_denoising = True
        try:
            sc.cycles.device = "CPU"
        except Exception:
            pass
    if sc.render.engine.startswith("BLENDER_EEVEE"):
        ee = sc.eevee
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = 128
    sc.render.resolution_x = SIZE
    sc.render.resolution_y = SIZE
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = -0.35
    except Exception:
        pass
    # Studio-ish world: warm top, dark bottom, so metals have something to reflect.
    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.10, 0.08, 0.06, 1)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (1.0, 0.95, 0.86, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.4
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 2.35
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    # Slightly from below-front looking up a touch, like an item shown on a menu board.
    cam.location = (0, -6.0, 0.9)
    cam.rotation_euler = (math.radians(81.5), 0, 0)
    sc.camera = cam

    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        direction = Vector((0, 0, 0)) - Vector(loc)
        lo.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    area("Key", (-3.0, -4.0, 4.0), 900, 3.0, (1.0, 0.95, 0.88))
    area("Fill", (4.0, -3.0, 0.5), 260, 4.0, (0.85, 0.9, 1.0))
    area("Rim", (0.5, 3.5, 3.5), 700, 2.0, (1.0, 0.9, 0.75))
    area("Top", (0.0, -1.0, 6.0), 300, 5.0)
    area("Front", (0.0, -7.0, 2.2), 650, 6.0, (1.0, 0.97, 0.92))  # softbox behind the camera for the metal


def bsdf_mat(name, color, metallic=0.0, rough=0.35, transmission=0.0, ior=1.5, coat=0.0, emission=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

    def setin(names, val):
        for nm in names:
            if nm in p.inputs:
                p.inputs[nm].default_value = val
                return

    setin(["Base Color"], (*color, 1))
    setin(["Metallic"], metallic)
    setin(["Roughness"], rough)
    setin(["Transmission Weight", "Transmission"], transmission)
    setin(["IOR"], ior)
    setin(["Coat Weight", "Clearcoat"], coat)
    if emission is not None:
        setin(["Emission Color", "Emission"], (*emission, 1))
        setin(["Emission Strength"], emit_strength)
    return m


def gold(name="Gold", tint=(1.0, 0.78, 0.36), rough=0.2):
    return bsdf_mat(name, tint, metallic=1.0, rough=rough)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def add_mod_bevel(obj, width=0.02, segments=3):
    md = obj.modifiers.new("Bevel", "BEVEL")
    md.width = width
    md.segments = segments
    md.limit_method = "ANGLE"
    return md


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def cylinder(name, r, depth, z=0.0, verts=96, mat=None, bevel=0.0, rot_x=90):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=verts, radius1=r, radius2=r, depth=depth)
    obj = mesh_obj(name, bm)
    obj.rotation_euler = (math.radians(rot_x), 0, 0)
    obj.location = (0, -z, 0)  # facing the camera (camera looks along +Y)
    if bevel:
        add_mod_bevel(obj, bevel, 4)
    smooth(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def torus(name, major, minor, z=0.0, mat=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=128, minor_segments=24)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = (math.radians(90), 0, 0)
    obj.location = (0, -z, 0)
    smooth(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def extrude_profile(name, pts2d, depth, z, mat, bevel=0.015, holes=()):
    """Extrude a 2D outline (x, y in the coin plane) toward the camera."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "2D"
    curve.fill_mode = "BOTH"
    curve.extrude = depth / 2.0
    curve.bevel_depth = bevel
    curve.bevel_resolution = 3
    for loop in (pts2d,) + tuple(holes):
        sp = curve.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for i, (x, y) in enumerate(loop):
            sp.points[i].co = (x, y, 0, 1)
        sp.use_cyclic_u = True
    obj = link(bpy.data.objects.new(name, curve))
    obj.rotation_euler = (math.radians(90), 0, 0)
    obj.location = (0, -z, 0)
    if mat:
        curve.materials.append(mat)
    return obj


def circle_pts(r, n=64, cx=0.0, cy=0.0, start=0.0):
    return [(cx + r * math.cos(start + 2 * math.pi * i / n), cy + r * math.sin(start + 2 * math.pi * i / n)) for i in range(n)]


def fit_camera(margin=0.05):
    """Centre the model in frame and zoom so its projected bounds fill the square with a small margin."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = sc.camera
    bpy.context.view_layer.update()
    xs, ys = [], []
    for obj in sc.objects:
        if obj.type not in {"MESH", "CURVE"}:
            continue
        for corner in obj.bound_box:
            v = world_to_camera_view(sc, cam, obj.matrix_world @ Vector(corner))
            xs.append(v.x)
            ys.append(v.y)
    if not xs:
        return
    old = cam.data.ortho_scale
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    new = old * span * (1.0 + 2.0 * margin)
    cam.data.shift_x += ((min(xs) + max(xs)) / 2.0 - 0.5) * old / new
    cam.data.shift_y += ((min(ys) + max(ys)) / 2.0 - 0.5) * old / new
    cam.data.ortho_scale = new


def render(name):
    path = os.path.join(OUT, name + ".png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


# ----------------------------------------------------------------------------- emblems (original, simple elemental motifs)
def emblem_sun():  # light: twelve-ray sun
    pts = []
    n = 12
    for i in range(n * 2):
        a = math.pi / 2 + math.pi * i / n
        r = 0.46 if i % 2 == 0 else 0.25
        pts.append((r * math.cos(a), r * math.sin(a)))
    return [pts], [circle_pts(0.13, 48)]


def emblem_leaf():  # forest: a leaf with a centre cut
    pts = []
    for i in range(48):
        t = i / 47.0
        y = -0.48 + 0.96 * t
        w = 0.30 * math.sin(math.pi * t) ** 0.8
        pts.append((w, y))
    for i in range(47, -1, -1):
        t = i / 47.0
        y = -0.48 + 0.96 * t
        w = 0.30 * math.sin(math.pi * t) ** 0.8
        pts.append((-w, y))
    rot = math.radians(-25)
    pts = [(x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)) for x, y in pts]
    vein = [(-0.02, -0.34), (0.02, -0.34), (0.02, 0.32), (-0.02, 0.32)]
    vein = [(x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)) for x, y in vein]
    return [pts], [vein]


def catmull(ctrl, per=10, sharp=()):
    """Closed Catmull-Rom outline through ctrl points; indices in sharp stay pointed."""
    out = []
    n = len(ctrl)
    for i in range(n):
        p0, p1, p2, p3 = ctrl[i - 1], ctrl[i], ctrl[(i + 1) % n], ctrl[(i + 2) % n]
        if i in sharp:
            p0 = p1
        if (i + 1) % n in sharp:
            p3 = p2
        for k in range(per):
            t = k / float(per)
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


def emblem_flame():  # fire: a three-tongued flame
    ctrl = [(0.0, -0.47), (0.24, -0.41), (0.36, -0.22), (0.33, 0.0), (0.37, 0.27), (0.19, 0.12),
            (0.13, 0.30), (0.03, 0.52), (-0.10, 0.30), (-0.17, 0.13), (-0.36, 0.28), (-0.33, 0.0),
            (-0.37, -0.22), (-0.24, -0.41)]
    return [catmull(ctrl, 10, sharp=(4, 7, 10))], []


def emblem_drop():  # water: a droplet with an inner ripple
    pts = []
    for i in range(96):
        t = 2 * math.pi * i / 96
        pts.append((0.34 * math.sin(t) * math.sin(t / 2.0), 0.44 * math.cos(t) - 0.02))
    return [pts], [circle_pts(0.09, 40, -0.06, -0.18)]


def emblem_moon():  # shadow: crescent with three stars
    outer = circle_pts(0.40, 96)
    shapes = [outer]
    holes = [circle_pts(0.33, 96, 0.14, 0.06)]
    return shapes, holes


def emblem_spiral():  # spirit: a spiral sun
    pts_out, pts_in = [], []
    turns = 1.6
    n = 140
    for i in range(n):
        t = i / (n - 1)
        a = math.pi / 2 + t * turns * 2 * math.pi
        r = 0.06 + 0.36 * t
        w = 0.035 + 0.045 * t
        pts_out.append(((r + w) * math.cos(a), (r + w) * math.sin(a)))
        pts_in.append(((r - w) * math.cos(a), (r - w) * math.sin(a)))
    return [pts_out + pts_in[::-1]], []


MEDALLIONS = {
    "medallion_light": ((0.95, 0.78, 0.22), emblem_sun),
    "medallion_forest": ((0.04, 0.45, 0.12), emblem_leaf),
    "medallion_fire": ((0.70, 0.06, 0.04), emblem_flame),
    "medallion_water": ((0.04, 0.20, 0.70), emblem_drop),
    "medallion_shadow": ((0.30, 0.08, 0.50), emblem_moon),
    "medallion_spirit": ((0.85, 0.30, 0.04), emblem_spiral),
}


def build_medallion(color, emblem_fn):
    g = gold()
    g_dark = gold("GoldDark", (0.85, 0.58, 0.22), 0.3)
    enamel = bsdf_mat("Enamel", color, metallic=0.0, rough=0.4, coat=1.0,
                      emission=color, emit_strength=0.12)
    glow = bsdf_mat("Glow", tuple(0.55 + 0.45 * c for c in color), metallic=0.0, rough=0.03,
                    transmission=1.0, ior=1.2, coat=0.0)
    cylinder("Coin", 0.95, 0.16, z=0.0, mat=g_dark, bevel=0.03)
    torus("Rim", 0.90, 0.07, z=0.09, mat=g)
    torus("InnerRim", 0.66, 0.035, z=0.10, mat=g)
    # little bead ring between the rims
    for i in range(36):
        a = 2 * math.pi * i / 36
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.028, segments=16, ring_count=8,
                                             location=(0.78 * math.cos(a), -0.10, 0.78 * math.sin(a)))
        b = bpy.context.active_object
        smooth(b)
        b.data.materials.append(g)
    cylinder("Inlay", 0.64, 0.04, z=0.08, mat=enamel)
    shapes, holes = emblem_fn()
    for i, shp in enumerate(shapes):
        extrude_profile(f"Emblem{i}", shp, 0.07, 0.20, g, 0.012, holes=tuple(holes))


STONES = {
    "stone_kokiri_emerald": "emerald",
    "stone_goron_ruby": "ruby",
    "stone_zoras_sapphire": "sapphire",
}


def gem_mesh(name, radius, height_top, height_bot, sides, mat, loc=(0, 0, 0), scale=(1, 1, 1), rot=(90, 0, 0)):
    """A brilliant-style cut: table, crown and pavilion, flat-shaded facets."""
    bm = bmesh.new()
    table_r = radius * 0.55
    girdle = [bm.verts.new((radius * math.cos(2 * math.pi * i / sides), radius * math.sin(2 * math.pi * i / sides), 0)) for i in range(sides)]
    table = [bm.verts.new((table_r * math.cos(2 * math.pi * (i + 0.5) / sides), table_r * math.sin(2 * math.pi * (i + 0.5) / sides), height_top)) for i in range(sides)]
    culet = bm.verts.new((0, 0, -height_bot))
    bm.faces.new(table)
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((girdle[i], girdle[j], table[i]))
        bm.faces.new((table[i], girdle[j], table[j]))
        bm.faces.new((girdle[j], girdle[i], culet))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = mesh_obj(name, bm)
    obj.rotation_euler = tuple(math.radians(a) for a in rot)
    obj.location = loc
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def gem_mat(name, color):
    return bsdf_mat(name, color, metallic=0.0, rough=0.02, transmission=1.0, ior=1.75, coat=0.0,
                    emission=color, emit_strength=0.35)


def build_stone(kind):
    g = gold()
    if kind == "emerald":
        gem = gem_mat("Emerald", (0.15, 0.85, 0.25))
        gem_mesh("Gem", 0.48, 0.26, 0.42, 16, gem, loc=(0, -0.25, 0.05), scale=(1.0, 1.0, 1.0))
        # curling gold band wrapping round the gem
        pts_o, pts_i = [], []
        for i in range(120):
            t = i / 119.0
            a = math.radians(200) + t * math.radians(300)
            r = 0.55 + 0.25 * t
            w = 0.06 + 0.05 * math.sin(math.pi * t)
            pts_o.append(((r + w) * math.cos(a), (r + w) * math.sin(a) + 0.05))
            pts_i.append(((r - w) * math.cos(a), (r - w) * math.sin(a) + 0.05))
        extrude_profile("Band", pts_o + pts_i[::-1], 0.14, 0.05, g, 0.02)
        torus("Seat", 0.50, 0.05, z=0.05, mat=g).location = (0, -0.05, 0.05)
    elif kind == "ruby":
        gem = gem_mat("Ruby", (0.95, 0.12, 0.12))
        gem_mesh("Gem", 0.40, 0.22, 0.36, 10, gem, loc=(0, -0.25, 0.0), scale=(0.8, 1.0, 1.35), rot=(90, 0, 0))
        # two swept gold wings
        for side in (-1, 1):
            pts = []
            for i in range(40):
                t = i / 39.0
                pts.append((side * (0.30 + 0.62 * t), 0.15 + 0.55 * t * t - 0.25 * t))
            for i in range(39, -1, -1):
                t = i / 39.0
                pts.append((side * (0.30 + 0.50 * t), -0.25 + 0.55 * t * t + 0.10 * t))
            extrude_profile(f"Wing{side}", pts, 0.10, 0.05, g, 0.018)
        torus("Seat", 0.36, 0.045, z=0.05, mat=g).scale = (0.8, 1.35, 1.0)
        # point below
        extrude_profile("Point", [(-0.12, -0.45), (0.12, -0.45), (0.0, -0.85)], 0.10, 0.05, g, 0.018)
    else:
        gem = gem_mat("Sapphire", (0.12, 0.35, 1.0))
        top_gem = gem_mat("Amethyst", (0.55, 0.40, 1.0))
        for i, (x, y, mt) in enumerate([(0.0, 0.36, top_gem), (-0.33, -0.22, gem), (0.33, -0.22, gem)]):
            gem_mesh(f"Gem{i}", 0.27, 0.15, 0.25, 12, mt, loc=(x, -0.22, y))
            t = torus(f"Seat{i}", 0.28, 0.04, z=0.05, mat=g)
            t.location = (x, -0.05, y)
        # gold star frame holding the three gems
        pts = []
        for i in range(6):
            a = math.pi / 2 + i * math.pi / 3
            r = 0.78 if i % 2 == 0 else 0.42
            pts.append((r * math.cos(a), r * math.sin(a) + 0.02))
        extrude_profile("Frame", pts, 0.10, -0.02, g, 0.03)


NOTES = {
    "note_gold": (1.0, 0.78, 0.25),
    "note_green": (0.25, 0.85, 0.35),
    "note_red": (0.95, 0.25, 0.20),
    "note_cyan": (0.25, 0.75, 1.0),
    "note_purple": (0.65, 0.40, 1.0),
}


def build_note(color):
    mat = bsdf_mat("NoteMat", color, metallic=0.85, rough=0.18, coat=0.6, emission=color, emit_strength=0.15)
    # eighth note: an oval head, a stem and a flag
    head = []
    for i in range(64):
        a = 2 * math.pi * i / 64
        x, y = 0.30 * math.cos(a), 0.21 * math.sin(a)
        r = math.radians(-22)
        head.append((x * math.cos(r) - y * math.sin(r) - 0.18, x * math.sin(r) + y * math.cos(r) - 0.55))
    extrude_profile("Head", head, 0.16, 0.0, mat, 0.03)
    stem = [(0.07, -0.50), (0.15, -0.50), (0.15, 0.70), (0.07, 0.70)]
    extrude_profile("Stem", stem, 0.14, 0.0, mat, 0.025)
    flag = []
    for i in range(40):
        t = i / 39.0
        flag.append((0.15 + 0.34 * math.sin(t * math.pi * 0.9), 0.70 - 0.62 * t))
    for i in range(39, -1, -1):
        t = i / 39.0
        flag.append((0.15 + 0.22 * math.sin(t * math.pi * 0.9), 0.48 - 0.50 * t))
    extrude_profile("Flag", flag, 0.12, 0.0, mat, 0.02)


JOBS = []
ITEM_EXPOSURE = float(os.environ.get("ICON_EXPOSURE", "-0.6"))


def main():
    for name, (color, fn) in MEDALLIONS.items():
        JOBS.append((name, lambda c=color, f=fn: build_medallion(c, f)))
    for name, kind in STONES.items():
        JOBS.append((name, lambda k=kind: build_stone(k)))
    for name, color in NOTES.items():
        JOBS.append((name, lambda c=color: build_note(c)))
    items_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_icons_items.py")
    exec(compile(open(items_file, encoding="utf-8").read(), items_file, "exec"), globals())
    names = [n for n, _ in JOBS]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate icon names")
    failed = []
    for name, build in JOBS:
        if ONLY and name not in ONLY:
            continue
        try:
            reset()
            build()
            fit_camera()
            # The key-item metals were tuned brighter; painted and cloth items need less light to keep their colour.
            if not name.startswith(("medallion_", "stone_k", "stone_g", "stone_z", "note_")):
                bpy.context.scene.view_settings.exposure = ITEM_EXPOSURE
            render(name)
        except Exception as err:  # keep going, report at the end
            import traceback
            traceback.print_exc()
            failed.append(name)
    print("FAILED:", failed)


main()
