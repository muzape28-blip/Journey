#!/usr/bin/env python3
"""Export skinned mesh for Mixamo, T-posed, world-space cm, facing +Z, no skeleton.
Variants:
  full = tail+cheek included (look lengkap), ground plane & outline shells removed
  lite = tail+cheek removed too (fallback bila auto-rigger menolak ekor)
Outputs: shibahu.obj/.mtl/.fbx (full), shibahu_lite.obj/.mtl, textures/,
         shibahu_mixamo.zip & shibahu_lite_mixamo.zip (obj+mtl+textures flat = upload ini ke Mixamo biar berwarna)
Usage: export_mixamo.py <gltf_dir> <out_dir>
"""
import json, os, sys, math, shutil, array, zipfile

SKIP_BASE = {'lambert2'}  # ground plane 2.5m: tidak pernah ikut (bukan bagian karakter)

def main():
    d = sys.argv[1]; out = sys.argv[2]
    os.makedirs(out, exist_ok=True); os.makedirs(os.path.join(out, 'textures'), exist_ok=True)
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
    tail_j = set(k for k in joints if 'Tail' in jname[k])
    arm_j = {}; sh_j = {}; ha_j = {}
    for S in ('Left', 'Right'):
        arm_j[S] = set(k for k in joints if jname[k].startswith('Shibahu_' + S) and any(t in jname[k] for t in ('Shoulder', 'Arm', 'Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky')))
        sh_j[S] = set(k for k in joints if jname[k] == 'Shibahu_%sShoulder' % S)
        ha_j[S] = set(k for k in joints if jname[k] == 'Shibahu_%sHand' % S)

    def build(lite):
        V = []; N = []; U = []; groups = []; tailw = []; wa_store = []
        cen = {S: {'sh': [0.0] * 4, 'ha': [0.0] * 4} for S in ('Left', 'Right')}
        tex_used = {}
        skip = set(SKIP_BASE)
        if lite: skip.add('Cheek_mt')
        for mi, me in enumerate(g['meshes']):
            for pr in me['primitives']:
                mat = g['materials'][pr['material']]; mname = mat['name']
                if mname.startswith('line') or mname in skip: continue
                pos = acc(pr['attributes']['POSITION']); nor = acc(pr['attributes']['NORMAL'])
                uv = acc(pr['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in pr['attributes'] else None
                jn = acc(pr['attributes']['JOINTS_0']); wt = acc(pr['attributes']['WEIGHTS_0'])
                idx = acc(pr['indices'])
                ni = [i for i, n in enumerate(nodes) if n.get('mesh') == mi]
                mg = gm(ni[0]) if ni else [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
                npts = len(pos) // 3; base = len(V); sm = {}
                for vi in range(npts):
                    x, y, z = pos[vi * 3:vi * 3 + 3]; X = Y = Z = 0.0; NX = NY = NZ = 0.0
                    tw = 0.0; wa = {'Left': 0.0, 'Right': 0.0}; wsh = {'Left': 0.0, 'Right': 0.0}; wha = {'Left': 0.0, 'Right': 0.0}
                    for k in range(4):
                        w = wt[vi * 4 + k]
                        if w <= 0: continue
                        ji = jn[vi * 4 + k]
                        if ji in tail_j: tw += w
                        for S in ('Left', 'Right'):
                            if ji in arm_j[S]: wa[S] += w
                            if ji in sh_j[S]: wsh[S] += w
                            if ji in ha_j[S]: wha[S] += w
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
                    wa_store.append((wa['Left'], wa['Right'])); tailw.append(tw)
                    if uv is not None: U.append((uv[vi * 2], 1.0 - uv[vi * 2 + 1]))
                    else: U.append((0.0, 0.0))
                    V.append((X, Y, Z)); N.append((NX, NY, NZ))
                kept = []
                for t in range(0, len(idx), 3):
                    a, b, c = idx[t], idx[t + 1], idx[t + 2]
                    if lite and tailw[a] > 0.5 and tailw[b] > 0.5 and tailw[c] > 0.5: continue
                    kept += [base + a, base + b, base + c]
                if kept:
                    groups.append((mname, kept))
                    t = mat.get('pbrMetallicRoughness', {}).get('baseColorTexture')
                    if t is not None:
                        uri = g['images'][g['textures'][t['index']]['source']]['uri']
                        tex_used[mname] = uri
                        shutil.copyfile(os.path.join(d, uri), os.path.join(out, 'textures', os.path.basename(uri)))
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
        for i, (wl, wr) in enumerate(wa_store):
            X, Y, Z = V[i]; NX, NY, NZ = N[i]
            for S, w in (('Left', wl), ('Right', wr)):
                a = w * theta[S]
                if abs(a) > 1e-6:
                    ca, sa = math.cos(a), math.sin(a); px, py = piv[S]
                    dx, dy = X - px, Y - py
                    X, Y = px + ca * dx - sa * dy, py + sa * dx + ca * dy
                    NX, NY = ca * NX - sa * NY, sa * NX + ca * NY
            V[i] = (X, Y, Z); N[i] = (NX, NY, NZ)
        used = sorted(set(i for _, tr in groups for i in tr))
        remap = {old: new for new, old in enumerate(used)}
        V = [V[i] for i in used]; N = [N[i] for i in used]; U = [U[i] for i in used]
        groups = [(m, [remap[i] for i in tr]) for m, tr in groups]
        return V, N, U, groups, tex_used

    def fnum(x): return ('%.6f' % x).rstrip('0').rstrip('.') or '0'

    def write_obj(path, V, N, U, groups, header):
        with open(path, 'w') as f:
            f.write(header + '\nmtllib %s\no Shibahu\n' % os.path.basename(path).replace('.obj', '.mtl'))
            for x, y, z in V: f.write('v %.6f %.6f %.6f\n' % (x, y, z))
            for u, v in U: f.write('vt %.6f %.6f\n' % (u, v))
            for x, y, z in N: f.write('vn %.6f %.6f %.6f\n' % (x, y, z))
            for mname, tris in groups:
                f.write('usemtl %s\n' % mname)
                for t in range(0, len(tris), 3):
                    a, b, c = tris[t] + 1, tris[t + 1] + 1, tris[t + 2] + 1
                    f.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (a, a, a, b, b, b, c, c, c))

    def mtl_text(matnames, tex_used, flat):
        s = '# Shibahu materials\n'
        for m in matnames:
            s += 'newmtl %s\nKd 1 1 1\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n' % m
            if m in tex_used:
                pfx = '' if flat else 'textures/'
                s += 'map_Kd %s%s\n' % (pfx, os.path.basename(tex_used[m]))
                if m in ('HairA_mt', 'HairB_mt'): s += 'map_d %s%s\n' % (pfx, os.path.basename(tex_used[m]))
            s += '\n'
        return s

    def write_fbx(path, V, N, U, groups, matnames, tex_used):
        GEOID = 1000; MODID = 2000
        mat_ids = {m: 3000 + i for i, m in enumerate(matnames)}
        tex_ids = {m: 4000 + i for i, m in enumerate(matnames) if m in tex_used}
        vid_ids = {m: 5000 + i for i, m in enumerate(matnames) if m in tex_used}
        with open(path, 'w') as f:
            f.write('; FBX 7.4.0 project file\n; Shibahu for Mixamo (T-pose, no skeleton)\n')
            f.write('FBXHeaderExtension:  {\n\tFBXHeaderVersion: 1003\n\tFBXVersion: 7400\n\tCreator: "Journey fbx2gltf"\n}\n')
            f.write('GlobalSettings:  {\n\tVersion: 1000\n\tProperties70:  {\n\t\tP: "UpAxis", "int", "Integer", "",1\n\t\tP: "UpAxisSign", "int", "Integer", "",1\n\t\tP: "FrontAxis", "int", "Integer", "",2\n\t\tP: "FrontAxisSign", "int", "Integer", "",1\n\t\tP: "CoordAxis", "int", "Integer", "",0\n\t\tP: "CoordAxisSign", "int", "Integer", "",1\n\t\tP: "UnitScaleFactor", "double", "Number", "",1\n\t}\n}\n')
            f.write('Documents:  {\n\tCount: 1\n}\nReferences:  {\n}\n')
            f.write('Definitions:  {\n\tVersion: 100\n\tCount: %d\n' % (2 + len(matnames) + 2 * len(tex_ids)))
            f.write('\tObjectType: "GlobalSettings" {\n\t\tCount: 1\n\t}\n\tObjectType: "Model" {\n\t\tCount: 1\n\t}\n\tObjectType: "Geometry" {\n\t\tCount: 1\n\t}\n')
            f.write('\tObjectType: "Material" {\n\t\tCount: %d\n\t}\n\tObjectType: "Texture" {\n\t\tCount: %d\n\t}\n\tObjectType: "Video" {\n\t\tCount: %d\n\t}\n}\n' % (len(matnames), len(tex_ids), len(vid_ids)))
            f.write('Objects:  {\n')
            f.write('\tGeometry: %d, "Geometry::Shibahu", "Mesh" {\n\t\tVertices: *%d {\n\t\t\ta: ' % (GEOID, len(V) * 3))
            f.write(','.join('%s,%s,%s' % (fnum(p[0]), fnum(p[1]), fnum(p[2])) for p in V))
            f.write('\n\t\t}\n\t\tPolygonVertexIndex: *%d {\n\t\t\ta: ' % sum(len(t) for _, t in groups))
            parts = []
            for _, tris in groups:
                for t in range(0, len(tris), 3):
                    parts.append('%d,%d,%d' % (tris[t], tris[t + 1], -tris[t + 2] - 1))
            f.write(','.join(parts))
            f.write('\n\t\t}\n')
            f.write('\t\tLayerElementNormal: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByPolygonVertex"\n\t\t\tReferenceInformationType: "Direct"\n\t\t\tNormals: *%d {\n\t\t\t\ta: ' % (sum(len(t) for _, t in groups) * 3))
            f.write(','.join('%s,%s,%s' % (fnum(N[i][0]), fnum(N[i][1]), fnum(N[i][2])) for _, tris in groups for i in tris))
            f.write('\n\t\t\t}\n\t\t}\n')
            f.write('\t\tLayerElementUV: 0 {\n\t\t\tVersion: 101\n\t\t\tName: "map1"\n\t\t\tMappingInformationType: "ByPolygonVertex"\n\t\t\tReferenceInformationType: "IndexToDirect"\n\t\t\tUV: *%d {\n\t\t\t\ta: ' % (len(U) * 2))
            f.write(','.join('%s,%s' % (fnum(u), fnum(v)) for u, v in U))
            f.write('\n\t\t\t}\n\t\t\tUVIndex: *%d {\n\t\t\t\ta: ' % sum(len(t) for _, t in groups))
            f.write(','.join(str(i) for _, tris in groups for i in tris))
            f.write('\n\t\t\t}\n\t\t}\n')
            f.write('\t\tLayerElementMaterial: 0 {\n\t\t\tVersion: 101\n\t\t\tName: ""\n\t\t\tMappingInformationType: "ByPolygon"\n\t\t\tReferenceInformationType: "IndexToDirect"\n\t\t\tMaterials: *%d {\n\t\t\t\ta: ' % sum(len(t) // 3 for _, t in groups))
            f.write(','.join(str(matnames.index(m)) for m, tris in groups for _ in range(len(tris) // 3)))
            f.write('\n\t\t\t}\n\t\t}\n')
            f.write('\t\tLayer: 0 {\n\t\t\tVersion: 100\n\t\t\tName: ""\n\t\t\tLayerElement:  {\n\t\t\t\tType: "LayerElementNormal"\n\t\t\t\tTypedIndex: 0\n\t\t\t}\n\t\t\tLayerElement:  {\n\t\t\t\tType: "LayerElementMaterial"\n\t\t\t\tTypedIndex: 0\n\t\t\t}\n\t\t\tLayerElement:  {\n\t\t\t\tType: "LayerElementUV"\n\t\t\t\tTypedIndex: 0\n\t\t\t}\n\t\t}\n\t}\n')
            f.write('\tModel: %d, "Model::Shibahu", "Mesh" {\n\t\tVersion: 232\n\t\tProperties70:  {\n\t\t\tP: "Lcl Translation", "Lcl Translation", "", "A",0,0,0\n\t\t\tP: "Lcl Rotation", "Lcl Rotation", "", "A",0,0,0\n\t\t\tP: "Lcl Scaling", "Lcl Scaling", "", "A",1,1,1\n\t\t}\n\t\tShading: T\n\t\tCulling: "CullingOff"\n\t}\n' % MODID)
            for m in matnames:
                f.write('\tMaterial: %d, "Material::%s", "" {\n\t\tVersion: 102\n\t\tShadingModel: "phong"\n\t\tMultiLayer: 0\n\t\tProperties70:  {\n\t\t\tP: "DiffuseColor", "Color", "", "A",0.8,0.8,0.8\n\t\t}\n\t}\n' % (mat_ids[m], m))
            for m in matnames:
                if m not in tex_used: continue
                fn = 'textures/' + os.path.basename(tex_used[m])
                f.write('\tTexture: %d, "Texture::%s_map", "" {\n\t\tType: "TextureVideoClip"\n\t\tVersion: 202\n\t\tTextureName: "%s_map"\n\t\tMedia: "Video::%s_vid"\n\t\tFileName: "%s"\n\t\tRelativeFilename: "%s"\n\t\tModelUVTranslation: 0,0\n\t\tModelUVScaling: 1,1\n\t\tTexture_Alpha_Source: "None"\n\t\tCropping: 0,0,0,0\n\t}\n' % (tex_ids[m], m, m, m, fn, fn))
                f.write('\tVideo: %d, "Video::%s_vid", "Clip" {\n\t\tType: "Clip"\n\t\tProperties70:  {\n\t\t\tP: "Path", "Path", "", "", "%s"\n\t\t}\n\t\tUseMipMap: 0\n\t\tFileName: "%s"\n\t\tRelativeFilename: "%s"\n\t}\n' % (vid_ids[m], m, fn, fn, fn))
            f.write('}\nConnections:  {\n')
            f.write('\tC: "OO",%d,0\n\tC: "OO",%d,%d\n' % (MODID, GEOID, MODID))
            for m in matnames:
                f.write('\tC: "OO",%d,%d\n' % (mat_ids[m], MODID))
                if m in tex_used:
                    f.write('\tC: "OO",%d,%d,"DiffuseColor"\n\tC: "OO",%d,%d\n' % (tex_ids[m], mat_ids[m], vid_ids[m], tex_ids[m]))
            f.write('}\n')

    res = {}
    for lite in (False, True):
        V, N, U, groups, tex_used = build(lite)
        matnames = []
        for m, _ in groups:
            if m not in matnames: matnames.append(m)
        tag = 'lite' if lite else 'full'
        print(tag, 'verts', len(V), 'tris', sum(len(t) // 3 for _, t in groups), 'mats', matnames)
        res[tag] = (V, N, U, groups, tex_used, matnames)

    Vf, Nf, Uf, gf, texf, matf = res['full']
    Vl, Nl, Ul, gl, texl, matl = res['lite']
    write_obj(os.path.join(out, 'shibahu.obj'), Vf, Nf, Uf, gf, '# Shibahu FULL (tail+cheek) - T-pose, no skeleton, cm. Upload ZIP-nya ke Mixamo.')
    write_obj(os.path.join(out, 'shibahu_lite.obj'), Vl, Nl, Ul, gl, '# Shibahu LITE (no tail/cheek) - fallback bila auto-rigger menolak ekor.')
    open(os.path.join(out, 'shibahu.mtl'), 'w').write(mtl_text(matf, texf, False))
    open(os.path.join(out, 'shibahu_lite.mtl'), 'w').write(mtl_text(matl, texl, False))
    write_fbx(os.path.join(out, 'shibahu.fbx'), Vf, Nf, Uf, gf, matf, texf)

    def make_zip(zpath, objpath, mtlstr, tex_used):
        with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(objpath, os.path.basename(objpath))
            z.writestr(os.path.basename(objpath).replace('.obj', '.mtl'), mtlstr)
            for m, uri in tex_used.items():
                p = os.path.join(out, 'textures', os.path.basename(uri))
                z.write(p, os.path.basename(uri))
    make_zip(os.path.join(out, 'shibahu_mixamo.zip'), os.path.join(out, 'shibahu.obj'), mtl_text(matf, texf, True), texf)
    make_zip(os.path.join(out, 'shibahu_lite_mixamo.zip'), os.path.join(out, 'shibahu_lite.obj'), mtl_text(matl, texl, True), texl)
    print('done ->', out)

main()
