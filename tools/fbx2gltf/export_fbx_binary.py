#!/usr/bin/env python3
"""Binary FBX 7.4 writer with EMBEDDED textures (single-file, Mixamo 'embed media').
Consumes the OBJ+MTL produced by export_mixamo.py (full variant) and packs
geometry + materials + PNG bytes into one .fbx. Verified round-trip via fbx2gltf.py.
Usage: export_fbx_binary.py <obj_path> <out_fbx>
"""
import struct, sys, os

def prop(t, v):
    if t == 'I': return b'I' + struct.pack('<i', v)
    if t == 'C': return b'C' + bytes([v])
    if t == 'D': return b'D' + struct.pack('<d', v)
    if t == 'L': return b'L' + struct.pack('<q', v)
    if t == 'S':
        b = v.encode('latin1'); return b'S' + struct.pack('<I', len(b)) + b
    if t == 'R': return b'R' + struct.pack('<I', len(v)) + v
    if t == 'd':
        raw = struct.pack('<%dd' % len(v), *v)
        return b'd' + struct.pack('<III', len(v), 0, len(raw)) + raw
    if t == 'i':
        raw = struct.pack('<%di' % len(v), *v)
        return b'i' + struct.pack('<III', len(v), 0, len(raw)) + raw
    raise ValueError(t)

class N:
    def __init__(s, name, props=(), children=()):
        s.name = name; s.props = list(props); s.children = list(children)
    def size(s):
        n = 13 + len(s.name) + sum(len(p) for p in s.props)
        if s.children: n += sum(c.size() for c in s.children) + 12
        return n
    def emit(s, base):
        nb = s.name.encode('latin1')
        body = b''.join(s.props)
        hdr = struct.pack('<III', base + s.size(), len(s.props), sum(len(p) for p in s.props)) + bytes([len(nb)]) + nb
        out = [hdr, body]
        if s.children:
            off = base + 13 + len(nb) + len(body)
            for c in s.children:
                out.append(c.emit(off)); off += c.size()
            out.append(b'\x00' * 12)
        return b''.join(out)

def P(name, t, sub, *vals):
    ps = [prop('S', name), prop('S', t), prop('S', ''), prop('S', sub)]
    for v in vals:
        ps.append(prop('D', float(v)) if isinstance(v, float) else prop('S', v) if isinstance(v, str) else prop('I', v))
    return N('P', ps)

