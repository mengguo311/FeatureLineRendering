from pathlib import Path
import numpy as np,json,sys
u=Path(sys.argv[1]);dest=Path(sys.argv[2]);c=json.loads((u/'CONFIG.json').read_text());a=np.load(u/'ORIGINAL_GAUSSIANS.npz',allow_pickle=False);b=np.load(u/'FULL_POSITION_ONLY_GAUSSIANS.npz',allow_pickle=False);m=np.load(u/'MEMBERSHIP.npz',allow_pickle=False);assigned=m['edge_id']>=0;p=float(c['p']);delta=np.linalg.norm(b['means']-a['means'],axis=1);report=dict(assigned_displacement_quantiles_p=np.quantile(delta[assigned]/p,[0,.5,.9,.95,.99,1]).tolist(),assigned_rows_above_source_scale={str(t):int(np.sum(delta[assigned]>t*p)) for t in [.01,.1,.5,1,2]},projected_center_shift={})
ready=json.loads((u/'READINESS.json').read_text())
for cam in ready['cameras']:
 E=np.asarray(cam['extrinsic']);uv=[];front=[]
 for means in [a['means'],b['means']]:
  x=means@E[:3,:3].T+E[:3,3];z=x[:,2];uv.append(np.column_stack([x[:,0]/z*cam['fx']+cam['cx'],x[:,1]/z*cam['fy']+cam['cy']]));front.append(z>.2)
 valid=assigned&front[0]&front[1]&np.isfinite(uv[0]).all(1)&np.isfinite(uv[1]).all(1)&(uv[0][:,0]>=0)&(uv[0][:,0]<cam['width'])&(uv[0][:,1]>=0)&(uv[0][:,1]<cam['height']);d=np.linalg.norm(uv[1]-uv[0],axis=1)[valid];report['projected_center_shift'][cam['view']]=dict(rows=int(valid.sum()),quantiles_pixels=np.quantile(d,[0,.5,.9,.95,.99,1]).tolist(),count_above_1_pixel=int((d>1).sum()),scope='assigned centers in original frame, front-facing in both; not surface visibility')
(dest/'PARENT_DISPLACEMENT_CONTEXT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
