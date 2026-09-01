#!/usr/bin/env python3
"""Binary FBX 7.4 writer, Blender-convention-exact, with EMBEDDED textures
(single-file Mixamo 'embed media'). IDs as int32, connections [S I I],
Blender-matching node tree (FileId/CreationTime/Creator/Takes, GeometryVersion,
LayerElement Version children). Verified round-trip via fbx2gltf.py parser.
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
        elif t[0] == 'vt': VT += [float(t[1]), 1.0 - float(t[2])]
        elif t[0] == 'vn': VN += [float(x) for x in t[1:4]]
        elif t[0] == 'usemtl':
            cur = t[1]; groups.append([cur, [], []])
        elif t[0] == 'f':
            ids = [tuple(int(x) for x in tok.split('/')) for tok in t[1:4]]
            groups[-1][1] += [i[0] - 1 for i in ids]
            groups[-1][2] += [(i[1] - 1, i[2] - 1) for i in ids]
    ntris = sum(len(g[1]) // 3 for g in groups)
    pvi = []; nrm = []; uvidx = []; matids = []
    for m, idxs, uvn in groups:
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

    def lay_el(typ, extra_children):
        return N('LayerElement' + typ, [prop('I', 101)], [
            N('Version', [prop('I', 101)]),
            N('Name', [prop('S', '')]),
            N('MappingInformationType', [prop('S', 'ByPolygonVertex' if typ == 'Normal' else 'ByPolygonVertex' if typ == 'UV' else 'ByPolygon')]),
            N('ReferenceInformationType', [prop('S', 'Direct' if typ == 'Normal' else 'IndexToDirect')]),
        ] + extra_children)

    geo = N('Geometry', [prop('I', GEO), prop('S', 'Geometry::Shibahu'), prop('S', 'Mesh')], [
        N('Vertices', [prop('d', V)]),
        N('PolygonVertexIndex', [prop('i', pvi)]),
        N('GeometryVersion', [prop('I', 124)]),
        lay_el('Normal', [N('Normals', [prop('d', nrm)])]),
        N('LayerElementUV', [prop('I', 101)], [
            N('Version', [prop('I', 101)]),
            N('Name', [prop('S', 'map1')]),
            N('MappingInformationType', [prop('S', 'ByPolygonVertex')]),
            N('ReferenceInformationType', [prop('S', 'IndexToDirect')]),
            N('UV', [prop('d', VT)]),
            N('UVIndex', [prop('i', uvidx)]),
        ]),
        N('LayerElementMaterial', [prop('I', 101)], [
            N('Version', [prop('I', 101)]),
            N('Name', [prop('S', '')]),
            N('MappingInformationType', [prop('S', 'ByPolygon')]),
            N('ReferenceInformationType', [prop('S', 'IndexToDirect')]),
            N('Materials', [prop('i', matids)]),
        ]),
        N('Layer', [prop('I', 100)], [
            N('LayerElement', [], [N('Type', [prop('S', 'LayerElementNormal')]), N('TypedIndex', [prop('I', 0)])]),
            N('LayerElement', [], [N('Type', [prop('S', 'LayerElementMaterial')]), N('TypedIndex', [prop('I', 0)])]),
            N('LayerElement', [], [N('Type', [prop('S', 'LayerElementUV')]), N('TypedIndex', [prop('I', 0)])]),
        ]),
    ])
    model = N('Model', [prop('I', MOD), prop('S', 'Model::Shibahu'), prop('S', 'Mesh')], [
        N('Version', [prop('I', 232)]),
        N('Properties70', [], [
            P('Lcl Translation', 'Lcl Translation', 'A', 0.0, 0.0, 0.0),
            P('Lcl Rotation', 'Lcl Rotation', 'A', 0.0, 0.0, 0.0),
            P('Lcl Scaling', 'Lcl Scaling', 'A', 1.0, 1.0, 1.0),
        ]),
        N('Shading', [prop('I', 1)]),
        N('Culling', [prop('S', 'CullingOff')]),
    ])
    matnodes = []
    for m in mtl_order:
        matnodes.append(N('Material', [prop('I', mat_ids[m]), prop('S', 'Material::%s' % m), prop('S', '')], [
            N('Version', [prop('I', 102)]),
            N('ShadingModel', [prop('S', 'phong')]),
            N('MultiLayer', [prop('I', 0)]),
            N('Properties70', [], [P('DiffuseColor', 'Color', 'A', 0.8, 0.8, 0.8)]),
        ]))
    texnodes = []; vidnodes = []
    for m in have_tex:
        fn = mtl_tex[m].split('/')[-1]
        png = open(os.path.join(base, mtl_tex[m]), 'rb').read()
        vidnodes.append(N('Video', [prop('I', vid_ids[m]), prop('S', 'Video::%s_vid' % m), prop('S', 'Clip')], [
            N('Type', [prop('S', 'Clip')]),
            N('UseMipMap', [prop('I', 0)]),
            N('FileName', [prop('S', fn)]),
            N('RelativeFilename', [prop('S', fn)]),
            N('Content', [prop('R', png)]),
        ]))
        texnodes.append(N('Texture', [prop('I', tex_ids[m]), prop('S', 'Texture::%s_map' % m), prop('S', '')], [
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
    cons = [N('C', [prop('S', 'OO'), prop('I', MOD), prop('I', 0)]),
            N('C', [prop('S', 'OO'), prop('I', GEO), prop('I', MOD)])]
    for m in mtl_order:
        cons.append(N('C', [prop('S', 'OO'), prop('I', mat_ids[m]), prop('I', MOD)]))
        if m in have_tex:
            cons.append(N('C', [prop('S', 'OO'), prop('I', tex_ids[m]), prop('I', mat_ids[m]), prop('S', 'DiffuseColor')]))
            cons.append(N('C', [prop('S', 'OO'), prop('I', vid_ids[m]), prop('I', tex_ids[m])]))
    nobj = 2 + len(mtl_order) + 2 * len(have_tex)
    roots = [
        N('FBXHeaderExtension', [], [
            N('FBXHeaderVersion', [prop('I', 1003)]),
            N('FBXVersion', [prop('I', 7400)]),
            N('EncryptionType', [prop('I', 0)]),
            N('CreationTimeStamp', [], [
                N('Version', [prop('I', 1000)]),
                N('Year', [prop('I', 2026)]), N('Month', [prop('I', 9)]), N('Day', [prop('I', 1)]),
                N('Hour', [prop('I', 0)]), N('Minute', [prop('I', 0)]), N('Second', [prop('I', 0)]), N('Millisecond', [prop('I', 0)]),
            ]),
            N('Creator', [prop('S', 'Journey fbx2gltf')]),
        ]),
        N('FileId', [prop('R', bytes(range(16)))]),
        N('CreationTime', [prop('S', '2026-09-01 00:00:00:000')]),
        N('Creator', [prop('S', 'Journey fbx2gltf (binary, embedded media)')]),
        N('GlobalSettings', [], [
            N('Version', [prop('I', 1000)]),
            N('Properties70', [], [
                P('UpAxis', 'int', 'Integer', '', 1),
                P('UpAxisSign', 'int', 'Integer', '', 1),
                P('FrontAxis', 'int', 'Integer', '', 2),
                P('FrontAxisSign', 'int', 'Integer', '', 1),
                P('CoordAxis', 'int', 'Integer', '', 0),
                P('CoordAxisSign', 'int', 'Integer', '', 1),
                P('OriginalUpAxis', 'int', 'Integer', '', -1),
                P('OriginalUpAxisSign', 'int', 'Integer', '', 1),
                P('UnitScaleFactor', 'double', 'Number', '', 1.0),
                P('OriginalUnitScaleFactor', 'double', 'Number', '', 1.0),
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
        N('Takes', [], [N('Current', [prop('S', '')])]),
    ]
    out = [b'Kaydara FBX Binary  \x00\x1a\x00', struct.pack('<I', 7400)]
    off = 27
    for r in roots:
        out.append(r.emit(off)); off += r.size()
    out.append(b'\x00' * 13 + struct.pack('<I', 7400) + b'\x00' * 120 + b'\x00' * 16)
    open(outp, 'wb').write(b''.join(out))
    print('binary fbx written:', outp, 'tris', ntris, 'embedded pngs', len(have_tex))

main()
