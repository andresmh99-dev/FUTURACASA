"""
Generador arquitectónico en Blender 5 (Cycles) — Casa Lote 8, Manzana 147, Fracc. México
Construye la escena completa desde la lámina A-1 y los 5 renders de referencia,
guarda el archivo editable `blender/casa_l8_mexico.blend` y renderiza
5 panoramas 360° equirectangulares fotorealistas en `assets/panoramas/`.

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


def configure_cycles(samples=48, res_x=2048, res_y=1024):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.03
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6

    # Intentar GPU si existe, de lo contrario CPU
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
    scene.render.image_settings.quality = 90

    # Color management AgX / Filmic
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        try:
            scene.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    scene.view_settings.exposure = -0.35


def setup_world_sky():
    world = bpy.data.worlds.new("Sky_Morelia")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.65

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.2)
    sky.sun_intensity = 0.85
    sky.sun_elevation = math.radians(28)
    sky.sun_rotation = math.radians(145)
    sky.altitude = 1920.0  # Morelia, Mich. (~1,920 m s. n. m.)
    if hasattr(sky, "air_density"):
        sky.air_density = 1.15
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 1.25

    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_pbr_mat(name, color, roughness=0.7, metallic=0.0, bump_scale=0.0, bump_strength=0.0,
                 emission=None, emission_strength=0.0, transmission=0.0, ior=1.45):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if transmission > 0 and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None and emission_strength > 0:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission_strength

    if bump_scale > 0 and bump_strength > 0:
        tex_coord = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 8.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        nt.links.new(tex_coord.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def make_marble_mat(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.22

    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.inputs["Scale"].default_value = 1.8
    wave.inputs["Distortion"].default_value = 9.5
    wave.inputs["Detail"].default_value = 6.0

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (0.52, 0.50, 0.48, 1.0)
    ramp.color_ramp.elements[1].position = 0.55
    ramp.color_ramp.elements[1].color = (0.95, 0.94, 0.92, 1.0)

    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def add_box(name, size, loc, mat, rot=(0, 0, 0)):
    """Blender usa Z arriba: size=(sx, sy, sz), loc=(x, y, z) centro."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.data.materials.append(mat)
    return obj


