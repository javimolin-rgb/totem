"""
Totem De Cosecha - escena fotorrealista en Cycles.

Construye el totem a escala real (metros), lo coloca en una explanada
pavimentada al anochecer y lo renderiza con una camara fotografica.

Uso:  python totem_scene.py --out render.png --res 1280x1600 --samples 220
      python totem_scene.py --preview        (test rapido de encuadre)
"""
import argparse, math, os, random, sys
import bpy, bmesh
from mathutils import Vector

R = math.radians
random.seed(7)

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")

# ------------------------------------------------------------------ escena
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc

def link(ob):
    bpy.context.collection.objects.link(ob)
    return ob

# ------------------------------------------------------------------ mallas
def cube(name, size, loc, mat=None, bevel=0.004):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.scale = Vector(size)
    ob.location = Vector(loc)
    if mat: ob.data.materials.append(mat)
    if bevel:
        m = ob.modifiers.new("bev", 'BEVEL')
        m.width = bevel; m.segments = 2
        m.limit_method = 'ANGLE'; m.angle_limit = R(30)
        m.harden_normals = False
    return ob

def quad(name, w, h, loc, facing, mat):
    """Plano vertical en XZ. facing=+1 mira a +Y, -1 mira a -Y. UV 0..1 legible."""
    hw, hh = w / 2.0, h / 2.0
    if facing > 0:
        vs = [(hw, 0, -hh), (-hw, 0, -hh), (-hw, 0, hh), (hw, 0, hh)]
    else:
        vs = [(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], [(0, 1, 2, 3)])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for i, lp in enumerate(me.loops):
        uvl.data[i].uv = uvs[i]
    ob = link(bpy.data.objects.new(name, me))
    ob.location = Vector(loc)
    ob.data.materials.append(mat)
    return ob

def blade(name, h, w, bend, mat):
    """Hoja de hierba: tira estrecha que se afina y se curva."""
    segs = 5
    vs, fs = [], []
    for i in range(segs + 1):
        t = i / segs
        half = w * (1 - t) ** 1.4 / 2
        z = h * t
        y = bend * (t ** 2)
        vs += [(-half, y, z), (half, y, z)]
    for i in range(segs):
        a = i * 2
        fs.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs); me.update()
    ob = link(bpy.data.objects.new(name, me))
    ob.data.materials.append(mat)
    return ob

