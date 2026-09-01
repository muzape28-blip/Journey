#!/usr/bin/env python3
"""Solid textured+shaded triangle rasterizer for a skinned glTF (pure stdlib).
Usage: render_solid.py <dir> <out_prefix> [W] [H]
Produces <prefix>_front/_threeq/_back PNG with toon bands + rim, for in-chat visual QA.
"""
import json, struct, sys, os, subprocess, math

def png_meta(p):
    d=open(p,'rb').read(33); w,h=struct.unpack('>II',d[16:24]); return w,h
def png_rgba(p):
    w,h=png_meta(p)
    raw=subprocess.run(['convert',p,'-depth','8','rgba:-'],capture_output=True,check=True).stdout
    return w,h,raw
def quat_mat(q):
    x,y,z,w=q
    return [1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0,2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0,2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0,0,0,0,1]
def mul(a,b):
    r=[0.0]*16
    for i in range(4):
        for j in range(4): r[i*4+j]=sum(a[i*4+k]*b[k*4+j] for k in range(4))
    return r
def nmat(n):
    c=n['matrix']; return [c[0],c[4],c[8],c[12],c[1],c[5],c[9],c[13],c[2],c[6],c[10],c[14],c[3],c[7],c[11],c[15]]
def xf(m,p):
    x,y,z=p
    return (m[0]*x+m[1]*y+m[2]*z+m[3],m[4]*x+m[5]*y+m[6]*z+m[7],m[8]*x+m[9]*y+m[10]*z+m[11])

