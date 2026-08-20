"""Honest per-view-visible carrier overlay: only draw crease points that are actually
visible (front-facing, depth-matched) in THIS view. Renders mesh depth for the view."""
import json,numpy as np,cv2,os,trimesh,torch
ROOT="/home/u00134/cglib"; SCENE="lego"; W=H=800
OUT="/home/u00134/3dgs_line/bcr/out"; FIG="/home/u00134/3dgs_line/bcr/figs"
dev="cuda" if torch.cuda.is_available() else "cpu"
d_basin=np.load(f"{OUT}/{SCENE}_dbasin_t30.npy"); q=np.load(f"{OUT}/{SCENE}_q_t30.npy")
d=json.load(open(f"{ROOT}/data/full/{SCENE}/transforms_train.json"))
f=0.5*W/np.tan(0.5*d["camera_angle_x"]); K=np.array([[f,0,W/2],[0,f,H/2],[0,0,1.]])
def w2c(fr): c2w=np.array(fr["transform_matrix"])@np.diag([1,-1,-1,1.]); return np.linalg.inv(c2w)
EPS=0.015
m=trimesh.load(f"/home/u00134/3dgs_line/bcr/meshes/NeRF_Mesh/{SCENE}_new.obj",process=True)
if isinstance(m,trimesh.Scene): m=trimesh.util.concatenate([g for g in m.geometry.values()])
V=torch.tensor(np.asarray(m.vertices),device=dev,dtype=torch.float32); Fc=torch.tensor(np.asarray(m.faces),device=dev,dtype=torch.long)
Kt=torch.tensor(K,device=dev,dtype=torch.float32)
def render_depth(Wc):
    w=torch.tensor(Wc,device=dev,dtype=torch.float32)
    ph=torch.cat([V,torch.ones(len(V),1,device=dev)],1); cam=(w@ph.T).T[:,:3]; z=cam[:,2]
    tri=Fc; zc=z[tri]; front=(zc>0).all(1); tri=tri[front]
    uv=(Kt@cam.T).T; px=uv[:,0]/uv[:,2].clamp(min=1e-6); py=uv[:,1]/uv[:,2].clamp(min=1e-6)
    cx=px[tri].mean(1); cy=py[tri].mean(1); cz=zc[front].mean(1)
    val=(cx>=0)&(cx<W)&(cy>=0)&(cy<H)&(cz>0)
    xi=cx[val].long(); yi=cy[val].long(); zi=cz[val]
    depth=torch.full((H*W,),1e9,device=dev); flat=yi*W+xi
    order=torch.argsort(zi,descending=True); depth[flat[order]]=zi[order]
    return depth.view(H,W).cpu().numpy()

for vidx in [0,25,50]:
    fr=d["frames"][vidx]; Wc=w2c(fr); db=render_depth(Wc)
    ph=np.concatenate([q,np.ones((len(q),1))],1); cam=(Wc@ph.T).T[:,:3]; z=cam[:,2]
    uv=(K@cam.T).T; uv=uv[:,:2]/uv[:,2:3]
    imgp=f"{ROOT}/data/full/{SCENE}/train/"+os.path.basename(fr["file_path"])+".png"
    im=cv2.imread(imgp,cv2.IMREAD_UNCHANGED); a=im[:,:,3:4]/255.; im=(im[:,:,:3]*a+255*(1-a)).astype(np.uint8)
    vis=im.copy()
    inb=(z>0)&(uv[:,0]>=0)&(uv[:,0]<W)&(uv[:,1]>=0)&(uv[:,1]<H)
    idx=np.where(inb)[0]; u=uv[idx,0].astype(int); v=uv[idx,1].astype(int)
    best=np.full(len(idx),1e9)
    for du in(-1,0,1):
        for dv in(-1,0,1):
            uu=np.clip(u+du,0,W-1); vv=np.clip(v+dv,0,H-1); best=np.minimum(best,np.abs(z[idx]-db[vv,uu]))
    visible=best<EPS
    cnt={"g":0,"y":0,"r":0}
    for j,i in enumerate(idx):
        if not visible[j]: continue
        dbi=d_basin[i]; col=(0,180,0) if dbi<=2 else ((0,200,255) if dbi<=5 else (0,0,255))
        cnt["g" if dbi<=2 else ("y" if dbi<=5 else "r")]+=1
        cv2.circle(vis,(int(uv[i,0]),int(uv[i,1])),1,col,-1)
    tot=sum(cnt.values())
    cv2.imwrite(f"{FIG}/{SCENE}_visible_v{vidx}.png",vis)
    print(f"v{vidx}: visible crease pts={tot}  green={cnt['g']/tot:.2%} yellow={cnt['y']/tot:.2%} red={cnt['r']/tot:.2%}")
