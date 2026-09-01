#!/usr/bin/env python3
"""Round-trip QA untuk GLB: parse chunk JSON+BIN, decode embedded PNG,
rasterize front view (konvensi UV glTF: v=0 atas). Usage: verify_glb_render.py <glb> <out_png>
"""
import struct, json, subprocess, math, sys

def main():
    data = open(sys.argv[1], 'rb').read()
    magic, ver, total = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67 and total == len(data)
    cl, ct = struct.unpack_from('<II', data, 12)
    g = json.loads(data[20:20 + cl])
    o = 20 + cl
    bl, bt = struct.unpack_from('<II', data, o)
    binb = data[o + 8:o + 8 + bl]

    def acc(i):
        a = g['accessors'][i]; b = g['bufferViews'][a['bufferView']]
        n = a['count'] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
        fmt = '<%df' % n if a['componentType'] == 5126 else '<%dI' % n
        return list(struct.unpack_from(fmt, binb, b['byteOffset']))

    imgs = {}
    for i, im in enumerate(g['images']):
        b = g['bufferViews'][im['bufferView']]
        raw = binb[b['byteOffset']:b['byteOffset'] + b['byteLength']]
        assert raw[:8] == b'\x89PNG\r\n\x1a\n'
        open('/tmp/g.png', 'wb').write(raw)
        d = subprocess.run(['convert', '/tmp/g.png', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
        w, h = struct.unpack('>II', raw[16:24])
        imgs[i] = (w, h, d)
    V = acc(0); N = acc(1); U = acc(2)
    faces = []
    for pr in g['meshes'][0]['primitives']:
        idx = acc(pr['indices'])
        m = g['materials'][pr['material']]
        ti = m.get('pbrMetallicRoughness', {}).get('baseColorTexture', {}).get('index')
        src = g['textures'][ti]['source'] if ti is not None else None
        for t in range(0, len(idx), 3):
            faces.append((src, [idx[t], idx[t + 1], idx[t + 2]]))
    W, H = 480, 640
    xs = V[0::3]; ys = V[1::3]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    sc = max(mxx - mnx, mxy - mny); cx = (mnx + mxx) / 2; cy = (mny + mxy) / 2
    fb = [(10, 20, 13)] * (W * H); depth = [-1e18] * (W * H)
    L = (0.45, 0.6, 0.65); ln = math.sqrt(sum(v * v for v in L)); L = [v / ln for v in L]
    def prj(vi): return (0.5 + ((V[vi * 3] - cx) / sc) * 0.9) * W, (0.5 - ((V[vi * 3 + 1] - cy) / sc) * 0.92) * H, V[vi * 3 + 2]
    for src, tri in faces:
        A, B, C = [prj(v) for v in tri]
        aS = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
        if abs(aS) < 1e-9: continue
        inv = 1.0 / aS
        minx = int(max(0, min(A[0], B[0], C[0]))); maxx = int(min(W - 1, max(A[0], B[0], C[0])))
        miny = int(max(0, min(A[1], B[1], C[1]))); maxy = int(min(H - 1, max(A[1], B[1], C[1])))
        for py in range(miny, maxy + 1):
            for px in range(minx, maxx + 1):
                w0 = ((B[0] - px) * (C[1] - py) - (B[1] - py) * (C[0] - px)) * inv
                w1 = ((C[0] - px) * (A[1] - py) - (C[1] - py) * (A[0] - px)) * inv
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0: continue
                z = w0 * A[2] + w1 * B[2] + w2 * C[2]; o = py * W + px
                if z <= depth[o]: continue
                depth[o] = z
                col = (200, 200, 200)
                if src is not None:
                    w, h, raw = imgs[src]
                    u = w0 * U[tri[0] * 2] + w1 * U[tri[1] * 2] + w2 * U[tri[2] * 2]
                    v = w0 * U[tri[0] * 2 + 1] + w1 * U[tri[1] * 2 + 1] + w2 * U[tri[2] * 2 + 1]
                    x = min(w - 1, max(0, int(u * w))); y = min(h - 1, max(0, int(v * h)))  # glTF: v=0 atas
                    oo = (y * w + x) * 4
                    if raw[oo + 3] / 255 < 0.5: continue
                    col = (raw[oo], raw[oo + 1], raw[oo + 2])
                n = (w0 * N[tri[0] * 3] + w1 * N[tri[1] * 3] + w2 * N[tri[2] * 3], w0 * N[tri[0] * 3 + 1] + w1 * N[tri[1] * 3 + 1] + w2 * N[tri[2] * 3 + 1], w0 * N[tri[0] * 3 + 2] + w1 * N[tri[1] * 3 + 2] + w2 * N[tri[2] * 3 + 2])
                nl = math.sqrt(sum(q * q for q in n)) or 1
                ndl = (n[0] * L[0] + n[1] * L[1] + n[2] * L[2]) / nl
                b = 1.05 if ndl > 0.6 else 0.9 if ndl > 0.15 else 0.75 if ndl > -0.1 else 0.6
                fb[o] = tuple(int(min(255, c * b)) for c in col)
    with open('/tmp/glb.ppm', 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (W, H))
        for r, g2, b in fb: f.write(bytes((r, g2, b)))
    subprocess.run(['convert', '/tmp/glb.ppm', sys.argv[2]], check=True)
    print('GLB verify render OK; faces', len(faces))

main()