# ------------------------------------------------------------------ shading
def nm(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (260, 0)
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    return nt, bsdf

def setin(bsdf, name, val, alts=()):
    for n in (name,) + tuple(alts):
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = val
            return True
    return False

def mat_corten():
    m = bpy.data.materials.new("Corten"); nt, b = nm(m)
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-900, 0)
    mp = nt.nodes.new("ShaderNodeMapping"); mp.location = (-720, 0)
    mp.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.location = (-540, 120)
    n1.inputs['Scale'].default_value = 7.0
    n1.inputs['Detail'].default_value = 12.0
    n1.inputs['Roughness'].default_value = 0.62
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.location = (-540, -200)
    n2.inputs['Scale'].default_value = 55.0
    n2.inputs['Detail'].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-320, 140)
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[0].color = (0.137, 0.052, 0.024, 1)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.372, 0.142, 0.055, 1)
    e = ramp.color_ramp.elements.new(0.52); e.color = (0.255, 0.090, 0.034, 1)
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.location = (-320, -140)
    rr.inputs['To Min'].default_value = 0.52
    rr.inputs['To Max'].default_value = 0.86
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-80, -320)
    bump.inputs['Strength'].default_value = 0.22
    bump.inputs['Distance'].default_value = 0.004
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], n1.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], n2.inputs['Vector'])
    nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(n2.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(n2.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Metallic', 0.62)
    return m

def mat_metal(name, col, rough, metal=1.0):
    m = bpy.data.materials.new(name); nt, b = nm(m)
    setin(b, 'Base Color', (*col, 1))
    setin(b, 'Metallic', metal)
    n = nt.nodes.new("ShaderNodeTexNoise"); n.location = (-400, -200)
    n.inputs['Scale'].default_value = 24.0
    n.inputs['Detail'].default_value = 6.0
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.location = (-200, -200)
    rr.inputs['To Min'].default_value = max(0.03, rough - 0.10)
    rr.inputs['To Max'].default_value = rough + 0.10
    nt.links.new(n.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(rr.outputs['Result'], b.inputs['Roughness'])
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-200, -420)
    bump.inputs['Strength'].default_value = 0.06
    bump.inputs['Distance'].default_value = 0.002
    nt.links.new(n.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def mat_panel(name, png, emit):
    """Cajon retroiluminado: el arte actua como difuso y como emisor."""
    m = bpy.data.materials.new(name); nt, b = nm(m)
    img = bpy.data.images.load(png)
    img.colorspace_settings.name = 'sRGB'
    t = nt.nodes.new("ShaderNodeTexImage"); t.location = (-420, 60)
    t.image = img
    t.interpolation = 'Cubic'
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if not setin(b, 'Emission Color', (1, 1, 1, 1), ('Emission',)):
        pass
    for n in ('Emission Color', 'Emission'):
        if n in b.inputs:
            nt.links.new(t.outputs['Color'], b.inputs[n]); break
    # el retroiluminado real no es perfectamente uniforme
    nse = nt.nodes.new("ShaderNodeTexNoise"); nse.location = (-620, -260)
    nse.inputs['Scale'].default_value = 2.6
    nse.inputs['Detail'].default_value = 3.0
    ev = nt.nodes.new("ShaderNodeMapRange"); ev.location = (-420, -260)
    ev.inputs['To Min'].default_value = emit * 0.90
    ev.inputs['To Max'].default_value = emit * 1.10
    if 'Emission Strength' in b.inputs:
        nt.links.new(ev.outputs['Result'], b.inputs['Emission Strength'])
    setin(b, 'Roughness', 0.13)
    setin(b, 'Metallic', 0.0)
    setin(b, 'Specular IOR Level', 0.62, ('Specular',))
    setin(b, 'Coat Weight', 0.25)
    setin(b, 'Coat Roughness', 0.08)
    return m

def mat_emit(name, col, strength):
    m = bpy.data.materials.new(name); nt, b = nm(m)
    setin(b, 'Base Color', (*col, 1))
    for n in ('Emission Color', 'Emission'):
        if n in b.inputs:
            b.inputs[n].default_value = (*col, 1); break
    setin(b, 'Emission Strength', strength)
    setin(b, 'Roughness', 0.3)
    return m

def mat_ground():
    m = bpy.data.materials.new("Asfalto"); nt, b = nm(m)
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1000, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.location = (-800, 160)
    n1.inputs['Scale'].default_value = 0.09
    n1.inputs['Detail'].default_value = 15.0
    n2 = nt.nodes.new("ShaderNodeTexVoronoi"); n2.location = (-800, -160)
    n2.inputs['Scale'].default_value = 7.5
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-580, 160)
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].position = 0.22
    ramp.color_ramp.elements[0].color = (0.042, 0.040, 0.039, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.205, 0.192, 0.176, 1)
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.location = (-580, -120)
    rr.inputs['To Min'].default_value = 0.26
    rr.inputs['To Max'].default_value = 0.78
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-340, -340)
    bump.inputs['Strength'].default_value = 0.55
    bump.inputs['Distance'].default_value = 0.055
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    nt.links.new(n1.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(n1.outputs['Fac'], rr.inputs['Value'])
    nt.links.new(n2.outputs['Distance'], bump.inputs['Height'])
    cd = nt.nodes.new("ShaderNodeCameraData"); cd.location = (-580, -380)
    haze = nt.nodes.new("ShaderNodeMapRange"); haze.location = (-380, -380)
    haze.inputs['From Min'].default_value = 28.0
    haze.inputs['From Max'].default_value = 190.0
    haze.clamp = True
    mixh = nt.nodes.new("ShaderNodeMixRGB"); mixh.location = (-120, 60)
    mixh.inputs['Color2'].default_value = (0.088, 0.080, 0.074, 1)
    mixr = nt.nodes.new("ShaderNodeMixRGB"); mixr.location = (-120, -160)
    mixr.inputs['Color2'].default_value = (0.92, 0.92, 0.92, 1)
    nt.links.new(ramp.outputs['Color'], mixh.inputs['Color1'])
    nt.links.new(rr.outputs['Result'], mixr.inputs['Color1'])
    nt.links.new(cd.outputs['View Distance'], haze.inputs['Value'])
    nt.links.new(haze.outputs['Result'], mixh.inputs['Fac'])
    nt.links.new(haze.outputs['Result'], mixr.inputs['Fac'])
    nt.links.new(mixh.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(mixr.outputs['Color'], b.inputs['Roughness'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Specular IOR Level', 0.4, ('Specular',))
    return m

def mat_leaf(col):
    m = bpy.data.materials.new("Hoja"); nt, b = nm(m)
    setin(b, 'Base Color', (*col, 1))
    setin(b, 'Roughness', 0.52)
    setin(b, 'Subsurface Weight', 0.22, ('Subsurface',))
    if 'Subsurface Radius' in b.inputs:
        b.inputs['Subsurface Radius'].default_value = (0.08, 0.14, 0.05)
    m.use_backface_culling = False
    return m

def mat_painted(name, lin_col):
    """Chapa pintada: color plano, grano fino y suciedad acumulada abajo."""
    m = bpy.data.materials.new(name); nt, b = nm(m)
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-1100, 0)
    geo = nt.nodes.new("ShaderNodeNewGeometry"); geo.location = (-1100, -300)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-920, -200)
    grime = nt.nodes.new("ShaderNodeMapRange"); grime.location = (-740, -200)
    grime.inputs['From Min'].default_value = 0.30
    grime.inputs['From Max'].default_value = 0.95
    grime.inputs['To Min'].default_value = 1.0
    grime.inputs['To Max'].default_value = 0.0
    grime.clamp = True
    n = nt.nodes.new("ShaderNodeTexNoise"); n.location = (-920, 220)
    n.inputs['Scale'].default_value = 3.4
    n.inputs['Detail'].default_value = 12.0
    mulg = nt.nodes.new("ShaderNodeMath"); mulg.location = (-560, -120)
    mulg.operation = 'MULTIPLY'
    mix = nt.nodes.new("ShaderNodeMixRGB"); mix.location = (-360, 60)
    mix.blend_type = 'MIX'
    mix.inputs['Color1'].default_value = (*lin_col, 1)
    mix.inputs['Color2'].default_value = (lin_col[0] * 0.62, lin_col[1] * 0.62, lin_col[2] * 0.60, 1)
    rough = nt.nodes.new("ShaderNodeMapRange"); rough.location = (-360, -260)
    rough.inputs['To Min'].default_value = 0.34
    rough.inputs['To Max'].default_value = 0.52
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-180, -420)
    bump.inputs['Strength'].default_value = 0.05
    bump.inputs['Distance'].default_value = 0.0015
    nt.links.new(geo.outputs['Position'], sep.inputs['Vector'])
    nt.links.new(geo.outputs['Position'], n.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], grime.inputs['Value'])
    nt.links.new(grime.outputs['Result'], mulg.inputs[0])
    nt.links.new(n.outputs['Fac'], mulg.inputs[1])
    nt.links.new(mulg.outputs['Value'], mix.inputs['Fac'])
    nt.links.new(n.outputs['Fac'], rough.inputs['Value'])
    nt.links.new(n.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(rough.outputs['Result'], b.inputs['Roughness'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Metallic', 0.0)
    setin(b, 'Specular IOR Level', 0.5, ('Specular',))
    return m

def mat_gravel():
    m = bpy.data.materials.new("Gravilla"); nt, b = nm(m)
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.location = (-900, 0)
    v = nt.nodes.new("ShaderNodeTexVoronoi"); v.location = (-700, 0)
    v.inputs['Scale'].default_value = 90.0
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-500, 60)
    ramp.color_ramp.elements[0].color = (0.085, 0.078, 0.068, 1)
    ramp.color_ramp.elements[1].color = (0.230, 0.212, 0.185, 1)
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-300, -240)
    bump.inputs['Strength'].default_value = 0.9
    bump.inputs['Distance'].default_value = 0.02
    nt.links.new(tc.outputs['Object'], v.inputs['Vector'])
    nt.links.new(v.outputs['Distance'], ramp.inputs['Fac'])
    nt.links.new(v.outputs['Distance'], bump.inputs['Height'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Roughness', 0.82)
    return m

def mat_concrete():
    m = bpy.data.materials.new("Hormigon"); nt, b = nm(m)
    n = nt.nodes.new("ShaderNodeTexNoise"); n.location = (-400, 0)
    n.inputs['Scale'].default_value = 16.0
    n.inputs['Detail'].default_value = 10.0
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.location = (-200, 0)
    ramp.color_ramp.elements[0].color = (0.17, 0.165, 0.155, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.292, 0.275, 1)
    bump = nt.nodes.new("ShaderNodeBump"); bump.location = (-200, -260)
    bump.inputs['Strength'].default_value = 0.18
    nt.links.new(n.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(n.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
    setin(b, 'Roughness', 0.76)
    return m

# ------------------------------------------------------------------ totem
# Retícula del artboard (640x1168 px) a escala real: 1 px = 5 mm.
PX     = 0.005
FACE_W = 640 * PX          # 3.20 m
FACE_H = 1168 * PX         # 5.84 m
PAD    = 30 * PX           # 0.15 m de marco
GAP    = 16 * PX           # 0.08 m entre cajones
BOX_W  = 580 * PX          # 2.90 m de arte
PLINTH = 0.32              # altura del zócalo
DEPTH_BODY = 0.36
PROUD  = 0.035             # cuánto sobresale el marco sobre el cajón

#  nombre, alto en px  -> 340 = 1,70 m ; 240 = 1,20 m
BOXES = [("logo", 340), ("p1", 240), ("p2", 240), ("p3", 240)]

def face_rows():
    """Devuelve (nombre, z_centro, alto_m) por cajón, y los huecos del marco."""
    z_top = PLINTH + FACE_H
    y = 30.0
    rows, bars = [], []
    for name, hpx in BOXES:
        z_hi = z_top - y * PX
        z_lo = z_top - (y + hpx) * PX
        rows.append((name, (z_hi + z_lo) / 2.0, hpx * PX))
        y += hpx
        if name != BOXES[-1][0]:
            bars.append((z_top - y * PX, z_top - (y + 16) * PX))
            y += 16
    return rows, bars

def build_totem(emit):
    cream = mat_painted("Crema", (0.624, 0.577, 0.490))
    dark  = mat_metal("Anodizado", (0.042, 0.041, 0.039), 0.30, 0.85)
    body_mat = mat_painted("Cuerpo", (0.030, 0.029, 0.027))
    z_top = PLINTH + FACE_H
    z_mid = PLINTH + FACE_H / 2.0

    # cuerpo del cajón
    cube("body", (FACE_W, DEPTH_BODY, FACE_H), (0, 0, z_mid), body_mat, 0.008)
    # zócalo y dado
    cube("plinth", (FACE_W + 0.20, DEPTH_BODY + 0.26, PLINTH), (0, 0, PLINTH / 2), dark, 0.010)
    cube("pad", (FACE_W + 1.60, DEPTH_BODY + 1.70, 0.14), (0, 0, 0.05), mat_concrete(), 0.012)

    rows, bars = face_rows()
    fy = DEPTH_BODY / 2.0

    # cajones retroiluminados, cara delantera y trasera
    for name, zc, h in rows:
        face = mat_panel("face_" + name, os.path.join(ART, name + ".png"), emit)
        quad("front_" + name, BOX_W, h, (0, -(fy + 0.002), zc), -1, face)
        quad("back_"  + name, BOX_W, h, (0,  (fy + 0.002), zc), +1, face)

    # marco crema que sobresale: rieles, coronación, base y travesaños
    def strip(n, w, h, x, z):
        for sgn in (-1, 1):
            cube(n + str(sgn), (w, PROUD * 2, h),
                 (x, sgn * (fy + PROUD), z), cream, 0.006)

    rail_w = PAD
    strip("railL", rail_w, FACE_H, -(FACE_W - rail_w) / 2, z_mid)
    strip("railR", rail_w, FACE_H,  (FACE_W - rail_w) / 2, z_mid)
    strip("top",   BOX_W, PAD, 0, z_top - PAD / 2)
    strip("bot",   BOX_W, PAD, 0, PLINTH + PAD / 2)
    for i, (z_hi, z_lo) in enumerate(bars):
        strip("bar%d" % i, BOX_W, z_hi - z_lo, 0, (z_hi + z_lo) / 2)

    # coronación y costados
    cube("cap", (FACE_W + 0.08, DEPTH_BODY + 2 * PROUD + 0.06, 0.06),
         (0, 0, z_top + 0.03), dark, 0.004)
    for sgn in (-1, 1):
        cube("side%d" % sgn, (0.03, DEPTH_BODY + 2 * PROUD, FACE_H),
             (sgn * (FACE_W / 2 + 0.014), 0, z_mid), dark, 0.004)

    # lecho de gravilla alrededor del dado
    gravel = mat_gravel()
    cube("bed", (FACE_W + 3.40, DEPTH_BODY + 3.20, 0.06), (0, 0, 0.03), gravel, 0.0)

# ------------------------------------------------------------------ entorno
def build_world(sun_elev_deg, sun_rot_deg, strength):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); out.location = (400, 0)
    bg = nt.nodes.new("ShaderNodeBackground"); bg.location = (200, 0)
    bg.inputs['Strength'].default_value = strength
    sky = nt.nodes.new("ShaderNodeTexSky"); sky.location = (-60, 0)
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = R(sun_elev_deg)
    sky.sun_rotation = R(sun_rot_deg)
    sky.sun_intensity = 0.18
    sky.sun_size = R(1.2)
    sky.altitude = 180
    sky.air_density = 1.6
    sky.dust_density = 2.2
    sky.ozone_density = 1.4
    nt.links.new(sky.outputs[0], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs[0])

def build_ground():
    me = bpy.data.meshes.new("ground")
    s = 300.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.update()
    ob = link(bpy.data.objects.new("ground", me))
    ob.data.materials.append(mat_ground())
    return ob

def build_backdrop():
    """Masa de vegetacion lejana y desenfocada: da profundidad sin inventar edificios."""
    m = mat_leaf((0.085, 0.098, 0.115))
    for i in range(96):
        ang = -1.25 + i * 0.027 + (random.random() - 0.5) * 0.05
        d = 74 + random.random() * 86
        h = 3.6 + random.random() * 5.4
        me = bpy.data.meshes.new("bd%d" % i)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=h * 0.34)
        bm.to_mesh(me); bm.free()
        ob = link(bpy.data.objects.new("bd%d" % i, me))
        ob.location = (math.sin(ang) * d, math.cos(ang) * d * 0.45 + d * 0.55, h * 0.42)
        ob.scale = (0.8 + random.random() * 0.7, 0.9, 1.1 + random.random() * 0.8)
        ob.data.materials.append(m)
        for poly in ob.data.polygons: poly.use_smooth = True

def build_sun(elev_deg, rot_deg, energy):
    d = bpy.data.lights.new("Sun", 'SUN')
    d.energy = energy
    d.angle = R(1.6)
    d.color = (1.0, 0.80, 0.64)
    ob = link(bpy.data.objects.new("Sun", d))
    e, a = R(elev_deg), R(rot_deg)
    ob.rotation_euler = (math.pi / 2 - e, 0, a)
    return ob

def build_camera(lens, fstop, loc, look_at, level=True):
    """Camara fotografica. level=True mantiene el eje horizontal y encuadra con
    desplazamiento vertical, asi las verticales del totem no convergen."""
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.sensor_height = 36.0
    cam.sensor_fit = 'VERTICAL'
    cam.dof.use_dof = True
    cam.dof.aperture_fstop = fstop
    ob = link(bpy.data.objects.new("Cam", cam))
    ob.location = Vector(loc)
    tgt = link(bpy.data.objects.new("Focus", None))
    tgt.location = Vector(look_at)
    cam.dof.focus_object = tgt

    dx, dy = look_at[0] - loc[0], look_at[1] - loc[1]
    yaw = math.atan2(dy, dx) - math.pi / 2
    if level:
        ob.rotation_euler = (math.pi / 2, 0.0, yaw)
        d = math.hypot(dx, dy)
        half = d * math.tan(math.atan(cam.sensor_height / 2 / lens))
        cam.shift_y = (look_at[2] - loc[2]) / (2 * half) if half else 0.0
    else:
        c = ob.constraints.new('TRACK_TO')
        c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = ob
    return ob

# ------------------------------------------------------------------ render
def setup_render(sc, w, h, samples, preview):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.threads_mode = 'AUTO'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.012 if not preview else 0.05
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    except Exception:
        pass
    sc.cycles.max_bounces = 8 if not preview else 4
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 6.0
    sc.cycles.blur_glossy = 1.2
    sc.cycles.use_fast_gi = preview
    sc.view_settings.view_transform = 'AgX'
    try:
        for lk in ('AgX - Punchy', 'AgX - Base Contrast', 'None'):
            try:
                sc.view_settings.look = lk; break
            except Exception:
                continue
    except Exception:
        pass
    sc.view_settings.exposure = 0.20
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'

def setup_compositor(sc):
    sc.use_nodes = True
    nt = sc.node_tree; nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers"); rl.location = (-400, 0)
    glare = nt.nodes.new("CompositorNodeGlare"); glare.location = (-150, 0)
    glare.glare_type = 'FOG_GLOW'
    glare.quality = 'HIGH'
    glare.iterations = 3
    glare.mix = -0.72
    glare.threshold = 0.85
    glare.size = 7
    lens = nt.nodes.new("CompositorNodeLensdist"); lens.location = (100, 0)
    lens.use_fit = True
    lens.inputs['Distortion'].default_value = 0.002
    lens.inputs['Dispersion'].default_value = 0.0025
    comp = nt.nodes.new("CompositorNodeComposite"); comp.location = (340, 0)
    nt.links.new(rl.outputs['Image'], glare.inputs['Image'])
    nt.links.new(glare.outputs['Image'], lens.inputs['Image'])
    nt.links.new(lens.outputs['Image'], comp.inputs['Image'])

# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/user/totem/render/out/totem.png")
    ap.add_argument("--res", default="1280x1600")
    ap.add_argument("--samples", type=int, default=220)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--backdrop", action="store_true", help="arboleda lejana")
    ap.add_argument("--tilt", action="store_true", help="deja que la camara se incline (verticales convergentes)")
    ap.add_argument("--elev", type=float, default=-1.2)
    ap.add_argument("--rot", type=float, default=25.0)
    ap.add_argument("--emit", type=float, default=1.9)
    ap.add_argument("--lens", type=float, default=70.0)
    ap.add_argument("--fstop", type=float, default=3.5)
    ap.add_argument("--cam", default="6.6,-10.6,2.85")
    ap.add_argument("--look", default="0.05,0,3.30")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

    w, h = (int(x) for x in a.res.lower().split("x"))
    sc = reset()

    build_world(a.elev, a.rot, 2.3)
    build_ground()
    if a.backdrop:
        build_backdrop()
    build_sun(2.0, a.rot, 1.3)
    build_totem(a.emit)
    build_camera(a.lens, a.fstop,
                 [float(v) for v in a.cam.split(",")],
                 [float(v) for v in a.look.split(",")],
                 level=not a.tilt)

    setup_render(sc, w, h, a.samples, a.preview)
    setup_compositor(sc)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    sc.render.filepath = a.out
    print("[render] %dx%d  samples=%d  objetos=%d" % (w, h, a.samples, len(bpy.data.objects)))
    bpy.ops.render.render(write_still=True)
    print("[render] escrito en", a.out)

main()
