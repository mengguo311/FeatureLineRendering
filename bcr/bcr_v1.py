"""BCR v1 — Seed Basin Capture Rate / Carrier Recall on vanilla 3DGS.
GT-line-anchored (flipped per W1): anchor on true mesh creases, ask whether a vanilla
gaussian carrier exists within the DT-pull basin. Locked spec (agy round9).

Pipeline:
 1. GT crease extraction: mesh dihedral edges (sweep 20/30/45 deg) -> dense points q_j
 2. Visibility: rasterize mesh depth per train view (torch z-buffer), q visible iff depth match (3x3)
 3. Carrier: KD-tree over alpha>0.1 gaussian centers;
      primary  d_basin(q)=min_k-nn median_view ||proj(mu)-proj(q)||px
      2nd      d3d(q)=min ||q-mu|| -> px via z/f
      extent   min Mahalanobis to sharp splats (max scale < s_max)
 4. CR@tau tau in {2,3,5,10}px ; contiguous void-length histogram
"""
import json, numpy as np, trimesh, os, sys, time
from plyfile import PlyData
from scipy.spatial import cKDTree
import torch

ROOT="/home/u00134/cglib"; SCENE=sys.argv[1] if len(sys.argv)>1 else "lego"
MESH=f"/home/u00134/3dgs_line/bcr/meshes/NeRF_Mesh/{SCENE}_new.obj"
OUT="/home/u00134/3dgs_line/bcr/out"; FIG="/home/u00134/3dgs_line/bcr/figs"
os.makedirs(OUT,exist_ok=True)
W=H=800
dev="cuda" if torch.cuda.is_available() else "cpu"
DS=0.0015                 # crease discretization step (world)
EPS_VIS=0.015             # depth-match tolerance (world)
KNN=20
TAUS=[2,3,5,10]
S_MAX_PX=5.0              # extent test: only trust splats with max scale < this many px
t0=time.time()

# ---------- cameras ----------
d=json.load(open(f"{ROOT}/data/full/{SCENE}/transforms_train.json"))
f=0.5*W/np.tan(0.5*d["camera_angle_x"])
K=np.array([[f,0,W/2],[0,f,H/2],[0,0,1]],np.float64)
def w2c_of(fr):
    c2w=np.array(fr["transform_matrix"],np.float64)@np.diag([1,-1,-1,1.])
    return np.linalg.inv(c2w)
W2C=[w2c_of(fr) for fr in d["frames"]]
NV=len(W2C)
print(f"[cam] f={f:.1f} views={NV}  t={time.time()-t0:.0f}s")

# ---------- mesh + creases ----------
m=trimesh.load(MESH,process=True)
if isinstance(m,trimesh.Scene): m=trimesh.util.concatenate([g for g in m.geometry.values()])
V=np.asarray(m.vertices,np.float64); Fc=np.asarray(m.faces)
print(f"[mesh] V={len(V)} F={len(Fc)}")
fa_angles=m.face_adjacency_angles                      # radians per adjacent face pair
fa_edges=m.face_adjacency_edges                        # vertex-index pairs of shared edge
def sample_edges(vidx_pairs):
    a=V[vidx_pairs[:,0]]; b=V[vidx_pairs[:,1]]
    seg=b-a; L=np.linalg.norm(seg,axis=1)
    pts=[]
    for i in range(len(a)):
        n=max(2,int(L[i]/DS)+1)
        ts=np.linspace(0,1,n)
        pts.append(a[i][None]+ts[:,None]*seg[i][None])
    return np.concatenate(pts,0) if pts else np.zeros((0,3))

CREASE_SETS={}
for deg in (20,30,45):
    thr=np.deg2rad(deg)
    sel=fa_edges[fa_angles>=thr]
    q=sample_edges(sel)
    CREASE_SETS[deg]=q
    print(f"[crease] theta>={deg}deg: edges={len(sel)} sampled_pts={len(q)}")

# ---------- gaussians ----------
p=PlyData.read(f"{ROOT}/outputs/{SCENE}_static/point_cloud.ply")["vertex"]
gx=np.stack([p["x"],p["y"],p["z"]],1).astype(np.float64)
op=1/(1+np.exp(-np.asarray(p["opacity"])))
scale=np.exp(np.stack([p["scale_0"],p["scale_1"],p["scale_2"]],1)).astype(np.float64)
quat=np.stack([p["rot_0"],p["rot_1"],p["rot_2"],p["rot_3"]],1).astype(np.float64)
keep=op>0.1
gx=gx[keep]; scale=scale[keep]; quat=quat[keep]
print(f"[3dgs] carriers alpha>0.1 = {len(gx)}")
tree=cKDTree(gx)

