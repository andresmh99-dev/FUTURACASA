"""
Generador ArchViz Fotorealista v2 (1:1) en Blender 5.3 (Cycles + OptiX GPU)
Casa Lote 8, Manzana 147, Fracc. México, Morelia, Mich.

Calibrado iterativamente frente a las 5 fotografías de render del arquitecto:
- Sol dorado Suroeste (228°, elev. 24°) unificado para las 5 vistas (fachada celosía cálida,
  voladizo con sombra diagonal nítida, brillo solar en calle curva, patio con sombras moteadas)
- Vidrio ArchViz cristalino sin bloqueo de sombras + interiores cálidos luminosos
- Pasto 3D fino de loma, bordes de calle y patio (Geometry Nodes)
- Bosque orgánico en lomas lejanas (420 grupos a 68–155 m, cero árboles cercanos toscos)
- Árboles botánicos frondosos continuos (~9,000 hojas finas + flores blancas)
- Rocas volcánicas angulosas fracturadas + lavanda botánica fina + sillones de rattan tejido
- Cocina Calacatta Gold hasta plafón con baño LED calibrado + grifo cuello de ganso
- Sofá entallado arquitectónico + piso microcemento pulido reflectivo + cuadros de galería
"""

import bpy
import bmesh
import math
import os
import sys
import random
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import archviz_assets as av

PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
GLB_PATH = os.path.join(PROJECT_ROOT, "assets", "L8_MEXICO_SKP_3.glb")
OUT_DIR = os.path.join(PROJECT_ROOT, "assets", "panoramas")
BLEND_PATH = os.path.join(SCRIPT_DIR, "casa_l8_mexico.blend")
COMPARE_DIR = os.environ.get("COMPARE_DIR", "")
os.makedirs(OUT_DIR, exist_ok=True)
if COMPARE_DIR:
    os.makedirs(COMPARE_DIR, exist_ok=True)

# Niveles exactos medidos al milímetro del modelo real 1:1
Z_PATIO = -3.093
Z_SOTANO = -2.893
Z_COCHERA = -0.620
Z_SALA = 0.150
Z_TECHO = 3.060


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def configure_cycles(samples=96, res_x=3072, res_y=1536):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.018
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 6
    scene.cycles.transparent_max_bounces = 10

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
    scene.render.image_settings.quality = 94

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            scene.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    scene.view_settings.exposure = -1.75


