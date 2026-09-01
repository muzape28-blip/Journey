#!/usr/bin/env python3
"""Round-trip QA: parse a binary FBX with fbx2gltf's real FBX parser,
extract embedded textures (Video Content), rasterize front view -> PNG.
Usage: verify_fbx_render.py <fbx> <out_png>
"""
import sys, struct, math, subprocess, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbx2gltf import parse, find, child, clean

def main():
    fbxp, outp = sys.argv[1], sys.argv[2]
    ver, root = parse(fbxp)
    objs = find(root, 'Objects'); cons = find(root, 'Connections')
    mats = {}; vids = {}; texs = {}
    for c in objs['c']:
        if c['n'] == 'Material': mats[c['p'][0]] = clean(c['p'][1])
        elif c['n'] == 'Video':
            ct = child(c, 'Content'); vids[clean(c['p'][1])] = ct['p'][0] if ct else None
        elif c['n'] == 'Texture':
            media = child(c, 'Media'); texs[c['p'][0]] = clean(media['p'][0]) if media else None
    mat_of_model = []; tex_of_mat = {}
    for c in cons['c']:
        if c['p'][0] == 'OO':
            dst = c['p'][2]
            if dst in (2000,) and c['p'][1] in mats: mat_of_model.append(c['p'][1])
            if len(c['p']) > 3 and c['p'][3] == 'DiffuseColor': tex_of_mat[c['p'][2]] = c['p'][1]
    matname2tex = {}
    for mid in mat_of_model:
        if mid in tex_of_mat: matname2tex[mats[mid]] = texs[tex_of_mat[mid]]
    g = [c for c in objs['c'] if c['n'] == 'Geometry'][0]
    V = list(child(g, 'Vertices')['p'][0]); pvi = list(child(g, 'PolygonVertexIndex')['p'][0])
    nrm = list(child(child(g, 'LayerElementNormal'), 'Normals')['p'][0])
    lu = child(g, 'LayerElementUV'); UV = list(child(lu, 'UV')['p'][0]); UVI = list(child(lu, 'UVIndex')['p'][0])
    MAT = list(child(child(g, 'LayerElementMaterial'), 'Materials')['p'][0])
    polys = []; i = 0; poly = []
    while i < len(pvi):
        v = pvi[i]; poly.append(v if v >= 0 else ~v); i += 1
        if pvi[i - 1] < 0: polys.append(poly); poly = []
    faces = []; corner = 0
    for pi, poly in enumerate(polys):
        mname = mats[mat_of_model[MAT[pi]]]
        for k in range(len(poly) - 2):
            faces.append((mname, [poly[0], poly[k + 1], poly[k + 2]], [corner, corner + 1, corner + 2])); corner += 3
    texcache = {}
    def load(mname):
        key = matname2tex[mname]
        if key not in texcache:
            raw = vids[key]
            open('/tmp/emb.png', 'wb').write(raw)
            d = subprocess.run(['convert', '/tmp/emb.png', '-depth', '8', 'rgba:-'], capture_output=True, check=True).stdout
            w, hh = struct.unpack('>II', raw[16:24])
            texcache[key] = (w, hh, d)
        return texcache[key]
    W, H = 480, 640
    xs = V[0::3]; ys = V[1::3]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    sc = max(mxx - mnx, mxy - mny); cx = (mnx + mxx) / 2; cy = (mny + mxy) / 2
    fb = [(10, 20, 13)] * (W * H); depth = [-1e18] * (W * H)
    L = (0.45, 0.6, 0.65); ln = math.sqrt(sum(v * v for v in L)); L = [v / ln for v in L]
    def pr(vi): return (0.5 + ((V[vi * 3] - cx) / sc) * 0.9) * W, (0.5 - ((V[vi * 3 + 1] - cy) / sc) * 0.92) * H, V[vi * 3 + 2]
    for mname, tri, co in faces:
        A, B, C = [pr(v) for v in tri]
        aS = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
        if abs(aS) < 1e-9: continue
        inv = 1.0 / aS
        minx = int(max(0, min(A[0], B[0], C[0]))); maxx = int(min(W - 1, max(A[0], B[0], C[0])))
        miny = int(max(0, min(A[1], B[1], C[1]))); maxy = int(min(H - 1, max(A[1], B[1], C[1])))
        hastex = mname in matname2tex
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
                if hastex:
                    w, h, raw = load(mname)
                    u0, v0 = UV[UVI[co[0]] * 2], UV[UVI[co[0]] * 2 + 1]; u1, v1 = UV[UVI[co[1]] * 2], UV[UVI[co[1]] * 2 + 1]; u2, v2 = UV[UVI[co[2]] * 2], UV[UVI[co[2]] * 2 + 1]
                    u = w0 * u0 + w1 * u1 + w2 * u2; v = w0 * v0 + w1 * v1 + w2 * v2
                    x = min(w - 1, max(0, int(u * w))); y = min(h - 1, max(0, int(v * h))); oo = (y * w + x) * 4
                    if raw[oo + 3] / 255 < 0.5: continue
                    col = (raw[oo], raw[oo + 1], raw[oo + 2])
                n = (w0 * nrm[co[0] * 3] + w1 * nrm[co[1] * 3] + w2 * nrm[co[2] * 3], w0 * nrm[co[0] * 3 + 1] + w1 * nrm[co[1] * 3 + 1] + w2 * nrm[co[2] * 3 + 1], w0 * nrm[co[0] * 3 + 2] + w1 * nrm[co[1] * 3 + 2] + w2 * nrm[co[2] * 3 + 2])
                nl = math.sqrt(sum(q * q for q in n)) or 1
                ndl = (n[0] * L[0] + n[1] * L[1] + n[2] * L[2]) / nl
                b = 1.05 if ndl > 0.6 else 0.9 if ndl > 0.15 else 0.75 if ndl > -0.1 else 0.6
                fb[o] = tuple(int(min(255, c * b)) for c in col)
    with open('/tmp/fbxcheck.ppm', 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (W, H))
        for r, g2, b in fb: f.write(bytes((r, g2, b)))
    subprocess.run(['convert', '/tmp/fbxcheck.ppm', outp], check=True)
    print('round-trip render OK; polys', len(polys), '->', outp)

main()
