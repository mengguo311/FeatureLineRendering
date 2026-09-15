"""A/B the camera convention + render one Truck frame from the trained 3DGS to LOOK.
Compares convention A (w2c_R=R.T, mine) vs B (w2c_R=R, transposed) on-screen fraction,
and rasterizes a splat preview (point-splat of albedo, not full 3DGS) at one camera so we
can eyeball whether the truck is centered/coherent. Driver-side sanity, no method change.
"""
import json, numpy as np
from plyfile import PlyData

CJ = "out/3dgs_truck/cameras.json"
PLY = "out/3dgs_truck/point_cloud/iteration_30000/point_cloud.ply"
SH_C0 = 0.28209479177387814
cams = json.load(open(CJ))
p = PlyData.read(PLY)["vertex"]
mu = np.stack([p["x"], p["y"], p["z"]], 1).astype(np.float64)
opacity = 1.0/(1.0+np.exp(-np.asarray(p["opacity"], np.float64)))
f_dc = np.stack([p["f_dc_0"], p["f_dc_1"], p["f_dc_2"]], 1).astype(np.float64)
albedo = np.clip(0.5 + SH_C0*f_dc, 0, 1)

def proj(c, w2c_R, w2c_t):
    W, H, fx, fy = c["width"], c["height"], c["fx"], c["fy"]
    K = np.array([[fx,0,W/2],[0,fy,H/2],[0,0,1]], np.float64)
    campts = (w2c_R @ mu.T).T + w2c_t
    z = campts[:,2]; uv = (K@campts.T).T; uv = uv[:,:2]/np.clip(uv[:,2:3],1e-9,None)
    infront = z>0
    on = infront & (uv[:,0]>=0)&(uv[:,0]<W)&(uv[:,1]>=0)&(uv[:,1]<H)
    return uv, z, on

fa, fb = [], []
for c in cams:
    R = np.array(c["rotation"], np.float64); pos = np.array(c["position"], np.float64)
    _,_,onA = proj(c, R.T, -R.T@pos)
    _,_,onB = proj(c, R, -R@pos)
    fa.append(onA.mean()); fb.append(onB.mean())
print(f"conv A (R.T): on-screen median {np.median(fa):.3f}")
print(f"conv B (R)  : on-screen median {np.median(fb):.3f}")

# render a splat preview at camera 0 with convention A (z-buffered point splat of albedo)
c = cams[0]; R = np.array(c["rotation"], np.float64); pos = np.array(c["position"], np.float64)
W, H, fx, fy = c["width"], c["height"], c["fx"], c["fy"]
sc = 3
Wd, Hd = W//sc, H//sc
K = np.array([[fx/sc,0,Wd/2],[0,fy/sc,Hd/2],[0,0,1]], np.float64)
w2c_R, w2c_t = R.T, -R.T@pos
campts = (w2c_R@mu.T).T + w2c_t
z = campts[:,2]; uv = (K@campts.T).T; uv = uv[:,:2]/np.clip(uv[:,2:3],1e-9,None)
sel = (z>0)&(uv[:,0]>=0)&(uv[:,0]<Wd)&(uv[:,1]>=0)&(uv[:,1]<Hd)&(opacity>0.3)
img = np.ones((Hd, Wd, 3), np.float32)
zbuf = np.full((Hd, Wd), 1e9)
order = np.argsort(-z[sel])  # far first
uvs = uv[sel][order].astype(int); zs = z[sel][order]; cols = albedo[sel][order]
for (x,y), zz, col in zip(uvs, zs, cols):
    if zz < zbuf[y,x]:
        zbuf[y,x]=zz; img[y,x]=col
from PIL import Image
Image.fromarray((img*255).astype(np.uint8)).save("out/truck_cam0_splat.png")
print("saved out/truck_cam0_splat.png  splatted px:", sel.sum())
