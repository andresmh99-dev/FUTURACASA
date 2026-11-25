"""
Generador arquitectónico 1:1 EXACTO en Blender 5 (Cycles + OptiX GPU)
Casa Lote 8, Manzana 147, Fracc. México, Morelia, Mich.

IMPORTA LA ESTRUCTURA ARQUITECTÓNICA REAL 1:1 (`assets/L8_MEXICO_SKP_3.glb`,
alineada exactamente a -31.15° -> Lote trapecial 15.07 m × 20.60 m, alturas reales
Sótano Z=-2.89 m / 1ª Planta Z=-0.14 m / Techo Z=+3.06..+3.28 m),
limpia aristas CAD y mosaico satelital, aplica materiales PBR de Cycles y amuebla
con precisión milimétrica TODOS los cuartos reales del proyecto:
- SÓTANO (Z = -2.89 m): Recámara Principal + Vestidor, Recámara 1, Recámara 2 / Sala TV,
  escalera de madera y Patio Jardín privado (6.1 m × 13.4 m).
- PRIMERA PLANTA (Z = -0.14 m): Cochera y Fachada de Entrada con celosía de madera y pérgola,
  Studio/Recámara PA, Pasillo con escalera abierta, Cocina (vistiendo la isla real),
  Sala en L, Comedor panorámico y cuadros enmarcados.

Guarda el proyecto 100% abierto `blender/casa_l8_mexico.blend` y renderiza
los 8 panoramas 360° equirectangulares en `assets/panoramas/`.
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GLB_PATH = os.path.join(PROJECT_ROOT, "assets", "L8_MEXICO_SKP_3.glb")
OUT_DIR = os.path.join(PROJECT_ROOT, "assets", "panoramas")
BLEND_PATH = os.path.join(SCRIPT_DIR, "casa_l8_mexico.blend")
os.makedirs(OUT_DIR, exist_ok=True)

# Niveles exactos medidos del modelo real 1:1
Z_SOTANO = -2.89
Z_1P = -0.14
Z_TECHO = 3.06


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def configure_cycles(samples=64, res_x=2048, res_y=1024):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.025
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6

    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev_type in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = dev_type
                prefs.get_devices()
                gpu_found = False
                for d in prefs.devices:
                    if d.type != "CPU":
                        d.use = True
                        gpu_found = True
                if gpu_found:
                    scene.cycles.device = "GPU"
                    print(f"[Cycles] Usando GPU ({dev_type})")
                    break
            except Exception:
                continue
    except Exception:
        pass

    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    scene.view_settings.exposure = -1.55


def setup_world_sky():
    world = bpy.data.worlds.new("Sky_Morelia_Golden")
    bpy.context.scene.world = world
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.24

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.0)
    sky.sun_intensity = 1.15
    sky.sun_elevation = math.radians(24)
    sky.sun_rotation = math.radians(125)
    sky.altitude = 1920.0
    if hasattr(sky, "air_density"):
        sky.air_density = 1.25
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 1.45

    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


# ---------------------------------------------------------------------------
# Materiales PBR
# ---------------------------------------------------------------------------
def make_pbr_mat(name, color, roughness=0.7, metallic=0.0, bump_scale=0.0, bump_strength=0.0,
                 emission=None, emission_strength=0.0, transmission=0.0, ior=1.45,
                 color2=None, color_noise_scale=6.0):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if transmission > 0 and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None and emission_strength > 0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    tc = nt.nodes.new("ShaderNodeTexCoord")
    if color2 is not None:
        cnoise = nt.nodes.new("ShaderNodeTexNoise")
        cnoise.inputs["Scale"].default_value = color_noise_scale
        cnoise.inputs["Detail"].default_value = 8.0
        cnoise.inputs["Roughness"].default_value = 0.65
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*color, 1.0)
        mix.inputs[7].default_value = (*color2, 1.0)
        nt.links.new(tc.outputs["Object"], cnoise.inputs["Vector"])
        nt.links.new(cnoise.outputs["Fac"], mix.inputs[0])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)

    if bump_scale > 0 and bump_strength > 0:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 10.0
        noise.inputs["Roughness"].default_value = 0.65
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_marble_mat(name):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.16
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.inputs["Scale"].default_value = 2.2
    wave.inputs["Distortion"].default_value = 11.0
    wave.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[0].color = (0.38, 0.36, 0.34, 1.0)
    ramp.color_ramp.elements[1].position = 0.52
    ramp.color_ramp.elements[1].color = (0.94, 0.93, 0.90, 1.0)
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def make_art_canvas_mat(name, col_a, col_b, col_c, scale=2.4):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.85
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 6.5
    wave.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (*col_a, 1.0)
    e_mid = ramp.color_ramp.elements.new(0.55)
    e_mid.color = (*col_b, 1.0)
    ramp.color_ramp.elements[2].position = 0.85
    ramp.color_ramp.elements[2].color = (*col_c, 1.0)
    nt.links.new(tc.outputs["Generated"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def make_rock_mat(name):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.92
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 4.5
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 14.0
    noise.inputs["Detail"].default_value = 10.0
    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs[6].default_value = (0.10, 0.11, 0.12, 1.0)
    mix_col.inputs[7].default_value = (0.28, 0.27, 0.26, 1.0)
    bump1 = nt.nodes.new("ShaderNodeBump")
    bump1.inputs["Strength"].default_value = 0.45
    bump2 = nt.nodes.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.28
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mix_col.inputs[0])
    nt.links.new(mix_col.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(vor.outputs["Distance"], bump1.inputs["Height"])
    nt.links.new(noise.outputs["Fac"], bump2.inputs["Height"])
    nt.links.new(bump1.outputs["Normal"], bump2.inputs["Normal"])
    nt.links.new(bump2.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------------------
# Helpers de mobiliario, vegetación e iluminación
# ---------------------------------------------------------------------------
def add_box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    if bevel > 0:
        bpy.ops.object.transform_apply(scale=True)
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def add_cyl(name, radius, depth, loc, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def add_framed_artwork(name, loc, width, height, axis, frame_mat, art_mat):
    x, y, z = loc
    depth, border = 0.045, 0.032
    if axis == "Y":
        add_box(f"{name}_c", (width - border * 2, depth * 0.5, height - border * 2), (x, y, z), art_mat)
        add_box(f"{name}_t", (width, depth, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_b", (width, depth, border), (x, y, z - height / 2 + border / 2), frame_mat)
        add_box(f"{name}_l", (border, depth, height), (x - width / 2 + border / 2, y, z), frame_mat)
        add_box(f"{name}_r", (border, depth, height), (x + width / 2 - border / 2, y, z), frame_mat)
    else:
        add_box(f"{name}_c", (depth * 0.5, width - border * 2, height - border * 2), (x, y, z), art_mat)
        add_box(f"{name}_t", (depth, width, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_b", (depth, width, border), (x, y, z - height / 2 + border / 2), frame_mat)
        add_box(f"{name}_l", (depth, border, height), (x, y - width / 2 + border / 2, z), frame_mat)
        add_box(f"{name}_r", (depth, border, height), (x, y + width / 2 - border / 2, z), frame_mat)


def add_boulder(name, radius, loc, mat, scale=(1.2, 1.0, 0.72), seed=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        p = v.co
        n1 = 0.22 * math.sin(p.x * 3.8 + seed) * math.cos(p.y * 3.4 - seed)
        n2 = 0.14 * math.sin(p.z * 7.5 + p.x * 5.0)
        n3 = 0.06 * math.cos(p.y * 13.0 - p.z * 11.0)
        f = 1.0 + n1 + n2 + n3
        v.co.x = p.x * f * scale[0]
        v.co.y = p.y * f * scale[1]
        v.co.z = max(-radius * 0.45, p.z * f * scale[2])
    bm.to_mesh(obj.data)
    bm.free()
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def add_detailed_tree(name, loc, scale, bark_mat, leaf_mat, leaf_light_mat, blossom_mat, seed=10):
    rng = random.Random(seed)
    x0, y0, z0 = loc
    add_cyl(f"{name}_trunk", 0.095 * scale, 2.5 * scale, (x0, y0, z0 + 1.25 * scale), bark_mat, (0.04, -0.05, 0), 12)
    branches = [
        (0.28, 0.14, 2.9, 0.28, 0.28, 0.0, 2.2, 0.048),
        (-0.32, -0.16, 2.85, -0.25, -0.34, 0.0, 2.1, 0.045),
        (0.06, 0.25, 3.25, -0.28, 0.10, 0.0, 2.4, 0.042),
        (0.75, 0.42, 4.0, 0.45, 0.42, 0.0, 1.6, 0.025),
        (-0.82, -0.35, 3.9, -0.38, -0.48, 0.0, 1.6, 0.024),
    ]
    for idx, (dx, dy, dz, rx, ry, rz, ln, rad) in enumerate(branches):
        add_cyl(f"{name}_br{idx}", rad * scale, ln * scale,
                (x0 + dx * scale, y0 + dy * scale, z0 + dz * scale), bark_mat, (rx, ry, rz), 8)

    def build_leaf_cloud(mesh_name, count, size_min, size_max, mat, z_min=2.6, z_span=3.6):
        mesh = bpy.data.meshes.new(mesh_name)
        bm = bmesh.new()
        for _ in range(count):
            layer = rng.random()
            rz = (z_min + layer * z_span) * scale
            max_r = max(0.45, (2.15 - abs(layer - 0.48) * 1.6) * scale)
            rad = (rng.random() ** 0.6) * max_r
            ang = rng.random() * math.tau
            center = Vector((rad * math.cos(ang), rad * math.sin(ang), rz))
            L = (size_min + rng.random() * (size_max - size_min)) * scale
            W = L * 0.46
            rx = rng.uniform(-1.2, 1.2)
            rz_rot = rng.uniform(0, math.tau)
            ca, sa = math.cos(rz_rot), math.sin(rz_rot)
            cb, sb = math.cos(rx), math.sin(rx)
            pts = [
                Vector((0, -L * 0.5, 0)),
                Vector((W * 0.5, 0, L * 0.08)),
                Vector((0, L * 0.5, 0)),
                Vector((-W * 0.5, 0, L * 0.08)),
            ]
            verts = []
            for p in pts:
                py1 = p.y * cb - p.z * sb
                pz1 = p.y * sb + p.z * cb
                px2 = p.x * ca - py1 * sa
                py2 = p.x * sa + py1 * ca
                verts.append(bm.verts.new(center + Vector((px2, py2, pz1))))
            bm.faces.new(verts)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(mesh_name, mesh)
        obj.location = (x0, y0, z0)
        obj.data.materials.append(mat)
        bpy.context.collection.objects.link(obj)

    build_leaf_cloud(f"{name}_leaves_dark", 520, 0.16, 0.28, leaf_mat, 2.5, 3.6)
    build_leaf_cloud(f"{name}_leaves_light", 380, 0.14, 0.25, leaf_light_mat, 2.7, 3.5)
    build_leaf_cloud(f"{name}_blossoms", 160, 0.08, 0.13, blossom_mat, 2.9, 3.0)


def add_lavender_clump(name, loc, green_mat, purple_mat, seed=1):
    rng = random.Random(seed)
    x0, y0, z0 = loc
    mesh_g = bpy.data.meshes.new(f"{name}_g")
    mesh_p = bpy.data.meshes.new(f"{name}_p")
    bmg, bmp = bmesh.new(), bmesh.new()
    for _ in range(28):
        ang = rng.uniform(0, math.tau)
        r = rng.uniform(0, 0.35)
        h = rng.uniform(0.28, 0.52)
        ox, oy = r * math.cos(ang), r * math.sin(ang)
        lx, ly = ox * 0.45, oy * 0.45
        v1 = bmg.verts.new((ox - 0.015, oy, 0))
        v2 = bmg.verts.new((ox + 0.015, oy, 0))
        v3 = bmg.verts.new((ox + lx + 0.01, oy + ly, h * 0.72))
        v4 = bmg.verts.new((ox + lx - 0.01, oy + ly, h * 0.72))
        bmg.faces.new((v1, v2, v3, v4))
        ret = bmesh.ops.create_icosphere(bmp, subdivisions=1, radius=0.032)
        for v in ret["verts"]:
            v.co.z *= 2.4
            v.co += Vector((ox + lx, oy + ly, h * 0.85))
    bmg.to_mesh(mesh_g)
    bmp.to_mesh(mesh_p)
    bmg.free()
    bmp.free()
    og = bpy.data.objects.new(f"{name}_stems", mesh_g)
    op = bpy.data.objects.new(f"{name}_flowers", mesh_p)
    og.location = op.location = (x0, y0, z0)
    og.data.materials.append(green_mat)
    op.data.materials.append(purple_mat)
    bpy.context.collection.objects.link(og)
    bpy.context.collection.objects.link(op)


def add_dining_chair(name, loc, rot_z, fabric_mat, wood_mat):
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)
    parts = [
        add_box(f"{name}_seat", (0.45, 0.45, 0.07), (0, 0, 0.45), fabric_mat, bevel=0.025),
        add_box(f"{name}_back", (0.45, 0.07, 0.35), (0, -0.19, 0.64), fabric_mat, (0.08, 0, 0), bevel=0.025),
        add_box(f"{name}_armL", (0.055, 0.34, 0.15), (-0.20, -0.04, 0.55), fabric_mat, bevel=0.02),
        add_box(f"{name}_armR", (0.055, 0.34, 0.15), (0.20, -0.04, 0.55), fabric_mat, bevel=0.02),
        add_cyl(f"{name}_l1", 0.017, 0.44, (-0.17, -0.17, 0.22), wood_mat, (0.08, -0.08, 0), 10),
        add_cyl(f"{name}_l2", 0.017, 0.44, (0.17, -0.17, 0.22), wood_mat, (0.08, 0.08, 0), 10),
        add_cyl(f"{name}_l3", 0.017, 0.44, (-0.17, 0.17, 0.22), wood_mat, (-0.08, -0.08, 0), 10),
        add_cyl(f"{name}_l4", 0.017, 0.44, (0.17, 0.17, 0.22), wood_mat, (-0.08, 0.08, 0), 10),
    ]
    for p in parts:
        p.parent = g


def add_rattan_armchair(name, loc, rot_z, fabric_mat, wood_mat):
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)
    parts = [
        add_cyl(f"{name}_base", 0.42, 0.24, (0, 0, 0.24), fabric_mat, verts=24),
        add_cyl(f"{name}_cush", 0.41, 0.12, (0, 0, 0.40), fabric_mat, verts=24),
        add_box(f"{name}_pil", (0.48, 0.16, 0.36), (0, -0.20, 0.60), fabric_mat, (0.15, 0, 0), bevel=0.05),
    ]
    for i in range(11):
        ang = math.radians(-105 + i * 21)
        parts.append(add_cyl(f"{name}_rib{i}", 0.016, 0.46, (0.42 * math.sin(ang), -0.42 * math.cos(ang), 0.56), wood_mat, verts=8))
    for lx, ly in [(-0.26, -0.26), (0.26, -0.26), (-0.26, 0.26), (0.26, 0.26)]:
        parts.append(add_cyl(f"{name}_leg_{lx}_{ly}", 0.02, 0.12, (lx, ly, 0.06), wood_mat, verts=8))
    for p in parts:
        p.parent = g


def add_full_bed(name, loc, mats, blanket_mat, rot_z=0.0, width=1.80):
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)
    parts = []
    n_pan = 8 if width > 1.75 else 6
    pan_w = (width + 0.12) / n_pan
    start_x = -(width + 0.12) / 2 + pan_w / 2
    for i in range(n_pan):
        parts.append(add_box(f"{name}_hb{i}", (pan_w - 0.01, 0.09, 1.20), (start_x + i * pan_w, -1.02, 0.62), mats["cream_fabric"], bevel=0.016))
    parts.append(add_box(f"{name}_base", (width, 2.02, 0.24), (0, 0, 0.14), mats["dark_wood"], bevel=0.015))
    parts.append(add_box(f"{name}_matt", (width - 0.08, 1.94, 0.22), (0, 0, 0.37), mats["white_linen"], bevel=0.04))
    parts.append(add_box(f"{name}_blnk", (width - 0.04, 1.18, 0.08), (0, 0.38, 0.49), blanket_mat, bevel=0.03))
    for px in (-width * 0.24, width * 0.24):
        parts.append(add_box(f"{name}_pA_{px:.2f}", (0.64, 0.32, 0.15), (px, -0.70, 0.54), mats["white_linen"], (0.18, 0, 0), bevel=0.04))
        parts.append(add_box(f"{name}_pB_{px:.2f}", (0.44, 0.22, 0.16), (px, -0.44, 0.56), mats["taupe"], (0.24, 0, 0), bevel=0.04))
    for side in (-1, 1):
        bx = side * (width / 2 + 0.34)
        parts.append(add_box(f"{name}_buro_{side}", (0.48, 0.38, 0.24), (bx, -0.78, 0.34), mats["wood"], bevel=0.012))
        parts.append(add_cyl(f"{name}_lb_{side}", 0.06, 0.20, (bx, -0.78, 0.56), mats["dark_metal"]))
        parts.append(add_cyl(f"{name}_ls_{side}", 0.12, 0.14, (bx, -0.78, 0.72), mats["led"]))
    for p in parts:
        p.parent = g
    return g


def add_area_light(name, loc, rot, energy, size_x, size_y, color=(1.0, 0.88, 0.72)):
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.energy = energy
    ldata.color = color
    ldata.shape = "RECTANGLE"
    ldata.size = size_x
    ldata.size_y = size_y
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = loc
    lobj.rotation_euler = rot
    if hasattr(lobj, "visible_glossy"):
        lobj.visible_glossy = False
    if hasattr(lobj, "visible_transmission"):
        lobj.visible_transmission = False
    bpy.context.collection.objects.link(lobj)
    return lobj


def add_point_light(name, loc, energy, radius=0.12, color=(1.0, 0.82, 0.58)):
    ldata = bpy.data.lights.new(name=name, type="POINT")
    ldata.energy = energy
    ldata.shadow_soft_size = radius
    ldata.color = color
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = loc
    if hasattr(lobj, "visible_glossy"):
        lobj.visible_glossy = False
    bpy.context.collection.objects.link(lobj)
    return lobj


# ---------------------------------------------------------------------------
# Importación 1:1 del modelo arquitectónico real + alineación exacta a ejes
# ---------------------------------------------------------------------------
def import_exact_architecture(mats):
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)

    # Eliminar únicamente líneas CAD negras y terreno satelital Bing (reemplazado por pasto/calle Cycles)
    for obj in list(bpy.data.objects):
        if obj.type == "MESH":
            mat_name = obj.active_material.name if obj.active_material else ""
            if "edges" in obj.name or "Geolocation" in mat_name:
                bpy.data.objects.remove(obj, do_unlink=True)

    # Agrupar, rotar -31.15° y alinear origen a (0.00, 0.00) -> X=[0..15.07], Y=[0..20.60]
    root = bpy.data.objects.new("Arquitectura_Exacta_1a1", None)
    bpy.context.collection.objects.link(root)
    arch_meshes = []
    for obj in list(bpy.data.objects):
        if obj != root and obj.parent is None:
            obj.parent = root
        if obj.type == "MESH":
            arch_meshes.append(obj)

    root.rotation_euler = (0, 0, math.radians(-31.15))
    bpy.context.view_layer.update()

    xs, ys = [], []
    for obj in arch_meshes:
        mw = obj.matrix_world
        for v in obj.data.vertices:
            w = mw @ v.co
            xs.append(w.x)
            ys.append(w.y)
    root.location = (-min(xs), -min(ys), 0.0)
    bpy.context.view_layer.update()

    # Asignar estuco blanco en muros y microcemento pulido en pisos horizontales (Z = -2.89 o -0.14)
    for obj in arch_meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mats["stucco"])          # slot 0
        obj.data.materials.append(mats["floor_polished"])  # slot 1
        obj.data.materials.append(mats["warm_wall"])       # slot 2
        mw = obj.matrix_world
        rot3 = mw.to_3x3()
        for poly in obj.data.polygons:
            n = (rot3 @ poly.normal).normalized()
            c = mw @ poly.center
            # Caras horizontales en niveles de piso interior -> microcemento pulido
            if abs(n.z) > 0.85 and (abs(c.z - Z_1P) < 0.18 or abs(c.z - Z_SOTANO) < 0.18) and c.x < 9.0:
                poly.material_index = 1
            else:
                poly.material_index = 0

    print(f"[Arq 1:1] Importados {len(arch_meshes)} meshes reales alineados a X=[0..15.07], Y=[0..20.60]")
    return root


def terrain_height(wx, wy):
    """Pendiente real fiel al topográfico (más alto al Norte/Oeste Y=20, baja al Sur/Este Y=0)."""
    dx = max(0.0, -wx, wx - 15.1)
    dy = max(0.0, -wy, wy - 20.6)
    dist = math.hypot(dx, dy)
    t = min(1.0, max(0.0, (dist - 0.4) / 9.5))
    blend = t * t * (3.0 - 2.0 * t)
    # Nivel de calle en esquina Sur (Y=0) ~ -3.15 m; sube hacia Norte (Y=20, entrada cochera) ~ -0.35 m!
    slope_y = -3.15 + (wy / 20.6) * 2.85
    slope_x = (7.5 - wx) * 0.045
    hill = math.sin(wx * 0.036) * 0.42 + math.cos(wy * 0.036) * 0.36
    base_pad = -3.10 + (max(0.0, min(20.6, wy)) / 20.6) * 2.55
    target_z = max(-7.5, min(3.2, slope_y + slope_x + hill))
    return base_pad * (1.0 - blend) + target_z * blend


def build_exact_scene():
    mats = {
        "stucco": make_pbr_mat("Estuco_Blanco", (0.86, 0.85, 0.82), roughness=0.84, bump_scale=38.0, bump_strength=0.04,
                               color2=(0.80, 0.79, 0.76), color_noise_scale=3.0),
        "warm_wall": make_pbr_mat("Muro_Interior", (0.72, 0.68, 0.62), roughness=0.82, bump_scale=30.0, bump_strength=0.025),
        "floor_polished": make_pbr_mat("Piso_Microcemento", (0.62, 0.58, 0.52), roughness=0.15, bump_scale=10.0, bump_strength=0.012,
                                       color2=(0.56, 0.52, 0.47), color_noise_scale=2.2),
        "grass": make_pbr_mat("Pasto_Lomas", (0.11, 0.14, 0.055), roughness=0.96, bump_scale=42.0, bump_strength=0.35,
                              color2=(0.18, 0.21, 0.09), color_noise_scale=2.5),
        "hill_forest": make_pbr_mat("Lomas_Bosque", (0.07, 0.10, 0.055), roughness=0.98, bump_scale=18.0, bump_strength=0.32,
                                    color2=(0.13, 0.15, 0.075), color_noise_scale=2.0),
        "road": make_pbr_mat("Grava_Vial", (0.36, 0.34, 0.31), roughness=0.72, bump_scale=85.0, bump_strength=0.18,
                             color2=(0.45, 0.43, 0.39), color_noise_scale=9.0),
        "gravel": make_pbr_mat("Grava_Patio", (0.30, 0.28, 0.25), roughness=0.92, bump_scale=95.0, bump_strength=0.25,
                               color2=(0.38, 0.36, 0.32), color_noise_scale=12.0),
        "slate": make_pbr_mat("Deck_Pizarra", (0.10, 0.11, 0.12), roughness=0.68, bump_scale=22.0, bump_strength=0.05),
        "paver": make_pbr_mat("Andador_Concreto", (0.28, 0.28, 0.27), roughness=0.84, bump_scale=35.0, bump_strength=0.06),
        "wood": make_pbr_mat("Madera_Roble", (0.34, 0.22, 0.13), roughness=0.58, bump_scale=24.0, bump_strength=0.05,
                             color2=(0.25, 0.16, 0.09), color_noise_scale=8.0),
        "dark_wood": make_pbr_mat("Madera_Nogal", (0.14, 0.09, 0.06), roughness=0.48, bump_scale=20.0, bump_strength=0.04),
        "beige_cab": make_pbr_mat("Cocina_Beige", (0.64, 0.51, 0.39), roughness=0.48),
        "dark_island": make_pbr_mat("Isla_Grafito", (0.09, 0.10, 0.12), roughness=0.52),
        "marble": make_marble_mat("Marmol_Calacatta"),
        "cream_fabric": make_pbr_mat("Tela_Crema", (0.76, 0.72, 0.65), roughness=0.94, bump_scale=65.0, bump_strength=0.06),
        "white_linen": make_pbr_mat("Sabana_Blanca", (0.88, 0.87, 0.84), roughness=0.90),
        "charcoal_fabric": make_pbr_mat("Cobija_Grafito", (0.11, 0.12, 0.15), roughness=0.94),
        "olive": make_pbr_mat("Cojin_Olivo", (0.18, 0.20, 0.11), roughness=0.92),
        "taupe": make_pbr_mat("Cojin_Taupe", (0.28, 0.26, 0.23), roughness=0.92),
        "rug": make_pbr_mat("Tapete_Tejido", (0.52, 0.49, 0.44), roughness=0.96, bump_scale=80.0, bump_strength=0.14,
                            color2=(0.45, 0.42, 0.38), color_noise_scale=15.0),
        "dark_metal": make_pbr_mat("Metal_Negro", (0.035, 0.038, 0.042), roughness=0.28, metallic=0.8),
        "alum": make_pbr_mat("Aluminio_Inox", (0.52, 0.54, 0.56), roughness=0.22, metallic=0.88),
        "chrome": make_pbr_mat("Cromo", (0.82, 0.83, 0.85), roughness=0.08, metallic=0.96),
        "black_glass": make_pbr_mat("Vidrio_Negro", (0.02, 0.02, 0.025), roughness=0.06, metallic=0.15),
        "glass": make_pbr_mat("Vidrio_Arq", (0.86, 0.93, 0.97), roughness=0.02, transmission=0.92, ior=1.5),
        "sheer": make_pbr_mat("Cortina_Transl", (0.86, 0.84, 0.80), roughness=0.92, transmission=0.45),
        "rock": make_rock_mat("Roca_Volcanica"),
        "bark": make_pbr_mat("Corteza", (0.13, 0.10, 0.07), roughness=0.94, bump_scale=28.0, bump_strength=0.22),
        "leaf_dark": make_pbr_mat("Follaje_Oscuro", (0.07, 0.15, 0.045), roughness=0.68),
        "leaf_light": make_pbr_mat("Follaje_Claro", (0.14, 0.24, 0.075), roughness=0.64),
        "blossom": make_pbr_mat("Flor_Blanca", (0.94, 0.93, 0.90), roughness=0.62),
        "lavender": make_pbr_mat("Lavanda", (0.24, 0.14, 0.34), roughness=0.88),
        "led": make_pbr_mat("LED_Calido", (1.0, 0.92, 0.76), roughness=0.3, emission=(1.0, 0.78, 0.44), emission_strength=9.5),
        "art_living": make_art_canvas_mat("Cuadro_Sala", (0.12, 0.11, 0.10), (0.68, 0.56, 0.42), (0.88, 0.85, 0.80), 2.0),
        "art_bed": make_art_canvas_mat("Cuadro_Recamara", (0.18, 0.20, 0.15), (0.58, 0.52, 0.44), (0.86, 0.83, 0.78), 2.8),
        "art_hall": make_art_canvas_mat("Cuadro_Pasillo", (0.15, 0.14, 0.14), (0.45, 0.34, 0.25), (0.84, 0.80, 0.74), 3.2),
    }

    # 1. IMPORTAR ARQUITECTURA EXACTA 1:1 DEL ARQUITECTO
    import_exact_architecture(mats)

    # 2. TERRENO EN PENDIENTE REAL + CALLE CURVA + LOMAS SUAVES EN HORIZONTE
    t_mesh = bpy.data.meshes.new("Terreno_Exacto_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=96, y_segments=96, size=90.0)
    for v in bm.verts:
        wx, wy = v.co.x + 7.5, v.co.y + 10.0
        # Excavar suavemente bajo el predio para que el pasto no atraviese el piso de sótano ni el patio
        if -0.2 <= wx <= 15.2 and -0.2 <= wy <= 20.7:
            vz = Z_SOTANO - 0.35
        else:
            vz = terrain_height(wx, wy)
        v.co = Vector((wx, wy, vz))
    bm.to_mesh(t_mesh)
    bm.free()
    terrain = bpy.data.objects.new("Terreno_Lomas", t_mesh)
    terrain.data.materials.append(mats["grass"])
    bpy.context.collection.objects.link(terrain)
    bpy.context.view_layer.objects.active = terrain
    bpy.ops.object.shade_smooth()

    # Vialidad curva abrazando la esquina Sur-Oeste y subiendo a la Cochera (Norte-Oeste)
    road_pts = [
        (-4.5, 45.0), (-3.6, 22.0), (-3.8, 13.0), (-4.0, 4.0),
        (-3.2, -2.5), (3.0, -4.2), (16.0, -4.6), (42.0, -5.8), (68.0, -7.2),
    ]
    road_mesh = bpy.data.meshes.new("Vialidad_Curva_Mesh")
    rbm = bmesh.new()
    dense = []
    for seg in range(len(road_pts) - 1):
        p0 = Vector(road_pts[max(0, seg - 1)])
        p1 = Vector(road_pts[seg])
        p2 = Vector(road_pts[seg + 1])
        p3 = Vector(road_pts[min(len(road_pts) - 1, seg + 2)])
        for s in range(10):
            t = s / 10.0
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense.append(Vector(road_pts[-1]))
    prev_pair = None
    for i, pt in enumerate(dense):
        tan = (dense[min(len(dense) - 1, i + 1)] - dense[max(0, i - 1)]).normalized()
        right = Vector((tan.y, -tan.x))
        pL, pR = pt - right * 3.1, pt + right * 3.1
        vL = rbm.verts.new((pL.x, pL.y, terrain_height(pL.x, pL.y) + 0.06))
        vR = rbm.verts.new((pR.x, pR.y, terrain_height(pR.x, pR.y) + 0.06))
        if prev_pair is not None:
            rbm.faces.new((prev_pair[0], prev_pair[1], vR, vL))
        prev_pair = (vL, vR)
    rbm.to_mesh(road_mesh)
    rbm.free()
    road_obj = bpy.data.objects.new("Vialidad_Curva", road_mesh)
    road_obj.data.materials.append(mats["road"])
    bpy.context.collection.objects.link(road_obj)
    bpy.context.view_layer.objects.active = road_obj
    bpy.ops.object.shade_smooth()

    # Lomas boscosas suaves en el horizonte
    ridge_mesh = bpy.data.meshes.new("Lomas_Suaves_Mesh")
    hbm = bmesh.new()
    n_ang = 120
    radii = [78.0, 92.0, 112.0, 134.0, 160.0]
    rings = []
    for r_idx, rad in enumerate(radii):
        ring = []
        bell = math.sin((r_idx / (len(radii) - 1)) * math.pi) ** 1.35
        for i in range(n_ang):
            ang = (i / n_ang) * math.tau
            wx, wy = 7.5 + math.cos(ang) * rad, 10.0 + math.sin(ang) * rad
            base_z = terrain_height(7.5 + math.cos(ang) * 76.0, 10.0 + math.sin(ang) * 76.0) - 0.5
            crest = 8.5 + 4.0 * math.sin(ang * 2.0 + 0.5) + 2.6 * math.cos(ang * 4.0 - 0.7) + 1.2 * math.sin(ang * 6.0)
            z = base_z * (1.0 - bell) + crest * bell if r_idx < len(radii) - 1 else -10.0
            ring.append(hbm.verts.new((wx, wy, z)))
        rings.append(ring)
    for r_idx in range(len(rings) - 1):
        for i in range(n_ang):
            ni = (i + 1) % n_ang
            hbm.faces.new((rings[r_idx][i], rings[r_idx][ni], rings[r_idx + 1][ni], rings[r_idx + 1][i]))
    hbm.to_mesh(ridge_mesh)
    hbm.free()
    ridge_obj = bpy.data.objects.new("Cordillera_Suave", ridge_mesh)
    ridge_obj.data.materials.append(mats["hill_forest"])
    bpy.context.collection.objects.link(ridge_obj)
    bpy.context.view_layer.objects.active = ridge_obj
    bpy.ops.object.shade_smooth()

    # =========================================================================
    # 3. PRIMERA PLANTA — AMUEBLADO 1:1 DENTRO DE LOS MUROS REALES (Z = -0.14 m)
    #    Ver `plan_1p_full.png`:
    #    - Cocina fondo: Y = 7.8, X = 3.5..7.4 | Isla real: X = 4.2..7.0, Y = 5.4..6.4
    #    - Estancia / Sala: X = 3.0..6.4, Y = 1.6..4.7
    #    - Comedor: X = 6.5..8.5, Y = 1.2..4.4
    #    - Ventanal panorámico Sur (Y = 0.2, X = 3.2..9.3) y Este (X = 8.8..9.3, Y = 0.2..7.6)
    #    - Escalera y Pasillo: X = 0.5..2.2, Y = 0.6..9.5
    #    - Cochera y Entrada: X = 2.0..15.0, Y = 13.7..20.3
    # =========================================================================
    z1 = Z_1P

    # Franja LED horizontal cálida bajo el voladizo real
    add_box("Franja_LED_Sur", (6.0, 0.08, 0.20), (6.2, 0.35, z1 - 0.16), mats["led"])
    add_box("Franja_LED_Este", (0.08, 7.2, 0.20), (8.95, 4.0, z1 - 0.16), mats["led"])

    # Ventanal panorámico Sur (Y = 0.25, X = 3.25..9.25) con cancelería fina de aluminio (Render 1 y 3)
    add_box("Ventanal_Sur_Glass", (6.0, 0.03, 3.05), (6.25, 0.25, z1 + 1.54), mats["glass"])
    for mx in (3.28, 5.25, 7.25, 9.22):
        add_box(f"Parteluz_S_{mx}", (0.06, 0.08, 3.08), (mx, 0.25, z1 + 1.54), mats["alum"])
    add_box("Travesano_S", (6.0, 0.08, 0.055), (6.25, 0.25, z1 + 0.78), mats["alum"])

    # Ventanal lateral Pasillo Oeste (X = 1.1..1.6, Y = 4.0..8.5)
    add_box("Pasamanos_Esc_Real", (0.09, 4.3, 0.045), (2.22, 2.35, z1 + 1.05), mats["wood"], bevel=0.006)

    # Puerta del pasillo hacia núcleo/baño/studio con franja metálica (Render 3 izquierda!)
    add_box("Puerta_Nucleo_1P", (1.02, 0.07, 2.35), (7.65, 13.55, z1 + 1.18), mats["beige_cab"], bevel=0.01)
    add_box("Puerta_Nucleo_Franja", (1.04, 0.08, 0.15), (7.65, 13.55, z1 + 0.92), mats["dark_metal"])

    # COCINA (Fondo Y = 7.75, X = 4.0..7.5 — encajada limpiamente dentro del nicho real sin cruzar el muro divisor!)
    for i in range(5):
        add_box(f"Gab_Sup_{i}", (0.52, 0.40, 1.10), (4.92 + i * 0.54, 7.62, z1 + 2.25), mats["beige_cab"], bevel=0.008)
    add_box("Nicho_Cocina_T", (0.40, 0.38, 0.035), (4.44, 7.62, z1 + 2.18), mats["beige_cab"])
    add_box("Nicho_Cocina_B", (0.40, 0.38, 0.035), (4.44, 7.62, z1 + 1.66), mats["beige_cab"])
    add_box("Backsplash_Marmol", (3.05, 0.05, 0.84), (5.78, 7.80, z1 + 1.28), mats["marble"])
    add_box("LED_Cocina", (2.90, 0.05, 0.035), (5.78, 7.68, z1 + 1.66), mats["led"])
    add_box("Cocina_Inf", (3.05, 0.60, 0.88), (5.78, 7.50, z1 + 0.44), mats["dark_island"], bevel=0.01)
    add_box("Cocina_Cubierta", (3.08, 0.64, 0.05), (5.78, 7.49, z1 + 0.90), mats["marble"], bevel=0.008)
    add_box("Parrilla_Vidrio", (0.72, 0.48, 0.025), (6.05, 7.49, z1 + 0.935), mats["black_glass"])
    for qx in (5.85, 6.25):
        for qy in (7.36, 7.62):
            add_cyl(f"Quemador_{qx}_{qy}", 0.06, 0.02, (qx, qy, z1 + 0.955), mats["dark_metal"], verts=14)
    add_box("Horno_Frente", (0.64, 0.04, 0.52), (6.05, 7.19, z1 + 0.48), mats["black_glass"])
    add_box("Refri_Izq", (0.38, 0.64, 2.02), (3.84, 7.48, z1 + 1.01), mats["alum"], bevel=0.015)
    add_box("Refri_Der", (0.38, 0.64, 2.02), (4.24, 7.48, z1 + 1.01), mats["alum"], bevel=0.015)

    # Vestir limpiamente la isla real del arquitecto (cubre todo el bloque blanco real sin escalón doble)
    add_box("Isla_Rev_Grafito", (3.05, 1.38, 0.96), (5.68, 5.55, z1 + 0.48), mats["dark_island"], bevel=0.012)
    add_box("Isla_Marmol_Top", (3.16, 1.48, 0.06), (5.68, 5.55, z1 + 0.99), mats["marble"], bevel=0.01)
    add_box("Tarja_Hundida", (0.64, 0.44, 0.03), (4.95, 5.60, z1 + 1.01), mats["dark_metal"])
    add_cyl("Grifo_Poste", 0.016, 0.34, (4.95, 5.86, z1 + 1.18), mats["chrome"], verts=12)
    add_cyl("Grifo_Pico", 0.014, 0.18, (4.95, 5.76, z1 + 1.34), mats["chrome"], (math.radians(90), 0, 0), verts=12)

    # SALA EN L (X = 3.2..6.2, Y = 1.6..4.4 — exactamente frente a cocina e isla, Render 3!)
    add_box("Tapete_Sala", (3.6, 3.1, 0.02), (4.85, 3.15, z1 + 0.01), mats["rug"])
    add_box("Sofa_Base", (2.85, 0.96, 0.24), (4.85, 3.85, z1 + 0.16), mats["cream_fabric"], bevel=0.03)
    for i in range(3):
        add_box(f"Sofa_As_{i}", (0.90, 0.86, 0.18), (3.94 + i * 0.91, 3.82, z1 + 0.36), mats["cream_fabric"], bevel=0.045)
        add_box(f"Sofa_Res_{i}", (0.90, 0.20, 0.44), (3.94 + i * 0.91, 4.18, z1 + 0.62), mats["cream_fabric"], (-0.12, 0, 0), bevel=0.045)
    add_box("Sofa_Chaise_B", (0.98, 2.00, 0.24), (3.92, 2.75, z1 + 0.16), mats["cream_fabric"], bevel=0.03)
    add_box("Sofa_Chaise_C", (0.92, 1.85, 0.18), (3.92, 2.75, z1 + 0.36), mats["cream_fabric"], bevel=0.045)
    for idx, (cx, cy, ry, cmat) in enumerate([
        (3.85, 3.92, 0.16, mats["taupe"]),
        (4.35, 3.90, -0.14, mats["olive"]),
        (5.15, 3.92, 0.10, mats["taupe"]),
        (5.85, 3.90, -0.16, mats["olive"]),
    ]):
        add_box(f"Cojin_S_{idx}", (0.40, 0.14, 0.35), (cx, cy, z1 + 0.56), cmat, (-0.18, ry, 0), bevel=0.045)

    add_cyl("Mesa_Centro", 0.44, 0.04, (5.25, 2.55, z1 + 0.38), mats["dark_metal"], verts=28)
    for a in (0, 2.09, 4.18):
        add_cyl(f"Mesa_P_{a:.1f}", 0.014, 0.36, (5.25 + 0.28 * math.cos(a), 2.55 + 0.28 * math.sin(a), z1 + 0.19), mats["dark_metal"], verts=8)
    add_cyl("Florero_S", 0.09, 0.21, (5.40, 2.58, z1 + 0.50), mats["white_linen"], verts=18)
    for idx, (rx, ry) in enumerate([(0.30, 0.2), (-0.26, 0.34), (0.14, -0.30)]):
        add_cyl(f"Rama_S_{idx}", 0.008, 0.40, (5.40, 2.58, z1 + 0.74), mats["dark_wood"], (rx, ry, 0), verts=6)

    # Mesa auxiliar mármol + lámpara hongo negra (Render 3)
    add_box("Mesa_Aux", (0.42, 0.42, 0.03), (3.12, 3.85, z1 + 0.46), mats["marble"])
    add_cyl("Lamp_H_Pie", 0.07, 0.24, (3.12, 3.85, z1 + 0.60), mats["dark_metal"], verts=16)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.17, location=(3.12, 3.85, z1 + 0.75))
    sh = bpy.context.active_object
    sh.scale = (1.0, 1.0, 0.55)
    bpy.ops.object.shade_smooth()
    sh.data.materials.append(mats["dark_metal"])

    # COMEDOR junto al ventanal (X = 7.45, Y = 2.65 — Render 3!)
    add_box("Comedor_Top", (1.05, 2.25, 0.05), (7.45, 2.65, z1 + 0.76), mats["dark_wood"], bevel=0.012)
    add_box("Comedor_Vid", (1.01, 2.20, 0.015), (7.45, 2.65, z1 + 0.795), mats["black_glass"])
    for lx in (-0.38, 0.38):
        for ly in (-0.84, 0.84):
            add_cyl(f"Com_P_{lx}_{ly}", 0.03, 0.75, (7.45 + lx, 2.65 + ly, z1 + 0.375), mats["wood"], (0.08 if ly > 0 else -0.08, -0.08 if lx > 0 else 0.08, 0), 10)
    for idx, cy in enumerate([1.85, 2.65, 3.45]):
        add_dining_chair(f"Silla_L_{idx}", (6.74, cy, z1), -math.pi / 2, mats["cream_fabric"], mats["wood"])
        add_dining_chair(f"Silla_R_{idx}", (8.16, cy, z1), math.pi / 2, mats["cream_fabric"], mats["wood"])
    add_box("Lamp_Com_B", (0.055, 1.55, 0.045), (7.45, 2.65, z1 + 2.35), mats["dark_metal"])
    add_box("Lamp_Com_L", (0.035, 1.48, 0.02), (7.45, 2.65, z1 + 2.32), mats["led"])

    # Cuadros enmarcados en Planta Alta (centrados sobre muros sólidos interiores sin invadir vanos)
    add_framed_artwork("Cuadro_Comedor", (8.72, 2.8, z1 + 1.65), 1.55, 0.95, "X", mats["dark_metal"], mats["art_living"])
    add_framed_artwork("Cuadro_Pasillo", (1.42, 7.2, z1 + 1.65), 1.25, 0.90, "X", mats["dark_metal"], mats["art_hall"])

    # STUDIO / RECÁMARA PA (X = 3.8..6.6, Y = 10.2..13.4 — muebles visibles desde el pasillo!)
    add_box("Escritorio_Studio", (1.65, 0.65, 0.05), (5.2, 13.0, z1 + 0.75), mats["wood"], bevel=0.01)
    add_dining_chair("Silla_Studio", (5.2, 12.3, z1), 0.0, mats["cream_fabric"], mats["wood"])
    add_framed_artwork("Cuadro_Studio", (5.2, 13.38, z1 + 1.75), 1.35, 0.85, "Y", mats["dark_metal"], mats["art_bed"])

    # FACHADA DE ENTRADA PRINCIPAL + COCHERA CON CELOSÍA DE MADERA Y PÉRGOLA (Y = 13.7..20.3)
    # Celosía vertical de madera sobre fachada Oeste de Cochera (X = 2.0..2.2, Y = 13.8..20.0 — Render 5!)
    for i in range(30):
        add_box(f"Celosia_Oeste_{i}", (0.10, 0.055, 3.05), (1.98, 14.0 + i * 0.205, z1 + 1.55), mats["wood"])
    # Pérgola superior de madera sobre la Cochera (Planta de Azotea A-1!)
    for i in range(14):
        add_box(f"Pergola_Cochera_{i}", (6.5, 0.10, 0.14), (5.3, 14.0 + i * 0.45, Z_TECHO + 0.08), mats["wood"])
    # Puerta Principal Pivotante de madera + marco negro + vidrio fijo + plafón LED (acceso en Y = 13.7, X = 7.2..8.8)
    add_box("Muro_Entrada_Madera", (2.6, 0.12, 3.00), (7.9, 13.72, z1 + 1.50), mats["dark_wood"])
    add_box("Marco_Ent_Top", (2.15, 0.16, 0.09), (7.9, 13.82, z1 + 2.66), mats["dark_metal"])
    add_box("Marco_Ent_L", (0.08, 0.16, 2.68), (6.86, 13.82, z1 + 1.34), mats["dark_metal"])
    add_box("Marco_Ent_R", (0.08, 0.16, 2.68), (8.94, 13.82, z1 + 1.34), mats["dark_metal"])
    add_box("Puerta_Principal", (1.34, 0.09, 2.60), (7.58, 13.84, z1 + 1.31), mats["wood"], bevel=0.015)
    for d in range(5):
        add_box(f"Pta_Duela_{d}", (0.02, 0.02, 2.56), (7.02 + d * 0.28, 13.90, z1 + 1.31), mats["dark_wood"])
    add_box("Jaladera_Ent", (0.045, 0.09, 1.30), (8.10, 13.92, z1 + 1.25), mats["dark_metal"])
    add_box("Vidrio_Fijo_Ent", (0.60, 0.04, 2.60), (8.60, 13.84, z1 + 1.31), mats["glass"])
    add_box("Macetero_Ent", (0.52, 0.52, 0.58), (6.25, 14.25, z1 + 0.30), mats["dark_metal"], bevel=0.015)
    add_lavender_clump("Planta_Ent", (6.25, 14.25, z1 + 0.60), mats["leaf_dark"], mats["leaf_light"], seed=88)
    add_box("Plafon_Ent_LED", (2.1, 0.52, 0.04), (7.9, 14.35, Z_TECHO - 0.05), mats["led"])
    add_point_light("Luz_Entrada", (7.9, 14.5, Z_TECHO - 0.5), energy=140, radius=0.25)

    # Escalera de madera real con huellas cálidas y LED (X = 0.6..2.0, bajando de Y=4.5 a Y=9.0 -> Z_SOTANO!)
    n_steps = 16
    for i in range(n_steps):
        sz = Z_SOTANO + 0.17 + i * ((Z_1P - Z_SOTANO) / n_steps)
        sy = 8.8 - i * 0.27
        add_box(f"Escalon_{i}", (1.20, 0.27, 0.075), (1.35, sy, sz), mats["wood"], bevel=0.008)
        if i % 3 == 0:
            add_box(f"Esc_LED_{i}", (1.10, 0.02, 0.02), (1.35, sy + 0.12, sz - 0.04), mats["led"])

    # =========================================================================
    # 4. SÓTANO / PLANTA BAJA — 3 CUARTOS EXACTOS + PATIO JARDÍN (Z = -2.89 m)
    #    Ver `plan_sotano_full.png`:
    #    - Recámara Principal: X = 5.2..8.6, Y = 0.3..4.9 (+ Vestidor/Baño X=2.2..5.2)
    #    - Recámara 1 (Centro): X = 4.5..8.6, Y = 5.2..8.6
    #    - Recámara 2 / Sala TV (Norte): X = 4.2..8.6, Y = 8.9..12.6
    #    - Patio Jardín Privado: X = 8.8..14.9, Y = 0.2..13.5
    # =========================================================================
    z0 = Z_SOTANO

    # Cancelería corrediza negra piso-techo en los 3 cuartos abriendo hacia el Patio (X = 8.65!)
    for idx, (y_start, y_end) in enumerate([(0.55, 4.35), (5.55, 8.25), (9.35, 12.15)]):
        span = y_end - y_start
        cy = (y_start + y_end) / 2.0
        add_box(f"Vidrio_PB_{idx}", (0.03, span, 2.40), (8.65, cy, z0 + 1.22), mats["glass"])
        for t in (0.0, 0.5, 1.0):
            add_box(f"Marco_PB_{idx}_{t:.1f}", (0.09, 0.07, 2.44), (8.65, y_start + span * t, z0 + 1.22), mats["dark_metal"])
        add_box(f"Cab_PB_{idx}", (0.10, span + 0.08, 0.07), (8.65, cy, z0 + 2.44), mats["dark_metal"])
        add_box(f"Cort_PB_A_{idx}", (0.08, 0.38, 2.38), (8.46, y_start + 0.22, z0 + 1.20), mats["sheer"])
        add_box(f"Cort_PB_B_{idx}", (0.08, 0.38, 2.38), (8.46, y_end - 0.22, z0 + 1.20), mats["sheer"])

    # CUARTO 1: RECÁMARA PRINCIPAL (X = 5.2..8.5, Y = 0.4..4.8) — Cama mirando al Patio (+X)!
    add_box("Tapete_RecP", (2.8, 3.2, 0.02), (6.9, 2.5, z0 + 0.01), mats["rug"])
    add_full_bed("Cama_Principal", (6.5, 2.5, z0), mats, mats["charcoal_fabric"], rot_z=-math.pi / 2, width=1.90)
    add_point_light("Luz_BP1", (5.8, 1.25, z0 + 0.85), 22, 0.14)
    add_point_light("Luz_BP2", (5.8, 3.75, z0 + 0.85), 22, 0.14)
    add_box("Banqueta_P", (0.42, 1.55, 0.40), (7.85, 2.5, z0 + 0.20), mats["cream_fabric"], bevel=0.03)
    add_framed_artwork("Cuadro_RecP_N", (6.8, 4.72, z0 + 1.55), 1.45, 0.85, "Y", mats["dark_metal"], mats["art_bed"])
    add_framed_artwork("Cuadro_RecP_S", (6.8, 0.56, z0 + 1.55), 1.45, 0.85, "Y", mats["dark_metal"], mats["art_living"])
    # Vestidor madera en zona posterior (X = 2.4..5.0, Y = 0.6..3.6)
    add_box("Vestidor_P", (0.55, 2.8, 2.35), (2.65, 2.1, z0 + 1.18), mats["wood"], bevel=0.01)
    for i in range(5):
        add_box(f"Vest_H_{i}", (0.03, 0.02, 0.36), (2.94, 0.95 + i * 0.55, z0 + 1.15), mats["dark_metal"])

    # CUARTO 2: RECÁMARA 1 (Centro, X = 4.6..8.5, Y = 5.3..8.5) — Cama mirando al Patio (+X)!
    add_box("Tapete_Rec1", (2.6, 2.6, 0.02), (6.6, 6.9, z0 + 0.01), mats["rug"])
    add_full_bed("Cama_Rec1", (6.1, 6.9, z0), mats, mats["olive"], rot_z=-math.pi / 2, width=1.65)
    add_point_light("Luz_BR1", (5.4, 5.8, z0 + 0.82), 18, 0.14)
    add_framed_artwork("Cuadro_Rec1", (6.6, 8.48, z0 + 1.52), 1.35, 0.80, "Y", mats["dark_metal"], mats["art_hall"])

    # CUARTO 3: RECÁMARA 2 / SALA TV (Norte, X = 4.4..8.5, Y = 9.0..12.4) — Cama + Mueble TV!
    add_box("Tapete_Rec2", (2.8, 2.8, 0.02), (6.5, 10.7, z0 + 0.01), mats["rug"])
    add_full_bed("Cama_Rec2", (5.9, 10.7, z0), mats, mats["taupe"], rot_z=-math.pi / 2, width=1.65)
    add_box("Mueble_TV_PB", (1.85, 0.42, 0.46), (6.5, 12.22, z0 + 0.23), mats["dark_wood"], bevel=0.012)
    add_box("TV_PB", (1.35, 0.04, 0.78), (6.5, 12.42, z0 + 1.18), mats["black_glass"])
    add_framed_artwork("Cuadro_Rec2", (6.5, 9.02, z0 + 1.52), 1.35, 0.80, "Y", mats["dark_metal"], mats["art_living"])

    # =========================================================================
    # 5. PATIO JARDÍN PRIVADO REAL (X = 8.8..14.8, Y = 0.2..13.5 — Fiel a Render 4!)
    # =========================================================================
    add_box("Grava_Patio", (6.0, 13.3, 0.08), (11.8, 6.85, z0 + 0.04), mats["gravel"])
    add_box("Pasto_Patio", (3.8, 6.2, 0.09), (12.8, 6.4, z0 + 0.048), mats["grass"])

    # Terraza de estar oscura al fondo Norte-Este del patio (Render 4)
    add_box("Terraza_Patio", (4.6, 3.6, 0.22), (12.2, 11.2, z0 + 0.15), mats["slate"], bevel=0.015)
    add_box("LED_Terraza", (4.3, 0.05, 0.04), (12.2, 9.38, z0 + 0.05), mats["led"])
    add_rattan_armchair("Sillon_P1", (11.1, 11.85, z0 + 0.26), -0.35, mats["cream_fabric"], mats["wood"])
    add_rattan_armchair("Sillon_P2", (13.3, 11.85, z0 + 0.26), 0.35, mats["cream_fabric"], mats["wood"])
    add_cyl("Mesa_P_Top", 0.50, 0.06, (12.2, 11.05, z0 + 0.58), mats["paver"])
    add_cyl("Mesa_P_Ped", 0.16, 0.30, (12.2, 11.05, z0 + 0.41), mats["paver"])
    add_cyl("Farol_P", 0.14, 0.28, (10.15, 9.65, z0 + 0.40), mats["dark_metal"], verts=14)
    add_cyl("Farol_L", 0.05, 0.12, (10.15, 9.65, z0 + 0.37), mats["led"], verts=10)

    # Andadores flotados de concreto gris (Render 4)
    for px, py, pw, pd in [
        (11.6, 8.65, 2.7, 1.05),
        (10.1, 7.10, 1.15, 1.35),
        (11.6, 7.10, 1.45, 1.35),
        (13.1, 7.10, 1.15, 1.35),
        (10.8, 5.20, 1.65, 1.15),
        (10.8, 3.40, 1.65, 1.15),
    ]:
        add_box(f"Paver_{px}_{py}", (pw, pd, 0.10), (px, py, z0 + 0.09), mats["paver"], bevel=0.015)

    # 2 Árboles frondosos con hojas individuales y flores blancas (Renders 1, 2 y 4)
    add_detailed_tree("Arbol_Principal", (13.1, 6.2, z0 + 0.05), 1.30, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=11)
    add_detailed_tree("Arbol_Secundario", (13.6, 9.8, z0 + 0.05), 1.02, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=29)

    # Rocas volcánicas esculpidas y lavanda (Render 4)
    add_boulder("Roca_1", 0.62, (12.1, 8.2, z0 + 0.34), mats["rock"], (1.35, 1.05, 0.62), seed=3)
    add_boulder("Roca_2", 0.78, (13.8, 9.1, z0 + 0.56), mats["rock"], (1.05, 0.95, 1.02), seed=7)
    add_boulder("Roca_3", 0.45, (10.2, 4.4, z0 + 0.25), mats["rock"], (1.28, 1.0, 0.58), seed=19)
    add_boulder("Roca_4", 0.50, (13.4, 4.6, z0 + 0.28), mats["rock"], (1.2, 0.9, 0.65), seed=41)

    for idx, (lx, ly) in enumerate([(12.5, 5.8), (13.2, 6.9), (12.3, 7.6), (13.6, 7.8), (12.8, 8.8)]):
        add_lavender_clump(f"Lavanda_{idx}", (lx, ly, z0 + 0.06), mats["leaf_dark"], mats["lavender"], seed=100 + idx)

    # Arbotantes cálidos negros en bardas del patio y machones entre recámaras (Render 4)
    for idx, (lx, ly, ox, oy) in enumerate([
        (14.70, 11.2, -0.18, 0),
        (14.70, 7.4, -0.18, 0),
        (14.70, 3.6, -0.18, 0),
        (12.2, 13.38, 0, -0.18),
        (8.78, 4.95, 0.18, 0),
        (8.78, 8.80, 0.18, 0),
    ]):
        add_box(f"Arb_{idx}", (0.14, 0.14, 0.15), (lx, ly, z0 + 1.95), mats["dark_metal"])
        add_box(f"Arb_L_{idx}", (0.11, 0.11, 0.19), (lx, ly, z0 + 1.95), mats["led"])
        add_point_light(f"Luz_Arb_{idx}", (lx + ox, ly + oy, z0 + 1.95), energy=26, radius=0.08)

    # =========================================================================
    # 6. ILUMINACIÓN ARQUITECTÓNICA CÁLIDA CALIBRADA A CADA CUARTO 1:1
    # =========================================================================
    add_area_light("Luz_Sala", (5.0, 3.2, Z_TECHO - 0.15), (0, 0, 0), 260, 2.8, 2.4, (1.0, 0.90, 0.76))
    add_area_light("Luz_Comedor", (7.45, 2.65, Z_TECHO - 0.25), (0, 0, 0), 170, 0.6, 1.8, (1.0, 0.88, 0.72))
    add_area_light("Luz_Cocina", (5.5, 6.7, Z_TECHO - 0.15), (0, 0, 0), 210, 3.2, 1.2, (1.0, 0.88, 0.70))
    add_area_light("Luz_Pasillo_1P", (2.4, 5.5, Z_TECHO - 0.15), (0, 0, 0), 170, 1.4, 4.0, (1.0, 0.89, 0.74))
    add_area_light("Luz_Studio", (5.2, 11.8, Z_TECHO - 0.15), (0, 0, 0), 140, 2.0, 2.0, (1.0, 0.89, 0.74))

    add_area_light("Luz_RecP", (6.8, 2.5, Z_1P - 0.42), (0, 0, 0), 185, 2.6, 2.8, (1.0, 0.87, 0.70))
    add_area_light("Luz_Rec1", (6.5, 6.9, Z_1P - 0.42), (0, 0, 0), 165, 2.4, 2.4, (1.0, 0.87, 0.70))
    add_area_light("Luz_Rec2", (6.4, 10.7, Z_1P - 0.42), (0, 0, 0), 165, 2.4, 2.4, (1.0, 0.87, 0.70))
    add_area_light("Luz_Esc_PB", (2.2, 6.5, Z_1P - 0.42), (0, 0, 0), 140, 1.6, 3.5, (1.0, 0.88, 0.72))
    add_area_light("Luz_Patio", (11.8, 7.5, Z_1P + 0.6), (0, 0, 0), 95, 3.5, 4.5, (1.0, 0.88, 0.72))


def render_panoramas():
    cam_data = bpy.data.cameras.new("Cam_360")
    cam_data.type = "PANO"
    if hasattr(cam_data, "panorama_type"):
        cam_data.panorama_type = "EQUIRECTANGULAR"
    elif hasattr(cam_data, "cycles"):
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"

    cam_obj = bpy.data.objects.new("Cam_360", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # 8 paradas exactas dentro y fuera de la geometría 1:1 del arquitecto
    stops = [
        ("01_fachada_esquina.jpg", (18.5, -6.2, -0.4)),
        ("02_fachada_entrada.jpg", (7.9, 16.4, Z_1P + 1.55)),
        ("03_pasillo_escaleras.jpg", (2.6, 5.4, Z_1P + 1.55)),
        ("04_sala_cocina.jpg", (5.8, 1.4, Z_1P + 1.50)),
        ("05_patio_jardin.jpg", (11.0, 5.2, Z_SOTANO + 1.60)),
        ("06_recamara_principal.jpg", (7.4, 3.9, Z_SOTANO + 1.45)),
        ("07_recamaras_sala_tv.jpg", (7.2, 10.6, Z_SOTANO + 1.45)),
        ("08_fachada_celosia.jpg", (-8.5, 13.5, Z_1P + 0.8)),
    ]

    only_env = os.environ.get("ONLY_STOPS", "").strip()
    only_prefixes = tuple(p.strip() for p in only_env.split(",") if p.strip()) if only_env else None

    for fname, loc in stops:
        if only_prefixes and not fname.startswith(only_prefixes):
            continue
        cam_obj.location = loc
        cam_obj.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
        out_path = os.path.join(OUT_DIR, fname)
        bpy.context.scene.render.filepath = out_path
        print(f"[Render 360 1:1] Generando {fname} en {loc} ...")
        bpy.ops.render.render(write_still=True)


def main():
    clear_scene()
    configure_cycles(samples=64, res_x=2048, res_y=1024)
    setup_world_sky()
    build_exact_scene()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"[Blender] Proyecto 1:1 exacto guardado en: {BLEND_PATH}")
    render_panoramas()
    print("[Blender] Los 8 panoramas 360° 1:1 exactos generados correctamente.")


if __name__ == "__main__":
    main()