def main():
    objp, outp = sys.argv[1], sys.argv[2]
    base = os.path.dirname(objp) or '.'
    V = []; VT = []; VN = []; groups = []; cur = None
    mtl_order = []; mtl_tex = {}
    for line in open(os.path.join(base, 'shibahu.mtl')):
        t = line.split()
        if not t: continue
        if t[0] == 'newmtl': mtl_order.append(t[1])
        elif t[0] == 'map_Kd': mtl_tex[mtl_order[-1]] = t[1]
    for line in open(objp):
        t = line.split()
        if not t: continue
        if t[0] == 'v': V += [float(x) for x in t[1:4]]
        elif t[0] == 'vt': VT += [float(t[1]), 1.0 - float(t[2])]  # OBJ bottom-left -> FBX top-left
        elif t[0] == 'vn': VN += [float(x) for x in t[1:4]]
        elif t[0] == 'usemtl':
            cur = t[1]; groups.append([cur, [], []])
        elif t[0] == 'f':
            ids = [tuple(int(x) for x in tok.split('/')) for tok in t[1:4]]
            groups[-1][1] += [i[0] - 1 for i in ids]
            groups[-1][2] += [(i[1] - 1, i[2] - 1) for i in ids]
    ntris = sum(len(g[1]) // 3 for g in groups)
    corners = ntris * 3
    pvi = []; nrm = []; uvi = []; uvidx = []; matids = []
    for mi, (m, idxs, uvn) in enumerate(groups):
        for k in range(len(idxs)):
            pvi.append(idxs[k] if k % 3 != 2 else ~idxs[k])
            vi, ni = uvn[k]
            nrm += VN[ni * 3:ni * 3 + 3]
            uvidx.append(vi)
        matids += [mtl_order.index(m)] * (len(idxs) // 3)
    GEO, MOD = 1000, 2000
    mat_ids = {m: 3000 + i for i, m in enumerate(mtl_order)}
    have_tex = [m for m in mtl_order if m in mtl_tex]
    tex_ids = {m: 4000 + i for i, m in enumerate(have_tex)}
    vid_ids = {m: 5000 + i for i, m in enumerate(have_tex)}

    geo = N('Geometry', [prop('L', GEO), prop('S', 'Geometry::Shibahu'), prop('S', 'Mesh')], [
        N('Vertices', [prop('d', V)]),
        N('PolygonVertexIndex', [prop('i', pvi)]),
        N('LayerElementNormal', [prop('I', 101)], [
            N('Name', [prop('S', '')]),
            N('MappingInformationType', [prop('S', 'ByPolygonVertex')]),
            N('ReferenceInformationType', [prop('S', 'Direct')]),
            N('Normals', [prop('d', nrm)]),
        ]),
        N('LayerElementUV', [prop('I', 101)], [
            N('Name', [prop('S', 'map1')]),
            N('MappingInformationType', [prop('S', 'ByPolygonVertex')]),
            N('ReferenceInformationType', [prop('S', 'IndexToDirect')]),
            N('UV', [prop('d', VT)]),
            N('UVIndex', [prop('i', uvidx)]),
        ]),
        N('LayerElementMaterial', [prop('I', 101)], [
            N('Name', [prop('S', '')]),
            N('MappingInformationType', [prop('S', 'ByPolygon')]),
            N('ReferenceInformationType', [prop('S', 'IndexToDirect')]),
            N('Materials', [prop('i', matids)]),
        ]),
        N('Layer', [prop('I', 100)], [
            N('LayerElement', [prop('S', 'LayerElementNormal'), prop('I', 0)]),
            N('LayerElement', [prop('S', 'LayerElementMaterial'), prop('I', 0)]),
            N('LayerElement', [prop('S', 'LayerElementUV'), prop('I', 0)]),
        ]),
    ])
    model = N('Model', [prop('L', MOD), prop('S', 'Model::Shibahu'), prop('S', 'Mesh')], [
        N('Version', [prop('I', 232)]),
        N('Properties70', [], [
            P('Lcl Translation', 'Lcl Translation', 'A', 0, 0, 0),
            P('Lcl Rotation', 'Lcl Rotation', 'A', 0, 0, 0),
            P('Lcl Scaling', 'Lcl Scaling', 'A', 1, 1, 1),
        ]),
        N('Shading', [prop('C', 1)]),
        N('Culling', [prop('S', 'CullingOff')]),
    ])
    matnodes = []
    for m in mtl_order:
        matnodes.append(N('Material', [prop('L', mat_ids[m]), prop('S', 'Material::%s' % m), prop('S', '')], [
            N('Version', [prop('I', 102)]),
            N('ShadingModel', [prop('S', 'phong')]),
            N('MultiLayer', [prop('C', 0)]),
            N('Properties70', [], [P('DiffuseColor', 'Color', 'A', 0.8, 0.8, 0.8)]),
        ]))
    texnodes = []; vidnodes = []
    for m in have_tex:
        rel = mtl_tex[m]
        fn = rel.split('/')[-1]
        png = open(os.path.join(base, rel), 'rb').read()
        vidnodes.append(N('Video', [prop('L', vid_ids[m]), prop('S', 'Video::%s_vid' % m), prop('S', 'Clip')], [
            N('Type', [prop('S', 'Clip')]),
            N('Properties70', [], [N('P', [prop('S','Path'),prop('S','Path'),prop('S',''),prop('S',''),prop('S',fn)])]),
            N('UseMipMap', [prop('I', 0)]),
            N('FileName', [prop('S', fn)]),
            N('RelativeFilename', [prop('S', fn)]),
            N('Content', [prop('R', png)]),
        ]))
        texnodes.append(N('Texture', [prop('L', tex_ids[m]), prop('S', 'Texture::%s_map' % m), prop('S', '')], [
            N('Type', [prop('S', 'TextureVideoClip')]),
            N('Version', [prop('I', 202)]),
            N('TextureName', [prop('S', '%s_map' % m)]),
            N('Media', [prop('S', 'Video::%s_vid' % m)]),
            N('FileName', [prop('S', fn)]),
            N('RelativeFilename', [prop('S', fn)]),
            N('ModelUVTranslation', [prop('D', 0), prop('D', 0)]),
            N('ModelUVScaling', [prop('D', 1), prop('D', 1)]),
            N('Texture_Alpha_Source', [prop('S', 'None')]),
            N('Cropping', [prop('I', 0), prop('I', 0), prop('I', 0), prop('I', 0)]),
        ]))
    cons = [N('C', [prop('S', 'OO'), prop('L', MOD), prop('L', 0)]),
            N('C', [prop('S', 'OO'), prop('L', GEO), prop('L', MOD)])]
    for m in mtl_order:
        cons.append(N('C', [prop('S', 'OO'), prop('L', mat_ids[m]), prop('L', MOD)]))
        if m in have_tex:
            cons.append(N('C', [prop('S', 'OO'), prop('L', tex_ids[m]), prop('L', mat_ids[m]), prop('S', 'DiffuseColor')]))
            cons.append(N('C', [prop('S', 'OO'), prop('L', vid_ids[m]), prop('L', tex_ids[m])]))
    nobj = 2 + len(mtl_order) + 2 * len(have_tex)
    roots = [
        N('FBXHeaderExtension', [], [
            N('FBXHeaderVersion', [prop('I', 1003)]),
            N('FBXVersion', [prop('I', 7400)]),
            N('Creator', [prop('S', 'Journey fbx2gltf (binary, embedded media)')]),
        ]),
        N('GlobalSettings', [], [
            N('Version', [prop('I', 1000)]),
            N('Properties70', [], [
                P('UpAxis', 'int', 'Integer', '', 1),
                P('UpAxisSign', 'int', 'Integer', '', 1),
                P('FrontAxis', 'int', 'Integer', '', 2),
                P('FrontAxisSign', 'int', 'Integer', '', 1),
                P('CoordAxis', 'int', 'Integer', '', 0),
                P('CoordAxisSign', 'int', 'Integer', '', 1),
                P('UnitScaleFactor', 'double', 'Number', '', 1),
            ]),
        ]),
        N('Documents', [], [N('Count', [prop('I', 1)])]),
        N('References', [], []),
        N('Definitions', [], [
            N('Version', [prop('I', 100)]),
            N('Count', [prop('I', nobj)]),
            N('ObjectType', [prop('S', 'GlobalSettings')], [N('Count', [prop('I', 1)])]),
            N('ObjectType', [prop('S', 'Model')], [N('Count', [prop('I', 1)])]),
            N('ObjectType', [prop('S', 'Geometry')], [N('Count', [prop('I', 1)])]),
            N('ObjectType', [prop('S', 'Material')], [N('Count', [prop('I', len(mtl_order))])]),
            N('ObjectType', [prop('S', 'Texture')], [N('Count', [prop('I', len(have_tex))])]),
            N('ObjectType', [prop('S', 'Video')], [N('Count', [prop('I', len(have_tex))])]),
        ]),
        N('Objects', [], [geo, model] + matnodes + texnodes + vidnodes),
        N('Connections', [], cons),
    ]
    out = [b'Kaydara FBX Binary  \x00\x1a\x00', struct.pack('<I', 7400)]
    off = 27
    for r in roots:
        out.append(r.emit(off)); off += r.size()
    out.append(b'\x00' * 13 + struct.pack('<I', 7400) + b'\x00' * 120 + b'\x00' * 16)
    open(outp, 'wb').write(b''.join(out))
    print('binary fbx written:', outp, 'tris', ntris, 'embedded pngs', len(have_tex))

main()