def add_box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.0):
    """Crea una caja con escala aplicada 1:1 en vértices (evita texturas estiradas en Cycles!)."""
    sx, sy, sz = size
    mesh = bpy.data.meshes.new(f"{name}_m")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=min(bevel, min(sx, sy, sz) * 0.35), segments=2, affect="EDGES", clamp_overlap=True)
    bm.to_mesh(mesh)
    bm.free()
    if bevel > 0 and len(mesh.polygons) > 0:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def add_cyl(name, radius, depth, loc, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    obj.data.materials.append(mat)
    return obj


def add_framed_artwork(name, loc, width, height, axis, frame_mat, art_mat):
    x, y, z = loc
    depth, border = 0.042, 0.028
    # Plano UV limpio para que la pintura de galería se mapee exactamente 0..1 sin distorsión
    cw, ch = width - border * 2, height - border * 2
    mesh = bpy.data.meshes.new(f"{name}_canvas_m")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    if axis == "Y":
        v0 = bm.verts.new((-cw / 2, 0, -ch / 2))
        v1 = bm.verts.new((cw / 2, 0, -ch / 2))
        v2 = bm.verts.new((cw / 2, 0, ch / 2))
        v3 = bm.verts.new((-cw / 2, 0, ch / 2))
    else:
        v0 = bm.verts.new((0, -cw / 2, -ch / 2))
        v1 = bm.verts.new((0, cw / 2, -ch / 2))
        v2 = bm.verts.new((0, cw / 2, ch / 2))
        v3 = bm.verts.new((0, -cw / 2, ch / 2))
    f = bm.faces.new((v0, v1, v2, v3))
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop, uv in zip(f.loops, uvs):
        loop[uv_layer].uv = uv
    bm.to_mesh(mesh)
    bm.free()
    canvas = bpy.data.objects.new(f"{name}_c", mesh)
    canvas.location = (x, y, z)
    canvas.data.materials.append(art_mat)
    bpy.context.collection.objects.link(canvas)

    if axis == "Y":
        add_box(f"{name}_t", (width, depth, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_b", (width, depth, border), (x, y, z - height / 2 + border / 2), frame_mat)
        add_box(f"{name}_l", (border, depth, height), (x - width / 2 + border / 2, y, z), frame_mat)
        add_box(f"{name}_r", (border, depth, height), (x + width / 2 - border / 2, y, z), frame_mat)
    else:
        add_box(f"{name}_t", (depth, width, border), (x, y, z + height / 2 - border / 2), frame_mat)
        add_box(f"{name}_b", (depth, width, border), (x, y, z - height / 2 + border / 2), frame_mat)
        add_box(f"{name}_l", (depth, border, height), (x, y - width / 2 + border / 2, z), frame_mat)
        add_box(f"{name}_r", (depth, border, height), (x, y + width / 2 - border / 2, z), frame_mat)


def add_luxury_bed(name, loc, mats, blanket_mat, rot_z=0.0, width=1.80):
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)
    parts = []
    n_pan = 8 if width > 1.75 else 6
    pan_w = (width + 0.12) / n_pan
    start_x = -(width + 0.12) / 2 + pan_w / 2
    for i in range(n_pan):
        parts.append(add_box(f"{name}_hb{i}", (pan_w - 0.012, 0.09, 1.32), (start_x + i * pan_w, -1.02, 0.68), mats["cream_fabric"], bevel=0.018))
    parts.append(add_box(f"{name}_base", (width, 2.02, 0.24), (0, 0, 0.14), mats["dark_wood"], bevel=0.015))
    parts.append(av.add_tailored_cushion(f"{name}_matt", (width - 0.05, 1.94, 0.24), (0, 0, 0.38), mats["white_linen"], crown=0.04, bevel_w=0.035, subdiv=2))
    parts.append(av.add_tailored_cushion(f"{name}_blnk", (width + 0.02, 1.22, 0.10), (0, 0.38, 0.50), blanket_mat, crown=0.06, bevel_w=0.03, subdiv=2))
    for px in (-width * 0.24, width * 0.24):
        parts.append(av.add_tailored_cushion(f"{name}_pA_{px:.2f}", (0.64, 0.32, 0.17), (px, -0.70, 0.56), mats["white_linen"], (0.18, 0, 0), crown=0.14, corner_pinch=0.25, bevel_w=0.035, subdiv=2))
        parts.append(av.add_tailored_cushion(f"{name}_pB_{px:.2f}", (0.44, 0.20, 0.17), (px, -0.44, 0.58), mats["taupe"], (0.24, 0, 0), crown=0.16, corner_pinch=0.30, bevel_w=0.03, subdiv=2))
    for side in (-1, 1):
        bx = side * (width / 2 + 0.34)
        parts.append(add_box(f"{name}_buro_{side}", (0.48, 0.38, 0.24), (bx, -0.78, 0.34), mats["wood"], bevel=0.012))
        parts.append(add_cyl(f"{name}_lb_{side}", 0.06, 0.20, (bx, -0.78, 0.56), mats["dark_metal"]))
        parts.append(add_cyl(f"{name}_ls_{side}", 0.12, 0.15, (bx, -0.78, 0.72), mats["led"]))
    for p in parts:
        p.parent = g
    return g


def add_recessed_spot(name, loc, mats):
    add_cyl(f"{name}_trim", 0.062, 0.014, loc, mats["dark_metal"], verts=16)
    add_cyl(f"{name}_glow", 0.042, 0.018, (loc[0], loc[1], loc[2] - 0.004), mats["led"], verts=14)


def add_area_light(name, loc, rot, energy, size_x, size_y, color=(1.0, 0.88, 0.72), spread_deg=None):
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.energy = energy
    ldata.color = color
    ldata.shape = "RECTANGLE"
    ldata.size = size_x
    ldata.size_y = size_y
    if spread_deg is not None and hasattr(ldata, "spread"):
        ldata.spread = math.radians(spread_deg)
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = loc
    lobj.rotation_euler = rot
    if hasattr(lobj, "visible_glossy"):
        lobj.visible_glossy = False
    if hasattr(lobj, "visible_transmission"):
        lobj.visible_transmission = False
    bpy.context.collection.objects.link(lobj)
    return lobj


def add_point_light(name, loc, energy, radius=0.12, color=(1.0, 0.80, 0.52)):
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
# Importación 1:1 del modelo arquitectónico real
# ---------------------------------------------------------------------------
def import_exact_architecture(mats):
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    for obj in list(bpy.data.objects):
        if obj.type == "MESH":
            mat_name = obj.active_material.name if obj.active_material else ""
            if "edges" in obj.name or "Geolocation" in mat_name:
                bpy.data.objects.remove(obj, do_unlink=True)

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

    for obj in arch_meshes:
        obj.data.materials.clear()
        obj.data.materials.append(mats["stucco"])          # 0
        obj.data.materials.append(mats["floor_polished"])  # 1
        obj.data.materials.append(mats["dark_island"])     # 2
        obj.data.materials.append(mats["marble"])          # 3
        obj.data.materials.append(mats["paver"])           # 4

        mw = obj.matrix_world
        rot3 = mw.to_3x3()
        for poly in obj.data.polygons:
            n = (rot3 @ poly.normal).normalized()
            c = mw @ poly.center
            if obj.name == "mesh-1" and 4.05 < c.x < 7.15 and 4.82 < c.y < 6.12 and 0.16 < c.z < 1.10:
                poly.material_index = 3 if (abs(n.z) > 0.85 and c.z > 0.98) else 2
            elif abs(n.z) > 0.85 and abs(c.z - Z_COCHERA) < 0.08 and c.y > 13.5:
                poly.material_index = 4
            elif abs(n.z) > 0.85 and (abs(c.z - Z_SALA) < 0.08 or abs(c.z - Z_SOTANO) < 0.08) and c.x < 9.2:
                poly.material_index = 1
            else:
                poly.material_index = 0
    return root


def terrain_height(wx, wy):
    dx = max(0.0, -wx, wx - 15.1)
    dy = max(0.0, -wy, wy - 20.6)
    dist = math.hypot(dx, dy)
    t = min(1.0, max(0.0, (dist - 0.4) / 10.0))
    blend = t * t * (3.0 - 2.0 * t)
    slope_y = -3.15 + (wy / 20.6) * 2.70
    slope_x = (7.5 - wx) * 0.042
    hill = math.sin(wx * 0.030) * 0.48 + math.cos(wy * 0.030) * 0.38
    base_pad = -3.10 + (max(0.0, min(20.6, wy)) / 20.6) * 2.48
    target_z = max(-7.5, min(3.2, slope_y + slope_x + hill))
    return base_pad * (1.0 - blend) + target_z * blend


def build_photoreal_scene():
    mats = {
        "stucco": av.make_pbr_mat("Estuco_Blanco", (0.89, 0.88, 0.85), roughness=0.84, bump_scale=52.0, bump_strength=0.04,
                                  color2=(0.84, 0.83, 0.80), color_noise_scale=3.5),
        "floor_polished": av.make_pbr_mat("Piso_Microcemento", (0.58, 0.54, 0.48), roughness=0.055, bump_scale=12.0, bump_strength=0.002,
                                          color2=(0.52, 0.48, 0.43), color_noise_scale=2.2, coat_weight=0.68, coat_roughness=0.03),
        "grass_ground": av.make_pbr_mat("Pasto_Base", (0.11, 0.135, 0.055), roughness=0.96, bump_scale=58.0, bump_strength=0.32,
                                        color2=(0.18, 0.20, 0.085), color_noise_scale=2.4),
        "grass_blade": av.make_translucent_leaf_mat("Pasto_3D_Brizna", (0.13, 0.17, 0.06), (0.24, 0.26, 0.105), (0.28, 0.32, 0.11), 0.28),
        "hill_forest": av.make_forest_hill_mat("Lomas_Bosque"),
        "road": av.make_speckled_gravel_mat("Grava_Vial", (0.17, 0.16, 0.15), (0.58, 0.55, 0.50), roughness_min=0.22, roughness_max=0.64, scale=16.0, bump_str=0.62),
        "gravel": av.make_speckled_gravel_mat("Grava_Patio", (0.16, 0.15, 0.14), (0.44, 0.42, 0.38), roughness_min=0.70, roughness_max=0.92, scale=36.0, bump_str=0.58),
        "slate": av.make_pbr_mat("Deck_Pizarra", (0.085, 0.095, 0.105), roughness=0.58, bump_scale=28.0, bump_strength=0.045),
        "paver": av.make_pbr_mat("Andador_Concreto", (0.26, 0.26, 0.25), roughness=0.76, bump_scale=42.0, bump_strength=0.05),
        "wood": av.make_pbr_mat("Madera_Roble", (0.33, 0.21, 0.12), roughness=0.50, bump_scale=28.0, bump_strength=0.05,
                                color2=(0.22, 0.14, 0.08), color_noise_scale=9.0, coat_weight=0.14, coat_roughness=0.30),
        "dark_wood": av.make_pbr_mat("Madera_Nogal", (0.12, 0.08, 0.05), roughness=0.42, bump_scale=24.0, bump_strength=0.04, coat_weight=0.15, coat_roughness=0.25),
        "rattan": av.make_woven_rattan_mat("Rattan_Tejido"),
        "beige_cab": av.make_pbr_mat("Cocina_Beige", (0.61, 0.48, 0.36), roughness=0.44),
        "dark_island": av.make_pbr_mat("Isla_Grafito", (0.075, 0.088, 0.105), roughness=0.46),
        "marble": av.make_calacatta_marble_mat("Marmol_Calacatta"),
        "cream_fabric": av.make_pbr_mat("Tela_Crema", (0.75, 0.71, 0.64), roughness=0.92, bump_scale=85.0, bump_strength=0.045, sheen_weight=0.65, sheen_roughness=0.55),
        "white_linen": av.make_pbr_mat("Sabana_Blanca", (0.89, 0.88, 0.85), roughness=0.88, sheen_weight=0.50),
        "charcoal_fabric": av.make_pbr_mat("Cobija_Grafito", (0.085, 0.095, 0.12), roughness=0.92, sheen_weight=0.55),
        "olive": av.make_pbr_mat("Cojin_Olivo", (0.16, 0.18, 0.09), roughness=0.90, sheen_weight=0.60),
        "taupe": av.make_pbr_mat("Cojin_Taupe", (0.24, 0.22, 0.19), roughness=0.90, sheen_weight=0.60),
        "rug": av.make_pbr_mat("Tapete_Tejido", (0.50, 0.47, 0.42), roughness=0.96, bump_scale=95.0, bump_strength=0.14,
                               color2=(0.43, 0.40, 0.36), color_noise_scale=18.0, sheen_weight=0.45),
        "dark_metal": av.make_pbr_mat("Metal_Negro", (0.025, 0.028, 0.032), roughness=0.25, metallic=0.84),
        "alum": av.make_pbr_mat("Aluminio_Inox", (0.54, 0.56, 0.58), roughness=0.20, metallic=0.90),
        "chrome": av.make_pbr_mat("Cromo", (0.86, 0.87, 0.89), roughness=0.05, metallic=0.98),
        "black_glass": av.make_pbr_mat("Vidrio_Negro", (0.012, 0.015, 0.020), roughness=0.03, metallic=0.12, coat_weight=0.88, coat_roughness=0.02),
        "glass": av.make_archviz_glass_mat("Vidrio_ArchViz", reflection_strength=0.15),
        "sheer": av.make_pbr_mat("Cortina_Transl", (0.87, 0.85, 0.81), roughness=0.90, transmission=0.50, sheen_weight=0.4),
        "rock": av.make_rock_mat("Roca_Volcanica"),
        "bark": av.make_pbr_mat("Corteza", (0.095, 0.075, 0.058), roughness=0.95, bump_scale=46.0, bump_strength=0.42,
                                color2=(0.15, 0.13, 0.105), color_noise_scale=12.0),
        "leaf_dark": av.make_translucent_leaf_mat("Follaje_Oscuro", (0.05, 0.125, 0.032), (0.09, 0.175, 0.048), (0.16, 0.25, 0.06), 0.34),
        "leaf_light": av.make_translucent_leaf_mat("Follaje_Claro", (0.10, 0.195, 0.052), (0.16, 0.25, 0.075), (0.24, 0.33, 0.09), 0.38),
        "pine_forest": av.make_translucent_leaf_mat("Pino_Loma", (0.024, 0.052, 0.028), (0.048, 0.082, 0.040), (0.07, 0.11, 0.05), 0.14),
        "autumn_forest": av.make_translucent_leaf_mat("Otono_Loma", (0.11, 0.085, 0.038), (0.16, 0.105, 0.044), (0.18, 0.12, 0.05), 0.15),
        "blossom": av.make_translucent_leaf_mat("Flor_Blanca", (0.95, 0.94, 0.90), (0.99, 0.98, 0.95), (1.0, 0.98, 0.92), 0.45),
        "lavender": av.make_pbr_mat("Lavanda", (0.23, 0.13, 0.38), roughness=0.86, sheen_weight=0.45),
        "led": av.make_pbr_mat("LED_Calido", (1.0, 0.88, 0.65), roughness=0.3, emission=(1.0, 0.74, 0.34), emission_strength=16.0),
        "led_soft": av.make_pbr_mat("LED_Suave", (1.0, 0.92, 0.76), roughness=0.3, emission=(1.0, 0.80, 0.46), emission_strength=9.0),
        "art_living": av.make_gallery_painting_mat("Cuadro_Sala", "earth_horizon"),
        "art_bed": av.make_gallery_painting_mat("Cuadro_Recamara", "arch_minimal"),
        "art_hall": av.make_gallery_painting_mat("Cuadro_Pasillo", "olive_stone"),
    }

    # 1. IMPORTAR ARQUITECTURA EXACTA 1:1
    import_exact_architecture(mats)

    # 2. VIALIDAD CURVA SUAVE SIN PLIEGUES EN ESQUINA + FALDA LATERAL ENTERRADA
    road_pts = [
        (-4.8, 56.0), (-4.0, 28.0), (-4.0, 16.0), (-4.4, 4.0),
        (-3.6, -2.2), (1.8, -5.0), (16.0, -5.2), (45.0, -6.2), (82.0, -7.8),
    ]
    road_mesh = bpy.data.meshes.new("Vialidad_Curva_Mesh")
    rbm = bmesh.new()
    dense = []
    for seg in range(len(road_pts) - 1):
        p0 = Vector(road_pts[max(0, seg - 1)])
        p1 = Vector(road_pts[seg])
        p2 = Vector(road_pts[seg + 1])
        p3 = Vector(road_pts[min(len(road_pts) - 1, seg + 2)])
        for s in range(28):
            t = s / 28.0
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense.append(Vector(road_pts[-1]))
    road_samples = dense[::2]

    prev_quad = None
    for i, pt in enumerate(dense):
        tan = (dense[min(len(dense) - 1, i + 1)] - dense[max(0, i - 1)]).normalized()
        right = Vector((tan.y, -tan.x))
        pLo = pt - right * 3.45
        pL = pt - right * 3.10
        pR = pt + right * 3.10
        pRo = pt + right * 3.45
        # Falda lateral enterrada -0.18 m para unión invisible sin sombras flotantes!
        vLo = rbm.verts.new((pLo.x, pLo.y, terrain_height(pLo.x, pLo.y) - 0.18))
        vL = rbm.verts.new((pL.x, pL.y, terrain_height(pL.x, pL.y) + 0.08))
        vR = rbm.verts.new((pR.x, pR.y, terrain_height(pR.x, pR.y) + 0.08))
        vRo = rbm.verts.new((pRo.x, pRo.y, terrain_height(pRo.x, pRo.y) - 0.18))
        if prev_quad is not None:
            rbm.faces.new((prev_quad[0], prev_quad[1], vL, vLo))
            rbm.faces.new((prev_quad[1], prev_quad[2], vR, vL))
            rbm.faces.new((prev_quad[2], prev_quad[3], vRo, vR))
        prev_quad = (vLo, vL, vR, vRo)
    rbm.to_mesh(road_mesh)
    rbm.free()
    road_mesh.polygons.foreach_set("use_smooth", [True] * len(road_mesh.polygons))
    road_obj = bpy.data.objects.new("Vialidad_Curva", road_mesh)
    road_obj.data.materials.append(mats["road"])
    bpy.context.collection.objects.link(road_obj)

    # Terreno base rebajado ligeramente debajo de la vialidad para que la calle curva NUNCA se entierre!
    t_mesh = bpy.data.meshes.new("Terreno_Exacto_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=120, y_segments=120, size=140.0)
    for v in bm.verts:
        wx, wy = v.co.x + 7.5, v.co.y + 8.0
        if -0.2 <= wx <= 15.2 and -0.2 <= wy <= 20.7:
            vz = Z_PATIO - 0.25
        else:
            vz = terrain_height(wx, wy)
            if any((wx - rp.x) ** 2 + (wy - rp.y) ** 2 < 3.45 ** 2 for rp in road_samples):
                vz -= 0.14
        v.co = Vector((wx, wy, vz))
    bm.to_mesh(t_mesh)
    bm.free()
    t_mesh.polygons.foreach_set("use_smooth", [True] * len(t_mesh.polygons))
    terrain = bpy.data.objects.new("Terreno_Lomas", t_mesh)
    terrain.data.materials.append(mats["grass_ground"])
    bpy.context.collection.objects.link(terrain)

    # Césped 3D fino cubriendo TODA la ladera visible (radio 58 m) con recorte exacto siguiendo la curva de la calle!
    grass_zone_mesh = bpy.data.meshes.new("Zona_Pasto_3D_Mesh")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=96, y_segments=96, size=116.0)
    to_del = []
    for f in gbm.faces:
        c = f.calc_center_median()
        wx, wy = c.x + 7.5, c.y + 4.0
        # Margen amplio en Este (16.6) para que NUNCA cruce pasto exterior el muro del patio!
        in_lot = (-0.65 <= wx <= 16.65 and -0.65 <= wy <= 21.8)
        on_road = any((wx - rp.x) ** 2 + (wy - rp.y) ** 2 < 3.22 ** 2 for rp in road_samples)
        if in_lot or on_road:
            to_del.append(f)
    bmesh.ops.delete(gbm, geom=to_del, context="FACES")
    for v in gbm.verts:
        wx, wy = v.co.x + 7.5, v.co.y + 4.0
        v.co = Vector((wx, wy, terrain_height(wx, wy) + 0.01))
    gbm.to_mesh(grass_zone_mesh)
    gbm.free()
    grass_zone = bpy.data.objects.new("Zona_Pasto_3D", grass_zone_mesh)
    grass_zone.data.materials.append(mats["grass_ground"])
    bpy.context.collection.objects.link(grass_zone)

    tuft_asset = av.create_grass_tuft_asset(mats["grass_blade"])
    av.apply_grass_geometry_nodes(grass_zone, tuft_asset, density=14.0, scale_min=0.90, scale_max=1.55, seed=17)

    # Borde suave de pasto abrazando la base exterior (sin losas grises visibles ni hojas atravesando muros!)
    curb_mesh = bpy.data.meshes.new("Borde_Pasto_Casa")
    cbm = bmesh.new()
    curb_pts = [(-0.82, 20.0), (-0.82, 10.0), (-0.82, 0.15), (0.15, -0.82), (7.5, -0.82), (15.1, -0.82)]
    for i in range(len(curb_pts) - 1):
        p1, p2 = Vector(curb_pts[i]), Vector(curb_pts[i + 1])
        d = (p2 - p1).normalized()
        n = Vector((-d.y, d.x)) * 0.45
        for s in range(10):
            a = p1.lerp(p2, s / 10.0)
            b = p1.lerp(p2, (s + 1) / 10.0)
            v1 = cbm.verts.new((a.x - n.x, a.y - n.y, terrain_height(a.x - n.x, a.y - n.y) + 0.02))
            v2 = cbm.verts.new((a.x + n.x, a.y + n.y, terrain_height(a.x + n.x, a.y + n.y) + 0.02))
            v3 = cbm.verts.new((b.x + n.x, b.y + n.y, terrain_height(b.x + n.x, b.y + n.y) + 0.02))
            v4 = cbm.verts.new((b.x - n.x, b.y - n.y, terrain_height(b.x - n.x, b.y - n.y) + 0.02))
            cbm.faces.new((v1, v2, v3, v4))
    cbm.to_mesh(curb_mesh)
    cbm.free()
    curb_obj = bpy.data.objects.new("Borde_Pasto_Casa", curb_mesh)
    curb_obj.data.materials.append(mats["grass_ground"])
    bpy.context.collection.objects.link(curb_obj)
    av.apply_grass_geometry_nodes(curb_obj, tuft_asset, density=42.0, scale_min=1.05, scale_max=1.65, seed=31)

    # Cordillera boscosa lejana (125..360 m) con miles de siluetas finas de pinos y encinos (nivel Renders 1, 2, 3 y 5!)
    ridge_mesh = bpy.data.meshes.new("Lomas_Suaves_Mesh")
    hbm = bmesh.new()
    n_ang = 160
    radii = [125.0, 175.0, 235.0, 300.0, 365.0]
    rings = []
    for r_idx, rad in enumerate(radii):
        ring = []
        bell = math.sin((r_idx / (len(radii) - 1)) * math.pi) ** 1.35
        for i in range(n_ang):
            ang = (i / n_ang) * math.tau
            wx, wy = 7.5 + math.cos(ang) * rad, 10.0 + math.sin(ang) * rad
            base_z = terrain_height(7.5 + math.cos(ang) * 115.0, 10.0 + math.sin(ang) * 115.0) - 0.8
            crest = 24.0 + 9.5 * math.sin(ang * 2.0 + 0.2) + 5.8 * math.cos(ang * 3.0 - 0.5) + 2.6 * math.sin(ang * 5.0 + 1.1)
            z = base_z * (1.0 - bell) + crest * bell if r_idx < len(radii) - 1 else -18.0
            ring.append(hbm.verts.new((wx, wy, z)))
        rings.append(ring)
    for r_idx in range(len(rings) - 1):
        for i in range(n_ang):
            ni = (i + 1) % n_ang
            hbm.faces.new((rings[r_idx][i], rings[r_idx][ni], rings[r_idx + 1][ni], rings[r_idx + 1][i]))
    hbm.to_mesh(ridge_mesh)
    hbm.free()
    ridge_mesh.polygons.foreach_set("use_smooth", [True] * len(ridge_mesh.polygons))
    ridge_obj = bpy.data.objects.new("Cordillera_Suave", ridge_mesh)
    ridge_obj.data.materials.append(mats["hill_forest"])
    bpy.context.collection.objects.link(ridge_obj)

    tree_pine = av.create_distant_forest_cluster("Distant_Pine", mats["pine_forest"], seed=201, conifer=True)
    tree_pine2 = av.create_distant_forest_cluster("Distant_Pine2", mats["pine_forest"], seed=204, conifer=True)
    tree_oak = av.create_distant_forest_cluster("Distant_Oak", mats["leaf_dark"], seed=202, conifer=False)
    tree_aut = av.create_distant_forest_cluster("Distant_Autumn", mats["autumn_forest"], seed=203, conifer=False)
    av.scatter_distant_forest_gn(ridge_obj, [tree_pine, tree_pine2, tree_oak, tree_aut], density=0.032, seed=707)

    # =========================================================================
    # 3. PRIMERA PLANTA — EXACTA EN Z_SALA = +0.150 m (Nivel Render 3)
    # =========================================================================
    z1 = Z_SALA
    add_box("Sellado_Plafon_1P", (6.4, 7.6, 0.10), (6.1, 4.1, Z_TECHO + 0.08), mats["stucco"])

    for idx, (sx, sy) in enumerate([
        (4.2, 2.2), (6.0, 2.2), (4.2, 4.2), (6.0, 4.2),
        (4.8, 6.8), (6.4, 6.8), (2.4, 3.0), (2.4, 6.2),
    ]):
        add_recessed_spot(f"Spot_1P_{idx}", (sx, sy, Z_TECHO - 0.01), mats)

    # Franja LED cálida dorada bajo el voladizo exterior (icónica de Renders 1 y 2!)
    add_box("Franja_LED_Sur", (6.0, 0.08, 0.24), (6.2, 0.42, -0.24), mats["led"])
    add_box("Franja_LED_Este", (0.08, 7.2, 0.24), (8.92, 4.0, -0.24), mats["led"])
    add_area_light("Luz_Franja_Sur", (6.2, 0.18, -0.26), (math.radians(90), 0, 0), 115, 5.5, 0.18, (1.0, 0.76, 0.36))

    # Ventanal panorámico Sur (Y = 0.25) con vidrio ArchViz cristalino
    win_h = Z_TECHO - z1
    add_box("Ventanal_Sur_Glass", (6.0, 0.018, win_h), (6.25, 0.25, z1 + win_h / 2), mats["glass"])
    for mx in (3.28, 5.25, 7.25, 9.22):
        add_box(f"Parteluz_S_{mx}", (0.06, 0.08, win_h + 0.02), (mx, 0.25, z1 + win_h / 2), mats["alum"])
    add_box("Travesano_S", (6.0, 0.08, 0.055), (6.25, 0.25, z1 + 0.62), mats["alum"])

    # Pasamanos + puerta pasillo minimalista enmarcada de lado a lado (Render 3 izquierda!)
    add_box("Pasamanos_Esc_Real", (0.09, 4.3, 0.045), (2.22, 2.35, z1 + 0.92), mats["wood"], bevel=0.006)
    add_box("Muro_Cierre_Pasillo", (1.60, 0.12, 2.91), (2.45, 8.95, z1 + 1.455), mats["stucco"])
    add_box("Puerta_Pasillo_Marco", (1.16, 0.09, 2.52), (2.52, 8.88, z1 + 1.26), mats["taupe"])
    add_box("Puerta_Pasillo_1P", (1.04, 0.08, 2.42), (2.52, 8.85, z1 + 1.21), mats["beige_cab"], bevel=0.01)
    add_box("Puerta_Pasillo_Franja", (1.06, 0.09, 0.14), (2.52, 8.84, z1 + 0.94), mats["dark_metal"])
    add_box("Puerta_Nucleo_1P", (1.02, 0.07, 2.30), (7.65, 13.55, z1 + 1.15), mats["beige_cab"], bevel=0.01)
    add_box("Puerta_Nucleo_Franja", (1.04, 0.08, 0.14), (7.65, 13.55, z1 + 0.90), mats["dark_metal"])

    # COCINA DE ALTA GAMA HASTA PLAFÓN (delante del muro real kitY=7.683 — Backsplash Calacatta 100% visible!)
    add_box("Cocina_Fondo_Juntas", (3.85, 0.04, 1.28), (5.38, 7.64, z1 + 2.27), mats["dark_metal"])
    for i in range(7):
        add_box(f"Gab_Top_{i}", (0.525, 0.42, 0.70), (3.80 + i * 0.54, 7.46, z1 + 2.56), mats["beige_cab"], bevel=0.005)
    for i in range(5):
        add_box(f"Gab_Mid_{i}", (0.525, 0.42, 0.525), (4.88 + i * 0.54, 7.46, z1 + 1.935), mats["beige_cab"], bevel=0.005)
    # Nicho abierto luminoso junto al refri (Render 3!)
    add_box("Nicho_Fondo", (0.48, 0.04, 0.53), (4.36, 7.60, z1 + 1.935), mats["beige_cab"])
    add_box("Nicho_Top", (0.50, 0.40, 0.035), (4.36, 7.46, z1 + 2.185), mats["beige_cab"])
    add_box("Nicho_Bot", (0.50, 0.40, 0.035), (4.36, 7.46, z1 + 1.685), mats["beige_cab"])
    add_box("Nicho_LatL", (0.035, 0.40, 0.53), (4.12, 7.46, z1 + 1.935), mats["beige_cab"])
    add_box("Nicho_LatR", (0.035, 0.40, 0.53), (4.60, 7.46, z1 + 1.935), mats["beige_cab"])
    add_cyl("Nicho_Vaso", 0.055, 0.14, (4.36, 7.44, z1 + 1.77), mats["white_linen"], verts=18)

    # Backsplash Calacatta Gold COMPLETAMENTE VISIBLE (Y = 7.62, delante del muro real 7.683!)
    add_box("Backsplash_Marmol", (3.20, 0.04, 0.78), (5.72, 7.62, z1 + 1.29), mats["marble"])
    add_box("LED_Cocina", (2.94, 0.035, 0.025), (5.72, 7.56, z1 + 1.665), mats["led_soft"])
    add_area_light("Luz_Backsplash_LED", (5.72, 7.52, z1 + 1.61), (0, 0, 0), 22, 2.8, 0.10, (1.0, 0.78, 0.42), spread_deg=115)

    add_box("Cocina_Inf", (3.14, 0.60, 0.88), (5.72, 7.34, z1 + 0.44), mats["dark_island"], bevel=0.01)
    add_box("Cocina_Cubierta", (3.18, 0.64, 0.045), (5.72, 7.33, z1 + 0.90), mats["marble"], bevel=0.008)
    add_box("Parrilla_Vidrio", (0.76, 0.48, 0.025), (6.05, 7.33, z1 + 0.935), mats["black_glass"])
    for qx in (5.82, 6.26):
        for qy in (7.20, 7.46):
            add_cyl(f"Quemador_{qx}_{qy}", 0.058, 0.02, (qx, qy, z1 + 0.955), mats["dark_metal"], verts=14)
    add_box("Horno_Frente", (0.64, 0.04, 0.52), (6.05, 7.03, z1 + 0.48), mats["black_glass"])
    add_box("Horno_Manija", (0.50, 0.04, 0.025), (6.05, 6.99, z1 + 0.68), mats["alum"])
    add_box("Refri_Izq", (0.37, 0.64, 2.12), (3.62, 7.34, z1 + 1.06), mats["alum"], bevel=0.012)
    add_box("Refri_Der", (0.37, 0.64, 2.12), (4.01, 7.34, z1 + 1.06), mats["alum"], bevel=0.012)
    add_box("Refri_ManL", (0.018, 0.03, 0.48), (3.76, 7.01, z1 + 1.25), mats["dark_metal"])
    add_box("Refri_ManR", (0.018, 0.03, 0.48), (3.87, 7.01, z1 + 1.25), mats["dark_metal"])

    # Isla real (Z = 1.05 m) con cubierta Calacatta, tarja y grifo curvo cuello de ganso
    add_box("Isla_Cubierta_Vuelo", (2.98, 1.24, 0.045), (5.59, 5.46, 1.072), mats["marble"], bevel=0.008)
    add_box("Tarja_Hundida", (0.64, 0.44, 0.025), (4.88, 5.52, 1.095), mats["dark_metal"])
    av.add_gooseneck_faucet("Grifo_Isla", (4.88, 5.78, 1.09), mats["chrome"])

    # SALA ARQUITECTÓNICA ENTALLADA (Idéntica a Render 3 — cero cojines tipo malvavisco!)
    add_box("Tapete_Sala", (3.6, 3.0, 0.016), (4.85, 3.05, z1 + 0.008), mats["rug"])
    add_box("Sofa_Base", (2.86, 0.96, 0.22), (4.85, 3.75, z1 + 0.14), mats["cream_fabric"], bevel=0.022)
    add_box("Sofa_Brazo_R", (0.20, 0.96, 0.56), (6.20, 3.75, z1 + 0.31), mats["cream_fabric"], bevel=0.022)
    for i in range(3):
        av.add_tailored_cushion(f"Sofa_As_{i}", (0.89, 0.88, 0.19), (3.94 + i * 0.90, 3.70, z1 + 0.33), mats["cream_fabric"], crown=0.05, bevel_w=0.03, subdiv=2)
        av.add_tailored_cushion(f"Sofa_Res_{i}", (0.88, 0.20, 0.46), (3.94 + i * 0.90, 4.06, z1 + 0.62), mats["cream_fabric"], (-0.14, 0, 0), crown=0.08, corner_pinch=0.14, bevel_w=0.032, subdiv=2)
    add_box("Sofa_Chaise_B", (0.98, 2.02, 0.22), (3.92, 2.65, z1 + 0.14), mats["cream_fabric"], bevel=0.022)
    av.add_tailored_cushion("Sofa_Chaise_C", (0.94, 1.94, 0.19), (3.92, 2.65, z1 + 0.33), mats["cream_fabric"], crown=0.04, bevel_w=0.03, subdiv=2)
    # Cojines decorativos cuadrados pellizcados en oliva y taupe oscuro (Render 3!)
    for idx, (cx, cy, ry, cmat) in enumerate([
        (3.80, 3.82, 0.16, mats["taupe"]),
        (4.32, 3.78, -0.14, mats["olive"]),
        (5.12, 3.82, 0.08, mats["taupe"]),
        (5.76, 3.78, -0.16, mats["olive"]),
        (6.02, 3.66, 0.22, mats["taupe"]),
    ]):
        av.add_tailored_cushion(f"Cojin_S_{idx}", (0.40, 0.14, 0.38), (cx, cy, z1 + 0.55), cmat, (-0.18, ry, 0), crown=0.18, corner_pinch=0.40, bevel_w=0.025, subdiv=2)

    # Mesa de centro negra redonda + florero blanco + ramitas orgánicas finas (Render 3!)
    add_cyl("Mesa_Centro", 0.44, 0.028, (5.25, 2.45, z1 + 0.38), mats["dark_metal"], verts=36)
    for a in (0, 2.09, 4.18):
        add_cyl(f"Mesa_P_{a:.1f}", 0.012, 0.36, (5.25 + 0.28 * math.cos(a), 2.45 + 0.28 * math.sin(a), z1 + 0.19), mats["dark_metal"], verts=10)
    add_cyl("Florero_S", 0.085, 0.21, (5.38, 2.48, z1 + 0.495), mats["white_linen"], verts=24)
    av.add_delicate_vase_twigs("Ramas_Florero_S", (5.38, 2.48, z1 + 0.59), mats["dark_wood"], seed=77)

    # Mesa auxiliar mármol + Lámpara hongo negra + Planta interior
    add_box("Mesa_Aux", (0.44, 0.44, 0.028), (3.16, 3.78, z1 + 0.46), mats["marble"], bevel=0.005)
    add_cyl("Lamp_H_Pie", 0.068, 0.24, (3.16, 3.78, z1 + 0.60), mats["dark_metal"], verts=24)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=16, radius=0.175, location=(3.16, 3.78, z1 + 0.76))
    sh = bpy.context.active_object
    sh.scale = (1.0, 1.0, 0.52)
    sh.data.polygons.foreach_set("use_smooth", [True] * len(sh.data.polygons))
    sh.data.materials.append(mats["dark_metal"])
    add_cyl("Planta_Sala_Pot", 0.18, 0.38, (8.35, 0.90, z1 + 0.19), mats["dark_metal"], verts=20)
    av.add_delicate_lavender_bed("Planta_Sala_Fol", (8.35, 0.90, z1 + 0.37), mats["leaf_dark"], mats["leaf_light"], radius=0.14, seed=61)

    # COMEDOR vidrio negro reflectivo + 6 sillas de concha curva (Render 3!)
    add_box("Comedor_Top", (1.05, 2.25, 0.05), (7.45, 2.55, z1 + 0.76), mats["dark_wood"], bevel=0.012)
    add_box("Comedor_Vid", (1.01, 2.20, 0.014), (7.45, 2.55, z1 + 0.793), mats["black_glass"])
    for lx in (-0.38, 0.38):
        for ly in (-0.84, 0.84):
            add_cyl(f"Com_P_{lx}_{ly}", 0.028, 0.75, (7.45 + lx, 2.55 + ly, z1 + 0.375), mats["wood"], (0.08 if ly > 0 else -0.08, -0.08 if lx > 0 else 0.08, 0), 12)
    for idx, cy in enumerate([1.75, 2.55, 3.35]):
        av.add_sculpted_dining_chair(f"Silla_L_{idx}", (6.72, cy, z1), -math.pi / 2, mats["cream_fabric"], mats["wood"])
        av.add_sculpted_dining_chair(f"Silla_R_{idx}", (8.18, cy, z1), math.pi / 2, mats["cream_fabric"], mats["wood"])
    add_box("Lamp_Com_B", (0.055, 1.55, 0.045), (7.45, 2.55, Z_TECHO - 0.58), mats["dark_metal"])
    add_box("Lamp_Com_L", (0.035, 1.48, 0.02), (7.45, 2.55, Z_TECHO - 0.61), mats["led_soft"])

    # Cuadros de galería con UV limpio (arte minimalista de autor)
    add_framed_artwork("Cuadro_Comedor", (8.68, 2.65, z1 + 1.55), 1.55, 0.95, "X", mats["dark_metal"], mats["art_living"])
    add_framed_artwork("Cuadro_Pasillo", (1.42, 7.2, z1 + 1.55), 1.25, 0.88, "X", mats["dark_metal"], mats["art_hall"])

    # Studio PA
    add_box("Escritorio_Studio", (1.65, 0.65, 0.05), (5.2, 13.0, z1 + 0.75), mats["wood"], bevel=0.01)
    av.add_sculpted_dining_chair("Silla_Studio", (5.2, 12.25, z1), 0.0, mats["cream_fabric"], mats["wood"])
    add_framed_artwork("Cuadro_Studio", (5.2, 13.38, z1 + 1.65), 1.35, 0.85, "Y", mats["dark_metal"], mats["art_bed"])

    # =========================================================================
    # 4. COCHERA Y FACHADA DE ENTRADA (Z_COCHERA = -0.62 m — Nivel Render 5!)
    # =========================================================================
    zc = Z_COCHERA
    cel_h = Z_TECHO - zc
    for i in range(32):
        add_box(f"Celosia_Oeste_{i}", (0.11, 0.052, cel_h), (1.98, 13.95 + i * 0.195, zc + cel_h / 2), mats["wood"])
    add_box("Viga_Cabezal_Pergola", (0.16, 6.4, 0.20), (8.65, 17.0, Z_TECHO + 0.06), mats["dark_metal"])
    add_box("Viga_Oeste_Pergola", (0.16, 6.4, 0.20), (2.05, 17.0, Z_TECHO + 0.06), mats["dark_metal"])
    for i in range(14):
        add_box(f"Pergola_Cochera_{i}", (6.7, 0.10, 0.14), (5.35, 14.0 + i * 0.46, Z_TECHO + 0.08), mats["wood"])

    # Árbol verde frondoso asomando por encima de la celosía/cochera (icónico de Renders 2 y 5!)
    av.add_botanical_tree("Arbol_Cochera_N", (4.2, 16.4, zc + 0.02), 1.15, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=53, with_blossoms=False, leaf_density=1.25)

    add_box("Esc_Entrada_1", (2.6, 0.65, 0.18), (7.9, 15.10, zc + 0.09), mats["slate"], bevel=0.012)
    add_box("Esc_Entrada_2", (2.6, 0.65, 0.18), (7.9, 14.55, zc + 0.27), mats["slate"], bevel=0.012)
    add_box("Descanso_Entrada", (2.8, 0.70, 0.48), (7.9, 14.05, zc + 0.24), mats["slate"], bevel=0.012)
    add_box("LED_Esc_Entrada", (2.4, 0.04, 0.03), (7.9, 15.42, zc + 0.03), mats["led"])

    z_ent = zc + 0.48
    add_box("Muro_Entrada_Madera", (2.8, 0.12, 3.16), (7.9, 13.72, z_ent + 1.58), mats["dark_wood"])
    add_box("Marco_Ent_Top", (2.16, 0.16, 0.09), (7.9, 13.82, z_ent + 2.66), mats["dark_metal"])
    add_box("Marco_Ent_L", (0.08, 0.16, 2.68), (6.86, 13.82, z_ent + 1.34), mats["dark_metal"])
    add_box("Marco_Ent_R", (0.08, 0.16, 2.68), (8.94, 13.82, z_ent + 1.34), mats["dark_metal"])
    add_box("Puerta_Principal", (1.34, 0.09, 2.60), (7.58, 13.84, z_ent + 1.31), mats["wood"], bevel=0.015)
    for d in range(5):
        add_box(f"Pta_Duela_{d}", (0.02, 0.02, 2.56), (7.02 + d * 0.28, 13.90, z_ent + 1.31), mats["dark_wood"])
    add_box("Jaladera_Ent", (0.045, 0.09, 1.30), (8.10, 13.92, z_ent + 1.25), mats["dark_metal"])
    add_box("Vidrio_Fijo_Ent", (0.60, 0.02, 2.60), (8.60, 13.84, z_ent + 1.31), mats["glass"])
    add_box("Macetero_Ent", (0.56, 0.56, 0.65), (6.15, 14.30, zc + 0.325), mats["dark_metal"], bevel=0.015)
    av.add_delicate_lavender_bed("Planta_Ent", (6.15, 14.30, zc + 0.66), mats["leaf_dark"], mats["leaf_light"], radius=0.20, seed=88)
    add_box("Marquesina_Ent", (3.2, 1.4, 0.16), (7.9, 14.35, Z_TECHO + 0.02), mats["stucco"])
    add_box("Plafon_Ent_LED", (2.1, 0.50, 0.04), (7.9, 14.35, Z_TECHO - 0.07), mats["led_soft"])
    add_point_light("Luz_Entrada", (7.9, 14.6, Z_TECHO - 0.55), energy=180, radius=0.25)

    for ax in (5.0, 10.5):
        av.add_updown_sconce(f"Arb_Coch_{ax}", (ax, 20.15, zc + 2.2), (0, -1), mats["dark_metal"], mats["led"], energy=220.0)

    # Escalera de madera real (holgada del muro Oeste westX=0.66 para cero salientes exteriores!)
    n_steps = 17
    for i in range(n_steps):
        sz = Z_SOTANO + 0.18 + i * ((Z_SALA - Z_SOTANO) / n_steps)
        sy = 8.9 - i * 0.27
        add_box(f"Escalon_{i}", (1.08, 0.27, 0.075), (1.48, sy, sz), mats["wood"], bevel=0.008)
        if i % 3 == 0:
            add_box(f"Esc_LED_{i}", (1.00, 0.02, 0.02), (1.48, sy + 0.12, sz - 0.04), mats["led_soft"])

    # =========================================================================
    # 5. SÓTANO / PLANTA BAJA — 3 CUARTOS CÁLIDOS VISIBLES DESDE EL PATIO (Render 4!)
    # =========================================================================
    z0 = Z_SOTANO
    add_box("Sellado_Plafon_PB", (5.8, 12.2, 0.06), (6.0, 6.5, -0.44), mats["stucco"])
    for idx, (sx, sy) in enumerate([(6.4, 2.0), (6.4, 3.4), (6.2, 6.9), (6.2, 10.7)]):
        add_recessed_spot(f"Spot_PB_{idx}", (sx, sy, -0.475), mats)

    for idx, (y_start, y_end) in enumerate([(0.65, 4.35), (5.55, 8.25), (9.35, 12.15)]):
        span = y_end - y_start
        cy = (y_start + y_end) / 2.0
        add_box(f"Vidrio_PB_{idx}", (0.016, span, 2.40), (8.65, cy, z0 + 1.21), mats["glass"])
        for t in (0.0, 0.5, 1.0):
            add_box(f"Marco_PB_{idx}_{t:.1f}", (0.09, 0.07, 2.44), (8.65, y_start + span * t, z0 + 1.22), mats["dark_metal"])
        add_box(f"Cab_PB_{idx}", (0.10, span + 0.08, 0.07), (8.65, cy, z0 + 2.44), mats["dark_metal"])
        add_box(f"Cort_PB_A_{idx}", (0.08, 0.34, 2.38), (8.46, y_start + 0.20, z0 + 1.20), mats["sheer"])
        add_box(f"Cort_PB_B_{idx}", (0.08, 0.34, 2.38), (8.46, y_end - 0.20, z0 + 1.20), mats["sheer"])

    # Recámara Principal (bien adentro para que 0 plantas atraviesen muros exteriores!)
    add_box("Tapete_RecP", (2.8, 3.2, 0.018), (6.9, 2.5, z0 + 0.009), mats["rug"])
    add_luxury_bed("Cama_Principal", (6.5, 2.5, z0), mats, mats["charcoal_fabric"], rot_z=-math.pi / 2, width=1.90)
    add_point_light("Luz_BP1", (5.8, 1.35, z0 + 0.90), 45, 0.16, (1.0, 0.78, 0.45))
    add_point_light("Luz_BP2", (5.8, 3.65, z0 + 0.90), 45, 0.16, (1.0, 0.78, 0.45))
    av.add_tailored_cushion("Banqueta_P", (0.44, 1.55, 0.40), (7.85, 2.5, z0 + 0.20), mats["cream_fabric"], crown=0.05, bevel_w=0.03, subdiv=2)
    add_framed_artwork("Cuadro_RecP_N", (6.8, 4.72, z0 + 1.50), 1.45, 0.84, "Y", mats["dark_metal"], mats["art_bed"])
    add_cyl("Planta_RecP_Pot", 0.16, 0.36, (8.05, 1.35, z0 + 0.18), mats["dark_metal"], verts=18)
    av.add_delicate_lavender_bed("Planta_RecP_Fol", (8.05, 1.35, z0 + 0.36), mats["leaf_dark"], mats["leaf_light"], radius=0.14, seed=72)
    add_box("Vestidor_P", (0.55, 2.8, 2.35), (2.65, 2.1, z0 + 1.18), mats["wood"], bevel=0.01)
    for i in range(5):
        add_box(f"Vest_H_{i}", (0.03, 0.02, 0.36), (2.94, 0.95 + i * 0.55, z0 + 1.15), mats["dark_metal"])

    # Recámara 1
    add_box("Tapete_Rec1", (2.6, 2.6, 0.018), (6.6, 6.9, z0 + 0.009), mats["rug"])
    add_luxury_bed("Cama_Rec1", (6.1, 6.9, z0), mats, mats["charcoal_fabric"], rot_z=-math.pi / 2, width=1.65)
    add_point_light("Luz_BR1", (5.4, 5.8, z0 + 0.88), 42, 0.16, (1.0, 0.78, 0.45))
    add_framed_artwork("Cuadro_Rec1", (6.6, 8.48, z0 + 1.48), 1.35, 0.80, "Y", mats["dark_metal"], mats["art_hall"])

    # Recámara 2 / Sala TV
    add_box("Tapete_Rec2", (2.8, 2.8, 0.018), (6.5, 10.7, z0 + 0.009), mats["rug"])
    add_luxury_bed("Cama_Rec2", (5.9, 10.7, z0), mats, mats["taupe"], rot_z=-math.pi / 2, width=1.65)
    add_box("Mueble_TV_PB", (1.85, 0.42, 0.46), (6.5, 12.22, z0 + 0.23), mats["dark_wood"], bevel=0.012)
    add_box("TV_PB", (1.35, 0.04, 0.78), (6.5, 12.42, z0 + 1.16), mats["black_glass"])
    add_framed_artwork("Cuadro_Rec2", (6.5, 9.02, z0 + 1.48), 1.35, 0.80, "Y", mats["dark_metal"], mats["art_living"])
    add_cyl("Planta_Rec2_Pot", 0.16, 0.36, (8.05, 12.05, z0 + 0.18), mats["dark_metal"], verts=18)
    av.add_delicate_lavender_bed("Planta_Rec2_Fol", (8.05, 12.05, z0 + 0.36), mats["leaf_dark"], mats["leaf_light"], radius=0.14, seed=83)

    # =========================================================================
    # 6. PATIO JARDÍN PRIVADO — NIVEL RENDER 4 (Árboles frondosos, rocas volcánicas, rattan, reloj de arena)
    # =========================================================================
    zp = Z_PATIO
    add_box("Grava_Patio", (6.1, 13.3, 0.08), (11.8, 6.85, zp + 0.04), mats["gravel"])

    # Jardín orgánico curvo de pasto 3D pegado al muro Este (estrictamente a la derecha de las losas — 0 pasto atravesando concreto!)
    pg_mesh = bpy.data.meshes.new("Pasto_Patio_Organico_m")
    pbm = bmesh.new()
    bmesh.ops.create_grid(pbm, x_segments=16, y_segments=26, size=1.0)
    for v in pbm.verts:
        u = v.co.x + 0.5  # 0..1
        w = v.co.y + 0.5  # 0..1
        wy = 4.6 + w * 5.2
        left_x = 13.30 + 0.18 * math.sin(w * math.pi * 2.2)
        wx = left_x + u * (14.85 - left_x)
        v.co = Vector((wx, wy, zp + 0.082))
    pbm.to_mesh(pg_mesh)
    pbm.free()
    patio_grass = bpy.data.objects.new("Pasto_Patio_3D", pg_mesh)
    patio_grass.data.materials.append(mats["grass_ground"])
    bpy.context.collection.objects.link(patio_grass)
    av.apply_grass_geometry_nodes(patio_grass, tuft_asset, density=40.0, scale_min=0.72, scale_max=1.22, seed=99)

    # Deck pizarra oscuro + LED cálido bajo el voladizo del deck (Render 4!)
    add_box("Terraza_Patio", (4.8, 3.8, 0.24), (12.1, 11.3, zp + 0.17), mats["slate"], bevel=0.015)
    add_box("LED_Terraza", (4.4, 0.04, 0.035), (12.1, 9.40, zp + 0.055), mats["led"])
    add_area_light("Luz_LED_Terraza", (12.1, 9.32, zp + 0.065), (math.radians(90), 0, 0), 42, 4.2, 0.08, (1.0, 0.76, 0.36))

    # 2 Sillones tubulares de RATTAN TEJIDO mirando hacia la mesa y cámara (idénticos a Render 4!)
    av.add_rattan_tub_chair("Sillon_P1", (11.0, 11.85, zp + 0.29), math.pi - 0.42, mats["cream_fabric"], mats["rattan"], mats["wood"])
    av.add_rattan_tub_chair("Sillon_P2", (13.2, 11.85, zp + 0.29), math.pi + 0.42, mats["cream_fabric"], mats["rattan"], mats["wood"])
    add_cyl("Mesa_P_Top", 0.50, 0.055, (12.1, 11.05, zp + 0.60), mats["paver"], verts=32)
    add_cyl("Mesa_P_Ped", 0.16, 0.29, (12.1, 11.05, zp + 0.43), mats["paver"], verts=20)
    add_cyl("Tazon_Patio", 0.10, 0.06, (12.02, 11.02, zp + 0.66), mats["white_linen"], verts=18)
    av.add_delicate_vase_twigs("Ramas_Patio", (12.02, 11.02, zp + 0.69), mats["white_linen"], seed=19)
    # Farol negro tejido bajo junto al deck
    add_cyl("Farol_P_Base", 0.135, 0.03, (9.85, 9.35, zp + 0.10), mats["dark_metal"], verts=20)
    add_cyl("Farol_P_Top", 0.135, 0.03, (9.85, 9.35, zp + 0.34), mats["dark_metal"], verts=20)
    for k in range(12):
        a = (k / 12.0) * math.tau
        add_cyl(f"Farol_Rib_{k}", 0.008, 0.24, (9.85 + 0.125 * math.cos(a), 9.35 + 0.125 * math.sin(a), zp + 0.22), mats["dark_metal"], verts=6)
    add_cyl("Farol_L", 0.04, 0.11, (9.85, 9.35, zp + 0.18), mats["led"], verts=12)

    # Losas flotantes de concreto gris (Render 4!)
    for px, py, pw, pd in [
        (11.3, 8.65, 2.75, 1.05),
        (9.9, 7.15, 1.15, 1.32),
        (11.35, 7.15, 1.42, 1.32),
        (12.65, 7.15, 1.02, 1.28),
        (10.6, 5.25, 1.65, 1.15),
        (10.6, 3.45, 1.65, 1.15),
    ]:
        add_box(f"Paver_{px}_{py}", (pw, pd, 0.11), (px, py, zp + 0.10), mats["paver"], bevel=0.014)

    # 2 Árboles botánicos ultra-frondosos altos y exuberantes (sobresalen sobre la fachada como Renders 1 y 2, y enmarcan el patio Render 4!)
    av.add_botanical_tree("Arbol_Principal", (13.30, 6.5, zp + 0.04), 1.76, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=11, with_blossoms=True, leaf_density=1.45)
    av.add_botanical_tree("Arbol_Secundario", (13.85, 9.7, zp + 0.04), 1.32, mats["bark"], mats["leaf_dark"], mats["leaf_light"], mats["blossom"], seed=29, with_blossoms=True, leaf_density=1.30)

    # Rocas volcánicas angulosas fracturadas (idénticas a Render 4!)
    av.add_craggy_boulder("Roca_1", 0.62, (12.65, 8.25, zp + 0.34), mats["rock"], (1.38, 1.02, 0.60), seed=3)
    av.add_craggy_boulder("Roca_2", 0.80, (13.85, 9.35, zp + 0.58), mats["rock"], (0.98, 0.92, 1.12), seed=7)
    av.add_craggy_boulder("Roca_3", 0.48, (9.85, 4.30, zp + 0.26), mats["rock"], (1.22, 0.95, 0.62), seed=19)
    av.add_craggy_boulder("Roca_4", 0.55, (13.65, 5.10, zp + 0.30), mats["rock"], (1.25, 0.92, 0.65), seed=41)

    # Macizos botánicos finos de lavanda morada (Render 4!)
    for idx, (lx, ly, rad) in enumerate([
        (13.45, 6.0, 0.58), (13.65, 7.0, 0.56), (13.45, 7.6, 0.48),
        (13.85, 8.2, 0.55), (13.45, 9.0, 0.48), (13.75, 5.3, 0.54),
    ]):
        av.add_delicate_lavender_bed(f"Lavanda_{idx}", (lx, ly, zp + 0.07), mats["leaf_dark"], mats["lavender"], radius=rad, seed=100 + idx)

    # Arbotantes negros AL RAS EXACTO de cada muro (eastX=14.915, northY=13.217, recX=8.70 — TODOS con cono reloj de arena!)
    for idx, (lx, ly, nx, ny) in enumerate([
        (14.84, 11.4, -1, 0),
        (14.84, 7.4, -1, 0),
        (14.84, 3.8, -1, 0),
        (12.10, 13.14, 0, -1),
        (8.78, 4.95, 1, 0),
        (8.78, 8.80, 1, 0),
    ]):
        av.add_updown_sconce(f"Arb_Patio_{idx}", (lx, ly, zp + 2.08), (nx, ny), mats["dark_metal"], mats["led"], energy=340.0)

    # =========================================================================
    # 7. ILUMINACIÓN INTERIOR CÁLIDA DE LUJO
    # =========================================================================
    add_area_light("Luz_Sala", (5.0, 3.1, Z_TECHO - 0.12), (0, 0, 0), 230, 2.8, 2.4, (1.0, 0.89, 0.74))
    add_area_light("Luz_Comedor", (7.45, 2.55, Z_TECHO - 0.22), (0, 0, 0), 155, 0.6, 1.8, (1.0, 0.86, 0.68))
    add_area_light("Luz_Cocina", (5.5, 6.5, Z_TECHO - 0.12), (0, 0, 0), 185, 3.0, 1.2, (1.0, 0.86, 0.66))
    add_area_light("Luz_Pasillo_1P", (2.4, 5.5, Z_TECHO - 0.12), (0, 0, 0), 165, 1.4, 4.0, (1.0, 0.88, 0.72))
    add_area_light("Luz_Studio", (5.2, 11.8, Z_TECHO - 0.12), (0, 0, 0), 140, 2.0, 2.0, (1.0, 0.88, 0.72))

    # Recámaras de Planta Baja muy cálidas y acogedoras para brillar a través de los canceles (Render 4!)
    add_area_light("Luz_RecP", (6.8, 2.5, -0.52), (0, 0, 0), 390, 2.6, 2.8, (1.0, 0.80, 0.50))
    add_area_light("Luz_Rec1", (6.5, 6.9, -0.52), (0, 0, 0), 370, 2.4, 2.4, (1.0, 0.80, 0.50))
    add_area_light("Luz_Rec2", (6.4, 10.7, -0.52), (0, 0, 0), 370, 2.4, 2.4, (1.0, 0.80, 0.50))
    add_area_light("Luz_Esc_PB", (2.2, 6.5, -0.52), (0, 0, 0), 165, 1.6, 3.5, (1.0, 0.86, 0.68))
    add_area_light("Luz_Patio", (11.6, 7.5, 0.45), (0, 0, 0), 55, 3.5, 4.5, (1.0, 0.86, 0.68))


def render_outputs():
    scene = bpy.context.scene

    # 1. Comparativas estilo fotografía (mismos encuadres que Renders 1, 3, 4 y 5)
    if COMPARE_DIR:
        pcam_data = bpy.data.cameras.new("Cam_Compare")
        pcam_data.lens = 24.0
        pcam_obj = bpy.data.objects.new("Cam_Compare", pcam_data)
        bpy.context.collection.objects.link(pcam_obj)
        scene.camera = pcam_obj
        scene.render.resolution_x = 1600
        scene.render.resolution_y = 900
        scene.cycles.samples = 96

        def look_at(cam, loc, target):
            cam.location = Vector(loc)
            direction = Vector(target) - Vector(loc)
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

        compares = [
            ("compare_01_esquina.jpg", (15.8, -9.8, -0.2), (7.5, 3.2, 0.5), 25.0),
            ("compare_02_frontal.jpg", (3.8, -15.5, -0.4), (7.2, 3.5, 0.2), 26.0),
            ("compare_03_sala_cocina.jpg", (4.05, 1.15, Z_SALA + 1.32), (5.75, 5.4, Z_SALA + 1.18), 20.5),
            ("compare_04_patio.jpg", (11.2, 4.5, Z_PATIO + 1.52), (11.6, 11.4, Z_PATIO + 1.38), 21.5),
            ("compare_05_celosia.jpg", (-12.5, 11.2, Z_COCHERA + 1.35), (3.5, 11.8, Z_COCHERA + 1.45), 28.0),
        ]
        for fname, loc, tgt, lens in compares:
            pcam_data.lens = lens
            look_at(pcam_obj, loc, tgt)
            scene.render.filepath = os.path.join(COMPARE_DIR, fname)
            print(f"[Compare Photo] Generando {fname} ...")
            bpy.ops.render.render(write_still=True)

    # 2. Renderizar los 8 panoramas 360° equirectangulares en 3K
    if os.environ.get("SKIP_PANOS", "") == "1":
        return

    cam_data = bpy.data.cameras.new("Cam_360")
    cam_data.type = "PANO"
    if hasattr(cam_data, "panorama_type"):
        cam_data.panorama_type = "EQUIRECTANGULAR"
    elif hasattr(cam_data, "cycles"):
        cam_data.cycles.panorama_type = "EQUIRECTANGULAR"

    cam_obj = bpy.data.objects.new("Cam_360", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    samples = int(os.environ.get("PANO_SAMPLES", "128"))
    res_x = int(os.environ.get("PANO_RES_X", "3072"))
    res_y = res_x // 2
    scene.cycles.samples = samples
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y

    stops = [
        ("01_fachada_esquina.jpg", (18.5, -6.2, -0.45)),
        ("02_fachada_entrada.jpg", (7.9, 16.8, Z_COCHERA + 1.65)),
        ("03_pasillo_escaleras.jpg", (2.6, 5.4, Z_SALA + 1.55)),
        ("04_sala_cocina.jpg", (5.4, 1.35, Z_SALA + 1.48)),
        ("05_patio_jardin.jpg", (11.0, 5.2, Z_PATIO + 1.62)),
        ("06_recamara_principal.jpg", (7.4, 3.9, Z_SOTANO + 1.48)),
        ("07_recamaras_sala_tv.jpg", (7.2, 10.6, Z_SOTANO + 1.48)),
        ("08_fachada_celosia.jpg", (-8.5, 13.5, Z_COCHERA + 1.55)),
    ]

    only_env = os.environ.get("ONLY_STOPS", "").strip()
    only_prefixes = tuple(p.strip() for p in only_env.split(",") if p.strip()) if only_env else None

    for fname, loc in stops:
        if only_prefixes and not fname.startswith(only_prefixes):
            continue
        cam_obj.location = loc
        cam_obj.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
        scene.render.filepath = os.path.join(OUT_DIR, fname)
        print(f"[Render 360 {res_x}x{res_y}] Generando {fname} ...")
        bpy.ops.render.render(write_still=True)


def main():
    clear_scene()
    configure_cycles(samples=96, res_x=3072, res_y=1536)
    av.setup_photoreal_world_sky(sun_elev_deg=24.0, sun_rot_deg=228.0, sky_strength=0.28)
    av.setup_compositor_bloom()
    build_photoreal_scene()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"[Blender] Proyecto ArchViz 1:1 guardado en: {BLEND_PATH}")
    render_outputs()
    print("[Blender] Renderizado ArchViz finalizado.")


if __name__ == "__main__":
    main()
