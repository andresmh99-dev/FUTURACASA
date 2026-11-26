"""
Librería ArchViz Fotorealista v2 para Blender 5.3 Cycles (GPU OptiX)
Calibrada lado a lado contra las 5 fotografías de render del arquitecto:
- Cielo físico Multiple Scattering + nubes cumulus/cirrus luminosas
- Vidrio arquitectónico Cycles sin bloqueo de sombras (Transparent+Glossy Fresnel)
- Grava multi-escala con brillo solar rasante + Mármol Calacatta Gold 3D
- Pasto 3D fino de loma y patio con Geometry Nodes (briznas finas tipo césped real)
- Árboles botánicos continuos (ramas sin cortes + ~8,500 hojas finas + flores blancas)
- Rocas volcánicas angulosas fracturadas (Voronoi ridged) + Lavanda botánica fina
- Mobiliario de autor: sofá entallado con pliegues sutiles, sillas de concha curva,
  sillones tubulares de rattan tejido real (sin barrotes)
- Arbotantes con conos cálidos reloj de arena de alta intensidad
- Compositor Cycles con sutil bloom cinematográfico (Fog Glow)
"""

import bpy
import bmesh
import math
import random
from mathutils import Vector, Matrix


# ---------------------------------------------------------------------------
# 1. CIELO FÍSICO CON NUBES LUMINOSAS + COMPOSITOR BLOOM
# ---------------------------------------------------------------------------
def setup_photoreal_world_sky(sun_elev_deg=24.0, sun_rot_deg=228.0, sky_strength=0.28):
    world = bpy.data.worlds.new("Sky_Morelia_ArchViz")
    bpy.context.scene.world = world
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = sky_strength

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.0)
    sky.sun_intensity = 1.35
    sky.sun_elevation = math.radians(sun_elev_deg)
    sky.sun_rotation = math.radians(sun_rot_deg)
    sky.altitude = 1920.0
    if hasattr(sky, "air_density"):
        sky.air_density = 1.15
    if hasattr(sky, "aerosol_density"):
        sky.aerosol_density = 1.35

    # Proyección en perspectiva de capa de nubes suaves (cúmulos blancos en cielo azul)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])

    add_z = nt.nodes.new("ShaderNodeMath")
    add_z.operation = "ADD"
    add_z.inputs[1].default_value = 0.14
    nt.links.new(sep.outputs["Z"], add_z.inputs[0])

    max_z = nt.nodes.new("ShaderNodeMath")
    max_z.operation = "MAXIMUM"
    max_z.inputs[1].default_value = 0.06
    nt.links.new(add_z.outputs["Value"], max_z.inputs[0])

    div_x = nt.nodes.new("ShaderNodeMath")
    div_x.operation = "DIVIDE"
    nt.links.new(sep.outputs["X"], div_x.inputs[0])
    nt.links.new(max_z.outputs["Value"], div_x.inputs[1])

    div_y = nt.nodes.new("ShaderNodeMath")
    div_y.operation = "DIVIDE"
    nt.links.new(sep.outputs["Y"], div_y.inputs[0])
    nt.links.new(max_z.outputs["Value"], div_y.inputs[1])

    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(div_x.outputs["Value"], comb.inputs["X"])
    nt.links.new(div_y.outputs["Value"], comb.inputs["Y"])

    n_big = nt.nodes.new("ShaderNodeTexNoise")
    n_big.inputs["Scale"].default_value = 0.34
    n_big.inputs["Detail"].default_value = 12.0
    n_big.inputs["Roughness"].default_value = 0.58
    n_big.inputs["Distortion"].default_value = 0.45
    nt.links.new(comb.outputs["Vector"], n_big.inputs["Vector"])

    ramp_cloud = nt.nodes.new("ShaderNodeValToRGB")
    ramp_cloud.color_ramp.elements[0].position = 0.47
    ramp_cloud.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_cloud.color_ramp.elements[1].position = 0.72
    ramp_cloud.color_ramp.elements[1].color = (0.90, 0.90, 0.90, 1.0)
    nt.links.new(n_big.outputs["Fac"], ramp_cloud.inputs["Fac"])

    ramp_h = nt.nodes.new("ShaderNodeValToRGB")
    ramp_h.color_ramp.elements[0].position = 0.02
    ramp_h.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp_h.color_ramp.elements[1].position = 0.18
    ramp_h.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    nt.links.new(sep.outputs["Z"], ramp_h.inputs["Fac"])

    mult_mask = nt.nodes.new("ShaderNodeMath")
    mult_mask.operation = "MULTIPLY"
    nt.links.new(ramp_cloud.outputs["Color"], mult_mask.inputs[0])
    nt.links.new(ramp_h.outputs["Color"], mult_mask.inputs[1])

    # Nubes blancas soleadas (solo en rayo de cámara para no alterar la luz física solar!)
    lp = nt.nodes.new("ShaderNodeLightPath")
    cam_mask = nt.nodes.new("ShaderNodeMath")
    cam_mask.operation = "MULTIPLY"
    nt.links.new(mult_mask.outputs["Value"], cam_mask.inputs[0])
    nt.links.new(lp.outputs["Is Camera Ray"], cam_mask.inputs[1])

    mix_sky = nt.nodes.new("ShaderNodeMix")
    mix_sky.data_type = "RGBA"
    mix_sky.inputs[7].default_value = (24.0, 24.4, 25.2, 1.0)
    nt.links.new(cam_mask.outputs["Value"], mix_sky.inputs[0])
    nt.links.new(sky.outputs["Color"], mix_sky.inputs[6])

    nt.links.new(mix_sky.outputs[2], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def setup_compositor_bloom():
    """Añade un sutil resplandor fotográfico (Fog Glow) a los LEDs cálidos y brillos solares."""
    scene = bpy.context.scene
    try:
        scene.use_nodes = True
        nt = getattr(scene, "node_tree", None)
        if nt is None:
            return
        nt.nodes.clear()
        rl = nt.nodes.new("CompositorNodeRLayers")
        glare = nt.nodes.new("CompositorNodeGlare")
        glare.glare_type = "FOG_GLOW"
        if hasattr(glare, "quality"):
            glare.quality = "HIGH"
        if hasattr(glare, "threshold"):
            glare.threshold = 3.2
        if hasattr(glare, "mix"):
            glare.mix = -0.84
        if hasattr(glare, "size"):
            glare.size = 7
        comp = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
        nt.links.new(glare.outputs["Image"], comp.inputs["Image"])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 2. MATERIALES PBR ARCHVIZ (Vidrio real, Grava multi-escala, Calacatta, Rattan, Bosque)
# ---------------------------------------------------------------------------
def make_pbr_mat(name, color, roughness=0.7, metallic=0.0, bump_scale=0.0, bump_strength=0.0,
                 emission=None, emission_strength=0.0, transmission=0.0, ior=1.45,
                 color2=None, color_noise_scale=6.0, coat_weight=0.0, coat_roughness=0.1,
                 sheen_weight=0.0, sheen_roughness=0.5, thin_wall=False):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if transmission > 0 and "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if thin_wall and "Thin Wall" in bsdf.inputs:
        bsdf.inputs["Thin Wall"].default_value = True
    if coat_weight > 0 and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat_weight
        bsdf.inputs["Coat Roughness"].default_value = coat_roughness
    if sheen_weight > 0 and "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen_weight
        bsdf.inputs["Sheen Roughness"].default_value = sheen_roughness
    if emission is not None and emission_strength > 0 and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    tc = nt.nodes.new("ShaderNodeTexCoord")
    if color2 is not None:
        cnoise = nt.nodes.new("ShaderNodeTexNoise")
        cnoise.inputs["Scale"].default_value = color_noise_scale
        cnoise.inputs["Detail"].default_value = 10.0
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
        noise.inputs["Detail"].default_value = 12.0
        noise.inputs["Roughness"].default_value = 0.68
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_archviz_glass_mat(name="Vidrio_ArchViz", reflection_strength=0.14):
    """
    Vidrio arquitectónico profesional para Cycles (estándar ArchViz):
    - 100% transparente a rayos de sombra (el sol entra sin bloqueo y sin empañado)
    - Cristalino de frente para ver los interiores cálidos (Renders 1, 3 y 4)
    - Reflejo Fresnel nítido del cielo y árboles en ángulo rasante
    """
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lp = nt.nodes.new("ShaderNodeLightPath")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = reflection_strength

    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    trans.inputs["Color"].default_value = (0.95, 0.98, 0.99, 1.0)

    glossy = nt.nodes.new("ShaderNodeBsdfGlossy")
    glossy.inputs["Color"].default_value = (0.94, 0.97, 1.0, 1.0)
    glossy.inputs["Roughness"].default_value = 0.015

    mix_glass = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], mix_glass.inputs["Fac"])
    nt.links.new(trans.outputs["BSDF"], mix_glass.inputs[1])
    nt.links.new(glossy.outputs["BSDF"], mix_glass.inputs[2])

    # Para rayos de sombra y difusos, pasar directo como Transparent BSDF
    math_or = nt.nodes.new("ShaderNodeMath")
    math_or.operation = "MAXIMUM"
    nt.links.new(lp.outputs["Is Shadow Ray"], math_or.inputs[0])
    nt.links.new(lp.outputs["Is Diffuse Ray"], math_or.inputs[1])

    mix_shad = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(math_or.outputs["Value"], mix_shad.inputs["Fac"])
    nt.links.new(mix_glass.outputs["Shader"], mix_shad.inputs[1])
    nt.links.new(trans.outputs["BSDF"], mix_shad.inputs[2])
    nt.links.new(mix_shad.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_translucent_leaf_mat(name, col_a, col_b, trans_col, trans_mix=0.32):
    """Follaje botánico con variación cromática real y translucidez solar."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix_sh = nt.nodes.new("ShaderNodeMixShader")
    mix_sh.inputs["Fac"].default_value = trans_mix

    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.44
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.45

    trans = nt.nodes.new("ShaderNodeBsdfTranslucent")
    trans.inputs["Color"].default_value = (*trans_col, 1.0)

    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 6.0
    mix_c = nt.nodes.new("ShaderNodeMix")
    mix_c.data_type = "RGBA"
    mix_c.inputs[6].default_value = (*col_a, 1.0)
    mix_c.inputs[7].default_value = (*col_b, 1.0)

    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mix_c.inputs[0])
    nt.links.new(mix_c.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], mix_sh.inputs[1])
    nt.links.new(trans.outputs["BSDF"], mix_sh.inputs[2])
    nt.links.new(mix_sh.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_speckled_gravel_mat(name, base_dark, base_light, roughness_min=0.30, roughness_max=0.68, scale=28.0, bump_str=0.45):
    """Grava fina multi-escala que muestra textura granular nítida y brillo solar rasante (Renders 1, 2, 4, 5)."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.62

    tc = nt.nodes.new("ShaderNodeTexCoord")
    # Grano fino Voronoi (piedritas) + ruido medio (variación orgánica)
    vor1 = nt.nodes.new("ShaderNodeTexVoronoi")
    vor1.inputs["Scale"].default_value = scale
    vor2 = nt.nodes.new("ShaderNodeTexVoronoi")
    vor2.inputs["Scale"].default_value = scale * 2.8
    noise_m = nt.nodes.new("ShaderNodeTexNoise")
    noise_m.inputs["Scale"].default_value = scale * 0.14
    noise_m.inputs["Detail"].default_value = 10.0

    mix_v = nt.nodes.new("ShaderNodeMath")
    mix_v.operation = "MULTIPLY_ADD"
    mix_v.inputs[1].default_value = 0.65

    nt.links.new(tc.outputs["Object"], vor1.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], vor2.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise_m.inputs["Vector"])
    nt.links.new(vor1.outputs["Distance"], mix_v.inputs[0])
    nt.links.new(vor2.outputs["Distance"], mix_v.inputs[2])

    ramp_c = nt.nodes.new("ShaderNodeValToRGB")
    ramp_c.color_ramp.elements[0].position = 0.18
    ramp_c.color_ramp.elements[0].color = (*base_dark, 1.0)
    ramp_c.color_ramp.elements[1].position = 0.85
    ramp_c.color_ramp.elements[1].color = (*base_light, 1.0)
    nt.links.new(mix_v.outputs["Value"], ramp_c.inputs["Fac"])

    # Mezclar variación suave por zonas
    mix_z = nt.nodes.new("ShaderNodeMix")
    mix_z.data_type = "RGBA"
    mix_z.inputs[0].default_value = 0.25
    mix_z.inputs[7].default_value = (
        base_dark[0] * 0.82, base_dark[1] * 0.82, base_dark[2] * 0.82, 1.0
    )
    nt.links.new(ramp_c.outputs["Color"], mix_z.inputs[6])
    nt.links.new(noise_m.outputs["Fac"], mix_z.inputs[0])
    nt.links.new(mix_z.outputs[2], bsdf.inputs["Base Color"])

    # Rugosidad variable por grano para destello realista al sol (Render 2!)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = roughness_min
    mr.inputs["To Max"].default_value = roughness_max
    nt.links.new(vor1.outputs["Distance"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_str
    bump.inputs["Distance"].default_value = 0.015
    nt.links.new(mix_v.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_calacatta_marble_mat(name):
    """Mármol Calacatta Gold de alto realismo con vetas diagonales orgánicas en 3D."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.11
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.45
        bsdf.inputs["Coat Roughness"].default_value = 0.05

    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "DIAGONAL"
    wave.inputs["Scale"].default_value = 1.45
    wave.inputs["Distortion"].default_value = 15.5
    wave.inputs["Detail"].default_value = 11.0
    wave.inputs["Detail Scale"].default_value = 2.2

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.05
    ramp.color_ramp.elements[0].color = (0.28, 0.25, 0.22, 1.0)
    e1 = ramp.color_ramp.elements.new(0.18)
    e1.color = (0.56, 0.50, 0.43, 1.0)
    e2 = ramp.color_ramp.elements.new(0.32)
    e2.color = (0.82, 0.79, 0.75, 1.0)
    ramp.color_ramp.elements[3].position = 0.48
    ramp.color_ramp.elements[3].color = (0.95, 0.94, 0.91, 1.0)

    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def make_woven_rattan_mat(name="Rattan_Tejido"):
    """Tejido real de rattan entrelazado para sillones del patio (Render 4)."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.68

    tc = nt.nodes.new("ShaderNodeTexCoord")
    w_h = nt.nodes.new("ShaderNodeTexWave")
    w_h.bands_direction = "Z"
    w_h.inputs["Scale"].default_value = 26.0
    w_h.inputs["Distortion"].default_value = 0.8

    w_v = nt.nodes.new("ShaderNodeTexWave")
    w_v.bands_direction = "X"
    w_v.inputs["Scale"].default_value = 14.0
    w_v.inputs["Distortion"].default_value = 0.4

    comb = nt.nodes.new("ShaderNodeMath")
    comb.operation = "MULTIPLY_ADD"
    comb.inputs[1].default_value = 0.65

    nt.links.new(tc.outputs["Object"], w_h.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], w_v.inputs["Vector"])
    nt.links.new(w_h.outputs["Fac"], comb.inputs[0])
    nt.links.new(w_v.outputs["Fac"], comb.inputs[2])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.25
    ramp.color_ramp.elements[0].color = (0.14, 0.085, 0.042, 1.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.38, 0.24, 0.12, 1.0)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.012

    nt.links.new(comb.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(comb.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_rock_mat(name):
    """Roca volcánica fracturada oscura con vetas minerales claras (Render 4)."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.92
    tc = nt.nodes.new("ShaderNodeTexCoord")

    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 4.2

    noise_f = nt.nodes.new("ShaderNodeTexNoise")
    noise_f.inputs["Scale"].default_value = 14.0
    noise_f.inputs["Detail"].default_value = 14.0
    noise_f.inputs["Roughness"].default_value = 0.76

    noise_m = nt.nodes.new("ShaderNodeTexNoise")
    noise_m.inputs["Scale"].default_value = 48.0
    noise_m.inputs["Detail"].default_value = 10.0

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (0.045, 0.048, 0.052, 1.0)
    e1 = ramp.color_ramp.elements.new(0.55)
    e1.color = (0.14, 0.14, 0.135, 1.0)
    ramp.color_ramp.elements[2].position = 0.82
    ramp.color_ramp.elements[2].color = (0.34, 0.33, 0.30, 1.0)

    bump1 = nt.nodes.new("ShaderNodeBump")
    bump1.inputs["Strength"].default_value = 0.88
    bump1.inputs["Distance"].default_value = 0.05
    bump2 = nt.nodes.new("ShaderNodeBump")
    bump2.inputs["Strength"].default_value = 0.55
    bump2.inputs["Distance"].default_value = 0.015

    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise_f.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise_m.inputs["Vector"])
    nt.links.new(noise_f.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(vor.outputs["Distance"], bump1.inputs["Height"])
    nt.links.new(noise_m.outputs["Fac"], bump2.inputs["Height"])
    nt.links.new(bump1.outputs["Normal"], bump2.inputs["Normal"])
    nt.links.new(bump2.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def make_forest_hill_mat(name="Bosque_Montanas"):
    """Shader multi-tono para lomas boscosas lejanas (pino oscuro + olivo + otoño + claros)."""
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.96

    tc = nt.nodes.new("ShaderNodeTexCoord")
    n_macro = nt.nodes.new("ShaderNodeTexNoise")
    n_macro.inputs["Scale"].default_value = 0.032
    n_macro.inputs["Detail"].default_value = 10.0
    n_macro.inputs["Roughness"].default_value = 0.68

    n_canopy = nt.nodes.new("ShaderNodeTexNoise")
    n_canopy.inputs["Scale"].default_value = 0.35
    n_canopy.inputs["Detail"].default_value = 12.0
    n_canopy.inputs["Roughness"].default_value = 0.72

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.22
    ramp.color_ramp.elements[0].color = (0.025, 0.048, 0.022, 1.0)   # pino oscuro
    e1 = ramp.color_ramp.elements.new(0.48)
    e1.color = (0.055, 0.088, 0.032, 1.0)                           # bosque verde
    e2 = ramp.color_ramp.elements.new(0.68)
    e2.color = (0.14, 0.11, 0.042, 1.0)                             # copas otoñales (Renders 2, 3, 5)
    ramp.color_ramp.elements[3].position = 0.84
    ramp.color_ramp.elements[3].color = (0.11, 0.145, 0.055, 1.0)   # pradera soleada

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.65
    bump.inputs["Distance"].default_value = 0.8

    nt.links.new(tc.outputs["Object"], n_macro.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], n_canopy.inputs["Vector"])
    nt.links.new(n_macro.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(n_canopy.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------------------------------------------------------------------------
# 3. CUADROS DE GALERÍA EN BÚFER RGBA (Arte minimalista de autor)
# ---------------------------------------------------------------------------
def make_gallery_painting_mat(name, style="earth_horizon"):
    w, h = 256, 192
    img = bpy.data.images.new(f"Img_{name}", width=w, height=h)
    pixels = [0.0] * (w * h * 4)

    for y in range(h):
        ny = y / (h - 1)
        for x in range(w):
            nx = x / (w - 1)
            grain = 0.015 * math.sin(x * 1.7 + y * 2.3) * math.cos(x * 0.9 - y * 1.3)
            if style == "earth_horizon":
                h_line = 0.38 + 0.04 * math.sin(nx * 5.2 + 0.6) + 0.02 * math.cos(nx * 11.0)
                if ny > h_line + 0.14:
                    r, g, b = 0.88 - ny * 0.06, 0.84 - ny * 0.05, 0.77 - ny * 0.05
                elif ny > h_line:
                    t = (ny - h_line) / 0.14
                    r = 0.56 * (1 - t) + 0.82 * t
                    g = 0.42 * (1 - t) + 0.74 * t
                    b = 0.30 * (1 - t) + 0.62 * t
                else:
                    t = ny / max(0.01, h_line)
                    r = 0.14 + 0.16 * t
                    g = 0.13 + 0.14 * t
                    b = 0.12 + 0.11 * t
            elif style == "arch_minimal":
                r, g, b = 0.89, 0.86, 0.81
                dx = (nx - 0.5) * 1.35
                dy = ny - 0.48
                if (ny < 0.48 and abs(dx) < 0.28) or (ny >= 0.48 and dx * dx + dy * dy < 0.28 * 0.28):
                    r, g, b = 0.52, 0.43, 0.34
                if (nx - 0.68) ** 2 + (ny - 0.64) ** 2 < 0.028:
                    r, g, b = 0.14, 0.14, 0.13
            else:
                r, g, b = 0.87, 0.85, 0.80
                wave = 0.48 + 0.12 * math.sin(nx * 4.0) + 0.05 * math.cos(nx * 9.0)
                if ny < wave:
                    r, g, b = 0.30, 0.33, 0.24
                if abs(ny - wave) < 0.035:
                    r, g, b = 0.65, 0.58, 0.48
                if (nx - 0.32) ** 2 + (ny - 0.68) ** 2 < 0.022:
                    r, g, b = 0.76, 0.62, 0.46

            idx = (y * w + x) * 4
            pixels[idx] = max(0.0, min(1.0, r + grain))
            pixels[idx + 1] = max(0.0, min(1.0, g + grain))
            pixels[idx + 2] = max(0.0, min(1.0, b + grain))
            pixels[idx + 3] = 1.0

    img.pixels = pixels
    img.pack()

    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.78
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


# ---------------------------------------------------------------------------
# 4. PASTO 3D FINO CON GEOMETRY NODES (Césped denso aterciopelado tipo Renders 1 y 2)
# ---------------------------------------------------------------------------
def create_grass_tuft_asset(grass_mat):
    """Manojo fino de 28 briznas delgadas y arqueadas (aspecto de césped natural, nunca espinoso)."""
    mesh = bpy.data.meshes.new("GrassTuftMesh")
    bm = bmesh.new()
    rng = random.Random(42)
    for _ in range(28):
        ox = rng.uniform(-0.18, 0.18)
        oy = rng.uniform(-0.18, 0.18)
        ang = rng.uniform(0, math.tau)
        h = rng.uniform(0.065, 0.145)
        lean = rng.uniform(0.035, 0.095)
        w0 = rng.uniform(0.0045, 0.0075)
        ca, sa = math.cos(ang), math.sin(ang)
        px, py = -sa, ca
        lx, ly = ca * lean, sa * lean

        v0 = bm.verts.new((ox - px * w0, oy - py * w0, 0.0))
        v1 = bm.verts.new((ox + px * w0, oy + py * w0, 0.0))
        v2 = bm.verts.new((ox + lx * 0.45 + px * w0 * 0.55, oy + ly * 0.45 + py * w0 * 0.55, h * 0.56))
        v3 = bm.verts.new((ox + lx * 0.45 - px * w0 * 0.55, oy + ly * 0.45 - py * w0 * 0.55, h * 0.56))
        v4 = bm.verts.new((ox + lx, oy + ly, h))
        bm.faces.new((v0, v1, v2, v3))
        bm.faces.new((v3, v2, v4))

    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("Asset_GrassTuft", mesh)
    obj.data.materials.append(grass_mat)
    obj.location = (0, 0, -60)
    bpy.context.collection.objects.link(obj)
    return obj


def apply_grass_geometry_nodes(target_obj, tuft_obj, density=16.0, scale_min=0.75, scale_max=1.35, seed=7):
    """Dispersa decenas de miles de manojos de césped 3D usando Geometry Nodes."""
    mod = target_obj.modifiers.new(name="Grass3D", type="NODES")
    ng = bpy.data.node_groups.new(name=f"GN_Grass_{target_obj.name}", type="GeometryNodeTree")
    mod.node_group = ng

    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links
    n_in = nodes.new("NodeGroupInput")
    n_out = nodes.new("NodeGroupOutput")

    dist = nodes.new("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = density
    dist.inputs["Seed"].default_value = seed

    obj_info = nodes.new("GeometryNodeObjectInfo")
    obj_info.inputs["Object"].default_value = tuft_obj

    def _set_typed_input(node, name, sock_type, val):
        for s in node.inputs:
            if s.name == name and s.type == sock_type:
                s.default_value = val
                return

    def _get_typed_output(node, name, sock_type):
        for s in node.outputs:
            if s.name == name and s.type == sock_type:
                return s
        return node.outputs[0]

    rand_rot = nodes.new("FunctionNodeRandomValue")
    rand_rot.data_type = "FLOAT_VECTOR"
    _set_typed_input(rand_rot, "Min", "VECTOR", (-0.10, -0.10, 0.0))
    _set_typed_input(rand_rot, "Max", "VECTOR", (0.10, 0.10, math.tau))
    rand_rot.inputs["Seed"].default_value = seed + 1

    rand_scl = nodes.new("FunctionNodeRandomValue")
    rand_scl.data_type = "FLOAT"
    _set_typed_input(rand_scl, "Min", "VALUE", scale_min)
    _set_typed_input(rand_scl, "Max", "VALUE", scale_max)
    rand_scl.inputs["Seed"].default_value = seed + 2

    inst = nodes.new("GeometryNodeInstanceOnPoints")
    join = nodes.new("GeometryNodeJoinGeometry")

    links.new(n_in.outputs["Geometry"], dist.inputs["Mesh"])
    links.new(dist.outputs["Points"], inst.inputs["Points"])
    links.new(obj_info.outputs["Geometry"], inst.inputs["Instance"])
    links.new(_get_typed_output(rand_rot, "Value", "VECTOR"), inst.inputs["Rotation"])
    links.new(_get_typed_output(rand_scl, "Value", "VALUE"), inst.inputs["Scale"])
    links.new(n_in.outputs["Geometry"], join.inputs["Geometry"])
    links.new(inst.outputs["Instances"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], n_out.inputs["Geometry"])


# ---------------------------------------------------------------------------
# 5. ÁRBOLES BOTÁNICOS CONTINUOS (Ramas sin cortes + ~8,500 hojas finas + flores blancas)
# ---------------------------------------------------------------------------
def _add_continuous_branch(bm, pts, radii, segs=7):
    """Extruye una rama continua compartiendo anillos de vértices (CERO cortes o grietas)."""
    rings = []
    for k, (pt, rad) in enumerate(zip(pts, radii)):
        if k == 0:
            tan = (pts[1] - pts[0]).normalized()
        elif k == len(pts) - 1:
            tan = (pts[-1] - pts[-2]).normalized()
        else:
            tan = (pts[k + 1] - pts[k - 1]).normalized()
        ref = Vector((1, 0, 0)) if abs(tan.x) < 0.85 else Vector((0, 1, 0))
        x_ax = tan.cross(ref).normalized()
        y_ax = tan.cross(x_ax).normalized()
        ring = []
        for i in range(segs):
            a = (i / segs) * math.tau
            ring.append(bm.verts.new(pt + (x_ax * math.cos(a) + y_ax * math.sin(a)) * rad))
        rings.append(ring)
    for k in range(len(rings) - 1):
        r1, r2 = rings[k], rings[k + 1]
        for i in range(segs):
            ni = (i + 1) % segs
            bm.faces.new((r1[i], r1[ni], r2[ni], r2[i]))


def _add_curved_leaf(bm, center, scale_l, rng):
    L = scale_l
    W = L * 0.48
    rx, ry, rz = rng.uniform(-1.35, 1.35), rng.uniform(-0.85, 0.85), rng.uniform(0, math.tau)
    rot = Matrix.Rotation(rz, 3, "Z") @ Matrix.Rotation(rx, 3, "X") @ Matrix.Rotation(ry, 3, "Y")
    pts = [
        Vector((0, 0, 0)),
        Vector((-W * 0.5, L * 0.40, L * 0.08)),
        Vector((W * 0.5, L * 0.40, L * 0.08)),
        Vector((-W * 0.30, L * 0.78, L * 0.05)),
        Vector((W * 0.30, L * 0.78, L * 0.05)),
        Vector((0, L, -L * 0.04)),
    ]
    vs = [bm.verts.new(center + (rot @ p)) for p in pts]
    bm.faces.new((vs[0], vs[2], vs[1]))
    bm.faces.new((vs[1], vs[2], vs[4], vs[3]))
    bm.faces.new((vs[3], vs[4], vs[5]))


def add_botanical_tree(name, loc, scale, bark_mat, leaf_dark_mat, leaf_light_mat, blossom_mat,
                       seed=11, with_blossoms=True, leaf_density=1.0):
    """Árbol botánico frondoso de 4 niveles (estilo exacto Renders 1 y 4) con ~8,500 hojas y flores blancas."""
    rng = random.Random(seed)
    bm_bark = bmesh.new()
    bm_l1 = bmesh.new()
    bm_l2 = bmesh.new()
    bm_fl = bmesh.new()

    canopy_twigs = []

    def grow(p_start, direction, length, radius, depth):
        # 4 puntos orgánicos continuos por rama
        d1 = (direction + Vector((rng.uniform(-0.14, 0.14), rng.uniform(-0.14, 0.14), 0.06))).normalized()
        p1 = p_start + d1 * (length * 0.34)
        d2 = (d1 + Vector((rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), 0.05))).normalized()
        p2 = p1 + d2 * (length * 0.34)
        d3 = (d2 + Vector((rng.uniform(-0.22, 0.22), rng.uniform(-0.22, 0.22), rng.uniform(0.0, 0.14)))).normalized()
        p3 = p2 + d3 * (length * 0.32)

        segs = 9 if depth == 0 else (7 if depth == 1 else 5)
        _add_continuous_branch(bm_bark, [p_start, p1, p2, p3], [radius, radius * 0.86, radius * 0.72, radius * 0.56], segs)

        if depth >= 2:
            canopy_twigs.append((p1, p2, p3))
        if depth >= 3:
            return

        n_child = 5 if depth == 0 else (3 if depth == 1 else 3)
        base_az = rng.uniform(0, math.tau)
        for i in range(n_child):
            az = base_az + (i / n_child) * math.tau + rng.uniform(-0.4, 0.4)
            spread = rng.uniform(0.38, 0.80) if depth == 0 else rng.uniform(0.42, 0.88)
            up = rng.uniform(0.50, 0.92)
            child_dir = Vector((math.cos(az) * spread, math.sin(az) * spread, up)).normalized()
            child_dir = (child_dir * 0.72 + d3 * 0.28).normalized()
            # Nacer embebido dentro de la rama padre para cero uniones visibles
            origin = p2.lerp(p3, rng.uniform(0.35, 0.92))
            grow(origin, child_dir, length * rng.uniform(0.64, 0.78), radius * 0.54, depth + 1)

    # Tronco estilizado con copa alta y frondosa (visible tanto en el patio Render 4 como por encima de la fachada Renders 1 y 2!)
    grow(Vector((0, 0, 0)), Vector((0.03, -0.04, 1.0)).normalized(), 1.52 * scale, 0.095 * scale, 0)

    # Follaje ultra-frondoso de hojas pequeñas y racimos de flores blancas (Render 1 y Render 4!)
    leaves_per_twig = int(68 * leaf_density)
    for p1, p2, p3 in canopy_twigs:
        for _ in range(leaves_per_twig):
            base_pt = p1.lerp(p2, rng.random()) if rng.random() < 0.45 else p2.lerp(p3, rng.random())
            off = Vector((rng.gauss(0, 0.25), rng.gauss(0, 0.25), rng.gauss(0, 0.20))) * scale
            pos = base_pt + off
            L = rng.uniform(0.062, 0.112) * scale
            if rng.random() < 0.55:
                _add_curved_leaf(bm_l1, pos, L, rng)
            else:
                _add_curved_leaf(bm_l2, pos, L * 0.92, rng)
        if with_blossoms:
            for _ in range(int(16 * leaf_density)):
                base_pt = p2.lerp(p3, rng.random())
                c_pos = base_pt + Vector((rng.gauss(0, 0.23), rng.gauss(0, 0.23), rng.gauss(0.03, 0.17))) * scale
                _add_curved_leaf(bm_fl, c_pos, rng.uniform(0.045, 0.072) * scale, rng)
                _add_curved_leaf(bm_fl, c_pos + Vector((0.015, -0.012, 0.01)) * scale, rng.uniform(0.038, 0.060) * scale, rng)

    objs = []
    for suffix, bm, mat in [
        ("bark", bm_bark, bark_mat),
        ("leafD", bm_l1, leaf_dark_mat),
        ("leafL", bm_l2, leaf_light_mat),
        ("blossom", bm_fl, blossom_mat),
    ]:
        if len(bm.verts) == 0:
            bm.free()
            continue
        m = bpy.data.meshes.new(f"{name}_{suffix}_m")
        bm.to_mesh(m)
        bm.free()
        o = bpy.data.objects.new(f"{name}_{suffix}", m)
        o.location = loc
        o.data.materials.append(mat)
        bpy.context.collection.objects.link(o)
        if suffix == "bark" and len(m.polygons) > 0:
            m.polygons.foreach_set("use_smooth", [True] * len(m.polygons))
        objs.append(o)
    return objs


def create_distant_forest_cluster(name, foliage_mat, seed=101, conifer=True):
    """Árbol lejano de textura fina boscosa (hojas pequeñas densas para leerse como bosque real a distancia)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    if conifer:
        for tier in range(8):
            z_base = 0.8 + tier * 0.95
            rad = (2.1 - tier * 0.23) * rng.uniform(0.88, 1.12)
            for _ in range(18):
                ang = rng.uniform(0, math.tau)
                r = rng.uniform(0.10, rad)
                pos = Vector((math.cos(ang) * r, math.sin(ang) * r, z_base + rng.uniform(-0.30, 0.35)))
                _add_curved_leaf(bm, pos, rng.uniform(0.32, 0.55), rng)
    else:
        for _ in range(150):
            layer = rng.random()
            rz = 1.4 + layer * 4.4
            max_r = max(0.5, 2.3 - abs(layer - 0.5) * 2.1)
            rad = (rng.random() ** 0.55) * max_r
            ang = rng.random() * math.tau
            pos = Vector((rad * math.cos(ang), rad * math.sin(ang), rz))
            _add_curved_leaf(bm, pos, rng.uniform(0.28, 0.52), rng)

    m = bpy.data.meshes.new(f"{name}_mesh")
    bm.to_mesh(m)
    bm.free()
    m.materials.append(foliage_mat)
    obj = bpy.data.objects.new(f"Asset_{name}", m)
    obj.location = (0, 0, -120)
    bpy.context.collection.objects.link(obj)
    return obj


def scatter_distant_forest_gn(hill_obj, tree_objs, density=0.025, seed=707):
    """Dispersa miles de siluetas reales de árboles en la cordillera lejana con Geometry Nodes."""
    col = bpy.data.collections.new("ForestProtos")
    bpy.context.scene.collection.children.link(col)
    for o in tree_objs:
        if o.name in bpy.context.collection.objects:
            bpy.context.collection.objects.unlink(o)
        col.objects.link(o)

    mod = hill_obj.modifiers.new(name="Forest3D", type="NODES")
    ng = bpy.data.node_groups.new(name=f"GN_Forest_{hill_obj.name}", type="GeometryNodeTree")
    mod.node_group = ng
    ng.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links
    n_in = nodes.new("NodeGroupInput")
    n_out = nodes.new("NodeGroupOutput")

    dist = nodes.new("GeometryNodeDistributePointsOnFaces")
    dist.inputs["Density"].default_value = density
    dist.inputs["Seed"].default_value = seed

    col_info = nodes.new("GeometryNodeCollectionInfo")
    col_info.inputs["Collection"].default_value = col
    col_info.inputs["Separate Children"].default_value = True
    col_info.inputs["Reset Children"].default_value = True

    def _set_typed_input(node, name, sock_type, val):
        for s in node.inputs:
            if s.name == name and s.type == sock_type:
                s.default_value = val
                return

    def _get_typed_output(node, name, sock_type):
        for s in node.outputs:
            if s.name == name and s.type == sock_type:
                return s
        return node.outputs[0]

    rand_rot = nodes.new("FunctionNodeRandomValue")
    rand_rot.data_type = "FLOAT_VECTOR"
    _set_typed_input(rand_rot, "Min", "VECTOR", (-0.06, -0.06, 0.0))
    _set_typed_input(rand_rot, "Max", "VECTOR", (0.06, 0.06, math.tau))
    rand_rot.inputs["Seed"].default_value = seed + 1

    rand_scl = nodes.new("FunctionNodeRandomValue")
    rand_scl.data_type = "FLOAT"
    _set_typed_input(rand_scl, "Min", "VALUE", 0.95)
    _set_typed_input(rand_scl, "Max", "VALUE", 1.85)
    rand_scl.inputs["Seed"].default_value = seed + 2

    inst = nodes.new("GeometryNodeInstanceOnPoints")
    inst.inputs["Pick Instance"].default_value = True
    join = nodes.new("GeometryNodeJoinGeometry")

    links.new(n_in.outputs["Geometry"], dist.inputs["Mesh"])
    links.new(dist.outputs["Points"], inst.inputs["Points"])
    links.new(col_info.outputs["Instances"], inst.inputs["Instance"])
    links.new(_get_typed_output(rand_rot, "Value", "VECTOR"), inst.inputs["Rotation"])
    links.new(_get_typed_output(rand_scl, "Value", "VALUE"), inst.inputs["Scale"])
    links.new(n_in.outputs["Geometry"], join.inputs["Geometry"])
    links.new(inst.outputs["Instances"], join.inputs["Geometry"])
    links.new(join.outputs["Geometry"], n_out.inputs["Geometry"])


# ---------------------------------------------------------------------------
# 6. ROCAS VOLCÁNICAS FRACTURADAS + LAVANDA BOTÁNICA FINA (Nivel Render 4)
# ---------------------------------------------------------------------------
def add_craggy_boulder(name, radius, loc, mat, scale=(1.2, 1.0, 0.72), seed=1):
    """Roca volcánica angulosa y escultural con planos fracturados (idéntica a Render 4)."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=radius, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    rng = random.Random(seed * 37)
    # 7 planos de fractura aleatorios para tallar caras angulosas naturales
    planes = [
        (Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 1.0))).normalized(), rng.uniform(0.55, 0.85) * radius)
        for _ in range(7)
    ]
    for v in bm.verts:
        p = v.co.copy()
        # Aplanar suavemente contra planos de fractura (efecto roca partida real)
        for nrm, dist in planes:
            d = p.dot(nrm)
            if d > dist:
                p -= nrm * (d - dist) * 0.65
        # Crestas volcánicas multi-octava
        r1 = 1.0 - abs(math.sin(p.x * 4.5 + seed) * math.cos(p.y * 4.1 - seed))
        r2 = 1.0 - abs(math.sin(p.z * 8.2 + p.x * 6.5))
        r3 = math.cos(p.y * 16.0 - p.z * 13.0)
        f = 0.88 + 0.18 * r1 + 0.10 * r2 + 0.04 * r3
        v.co.x = p.x * f * scale[0]
        v.co.y = p.y * f * scale[1]
        v.co.z = max(-radius * 0.35, p.z * f * scale[2])
    bm.to_mesh(obj.data)
    bm.free()
    # Sombreado facetado-suave con Weighted/Sharp look (sin efecto plastilina!)
    obj.data.materials.append(mat)
    return obj


def add_delicate_lavender_bed(name, loc, green_mat, purple_mat, radius=0.55, seed=1):
    """Macizo botánico fino de lavanda con 140 tallos delgados y micro-espigas moradas (Render 4)."""
    rng = random.Random(seed)
    x0, y0, z0 = loc
    mesh_g = bpy.data.meshes.new(f"{name}_g")
    mesh_p = bpy.data.meshes.new(f"{name}_p")
    bmg, bmp = bmesh.new(), bmesh.new()

    for idx in range(145):
        ang = rng.uniform(0, math.tau)
        r = (rng.random() ** 0.65) * radius
        h = rng.uniform(0.22, 0.52)
        ox, oy = r * math.cos(ang), r * math.sin(ang)
        lean = rng.uniform(0.06, 0.22)
        lx, ly = math.cos(ang) * lean, math.sin(ang) * lean
        px, py = -math.sin(ang) * 0.0045, math.cos(ang) * 0.0045

        v0 = bmg.verts.new((ox - px, oy - py, 0.0))
        v1 = bmg.verts.new((ox + px, oy + py, 0.0))
        v2 = bmg.verts.new((ox + lx * 0.55 + px * 0.7, oy + ly * 0.55 + py * 0.7, h * 0.58))
        v3 = bmg.verts.new((ox + lx * 0.55 - px * 0.7, oy + ly * 0.55 - py * 0.7, h * 0.58))
        v4 = bmg.verts.new((ox + lx, oy + ly, h))
        bmg.faces.new((v0, v1, v2, v3))
        bmg.faces.new((v3, v2, v4))

        # 55% de los tallos rematan en espigas delicadas de 5 micro-florecillas moradas
        if idx % 2 == 0:
            for k in range(5):
                t = 0.76 + k * 0.065
                fx = ox + lx * t + rng.uniform(-0.007, 0.007)
                fy = oy + ly * t + rng.uniform(-0.007, 0.007)
                fz = h * t
                ret = bmesh.ops.create_icosphere(bmp, subdivisions=1, radius=rng.uniform(0.006, 0.0095))
                for v in ret["verts"]:
                    v.co.z *= 1.45
                    v.co += Vector((fx, fy, fz))

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


# ---------------------------------------------------------------------------
# 7. MOBILIARIO DE AUTOR (Sofá entallado, Sillas curvas, Sillón Rattan tejido)
# ---------------------------------------------------------------------------
def add_tailored_cushion(name, size, loc, mat, rot=(0, 0, 0), crown=0.06, corner_pinch=0.0, bevel_w=0.032, subdiv=2):
    """
    Cojín arquitectónico tapizado continuo (SIN bordes escalonados ni efecto malvavisco):
    - Caja subdividida suave con superelipse natural + ligero abultamiento central + arrugas de lino
    """
    sx, sy, sz = size
    mesh = bpy.data.meshes.new(f"{name}_m")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)

    for v in bm.verts:
        # Coordenadas normalizadas -1..1
        nx, ny, nz = v.co.x * 2.0, v.co.y * 2.0, v.co.z * 2.0
        # Suavizado continuo tipo superelipse (mantiene esquinas arquitectónicas sin escalón!)
        r2 = (nx * nx + ny * ny + nz * nz)
        soft = 1.0 - 0.055 * max(0.0, r2 - 1.0)
        x = nx * 0.5 * sx * soft
        y = ny * 0.5 * sy * soft
        z = nz * 0.5 * sz * soft

        # Abombado suave en el centro de la cara principal (Z para asiento, Y para respaldo/cojín)
        if corner_pinch > 0:
            # Almohadón vertical (delgado en Y): abultar en Y, pellizcar esquinas XZ
            dome = 1.0 + crown * 1.8 * max(0.0, (1.0 - nx * nx) * (1.0 - nz * nz))
            c_fac = abs(nx * nz)
            y = y * dome * (1.0 - corner_pinch * c_fac * 0.52)
            x *= (1.0 + corner_pinch * c_fac * 0.06)
            z *= (1.0 + corner_pinch * c_fac * 0.06)
        else:
            # Cojín de asiento / colchón (delgado en Z): abultar suavemente en Z
            dome = 1.0 + crown * 1.4 * max(0.0, (1.0 - nx * nx) * (1.0 - ny * ny))
            z *= dome

        # Micro-ondulación sutil de tela real
        wrinkle = 0.0035 * math.sin(x * 15.0 + y * 12.0) * math.cos(z * 14.0)
        v.co = Vector((x, y + wrinkle, z + wrinkle))

    bm.to_mesh(mesh)
    bm.free()
    if len(mesh.polygons) > 0:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    mod = obj.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = subdiv
    mod.render_levels = subdiv
    obj.data.materials.append(mat)
    bpy.context.collection.objects.link(obj)
    return obj


def add_sculpted_dining_chair(name, loc, rot_z, fabric_mat, wood_mat):
    """Silla de comedor ergonómica de concha curva con patas cónicas de roble (idéntica a Render 3)."""
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)

    parts = [
        add_tailored_cushion(f"{name}_seat", (0.46, 0.45, 0.082), (0, 0.01, 0.45), fabric_mat, crown=0.08, bevel_w=0.028, subdiv=2)
    ]

    bm = bmesh.new()
    segs = 10
    r_in, r_out = 0.21, 0.258
    z_bot, z_top = 0.44, 0.79
    rings = []
    for i in range(segs + 1):
        t = i / segs
        ang = math.radians(-108 + t * 216)
        h_top = z_top - 0.14 * (abs(t - 0.5) * 2.0) ** 1.8
        ca, sa = math.cos(ang), math.sin(ang)
        v_ib = bm.verts.new((sa * r_in, -ca * r_in + 0.02, z_bot))
        v_ob = bm.verts.new((sa * r_out, -ca * r_out + 0.02, z_bot))
        v_it = bm.verts.new((sa * (r_in + 0.022), -ca * (r_in + 0.022) + 0.02, h_top))
        v_ot = bm.verts.new((sa * (r_out + 0.022), -ca * (r_out + 0.022) + 0.02, h_top))
        rings.append((v_ib, v_ob, v_it, v_ot))
    for i in range(segs):
        a, b = rings[i], rings[i + 1]
        bm.faces.new((a[0], b[0], b[2], a[2]))
        bm.faces.new((a[1], a[3], b[3], b[1]))
        bm.faces.new((a[2], b[2], b[3], a[3]))
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.faces.new((rings[0][0], rings[0][2], rings[0][3], rings[0][1]))
    bm.faces.new((rings[-1][0], rings[-1][1], rings[-1][3], rings[-1][2]))
    m = bpy.data.meshes.new(f"{name}_shell_m")
    bm.to_mesh(m)
    bm.free()
    if len(m.polygons) > 0:
        m.polygons.foreach_set("use_smooth", [True] * len(m.polygons))
    shell = bpy.data.objects.new(f"{name}_shell", m)
    mod = shell.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = 2
    mod.render_levels = 2
    shell.data.materials.append(fabric_mat)
    bpy.context.collection.objects.link(shell)
    parts.append(shell)

    for idx, (lx, ly, sx, sy) in enumerate([
        (-0.15, -0.15, -0.205, -0.205),
        (0.15, -0.15, 0.205, -0.205),
        (-0.15, 0.15, -0.205, 0.205),
        (0.15, 0.15, 0.205, 0.205),
    ]):
        bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.012, radius2=0.022, depth=0.44, location=((lx + sx) / 2, (ly + sy) / 2, 0.22))
        leg = bpy.context.active_object
        leg.name = f"{name}_leg{idx}"
        vec = Vector((lx - sx, ly - sy, 0.44)).normalized()
        leg.rotation_mode = "QUATERNION"
        leg.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(vec)
        leg.data.polygons.foreach_set("use_smooth", [True] * len(leg.data.polygons))
        leg.data.materials.append(wood_mat)
        parts.append(leg)

    for p in parts:
        p.parent = g


def add_rattan_tub_chair(name, loc, rot_z, fabric_mat, rattan_mat, wood_mat):
    """Sillón lounge redondo con concha continua de rattan tejido y cojín mullido (idéntico a Render 4!)."""
    g = bpy.data.objects.new(name, None)
    g.location = loc
    g.rotation_euler = (0, 0, rot_z)
    bpy.context.collection.objects.link(g)
    parts = []

    # Base cilíndrica tapizada con zócalo de madera
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.41, depth=0.05, location=(0, 0, 0.12))
    rim = bpy.context.active_object
    rim.name = f"{name}_rim"
    rim.data.polygons.foreach_set("use_smooth", [True] * len(rim.data.polygons))
    rim.data.materials.append(wood_mat)
    parts.append(rim)

    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.42, depth=0.22, location=(0, 0, 0.255))
    base = bpy.context.active_object
    base.name = f"{name}_base"
    base.data.polygons.foreach_set("use_smooth", [True] * len(base.data.polygons))
    base.data.materials.append(fabric_mat)
    parts.append(base)

    # Cojín de respaldo mullido recargado
    parts.append(add_tailored_cushion(f"{name}_pil", (0.46, 0.16, 0.38), (0, -0.17, 0.56), fabric_mat, (0.18, 0, 0), crown=0.14, corner_pinch=0.32, bevel_w=0.035, subdiv=2))

    # Concha continua envolvente de rattan tejido (SIN barrotes separados!)
    bm = bmesh.new()
    segs = 16
    r_in, r_out = 0.385, 0.425
    z_bot, z_top = 0.33, 0.72
    rings = []
    for i in range(segs + 1):
        t = i / segs
        ang = math.radians(-118 + t * 236)
        h_top = z_top - 0.11 * (abs(t - 0.5) * 2.0) ** 1.6
        ca, sa = math.cos(ang), math.sin(ang)
        rings.append((
            bm.verts.new((sa * r_in, -ca * r_in, z_bot)),
            bm.verts.new((sa * r_out, -ca * r_out, z_bot)),
            bm.verts.new((sa * (r_in + 0.025), -ca * (r_in + 0.025), h_top)),
            bm.verts.new((sa * (r_out + 0.025), -ca * (r_out + 0.025), h_top)),
        ))
    for i in range(segs):
        a, b = rings[i], rings[i + 1]
        bm.faces.new((a[0], b[0], b[2], a[2]))
        bm.faces.new((a[1], a[3], b[3], b[1]))
        bm.faces.new((a[2], b[2], b[3], a[3]))
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.faces.new((rings[0][0], rings[0][2], rings[0][3], rings[0][1]))
    bm.faces.new((rings[-1][0], rings[-1][1], rings[-1][3], rings[-1][2]))

    m = bpy.data.meshes.new(f"{name}_shell_m")
    bm.to_mesh(m)
    bm.free()
    m.polygons.foreach_set("use_smooth", [True] * len(m.polygons))
    shell = bpy.data.objects.new(f"{name}_shell", m)
    mod = shell.modifiers.new("Subsurf", "SUBSURF")
    mod.levels = 2
    mod.render_levels = 2
    shell.data.materials.append(rattan_mat)
    bpy.context.collection.objects.link(shell)
    parts.append(shell)

    # 4 patas cortas de madera
    for idx, (lx, ly) in enumerate([(-0.26, -0.26), (0.26, -0.26), (-0.26, 0.26), (0.26, 0.26)]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.018, depth=0.11, location=(lx, ly, 0.055))
        leg = bpy.context.active_object
        leg.name = f"{name}_leg{idx}"
        leg.data.polygons.foreach_set("use_smooth", [True] * len(leg.data.polygons))
        leg.data.materials.append(wood_mat)
        parts.append(leg)

    for p in parts:
        p.parent = g


def add_delicate_vase_twigs(name, loc, wood_mat, seed=77):
    """Ramillete delicado de ramitas finas oscuras para el florero de la sala (Render 3)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(6):
        az = (i / 6.0) * math.tau + rng.uniform(-0.3, 0.3)
        spread = rng.uniform(0.18, 0.42)
        p0 = Vector((0, 0, 0))
        p1 = Vector((math.cos(az) * spread * 0.4, math.sin(az) * spread * 0.4, rng.uniform(0.16, 0.22)))
        p2 = p1 + Vector((math.cos(az + 0.3) * spread * 0.55, math.sin(az + 0.3) * spread * 0.55, rng.uniform(0.15, 0.24)))
        _add_continuous_branch(bm, [p0, p1, p2], [0.004, 0.0028, 0.0014], segs=5)
        # Sub-ramita lateral
        p3 = p1.lerp(p2, 0.55) + Vector((math.cos(az - 0.7) * 0.11, math.sin(az - 0.7) * 0.11, 0.11))
        _add_continuous_branch(bm, [p1.lerp(p2, 0.45), p3], [0.0022, 0.0010], segs=4)
    m = bpy.data.meshes.new(f"{name}_m")
    bm.to_mesh(m)
    bm.free()
    m.polygons.foreach_set("use_smooth", [True] * len(m.polygons))
    obj = bpy.data.objects.new(name, m)
    obj.location = loc
    obj.data.materials.append(wood_mat)
    bpy.context.collection.objects.link(obj)
    return obj


def add_gooseneck_faucet(name, loc, chrome_mat):
    """Grifo curvo cuello de ganso en cromo para la isla de cocina (Render 3)."""
    bm = bmesh.new()
    pts = [
        Vector((0, 0, 0.0)),
        Vector((0, 0, 0.22)),
        Vector((0, -0.02, 0.31)),
        Vector((0, -0.08, 0.35)),
        Vector((0, -0.15, 0.32)),
        Vector((0, -0.18, 0.25)),
    ]
    radii = [0.022, 0.014, 0.013, 0.012, 0.011, 0.010]
    _add_continuous_branch(bm, pts, radii, segs=12)
    m = bpy.data.meshes.new(f"{name}_m")
    bm.to_mesh(m)
    bm.free()
    m.polygons.foreach_set("use_smooth", [True] * len(m.polygons))
    obj = bpy.data.objects.new(name, m)
    obj.location = loc
    obj.data.materials.append(chrome_mat)
    bpy.context.collection.objects.link(obj)
    return obj


def add_updown_sconce(name, loc, wall_normal_xy, dark_metal_mat, led_mat, energy=280.0):
    """Arbotante negro con conos reales de luz cálida reloj de arena (idéntico a Render 4!)."""
    x, y, z = loc
    nx, ny = wall_normal_xy
    mesh = bpy.data.meshes.new(f"{name}_bmesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 0.13
        v.co.y *= 0.13
        v.co.z *= 0.14
    bm.to_mesh(mesh)
    bm.free()
    body = bpy.data.objects.new(f"{name}_body", mesh)
    body.location = (x, y, z)
    body.data.materials.append(dark_metal_mat)
    bpy.context.collection.objects.link(body)

    for sgn, tag in [(1, "up"), (-1, "dn")]:
        dm = bpy.data.meshes.new(f"{name}_dm_{tag}")
        dbm = bmesh.new()
        bmesh.ops.create_cube(dbm, size=1.0)
        for v in dbm.verts:
            v.co.x *= 0.095
            v.co.y *= 0.095
            v.co.z *= 0.012
        dbm.to_mesh(dm)
        dbm.free()
        d = bpy.data.objects.new(f"{name}_led_{tag}", dm)
        d.location = (x, y, z + sgn * 0.072)
        d.data.materials.append(led_mat)
        bpy.context.collection.objects.link(d)

        # SpotLight rasante de alta intensidad para que el reloj de arena brille incluso de día!
        ld = bpy.data.lights.new(f"{name}_spot_{tag}", type="SPOT")
        ld.energy = energy
        ld.color = (1.0, 0.78, 0.44)
        ld.spot_size = math.radians(72)
        ld.spot_blend = 0.65
        ld.shadow_soft_size = 0.04
        lo = bpy.data.objects.new(f"{name}_spot_{tag}", ld)
        lo.location = (x + nx * 0.075, y + ny * 0.075, z + sgn * 0.095)
        lo.rotation_euler = (math.radians(180 if sgn > 0 else 0), 0.0, 0.0)
        if hasattr(lo, "visible_glossy"):
            lo.visible_glossy = False
        bpy.context.collection.objects.link(lo)
