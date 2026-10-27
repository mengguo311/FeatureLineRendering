"""Saved selective Chair preset, with the inherited two-region editor."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,os,shutil
import numpy as np
from linked_asset import load_asset,seal,query
from whole_asset import STYLE_PRESET,load_preset,render_whole
from parts_asset import part_edit,regenerate_paths

CHANGES={4:dict(length=.44),5:dict(spacing=.0675,length=.44)}
def create_style(asset,out):
    asset=Path(asset).resolve();load_preset(asset)
    mesh,paths,meta,link,_=load_asset(asset);parent=sha(asset/'FILES.json')
    ids=np.concatenate([p['stroke_id'] for p in paths.values()]);new={}
    for r,changes in CHANGES.items():
        style={**meta['styles'][str(r)],**changes}
        if style.get('cross_enabled',False):raise ValueError('frozen style requires a single direction')
        new[r],stats=regenerate_paths(mesh,r,style,parent,ids)
        ids=np.concatenate([ids,new[r]['stroke_id']])
        meta['styles'][str(r)]=style;meta['statistics'][str(r)]=stats
    out=runtime.configure_output(out)
    for f in asset.iterdir():
        if f.is_file() and f.name!='FILES.json':shutil.copy2(f,out/f.name)
    for r,data in new.items():np.savez_compressed(out/f'region_{r}.npz',**data)
    for k in ('source_file','binding_file'):link[k]=os.path.relpath((asset/link[k]).resolve(),out)
    meta['original']['original_ply']=link['source_file']
    meta['style_preset_edit']=dict(parent_asset_sha256=parent,changes=CHANGES,hidden_regions=[1,2,3],
        scope='Bundled style and display-scope intervention, not isolated smoothness or Gaussian support gain; no geometry or label changes.')
    meta['linked_scope']='Fixed global original-GS paper; source S only gates region4. Region5 is proxy-only. Regions1-3 paths retained but their hatching hidden.'
    link.update(parent=parent,active_regions=[4,5],editable_proxy_regions=[4,5],path_source_certificate='None: new identities; unit004 evidence not transferred.')
    js(out/'asset.json',meta);js(out/'LINKED_ASSET.json',link);js(out/'WHOLE_PRESET.json',STYLE_PRESET);seal(out);load_preset(out)
    for r in (1,2,3):assert sha(asset/f'region_{r}.npz')==sha(out/f'region_{r}.npz')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('preset','edit','render','query'):
        q=sub.add_parser(name);q.add_argument('--asset',type=Path,required=True)
        if name!='query':q.add_argument('--out',type=Path,required=True)
        if name=='edit':
            q.add_argument('--region',type=int,choices=[4,5],required=True)
            for key in ('angle','spacing','length'):q.add_argument('--'+key,type=float)
        if name=='render':q.add_argument('--camera',type=Path,required=True);q.add_argument('--reference',type=Path)
        if name=='query':q.add_argument('--ids',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='preset':create_style(a.asset,a.out)
    elif a.command=='edit':
        changes={k:getattr(a,k) for k in ('angle','spacing','length') if getattr(a,k) is not None}
        if not changes:p.error('provide angle, spacing or length')
        part_edit(a.asset,a.out,a.region,changes)
    elif a.command=='render':render_whole(a.asset,a.out,json.loads(a.camera.read_text()),a.reference)
    else:print(json.dumps(query(a.asset,a.ids),indent=2,default=runtime.json_default))
if __name__=='__main__':main()
