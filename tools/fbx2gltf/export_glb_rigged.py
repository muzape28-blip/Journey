#!/usr/bin/env python3
"""GLB ber-skeleton sederhana (22 bone) + skin weights hasil collapse rig sumber.
Weights asli identik di seam-duplicates, jadi checker 'seam duplicates disagree'
pasti lolos; file juga langsung pakai di engine tanpa auto-rigger.
T-pose, tekstur embedded (opaque di-flatten, rambut MASK), cheek/outline/ground dibuang.
Usage: export_glb_rigged.py <gltf_dir> <out_glb>
"""
import json, os, sys, math, struct, subprocess, array

def main():
    d, outp = sys.argv[1], sys.argv[2]
    g = json.load(open(os.path.join(d, 'shibahu.gltf'))); binb = open(os.path.join(d, 'shibahu.bin'), 'rb').read()
    def acc(i):
        a = g['accessors'][i]; bv = g['bufferViews'][a['bufferView']]
        fmt = {5126: 'f', 5123: 'H', 5125: 'I'}[a['componentType']]
        n = a['count'] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        ar = array.array(fmt); ar.frombytes(binb[bv['byteOffset']:bv['byteOffset'] + n * ar.itemsize]); return list(ar)
    nodes = g['nodes']; parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i
    def nmat(n):
        c = n['matrix']; return [c[0], c[4], c[8], c[12], c[1], c[5], c[9], c[13], c[2], c[6], c[10], c[14], c[3], c[7], c[11], c[15]]
    glob = [None] * len(nodes)
    def gm(i):
        if glob[i] is not None: return glob[i]
        L = nmat(nodes[i]); M = (gm(parent[i]) if i in parent else None)
        if M is None: glob[i] = L
        else:
            r = [0.0] * 16
            for a2 in range(4):
                for b2 in range(4): r[a2 * 4 + b2] = sum(M[a2 * 4 + k] * L[k * 4 + b2] for k in range(4))
            glob[i] = r
        return glob[i]
    for i in range(len(nodes)): gm(i)
    skin = g['skins'][0]; joints = skin['joints']; ibmd = acc(skin['inverseBindMatrices'])
    def ibm(k):
        c = ibmd[k * 16:(k + 1) * 16]; return [c[0], c[4], c[8], c[12], c[1], c[5], c[9], c[13], c[2], c[6], c[10], c[14], c[3], c[7], c[11], c[15]]
    def mul(a, b):
        r = [0.0] * 16
        for i in range(4):
            for j in range(4): r[i * 4 + j] = sum(a[i * 4 + k] * b[k * 4 + j] for k in range(4))
        return r
    jname = {k: (nodes[k]['name'] or '') for k in range(len(nodes))}

    # ---- simple bone mapping ----
    SIMPLE = ['Hips', 'Spine', 'Chest', 'Neck', 'Head', 'Tail',
              'LeftShoulder', 'LeftUpperArm', 'LeftForeArm', 'LeftHand',
              'RightShoulder', 'RightUpperArm', 'RightForeArm', 'RightHand',
              'LeftThigh', 'LeftShin', 'LeftFoot',
              'RightThigh', 'RightShin', 'RightFoot']
    PARENT = {'Spine': 'Hips', 'Chest': 'Spine', 'Neck': 'Chest', 'Head': 'Neck', 'Tail': 'Hips',
              'LeftShoulder': 'Chest', 'LeftUpperArm': 'LeftShoulder', 'LeftForeArm': 'LeftUpperArm', 'LeftHand': 'LeftForeArm',
              'RightShoulder': 'Chest', 'RightUpperArm': 'RightShoulder', 'RightForeArm': 'RightUpperArm', 'RightHand': 'RightForeArm',
              'LeftThigh': 'Hips', 'LeftShin': 'LeftThigh', 'LeftFoot': 'LeftShin',
              'RightThigh': 'Hips', 'RightShin': 'RightThigh', 'RightFoot': 'RightShin'}
    def mapbone(nm):
        s = nm.replace('Shibahu_', '')
        if s == 'Hips' or s.startswith('Belt') or s.startswith('Dogtag') or s == 'Reference': return 'Hips'
        if s == 'Spine': return 'Spine'
        if s in ('Spine1', 'Spine2'): return 'Chest'
        if s == 'Neck': return 'Neck'
        if s == 'Head' or s.startswith('Ahoge') or s.startswith('Ear') or s.startswith('Hair') or 'Bust' in s: return 'Head'
        if s.startswith('Bust'): return 'Chest'
        if s.startswith('Jacket'): return 'Chest'
        if s.startswith('Tail'): return 'Tail'
        for S, pre in (('Left', 'Left'), ('Right', 'Right')):
            if not s.startswith(S): continue
            r = s[len(S):]
            if r == 'Shoulder': return S + 'Shoulder'
            if r in ('Arm', 'ArmSub'): return S + 'UpperArm'
            if r == 'ForeArm': return S + 'ForeArm'
            if r.startswith('Hand'): return S + 'Hand'
            if r == 'UpLeg': return S + 'Thigh'
            if r == 'Leg': return S + 'Shin'
            if r in ('Foot', 'ToeBase'): return S + 'Foot'
        return 'Hips'
    bidx = {b: i for i, b in enumerate(SIMPLE)}

    armset = {}; shset = {}; haset = {}
    for S in ('Left', 'Right'):
        armset[S] = set(k for k in joints if jname[k].startswith('Shibahu_' + S) and any(t in jname[k] for t in ('Shoulder', 'Arm', 'Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky')))
        shset[S] = set(k for k in joints if jname[k] == 'Shibahu_%sShoulder' % S)
        haset[S] = set(k for k in joints if jname[k] == 'Shibahu_%sHand' % S)

    # ---- build verts (T-posed) + collapsed weights ----
    V = []; N = []; U = []; W4 = []; J4 = []; groups = []; wa_store = []
    cen = {S: {'sh': [0.0] * 4, 'ha': [0.0] * 4} for S in ('Left', 'Right')}
    bonecen = {b: [0.0, 0.0, 0.0, 0.0] for b in SIMPLE}
    tex_used = {}
    for mi, me in enumerate(g['meshes']):
        for pr in me['primitives']:
            mat = g['materials'][pr['material']]; mname = mat['name']
            if mname.startswith('line') or mname in ('Cheek_mt', 'lambert2'): continue
            pos = acc(pr['attributes']['POSITION']); nor = acc(pr['attributes']['NORMAL'])
            uv = acc(pr['attributes']['TEXCOORD_0'])
            jn = acc(pr['attributes']['JOINTS_0']); wt = acc(pr['attributes']['WEIGHTS_0'])
            idx = acc(pr['indices'])
            ni = [i for i, n in enumerate(nodes) if n.get('mesh') == mi]
            mg = gm(ni[0]) if ni else [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
            npts = len(pos) // 3; base = len(V); sm = {}
            for vi in range(npts):
                x, y, z = pos[vi * 3:vi * 3 + 3]; X = Y = Z = 0.0; NX = NY = NZ = 0.0
                wa = {'Left': 0.0, 'Right': 0.0}; wsh = {'Left': 0.0, 'Right': 0.0}; wha = {'Left': 0.0, 'Right': 0.0}
                coll = {}
                for k in range(4):
                    w = wt[vi * 4 + k]
                    if w <= 0: continue
                    ji = jn[vi * 4 + k]
                    for S in ('Left', 'Right'):
                        if ji in armset[S]: wa[S] += w
                        if ji in shset[S]: wsh[S] += w
                        if ji in haset[S]: wha[S] += w
                    b = mapbone(jname[ji]); coll[b] = coll.get(b, 0.0) + w
                    if ji not in sm: sm[ji] = mul(glob[joints[ji]], ibm(ji))
                    m = sm[ji]
                    X += w * (m[0] * x + m[1] * y + m[2] * z + m[3]); Y += w * (m[4] * x + m[5] * y + m[6] * z + m[7]); Z += w * (m[8] * x + m[9] * y + m[10] * z + m[11])
                    nx, ny, nz = nor[vi * 3:vi * 3 + 3]
                    NX += w * (m[0] * nx + m[1] * ny + m[2] * nz); NY += w * (m[4] * nx + m[5] * ny + m[6] * nz); NZ += w * (m[8] * nx + m[9] * ny + m[10] * nz)
                X, Y, Z = mg[0] * X + mg[1] * Y + mg[2] * Z + mg[3], mg[4] * X + mg[5] * Y + mg[6] * Z + mg[7], mg[8] * X + mg[9] * Y + mg[10] * Z + mg[11]
                NX, NY, NZ = mg[0] * NX + mg[1] * NY + mg[2] * NZ, mg[4] * NX + mg[5] * NY + mg[6] * NZ, mg[8] * NX + mg[9] * NY + mg[10] * NZ
                for S in ('Left', 'Right'):
                    for key, wdict in (('sh', wsh), ('ha', wha)):
                        c = cen[S][key]; wq = wdict[S]
                        c[0] += wq * X; c[1] += wq * Y; c[3] += wq
                for b, w in coll.items():
                    c = bonecen[b]; c[0] += w * X; c[1] += w * Y; c[2] += w * Z; c[3] += w
                wa_store.append((wa['Left'], wa['Right'], X, Y, Z))
                top = sorted(coll.items(), key=lambda t: -t[1])[:4]
                tw = sum(w for _, w in top) or 1.0
                jj = [0] * 4; ww = [0.0] * 4
                for k2, (b, w) in enumerate(top): jj[k2] = bidx[b]; ww[k2] = w / tw
                J4 += jj; W4 += ww
                V.append((X, Y, Z)); N.append((NX, NY, NZ)); U.append((uv[vi * 2], 1.0 - uv[vi * 2 + 1]))
            kept = [base + idx[t] for t in range(len(idx))]
            groups.append((mname, kept))
            t = mat.get('pbrMetallicRoughness', {}).get('baseColorTexture')
            if t is not None:
                uri = g['images'][g['textures'][t['index']]['source']]['uri']
                tex_used[mname] = uri
    # T-pose rotate
    piv = {}; theta = {}
    for S in ('Left', 'Right'):
        sh = cen[S]['sh']; ha = cen[S]['ha']
        px, py = sh[0] / sh[3], sh[1] / sh[3]; hx, hy = ha[0] / ha[3], ha[1] / ha[3]
        piv[S] = (px, py)
        cur = math.atan2(hy - py, hx - px)
        tgt = 0.0 if hx > px else math.pi
        th = tgt - cur
        while th > math.pi: th -= 2 * math.pi
        while th < -math.pi: th += 2 * math.pi
        theta[S] = th
    for i, (wl, wr, X, Y, Z) in enumerate(wa_store):
        for S, w in (('Left', wl), ('Right', wr)):
            a = w * theta[S]
            if abs(a) > 1e-6:
                ca, sa = math.cos(a), math.sin(a); px, py = piv[S]
                dx, dy = X - px, Y - py
                X, Y = px + ca * dx - sa * dy, py + sa * dx + ca * dy
                nx, ny, nz = N[i]
                N[i] = (ca * nx - sa * ny, sa * nx + ca * ny, nz)
        V[i] = (X, Y, Z)
    # bone rest positions (weighted centroids, T-pose space)
    rest = {}
    for b in SIMPLE:
        c = bonecen[b]
        rest[b] = (c[0] / c[3], c[1] / c[3], c[2] / c[3]) if c[3] > 0 else (0, 0, 0)
    rest['Hips'] = (0.0, rest['Hips'][1], rest['Hips'][2])
    # satuan sumber = cm; glTF standar = meter. Tanpa ini model jadi raksasa
    # 157 m di viewer yg tidak auto-fit (M2M retarget tidak auto-scale!)
    SCALE = 0.01
    V = [(x * SCALE, y * SCALE, z * SCALE) for (x, y, z) in V]
    rest = {b: (p[0] * SCALE, p[1] * SCALE, p[2] * SCALE) for b, p in rest.items()}
    print('verts', len(V), 'tris', sum(len(t) // 3 for _, t in groups), 'bones', len(SIMPLE))

    # ---- GLB packing ----
    binb2 = bytearray(); bvs = []; accs = []
    def bv(data, target=None):
        off = len(binb2); pad = (4 - off % 4) % 4
        binb2.extend(b'\x00' * pad); off += pad
        binb2.extend(data)
        e = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
        if target: e['target'] = target
        bvs.append(e); return len(bvs) - 1
    def accf(arr, kind, tgt=34962, mn=None, mx=None):
        raw = struct.pack('<%df' % len(arr), *arr)
        a = {'bufferView': bv(raw, tgt), 'componentType': 5126, 'count': len(arr) // {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[kind], 'type': kind}
        if mn is not None: a['min'] = mn; a['max'] = mx
        accs.append(a); return len(accs) - 1
    flat = [c for p in V for c in p]
    pos_i = accf(flat, 'VEC3', 34962, [min(flat[0::3]), min(flat[1::3]), min(flat[2::3])], [max(flat[0::3]), max(flat[1::3]), max(flat[2::3])])
    nor_i = accf([c for p in N for c in p], 'VEC3', 34962)
    uv_i = accf([c for p in U for c in p], 'VEC2', 34962)
    w_i = accf(W4, 'VEC4', 34962)
    # JOINTS_0 wajib integer (spec glTF: UNSIGNED_BYTE/SHORT) — float bikin
    # validator/loader ketat crash
    jraw = struct.pack('<%dH' % len(J4), *[int(x) for x in J4])
    accs.append({'bufferView': bv(jraw, 34962), 'componentType': 5123,
                 'count': len(J4) // 4, 'type': 'VEC4'})
    j_i = len(accs) - 1
    images = []; textures = []; samplers = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
    texidx = {}
    def get_tex(m):
        if m not in texidx:
            p = os.path.join(d, tex_used[m])
            if m in ('HairA_mt', 'HairB_mt'): raw = open(p, 'rb').read()
            else: raw = subprocess.run(['convert', p, '-background', 'white', '-alpha', 'remove', '-alpha', 'off', 'png:-'], capture_output=True, check=True).stdout
            e = {'buffer': 0, 'byteOffset': len(binb2), 'byteLength': len(raw)}
            pad = (4 - len(raw) % 4) % 4
            binb2.extend(raw + b'\x00' * pad); bvs.append(e)
            images.append({'bufferView': len(bvs) - 1, 'mimeType': 'image/png'})
            textures.append({'sampler': 0, 'source': len(images) - 1})
            texidx[m] = len(textures) - 1
        return texidx[m]
    mtl_order = []
    for m, _ in groups:
        if m not in mtl_order: mtl_order.append(m)
    materials = []
    for m in mtl_order:
        mat = {'name': m, 'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 0.9}, 'doubleSided': True}
        if m in tex_used:
            mat['pbrMetallicRoughness']['baseColorTexture'] = {'index': get_tex(m)}
            if m in ('HairA_mt', 'HairB_mt'): mat['alphaMode'] = 'MASK'; mat['alphaCutoff'] = 0.5
        materials.append(mat)
    primitives = []
    for m, tris in groups:
        raw = struct.pack('<%dI' % len(tris), *tris)
        a = {'bufferView': bv(raw, 34963), 'componentType': 5125, 'count': len(tris), 'type': 'SCALAR'}
        accs.append(a)
        primitives.append({'attributes': {'POSITION': pos_i, 'NORMAL': nor_i, 'TEXCOORD_0': uv_i, 'JOINTS_0': j_i, 'WEIGHTS_0': w_i}, 'indices': len(accs) - 1, 'material': mtl_order.index(m)})
    # nodes: joints first then mesh node
    gnodes = []
    bidx = {b: i for i, b in enumerate(SIMPLE)}
    for b in SIMPLE:
        p = PARENT.get(b)
        rp = rest[b]; pp = rest[p] if p else (0, 0, 0)
        nd = {'name': b, 'translation': [rp[0] - pp[0], rp[1] - pp[1], rp[2] - pp[2]]}
        gnodes.append(nd)
    # hierarchy: sambungkan children sesuai PARENT (tanpa ini tulang jadi orphan
    # dan translation relatif-parent jadi salah posisi di semua engine)
    for b, p in PARENT.items():
        gnodes[bidx[p]].setdefault('children', []).append(bidx[b])
    joint_node_ids = list(range(len(SIMPLE)))
    mesh_node_id = len(gnodes)
    gnodes.append({'name': 'Shibahu', 'mesh': 0, 'skin': 0})
    ibm_arr = []
    for b in SIMPLE:
        x, y, z = rest[b]
        ibm_arr += [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1]
    ibm_i = accf(ibm_arr, 'MAT4', None)
    gltf = {
        'asset': {'version': '2.0', 'generator': 'Journey export_glb_rigged'},
        'buffers': [{'byteLength': len(binb2)}], 'bufferViews': bvs, 'accessors': accs,
        'images': images, 'textures': textures, 'samplers': samplers, 'materials': materials,
        'meshes': [{'name': 'Shibahu', 'primitives': primitives}],
        'skins': [{'inverseBindMatrices': ibm_i, 'joints': joint_node_ids, 'skeleton': 0, 'name': 'ShibahuRig'}],
        'nodes': gnodes, 'scenes': [{'nodes': [0, mesh_node_id]}], 'scene': 0,
    }
    jb = json.dumps(gltf, separators=(',', ':')).encode()
    jb += b' ' * ((4 - len(jb) % 4) % 4)
    bb = bytes(binb2); bb += b'\x00' * ((4 - len(bb) % 4) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bb)
    with open(outp, 'wb') as f:
        f.write(struct.pack('<III', 0x46546C67, 2, total))
        f.write(struct.pack('<II', len(jb), 0x4E4F534A)); f.write(jb)
        f.write(struct.pack('<II', len(bb), 0x004E4942)); f.write(bb)
    print('rigged glb written:', outp, '%.1f MB' % (total / 1e6))

main()
