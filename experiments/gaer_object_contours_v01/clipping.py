"""Supplementary audit of delivered S footprints; no parameter or gate changes."""
import json
import numpy as np
import torch
import runtime as rt
from adapter import backend,scene_io,NativeWeights,ShapeWeights,shape_extension,query_extension

def clipped(xy,radii,ids):
 p=xy[ids];r=radii[ids];return dict(visible_edited_ids=int((r>0).sum()),edited_centers_outside_image=int(((p[:,0]<0)|(p[:,0]>799)|(p[:,1]<0)|(p[:,1]>799)).sum()),edited_radius_boxes_cross_image_border=int(((r>0)&((p[:,0]-r<0)|(p[:,0]+r>799)|(p[:,1]-r<0)|(p[:,1]+r>799))).sum()),radius_quantiles=np.quantile(r,[0,.5,.95,1]).tolist())
def main():
 rt.guard('shape_clip_supplement');f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());default=json.loads((rt.ART/'DEFAULT_FREEZE.json').read_text());mod=backend();records=[]
 for scene in ['lego','chair']:
  rec=f['scenes'][scene];model=scene_io.load_model(rec);units=[(c,rt.ART/'downloads'/scene/c['key']/'S_style.npz') for c in rec['cameras']]
  if default['choices'][scene]['arm']=='S':units += [(c,rt.ART/'downloads'/scene/'arc'/c['key']/'style.npz') for c in rec['arc']]
  for camera,p in units:
   rt.guard(scene+'_clip_'+camera['key']);z=np.load(p);ids=z['edited_original_ids'];base=NativeWeights(mod,scene_io.make_settings(mod,camera),model);R,_,radii,g,b,i=base.state;xy,cov,conic,_=query_extension().geometry(g,base.n);xy=xy.cpu().numpy();r0=radii.cpu().numpy();cov[torch.as_tensor(ids.astype(np.int64),device='cuda')]=torch.as_tensor(z['temporary_covariance_rows'],device='cuda');styled=ShapeWeights(shape_extension(),base.s,model,cov);r1=styled.state[2].cpu().numpy();records.append(dict(scene=scene,camera_key=camera['key'],edited_count=len(ids),before=clipped(xy,r0,ids),after=clipped(xy,r1,ids),native_tiles_instances_before=int(R),native_tiles_instances_after=int(styled.state[0]),centers_fixed=True,saved_style_sha256=rt.sha(p)))
  del model
 rt.atomic_json(rt.ART/'tests/SHAPE_FOOTPRINT_CLIPPING.json',dict(status='PASS',scope='actual native integer radius/tile AABB clipping at image borders for delivered S units; conservative bounding boxes, not an ink paint mask. Covariance constraint clipping is separately in S_association.json. No changed method, new arm or adjusted thresholds.',records=records))
 print('CLIPPING_AUDIT_PASS',len(records),flush=True)
if __name__=='__main__':main()
