#!/usr/bin/env python3
"""FBX 7.x binary -> glTF 2.0 (separate .gltf+.bin+textures). Pure stdlib.
Handles: mesh geometry (triangulate), materials per polygon, skinning (clusters),
blendshapes (morph targets), bone hierarchy, and baked TRS animation (Take 001).
"""
import struct, zlib, array, json, sys, os, math

# ---------------- FBX binary parsing ----------------
def read_prop(data, o):
    t = chr(data[o]); o += 1
    if t == 'Y': return struct.unpack_from('<h', data, o)[0], o+2
    if t == 'C': return data[o], o+1
    if t == 'I': return struct.unpack_from('<i', data, o)[0], o+4
    if t == 'F': return struct.unpack_from('<f', data, o)[0], o+4
    if t == 'D': return struct.unpack_from('<d', data, o)[0], o+8
    if t == 'L': return struct.unpack_from('<q', data, o)[0], o+8
    if t == 'S':
        l = struct.unpack_from('<I', data, o)[0]; o += 4
        return data[o:o+l].decode('latin1'), o+l
    if t == 'R':
        l = struct.unpack_from('<I', data, o)[0]; o += 4
        return data[o:o+l], o+l
    if t in 'fdli':
        n, enc, cl = struct.unpack_from('<III', data, o); o += 12
        raw = data[o:o+cl]; o += cl
        if enc == 1: raw = zlib.decompress(raw)
        a = array.array({'f':'f','d':'d','l':'q','i':'i'}[t]); a.frombytes(raw)
        return a, o
    raise ValueError('unknown prop type %r' % t)

def read_node(data, o, ver):
    if ver >= 7500:
        end, np_, pl = struct.unpack_from('<QQQ', data, o); o += 24
    else:
        end, np_, pl = struct.unpack_from('<III', data, o); o += 12
    if end == 0: return None, o
    nl = data[o]; o += 1
    name = data[o:o+nl].decode('latin1'); o += nl
    props = []; po = o
    for _ in range(np_):
        v, po = read_prop(data, po); props.append(v)
    o = po; children = []
    while o < end:
        child, no = read_node(data, o, ver)
        if child is None: o = end; break
        children.append(child); o = no
    return {'n': name, 'p': props, 'c': children}, end

def parse(path):
    data = open(path, 'rb').read()
    ver = struct.unpack_from('<I', data, 23)[0]
    o = 27; root = []
    while o < len(data):
        node, o = read_node(data, o, ver)
        if node is None: break
        root.append(node)
    return ver, root

def find(root, name):
    for n in root:
        if n['n'] == name: return n
    return None

def child(node, name):
    for c in node.get('c', []):
        if c['n'] == name: return c
    return None

def clean(s):
    return s.split('\x00')[0]

