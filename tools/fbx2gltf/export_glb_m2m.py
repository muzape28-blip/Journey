#!/usr/bin/env python3
"""Export GLB paling kompatibel utk auto-rigger browser (Mesh2Motion dkk).

Strategi: satu mesh, SATU primitive, satu material polos + tekstur 1x1 px
embedded (banyak loader browser cuma ngecek material/texture minimal), TANPA
skeleton (auto-rigger bikin sendiri), TANPA material/ground/cheek. Geometry
saja: POSITION + NORMAL + TEXCOORD_0. Ukuran file kecil (~3 MB).

Usage: python3 export_glb_m2m.py <gltf_dir> <out.glb>
"""
import base64
import json
import os
import struct
import sys

SKIP = ('MESH__Plane', 'Cheek_mt', 'lambert2')   # ground plane + blush overlay: bukan tubuh


def main():
    srcdir = sys.argv[1]
    out = sys.argv[2]
    g = json.load(open(os.path.join(srcdir, 'shibahu.gltf')))
    binb = open(os.path.join(srcdir, 'shibahu.bin'), 'rb').read()

    def acc(i):
        a = g['accessors'][i]
        b = g['bufferViews'][a['bufferView']]
        n = a['count'] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        fmt = '<%df' % n if a['componentType'] == 5126 else '<%dI' % n
        return list(struct.unpack_from(fmt, binb, b['byteOffset']))

    mnames = [m.get('name', '') for m in g.get('materials', [])]
    P, N, T, IDX = [], [], [], []
    off = 0
    skipped = set()
    for mesh in g['meshes']:
        for prim in mesh['primitives']:
            mn = mnames[prim['material']] if 'material' in prim else ''
            if mn in SKIP or mn.startswith('line'):
                skipped.add(mn)
                continue
            P += acc(prim['attributes']['POSITION'])
            N += acc(prim['attributes']['NORMAL'])
            T += acc(prim['attributes']['TEXCOORD_0'])
            IDX += [off + i for i in acc(prim['indices'])]
            off += g['accessors'][prim['attributes']['POSITION']]['count']
    print('merged:', off, 'verts', len(IDX) // 3, 'tris | skipped:', sorted(skipped))

    def fbuf(vals):
        return struct.pack('<%df' % len(vals), *vals)

    def ubuf(vals):
        n = len(vals)
        if n <= 65535:
            return struct.pack('<%dH' % n, *vals), 5123, n * 2
        return struct.pack('<%dI' % n, *vals), 5125, n * 4

    idxb, icomp, ibytes = ubuf(IDX)
    bufs = [fbuf(P), fbuf(N), fbuf(T), idxb]
    comps = [5126, 5126, 5126, icomp]
    types = ['VEC3', 'VEC3', 'VEC2', 'SCALAR']
    mins = [[min(P[i::3]) for i in range(3)], [-1, -1, -1], [0, 0], [0]]
    maxs = [[max(P[i::3]) for i in range(3)], [1, 1, 1], [1, 1], [max(IDX)]]

    # tekstur 1x1 putih embedded (material polos, tetap valid utk loader ketat)
    tex = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8'
        'z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')

    binb2 = b''.join(b + (-len(b) % 4) * b'\x00' for b in bufs)
    views, accs = [], []
    o = 0
    for k, b in enumerate(bufs):
        # 34962=ARRAY_BUFFER (vertex), 34963=ELEMENT_ARRAY_BUFFER (index)
        views.append({'buffer': 0, 'byteOffset': o, 'byteLength': len(b),
                      'target': 34963 if k == 3 else 34962})
        o += len(b) + (-len(b) % 4)
    counts = [off, off, off, len(IDX)]
    for k in range(4):
        a = {'bufferView': k, 'componentType': comps[k], 'count': counts[k], 'type': types[k]}
        if k == 0:
            a['min'] = mins[0]
            a['max'] = maxs[0]
        accs.append(a)
    views.append({'buffer': 0, 'byteOffset': len(binb2), 'byteLength': len(tex)})
    images = [{'bufferView': len(views) - 1, 'mimeType': 'image/png'}]
    textures = [{'source': 0}]

    gltf = {
        'asset': {'version': '2.0', 'generator': 'Journey m2m-glb exporter'},
        'scene': 0,
        'scenes': [{'nodes': [0]}],
        'nodes': [{'name': 'Shibahu', 'mesh': 0}],
        'meshes': [{'name': 'Shibahu', 'primitives': [{
            'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2},
            'indices': 3, 'material': 0}]}],
        'materials': [{'name': 'Shibahu_mtl', 'doubleSided': True,
                       'pbrMetallicRoughness': {
                           'baseColorFactor': [1, 1, 1, 1],
                           'baseColorTexture': {'index': 0},
                           'metallicFactor': 0.0, 'roughnessFactor': 0.9}}],
        'textures': textures,
        'images': images,
        'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
        'accessors': accs,
        'bufferViews': views,
        'buffers': [{'byteLength': len(binb2) + len(tex)}],
    }
    textures[0]['sampler'] = 0
    js = json.dumps(gltf, separators=(',', ':')).encode()
    js += (-len(js) % 4) * b' '
    binb2 += tex
    binb2 += (-len(binb2) % 4) * b'\x00'
    total = 12 + 8 + len(js) + 8 + len(binb2)
    with open(out, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<II', len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack('<II', len(binb2), 0x004E4942))
        f.write(binb2)
    print('m2m glb written:', out, '%.1f MB' % (total / 1e6))


if __name__ == '__main__':
    main()