def add_cyl(name, radius, depth, loc, mat, rot=(0, 0, 0), verts=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def add_boulder(name, radius, loc, mat, scale=(1.2, 1.0, 0.72), seed=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    rng = random.Random(seed)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for v in bm.verts:
        n = 1.0 + 0.18 * math.sin(v.co.x * 4.5 + seed) + 0.14 * math.cos(v.co.y * 5.0 - v.co.z * 3.0)
        v.co.x *= n * scale[0]
        v.co.y *= n * scale[1]
        v.co.z *= n * scale[2]
    bm.to_mesh(obj.data)
    bm.free()
    bpy.ops.object.shade_smooth()
    obj.data.materials.append(mat)
    return obj


def add_tree(name, loc, scale, bark_mat, leaf_mat, blossom_mat, seed=10):
    rng = random.Random(seed)
    x0, y0, z0 = loc
    # Tronco y ramas principales
    add_cyl(f"{name}_trunk", 0.11 * scale, 2.5 * scale, (x0, y0, z0 + 1.25 * scale), bark_mat, (0.04, -0.04, 0), 10)
    branches = [
        (0.32, 0.15, 2.9, 0.25, 0.3, 0.0, 2.0),
        (-0.35, -0.18, 2.8, -0.22, -0.32, 0.0, 1.9),
        (0.05, 0.28, 3.2, -0.25, 0.08, 0.0, 2.2),
    ]
    for idx, (dx, dy, dz, rx, ry, rz, ln) in enumerate(branches):
        add_cyl(f"{name}_br{idx}", 0.05 * scale, ln * scale, (x0 + dx * scale, y0 + dy * scale, z0 + dz * scale),
                bark_mat, (rx, ry, rz), 8)

    # Copa orgánica con decenas de pequeños racimos de hojas (sombras moteadas reales en Cycles)
    mesh = bpy.data.meshes.new(f"{name}_canopy_mesh")
    bm = bmesh.new()
    for _ in range(135):
        layer = rng.random()
        rz = (2.6 + layer * 3.5) * scale
        max_r = max(0.45, (1.85 - abs(layer - 0.45) * 1.4) * scale)
        rad = math.sqrt(rng.random()) * max_r
        ang = rng.random() * math.tau
        px = rad * math.cos(ang)
        py = rad * math.sin(ang)
        r = (0.18 + rng.random() * 0.22) * scale
        ret = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        for v in ret["verts"]:
            v.co += Vector((px, py, rz))
    bm.to_mesh(mesh)
    bm.free()
    canopy = bpy.data.objects.new(f"{name}_canopy", mesh)
    canopy.location = (x0, y0, z0)
    canopy.data.materials.append(leaf_mat)
    bpy.context.collection.objects.link(canopy)

    # Flores blancas sutiles
    fmesh = bpy.data.meshes.new(f"{name}_blossoms_mesh")
    fbm = bmesh.new()
    for _ in range(42):
        layer = rng.random()
        rz = (2.9 + layer * 3.1) * scale
        rad = (0.5 + rng.random() * 1.25) * scale
        ang = rng.random() * math.tau
        ret = bmesh.ops.create_icosphere(fbm, subdivisions=1, radius=0.07 * scale)
        for v in ret["verts"]:
            v.co += Vector((rad * math.cos(ang), rad * math.sin(ang), rz))
    fbm.to_mesh(fmesh)
    fbm.free()
    blossoms = bpy.data.objects.new(f"{name}_blossoms", fmesh)
    blossoms.location = (x0, y0, z0)
    blossoms.data.materials.append(blossom_mat)
    bpy.context.collection.objects.link(blossoms)


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
    bpy.context.collection.objects.link(lobj)
    return lobj


def build_house_scene():
    # Materiales PBR (Blender Z-up: X Oeste->Este 0..15, Y Norte->Sur 0..20, Z Altura 0..7)
    mats = {
        "stucco": make_pbr_mat("Estuco_Blanco", (0.86, 0.85, 0.82), roughness=0.82, bump_scale=35.0, bump_strength=0.04),
        "warm_wall": make_pbr_mat("Muro_Interior", (0.76, 0.72, 0.67), roughness=0.82),
        "floor_polished": make_pbr_mat("Piso_Pulido", (0.68, 0.64, 0.58), roughness=0.18, bump_scale=12.0, bump_strength=0.015),
        "grass": make_pbr_mat("Pasto_Lomas", (0.14, 0.18, 0.08), roughness=0.95, bump_scale=24.0, bump_strength=0.22),
        "road": make_pbr_mat("Grava_Vial", (0.45, 0.43, 0.39), roughness=0.78, bump_scale=65.0, bump_strength=0.12),
        "gravel": make_pbr_mat("Grava_Patio", (0.38, 0.36, 0.33), roughness=0.92, bump_scale=80.0, bump_strength=0.18),
        "slate": make_pbr_mat("Deck_Pizarra", (0.12, 0.13, 0.14), roughness=0.72, bump_scale=20.0, bump_strength=0.05),
        "paver": make_pbr_mat("Andador_Concreto", (0.32, 0.32, 0.31), roughness=0.84, bump_scale=30.0, bump_strength=0.06),
        "wood": make_pbr_mat("Madera_Celosia", (0.32, 0.21, 0.13), roughness=0.62, bump_scale=18.0, bump_strength=0.05),
        "beige_cab": make_pbr_mat("Cocina_Beige", (0.66, 0.55, 0.44), roughness=0.52),
        "dark_island": make_pbr_mat("Isla_Grafito", (0.11, 0.12, 0.14), roughness=0.55),
        "marble": make_marble_mat("Marmol_Calacatta"),
        "cream_fabric": make_pbr_mat("Tela_Crema", (0.78, 0.74, 0.68), roughness=0.92, bump_scale=50.0, bump_strength=0.04),
        "olive": make_pbr_mat("Cojin_Olivo", (0.22, 0.24, 0.15), roughness=0.9),
        "dark_metal": make_pbr_mat("Canceleria_Negra", (0.05, 0.055, 0.06), roughness=0.32, metallic=0.75),
        "alum": make_pbr_mat("Aluminio", (0.48, 0.50, 0.52), roughness=0.25, metallic=0.85),
        "glass": make_pbr_mat("Vidrio_Arq", (0.88, 0.94, 0.98), roughness=0.03, transmission=0.92, ior=1.5),
        "rock": make_pbr_mat("Roca_Volcanica", (0.18, 0.19, 0.20), roughness=0.92, bump_scale=16.0, bump_strength=0.3),
        "bark": make_pbr_mat("Corteza", (0.16, 0.12, 0.09), roughness=0.92),
        "leaf": make_pbr_mat("Follaje", (0.11, 0.20, 0.07), roughness=0.72),
        "blossom": make_pbr_mat("Flor_Blanca", (0.94, 0.93, 0.90), roughness=0.65),
        "led": make_pbr_mat("LED_Calido", (1.0, 0.92, 0.76), roughness=0.3, emission=(1.0, 0.78, 0.45), emission_strength=9.0),
    }

    # Nota de ejes en Blender (Z arriba):
    # X: 0..15 m (Oeste -> Este)
    # Y: 0..20 m (Sur frente Calle Zacamixtle = 0 -> Norte Patio = 20)
    # Z: 0.0 = Sótano/Jardín, 3.3 = Primera Planta, 6.6 = Azotea

    # 1. TERRENO SUAVE EN PENDIENTE + VIALIDAD
    mesh = bpy.data.meshes.new("Terreno_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=64, y_segments=64, size=65.0)
    for v in bm.verts:
        wx = v.co.x + 7.5
        wy = v.co.y + 10.0
        dx = max(0.0, -wx, wx - 15.0)
        dy = max(0.0, -wy, wy - 20.0)
        dist = math.hypot(dx, dy)
        t = min(1.0, max(0.0, (dist - 0.5) / 10.0))
        blend = t * t * (3 - 2 * t)
        slope = (5.0 - wx) * 0.065 + (wy - 10.0) * 0.055
        hill = math.sin(wx * 0.045) * 0.55 + math.cos(wy * 0.045) * 0.45
        target_z = max(-5.5, min(4.2, slope + hill - 0.15))
        v.co.x = wx
        v.co.y = wy
        v.co.z = -0.15 * (1.0 - blend) + target_z * blend
    bm.to_mesh(mesh)
    bm.free()
    terrain = bpy.data.objects.new("Terreno_Lomas", mesh)
    terrain.data.materials.append(mats["grass"])
    bpy.context.collection.objects.link(terrain)
    bpy.context.view_layer.objects.active = terrain
    bpy.ops.object.shade_smooth()

    # Vialidad frontal y lateral en pendiente
    add_box("Calle_Sur", (44.0, 6.8, 0.2), (10.0, -4.2, -0.18), mats["road"], (0.0, -0.05, 0.0))
    add_box("Calle_Oeste", (6.2, 34.0, 0.2), (-3.8, 10.5, 0.95), mats["road"], (0.095, 0.0, 0.0))

    # 2. SÓTANO / PLANTA BAJA (Z = 0..3.05 m) — Recámaras + Patio Jardín
    add_box("Losa_Sotano", (15.0, 20.0, 0.25), (7.5, 10.0, -0.125), mats["floor_polished"])
    add_box("Cimentacion", (15.04, 20.04, 1.8), (7.5, 10.0, -1.0), mats["stucco"])

    # Bardas perimetrales blancas + aletas altas de fachada
    add_box("Barda_Sur", (15.0, 0.28, 3.0), (7.5, 0.14, 1.5), mats["stucco"])
    add_box("Barda_Norte", (15.0, 0.28, 3.05), (7.5, 19.86, 1.525), mats["stucco"])
    add_box("Barda_Este", (0.28, 20.0, 3.05), (14.86, 10.0, 1.525), mats["stucco"])
    add_box("Muro_Oeste_Base", (0.28, 20.0, 3.25), (0.14, 10.0, 1.625), mats["stucco"])
    add_box("Aleta_Este_Patio", (0.28, 5.2, 6.2), (14.86, 17.4, 3.1), mats["stucco"])
    add_box("Aleta_Oeste_Sur", (0.28, 4.4, 6.45), (0.14, 2.2, 3.225), mats["stucco"])

    # Recámaras Sótano (Y = 0.28..11.5) + Cancelería negra piso-techo hacia el Patio (Y = 11.55)
    add_box("Muro_Div_Rec", (0.22, 11.2, 3.0), (4.4, 5.9, 1.5), mats["warm_wall"])
    add_box("Muro_Pasillo", (8.2, 0.22, 3.0), (4.3, 5.8, 1.5), mats["warm_wall"])
    add_box("Muro_RecPrincipal", (0.22, 6.2, 3.0), (8.4, 3.4, 1.5), mats["warm_wall"])

    # Cancelería negra hacia el patio jardín (Y = 11.55)
    add_box("Vidrio_Recamaras", (7.8, 0.03, 2.86), (4.3, 11.55, 1.45), mats["glass"])
    for mx in (0.4, 2.35, 4.3, 6.25, 8.2):
        add_box(f"Marco_Rec_{mx}", (0.08, 0.09, 2.9), (mx, 11.55, 1.45), mats["dark_metal"])
    add_box("Cabezal_Rec", (7.9, 0.1, 0.08), (4.3, 11.55, 2.92), mats["dark_metal"])

    # Camas en recámaras
    for idx, (bx, by) in enumerate([(2.3, 8.6), (6.4, 8.6)]):
        add_box(f"Cama_Base_{idx}", (1.9, 2.05, 0.28), (bx, by, 0.14), mats["wood"])
        add_box(f"Cama_Colchon_{idx}", (1.82, 1.98, 0.24), (bx, by, 0.38), mats["cream_fabric"])
        add_box(f"Cama_Cabecera_{idx}", (1.95, 0.12, 1.08), (bx, by - 1.0, 0.54), mats["beige_cab"])

    # PATIO JARDÍN PRIVADO (Y = 11.7..19.7 — Render 4)
    add_box("Grava_Patio", (14.3, 7.9, 0.06), (7.55, 15.7, 0.03), mats["gravel"])
    add_box("Terraza_Patio", (5.3, 3.7, 0.22), (11.75, 17.5, 0.14), mats["slate"])
    add_box("LED_Terraza", (4.9, 0.06, 0.04), (11.75, 15.62, 0.04), mats["led"])

    for cx in (10.65, 12.85):
        add_cyl(f"Sillon_Patio_{cx}", 0.45, 0.45, (cx, 18.15, 0.48), mats["cream_fabric"])
    add_cyl("Mesa_Patio", 0.48, 0.34, (11.75, 17.4, 0.42), mats["paver"])

    for px, py, pw, pd in [
        (11.75, 14.9, 2.6, 1.05),
        (10.25, 13.35, 1.12, 1.3),
        (11.75, 13.35, 1.42, 1.3),
        (13.3, 13.35, 1.12, 1.3),
    ]:
        add_box(f"Paver_{px}_{py}", (pw, pd, 0.1), (px, py, 0.08), mats["paver"])

    add_tree("Arbol_Principal", (12.2, 14.4, 0.04), 1.2, mats["bark"], mats["leaf"], mats["blossom"], seed=11)
    add_tree("Arbol_Secundario", (13.3, 17.1, 0.04), 0.96, mats["bark"], mats["leaf"], mats["blossom"], seed=23)

    add_boulder("Roca_1", 0.62, (10.1, 15.6, 0.34), mats["rock"], (1.3, 1.0, 0.68), seed=3)
    add_boulder("Roca_2", 0.76, (13.65, 15.9, 0.56), mats["rock"], (1.1, 0.95, 0.92), seed=7)
    add_boulder("Roca_3", 0.45, (9.4, 13.1, 0.28), mats["rock"], (1.25, 1.0, 0.65), seed=19)

    # Arbotantes cálidos en bardas del patio
    for lx, ly in [(14.66, 17.4), (14.66, 14.0), (11.5, 19.66), (7.2, 19.66)]:
        add_box(f"Arbotante_{lx}_{ly}", (0.16, 0.16, 0.16), (lx, ly, 2.2), mats["dark_metal"])
        add_box(f"Arbotante_Luz_{lx}_{ly}", (0.12, 0.12, 0.24), (lx, ly, 2.2), mats["led"])

    # 3. PRIMERA PLANTA (Z = 3.25..6.45 m) — Voladizo Social + Cochera con Celosía
    # Franja horizontal iluminada bajo voladizo
    add_box("Franja_LED_Sur", (9.1, 0.1, 0.28), (10.05, 0.65, 3.13), mats["led"])
    add_box("Franja_LED_Este", (0.1, 9.6, 0.28), (14.35, 5.6, 3.13), mats["led"])

    # Losa Primera Planta
    add_box("Losa_1P", (14.5, 11.5, 0.26), (7.5, 6.0, 3.32), mats["floor_polished"])

    # Fachada Oeste + Celosía vertical de madera (Render 5)
    add_box("Muro_Oeste_1P", (0.28, 10.2, 3.35), (0.14, 5.3, 4.95), mats["stucco"])
    add_box("Dintel_Celosia", (0.28, 8.6, 0.36), (0.14, 14.35, 6.45), mats["stucco"])
    add_box("Jamba_Celosia", (0.28, 0.38, 3.35), (0.14, 18.48, 4.95), mats["stucco"])
    for i in range(38):
        add_box(f"Celosia_{i}", (0.11, 0.055, 3.08), (0.18, 10.4 + i * 0.205, 4.78), mats["wood"])

    # Volumen social en voladizo (Sur ciego + marco profundo Este + muro fondo cocina)
    add_box("Voladizo_Sur", (9.45, 0.34, 3.22), (10.12, 0.14, 5.02), mats["stucco"])
    add_box("Marco_Inf_Este", (0.55, 11.6, 0.28), (14.62, 5.85, 3.44), mats["stucco"])
    add_box("Marco_Sup_Este", (0.55, 11.6, 0.32), (14.62, 5.85, 6.48), mats["stucco"])
    add_box("Muro_Cocina", (5.8, 0.26, 3.18), (9.0, 11.58, 5.0), mats["stucco"])
    add_box("Muro_Cochera_Div", (0.24, 10.9, 3.05), (6.2, 5.8, 4.95), mats["stucco"])

    # Ventanal panorámico rehundido (Este y Norte)
    add_box("Ventanal_Este", (0.03, 10.8, 2.95), (14.48, 6.0, 4.96), mats["glass"])
    for my in (0.65, 3.3, 5.95, 8.6, 11.25):
        add_box(f"Parteluz_{my}", (0.08, 0.06, 2.96), (14.48, my, 4.96), mats["alum"])
    add_box("Travesano_Este", (0.08, 10.7, 0.055), (14.48, 6.0, 4.18), mats["alum"])

    # Mobiliario 1ª Planta (Cocina, Sala y Comedor — Render 3)
    z1 = 3.45
    add_box("Gabinetes_Cocina", (3.85, 0.44, 1.18), (10.45, 11.16, z1 + 2.22), mats["beige_cab"])
    add_box("Backsplash_Marmol", (3.85, 0.06, 0.84), (10.45, 11.36, z1 + 1.26), mats["marble"])
    add_box("LED_Cocina", (3.65, 0.06, 0.05), (10.45, 11.24, z1 + 1.62), mats["led"])
    add_box("Base_Cocina", (3.85, 0.64, 0.88), (10.45, 11.05, z1 + 0.44), mats["dark_island"])
    add_box("Refrigerador", (0.92, 0.72, 2.1), (8.0, 11.02, z1 + 1.05), mats["alum"])

    add_box("Isla_Base", (3.45, 1.04, 0.9), (10.45, 9.05, z1 + 0.45), mats["dark_island"])
    add_box("Isla_Marmol", (3.56, 1.14, 0.07), (10.45, 9.05, z1 + 0.93), mats["marble"])

    add_box("Sofa_Base", (3.2, 1.02, 0.46), (10.55, 6.45, z1 + 0.23), mats["cream_fabric"])
    add_box("Sofa_Respaldo", (3.2, 0.24, 0.54), (10.55, 6.85, z1 + 0.67), mats["cream_fabric"])
    add_box("Sofa_Chaise", (1.06, 2.2, 0.46), (9.48, 5.45, z1 + 0.23), mats["cream_fabric"])
    add_box("Cojin_1", (0.42, 0.16, 0.36), (9.8, 6.62, z1 + 0.6), mats["olive"])
    add_box("Cojin_2", (0.42, 0.16, 0.36), (11.4, 6.62, z1 + 0.6), mats["olive"])
    add_cyl("Mesa_Centro", 0.46, 0.05, (11.1, 5.05, z1 + 0.36), mats["dark_metal"])

    add_box("Comedor_Mesa", (1.12, 2.4, 0.06), (13.25, 5.2, z1 + 0.75), mats["wood"])
    for cy in (4.3, 5.2, 6.1):
        for dx in (-0.7, 0.7):
            add_box(f"Silla_{cy}_{dx}", (0.44, 0.44, 0.48), (13.25 + dx, cy, z1 + 0.25), mats["cream_fabric"])

    # 4. AZOTEA Y PÉRGOLA COCHERA
    add_box("Losa_Azotea", (9.45, 11.65, 0.24), (10.12, 5.85, 6.62), mats["stucco"])
    add_box("Pretil_Sur", (9.45, 0.22, 0.34), (10.12, 0.14, 6.86), mats["stucco"])
    add_box("Pretil_Norte", (9.45, 0.22, 0.34), (10.12, 11.56, 6.86), mats["stucco"])
    add_box("Pretil_Este", (0.22, 11.65, 0.34), (14.74, 5.85, 6.86), mats["stucco"])
    add_box("Pretil_Oeste", (0.22, 11.65, 0.34), (5.5, 5.85, 6.86), mats["stucco"])
    for i in range(15):
        add_box(f"Pergola_{i}", (5.6, 0.1, 0.14), (3.0, 10.6 + i * 0.5, 6.54), mats["wood"])

    # 5. LUCES DE ÁREA INTERIORES Y DE PATIO (cálidas)
    add_area_light("Luz_Sala", (11.4, 6.2, 6.15), (0, 0, 0), 320, 3.0, 2.5)
    add_area_light("Luz_Cocina", (10.4, 10.2, 6.15), (0, 0, 0), 260, 3.5, 1.2)
    add_area_light("Luz_Recamaras", (4.5, 8.8, 2.75), (0, 0, 0), 220, 5.0, 2.5)
    add_area_light("Luz_Patio", (11.8, 16.0, 2.8), (0, 0, 0), 180, 3.0, 3.0)


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

    # 5 paradas del recorrido 360° (en coordenadas Blender Z-up)
    stops = [
        ("01_fachada_esquina.jpg", (23.5, -5.5, 2.4)),
        ("02_patio_jardin.jpg", (11.5, 13.6, 1.65)),
        ("03_sala_cocina.jpg", (11.6, 3.8, 4.95)),
        ("04_recamara.jpg", (5.8, 7.6, 1.65)),
        ("05_fachada_celosia.jpg", (-11.5, 11.5, 3.2)),
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
    configure_cycles(samples=64, res_x=2048, res_y=1024)
    setup_world_sky()
    build_house_scene()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"[Blender] Proyecto guardado en: {BLEND_PATH}")
    render_panoramas()
    print("[Blender] Todos los panoramas 360° generados correctamente.")


if __name__ == "__main__":
    main()
