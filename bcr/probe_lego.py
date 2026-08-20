import json, numpy as np
from plyfile import PlyData
d=json.load(open("/home/u00134/cglib/data/full/lego/transforms_train.json"))
print("camera_angle_x",d["camera_angle_x"],"n",len(d["frames"]))
c2w=np.array(d["frames"][0]["transform_matrix"])
print("frame0 cam pos:",c2w[:3,3], "dist", round(float(np.linalg.norm(c2w[:3,3])),3))
p=PlyData.read("/home/u00134/cglib/outputs/lego_static/point_cloud.ply")["vertex"]
xyz=np.stack([p["x"],p["y"],p["z"]],1)
op=1/(1+np.exp(-p["opacity"]))
print("N gauss",len(xyz))
print("xyz min",xyz.min(0).round(3),"max",xyz.max(0).round(3),"center",xyz.mean(0).round(3))
m=op>0.1
print("frac opacity>0.1:",round(float(m.mean()),3))
xyzf=xyz[m]
print("filtered xyz min",xyzf.min(0).round(2),"max",xyzf.max(0).round(2))
sc=np.exp(np.stack([p["scale_0"],p["scale_1"],p["scale_2"]],1))
print("median splat scale/axis:",np.median(sc,0).round(4),"overall median",round(float(np.median(sc)),4))
W=800; f=0.5*W/np.tan(0.5*d["camera_angle_x"]); print("focal px",round(float(f),2))
