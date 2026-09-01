#!/usr/bin/env python3
"""Write single-file binary FBX 7.4 with EMBEDDED PNG textures (Mixamo 'embed media' path).
Input: OBJ+MTL+textures produced by export_mixamo.py (T-pose, merged mesh).
Output: <out>/shibahu_mixamo.fbx  (binary, zlib-compressed arrays, Video Content = raw PNG bytes)
Usage: export_fbx_bin.py <dir_with_obj_mtl_textures> <out_fbx_path>
"""
import struct, zlib, array, os, sys

def P_S(s): b = s.encode('latin1'); return b'S' + struct.pack('<I', len(b)) + b
def P_I(v): return b'I' + struct.pack('<i', v)
def P_L(v): return b'L' + struct.pack('<q', v)
def P_D(v): return b'D' + struct.pack('<d', v)
def P_C(v): return b'C' + struct.pack('B', v)
def P_R(v): return b'R' + struct.pack('<I', len(v)) + v
def P_ARR(t, vals):
    a = array.array({'d': 'd', 'i': 'i', 'f': 'f', 'l': 'q'}[t], vals)
    raw = a.tobytes(); comp = zlib.compress(raw)
    return t.encode() + struct.pack('<III', len(vals), 1, len(comp)) + comp

class Node:
    def __init__(self, name, props=(), children=()):
        self.name = name.encode('latin1'); self.props = list(props); self.children = list(children)

HDR = 27
def emit(n, buf):
    start = len(buf)
    buf += struct.pack('<III', 0, len(n.props), 0)
    buf += struct.pack('B', len(n.name)) + n.name
    p0 = len(buf)
    for p in n.props: buf += p
    proplen = len(buf) - p0
    for c in n.children: emit(c, buf)
    if n.children: buf += b'\x00' * 13
    end = len(buf)
    struct.pack_into('<III', buf, start, end, len(n.props), proplen)
    return buf

def N(name, *props, **kw): return Node(name, props, kw.get('c', []))

