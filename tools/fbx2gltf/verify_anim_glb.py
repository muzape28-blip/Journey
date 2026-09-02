#!/usr/bin/env python3
"""Render pose ber-animasi dari GLB ber-skin (verifikasi visual animasi).
Usage: verify_anim_glb.py <glb> <anim_index> <time_sec> <out_png>
Sampler LINEAR, tekstur baseColor, proyeksi depan ortografik.
"""
import json
import math
import struct
import subprocess
import sys


def main():
    glbp, ai, tsec, outp = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    data = open(glbp, 'rb').read()
    cl, _ = struct.unpack_from('<II', data, 12)
    g = json.loads(data[20:20 + cl])
    o = 20 + cl
    bl, _ = struct.unpack_from('<II', data, o)
    binb = data[o + 8:o + 8 + bl]

    def acc(i):
        a = g['accessors'][i]
        b = g['bufferViews'][a['bufferView']]
        n = a['count'] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        fmt = {5126: '<%df', 5123: '<%dH', 5125: '<%dI', 5121: '<%dB'}[a['componentType']] % n
        return list(struct.unpack_from(fmt, binb, b['byteOffset']))

    imgs = {}
    for i, im in enumerate(g['images']):
        b = g['bufferViews'][im['bufferView']]
        raw = binb[b['byteOffset']:b['byteOffset'] + b['byteLength']]
        open('/tmp/g.png', 'wb').write(raw)
        d = subprocess.run(['convert', '/tmp/g.png', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
        w, h = struct.unpack('>II', raw[16:24])
        imgs[i] = (w, h, d)

    nodes = g['nodes']
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []):
            parent[c] = i

    anim = g['animations'][ai]
    samp = {}
    for ch in anim['channels']:
        s = anim['samplers'][ch['sampler']]
        samp.setdefault(ch['target']['node'], {})[ch['target']['path']] = (acc(s['input']), acc(s['output']))

    def sample(node_i, path, t, dim):
        if node_i not in samp or path not in samp[node_i]:
            return None
        times, vals = samp[node_i][path]
        if t <= times[0]:
            return vals[:dim]
        if t >= times[-1]:
            return vals[-dim:]
        k = 0
        while k < len(times) - 1 and times[k + 1] < t:
            k += 1
        f = (t - times[k]) / max(1e-9, times[k + 1] - times[k])
        a = vals[k * dim:(k + 1) * dim]
        b = vals[(k + 1) * dim:(k + 2) * dim]
        r = [a[q] + (b[q] - a[q]) * f for q in range(dim)]
        if path == 'rotation':
            nrm = math.sqrt(sum(x * x for x in r)) or 1
            r = [x / nrm for x in r]
        return r

    def qmat(q):
        x, y, z, w = q
        return [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
                2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
                2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]

    def local_mat(i, t):
        n = nodes[i]
        tr = sample(i, 'translation', t, 3) or n.get('translation', [0, 0, 0])
        ro = sample(i, 'rotation', t, 4) or n.get('rotation', [0, 0, 0, 1])
        sc = sample(i, 'scale', t, 3) or n.get('scale', [1, 1, 1])
        R = qmat(ro)
        m = [0.0] * 16
        for r in range(3):
            for c in range(3):
                m[r * 4 + c] = R[r * 3 + c] * sc[c]
        m[12], m[13], m[14], m[15] = tr[0], tr[1], tr[2], 1.0
        return m

    def mul(a, b):
        r = [0.0] * 16
        for i2 in range(4):
            for j2 in range(4):
                r[i2 * 4 + j2] = sum(a[i2 * 4 + k] * b[k * 4 + j2] for k in range(4))
        return r

    glob = {}

    def gmat(i):
        if i not in glob:
            L = local_mat(i, tsec)
            glob[i] = mul(gmat(parent[i]), L) if i in parent else L
        return glob[i]

    for i in range(len(nodes)):
        gmat(i)

    skins = g['skins']
    PX, PY, PZ, NX, NY, NZ, UU, VV = [], [], [], [], [], [], [], []
    faces = []
    for ni, n in enumerate(nodes):
        if 'mesh' not in n:
            continue
        skin = skins[n['skin']] if 'skin' in n else None
        joints = skin['joints'] if skin else []
        ibm_raw = acc(skin['inverseBindMatrices']) if skin else None
        # glTF MAT4 = column-major; konversi ke row-major biar mul() standar
        ibm = None
        if ibm_raw:
            ibm = []
            for k in range(len(ibm_raw) // 16):
                m = ibm_raw[k * 16:k * 16 + 16]
                ibm += [m[j * 4 + i] for i in range(4) for j in range(4)]
        GJ = [mul(glob[j], ibm[k * 16:k * 16 + 16]) for k, j in enumerate(joints)] if skin else None
        me = g['meshes'][n['mesh']]
        GM = glob[ni]
        for pr in me['primitives']:
            P = acc(pr['attributes']['POSITION'])
            NR = acc(pr['attributes']['NORMAL'])
            U = acc(pr['attributes']['TEXCOORD_0'])
            J = acc(pr['attributes']['JOINTS_0']) if 'JOINTS_0' in pr['attributes'] else None
            W = acc(pr['attributes']['WEIGHTS_0']) if 'WEIGHTS_0' in pr['attributes'] else None
            idx = acc(pr['indices'])
            ti = g['materials'][pr['material']].get('pbrMetallicRoughness', {}).get('baseColorTexture', {}).get('index')
            src = g['textures'][ti]['source'] if ti is not None else None
            base = len(PX)
            for vi in range(len(P) // 3):
                x, y, z = P[vi * 3:vi * 3 + 3]
                nx, ny, nz = NR[vi * 3:vi * 3 + 3]
                if GJ is not None and W is not None:
                    X = Y = Z = NXv = NYv = NZv = 0.0
                    for k in range(4):
                        w = W[vi * 4 + k]
                        if w <= 0:
                            continue
                        m = GJ[int(J[vi * 4 + k])]
                        X += w * (m[0] * x + m[1] * y + m[2] * z + m[3])
                        Y += w * (m[4] * x + m[5] * y + m[6] * z + m[7])
                        Z += w * (m[8] * x + m[9] * y + m[10] * z + m[11])
                        NXv += w * (m[0] * nx + m[1] * ny + m[2] * nz)
                        NYv += w * (m[4] * nx + m[5] * ny + m[6] * nz)
                        NZv += w * (m[8] * nx + m[9] * ny + m[10] * nz)
                    x, y, z, nx, ny, nz = X, Y, Z, NXv, NYv, NZv
                if GJ is not None:
                    # world = sum w * G_j * IBM * v (G_mesh cancel dlm three.js-style skinning)
                    PX.append(x); PY.append(y); PZ.append(z)
                    NX.append(nx); NY.append(ny); NZ.append(nz)
                else:
                    PX.append(GM[0] * x + GM[1] * y + GM[2] * z + GM[3])
                    PY.append(GM[4] * x + GM[5] * y + GM[6] * z + GM[7])
                    PZ.append(GM[8] * x + GM[9] * y + GM[10] * z + GM[11])
                    NX.append(GM[0] * nx + GM[1] * ny + GM[2] * nz)
                    NY.append(GM[4] * nx + GM[5] * ny + GM[6] * nz)
                    NZ.append(GM[8] * nx + GM[9] * ny + GM[10] * nz)
                UU.append(U[vi * 2])
                VV.append(U[vi * 2 + 1])
            for t in range(0, len(idx), 3):
                faces.append((src, base + idx[t], base + idx[t + 1], base + idx[t + 2]))

    print('posed bounds X',[round(min(PX),2),round(max(PX),2)],'Y',[round(min(PY),2),round(max(PY),2)],'Z',[round(min(PZ),2),round(max(PZ),2)])
    W2, H2 = 480, 640
    mnx, mxx = min(PX), max(PX)
    mny, mxy = min(PY), max(PY)
    sc2 = max(mxx - mnx, mxy - mny) or 1
    cx, cy = (mnx + mxx) / 2, (mny + mxy) / 2
    fb = [(10, 20, 13)] * (W2 * H2)
    depth = [-1e18] * (W2 * H2)
    L = (0.45, 0.6, 0.65)
    ln = math.sqrt(sum(v * v for v in L))
    L = [v / ln for v in L]

    def prj(vi):
        return ((0.5 + ((PX[vi] - cx) / sc2) * 0.9) * W2,
                (0.5 - ((PY[vi] - cy) / sc2) * 0.92) * H2, PZ[vi])

    for src, a, b, c in faces:
        A, B, C = prj(a), prj(b), prj(c)
        aS = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
        if abs(aS) < 1e-9:
            continue
        inv = 1.0 / aS
        minx = int(max(0, min(A[0], B[0], C[0])))
        maxx = int(min(W2 - 1, max(A[0], B[0], C[0])))
        miny = int(max(0, min(A[1], B[1], C[1])))
        maxy = int(min(H2 - 1, max(A[1], B[1], C[1])))
        for py in range(miny, maxy + 1):
            for px in range(minx, maxx + 1):
                w0 = ((B[0] - px) * (C[1] - py) - (B[1] - py) * (C[0] - px)) * inv
                w1 = ((C[0] - px) * (A[1] - py) - (C[1] - py) * (A[0] - px)) * inv
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                z = w0 * A[2] + w1 * B[2] + w2 * C[2]
                o2 = py * W2 + px
                if z <= depth[o2]:
                    continue
                depth[o2] = z
                col = (200, 200, 200)
                if src is not None:
                    w, h, raw = imgs[src]
                    u = w0 * UU[a] + w1 * UU[b] + w2 * UU[c]
                    v = w0 * VV[a] + w1 * VV[b] + w2 * VV[c]
                    x = min(w - 1, max(0, int(u * w)))
                    y = min(h - 1, max(0, int(v * h)))
                    oo = (y * w + x) * 4
                    if raw[oo + 3] / 255 < 0.5:
                        continue
                    col = (raw[oo], raw[oo + 1], raw[oo + 2])
                n = (w0 * NX[a] + w1 * NX[b] + w2 * NX[c],
                     w0 * NY[a] + w1 * NY[b] + w2 * NY[c],
                     w0 * NZ[a] + w1 * NZ[b] + w2 * NZ[c])
                nl = math.sqrt(sum(q * q for q in n)) or 1
                ndl = (n[0] * L[0] + n[1] * L[1] + n[2] * L[2]) / nl
                br = 1.05 if ndl > 0.6 else 0.9 if ndl > 0.15 else 0.75 if ndl > -0.1 else 0.6
                fb[o2] = tuple(int(min(255, cc * br)) for cc in col)
    with open('/tmp/glb.ppm', 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (W2, H2))
        for c2 in fb:
            f.write(bytes(c2))
    subprocess.run(['convert', '/tmp/glb.ppm', outp], check=True)
    print('pose render:', outp, '| anim', ai, g['animations'][ai]['name'], 't=', tsec,
          '| verts', len(PX), 'tris', len(faces))


if __name__ == '__main__':
    main()
