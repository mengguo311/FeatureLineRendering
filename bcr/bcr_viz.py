"""BCR viz: color GT crease points by d_basin (green<=2 captured / yellow 2-5 marginal /
red>5 carrier-void hard-tail), overlay on a train RGB view; plus d_basin CDF plot."""
import json,numpy as np,cv2,os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT="/home/u00134/cglib"; SCENE="lego"; W=H=800
OUT="/home/u00134/3dgs_line/bcr/out"; FIG="/home/u00134/3dgs_line/bcr/figs"
d_basin=np.load(f"{OUT}/{SCENE}_dbasin_t30.npy"); q=np.load(f"{OUT}/{SCENE}_q_t30.npy")
d=json.load(open(f"{ROOT}/data/full/{SCENE}/transforms_train.json"))
f=0.5*W/np.tan(0.5*d["camera_angle_x"]); K=np.array([[f,0,W/2],[0,f,H/2],[0,0,1.]])
def w2c(fr): 
    c2w=np.array(fr["transform_matrix"])@np.diag([1,-1,-1,1.]); return np.linalg.inv(c2w)

# CDF
plt.figure(figsize=(6,4))
xs=np.sort(np.clip(d_basin,0,20)); ys=np.arange(1,len(xs)+1)/len(xs)
plt.plot(xs,ys,lw=2)
for t,c in [(2,'g'),(5,'orange'),(10,'r')]:
    cr=(d_basin<=t).mean(); plt.axvline(t,ls='--',color=c,alpha=.6); plt.text(t+.2,.1,f"CR@{t}={cr:.2f}",color=c)
plt.xlabel("d_basin (px)  = reprojection dist to nearest vanilla gaussian carrier")
plt.ylabel("cumulative frac of GT crease points"); plt.title(f"{SCENE}: Carrier Recall CDF (theta>=30, N={len(d_basin)})")
plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(f"{FIG}/{SCENE}_cdf.png",dpi=110); plt.close()
print("saved CDF")

# overlay on best view (most crease pts visible-ish -> just use view 0)
for vidx in [0,25]:
    fr=d["frames"][vidx]; Wc=w2c(fr)
    ph=np.concatenate([q,np.ones((len(q),1))],1); cam=(Wc@ph.T).T[:,:3]; z=cam[:,2]
    uv=(K@cam.T).T; uv=uv[:,:2]/uv[:,2:3]
    imgp=f"{ROOT}/data/full/{SCENE}/train/"+os.path.basename(fr["file_path"])+".png"
    im=cv2.imread(imgp,cv2.IMREAD_UNCHANGED)
    if im.shape[2]==4:
        a=im[:,:,3:4]/255.; im=(im[:,:,:3]*a+255*(1-a)).astype(np.uint8)
    vis=im.copy()
    valid=(z>0)&(uv[:,0]>=0)&(uv[:,0]<W)&(uv[:,1]>=0)&(uv[:,1]<H)
    for i in np.where(valid)[0]:
        u,v=int(uv[i,0]),int(uv[i,1]); db=d_basin[i]
        col=(0,180,0) if db<=2 else ((0,200,255) if db<=5 else (0,0,255))
        cv2.circle(vis,(u,v),1,col,-1)
    cv2.imwrite(f"{FIG}/{SCENE}_carrier_v{vidx}.png",vis)
    print(f"saved overlay v{vidx}: visible crease pts={int(valid.sum())}")
print("green<=2px captured | yellow 2-5px marginal | red>5px CARRIER VOID (hard tail)")
