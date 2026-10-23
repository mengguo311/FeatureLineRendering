"""Cold replay of one frozen hybrid view into a new v06 directory."""
import runtime
from runtime import ACTIVE_UNIT,output_guard,js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from geometry import mesh_data
from membership import load_binding
from link_renderer import Renderer
from render import render
from hybrid import region_strength,paper_copy,compose
from run_hybrid import png,read_npz,protocol,array_hashes

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,default=ACTIVE_UNIT)
    ap.add_argument('--scene',choices=['chair','lego'],required=True);ap.add_argument('--index',type=int,default=1)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    p=protocol(args.unit);s=p['scenes'][args.scene];c=s['evaluation_cameras'][args.index]
    out=output_guard(args.output);out.mkdir(parents=True,exist_ok=False)
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    before=array_hashes(a)
    assert sha(s['binding'])==p['input_hashes'][s['binding']]
    b,_=load_binding(s['binding'],s['source']['sha256'],len(a['means']));strength=region_strength(b)
    asset=Path(s['asset'])
    for file in ('mesh.npz','region_4.npz','asset.json'):assert sha(asset/file)==p['input_hashes'][str(asset/file)]
    m=read_npz(asset/'mesh.npz');mesh=mesh_data(m['vertices'],m['faces'],m['face_regions'])
    paths=read_npz(asset/'region_4.npz');meta=json.loads((asset/'asset.json').read_text())
    r=Renderer(output_guard(out/'build'));source,_=r.render(a,c,strength=strength)
    paper,_=r.render(paper_copy(a,c,strength,p['paper']),c)
    h=render(mesh,{4:paths},meta['styles'],c,p['supersample'],meta.get('display'))['layers'][4]
    image,alpha=compose(paper['rgb'],h,source['contribution'],True,ink_color=p['ink_color'])
    saved=read_npz(args.unit/'results'/args.scene/c['view']/'FRAME.npz')
    current=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'],reference_ink=h,hybrid_gated=image,gated_alpha=alpha)
    exact={k:bool(np.array_equal(v,saved[k])) for k,v in current.items()}
    assert all(exact.values()),exact
    assert before==array_hashes(a)
    png(out/'hybrid.png',image);png(out/'paper.png',paper['rgb']);png(out/'ink.png',1-alpha)
    np.savez_compressed(out/'REPLAY.npz',**current)
    js(out/'REPLAY.json',dict(utc=now(),scene=args.scene,camera=c,exact=exact,source_arrays_unchanged=True,
        original_PLY_sha256=s['source']['sha256'],scope=p['scope']))
    print(json.dumps(dict(scene=args.scene,view=c['view'],exact=exact)),flush=True)

if __name__=='__main__':main()
