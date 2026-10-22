"""Cold source-only replay and unpruned saved path -> original-ID inspection."""
import runtime
from runtime import js,sha,output_guard,now
from pathlib import Path
import argparse,csv,json
import numpy as np
import base_model as base
from footprint import FootprintRenderer
from membership import evaluated_tint_copy
from path_control import opacity_copy
from run_path_unit import read_npz
from run_footprint_unit import load,ARMS
from run_unit import png,arrays_hash

def run(unit,scene,index,operation,arm,output,query=False):
    p=load(unit);s=p['scenes'][scene];root=unit/'results'/scene
    c=[v for v in s['cameras'] if v['split']=='evaluation'][index]
    output=output_guard(output);output.mkdir(parents=True,exist_ok=False)
    selection=read_npz(root/'EDIT_SELECTION.npz');q=read_npz(root/'FOOTPRINT_BINDING.npz')
    np.testing.assert_array_equal(selection['source_index'],np.arange(s['source_count']))
    assert str(selection['source_sha256'])==s['source']['sha256']
    if query:
        ps=read_npz(root/c['view']/'path_support.npz');written=0
        with (output/'path_original_ID_support.csv').open('w') as f:
            writer=csv.writer(f);writer.writerow(['segment_index','stroke_id','region_id','face','bary0','bary1','bary2','sample_index','state','source_index','alpha_T','depth','depth_eligible','tint_strength','weighted_tint_support','footprint_unknown','BUILD_far_fraction'])
            for k,(lo,hi) in enumerate(zip(ps['offsets'][:-1],ps['offsets'][1:])):
                for j in range(lo,hi):
                    gid=ps['source_index'][j];st=selection[arm][gid]
                    writer.writerow([ps['segment_index'][k],ps['stroke_id'][k],ps['region_id'][k],ps['face'][k],*ps['bary'][k],ps['sample_index'][k],ps['state'][k],gid,ps['weight'][j],ps['contributor_depth'][j],ps['eligible'][j],st,ps['weight'][j]*st,q['unknown'][gid],q['far_fraction'][gid]])
                    written+=1
        # A separate anchor table keeps anchors with zero events, occluded and UNKNOWN.
        np.savez_compressed(output/'ALL_ANCHORS.npz',**{k:ps[k] for k in ('segment_index','stroke_id','region_id','face','bary','world','sample_index','state','unknown','total_mass','retained_mass')})
        result=dict(scene=scene,camera=c,arm=arm,rows=written,anchors=len(ps['state']),unknown_anchors=int(ps['unknown'].sum()),
            no_weak_or_occluded_records_pruned=True,source_sha256=s['source']['sha256'],protocol_sha256=sha(unit/'PROTOCOL.json'))
    else:
        a=base.load_source(s['source']['original_ply'],s['source']['sha256']);a['source_index']=np.arange(len(a['means']))
        original=arrays_hash(a);r=FootprintRenderer(output/'build')
        if operation=='tint':
            changed=evaluated_tint_copy(a,c,selection[arm],selection['tint']);filename='tint_'+arm+'.npz'
        else:
            if arm!='specific':raise ValueError('opacity is a specific-arm diagnostic only')
            cand=read_npz(root/'CANDIDATES.npz');changed=opacity_copy(a,cand[arm],.5);filename='opacity_specific.npz'
        frame,_=r.render(changed,c);expected=read_npz(root/c['view']/filename)
        equal={k:bool(np.array_equal(v,expected[k])) for k,v in frame.items()};assert all(equal.values())
        np.savez_compressed(output/'source_replay.npz',**frame);png(output/'source_replay.png',frame['rgb'])
        assert original==arrays_hash(a)
        result=dict(scene=scene,camera=c,operation=operation,arm=arm,all_arrays_exact=equal,
            original_arrays_unchanged=True,source_sha256=s['source']['sha256'],protocol_sha256=sha(unit/'PROTOCOL.json'),utc=now())
    js(output/'RECEIPT.json',result);print(json.dumps(result,default=runtime.json_default),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);ap.add_argument('--scene',choices=['chair','lego'],required=True)
    ap.add_argument('--index',type=int,default=2);ap.add_argument('--operation',choices=['tint','opacity'],default='tint')
    ap.add_argument('--arm',choices=ARMS,default='specific');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--query',action='store_true')
    args=ap.parse_args();run(args.unit,args.scene,args.index,args.operation,args.arm,args.output,args.query)