# ---------- depth rasterizer (torch, batched over faces) ----------
Vt=torch.tensor(V,device=dev); Ft=torch.tensor(Fc,dtype=torch.long,device=dev)
Kt=torch.tensor(K,device=dev)
def render_depth(w2c):
    w2ct=torch.tensor(w2c,device=dev,dtype=torch.float32)
    ph=torch.cat([Vt.float(),torch.ones(len(Vt),1,device=dev)],1)
    cam=(w2ct@ph.T).T[:,:3]
    z=cam[:,2]
    uv=(Kt.float()@cam.T).T
    uvz=uv[:,2].clamp(min=1e-6)
    px=uv[:,0]/uvz; py=uv[:,1]/uvz
    tri=Ft
    zc=z[tri]                              # (F,3)
    front=(zc>0).all(1)
    tri=tri[front]; 
    if len(tri)==0: return torch.full((H,W),1e9,device=dev)
    pxt=px[tri]; pyt=py[tri]; zt=zc[front]
    # bounding box per triangle
    x0=torch.floor(pxt.min(1).values).clamp(0,W-1).long()
    x1=torch.ceil (pxt.max(1).values).clamp(0,W-1).long()
    y0=torch.floor(pyt.min(1).values).clamp(0,H-1).long()
    y1=torch.ceil (pyt.max(1).values).clamp(0,H-1).long()
    depth=torch.full((H,W),1e9,device=dev)
    # rasterize small triangles by scatter of vertex depth into their pixel bbox center is too coarse;
    # use point-splat of triangle centroids + barycentric fill for small tris (mesh is dense ~2M faces => tris ~subpixel)
    cx=pxt.mean(1); cy=pyt.mean(1); cz=zt.mean(1)
    valid=(cx>=0)&(cx<W)&(cy>=0)&(cy<H)&(cz>0)
    xi=cx[valid].long(); yi=cy[valid].long(); zi=cz[valid]
    flat=yi*W+xi
    df=depth.view(-1)
    # z-min scatter
    order=torch.argsort(zi,descending=True)
    df[flat[order]]=zi[order]
    return depth.view(H,W)

# Because faces are ~subpixel dense, centroid splat gives a solid depth buffer.
print("[depth] rendering", NV, "views ...")
DEPTH=torch.stack([render_depth(w2c) for w2c in W2C])   # (NV,H,W)
DEPTH_np=DEPTH.detach().cpu().numpy()                    # cache once
print(f"[depth] done t={time.time()-t0:.0f}s")

def project_np(pts,w2c):
    ph=np.concatenate([pts,np.ones((len(pts),1))],1)
    cam=(w2c@ph.T).T[:,:3]; z=cam[:,2]
    uv=(K@cam.T).T; uv=uv[:,:2]/uv[:,2:3]
    return uv,z

def visibility(q):
    """return list over views: bool visible per point -> (Npts,NV) bool, plus proj uv per view"""
    N=len(q); vis=np.zeros((N,NV),bool); UV=np.zeros((N,NV,2)); ZZ=np.zeros((N,NV))
    for k in range(NV):
        uv,z=project_np(q,W2C[k]); UV[:,k]=uv; ZZ[:,k]=z
        inb=(z>0)&(uv[:,0]>=0)&(uv[:,0]<W)&(uv[:,1]>=0)&(uv[:,1]<H)
        idx=np.where(inb)[0]
        if len(idx)==0: continue
        u=uv[idx,0].astype(int); v=uv[idx,1].astype(int)
        db=DEPTH_np[k]
        # 3x3 min-diff
        best=np.full(len(idx),1e9)
        for du in (-1,0,1):
            for dv in (-1,0,1):
                uu=np.clip(u+du,0,W-1); vv=np.clip(v+dv,0,H-1)
                best=np.minimum(best,np.abs(z[idx]-db[vv,uu]))
        ok=best<EPS_VIS
        vis[idx[ok],k]=True
    return vis,UV,ZZ

