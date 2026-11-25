"""
Generador arquitectónico de alto detalle en Blender 5 (Cycles + OptiX GPU)
Casa Lote 8, Manzana 147, Fracc. México, Morelia, Mich.
Basado en la Lámina A-1 (Arq. Salvador Emmanuel Valencia Contreras) y los 5 renders de referencia.

Incluye:
- Terreno continuo con vialidad curva integrada a la pendiente (sin flotar) y lomas boscosas lejanas
- Cocina completa (gabinetes con juntas, nicho abierto, refrigerador doble puerta, estufa, tarja, grifo, mármol Calacatta y LED)
- Sala y Comedor detallados (sofá en L con cojines, tapete, mesa con florero y ramas, lámpara negra, mesa comedor y 6 sillas con patas)
- Recámaras detalladas (cabecera acanalada, ropa de cama en capas, burós con lámparas, closet de madera, mueble TV, cortinas y cuadros)
- Patio Jardín fotorrealista (árboles con hojas pequeñas y flores blancas, rocas volcánicas detalladas, lavanda, pasto, terraza pizarra, sillones rattan, faroles y arbotantes)
- Cuadros artísticos enmarcados en paredes de sala, pasillo y recámaras

Uso:
  blender --background --python blender/render_tour_360.py
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUT_DIR = os.path.join(PROJECT_ROOT, "assets", "panoramas")
BLEND_PATH = os.path.join(SCRIPT_DIR, "casa_l8_mexico.blend")
os.makedirs(OUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def configure_cycles(samples=72, res_x=2048, res_y=1024):
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
    scene.view_settings.exposure = -1.65


def setup_world_sky():
    world = bpy.data.worlds.new("Sky_Morelia_Golden")
    bpy.context.scene.world = world
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    # Intensidad física calibrada para evitar sobreexposición en exteriores con MULTIPLE_SCATTERING
    bg.inputs["Strength"].default_value = 0.24

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.0)
    sky.sun_intensity = 1.15
    sky.sun_elevation = math.radians(22)
    sky.sun_rotation = math.radians(132)
    sky.altitude = 1920.0
    if hasattr(sky, "air_density"):
        sky.air_density = 1.25
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 1.45

    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


# ---------------------------------------------------------------------------
# Materiales PBR procedurales ricos
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


def make_art_canvas_mat(name, col_a, col_b, col_c, scale=2.5):
    """Genera un cuadro minimalista abstracto procedural para muros interiores."""
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
# Helpers geométricos con biselado y detalle arquitectónico
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
    """Cuadro enmarcado montado en muro (axis='X' para muro paralelo a YZ, 'Y' para muro paralelo a XZ)."""
    x, y, z = loc
    depth = 0.045
    border = 0.035
    if axis == "Y":
        add_box(f"{name}_canvas", (width - border * 2, depth * 0.5, height - border * 2), (x, y, z), art_mat)
        add_box(f"{name}_top", (width, depth, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_bot", (width, depth, border), (x, y, z - height / 2 + border / 2), frame_mat)
        add_box(f"{name}_l", (border, depth, height), (x - width / 2 + border / 2, y, z), frame_mat)
        add_box(f"{name}_r", (border, depth, height), (x + width / 2 - border / 2, y, z), frame_mat)
    else:
        add_box(f"{name}_canvas", (depth * 0.5, width - border * 2, height - border * 2), (x, y, z), art_mat)
        add_box(f"{name}_top", (depth, width, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_bot", (depth, width, border), (x, y, z - height / 2 + border / 2), frame_mat)
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
        # Desplazamiento multifrecuencia anguloso como roca volcánica real
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
    """Árbol arquitectónico orgánico con ramas finas y cientos de hojas planas individuales (sombras moteadas reales)."""
    rng = random.Random(seed)
    x0, y0, z0 = loc

    # Tronco esbelto y ramas secundarias/terciarias
    add_cyl(f"{name}_trunk", 0.095 * scale, 2.3 * scale, (x0, y0, z0 + 1.15 * scale), bark_mat, (0.04, -0.05, 0), 12)
    branches = [
        (0.28, 0.14, 2.7, 0.28, 0.28, 0.0, 2.1, 0.048),
        (-0.32, -0.16, 2.65, -0.25, -0.34, 0.0, 2.0, 0.045),
        (0.06, 0.25, 3.05, -0.28, 0.10, 0.0, 2.3, 0.042),
        (0.75, 0.42, 3.8, 0.45, 0.42, 0.0, 1.5, 0.025),
        (-0.82, -0.35, 3.7, -0.38, -0.48, 0.0, 1.5, 0.024),
        (0.18, 0.72, 4.1, -0.45, 0.15, 0.0, 1.6, 0.022),
    ]
    for idx, (dx, dy, dz, rx, ry, rz, ln, rad) in enumerate(branches):
        add_cyl(f"{name}_br{idx}", rad * scale, ln * scale,
                (x0 + dx * scale, y0 + dy * scale, z0 + dz * scale), bark_mat, (rx, ry, rz), 8)

    # Malla de 750 hojitas planas en forma de rombo (aspecto ligero y natural, no bolas gruesas)
    def build_leaf_cloud(mesh_name, count, size_min, size_max, mat, z_min=2.4, z_span=3.5):
        mesh = bpy.data.meshes.new(mesh_name)
        bm = bmesh.new()
        for _ in range(count):
            layer = rng.random()
            rz = (z_min + layer * z_span) * scale
            max_r = max(0.45, (2.1 - abs(layer - 0.48) * 1.65) * scale)
            rad = (rng.random() ** 0.6) * max_r
            ang = rng.random() * math.tau
            center = Vector((rad * math.cos(ang), rad * math.sin(ang), rz))

            L = (size_min + rng.random() * (size_max - size_min)) * scale
            W = L * 0.46
            # Orientación aleatoria de la hoja
            rx = rng.uniform(-1.2, 1.2)
            ry = rng.uniform(-1.2, 1.2)
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
                # Rotar en X luego Z
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

    build_leaf_cloud(f"{name}_leaves_dark", 520, 0.16, 0.28, leaf_mat, 2.3, 3.6)
    build_leaf_cloud(f"{name}_leaves_light", 380, 0.14, 0.25, leaf_light_mat, 2.5, 3.5)
    build_leaf_cloud(f"{name}_blossoms", 160, 0.08, 0.13, blossom_mat, 2.7, 3.0)


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
        ox = r * math.cos(ang)
        oy = r * math.sin(ang)
        lean_x = ox * 0.45
        lean_y = oy * 0.45
        # Tallo verde
        v1 = bmg.verts.new((ox - 0.015, oy, 0))
        v2 = bmg.verts.new((ox + 0.015, oy, 0))
        v3 = bmg.verts.new((ox + lean_x + 0.01, oy + lean_y, h * 0.72))
        v4 = bmg.verts.new((ox + lean_x - 0.01, oy + lean_y, h * 0.72))
        bmg.faces.new((v1, v2, v3, v4))
        # Espiga morada arriba
        ret = bmesh.ops.create_icosphere(bmp, subdivisions=1, radius=0.032)
        for v in ret["verts"]:
            v.co.z *= 2.4
            v.co += Vector((ox + lean_x, oy + lean_y, h * 0.85))
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
    """Silla de comedor moderna con asiento tapizado curvo y patas inclinadas de roble (Render 3)."""
    x, y, z = loc
    g = bpy.data.objects.new(name, None)
    g.location = (x, y, z)
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)

    parts = [
        add_box(f"{name}_seat", (0.46, 0.46, 0.07), (0, 0, 0.45), fabric_mat, bevel=0.025),
        add_box(f"{name}_back", (0.46, 0.07, 0.36), (0, -0.20, 0.65), fabric_mat, (0.08, 0, 0), bevel=0.025),
        add_box(f"{name}_armL", (0.06, 0.36, 0.16), (-0.21, -0.04, 0.56), fabric_mat, bevel=0.02),
        add_box(f"{name}_armR", (0.06, 0.36, 0.16), (0.21, -0.04, 0.56), fabric_mat, bevel=0.02),
        add_cyl(f"{name}_leg1", 0.018, 0.44, (-0.18, -0.18, 0.22), wood_mat, (0.08, -0.08, 0), 10),
        add_cyl(f"{name}_leg2", 0.018, 0.44, (0.18, -0.18, 0.22), wood_mat, (0.08, 0.08, 0), 10),
        add_cyl(f"{name}_leg3", 0.018, 0.44, (-0.18, 0.18, 0.22), wood_mat, (-0.08, -0.08, 0), 10),
        add_cyl(f"{name}_leg4", 0.018, 0.44, (0.18, 0.18, 0.22), wood_mat, (-0.08, 0.08, 0), 10),
    ]
    for p in parts:
        p.parent = g


def add_rattan_armchair(name, loc, rot_z, fabric_mat, wood_mat):
    """Sillón de patio con respaldo curvo de madera/rattan y cojines crema (Render 4)."""
    x, y, z = loc
    g = bpy.data.objects.new(name, None)
    g.location = (x, y, z)
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)

    parts = [
        add_cyl(f"{name}_base", 0.42, 0.24, (0, 0, 0.24), fabric_mat, verts=24),
        add_cyl(f"{name}_cushion", 0.41, 0.12, (0, 0, 0.40), fabric_mat, verts=24),
        add_box(f"{name}_pillow", (0.48, 0.16, 0.36), (0, -0.20, 0.60), fabric_mat, (0.15, 0, 0), bevel=0.05),
    ]
    # Costillas verticales del respaldo curvo de rattan
    for i in range(11):
        ang = math.radians(-105 + i * 21)
        px = 0.42 * math.sin(ang)
        py = -0.42 * math.cos(ang)
        parts.append(add_cyl(f"{name}_rib{i}", 0.016, 0.46, (px, py, 0.56), wood_mat, verts=8))
    # Patas cortas
    for lx, ly in [(-0.26, -0.26), (0.26, -0.26), (-0.26, 0.26), (0.26, 0.26)]:
        parts.append(add_cyl(f"{name}_leg_{lx}_{ly}", 0.02, 0.12, (lx, ly, 0.06), wood_mat, verts=8))
    for p in parts:
        p.parent = g


def add_area_light(name, loc, rot, energy, size_x, size_y, color=(1.0, 0.87, 0.70)):
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.energy = energy
    ldata.color = color
    ldata.shape = "RECTANGLE"
    ldata.size = size_x
    ldata.size_y = size_y
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = loc
    lobj.rotation_euler = rot
    # Evitar reflejos rectangulares blancos en los ventanales
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
    bpy.context.collection.objects.link(lobj)
    return lobj


# ---------------------------------------------------------------------------
# Función de altura del terreno (compartida entre terreno y calle para que nunca flote)
# ---------------------------------------------------------------------------
def terrain_height(wx, wy):
    dx = max(0.0, -wx, wx - 15.0)
    dy = max(0.0, -wy, wy - 20.0)
    dist = math.hypot(dx, dy)
    t = min(1.0, max(0.0, (dist - 0.6) / 11.0))
    blend = t * t * (3.0 - 2.0 * t)
    slope = (5.0 - wx) * 0.055 + (wy - 10.0) * 0.048
    hill = math.sin(wx * 0.04) * 0.50 + math.cos(wy * 0.04) * 0.42
    target_z = max(-4.8, min(3.8, slope + hill - 0.12))
    return -0.14 * (1.0 - blend) + target_z * blend


def build_house_scene():
    mats = {
        "stucco": make_pbr_mat("Estuco_Blanco", (0.86, 0.85, 0.82), roughness=0.84, bump_scale=38.0, bump_strength=0.045,
                               color2=(0.80, 0.79, 0.76), color_noise_scale=3.0),
        "warm_wall": make_pbr_mat("Muro_Interior", (0.72, 0.68, 0.62), roughness=0.82, bump_scale=30.0, bump_strength=0.025),
        "floor_polished": make_pbr_mat("Piso_Microcemento", (0.62, 0.58, 0.52), roughness=0.14, bump_scale=10.0, bump_strength=0.012,
                                       color2=(0.56, 0.52, 0.47), color_noise_scale=2.2),
        "grass": make_pbr_mat("Pasto_Lomas", (0.11, 0.14, 0.055), roughness=0.96, bump_scale=42.0, bump_strength=0.35,
                              color2=(0.18, 0.21, 0.09), color_noise_scale=2.5),
        "hill_forest": make_pbr_mat("Lomas_Bosque", (0.06, 0.09, 0.04), roughness=0.98, bump_scale=12.0, bump_strength=0.45,
                                    color2=(0.13, 0.14, 0.06), color_noise_scale=1.5),
        "road": make_pbr_mat("Grava_Vial", (0.36, 0.34, 0.31), roughness=0.72, bump_scale=85.0, bump_strength=0.18,
                             color2=(0.45, 0.43, 0.39), color_noise_scale=9.0),
        "gravel": make_pbr_mat("Grava_Patio", (0.30, 0.28, 0.25), roughness=0.92, bump_scale=95.0, bump_strength=0.25,
                               color2=(0.38, 0.36, 0.32), color_noise_scale=12.0),
        "slate": make_pbr_mat("Deck_Pizarra", (0.10, 0.11, 0.12), roughness=0.68, bump_scale=22.0, bump_strength=0.05),
        "paver": make_pbr_mat("Andador_Concreto", (0.28, 0.28, 0.27), roughness=0.84, bump_scale=35.0, bump_strength=0.06),
        "wood": make_pbr_mat("Madera_Roble", (0.34, 0.22, 0.13), roughness=0.58, bump_scale=24.0, bump_strength=0.05,
                             color2=(0.25, 0.16, 0.09), color_noise_scale=8.0),
        "dark_wood": make_pbr_mat("Madera_Nogal", (0.14, 0.09, 0.06), roughness=0.52),
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
        "black_glass": make_pbr_mat("Vidrio_Negro_Parrilla", (0.02, 0.02, 0.025), roughness=0.06, metallic=0.15),
        "glass": make_pbr_mat("Vidrio_Arq", (0.86, 0.93, 0.97), roughness=0.02, transmission=0.92, ior=1.5),
        "sheer": make_pbr_mat("Cortina_Transl", (0.86, 0.84, 0.80), roughness=0.92, transmission=0.45),
        "rock": make_rock_mat("Roca_Volcanica"),
        "bark": make_pbr_mat("Corteza", (0.13, 0.10, 0.07), roughness=0.94, bump_scale=28.0, bump_strength=0.22),
        "leaf_dark": make_pbr_mat("Follaje_Oscuro", (0.07, 0.15, 0.045), roughness=0.68),
        "leaf_light": make_pbr_mat("Follaje_Claro", (0.14, 0.24, 0.075), roughness=0.64),
        "blossom": make_pbr_mat("Flor_Blanca", (0.94, 0.93, 0.90), roughness=0.62),
        "lavender": make_pbr_mat("Lavanda", (0.24, 0.14, 0.34), roughness=0.88),
        "led": make_pbr_mat("LED_Calido", (1.0, 0.92, 0.76), roughness=0.3, emission=(1.0, 0.78, 0.44), emission_strength=10.0),
        "art_living": make_art_canvas_mat("Cuadro_Sala", (0.12, 0.11, 0.10), (0.68, 0.56, 0.42), (0.88, 0.85, 0.80), 2.0),
        "art_bed": make_art_canvas_mat("Cuadro_Recamara", (0.18, 0.20, 0.15), (0.58, 0.52, 0.44), (0.86, 0.83, 0.78), 2.8),
        "art_hall": make_art_canvas_mat("Cuadro_Pasillo", (0.15, 0.14, 0.14), (0.45, 0.34, 0.25), (0.84, 0.80, 0.74), 3.2),
    }

    # =========================================================================
    # 1. TERRENO EN PENDIENTE + CALLE CURVA PEGADA AL TERRENO + LOMAS LEJANAS
    # =========================================================================
    mesh = bpy.data.meshes.new("Terreno_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=84, y_segments=84, size=75.0)
    for v in bm.verts:
        wx = v.co.x + 7.5
        wy = v.co.y + 10.0
        v.co.x = wx
        v.co.y = wy
        v.co.z = terrain_height(wx, wy)
    bm.to_mesh(mesh)
    bm.free()
    terrain = bpy.data.objects.new("Terreno_Lomas", mesh)
    terrain.data.materials.append(mats["grass"])
    bpy.context.collection.objects.link(terrain)
    bpy.context.view_layer.objects.active = terrain
    bpy.ops.object.shade_smooth()

    # Vialidad curva conformada exactamente a `terrain_height(x, y) + 0.04` (NUNCA flota)
    road_pts = [
        (-4.2, 34.0), (-4.0, 20.0), (-3.8, 8.0), (-3.6, 0.5),
        (-2.5, -3.5), (2.5, -4.4), (14.5, -4.6), (34.0, -5.8),
    ]
    road_mesh = bpy.data.meshes.new("Vialidad_Curva_Mesh")
    rbm = bmesh.new()
    # Interpolar puntos suaves Catmull-Rom simple
    dense = []
    for seg in range(len(road_pts) - 1):
        p0 = Vector(road_pts[max(0, seg - 1)])
        p1 = Vector(road_pts[seg])
        p2 = Vector(road_pts[seg + 1])
        p3 = Vector(road_pts[min(len(road_pts) - 1, seg + 2)])
        steps = 10
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            pt = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            dense.append(pt)
    dense.append(Vector(road_pts[-1]))

    half_w = 3.1
    prev_pair = None
    for i, pt in enumerate(dense):
        nxt = dense[min(len(dense) - 1, i + 1)]
        prv = dense[max(0, i - 1)]
        tan = (nxt - prv).normalized()
        right = Vector((tan.y, -tan.x))
        pL = pt - right * half_w
        pR = pt + right * half_w
        vL = rbm.verts.new((pL.x, pL.y, terrain_height(pL.x, pL.y) + 0.05))
        vR = rbm.verts.new((pR.x, pR.y, terrain_height(pR.x, pR.y) + 0.05))
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

    # Cordillera natural continua en el horizonte (crestas irregulares, no esferas lisas)
    ridge_mesh = bpy.data.meshes.new("Cordillera_Horizonte_Mesh")
    hbm = bmesh.new()
    rings = 72
    r_inner = 68.0
    r_outer = 145.0
    ring_in = []
    ring_mid = []
    ring_out = []
    for i in range(rings):
        ang = (i / rings) * math.tau
        ca, sa = math.cos(ang), math.sin(ang)
        # Perfil montañoso natural con múltiples armónicos (estilo lomas de Morelia)
        h_peak = (
            12.0
            + 5.5 * math.sin(ang * 3.0 + 0.4)
            + 3.8 * math.cos(ang * 7.0 - 0.8)
            + 2.4 * math.sin(ang * 13.0 + 1.2)
            + 1.5 * math.cos(ang * 23.0)
        )
        z_in = terrain_height(7.5 + ca * r_inner, 10.0 + sa * r_inner) - 0.8
        ring_in.append(hbm.verts.new((7.5 + ca * r_inner, 10.0 + sa * r_inner, z_in)))
        ring_mid.append(hbm.verts.new((7.5 + ca * 105.0, 10.0 + sa * 105.0, max(3.5, h_peak))))
        ring_out.append(hbm.verts.new((7.5 + ca * r_outer, 10.0 + sa * r_outer, -6.0)))
    for i in range(rings):
        ni = (i + 1) % rings
        hbm.faces.new((ring_in[i], ring_in[ni], ring_mid[ni], ring_mid[i]))
        hbm.faces.new((ring_mid[i], ring_mid[ni], ring_out[ni], ring_out[i]))
    hbm.to_mesh(ridge_mesh)
    hbm.free()
    ridge_obj = bpy.data.objects.new("Cordillera_Horizonte", ridge_mesh)
    ridge_obj.data.materials.append(mats["hill_forest"])
    bpy.context.collection.objects.link(ridge_obj)
    bpy.context.view_layer.objects.active = ridge_obj
    bpy.ops.object.shade_smooth()

    # =========================================================================
    # 2. SÓTANO / PLANTA BAJA (Z = 0..3.05 m) — Recámaras + Patio Jardín
    # =========================================================================
    add_box("Losa_Sotano", (15.0, 20.0, 0.25), (7.5, 10.0, -0.125), mats["floor_polished"])
    add_box("Cimentacion", (15.04, 20.04, 2.2), (7.5, 10.0, -1.2), mats["stucco"])

    # Bardas perimetrales blancas + aletas altas de fachada (Renders 1, 2 y 4)
    add_box("Barda_Sur", (15.0, 0.28, 3.0), (7.5, 0.14, 1.5), mats["stucco"])
    add_box("Barda_Norte", (15.0, 0.28, 3.05), (7.5, 19.86, 1.525), mats["stucco"])
    add_box("Barda_Este", (0.28, 20.0, 3.05), (14.86, 10.0, 1.525), mats["stucco"])
    add_box("Muro_Oeste_Base", (0.28, 20.0, 3.25), (0.14, 10.0, 1.625), mats["stucco"])
    add_box("Aleta_Este_Patio", (0.28, 5.2, 6.2), (14.86, 17.4, 3.1), mats["stucco"])
    add_box("Aleta_Oeste_Sur", (0.28, 4.4, 6.45), (0.14, 2.2, 3.225), mats["stucco"])

    # Cerramiento arquitectónico completo de las Recámaras hacia el Patio (Render 4: dos vanos con machón blanco entre ellos!)
    add_box("Muro_Oeste_Rec", (0.24, 11.4, 3.05), (0.26, 5.8, 1.52), mats["warm_wall"])
    add_box("Muro_Div_Rec1_Rec2", (0.22, 11.4, 3.05), (4.5, 5.8, 1.52), mats["warm_wall"])
    add_box("Muro_Pasillo_Sur", (9.2, 0.22, 3.05), (4.7, 4.2, 1.52), mats["warm_wall"])
    add_box("Muro_Este_Recamaras", (0.26, 11.5, 3.05), (9.15, 5.85, 1.52), mats["stucco"])
    # Machón blanco central en fachada hacia patio con arbotante (Render 4)
    add_box("Machon_Patio_Central", (1.25, 0.30, 3.05), (4.5, 11.55, 1.52), mats["stucco"])
    add_box("Machon_Patio_Der", (0.75, 0.30, 3.05), (8.85, 11.55, 1.52), mats["stucco"])
    add_box("Machon_Patio_Izq", (0.55, 0.30, 3.05), (0.45, 11.55, 1.52), mats["stucco"])

    # Dos ventanales corredizos con cancelería negra piso-techo hacia el Patio (Render 4)
    for v_idx, (x_start, x_end) in enumerate([(0.72, 3.88), (5.12, 8.48)]):
        w_span = x_end - x_start
        cx = (x_start + x_end) / 2.0
        add_box(f"Vidrio_Rec_{v_idx}", (w_span, 0.03, 2.86), (cx, 11.55, 1.45), mats["glass"])
        for t in (0.0, 0.33, 0.67, 1.0):
            mx = x_start + w_span * t
            add_box(f"Marco_Rec_{v_idx}_{t:.2f}", (0.075, 0.09, 2.92), (mx, 11.55, 1.46), mats["dark_metal"])
        add_box(f"Cabezal_Rec_{v_idx}", (w_span + 0.08, 0.10, 0.08), (cx, 11.55, 2.94), mats["dark_metal"])
        # Cortinas traslúcidas laterales
        add_box(f"Cortina_L_{v_idx}", (0.42, 0.08, 2.86), (x_start + 0.25, 11.36, 1.44), mats["sheer"])
        add_box(f"Cortina_R_{v_idx}", (0.42, 0.08, 2.86), (x_end - 0.25, 11.36, 1.44), mats["sheer"])

    # MOBILIARIO DETALLADO DE RECÁMARAS (Recámara Principal derecha + Recámara 2 izquierda)
    # Recámara Principal (X = 4.6..9.0, Y = 4.3..11.4 — donde está la cámara 04_recamara)
    add_box("Tapete_RecP", (3.1, 3.4, 0.02), (6.75, 8.5, 0.01), mats["rug"])
    # Cabecera alta acanalada (paneles verticales beige como en Render 4!)
    for i in range(9):
        add_box(f"Cabecera_Panel_{i}", (0.24, 0.10, 1.38), (5.75 + i * 0.25, 6.95, 0.72), mats["cream_fabric"], bevel=0.02)
    # Base de cama + colchón + sábanas blancas + cobija oscura doblada + 4 almohadas
    add_box("CamaP_Base", (2.05, 2.15, 0.26), (6.75, 8.05, 0.15), mats["dark_wood"], bevel=0.015)
    add_box("CamaP_Colchon", (1.96, 2.04, 0.24), (6.75, 8.05, 0.40), mats["white_linen"], bevel=0.04)
    add_box("CamaP_Cobija", (2.00, 1.25, 0.08), (6.75, 8.45, 0.53), mats["charcoal_fabric"], bevel=0.03)
    for px in (6.25, 7.25):
        add_box(f"Almohada_A_{px}", (0.72, 0.36, 0.16), (px, 7.30, 0.58), mats["white_linen"], (0.18, 0, 0), bevel=0.05)
        add_box(f"Almohada_B_{px}", (0.52, 0.26, 0.18), (px, 7.58, 0.60), mats["taupe"], (0.25, 0, 0), bevel=0.05)

    # Burós de madera flotados + lámparas cálidas de noche
    for idx, bx in enumerate([5.25, 8.25]):
        add_box(f"Buro_{idx}", (0.58, 0.44, 0.28), (bx, 7.22, 0.36), mats["wood"], bevel=0.012)
        add_cyl(f"LampBase_{idx}", 0.08, 0.24, (bx, 7.22, 0.62), mats["dark_metal"])
        add_cyl(f"LampShade_{idx}", 0.15, 0.18, (bx, 7.22, 0.80), mats["led"])
        add_point_light(f"Luz_Buro_{idx}", (bx, 7.22, 0.82), energy=22, radius=0.14)

    # Cuadro enmarcado sobre la cabecera + cuadro lateral en muro Oeste de recámara
    add_framed_artwork("Cuadro_Cabecera", (6.75, 6.86, 2.02), 1.75, 0.95, "Y", mats["dark_metal"], mats["art_bed"])
    add_framed_artwork("Cuadro_Rec_Oeste", (4.64, 8.6, 1.72), 1.25, 0.85, "X", mats["dark_metal"], mats["art_hall"])

    # Closet / Vestidor de madera acanalada con jaladeras negras en muro Este de recámara
    add_box("Closet_Cuerpo", (0.58, 3.2, 2.75), (8.72, 8.5, 1.38), mats["wood"], bevel=0.01)
    for i in range(6):
        add_box(f"Closet_Junta_{i}", (0.02, 0.015, 2.72), (8.42, 7.18 + i * 0.52, 1.38), mats["dark_metal"])
        add_box(f"Closet_Jal_{i}", (0.03, 0.02, 0.38), (8.40, 7.36 + i * 0.52, 1.32), mats["dark_metal"])

    # Recámara 2 (visible a través del segundo ventanal desde el patio)
    add_box("Cama2_Base", (1.85, 2.05, 0.28), (2.3, 8.6, 0.14), mats["wood"], bevel=0.015)
    add_box("Cama2_Colchon", (1.78, 1.98, 0.24), (2.3, 8.6, 0.38), mats["white_linen"], bevel=0.04)
    add_box("Cama2_Cobija", (1.80, 1.15, 0.08), (2.3, 9.0, 0.51), mats["olive"], bevel=0.03)
    add_box("Cama2_Cabecera", (1.92, 0.12, 1.25), (2.3, 7.55, 0.62), mats["cream_fabric"], bevel=0.02)
    add_framed_artwork("Cuadro_Rec2", (2.3, 7.46, 1.85), 1.35, 0.82, "Y", mats["dark_metal"], mats["art_living"])

    # =========================================================================
    # 3. PATIO JARDÍN PRIVADO DETALLADO (Y = 11.7..19.7 — Fiel a Render 4)
    # =========================================================================
    add_box("Grava_Patio", (14.4, 8.0, 0.06), (7.55, 15.75, 0.03), mats["gravel"])
    # Parche de pasto verde natural bajo los árboles y rocas (Render 4)
    add_box("Pasto_Jardin_Patio", (5.2, 6.2, 0.07), (12.1, 15.6, 0.038), mats["grass"])

    # Terraza de estar en pizarra oscura + luz LED inferior + 2 sillones rattan + mesa + farol
    add_box("Terraza_Patio", (5.5, 3.8, 0.22), (10.8, 17.55, 0.14), mats["slate"], bevel=0.015)
    add_box("LED_Terraza", (5.1, 0.05, 0.04), (10.8, 15.62, 0.04), mats["led"])
    add_rattan_armchair("Sillon_Patio_1", (9.6, 18.2, 0.25), -0.35, mats["cream_fabric"], mats["wood"])
    add_rattan_armchair("Sillon_Patio_2", (12.0, 18.2, 0.25), 0.35, mats["cream_fabric"], mats["wood"])
    add_cyl("Mesa_Patio_Top", 0.52, 0.06, (10.8, 17.45, 0.58), mats["paver"])
    add_cyl("Mesa_Patio_Ped", 0.18, 0.32, (10.8, 17.45, 0.40), mats["paver"])
    # Farol negro con vela cálida en esquina de terraza (Render 4)
    add_cyl("Farol_Patio", 0.14, 0.28, (8.6, 15.85, 0.39), mats["dark_metal"], verts=14)
    add_cyl("Farol_Luz", 0.05, 0.12, (8.6, 15.85, 0.36), mats["led"], verts=10)

    # Andadores de concreto gris flotados (Render 4)
    for px, py, pw, pd in [
        (10.8, 14.95, 2.9, 1.12),
        (9.1, 13.35, 1.22, 1.42),
        (10.8, 13.35, 1.65, 1.42),
        (12.5, 13.35, 1.22, 1.42),
        (6.4, 13.35, 1.5, 1.1),
        (4.2, 13.35, 1.5, 1.1),
    ]:
        add_box(f"Paver_{px}_{py}", (pw, pd, 0.10), (px, py, 0.08), mats["paver"], bevel=0.015)

    # Árboles ornamentales con hojas individuales y flores blancas (Renders 1, 2 y 4)
    add_detailed_tree("Arbol_Principal", (12.8, 14.6, 0.05), 1.25, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=11)
    add_detailed_tree("Arbol_Secundario", (13.4, 17.4, 0.05), 0.98, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=29)

    # Rocas volcánicas esculpidas realistas (Render 4)
    add_boulder("Roca_1", 0.65, (11.6, 15.3, 0.32), mats["rock"], (1.35, 1.05, 0.62), seed=3)
    add_boulder("Roca_2", 0.82, (13.7, 16.2, 0.56), mats["rock"], (1.05, 0.95, 1.02), seed=7)
    add_boulder("Roca_3", 0.46, (8.5, 12.6, 0.24), mats["rock"], (1.28, 1.0, 0.58), seed=19)
    add_boulder("Roca_4", 0.52, (13.3, 13.2, 0.28), mats["rock"], (1.2, 0.9, 0.65), seed=41)

    # Macizos de lavanda morada (Render 4)
    for idx, (lx, ly) in enumerate([(12.2, 14.2), (12.9, 15.3), (11.8, 16.0), (13.5, 14.9), (12.4, 16.8)]):
        add_lavender_clump(f"Lavanda_{idx}", (lx, ly, 0.05), mats["leaf_dark"], mats["lavender"], seed=100 + idx)

    # Arbotantes negros con luz real arriba/abajo sobre bardas blancas (Render 4)
    for idx, (lx, ly, off_x, off_y) in enumerate([
        (14.66, 17.4, -0.18, 0),
        (14.66, 14.0, -0.18, 0),
        (10.8, 19.66, 0, -0.18),
        (6.4, 19.66, 0, -0.18),
        (4.5, 11.72, 0, 0.18),
    ]):
        add_box(f"Arbotante_{idx}", (0.14, 0.14, 0.15), (lx, ly, 2.25), mats["dark_metal"])
        add_box(f"Arbotante_LED_{idx}", (0.11, 0.11, 0.19), (lx, ly, 2.25), mats["led"])
        add_point_light(f"Luz_Arbotante_{idx}", (lx + off_x, ly + off_y, 2.25), energy=28, radius=0.08)

    # =========================================================================
    # 4. PRIMERA PLANTA (Z = 3.25..6.45 m) — Voladizo Social + Cochera Celosía
    # =========================================================================
    add_box("Franja_LED_Sur", (9.1, 0.10, 0.28), (10.05, 0.65, 3.13), mats["led"])
    add_box("Franja_LED_Este", (0.10, 9.6, 0.28), (14.35, 5.6, 3.13), mats["led"])

    add_box("Losa_1P", (14.5, 11.5, 0.26), (7.5, 6.0, 3.32), mats["floor_polished"])

    # Fachada Oeste + Celosía vertical de madera (Render 5)
    add_box("Muro_Oeste_1P", (0.28, 10.2, 3.35), (0.14, 5.3, 4.95), mats["stucco"])
    add_box("Dintel_Celosia", (0.28, 8.6, 0.36), (0.14, 14.35, 6.45), mats["stucco"])
    add_box("Jamba_Celosia", (0.28, 0.38, 3.35), (0.14, 18.48, 4.95), mats["stucco"])
    for i in range(40):
        add_box(f"Celosia_{i}", (0.11, 0.052, 3.08), (0.18, 10.3 + i * 0.20, 4.78), mats["wood"])

    # Volumen social en voladizo (Sur ciego + marco profundo Este + fondo cocina + pasillo con puerta!)
    add_box("Voladizo_Sur", (9.45, 0.34, 3.22), (10.12, 0.14, 5.02), mats["stucco"])
    add_box("Marco_Inf_Este", (0.55, 11.6, 0.28), (14.62, 5.85, 3.44), mats["stucco"])
    add_box("Marco_Sup_Este", (0.55, 11.6, 0.32), (14.62, 5.85, 6.48), mats["stucco"])
    add_box("Muro_Cocina", (5.8, 0.26, 3.18), (9.0, 11.58, 5.0), mats["stucco"])
    add_box("Muro_Oeste_Sala", (0.24, 11.0, 3.08), (6.2, 5.8, 4.95), mats["warm_wall"])
    # Muro bajo de escalera en pasillo izquierdo + puerta de madera con franja de vidrio (Render 3!)
    add_box("Barandal_Escalera", (0.18, 3.4, 1.05), (7.15, 7.6, 3.98), mats["warm_wall"])
    add_box("Puerta_Pasillo", (1.05, 0.08, 2.35), (6.75, 11.35, 4.62), mats["beige_cab"], bevel=0.01)
    add_box("Puerta_Franja", (1.06, 0.09, 0.16), (6.75, 11.35, 4.35), mats["dark_metal"])

    # Ventanal panorámico rehundido (Este y Norte)
    add_box("Ventanal_Este", (0.03, 10.8, 2.95), (14.48, 6.0, 4.96), mats["glass"])
    for my in (0.65, 3.3, 5.95, 8.6, 11.25):
        add_box(f"Parteluz_{my}", (0.08, 0.06, 2.96), (14.48, my, 4.96), mats["alum"])
    add_box("Travesano_Este", (0.08, 10.7, 0.055), (14.48, 6.0, 4.18), mats["alum"])

    # =========================================================================
    # 5. COCINA, SALA, COMEDOR Y CUADROS DE ALTO DETALLE (Fiel a Render 3)
    # =========================================================================
    z1 = 3.45

    # COCINA: 6 puertas individuales de gabinetes beige superiores con juntas oscuras + nicho abierto
    for i in range(6):
        add_box(f"Gab_Sup_{i}", (0.58, 0.44, 1.18), (9.02 + i * 0.61, 11.18, z1 + 2.28), mats["beige_cab"], bevel=0.008)
    # Nicho abierto de madera junto al refrigerador (Render 3)
    add_box("Nicho_Cocina_Top", (0.48, 0.42, 0.04), (8.46, 11.18, z1 + 2.22), mats["beige_cab"])
    add_box("Nicho_Cocina_Bot", (0.48, 0.42, 0.04), (8.46, 11.18, z1 + 1.66), mats["beige_cab"])
    add_box("Nicho_Cocina_Side", (0.04, 0.42, 0.58), (8.24, 11.18, z1 + 1.94), mats["beige_cab"])
    # Backsplash de mármol Calacatta + tira LED cálida bajo gabinetes
    add_box("Backsplash_Marmol", (4.15, 0.05, 0.86), (10.35, 11.38, z1 + 1.28), mats["marble"])
    add_box("LED_Cocina", (3.95, 0.05, 0.04), (10.35, 11.25, z1 + 1.66), mats["led"])
    # Mueble inferior cocina + cubierta mármol + parrilla de gas negra + horno
    add_box("Cocina_Inf", (4.15, 0.64, 0.88), (10.35, 11.06, z1 + 0.44), mats["dark_island"], bevel=0.01)
    add_box("Cocina_Cubierta", (4.18, 0.68, 0.05), (10.35, 11.05, z1 + 0.90), mats["marble"], bevel=0.008)
    add_box("Parrilla_Vidrio", (0.76, 0.52, 0.025), (10.6, 11.05, z1 + 0.935), mats["black_glass"])
    for qx in (10.38, 10.82):
        for qy in (10.92, 11.18):
            add_cyl(f"Quemador_{qx}_{qy}", 0.065, 0.02, (qx, qy, z1 + 0.955), mats["dark_metal"], verts=14)
    add_box("Horno_Frente", (0.68, 0.04, 0.54), (10.6, 10.73, z1 + 0.48), mats["black_glass"])
    add_box("Horno_Manija", (0.52, 0.04, 0.025), (10.6, 10.69, z1 + 0.68), mats["alum"])

    # Refrigerador inoxidable de doble puerta con división vertical (Render 3)
    add_box("Refri_Izq", (0.45, 0.72, 2.08), (7.52, 11.02, z1 + 1.04), mats["alum"], bevel=0.015)
    add_box("Refri_Der", (0.45, 0.72, 2.08), (7.99, 11.02, z1 + 1.04), mats["alum"], bevel=0.015)

    # Isla oscura con cubierta cascada de mármol + tarja y llave cuello de ganso cromada (Render 3)
    add_box("Isla_Base", (3.55, 1.02, 0.90), (10.35, 9.05, z1 + 0.45), mats["dark_island"], bevel=0.012)
    add_box("Isla_Marmol", (3.68, 1.14, 0.06), (10.35, 9.05, z1 + 0.93), mats["marble"], bevel=0.01)
    add_box("Tarja_Hundida", (0.68, 0.46, 0.03), (9.55, 9.15, z1 + 0.95), mats["dark_metal"])
    add_cyl("Grifo_Poste", 0.018, 0.34, (9.55, 9.42, z1 + 1.12), mats["chrome"], verts=12)
    add_cyl("Grifo_Pico", 0.015, 0.20, (9.55, 9.32, z1 + 1.28), mats["chrome"], (math.radians(90), 0, 0), verts=12)

    # SALA (Render 3): Tapete tejido + Sofá en L mullido con cojines individuales + Mesa negra con florero + Lámpara hongo
    add_box("Tapete_Sala", (4.0, 3.4, 0.02), (10.6, 5.8, z1 + 0.01), mats["rug"])
    # Estructura sofá en L
    add_box("Sofa_Frame_1", (3.25, 1.02, 0.24), (10.55, 6.45, z1 + 0.16), mats["cream_fabric"], bevel=0.03)
    for i in range(3):
        add_box(f"Sofa_Asiento_{i}", (1.02, 0.92, 0.18), (9.52 + i * 1.04, 6.42, z1 + 0.36), mats["cream_fabric"], bevel=0.05)
        add_box(f"Sofa_Respaldo_{i}", (1.02, 0.22, 0.46), (9.52 + i * 1.04, 6.82, z1 + 0.64), mats["cream_fabric"], (-0.12, 0, 0), bevel=0.05)
    add_box("Sofa_Brazo_R", (0.22, 1.02, 0.54), (12.16, 6.45, z1 + 0.36), mats["cream_fabric"], bevel=0.04)
    # Chaise longue izquierdo
    add_box("Sofa_Chaise_Base", (1.06, 2.15, 0.24), (9.48, 5.25, z1 + 0.16), mats["cream_fabric"], bevel=0.03)
    add_box("Sofa_Chaise_Cush", (1.00, 1.98, 0.18), (9.48, 5.25, z1 + 0.36), mats["cream_fabric"], bevel=0.05)
    # 5 cojines decorativos olivo y taupe (Render 3)
    for idx, (cx, cy, cz, ry, cmat) in enumerate([
        (9.35, 6.55, z1 + 0.58, 0.18, mats["taupe"]),
        (9.85, 6.52, z1 + 0.56, -0.14, mats["olive"]),
        (10.65, 6.54, z1 + 0.57, 0.10, mats["taupe"]),
        (11.65, 6.54, z1 + 0.57, -0.16, mats["olive"]),
        (11.95, 6.38, z1 + 0.55, 0.22, mats["taupe"]),
    ]):
        add_box(f"Cojin_{idx}", (0.44, 0.15, 0.38), (cx, cy, cz), cmat, (-0.18, ry, 0), bevel=0.05)

    # Mesa de centro redonda negra con patas + florero cerámico blanco y ramas (Render 3)
    add_cyl("Mesa_Centro_Top", 0.46, 0.04, (10.95, 5.05, z1 + 0.38), mats["dark_metal"], verts=28)
    for a in (0, 2.09, 4.18):
        add_cyl(f"Mesa_Pata_{a:.1f}", 0.015, 0.36, (10.95 + 0.30 * math.cos(a), 5.05 + 0.30 * math.sin(a), z1 + 0.19), mats["dark_metal"], verts=8)
    add_cyl("Florero_Sala", 0.095, 0.22, (11.12, 5.08, z1 + 0.51), mats["white_linen"], verts=18)
    for idx, (rx, ry) in enumerate([(0.32, 0.2), (-0.28, 0.35), (0.15, -0.32)]):
        add_cyl(f"Rama_Florero_{idx}", 0.008, 0.42, (11.12, 5.08, z1 + 0.76), mats["dark_wood"], (rx, ry, 0), verts=6)

    # Mesa auxiliar de mármol + Lámpara de hongo negra (Render 3!)
    add_box("Mesa_Aux_Top", (0.46, 0.46, 0.03), (8.65, 6.45, z1 + 0.48), mats["marble"])
    add_cyl("Lamp_Hongo_Pie", 0.075, 0.26, (8.65, 6.45, z1 + 0.62), mats["dark_metal"], verts=16)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.19, location=(8.65, 6.45, z1 + 0.78))
    shade = bpy.context.active_object
    shade.name = "Lamp_Hongo_Pantalla"
    shade.scale = (1.0, 1.0, 0.55)
    bpy.ops.object.shade_smooth()
    shade.data.materials.append(mats["dark_metal"])

    # COMEDOR junto al ventanal panorámico: Mesa de vidrio oscuro/madera con patas + 6 sillas detalladas + luminaria lineal
    add_box("Comedor_Cubierta", (1.12, 2.45, 0.055), (13.25, 5.15, z1 + 0.76), mats["dark_wood"], bevel=0.012)
    add_box("Comedor_Vidrio", (1.08, 2.40, 0.015), (13.25, 5.15, z1 + 0.795), mats["black_glass"])
    for lx in (-0.42, 0.42):
        for ly in (-0.92, 0.92):
            add_cyl(f"Comedor_Pata_{lx}_{ly}", 0.032, 0.75, (13.25 + lx, 5.15 + ly, z1 + 0.375), mats["wood"], (0.08 if ly > 0 else -0.08, -0.08 if lx > 0 else 0.08, 0), 10)
    for idx, cy in enumerate([4.30, 5.15, 6.00]):
        add_dining_chair(f"Silla_Com_L_{idx}", (12.48, cy, z1), -math.pi / 2, mats["cream_fabric"], mats["wood"])
        add_dining_chair(f"Silla_Com_R_{idx}", (14.02, cy, z1), math.pi / 2, mats["cream_fabric"], mats["wood"])
    # Luminaria colgante lineal sobre comedor
    add_box("Lamp_Comedor_Barra", (0.06, 1.65, 0.05), (13.25, 5.15, z1 + 2.25), mats["dark_metal"])
    add_box("Lamp_Comedor_LED", (0.04, 1.58, 0.02), (13.25, 5.15, z1 + 2.22), mats["led"])

    # CUADROS ENMARCADOS EN PAREDES DE SALA Y PASILLO
    add_framed_artwork("Cuadro_Sala_Sur", (10.55, 0.35, z1 + 1.65), 2.1, 1.15, "Y", mats["dark_metal"], mats["art_living"])
    add_framed_artwork("Cuadro_Sala_Oeste", (6.36, 4.4, z1 + 1.65), 1.45, 1.05, "X", mats["dark_metal"], mats["art_hall"])

    # =========================================================================
    # 6. AZOTEA Y PÉRGOLA DE COCHERA
    # =========================================================================
    add_box("Losa_Azotea", (9.45, 11.65, 0.24), (10.12, 5.85, 6.62), mats["stucco"])
    add_box("Pretil_Sur", (9.45, 0.22, 0.34), (10.12, 0.14, 6.86), mats["stucco"])
    add_box("Pretil_Norte", (9.45, 0.22, 0.34), (10.12, 11.56, 6.86), mats["stucco"])
    add_box("Pretil_Este", (0.22, 11.65, 0.34), (14.74, 5.85, 6.86), mats["stucco"])
    add_box("Pretil_Oeste", (0.22, 11.65, 0.34), (5.5, 5.85, 6.86), mats["stucco"])
    for i in range(15):
        add_box(f"Pergola_{i}", (5.6, 0.10, 0.14), (3.0, 10.6 + i * 0.5, 6.54), mats["wood"])

    # =========================================================================
    # 7. ILUMINACIÓN ARQUITECTÓNICA CÁLIDA CALIBRADA
    # =========================================================================
    add_area_light("Luz_Sala", (10.6, 5.6, 6.22), (0, 0, 0), 280, 2.8, 2.4, (1.0, 0.90, 0.76))
    add_area_light("Luz_Comedor", (13.2, 5.15, 6.10), (0, 0, 0), 180, 0.6, 1.8, (1.0, 0.88, 0.72))
    add_area_light("Luz_Cocina", (10.35, 10.1, 6.22), (0, 0, 0), 220, 3.6, 1.2, (1.0, 0.88, 0.70))
    add_area_light("Luz_RecPrincipal", (6.75, 8.2, 2.88), (0, 0, 0), 190, 2.8, 2.8, (1.0, 0.87, 0.70))
    add_area_light("Luz_Rec2", (2.3, 8.4, 2.88), (0, 0, 0), 150, 2.2, 2.2, (1.0, 0.87, 0.70))
    add_area_light("Luz_Patio_Suave", (10.8, 16.5, 3.2), (0, 0, 0), 120, 3.2, 3.2, (1.0, 0.88, 0.72))


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

    # 5 paradas optimizadas para encuadres arquitectónicos protagonistas
    stops = [
        ("01_fachada_esquina.jpg", (20.8, -5.2, 2.35)),
        ("02_patio_jardin.jpg", (9.6, 13.8, 1.62)),
        ("03_sala_cocina.jpg", (10.9, 3.6, 4.92)),
        ("04_recamara.jpg", (5.8, 9.8, 1.58)),
        ("05_fachada_celosia.jpg", (-9.8, 12.2, 2.95)),
    ]

    for fname, loc in stops:
        cam_obj.location = loc
        cam_obj.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
        out_path = os.path.join(OUT_DIR, fname)
        bpy.context.scene.render.filepath = out_path
        print(f"[Render 360] Generando {fname} en {loc} ...")
        bpy.ops.render.render(write_still=True)


def main():
    clear_scene()
    configure_cycles(samples=72, res_x=2048, res_y=1024)
    setup_world_sky()
    build_house_scene()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"[Blender] Proyecto guardado en: {BLEND_PATH}")
    render_panoramas()
    print("[Blender] Todos los panoramas 360° de alto detalle generados.")


if __name__ == "__main__":
    main()
