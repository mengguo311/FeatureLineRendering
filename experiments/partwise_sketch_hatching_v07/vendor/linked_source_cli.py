#!/usr/bin/env python3
"""Package-local original-ID query and CPU linked-source replay; no training."""
import runtime
from pathlib import Path
import argparse
import json
import numpy as np
from membership import load_binding

PACKAGE = Path(__file__).resolve().parent.parent

def npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {k:z[k] for k in z.files}

def load_inputs(scene):
    folder=PACKAGE/'data'/scene
    config=json.loads((folder/'scene.json').read_text())
    binding,meta=load_binding(folder/'SOURCE_BINDING.npz',config['source_sha256'],config['source_count'])
    links=npz(folder/'SOURCE_LINK.npz')
    n=config['source_count']
    if not np.array_equal(links['source_index'], np.arange(n)):
        raise ValueError('link arrays must preserve complete original PLY row order')
    for key in ('paper_strength','ink_strength'):
        s=links[key]
        if s.shape!=(n,) or not np.isfinite(s).all() or (s<0).any() or (s>1).any():
            raise ValueError('invalid original-row '+key)
    return folder,config,binding,links,meta

def mapping(args):
    folder,config,b,links,meta=load_inputs(args.scene)
    path_binding=npz(folder/'BASELINE_PATH_BINDING.npz') if (folder/'BASELINE_PATH_BINDING.npz').exists() else None
    if path_binding is not None and not np.array_equal(path_binding['source_index'],np.arange(config['source_count'])):
        raise ValueError('baseline path binding row identity mismatch')
    rows=[]
    for i in args.ids:
        if i<0 or i>=config['source_count']:
            raise ValueError('source ID out of original PLY bounds: '+str(i))
        row={'source_index':i,'region_id':int(b['region_id'][i]),'unknown':bool(b['unknown'][i]),
             'membership':b['membership'][i].tolist(),'paper_strength':float(links['paper_strength'][i]),
             'ink_strength':float(links['ink_strength'][i])}
        for key in ('exposure','distinct_views','conflict','reason'):
            if key in b: row[key]=b[key][i].item()
        if path_binding is not None:
            row['baseline_path_support']={key:path_binding[key][i].item() for key in ('strength','accepted','total','unknown','reason','fraction','distinct_views') if key in path_binding}
            row['baseline_path_support']['scope']='Frozen v05 unit005 aggregated original-row support for sampled paths; not per-stroke attachment and not the latest region operation'
        rows.append(row)
    result={'scene':args.scene,'source_sha256':config['source_sha256'],'source_count':config['source_count'],
            'id_definition':'Zero-based ORIGINAL PLY vertex row, preserved through culling and sorting',
            'membership_definition':'Authored-region evidence channels 0..5; UNKNOWN retained; not semantic/physical probabilities',
            'binding_metadata':meta,'rows':rows}
    print(json.dumps(result,indent=2,ensure_ascii=False,default=runtime.json_default))