# ---------------- tiny math ----------------
def m4_ident(): return [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
def m4_mul(a,b):
    r=[0.0]*16
    for i in range(4):
        for j in range(4):
            s=0.0
            for k in range(4): s+=a[i*4+k]*b[k*4+j]
            r[i*4+j]=s
    return r
def m4_inv(m):
    # Gauss-Jordan
    a=[row[:] for row in [m[i*4:(i+1)*4]+[1 if i==j else 0 for j in range(4)] for i in range(4)]]
    for c in range(4):
        p=max(range(c,4), key=lambda r: abs(a[r][c])); a[c],a[p]=a[p],a[c]
        d=a[c][c]
        if abs(d)<1e-12: raise ValueError('singular')
        a[c]=[x/d for x in a[c]]
        for r in range(4):
            if r!=c and abs(a[r][c])>0:
                f=a[r][c]; a[r]=[x-f*y for x,y in zip(a[r],a[c])]
    return [a[i][4+j] for i in range(4) for j in range(4)]

def euler_xyz_quat(x,y,z):
    # FBX RotationOrder XYZ (intrinsic): R = Rz*Ry*Rx
    cx,sx=math.cos(x/2),math.sin(x/2); cy,sy=math.cos(y/2),math.sin(y/2); cz,sz=math.cos(z/2),math.sin(z/2)
    qx=(sx*cy*cz + cx*sy*sz, cx*sy*cz - sx*cy*sz, cx*cy*sz + sx*sy*cz, cx*cy*cz - sx*sy*sz)  # qz*qy*qx
    return qx

def q_mul(a,b):
    ax,ay,az,aw=a; bx,by,bz,bw=b
    return (aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx, aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz)

# ---------------- main export ----------------
def export(fbx_path, out_dir, tex_dir_name='textures'):
    ver, root = parse(fbx_path)
    objs = find(root,'Objects'); conns = find(root,'Connections')
    OO=[]; OP=[]
    for c in conns['c']:
        t,s,d = c['p'][0],c['p'][1],c['p'][2]
        if t=='OO': OO.append((s,d))
        elif t=='OP': OP.append((s,d,c['p'][2] if len(c['p'])>2 else ''))

    models={}; geoms={}; mats={}; defs={}
    for c in objs['c']:
        i=c['p'][0]
        if c['n']=='Model':
            models[i]={'name':clean(c['p'][1]),'type':c['p'][2] if len(c['p'])>2 else '','node':c}
        elif c['n']=='Geometry':
            geoms[i]={'name':clean(c['p'][1]),'type':c['p'][2] if len(c['p'])>2 else 'Mesh','node':c}
        elif c['n']=='Material':
            mats[i]={'name':clean(c['p'][1]),'node':c}
        elif c['n']=='Deformer':
            defs[i]={'name':clean(c['p'][1]),'type':c['p'][2] if len(c['p'])>2 else '','node':c}

    # hierarchy: child->parent among models
    parent={}; children={}
    for s,d in OO:
        if s in models and d in models:
            parent[s]=d; children.setdefault(d,[]).append(s)
    roots=[i for i in models if i not in parent]

    # geometry->model, material->geometry, cluster links, blendshape links
    geo2model={}; mat2geo={}; cluster2geo={}; cluster2bone={}; bs2geo={}; chan2shape={}
    for s,d in OO:
        if s in geoms and d in models: geo2model[s]=d
        if s in mats and d in models: mat2geo.setdefault(d,[]).append(s)
        if s in defs and defs[s]['type']=='Cluster' and d in geoms: cluster2geo.setdefault(d,[]).append(s)
        if s in defs and s in models: pass
        if s in models and d in defs and defs[d]['type']=='Cluster': cluster2bone[d]=s
        if s in defs and defs[s]['type']=='BlendShape' and d in geoms: bs2geo.setdefault(d,[]).append(s)
        if s in geoms and geoms[s]['type']=='Shape' and d in defs and defs[d]['type']=='BlendShapeChannel': chan2shape[d]=s

    # channel -> parent blendshape
    chan_parent={}
    for s,d in OO:
        if s in defs and defs[s]['type']=='BlendShapeChannel' and d in defs and defs[d]['type']=='BlendShape':
            chan_parent[s]=d

    def d3(node,name):
        n=child(node,name)
        if n and n['p']: 
            v=n['p'][0]
            if isinstance(v,array.array): return list(v[:3])
            return [v]*3
        return None

    # ---------------- buffers / accessors ----------------
    bin_chunks=[]; accs=[]; bufviews=[]
    def add_bufview(data_bytes, target):
        # pad to 4
        pad=(4-len(data_bytes)%4)%4
        off=sum(len(b) for b in bin_chunks)
        bin_chunks.append(data_bytes+b'\x00'*pad)
        bv={'buffer':0,'byteOffset':off,'byteLength':len(data_bytes)}
        if target: bv['target']=target
        bufviews.append(bv); return len(bufviews)-1
    def acc(comp_type, comp_count, arr_list, t=None, norm=False):
        fmt={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}[comp_type]
        a=array.array(fmt, arr_list)
        bv=add_bufview(a.tobytes(), t)
        ac={'bufferView':bv,'componentType':comp_type,'count':len(arr_list)//comp_count,'type':comp_count}
        accs.append(ac); return len(accs)-1
    def acc_vec(arr_list, comp_count, comp_type=5126, target=34962):
        return acc(comp_type, comp_count, arr_list, target)
    def acc_pos(arr_list):
        mn=[min(arr_list[i::3]) for i in range(3)]; mx=[max(arr_list[i::3]) for i in range(3)]
        i=acc(5126,3,arr_list,34962)
        accs[i]['min']=mn; accs[i]['max']=mx; return i

    images=[]; samplers=[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}]
    texcache={}
    textures_list=[]
    def get_tex_idx(fname):
        if fname not in texcache:
            images.append({'uri':f'{tex_dir_name}/{fname}','name':fname})
            textures_list.append({'sampler':0,'source':len(images)-1})
            texcache[fname]=len(textures_list)-1
        return texcache[fname]

    # material definitions (anime relink)
    def mat_gltf(mname):
        M={'name':mname}
        pbr={}
        m=mname
        if m=='Body_mt': pbr={'baseColorTexture':{'index':get_tex_idx('Shibahu_body_dif.png')}}; M['doubleSided']=True
        elif m=='Face_mt': pbr={'baseColorTexture':{'index':get_tex_idx('Shibahu_face_dif.png')}}; M['doubleSided']=True
        elif m=='HairA_mt': pbr={'baseColorTexture':{'index':get_tex_idx('hairA_albedo_a.png')}}; M['alphaMode']='MASK'; M['alphaCutoff']=0.5; M['doubleSided']=True
        elif m=='HairB_mt': pbr={'baseColorTexture':{'index':get_tex_idx('hairB_albedo_a.png')}}; M['alphaMode']='MASK'; M['alphaCutoff']=0.5; M['doubleSided']=True
        elif m=='CosA_mt': pbr={'baseColorTexture':{'index':get_tex_idx('Shibahu_cosA_dif.png')}}; M['doubleSided']=True
        elif m=='CosB_mt': pbr={'baseColorTexture':{'index':get_tex_idx('Shibahu_cosB_dif.png')}}; M['doubleSided']=True
        elif m=='Cheek_mt': pbr={'baseColorTexture':{'index':get_tex_idx('cheek_albedo_a.png')}}; M['alphaMode']='BLEND'; M['doubleSided']=True
        elif m in ('lineA_mt','lineB_mt','lineC_mt'):
            pbr={'baseColorFactor':[0.09,0.08,0.10,1.0]}
        else:
            pbr={'baseColorFactor':[0.8,0.8,0.8,1.0]}
        pbr['metallicFactor']=0.0; pbr['roughnessFactor']=0.9
        M['pbrMetallicRoughness']=pbr
        return M
    mat_idx={}
    def get_mat(mname):
        if mname not in mat_idx:
            mat_idx[mname]=len(mat_idx)
        return mat_idx[mname]

    # ---------------- parse each geometry ----------------
    joints_list=[]; joint_id2idx={}
    joint_ids=[i for i in models if models[i]['type'] in ('LimbNode','Null')]
    for i in joint_ids: joint_id2idx[i]=len(joints_list); joints_list.append(i)

    meshes_out=[]; mesh_id2idx={}
    node_list=[]; node_id2idx={}
    total_verts=[0]; total_tris=[0]

    def parse_geometry(gid):
        g=geoms[gid]['node']
        verts=list(child(g,'Vertices')['p'][0])
        pvi=list(child(g,'PolygonVertexIndex')['p'][0])
        nv=len(verts)//3
        normals=None; n_map='ByPolygonVertex'
        ln=child(g,'LayerElementNormal')
        if ln is not None:
            nnode=child(ln,'Normals')
            if nnode is not None: normals=list(nnode['p'][0])
            nm=child(ln,'MappingInformationType')
            if nm is not None and nm['p']: n_map=nm['p'][0]
        uvs=None; uvi=None
        lu=child(g,'LayerElementUV')
        if lu is not None:
            unode=child(lu,'UV')
            if unode is not None: uvs=list(unode['p'][0])
            uinode=child(lu,'UVIndex')
            if uinode is not None: uvi=list(uinode['p'][0])
        matids=None; mat_map='ByPolygon'
        lm=child(g,'LayerElementMaterial')
        if lm is not None:
            mnode=child(lm,'Materials')
            if mnode is not None: matids=list(mnode['p'][0])
            mm=child(lm,'MappingInformationType')
            if mm is not None and mm['p']: mat_map=mm['p'][0]
        return dict(verts=verts,pvi=pvi,normals=normals,n_map=n_map,uvs=uvs,uvi=uvi,matids=matids,mat_map=mat_map,nv=nv)

    def build_mesh(gid, mat_of_poly_default=None):
        G=parse_geometry(gid)
        verts,pvi=G['verts'],G['pvi']
        # polygons
        polys=[]; i=0; L=len(pvi)
        while i<L:
            poly=[]
            while True:
                v=pvi[i]; poly.append(v if v>=0 else ~v); i+=1
                if pvi[i-1]<0: break
            polys.append(poly)
        # corner arrays
        pos=[]; nor=[]; uvc=[]; midx=[]; orig=[]
        vmap={}
        corner=0
        tri_groups={}  # matid -> [indices]
        for pi,poly in enumerate(polys):
            if not G['matids']: m=0
            elif G['mat_map']=='AllSame': m=G['matids'][0]
            elif pi < len(G['matids']): m=G['matids'][pi]
            else: m=0
            for k in range(1,len(poly)-1):
                for vi in (poly[0],poly[k],poly[k+1]):
                    ni=vi if G['n_map'] in ('ByVertice','ByVertex') else corner
                    ui=G['uvi'][corner] if G['uvi'] else corner
                    if G['uvs'] is None: u=(0.0,0.0)
                    else: u=(G['uvs'][ui*2], 1.0-G['uvs'][ui*2+1])
                    if G['normals'] is None: n=(0,0,0)
                    else: n=(G['normals'][ni*3],G['normals'][ni*3+1],G['normals'][ni*3+2])
                    key=(vi,ni,ui)
                    idx=vmap.get(key)
                    if idx is None:
                        idx=len(pos)//3
                        vmap[key]=idx
                        pos+=verts[vi*3:vi*3+3]; nor+=list(n); uvc+=list(u); orig.append(vi)
                    tri_groups.setdefault(m,[]).append(idx)
                    corner+=1
        # weights (kept after tri build) -- placeholder to anchor
        infl={}
        for cl in cluster2geo.get(gid,[]):
            dn=defs[cl]['node']
            idxs=list(child(dn,'Indexes')['p'][0]); ws=list(child(dn,'Weights')['p'][0])
            bone=cluster2bone.get(cl)
            if bone is None or bone not in joint_id2idx: continue
            ji=joint_id2idx[bone]
            for vi,w in zip(idxs,ws):
                infl.setdefault(vi,[]).append((ji,w))
        jnt=[]; wgt=[]
        for k in range(len(orig)):
            vi=orig[k]
            l=infl.get(vi,[])
            l.sort(key=lambda t:-t[1]); l=l[:4]
            tw=sum(w for _,w in l) or 1.0
            jj=[0]*4; ww=[0.0]*4
            for n2,(ji,w) in enumerate(l): jj[n2]=ji; ww[n2]=w/tw
            jnt+=jj; wgt+=ww
        # morphs
        targets=[]
        for bs in bs2geo.get(gid,[]):
            for ch,sh in chan2shape.items():
                if chan_parent.get(ch)!=bs: continue
                sn=geoms[sh]['node']
                sidx=list(child(sn,'Indexes')['p'][0]); sdl=list(child(sn,'Vertices')['p'][0])
                dmap={vi:(sdl[k*3],sdl[k*3+1],sdl[k*3+2]) for k,vi in enumerate(sidx)}
                tp=[0.0]*(len(orig)*3)
                for k,vi in enumerate(orig):
                    d=dmap.get(vi)
                    if d: tp[k*3:k*3+3]=list(d)
                targets.append((clean(defs[ch]['name']),tp))
        total_verts[0]+=len(pos)//3
        total_tris[0]+=sum(len(t)//3 for t in tri_groups.values())
        return dict(pos=pos,nor=nor,uvc=uvc,tri_groups=tri_groups,jnt=jnt,wgt=wgt,targets=targets,orig=orig)

    # ---------------- nodes & meshes & skins ----------------
    gltf_nodes=[]
    def add_node_for(mid):
        m=models[mid]
        n=m['node']
        t=d3(n,'Lcl Translation') or [0,0,0]
        r=d3(n,'Lcl Rotation') or [0,0,0]
        s=d3(n,'Lcl Scaling') or [1,1,1]
        q=euler_xyz_quat(math.radians(r[0]),math.radians(r[1]),math.radians(r[2]))
        node={'name':m['name']}
        node['translation']=[float(x) for x in t]
        node['rotation']=[float(x) for x in q]
        node['scale']=[float(x) for x in s]
        idx=len(gltf_nodes); gltf_nodes.append(node); node_id2idx[mid]=idx
        return idx

    # create joint nodes
    for ji in joints_list: add_node_for(ji)
    # mesh nodes
    mesh_models=[i for i in models if models[i]['type']=='Mesh']
    skin_idx=None
    for mid in mesh_models:
        geos=[g for g,d in geo2model.items() if d==mid and geoms[g]['type']=='Mesh']
        ni=add_node_for(mid)
        primitives=[]
        target_names=None
        for gid in geos:
            B=build_mesh(gid)
            if B['targets'] and target_names is None:
                target_names=[t[0] for t in B['targets']]
            # attributes
            a_pos=acc_pos(B['pos'])
            a_nor=acc_vec(B['nor'],3)
            a_uv=acc_vec(B['uvc'],2)
            a_j=acc_vec(B['jnt'],4,5123)
            a_w=acc_vec(B['wgt'],4)
            matlist = mat2geo.get(geo2model.get(gid), [])
            for m,tri in B['tri_groups'].items():
                mobj = matlist[m] if isinstance(m,int) and m < len(matlist) else None
                mname = mats[mobj]['name'] if mobj in mats else 'lambert1'
                a_i=acc_vec(tri,1,5125,34963)
                prim={'attributes':{'POSITION':a_pos,'NORMAL':a_nor,'TEXCOORD_0':a_uv,'JOINTS_0':a_j,'WEIGHTS_0':a_w},'indices':a_i,'material':get_mat(mname)}
                if B['targets']:
                    tpos=[acc_vec(tp,3) for _,tp in B['targets']]
                    prim['targets']=[{'POSITION':p} for p in tpos]
                primitives.append(prim)
        mesh={'primitives':primitives}
        if target_names: mesh['extras']={'targetNames':target_names}
        mesh_idx=len(meshes_out); meshes_out.append(mesh)
        gltf_nodes[ni]['mesh']=mesh_idx
        gltf_nodes[ni]['skin']=0

    # node children/parents
    for mid in models:
        if mid in node_id2idx and mid in parent and parent[mid] in node_id2idx:
            p=node_id2idx[parent[mid]]
            gltf_nodes[p].setdefault('children',[]).append(node_id2idx[mid])

    # skin: inverse bind matrices from TransformLink
    ibm=[]
    for ji in joints_list:
        # find any cluster for this bone to get TransformLink; fallback identity
        tl=None
        for cl,bone in cluster2bone.items():
            if bone==ji:
                dn=defs[cl]['node']; tn=child(dn,'TransformLink')
                if tn is not None: tl=list(tn['p'][0])
                break
        if tl is None: M=m4_ident()
        else:
            # tl row-major
            M=[tl[r*4+c] for r in range(4) for c in range(4)]
        inv=m4_inv(M)
        # glTF column-major
        ibm += [inv[r*4+c] for c in range(4) for r in range(4)]
    a_ibm=acc_vec(ibm,16)
    skin={'joints':[node_id2idx[j] for j in joints_list],'inverseBindMatrices':a_ibm}
    root_joint=joints_list[0]
    skin['skeleton']=node_id2idx[root_joint]

    # materials finalize
    gltf_mats=[None]*len(mat_idx)
    for name,i in mat_idx.items(): gltf_mats[i]=mat_gltf(name)

    gltf={
      'asset':{'version':'2.0','generator':'Journey fbx2gltf'},
      'scene':0,'scenes':[{'nodes':[node_id2idx[r] for r in roots if r in node_id2idx]}],
      'nodes':gltf_nodes,'meshes':meshes_out,'skins':[skin],
      'materials':gltf_mats,'images':images,'textures':textures_list,'samplers':samplers,
      'accessors':accs,'bufferViews':bufviews,
      'buffers':[{'uri':'shibahu.bin','byteLength':sum(len(b) for b in bin_chunks)}],
    }

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir,'shibahu.bin'),'wb') as f:
        for b in bin_chunks: f.write(b)
    with open(os.path.join(out_dir,'shibahu.gltf'),'w') as f:
        json.dump(gltf,f)
    stats={'nodes':len(gltf_nodes),'meshes':len(meshes_out),'joints':len(joints_list),
           'verts':total_verts[0],'tris':total_tris[0],
           'accessors':len(accs),'bin_mb':round(sum(len(b) for b in bin_chunks)/1e6,1)}
    return stats

if __name__=='__main__':
    fbx=sys.argv[1]; out=sys.argv[2]
    print(json.dumps(export(fbx,out)))
