"""Query sampled path evidence or render a saved original-kernel highlight."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,time
import numpy as np
from linked_asset import load_asset,npz,png,source_hashes
from path_source import query_arrays

def load_selection(asset,evidence):
    mesh,paths,meta,link,b=load_asset(asset)
    saved=json.loads((Path(evidence)/'HIGHLIGHTS.json').read_text())
    if saved['asset_manifest_sha256']!=sha(Path(asset)/'FILES.json') or saved['source_sha256']!=link['source_sha256'] or saved['source_count']!=link['source_count']:
        raise ValueError('evidence belongs to a different saved asset/source; regenerated paths need fresh samples')
    return saved,link

def query(asset,evidence,view,stroke,fraction):
    saved,link=load_selection(asset,evidence);evidence=Path(evidence)
    meta=json.loads((evidence/(view+'.json')).read_text())
    if meta['asset_manifest_sha256']!=sha(Path(asset)/'FILES.json') or meta['source_sha256']!=link['source_sha256']:
        raise ValueError('view evidence belongs to another asset/source')
    file=evidence/(view+'.npz')
    if sha(file)!=meta['csr_sha256']:raise ValueError('CSR checksum mismatch')
    d=npz(file);result=query_arrays(d,stroke,fraction)
    result.update(camera=meta['camera'],source_sha256=link['source_sha256'],source_count=link['source_count'],
        highlight_source_ids=saved['paths'].get(str(stroke),[]),highlight_strength=saved['strength'],
        paper_scope='Whole presentation overrides all original-row colors; region strength here is seat S responsibility, not applied global paper permission')
    if 'anchor_index' in result:
        k=result['anchor_index'];result.update(projected_uv=d['uv'][k].tolist(),world_camera_z=float(d['camera_z'][k]),
            own_post=float(d['own_post'][k]),pixel_coordinates=d['xy'].tolist())
    return result

def highlight(asset,evidence,view,stroke,out,reference=None):
    import base_model as base
    from link_renderer import Renderer
    from membership import evaluated_tint_copy
    start=time.monotonic();asset=Path(asset).resolve();evidence=Path(evidence);saved,link=load_selection(asset,evidence)
    if str(stroke) not in saved['paths']:raise ValueError('path not sampled; cannot invent highlight selection')
    c=json.loads((evidence/(view+'.json')).read_text())['camera'];out=runtime.configure_output(out)
    a=base.load_source((asset/link['source_file']).resolve(),link['source_sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    before=source_hashes(a);r=Renderer(out/'build');original,_=r.render(a,c)
    ids=np.asarray(saved['paths'][str(stroke)],np.int64)
    if len(ids) and ((ids<0).any() or (ids>=len(a['means'])).any() or len(np.unique(ids))!=len(ids)):raise ValueError('invalid original IDs')
    strength=np.zeros(len(a['means']));strength[ids]=saved['strength']
    edited,_=r.render(evaluated_tint_copy(a,c,strength,saved['color']),c)
    np.testing.assert_array_equal(original['alpha'],edited['alpha'])
    equal=None
    if reference:
        prior=npz(Path(reference)/'HIGHLIGHTS.npz');equal=bool(np.array_equal(prior[str(stroke)],edited['rgb']));assert equal
        np.testing.assert_array_equal(npz(Path(reference)/'FRAME.npz')['source'],original['rgb'])
    assert source_hashes(a)==before
    png(out/'source.png',original['rgb']);png(out/'highlight.png',edited['rgb'])
    np.savez_compressed(out/'FRAME.npz',source=original['rgb'],highlight=edited['rgb'],source_alpha=original['alpha'])
    js(out/'RELOAD_RECEIPT.json',dict(camera=c,stroke_id=stroke,selected_ids=len(ids),highlight_manifest_sha256=sha(evidence/'HIGHLIGHTS.json'),
        cold_original_GS=True,source_arrays_unchanged=True,array_equal=equal,seconds=time.monotonic()-start,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()}))
    print(json.dumps(dict(out=str(out),array_equal=equal,selected_ids=len(ids))),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['query','highlight'])
    p.add_argument('--asset',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--view',required=True);p.add_argument('--stroke-id',type=int,required=True);p.add_argument('--fraction',type=float,default=.5)
    p.add_argument('--out',type=Path);p.add_argument('--reference',type=Path);a=p.parse_args()
    if a.command=='query':
        result=query(a.asset,a.evidence,a.view,a.stroke_id,a.fraction)
        if a.out:
            out=runtime.configure_output(a.out);js(out/'QUERY.json',result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    else:
        if not a.out:p.error('highlight needs --out')
        highlight(a.asset,a.evidence,a.view,a.stroke_id,a.out,a.reference)
if __name__=='__main__':main()
