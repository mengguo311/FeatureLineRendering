"""BCR step-1: alignment gate. Load lego GT mesh, check coord-frame consistency with the
3DGS ply and the training cameras via silhouette-IoU overlay on train views.
NeRF-synthetic blender convention: transform_matrix is c2w in OpenGL frame (x right, y up, z back)."""
import json, numpy as np, trimesh, cv2, os
from plyfile import PlyData

ROOT="/home/u00134/cglib"
SCENE="lego"
MESH="/home/u00134/3dgs_line/bcr/meshes/NeRF_Mesh/lego_new.obj"
OUT="/home/u00134/3dgs_line/bcr/out"; os.makedirs(OUT,exist_ok=True)
FIG="/home/u00134/3dgs_line/bcr/figs"; os.makedirs(FIG,exist_ok=True)
W=H=800

d=json.load(open(f"{ROOT}/data/full/{SCENE}/transforms_train.json"))
f=0.5*W/np.tan(0.5*d["camera_angle_x"])
K=np.array([[f,0,W/2],[0,f,H/2],[0,0,1]])
print(f"[cam] focal={f:.2f} nframes={len(d['frames'])}")

# --- load mesh ---
m=trimesh.load(MESH,process=False)
if isinstance(m,trimesh.Scene):
    m=trimesh.util.concatenate([g for g in m.geometry.values()])
V=np.asarray(m.vertices); Fc=np.asarray(m.faces)
print(f"[mesh] V={len(V)} F={len(Fc)} bounds min={V.min(0).round(3)} max={V.max(0).round(3)}")

# --- load 3dgs centers (alpha>0.1) ---
p=PlyData.read(f"{ROOT}/outputs/{SCENE}_static/point_cloud.ply")["vertex"]
xyz=np.stack([p["x"],p["y"],p["z"]],1).astype(np.float64)
op=1/(1+np.exp(-p["opacity"])); xyz=xyz[op>0.1]
print(f"[3dgs] centers>0.1 = {len(xyz)} bounds min={xyz.min(0).round(3)} max={xyz.max(0).round(3)}")

def c2w_to_w2c(c2w):
    # blender/opengl c2w -> opencv w2c: flip y,z of camera axes
    c2w=np.array(c2w,dtype=np.float64)
    flip=np.diag([1,-1,-1,1]).astype(np.float64)
    c2w_cv=c2w@flip
    w2c=np.linalg.inv(c2w_cv)
    return w2c

def project(pts, w2c):
    ph=np.concatenate([pts,np.ones((len(pts),1))],1)
    cam=(w2c@ph.T).T[:,:3]
    z=cam[:,2]
    uv=(K@cam.T).T
    uv=uv[:,:2]/uv[:,2:3]
    return uv, z

# --- silhouette IoU on a few views: mesh points vs gaussian points vs image alpha ---
def splat_mask(uv,z,rad=2):
    msk=np.zeros((H,W),bool)
    valid=(z>0)&(uv[:,0]>=0)&(uv[:,0]<W)&(uv[:,1]>=0)&(uv[:,1]<H)
    u=uv[valid,0].astype(int); v=uv[valid,1].astype(int)
    for du in range(-rad,rad+1):
        for dv in range(-rad,rad+1):
            uu=np.clip(u+du,0,W-1); vv=np.clip(v+dv,0,H-1)
            msk[vv,uu]=True
    return msk

ious=[]
for idx in [0,25,50,75]:
    fr=d["frames"][idx]
    w2c=c2w_to_w2c(fr["transform_matrix"])
    uvm,zm=project(V,w2c)
    uvg,zg=project(xyz,w2c)
    mm=splat_mask(uvm,zm,1); mg=splat_mask(uvg,zg,2)
    # image alpha
    imgp=f"{ROOT}/data/full/{SCENE}/train/"+os.path.basename(fr["file_path"])+".png"
    ims=cv2.imread(imgp,cv2.IMREAD_UNCHANGED)
    alpha=(ims[:,:,3]>10) if (ims is not None and ims.shape[2]==4) else None
    inter=(mm&mg).sum(); union=(mm|mg).sum()
    iou_mg=inter/max(union,1)
    line=f"view{idx}: mesh-vs-gauss IoU={iou_mg:.3f}"
    if alpha is not None:
        iou_ma=(mm&alpha).sum()/max((mm|alpha).sum(),1)
        iou_ga=(mg&alpha).sum()/max((mg|alpha).sum(),1)
        line+=f"  mesh-vs-imgAlpha={iou_ma:.3f}  gauss-vs-imgAlpha={iou_ga:.3f}"
        ious.append(iou_ma)
    print("[iou] "+line)
    # save overlay
    vis=np.zeros((H,W,3),np.uint8)
    vis[mg]=[0,80,0]; vis[mm]=[0,0,255]
    if alpha is not None: vis[alpha & ~mg & ~mm]=[60,60,60]
    cv2.imwrite(f"{FIG}/align_{SCENE}_v{idx}.png",vis)

print(f"\n[GATE] mean mesh-vs-imgAlpha IoU = {np.mean(ious):.3f}  (need >0.90 to proceed)")
print("[done] overlays in figs/align_lego_v*.png")
