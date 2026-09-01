#!/usr/bin/env python3
"""Render skinned+textured point-cloud views of a glTF as PNG (no GPU/browser).
Usage: render_check.py <dir-with-gltf> <out_prefix> [size]
Outputs <out_prefix>_front.png / _back.png / _side.png
"""
import json, struct, sys, os, subprocess, math

def png_meta(path):
    d=open(path,'rb').read(33)
    w,h=struct.unpack('>II', d[16:24]); return w,h

def png_rgba(path):
    w,h=png_meta(path)
    raw=subprocess.run(['convert',path,'-depth','8','rgba:-'],capture_output=True,check=True).stdout
    return w,h,raw

def quat_mat(q):
    x,y,z,w=q
    return [1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0,
            2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0,
            2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0,
            0,0,0,1]
def mul(a,b):
    r=[0.0]*16
    for i in range(4):
        for j in range(4):
            r[i*4+j]=sum(a[i*4+k]*b[k*4+j] for k in range(4))
    return r
def trs_mat(n):
    if 'matrix' in n:
        c=n['matrix']
        return [c[0],c[4],c[8],c[12], c[1],c[5],c[9],c[13], c[2],c[6],c[10],c[14], c[3],c[7],c[11],c[15]]
    t=n.get('translation',[0,0,0]); q=n.get('rotation',[0,0,0,1]); s=n.get('scale',[1,1,1])
    T=[1,0,0,t[0],0,1,0,t[1],0,0,1,t[2],0,0,0,1]
    S=[s[0],0,0,0,0,s[1],0,0,0,0,s[2],0,0,0,0,1]
    return mul(mul(T,quat_mat(q)),S)
def xform(m,p):
    x,y,z=p
    return (m[0]*x+m[1]*y+m[2]*z+m[3], m[4]*x+m[5]*y+m[6]*z+m[7], m[8]*x+m[9]*y+m[10]*z+m[11])

