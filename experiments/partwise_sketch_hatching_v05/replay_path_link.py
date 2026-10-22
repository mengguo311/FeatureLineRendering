"""Source-only cold replay and per-anchor original-ID query for unit002 assets."""
import runtime
from runtime import js,sha,output_guard
from pathlib import Path
import argparse,json,csv
import numpy as np
import base_model as base
from link_renderer import Renderer
from membership import load_binding,evaluated_tint_copy
from path_control import opacity_copy
from run_path_unit import load_protocol,read_npz
from run_unit import png,panel

def replay(unit,output,scene,view,operation,arm):
    p=load_protocol(unit);s=p['scenes'][scene];out=output_guard(output);out.mkdir(parents=True,exist_ok=False)
    c=next(c for c in s['cameras'] if c['view']==view) if view else next(c for c in s['cameras'] if c['split']=='evaluation')
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);n=len(a['means'])
    root=unit/'results'/scene;b,_=load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    z=read_npz(root/'EDIT_SELECTION.npz');np.testing.assert_array_equal(z['source_index'],b['source_index'])
    assert str(z['source_sha256'])==s['source']['sha256']
    key=operation+'_'+arm;strength=z[key]
    changed=evaluated_tint_copy(a,c,strength,z['tint']) if operation=='tint' else opacity_copy(a,strength)
    r=Renderer(out/'build');f,_=r.render(a,c);g,_=r.render(changed,c)
    checks={}
    for label,data,expected in [('baseline',f,root/c['view']/'baseline.npz'),('edit',g,root/c['view']/(key+'.npz'))]:
        old=read_npz(expected);checks[label]={k:bool(np.array_equal(v,old[k])) for k,v in data.items()}
        assert all(checks[label].values()),checks
    np.savez_compressed(out/'source.npz',**f);np.savez_compressed(out/'edited.npz',**g)
    png(out/'source.png',f['rgb']);png(out/'edited.png',g['rgb'])
    panel(out/'replay.png',[f['rgb'],g['rgb']],['Original GS / SH3','Replayed '+key],scene+' '+c['view'])
    receipt=dict(scene=scene,camera=c,operation=operation,arm=arm,checks=checks,
        source_sha256=s['source']['sha256'],binding_sha256=sha(root/'SOURCE_BINDING.npz'),
        path_binding_sha256=sha(root/'PATH_BINDING.npz'),selection_sha256=sha(root/'EDIT_SELECTION.npz'),
        original_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],
        scope='fresh process original PLY + saved original-row weights, source-only rendering; no proxy raster used')
    js(out/'REPLAY.json',receipt);print(json.dumps(receipt,default=runtime.json_default))

def query(unit,output,scene,view,segment):
    p=load_protocol(unit);s=p['scenes'][scene];root=unit/'results'/scene
    c=next(c for c in s['cameras'] if c['view']==view) if view else next(c for c in s['cameras'] if c['split']=='evaluation')
    ps=read_npz(root/c['view']/'path_support.npz');ix=np.flatnonzero(ps['segment_index']==segment)
    if len(ix)!=1:raise ValueError('segment is outside the frozen path sample set')
    k=int(ix[0]);lo,hi=ps['offsets'][k:k+2];z=read_npz(root/'EDIT_SELECTION.npz')
    out=output_guard(output);out.mkdir(parents=True,exist_ok=False)
    with (out/'original_contributors.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['source_index','accepted_alpha_T','depth','eligible','path_tint_strength','path_opacity_attenuation'])
        for i in range(lo,hi):
            row=int(ps['source_index'][i]);w.writerow([row,ps['weight'][i],ps['contributor_depth'][i],bool(ps['eligible'][i]),z['tint_path_linked'][row],z['opacity_path_linked'][row]])
    receipt={key:ps[key][k] for key in ('segment_index','stroke_id','face','bary','world','region_id','state','retained_mass','rejected_mass','total_mass','unknown')}
    receipt.update(scene=scene,camera=c,original_rows=int(hi-lo),source_sha256=s['source']['sha256'],
                   scope='all accepted full-model contributors for one anchor; eligible and rejected retained; not one kernel per point')
    js(out/'QUERY.json',receipt);print(json.dumps(receipt,default=runtime.json_default))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['replay','query']);p.add_argument('--unit',type=Path,required=True)
    p.add_argument('--scene',choices=['chair','lego'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--view')
    p.add_argument('--operation',choices=['tint','opacity'],default='opacity');p.add_argument('--arm',choices=['path_linked','nearest_path','shuffled'],default='path_linked')
    p.add_argument('--segment',type=int,default=0);a=p.parse_args()
    if a.command=='replay':replay(a.unit,a.output,a.scene,a.view,a.operation,a.arm)
    else:query(a.unit,a.output,a.scene,a.view,a.segment)
