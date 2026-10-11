"""Count original Open3D marching-cubes prerequisites; visualize negative output.

Does not extract at alternative thresholds or fit/tune against GT.
"""
import itertools
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=HDD/'full_reproduction_v01/suite_execution_v01/scan40_result_v01/diagnosis'
with np.load('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/scan40_v01/state/tsdf_attempts/1791527424817437409/volume.npz') as z:
    keys=z['key'];size=int(z['block_resolution'][0]);voxel=float(z['voxel_size'][0])
    w=z['value_%03d'%z['attr_name_weight'][0]][...,0]
    t=z['value_%03d'%z['attr_name_tsdf'][0]][...,0]
index={tuple(k):i for i,k in enumerate(keys)}
blocks,zz,yy,xx=np.nonzero(w>3.)
origins=keys[blocks]*size+np.stack((xx,yy,zz),axis=1)
full=[];crossing=[]
for origin in origins:
    values=[]
    for shift in itertools.product((0,1),repeat=3):
        xyz=origin+shift;bid=index.get(tuple(xyz//size))
        if bid is None:break
        x,y,z=xyz%size
        if w[bid,z,y,x]<=3.:break
        values.append(t[bid,z,y,x])
    if len(values)==8:
        full.append(origin.tolist())
        if min(values)<0<=max(values):crossing.append(origin.tolist())
detail={'native_threshold_condition':'all eight corners weight > 3 (strict), not >= 3',
    'voxels_weight_gt_3':len(origins),'cubes_all_corners_weight_gt_3':len(full),
    'cubes_with_supported_sign_crossing':len(crossing),
    'empty_surface_confirmed':len(crossing)==0,
    'source':'Open3D 0f06a149c4fb9406fd3e432a5cb0c024f38e2f0e VoxelBlockGridImpl.h:1385-1403',
    'alternative_threshold_extractions':0,'all_full_cubes':full,'supported_crossings':crossing}
(OUT/'marching_cubes_support.json').write_text(json.dumps(detail,indent=2)+'\n')

fig=plt.figure(figsize=(16,5))
for j,(azim,elev) in enumerate([(20,20),(110,20),(200,60)]):
    ax=fig.add_subplot(1,3,j+1,projection='3d')
    points=origins*voxel
    ax.scatter(points[:,0],points[:,1],points[:,2],s=3,c=t[blocks,zz,yy,xx],cmap='coolwarm',vmin=-1,vmax=1)
    ax.view_init(elev=elev,azim=azim);ax.set_title('Observed voxel support (>3), NOT a mesh')
    ax.set_xlabel('scene x');ax.set_ylabel('scene y');ax.set_zlabel('scene z')
fig.suptitle(f'scan40 precision-corrected 30k: {len(crossing)} supported crossing cubes\nOriginal alpha/mask >=0.5, voxel=0.002, depth_scale=1, depth_max=8; all49 views fused')
fig.tight_layout();fig.savefig(OUT/'scan40_mesh_support.png',dpi=150);plt.close(fig)
print(json.dumps({k:v for k,v in detail.items() if k not in ['all_full_cubes','supported_crossings']}))
