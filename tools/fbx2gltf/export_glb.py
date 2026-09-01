#!/usr/bin/env python3
"""Pack the OBJ+MTL+textures (full T-pose variant) into a single GLB file
with embedded PNGs - for modern web auto-riggers (Cinevva, Mesh2Motion, etc.)
Usage: export_glb.py <obj_path> <out_glb>
"""
import json, os, struct, sys

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
        elif t[0] == 'vt': VT += [float(t[1]), float(t[2])]
        elif t[0] == 'vn': VN += [float(x) for x in t[1:4]]
        elif t[0] == 'usemtl':
            cur = t[1]; groups.append([cur, []])
        elif t[0] == 'f':
            ids = [int(x.split('/')[0]) - 1 for x in t[1:4]]
            groups[-1][1] += ids
    binb = bytearray()
    buffer_views = []; accessors = []
    def bv(data, target):
        off = len(binb)
        pad = (4 - off % 4) % 4
        binb.extend(b'\x00' * pad); off += pad
        binb.extend(data)
        buffer_views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data), 'target': target})
        return len(buffer_views) - 1
    def acc_f32(arr, kind, target=34962, mn=None, mx=None):
        raw = struct.pack('<%df' % len(arr), *arr)
        i = bv(raw, target)
        a = {'bufferView': i, 'componentType': 5126, 'count': len(arr) // {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[kind], 'type': kind}
        if mn is not None: a['min'] = mn; a['max'] = mx
        accessors.append(a); return len(accessors) - 1
    pos_i = acc_f32(V, 'VEC3', 34962, [min(V[0::3]), min(V[1::3]), min(V[2::3])], [max(V[0::3]), max(V[1::3]), max(V[2::3])])
    nor_i = acc_f32(VN, 'VEC3', 34962)
    uv_i = acc_f32(VT, 'VEC2', 34962)
    images = []; textures = []; samplers = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
    tex_idx = {}
    def get_tex(m):
        if m not in tex_idx:
            p = os.path.join(base, mtl_tex[m])
            raw = open(p, 'rb').read()
            i = bv(raw, 0)
            buffer_views[-1].pop('target')
            images.append({'bufferView': i, 'mimeType': 'image/png'})
            textures.append({'sampler': 0, 'source': len(images) - 1})
            tex_idx[m] = len(textures) - 1
        return tex_idx[m]
    materials = []
    for m in mtl_order:
        mat = {'name': m, 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.9}, 'doubleSided': True}
        if m in mtl_tex:
            mat['pbrMetallicRoughness']['baseColorTexture'] = {'index': get_tex(m)}
            if m in ('HairA_mt', 'HairB_mt'):
                mat['alphaMode'] = 'MASK'; mat['alphaCutoff'] = 0.5
            if m == 'Cheek_mt': mat['alphaMode'] = 'BLEND'
        materials.append(mat)
    primitives = []
    for m, idxs in groups:
        raw = struct.pack('<%dI' % len(idxs), *idxs)
        i = bv(raw, 34963)
        accessors.append({'bufferView': i, 'componentType': 5125, 'count': len(idxs), 'type': 'SCALAR'})
        primitives.append({'attributes': {'POSITION': pos_i, 'NORMAL': nor_i, 'TEXCOORD_0': uv_i}, 'indices': len(accessors) - 1, 'material': mtl_order.index(m)})
    gltf = {
        'asset': {'version': '2.0', 'generator': 'Journey export_glb'},
        'buffers': [{'byteLength': len(binb)}],
        'bufferViews': buffer_views, 'accessors': accessors,
        'images': images, 'textures': textures, 'samplers': samplers, 'materials': materials,
        'meshes': [{'name': 'Shibahu', 'primitives': primitives}],
        'nodes': [{'name': 'Shibahu', 'mesh': 0}],
        'scenes': [{'nodes': [0]}], 'scene': 0,
    }
    jb = json.dumps(gltf, separators=(',', ':')).encode()
    jb_pad = (4 - len(jb) % 4) % 4; jb += b' ' * jb_pad
    bb = bytes(binb); bb_pad = (4 - len(bb) % 4) % 4; bb += b'\x00' * bb_pad
    total = 12 + 8 + len(jb) + 8 + len(bb)
    with open(outp, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(jb), 0x4E4F534A)); f.write(jb)
        f.write(struct.pack('<II', len(bb), 0x004E4942)); f.write(bb)
    print('glb written:', outp, '%.1f MB' % (total / 1e6))

main()
