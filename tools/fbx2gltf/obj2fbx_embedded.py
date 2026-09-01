#!/usr/bin/env python3
"""Convert our OBJ+MTL into ONE binary FBX 7.4 (=2014 SDK, batas Mixamo) with
textures EMBEDDED (Video node Content = raw PNG). Satu file untuk Mixamo.
Usage:
  obj2fbx_embedded.py make <obj> <mtl> <texdir> <out.fbx>
  obj2fbx_embedded.py verify <fbx> <out.png>   (baca balik + render dari konten embedded)
"""
import struct, sys, os, math, subprocess

MAGIC = b'Kaydara FBX Binary  \x00'
VER = 7400

# ---------- property encoders ----------
def pI(v): return b'I' + struct.pack('<i', v)
def pL(v): return b'L' + struct.pack('<q', v)
def pD(v): return b'D' + struct.pack('<d', v)
def pC(v): return b'C' + struct.pack('<B', v)
def pS(s):
    b = s.encode('utf-8'); return b'S' + struct.pack('<I', len(b)) + b
def pR(b): return b'R' + struct.pack('<I', len(b)) + b
def arrD(vals):
    raw = struct.pack('<%dd' % len(vals), *vals)
    return b'd' + struct.pack('<III', len(vals), 0, len(raw)) + raw
def arrI(vals):
    raw = struct.pack('<%di' % len(vals), *vals)
    return b'i' + struct.pack('<III', len(vals), 0, len(raw)) + raw

def N(name, props, kids=None): return (name, props, kids or [])

def ser(n, base):
    name, props, kids = n
    nb = name.encode('utf-8'); body = b''.join(props)
    headsize = 10 + len(nb)
    cb = b''; cbase = base + headsize + len(body)
    for k in kids:
        kb = ser(k, cbase); cbase += len(kb); cb += kb
    if kids: cb += b'\x00' * 13
    total = base + headsize + len(body) + len(cb)
    return struct.pack('<IBI', total, len(props), len(body)) + struct.pack('<B', len(nb)) + nb + body + cb

def P(*vals): return N('P', list(vals))

