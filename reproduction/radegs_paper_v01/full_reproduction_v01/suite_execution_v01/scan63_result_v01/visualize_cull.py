"""Actual raw mesh and original mask projections, CPU only; no metric fitting."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from skimage.morphology import binary_dilation,disk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan63_result_v01/diagnosis';D=H/'data/prepared/scan63';M=H/'models/scan63_paper_text_precision_v01_half_30k'
with np.load(O/'cull_cpu_arrays.npz') as z:v=z['raw_vertices'];f=z['raw_faces'];g=z['grids'];valid=z['valid']
meta=json.loads((M/'depth_normal/cameras_and_conventions.json').read_text());margins=[]
fig,axs=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,j in zip(axs,[0,12,24]):
 c=meta[j];W,HH=c['width'],c['height'];im=Image.open(D/'images'/(c['view']+'.png'));rgb=np.array(im.convert('RGB').resize((W,HH)));mask=np.asarray(im.split()[3].resize((W,HH)),dtype=np.float32)/255;dil=binary_dilation(mask/256.,disk(6));pix=(g[j]+1)*.5*np.array([W-1,HH-1]);idx=np.rint(pix).astype(int);assert valid[j].all();dist=distance_transform_edt(~dil)[idx[:,1],idx[:,0]]
 margins.append({'view':c['view'],'vertices':len(v),'all_in_frame':True,'min_distance_to_dilated_foreground_pixels':float(dist.min()),'max_distance_to_dilated_foreground_pixels':float(dist.max())})
 ax.imshow(rgb);ax.contour(dil,levels=[.5],colors=['cyan'],linewidths=.6);ax.scatter(pix[:,0],pix[:,1],s=12,c='red',marker='x');ax.set_title('View '+c['view']+' | all 29 rejected\nMin mask distance %.1f px'%dist.min());ax.set_xlim(0,W);ax.set_ylim(HH,0);ax.set_axis_off()
fig.suptitle('Actual scan63 raw mesh projections (red); original author disk(6) mask boundary (cyan)\nCPU literal C24 projection; no dilation/threshold changes. Training images used only for evaluation-mask audit.');fig.savefig(O/'scan63_mesh_mask_projections.png',dpi=150);plt.close(fig)
fig=plt.figure(figsize=(15,5),constrained_layout=True);center=v.mean(0);radius=max(np.ptp(v,axis=0))*.55
for i,(elev,azim) in enumerate([(20,-60),(20,60),(75,0)]):
 ax=fig.add_subplot(1,3,i+1,projection='3d');ax.add_collection3d(Poly3DCollection(v[f],facecolors='#5689ba',edgecolors='black',linewidths=.35));ax.set_xlim(center[0]-radius,center[0]+radius);ax.set_ylim(center[1]-radius,center[1]+radius);ax.set_zlim(center[2]-radius,center[2]+radius);ax.set_box_aspect((1,1,1));ax.view_init(elev,azim);ax.set_xlabel('x scene units');ax.set_ylabel('y');ax.set_zlabel('z');ax.set_title('elev %d / azimuth %d'%(elev,azim))
fig.suptitle('Actual unculled scan63 TSDF: 29 vertices / 22 faces, three magnified views\nNot a complete reconstruction; original all-view mask leaves no evaluable surface.');fig.savefig(O/'scan63_actual_raw_mesh_three_views.png',dpi=150);plt.close(fig)
(O/'cull_margin_and_visuals.json').write_text(json.dumps({'rows':margins,'raw_mesh_bounds_scene_units':[v.min(0).tolist(),v.max(0).tolist()],'raw_mesh_extents_scene_units':np.ptp(v,axis=0).tolist(),'visuals':['scan63_mesh_mask_projections.png','scan63_actual_raw_mesh_three_views.png'],'scientificdone':False},indent=2)+'\n');print(json.dumps(margins))
