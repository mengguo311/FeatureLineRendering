"""Save, toggle, edit and render one authored Chair structure layer."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,os,shutil,argparse
import numpy as np
from linked_asset import load_asset,seal,query
from whole_asset import load_preset,render_whole
from parts_asset import part_edit
from structure import project_curve,validate_curve,load_structure

def copy_asset(asset,out):
    asset=Path(asset).resolve();load_preset(asset)
    _,_,meta,link,_=load_asset(asset);out=runtime.configure_output(out)
    for f in asset.iterdir():
        if f.is_file() and f.name!='FILES.json':shutil.copy2(f,out/f.name)
    for key in ('source_file','binding_file'):link[key]=os.path.relpath((asset/link[key]).resolve(),out)
    meta['original']['original_ply']=link['source_file']
    js(out/'asset.json',meta);js(out/'LINKED_ASSET.json',link)
    return out

def attach_structure(asset,out,curve,author,report):
    asset=Path(asset).resolve();mesh,_,_,_,_=load_asset(asset);validate_curve(mesh,curve)
    out=copy_asset(asset,out);np.savez_compressed(out/'structure.npz',**curve)
    js(out/'AUTHOR.json',author);js(out/'PROJECTION.json',report)
    config=dict(schema='chair_authored_structure_v1',enabled=True,width=1.,strength=.85,ink_color=.03,aa=2,depth_tolerance=.004,
        curve_name='Authored rear back-panel inner rim (open, uncertain left return omitted)',curve_id=240807000001,
        path_sha256=sha(out/'structure.npz'),mesh_sha256=sha(out/'mesh.npz'),author_sha256=sha(out/'AUTHOR.json'),
        source_support='None: independent proxy structural/detail layer; seat source S not applied',
        scope='Single authored source-image detail, not automatic structure/semantic recovery or physical GT. No forced closure.')
    js(out/'STRUCTURE.json',config);seal(out);load_preset(out);load_structure(out,mesh)
    for r in range(1,6):assert sha(asset/f'region_{r}.npz')==sha(out/f'region_{r}.npz')
    return out

def author_structure(asset,out,recipe,camera):
    a=json.loads(Path(recipe).read_text());mesh,_,_,_,_=load_asset(asset)
    if camera['view']!=a['camera_view']:raise ValueError('author camera mismatch')
    p,r=project_curve(mesh,camera,a['controls'],240807000001)
    return attach_structure(asset,out,p,a,r)

def toggle_structure(asset,out,enabled):
    if type(enabled) is not bool:raise ValueError('boolean on/off required')
    asset=Path(asset).resolve();mesh,_,_,_,_=load_asset(asset);_,m=load_structure(asset,mesh)
    out=copy_asset(asset,out);m['enabled']=enabled;js(out/'STRUCTURE.json',m);seal(out);load_structure(out,mesh)
    for name in ['structure.npz','mesh.npz','SOURCE_LINK.npz']+[f'region_{r}.npz' for r in range(1,6)]:
        assert sha(asset/name)==sha(out/name)
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('author','toggle','edit','render','query'):
        q=sub.add_parser(name);q.add_argument('--asset',type=Path,required=True)
        if name!='query':q.add_argument('--out',type=Path,required=True)
        if name=='author':q.add_argument('--recipe',type=Path,required=True)
        if name in ('author','render'):q.add_argument('--camera',type=Path,required=True)
        if name=='toggle':q.add_argument('--enabled',choices=['on','off'],required=True)
        if name=='render':q.add_argument('--reference',type=Path)
        if name=='edit':
            q.add_argument('--region',type=int,choices=[4,5],required=True)
            for k in ('angle','spacing','length'):q.add_argument('--'+k,type=float)
        if name=='query':q.add_argument('--ids',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='author':author_structure(a.asset,a.out,a.recipe,json.loads(a.camera.read_text()))
    elif a.command=='toggle':toggle_structure(a.asset,a.out,a.enabled=='on')
    elif a.command=='edit':
        changes={k:getattr(a,k) for k in ('angle','spacing','length') if getattr(a,k) is not None}
        if not changes:p.error('provide angle, spacing or length')
        part_edit(a.asset,a.out,a.region,changes);mesh,_,_,_,_=load_asset(a.out);load_structure(a.out,mesh)
    elif a.command=='query':print(json.dumps(query(a.asset,a.ids),default=runtime.json_default,indent=2))
    else:render_whole(a.asset,a.out,json.loads(a.camera.read_text()),a.reference)
if __name__=='__main__':main()