def main():
    d=sys.argv[1]; prefix=sys.argv[2]; W=int(sys.argv[3]) if len(sys.argv)>3 else 640; H=int(sys.argv[4]) if len(sys.argv)>4 else 840
    g=json.load(open(os.path.join(d,'shibahu.gltf'))); binb=open(os.path.join(d,'shibahu.bin'),'rb').read()
    def acc(i):
        a=g['accessors'][i]; bv=g['bufferViews'][a['bufferView']]
        fmt={5126:'f',5123:'H',5125:'I'}[a['componentType']]
        n=a['count']*{'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
        arr=__import__('array').array(fmt); arr.frombytes(binb[bv['byteOffset']:bv['byteOffset']+n*arr.itemsize]); return list(arr)
    nodes=g['nodes']; parent={}
    for i,n in enumerate(nodes):
        for c in n.get('children',[]): parent[c]=i
    glob=[None]*len(nodes)
    def gm(i):
        if glob[i] is not None: return glob[i]
        L=nmat(nodes[i]); glob[i]=mul(gm(parent[i]),L) if i in parent else L; return glob[i]
    for i in range(len(nodes)): gm(i)
    skin=g['skins'][0]; joints=skin['joints']; ibmd=acc(skin['inverseBindMatrices'])
    def ibm(k):
        c=ibmd[k*16:(k+1)*16]; return [c[0],c[4],c[8],c[12],c[1],c[5],c[9],c[13],c[2],c[6],c[10],c[14],c[3],c[7],c[11],c[15]]
    texc={}
    def tex_of(m):
        p=m.get('pbrMetallicRoughness',{}); t=p.get('baseColorTexture')
        if t is None: return None
        uri=g['images'][g['textures'][t['index']]['source']]['uri']
        if uri not in texc: texc[uri]=png_rgba(os.path.join(d,uri))
        return texc[uri]
    def sample(m,u,v):
        t=tex_of(m)
        if t is None:
            f=m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[0.8,0.8,0.8,1]); return tuple(int(255*c) for c in f[:3]),1.0
        w,h,raw=t; x=min(w-1,max(0,int(u*w))); y=min(h-1,max(0,int(v*h))); o=(y*w+x)*4
        return (raw[o],raw[o+1],raw[o+2]),raw[o+3]/255
    tris=[]  # (p0,p1,p2, n0,n1,n2, uv0,uv1,uv2, mat, line)
    for mi,me in enumerate(g['meshes']):
        for pr in me['primitives']:
            mat=g['materials'][pr['material']]
            pos=acc(pr['attributes']['POSITION']); nor=acc(pr['attributes']['NORMAL'])
            uv=acc(pr['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in pr['attributes'] else None
            jn=acc(pr['attributes']['JOINTS_0']); wt=acc(pr['attributes']['WEIGHTS_0'])
            idx=acc(pr['indices'])
            ni=[i for i,n in enumerate(nodes) if n.get('mesh')==mi]
            mg=gm(ni[0]) if ni else [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
            npts=len(pos)//3
            P=[None]*npts; N=[None]*npts; sm={}
            for vi in range(npts):
                x,y,z=pos[vi*3:vi*3+3]; X=Y=Z=0.0;NX=NY=NZ=0.0
                for k in range(4):
                    w=wt[vi*4+k]
                    if w<=0: continue
                    ji=jn[vi*4+k]
                    if ji not in sm: sm[ji]=mul(glob[joints[ji]],ibm(ji))
                    m=sm[ji]
                    X+=w*(m[0]*x+m[1]*y+m[2]*z+m[3]); Y+=w*(m[4]*x+m[5]*y+m[6]*z+m[7]); Z+=w*(m[8]*x+m[9]*y+m[10]*z+m[11])
                    nx,ny,nz=nor[vi*3:vi*3+3]
                    NX+=w*(m[0]*nx+m[1]*ny+m[2]*nz); NY+=w*(m[4]*nx+m[5]*ny+m[6]*nz); NZ+=w*(m[8]*nx+m[9]*ny+m[10]*nz)
                P[vi]=xf(mg,(X,Y,Z)); N[vi]= (mg[0]*NX+mg[1]*NY+mg[2]*NZ,mg[4]*NX+mg[5]*NY+mg[6]*NZ,mg[8]*NX+mg[9]*NY+mg[10]*NZ)
            line=(mat.get('pbrMetallicRoughness',{}).get('baseColorTexture') is None)
            for t in range(0,len(idx),3):
                a,b,c=idx[t],idx[t+1],idx[t+2]
                uvs=None
                if uv is not None: uvs=[(uv[a*2],uv[a*2+1]),(uv[b*2],uv[b*2+1]),(uv[c*2],uv[c*2+1])]
                tris.append((P[a],P[b],P[c],N[a],N[b],N[c],uvs,mat,line))
    xs=[p[0] for t in tris for p in t[:3]]; ys=[p[1] for t in tris for p in t[:3]]; zs=[p[2] for t in tris for p in t[:3]]
    mn=[min(xs),min(ys),min(zs)]; mx=[max(xs),max(ys),max(zs)]
    print('tris',len(tris))
    L=(0.45,0.6,0.65); ln=math.sqrt(sum(v*v for v in L)); L=[v/ln for v in L]
    def render(view,out):
        fb=[(10,20,13)]*(W*H); depth=[1e18]*(W*H)
        sc=max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])
        cy0=(mn[1]+mx[1])/2
        import math as _m
        ang={'front':0.0,'threeq':0.6,'back':3.1416}[view]
        ca,sa=_m.cos(ang),_m.sin(ang)
        V=(sa,0,ca)
        def proj(p):
            x,y,z=p
            xr=x*ca - z*sa; zr=x*sa + z*ca
            sx=(xr/sc)*W*0.86+W*0.5
            sy=H*0.5 - ((y-cy0)/sc)*H*0.92
            return sx,sy,zr
        for (p0,p1,p2,n0,n1,n2,uvs,mat,line) in tris:
            a=proj(p0); b=proj(p1); c=proj(p2)
            # backface cull for solid (not line)
            area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if not line and area<=0: continue
            if line and area==0: continue
            minx=int(max(0,min(a[0],b[0],c[0]))); maxx=int(min(W-1,max(a[0],b[0],c[0])))
            miny=int(max(0,min(a[1],b[1],c[1]))); maxy=int(min(H-1,max(a[1],b[1],c[1])))
            if maxx<minx or maxy<miny: continue
            inv=1.0/area
            for py in range(miny,maxy+1):
                for px in range(minx,maxx+1):
                    w0=((b[0]-px)*(c[1]-py)-(b[1]-py)*(c[0]-px))*inv
                    w1=((c[0]-px)*(a[1]-py)-(c[1]-py)*(a[0]-px))*inv
                    w2=1-w0-w1
                    if (w0<0 or w1<0 or w2<0) if area>0 else (w0>0 or w1>0 or w2>0): continue
                    z=w0*a[2]+w1*b[2]+w2*c[2]
                    o=py*W+px
                    if z<depth[o]-1e-6 or (line and z<depth[o]):
                        depth[o]=z
                        nx=w0*n0[0]+w1*n1[0]+w2*n2[0]; ny=w0*n0[1]+w1*n1[1]+w2*n2[1]; nz=w0*n0[2]+w1*n1[2]+w2*n2[2]
                        nl=math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0; nx,ny,nz=nx/nl,ny/nl,nz/nl
                        if uvs is not None:
                            u=w0*uvs[0][0]+w1*uvs[1][0]+w2*uvs[2][0]; v=w0*uvs[0][1]+w1*uvs[1][1]+w2*uvs[2][1]
                            col,al=sample(mat,u,v)
                            if mat.get('alphaMode') in ('MASK','BLEND') and al<0.5: continue
                        else:
                            col,_=sample(mat,0,0)
                        if line:
                            fb[o]=(20,16,26); continue
                        ndl=nx*L[0]+ny*L[1]+nz*L[2]
                        band=1.05 if ndl>0.6 else 0.9 if ndl>0.15 else 0.75 if ndl>-0.1 else 0.6
                        r=int(min(255,col[0]*band)); gg=int(min(255,col[1]*band)); bb=int(min(255,col[2]*band))
                        fb[o]=(r,gg,bb)
        with open(out+'.ppm','wb') as f:
            f.write(b'P6\n%d %d\n255\n'%(W,H))
            for r,gc,b in fb: f.write(bytes((r,gc,b)))
        subprocess.run(['convert',out+'.ppm',out+'.png'],check=True); os.remove(out+'.ppm')
    for v in ('front','threeq','back'):
        render(v,f'{prefix}_{v}')
    print('done')
main()