def render(args):
    from PIL import Image
    import base_model as base
    from link_renderer import Renderer
    from hybrid import paper_copy
    folder,config,b,links,meta=load_inputs(args.scene)
    out=runtime.configure_output(args.out)
    c=json.loads((folder/'camera.json').read_text())
    a=base.load_source(folder/'source.ply',config['source_sha256'])
    if len(a['means'])!=config['source_count']: raise ValueError('source row count mismatch')
    a['source_index']=np.arange(config['source_count'],dtype=np.int64)
    r=Renderer(runtime.output_guard(out/'build'))
    source,_=r.render(a,c,strength=links['ink_strength'])
    paper,_=r.render(paper_copy(a,c,links['paper_strength'],config.get('paper',[.95,.95,.95])),c)
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    frames={'source':source['rgb'],'paper':paper['rgb'],'support':source['contribution'],'alpha':source['alpha']}
    if args.hybrid:
        if args.scene!='lego': raise ValueError('--hybrid is the saved Lego unit010 local path replay only')
        from geometry import mesh_data
        from target_completion import render_pair
        from hybrid import compose
        target=npz(folder/'unit_008_asset/TARGET.npz')
        oldmesh=mesh_data(target['vertices'],target['faces'],target['old_face_regions'])
        newmesh=mesh_data(target['vertices'],target['faces'],target['face_regions'])
        old=npz(folder/'unit_010_asset/LOCAL_OLD_PARTITION.npz')
        added=npz(folder/'unit_010_asset/LOCAL_ADDED_PARTITION.npz')
        asset=json.loads((folder/'asset.json').read_text())
        ink,_=render_pair(oldmesh,newmesh,old,added,asset,c)
        combined,alpha=compose(frames['paper'],ink['new'],frames['support'],True,ink_color=config.get('ink_color',.03))
        frames.update(local_ink=ink['new'],local_raw=combined,local_raw_alpha=alpha)
    np.savez_compressed(runtime.output_guard(out/'FRAME.npz'),**frames)
    image_keys=['source','paper','support']+(['local_ink','local_raw'] if args.hybrid else [])
    for name in image_keys:
        array=frames[name]
        if array.ndim==2: array=np.repeat(array[:,:,None],3,axis=2)
        Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(runtime.output_guard(out/(name+'.png')))
    verification=None
    if args.verify:
        ref=npz(folder/'reference.npz')
        verification={}
        for name in ['source','paper','support']+(['local_ink','local_raw'] if args.hybrid else []):
            if frames[name].shape!=ref[name].shape: raise ValueError('reference shape mismatch: '+name)
            error=float(np.max(np.abs(frames[name].astype(float)-ref[name].astype(float))))
            verification[name]={'max_absolute_error':error,'array_equal':bool(np.array_equal(frames[name],ref[name])),
                                'pass_tolerance_1e_6':bool(error<=1e-6)}
    receipt={'utc':runtime.now(),'scene':args.scene,'camera':c,'source_sha256':config['source_sha256'],
             'inputs':{name:runtime.sha(folder/name) for name in ('source.ply','SOURCE_BINDING.npz','SOURCE_LINK.npz','camera.json','scene.json')},
             'verification':verification,'output_files':{name:runtime.sha(out/name) for name in ['FRAME.npz']+[key+'.png' for key in image_keys]},
             'hybrid_replay':bool(args.hybrid),
             'scope':'Original full-SH3 Gaussian CPU EWA + reversible per-original-row paper color override + full-T ink support. Optional --hybrid exactly reuses saved unit010 Lego local proxy paths with original-ID support; proxy ink is not native Gaussian ink. No native CUDA or semantic/physical ownership claim.',
             'source_geometry_opacity_SH_and_PLY_unchanged':True,'CUDA_VISIBLE_DEVICES':'','numeric_threads':1,
             'cpu_affinity_count':len(runtime.os.sched_getaffinity(0)) if hasattr(runtime.os,'sched_getaffinity') else None}
    runtime.js(out/'RELOAD_RECEIPT.json',receipt)
    print(json.dumps({'output':str(out),'verification':verification},indent=2))
    if verification and not all(v['pass_tolerance_1e_6'] for v in verification.values()):
        raise SystemExit('cold replay differs from packaged reference; see RELOAD_RECEIPT.json')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    q=sub.add_parser('mapping',help='Read original PLY IDs and saved binding/link strengths')
    q.add_argument('--scene',choices=('chair','lego'),required=True)
    q.add_argument('--ids',nargs='+',type=int,required=True)
    r=sub.add_parser('render',help='Cold CPU source/paper/support replay into a NEW output directory')
    r.add_argument('--scene',choices=('chair','lego'),required=True)
    r.add_argument('--out',type=Path,required=True)
    r.add_argument('--hybrid',action='store_true',help='Also replay saved Lego unit010 local proxy ink + original-ID-gated raw hybrid')
    r.add_argument('--verify',action='store_true',help='Compare source/paper/support with packaged saved reference, tolerance 1e-6')
    args=ap.parse_args()
    (mapping if args.command=='mapping' else render)(args)

if __name__=='__main__': main()