def main():
    d=sys.argv[1]; prefix=sys.argv[2]; SIZE=int(sys.argv[3]) if len(sys.argv)>3 else 900
    g=json.load(open(os.path.join(d,'shibahu.gltf')))
    binb=open(os.path.join(d,'shibahu.bin'),'rb').read()
    def acc_data(i):
        a=g['accessors'][i]; bv=g['bufferViews'][a['bufferView']]
        off=bv['byteOffset']+a.get('byteOffset',0)
        n=a['count']; ct=a['componentType']
        comp={5126:('f',4),5123:('H',2),5125:('I',4),5121:('B',1)}[ct]
        fmt,size=comp
        import array
        cnt=n*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        arr=array.array(fmt)
        arr.frombytes(binb[off:off+cnt*size])
        return list(arr), a['type']
    nodes=g['nodes']
    # globals
    parent={}
    for i,n in enumerate(nodes):
        for c in n.get('children',[]): parent[c]=i
    glob=[None]*len(nodes)
    def gmat(i):
        if glob[i] is not None: return glob[i]
        L=trs_mat(nodes[i])
        glob[i]= mul(gmat(parent[i]),L) if i in parent else L
        return glob[i]
    for i in range(len(nodes)): gmat(i)
    skin=g['skins'][0]
    joints=skin['joints']; ibm_data,_=acc_data(skin['inverseBindMatrices'])
    ibms=[ [ibm_data[k*16+r] for r in range(16)] for k in range(len(joints))]  # column-major stored
    def ibm_mat(k):
        c=ibms[k]
        # convert column-major list to row-major matrix
        return [c[0],c[4],c[8],c[12], c[1],c[5],c[9],c[13], c[2],c[6],c[10],c[14], c[3],c[7],c[11],c[15]]
    texcache={}
    def tex_of(mat):
        p=mat.get('pbrMetallicRoughness',{})
        t=p.get('baseColorTexture')
        if t is None: return None
        uri=g['images'][g['textures'][t['index']]['source']]['uri']
        if uri not in texcache:
            w,h,raw=png_rgba(os.path.join(d,uri))
            texcache[uri]=(w,h,raw)
        return texcache[uri]
    def sample(mat,u,v):
        t=tex_of(mat)
        if t is None:
            f=mat.get('pbrMetallicRoughness',{}).get('baseColorFactor',[0.8,0.8,0.8,1])
            return tuple(int(255*c) for c in f[:3]),1.0
        w,h,raw=t
        x=min(w-1,max(0,int(u*w))); y=min(h-1,max(0,int(v*h)))
        o=(y*w+x)*4
        return (raw[o],raw[o+1],raw[o+2]), raw[o+3]/255
    # collect points
    pts=[]  # (x,y,z,r,g,b)
    for mi,me in enumerate(g['meshes']):
        for pr in me['primitives']:
            mat=g['materials'][pr['material']]
            pos,_=acc_data(pr['attributes']['POSITION'])
            uv,_=acc_data(pr['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in pr['attributes'] else (None,None)
            jn,_=acc_data(pr['attributes']['JOINTS_0']); wt,_=acc_data(pr['attributes']['WEIGHTS_0'])
            node_idx=None
            # find node using this mesh
            for ni,n in enumerate(nodes):
                if n.get('mesh')==mi: node_idx=ni; break
            mg=gmat(node_idx) if node_idx is not None else [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
            npts=len(pos)//3
            smats={}
            for vi in range(npts):
                x,y,z=pos[vi*3:vi*3+3]
                X=Y=Z=0.0
                for k in range(4):
                    w=wt[vi*4+k]
                    if w<=0: continue
                    ji=jn[vi*4+k]
                    key=ji
                    if key not in smats: smats[key]=mul(glob[joints[ji]], ibm_mat(ji))
                    m=smats[key]
                    px=m[0]*x+m[1]*y+m[2]*z+m[3]; py=m[4]*x+m[5]*y+m[6]*z+m[7]; pz=m[8]*x+m[9]*y+m[10]*z+m[11]
                    X+=w*px; Y+=w*py; Z+=w*pz
                X,Y,Z = xform(mg,(X,Y,Z))
                if uv is not None:
                    u,v=uv[vi*2],uv[vi*2+1]
                    col,al=sample(mat,u,v)
                    if mat.get('alphaMode') in ('MASK','BLEND') and al<0.5: continue
                else:
                    col,_=sample(mat,0,0)
                pts.append((X,Y,Z,col))
    # bounds
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; zs=[p[2] for p in pts]
    mn=[min(xs),min(ys),min(zs)]; mx=[max(xs),max(ys),max(zs)]
    print('points',len(pts),'bounds',mn,mx)
    def render(view,out):
        W=SIZE; H=SIZE
        fb=[(24,28,38)]*(W*H); depth=[-1e18]*(W*H)
        sc=max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])
        def proj(p):
            x,y,z=p
            if view=='front': sx,sy,d = x,y,z
            elif view=='back': sx,sy,d = -x,y,-z
            else: sx,sy,d = z,y,x
            cx=( (sx-(mn[0] if view=='front' else (-mx[0] if view=='back' else mn[2])))/sc )*W*0.8+W*0.1
            cy=H-(((sy-mn[1])/sc)*H*0.9+H*0.05)
            return cx,cy,d
        order=sorted(pts,key=lambda p:(p[2] if view=='front' else (-p[2] if view=='back' else p[0])))
        for x,y,z,col in order:
            cx,cy,d=proj((x,y,z))
            ix,iy=int(cx),int(cy)
            for dy in range(2):
                for dx in range(2):
                    px,py=ix+dx,iy+dy
                    if 0<=px<W and 0<=py<H and d>=depth[py*W+px]:
                        depth[py*W+px]=d; fb[py*W+px]=col
        with open(out+'.ppm','wb') as f:
            f.write(b'P6\n%d %d\n255\n'%(W,H))
            for r,gc,b in fb: f.write(bytes((r,gc,b)))
        subprocess.run(['convert',out+'.ppm',out+'.png'],check=True)
        os.remove(out+'.ppm')
    for v in ('front','back','side'):
        render(v, f'{prefix}_{v}')
    print('done')

main()