def carrier_recall(q):
    vis,UV,ZZ=visibility(q)
    nvis=vis.sum(1)
    keepm=nvis>=3
    q=q[keepm]; vis=vis[keepm]; UV=UV[keepm]; ZZ=ZZ[keepm]
    N=len(q)
    if N==0: return None
    dist3d,knn=tree.query(q,k=KNN)          # (N,KNN)
    # --- GPU-vectorized reprojection error ---
    # project ALL gaussians once per view is huge; instead project only the union of KNN gaussians.
    uniq=np.unique(knn.ravel())
    remap=-np.ones(len(gx),np.int64); remap[uniq]=np.arange(len(uniq))
    gsub=torch.tensor(gx[uniq],device=dev,dtype=torch.float32)          # (U,3)
    gsub_h=torch.cat([gsub,torch.ones(len(gsub),1,device=dev)],1)
    knn_r=torch.tensor(remap[knn],device=dev)                          # (N,KNN) -> idx into uniq
    UVt=torch.tensor(UV,device=dev,dtype=torch.float32)                # (N,NV,2)
    vist=torch.tensor(vis,device=dev)                                  # (N,NV) bool
    Kt2=torch.tensor(K,device=dev,dtype=torch.float32)
    # gaussian proj per view: (NV,U,2)
    guv=torch.empty(NV,len(gsub),2,device=dev)
    for k in range(NV):
        w=torch.tensor(W2C[k],device=dev,dtype=torch.float32)
        cam=(w@gsub_h.T).T[:,:3]
        uv=(Kt2@cam.T).T
        guv[k]=uv[:,:2]/uv[:,2:3].clamp(min=1e-6)
    # accumulate median reproj err per (point, knn) over visible views -> do in chunks over N
    d_basin=np.full(N,1e9)
    CH=4000
    for s in range(0,N,CH):
        e=min(N,s+CH); n=e-s
        kr=knn_r[s:e]                      # (n,KNN)
        vv=vist[s:e]                       # (n,NV)
        uvp=UVt[s:e]                       # (n,NV,2)
        # gather gaussian projections for these knn across all views: (n,KNN,NV,2)
        gk=guv[:,kr]                       # (NV,n,KNN,2)
        gk=gk.permute(1,2,0,3)             # (n,KNN,NV,2)
        err=torch.linalg.norm(gk-uvp[:,None,:,:],dim=3)   # (n,KNN,NV)
        big=~vv[:,None,:]                  # invisible mask
        err=err.masked_fill(big, float('nan'))
        med=torch.nanmedian(err,dim=2).values             # (n,KNN)
        med=torch.nan_to_num(med,nan=1e9)
        d_basin[s:e]=med.min(1).values.cpu().numpy()
    # 3d euclidean -> px via median visible depth
    zmed=np.array([np.median(ZZ[i,vis[i]]) for i in range(N)])
    d3d_px=dist3d[:,0]*f/np.clip(zmed,1e-6,None)
    res={"N":int(N)}
    for t in TAUS:
        res[f"CR_basin@{t}"]=float((d_basin<=t).mean())
        res[f"CR_3d@{t}"]=float((d3d_px<=t).mean())
    return res,d_basin,q,keepm

print("\n===== RESULTS =====")
CAP=int(os.environ.get("CAP","200000"))
summary={"scene":SCENE,"f":float(f),"n_carriers":int(len(gx))}
for deg,q in CREASE_SETS.items():
    if len(q)>CAP:   # cap for speed, random subsample
        sel=np.random.RandomState(0).choice(len(q),CAP,replace=False); q=q[sel]
    tq=time.time()
    out=carrier_recall(q)
    if out is None: 
        print(f"theta={deg}: no visible pts"); continue
    res,d_basin,qv,_=out
    summary[f"theta{deg}"]=res
    line=f"theta>={deg}deg  Nvis={res['N']}  " + "  ".join(f"CRbasin@{t}={res[f'CR_basin@{t}']:.3f}" for t in TAUS)
    print(line + f"   ({time.time()-tq:.0f}s)")
    print("            "+ "  ".join(f"CR3d@{t}={res[f'CR_3d@{t}']:.3f}" for t in TAUS))
    if deg==30:
        np.save(f"{OUT}/{SCENE}_dbasin_t30.npy",d_basin)
        np.save(f"{OUT}/{SCENE}_q_t30.npy",qv)

json.dump(summary,open(f"{OUT}/{SCENE}_bcr.json","w"),indent=2)
print(f"\n[done] saved {OUT}/{SCENE}_bcr.json  total t={time.time()-t0:.0f}s")