# ---------- make ----------
def make(objp, mtlp, texdir, outp):
    V = []; VT = []; VN = []; groups = []; cur = None
    for line in open(objp):
        t = line.split()
        if not t: continue
        if t[0] == 'v': V += map(float, t[1:4])
        elif t[0] == 'vt': VT += map(float, t[1:3])
        elif t[0] == 'vn': VN += map(float, t[1:4])
        elif t[0] == 'usemtl': cur = t[1]
        elif t[0] == 'f':
            groups.append((cur, [tuple(map(int, x.split('/'))) for x in t[1:4]]))
    mtl = {}; cur = None
    for line in open(mtlp):
        t = line.split()
        if not t: continue
        if t[0] == 'newmtl': cur = t[1]; mtl[cur] = {}
        elif t[0] == 'map_Kd': mtl[cur]['map'] = t[1]
    V = list(V); VT = list(VT); VN = list(VN)
    matnames = []
    for m, _ in groups:
        if m not in matnames: matnames.append(m)
    nv = len(V) // 3
    pvi = []; nrm = []; uvs = []; uvi = []; mats = []
    for m, ids in groups:
        for (vi, ti, ni) in ids:
            pvi.append(vi - 1)
            nrm += VN[(ni - 1) * 3:(ni - 1) * 3 + 3]
            u = VT[(ti - 1) * 2]; v = 1.0 - VT[(ti - 1) * 2 + 1]
            uvs += [u, v]; uvi.append(len(uvs) // 2 - 1)
        mats += [matnames.index(m)] * (len(ids) // 3)
    GEO, MOD = 1000, 2000
    mat_ids = {m: 3000 + i for i, m in enumerate(matnames)}
    texs = {m: os.path.basename(mtl[m]['map']) for m in matnames if m in mtl and 'map' in mtl[m]}
    tex_ids = {m: 4000 + i for i, m in enumerate(matnames) if m in texs}
    vid_ids = {m: 5000 + i for i, m in enumerate(matnames) if m in texs}

    geo = N('Geometry', [pL(GEO), pS('Geometry::Shibahu'), pS('Mesh')], [
        N('Vertices', [arrD(V)]),
        N('PolygonVertexIndex', [arrI(pvi)]),
        N('LayerElementNormal', [pI(0)], [
            N('Version', [pI(101)]), N('Name', [pS('')]),
            N('MappingInformationType', [pS('ByPolygonVertex')]),
            N('ReferenceInformationType', [pS('Direct')]),
            N('Normals', [arrD(nrm)])]),
        N('LayerElementUV', [pI(0)], [
            N('Version', [pI(101)]), N('Name', [pS('map1')]),
            N('MappingInformationType', [pS('ByPolygonVertex')]),
            N('ReferenceInformationType', [pS('IndexToDirect')]),
            N('UV', [arrD(uvs)]), N('UVIndex', [arrI(uvi)])]),
        N('LayerElementMaterial', [pI(0)], [
            N('Version', [pI(101)]), N('Name', [pS('')]),
            N('MappingInformationType', [pS('ByPolygon')]),
            N('ReferenceInformationType', [pS('IndexToDirect')]),
            N('Materials', [arrI(mats)])]),
        N('Layer', [pI(0)], [
            N('Version', [pI(100)]), N('Name', [pS('')]),
            N('LayerElement', [pS('LayerElementNormal'), pI(0)]),
            N('LayerElement', [pS('LayerElementMaterial'), pI(0)]),
            N('LayerElement', [pS('LayerElementUV'), pI(0)])])])
    mod = N('Model', [pL(MOD), pS('Model::Shibahu'), pS('Mesh')], [
        N('Version', [pI(232)]),
        N('Properties70', [], [
            P(pS('Lcl Translation'), pS('Lcl Translation'), pS(''), pS('A'), pD(0), pD(0), pD(0)),
            P(pS('Lcl Rotation'), pS('Lcl Rotation'), pS(''), pS('A'), pD(0), pD(0), pD(0)),
            P(pS('Lcl Scaling'), pS('Lcl Scaling'), pS(''), pS('A'), pD(1), pD(1), pD(1))]),
        N('Shading', [pC(1)]), N('Culling', [pS('CullingOff')])])
    matkids = []
    for m in matnames:
        matkids.append(N('Material', [pL(mat_ids[m]), pS('Material::%s' % m), pS('')], [
            N('Version', [pI(102)]), N('ShadingModel', [pS('phong')]), N('MultiLayer', [pC(0)]),
            N('Properties70', [], [P(pS('DiffuseColor'), pS('Color'), pS(''), pS('A'), pD(0.8), pD(0.8), pD(0.8))])]))
    texkids = []
    for m in matnames:
        if m not in texs: continue
        fn = texs[m]
        texkids.append(N('Texture', [pL(tex_ids[m]), pS('Texture::%s_map' % m), pS('')], [
            N('Type', [pS('TextureVideoClip')]), N('Version', [pI(202)]),
            N('TextureName', [pS('%s_map' % m)]), N('Media', [pS('Video::%s_vid' % m)]),
            N('FileName', [pS(fn)]), N('RelativeFilename', [pS(fn)]),
            N('ModelUVTranslation', [pD(0), pD(0)]), N('ModelUVScaling', [pD(1), pD(1)]),
            N('Texture_Alpha_Source', [pS('None')]), N('Cropping', [pI(0), pI(0), pI(0), pI(0)])]))
        data = open(os.path.join(texdir, fn), 'rb').read()
        texkids.append(N('Video', [pL(vid_ids[m]), pS('Video::%s_vid' % m), pS('Clip')], [
            N('Type', [pS('Clip')]), N('UseMipMap', [pI(0)]),
            N('FileName', [pS(fn)]), N('RelativeFilename', [pS(fn)]),
            N('Content', [pR(data)])]))
    objs = N('Objects', [], [geo, mod] + matkids + texkids)
    conns = [N('C', [pS('OO'), pL(MOD), pL(0)]), N('C', [pS('OO'), pL(GEO), pL(MOD)])]
    for m in matnames:
        conns.append(N('C', [pS('OO'), pL(mat_ids[m]), pL(MOD)]))
        if m in texs:
            conns.append(N('C', [pS('OO'), pL(tex_ids[m]), pL(mat_ids[m]), pS('DiffuseColor')]))
            conns.append(N('C', [pS('OO'), pL(vid_ids[m]), pL(tex_ids[m])]))
    cons = N('Connections', [], conns)
    hdr = N('FBXHeaderExtension', [], [
        N('FBXHeaderVersion', [pI(1003)]), N('FBXVersion', [pI(VER)]),
        N('Creator', [pS('Journey obj2fbx_embedded')])])
    gs = N('GlobalSettings', [], [
        N('Version', [pI(1000)]),
        N('Properties70', [], [
            P(pS('UpAxis'), pS('int'), pS('Integer'), pS(''), pI(1)),
            P(pS('UpAxisSign'), pS('int'), pS('Integer'), pS(''), pI(1)),
            P(pS('FrontAxis'), pS('int'), pS('Integer'), pS(''), pI(2)),
            P(pS('FrontAxisSign'), pS('int'), pS('Integer'), pS(''), pI(1)),
            P(pS('CoordAxis'), pS('int'), pS('Integer'), pS(''), pI(0)),
            P(pS('CoordAxisSign'), pS('int'), pS('Integer'), pS(''), pI(1)),
            P(pS('UnitScaleFactor'), pS('double'), pS('Number'), pS(''), pD(1))])])
    docs = N('Documents', [], [N('Count', [pI(1)])])
    refs = N('References', [])
    roots = [hdr, gs, docs, refs, objs, cons]
    blob = MAGIC + struct.pack('<I', VER)
    base = len(blob)
    for r in roots:
        b = ser(r, base); base += len(b); blob += b
    blob += b'\x00' * 13 + b'\x00' * 120
    open(outp, 'wb').write(blob)
    print('wrote', outp, len(blob), 'bytes; verts', nv, 'tris', len(pvi) // 3, 'embedded', len(texs), 'textures')

# ---------- verify: parse binary back & render from embedded content ----------
def parse(fbxp):
    d = open(fbxp, 'rb').read()
    assert d[:len(MAGIC)] == MAGIC, 'bad magic'
    ver = struct.unpack_from('<I', d, len(MAGIC))[0]
    pos = len(MAGIC) + 4
    roots = []
    def props_at(p, n):
        out = []; e = p
        for _ in range(n):
            t = d[e]; e += 1
            if t == ord('I'): out.append(('I', struct.unpack_from('<i', d, e)[0])); e += 4
            elif t == ord('L'): out.append(('L', struct.unpack_from('<q', d, e)[0])); e += 8
            elif t == ord('F'): out.append(('F', struct.unpack_from('<f', d, e)[0])); e += 4
            elif t == ord('D'): out.append(('D', struct.unpack_from('<d', d, e)[0])); e += 8
            elif t == ord('C'): out.append(('C', d[e])); e += 1
            elif t == ord('Y'): out.append(('Y', struct.unpack_from('<h', d, e)[0])); e += 2
            elif t == ord('S'):
                l = struct.unpack_from('<I', d, e)[0]; out.append(('S', d[e + 4:e + 4 + l].decode('utf-8', 'replace'))); e += 4 + l
            elif t == ord('R'):
                l = struct.unpack_from('<I', d, e)[0]; out.append(('R', d[e + 4:e + 4 + l])); e += 4 + l
            elif t in (ord('i'), ord('l'), ord('f'), ord('d')):
                cnt, enc, comp = struct.unpack_from('<III', d, e)[0:3]; e += 12
                raw = d[e:e + comp]; e += comp
                if enc == 1:
                    import zlib as _z; raw = _z.decompress(raw)
                fmt = {'i': '<%di' % cnt, 'l': '<%dq' % cnt, 'f': '<%df' % cnt, 'd': '<%dd' % cnt}[chr(t)]
                out.append((chr(t), list(struct.unpack(fmt, raw))))
            else:
                raise Exception('bad prop type %r' % chr(t))
        return out, e
    def read_node(p):
        end, nprop, proplen = struct.unpack_from('<IBI', d, p)[0:3]
        nl = d[p + 9]; name = d[p + 10:p + 10 + nl].decode('utf-8', 'replace')
        pr, e = props_at(p + 10 + nl, nprop)
        assert e == p + 10 + nl + proplen, 'proplen mismatch in %s' % name
        kids = []
        while e < end:
            child_end = struct.unpack_from('<I', d, e)[0]
            if child_end == 0:
                e += 13; continue
            kids.append(read_node(e)[0]); e = child_end
        return (name, pr, kids), end
    while pos < len(d):
        end = struct.unpack_from('<I', d, pos)[0]
        if end == 0: break
        n, _ = read_node(pos); roots.append(n); pos = _
    return ver, roots

def find(roots, name):
    for n in roots:
        if n[0] == name: return n
    return None

def child(n, name):
    for c in n[2]:
        if c[0] == name: return c
    return None

def val(n, i=0):
    return n[1][i][1]

def verify(fbxp, outpng):
    ver, roots = parse(fbxp)
    objs = find(roots, 'Objects')
    geo = None; vids = {}
    mats_order = []
    for c in objs[2]:
        if c[0] == 'Geometry': geo = c
        if c[0] == 'Video':
            vids[val(child(c, 'FileName'))] = val(child(c, 'Content'))
        if c[0] == 'Material': mats_order.append(c[1][1][1].replace('Material::', ''))
    V = val(child(geo, 'Vertices'))
    pvi = val(child(geo, 'PolygonVertexIndex'))
    nrm = val(child(child(geo, 'LayerElementNormal'), 'Normals'))
    lu = child(geo, 'LayerElementUV'); uvs = val(child(lu, 'UV')); uvi = val(child(lu, 'UVIndex'))
    mats = val(child(child(geo, 'LayerElementMaterial'), 'Materials'))
    print('ver', ver, 'verts', len(V) // 3, 'pvi', len(pvi), 'mats', mats_order, 'embedded:', {k: len(v) for k, v in vids.items()})
    tex = {}
    for fn, raw in vids.items():
        assert raw[:8] == b'\x89PNG\r\n\x1a\n', fn
        w, h = struct.unpack('>II', raw[16:24])
        rgba = subprocess.run(['convert', '-', '-depth', '8', 'rgba:-'], input=raw, capture_output=True, check=True).stdout
        tex[fn] = (w, h, rgba)
    W, H = 640, 640
    xs = V[0::3]; ys = V[1::3]
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    sc = max(mxx - mnx, mxy - mny); cx = (mnx + mxx) / 2; cy = (mny + mxy) / 2
    fb = [(10, 20, 13)] * (W * H); depth = [-1e18] * (W * H)
    L = (0.45, 0.6, 0.65); lnl = math.sqrt(sum(v * v for v in L)); L = [v / lnl for v in L]
    def pr(i):
        return (0.5 + ((V[i * 3] - cx) / sc) * 0.95) * W, (0.5 - ((V[i * 3 + 1] - cy) / sc) * 0.95) * H, V[i * 3 + 2]
    def texfor(m):
        for k in tex:
            b = os.path.basename(k).lower()
            if (m == 'Body_mt' and 'body' in b) or (m == 'Face_mt' and 'face' in b) or (m == 'CosA_mt' and 'cosa' in b) or (m == 'CosB_mt' and 'cosb' in b) or (m == 'HairA_mt' and 'haira' in b) or (m == 'HairB_mt' and 'hairb' in b) or (m == 'Cheek_mt' and 'cheek' in b):
                return k
        return None
    tris = len(pvi) // 3
    for t in range(tris):
        ia, ib, ic = pvi[t * 3], pvi[t * 3 + 1], pvi[t * 3 + 2]
        A, B, C = pr(ia), pr(ib), pr(ic)
        aS = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
        if abs(aS) < 1e-9: continue
        inv = 1.0 / aS
        minx = int(max(0, min(A[0], B[0], C[0]))); maxx = int(min(W - 1, max(A[0], B[0], C[0])))
        miny = int(max(0, min(A[1], B[1], C[1]))); maxy = int(min(H - 1, max(A[1], B[1], C[1])))
        texf = texfor(mats_order[mats[t]])
        for py in range(miny, maxy + 1):
            for px in range(minx, maxx + 1):
                w0 = ((B[0] - px) * (C[1] - py) - (B[1] - py) * (C[0] - px)) * inv
                w1 = ((C[0] - px) * (A[1] - py) - (C[1] - py) * (A[0] - px)) * inv
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0: continue
                z = w0 * A[2] + w1 * B[2] + w2 * C[2]; o = py * W + px
                if z <= depth[o]: continue
                depth[o] = z
                ca, cb, cc = uvi[t * 3], uvi[t * 3 + 1], uvi[t * 3 + 2]
                u = w0 * uvs[ca * 2] + w1 * uvs[cb * 2] + w2 * uvs[cc * 2]
                v = w0 * uvs[ca * 2 + 1] + w1 * uvs[cb * 2 + 1] + w2 * uvs[cc * 2 + 1]
                if texf:
                    w, h, raw = tex[texf]
                    x = min(w - 1, max(0, int(u * w))); y = min(h - 1, max(0, int(v * h)))
                    oo = (y * w + x) * 4
                    col = (raw[oo], raw[oo + 1], raw[oo + 2]); al = raw[oo + 3] / 255
                    if al < 0.5: continue
                else:
                    col = (200, 200, 200)
                na = t * 9
                n = (w0 * nrm[na] + w1 * nrm[na + 3] + w2 * nrm[na + 6],
                     w0 * nrm[na + 1] + w1 * nrm[na + 4] + w2 * nrm[na + 7],
                     w0 * nrm[na + 2] + w1 * nrm[na + 5] + w2 * nrm[na + 8])
                nl2 = math.sqrt(sum(q * q for q in n)) or 1
                ndl = (n[0] * L[0] + n[1] * L[1] + n[2] * L[2]) / nl2
                b = 1.05 if ndl > 0.6 else 0.9 if ndl > 0.15 else 0.75 if ndl > -0.1 else 0.6
                fb[o] = tuple(int(min(255, q * b)) for q in col)
    with open('/tmp/fbxv.ppm', 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (W, H))
        for r, g2, b in fb: f.write(bytes((r, g2, b)))
    subprocess.run(['convert', '/tmp/fbxv.ppm', outpng], check=True)
    print('verify render ->', outpng)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'make':
        make(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        verify(sys.argv[2], sys.argv[3])