def main():
    src, outp = sys.argv[1], sys.argv[2]
    V = []; VT = []; VN = []; groups = []; cur = None
    for line in open(os.path.join(src, 'shibahu.obj')):
        t = line.split()
        if not t: continue
        if t[0] == 'v': V.append(tuple(map(float, t[1:4])))
        elif t[0] == 'vt': VT.append(tuple(map(float, t[1:3])))
        elif t[0] == 'vn': VN.append(tuple(map(float, t[1:4])))
        elif t[0] == 'usemtl': cur = t[1]
        elif t[0] == 'f':
            ids = [tuple(map(int, x.split('/'))) for x in t[1:4]]
            groups.append((cur, ids))
    mat_tex = {}; cur = None
    for line in open(os.path.join(src, 'shibahu.mtl')):
        t = line.split()
        if not t: continue
        if t[0] == 'newmtl': cur = t[1]
        elif t[0] == 'map_Kd': mat_tex[cur] = os.path.basename(t[1])
    matnames = []
    for m, _ in groups:
        if m not in matnames: matnames.append(m)

    verts = [c for p in V for c in p]
    pvi = []; uvi = []; ncor = []
    for _, ids in groups:
        (va, ta, na), (vb, tb, nb), (vc, tc, nc) = ids
        pvi += [va - 1, vb - 1, -vc]
        for (vi, ti, ni) in ids:
            uvi.append(ti - 1)
            ncor += VN[ni - 1]
    uv = [c for p in VT for c in p]
    matidx = [matnames.index(m) for m, _ in groups]

    GEO, MOD = 1000, 2000
    mat_id = {m: 3000 + i for i, m in enumerate(matnames)}
    texm = [m for m in matnames if m in mat_tex]
    tex_id = {m: 4000 + i for i, m in enumerate(texm)}
    vid_id = {m: 5000 + i for i, m in enumerate(texm)}

    geo_children = [
        N('Vertices', P_ARR('d', verts)),
        N('PolygonVertexIndex', P_ARR('i', pvi)),
        N('GeometryVersion', P_I(124)),
        N('LayerElementNormal', P_I(0), c=[
            N('Version', P_I(102)), N('Name', P_S('')),
            N('MappingInformationType', P_S('ByPolygonVertex')),
            N('ReferenceInformationType', P_S('Direct')),
            N('Normals', P_ARR('d', ncor)),
        ]),
        N('LayerElementUV', P_I(0), c=[
            N('Version', P_I(101)), N('Name', P_S('UVMap')),
            N('MappingInformationType', P_S('ByPolygonVertex')),
            N('ReferenceInformationType', P_S('IndexToDirect')),
            N('UV', P_ARR('d', uv)), N('UVIndex', P_ARR('i', uvi)),
        ]),
        N('LayerElementMaterial', P_I(0), c=[
            N('Version', P_I(101)), N('Name', P_S('')),
            N('MappingInformationType', P_S('ByPolygon')),
            N('ReferenceInformationType', P_S('IndexToDirect')),
            N('Materials', P_ARR('i', matidx)),
        ]),
        N('Layer', P_I(0), c=[
            N('Version', P_I(100)),
            N('LayerElement'), N('LayerElement'), N('LayerElement'),
        ]),
    ]
    objects = [
        N('Geometry', P_L(GEO), P_S('Shibahu\x00\x01Geometry'), P_S('Mesh'), c=geo_children),
        N('Model', P_L(MOD), P_S('Shibahu\x00\x01Model'), P_S('Mesh'), c=[
            N('Version', P_I(232)),
            N('Properties70', c=[
                N('P', P_S('Lcl Translation'), P_S('Lcl Translation'), P_S(''), P_S('A'), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('Lcl Rotation'), P_S('Lcl Rotation'), P_S(''), P_S('A'), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('Lcl Scaling'), P_S('Lcl Scaling'), P_S(''), P_S('A'), P_D(1), P_D(1), P_D(1)),
            ]),
            N('Shading', P_C(1)), N('Culling', P_S('CullingOff')),
        ]),
    ]
    for m in matnames:
        objects.append(N('Material', P_L(mat_id[m]), P_S(m + '\x00\x01Material'), P_S(''), c=[
            N('Version', P_I(102)), N('ShadingModel', P_S('phong')), N('MultiLayer', P_I(0)),
            N('Properties70', c=[
                N('P', P_S('EmissiveColor'), P_S('Color'), P_S(''), P_S('A'), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('AmbientColor'), P_S('Color'), P_S(''), P_S('A'), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('DiffuseColor'), P_S('Color'), P_S(''), P_S('A'), P_D(0.8), P_D(0.8), P_D(0.8)),
                N('P', P_S('TransparencyFactor'), P_S('Number'), P_S(''), P_S('A'), P_D(0)),
                N('P', P_S('SpecularColor'), P_S('Color'), P_S(''), P_S('A'), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('ReflectionFactor'), P_S('Number'), P_S(''), P_S('A'), P_D(1)),
                N('P', P_S('Emissive'), P_S('Vector3D'), P_S('Vector'), P_S(''), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('Ambient'), P_S('Vector3D'), P_S('Vector'), P_S(''), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('Diffuse'), P_S('Vector3D'), P_S('Vector'), P_S(''), P_D(0.8), P_D(0.8), P_D(0.8)),
                N('P', P_S('Specular'), P_S('Vector3D'), P_S('Vector'), P_S(''), P_D(0), P_D(0), P_D(0)),
                N('P', P_S('Shininess'), P_S('double'), P_S('Number'), P_S(''), P_D(20)),
                N('P', P_S('Opacity'), P_S('double'), P_S('Number'), P_S(''), P_D(1)),
                N('P', P_S('Reflectivity'), P_S('double'), P_S('Number'), P_S(''), P_D(0)),
            ]),
        ]))
    for m in texm:
        fn = mat_tex[m]
        objects.append(N('Texture', P_L(tex_id[m]), P_S(m + '_map\x00\x01Texture'), P_S(''), c=[
            N('Type', P_S('TextureVideoClip')), N('Version', P_I(202)),
            N('TextureName', P_S(m + '_map\x00\x01Texture')),
            N('Properties70', c=[
                N('P', P_S('CurrentTextureBlendMode'), P_S('enum'), P_S(''), P_S(''), P_I(0)),
                N('P', P_S('UVSet'), P_S('KString'), P_S(''), P_S(''), P_S('UVMap')),
                N('P', P_S('UseMaterial'), P_S('bool'), P_S(''), P_S(''), P_I(1)),
            ]),
            N('Media', P_S('Video::%s_vid' % m)),
            N('FileName', P_S(fn)), N('RelativeFilename', P_S(fn)),
            N('ModelUVTranslation', P_D(0), P_D(0)), N('ModelUVScaling', P_D(1), P_D(1)),
            N('Texture_Alpha_Source', P_S('None')),
            N('Cropping', P_I(0), P_I(0), P_I(0), P_I(0)),
        ]))
        png = open(os.path.join(src, 'textures', fn), 'rb').read()
        objects.append(N('Video', P_L(vid_id[m]), P_S(m + '_vid\x00\x01Video'), P_S('Clip'), c=[
            N('Type', P_S('Clip')),
            N('Properties70', c=[N('P', P_S('Path'), P_S('Path'), P_S(''), P_S(''), P_S(fn))]),
            N('UseMipMap', P_I(0)), N('FileName', P_S(fn)), N('RelativeFilename', P_S(fn)),
            N('Content', P_R(png)),
        ]))

    conns = [N('C', P_S('OO'), P_L(MOD), P_L(0)), N('C', P_S('OO'), P_L(GEO), P_L(MOD))]
    for m in matnames:
        conns.append(N('C', P_S('OO'), P_L(mat_id[m]), P_L(MOD)))
    for m in texm:
        conns.append(N('C', P_S('OP'), P_L(tex_id[m]), P_L(mat_id[m]), P_S('DiffuseColor')))
        conns.append(N('C', P_S('OO'), P_L(vid_id[m]), P_L(tex_id[m])))

    root = [
        N('FBXHeaderExtension', c=[N('FBXHeaderVersion', P_I(1003)), N('FBXVersion', P_I(7400)), N('Creator', P_S('Journey fbx2gltf binary'))]),
        N('FileId', P_R(bytes(range(16)))),
        N('CreationTime', P_S('2026-09-01 00:00:00:000')),
        N('Creator', P_S('Journey fbx2gltf binary')),
        N('GlobalSettings', c=[N('Version', P_I(1000)), N('Properties70', c=[
            N('P', P_S('UpAxis'), P_S('int'), P_S('Integer'), P_S(''), P_I(1)),
            N('P', P_S('UpAxisSign'), P_S('int'), P_S('Integer'), P_S(''), P_I(1)),
            N('P', P_S('FrontAxis'), P_S('int'), P_S('Integer'), P_S(''), P_I(2)),
            N('P', P_S('FrontAxisSign'), P_S('int'), P_S('Integer'), P_S(''), P_I(1)),
            N('P', P_S('CoordAxis'), P_S('int'), P_S('Integer'), P_S(''), P_I(0)),
            N('P', P_S('CoordAxisSign'), P_S('int'), P_S('Integer'), P_S(''), P_I(1)),
            N('P', P_S('UnitScaleFactor'), P_S('double'), P_S('Number'), P_S(''), P_D(1)),
        ])]),
        N('Documents', c=[N('Count', P_I(1))]),
        N('References'),
        N('Definitions', c=[
            N('Version', P_I(100)), N('Count', P_I(2 + len(matnames) + 2 * len(texm))),
            N('ObjectType', P_S('GlobalSettings'), c=[N('Count', P_I(1))]),
            N('ObjectType', P_S('Model'), c=[N('Count', P_I(1))]),
            N('ObjectType', P_S('Geometry'), c=[N('Count', P_I(1))]),
            N('ObjectType', P_S('Material'), c=[N('Count', P_I(len(matnames)))]),
            N('ObjectType', P_S('Texture'), c=[N('Count', P_I(len(texm)))]),
            N('ObjectType', P_S('Video'), c=[N('Count', P_I(len(texm)))]),
        ]),
        N('Objects', c=objects),
        N('Connections', c=conns),
    ]
    buf = bytearray(b'Kaydara FBX Binary  \x00\x1a\x00' + struct.pack('<I', 7400))
    for r in root: emit(r, buf)
    buf += b'\x00' * 13
    buf += b'\x00' * 120
    open(outp, 'wb').write(bytes(buf))
    print('binary fbx written:', outp, len(buf), 'bytes; verts', len(V), 'tris', len(groups))

main()
