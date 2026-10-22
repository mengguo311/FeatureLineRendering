"""Cold replay of saved ORIGINAL source-ID edits; no proxy raster dependency."""
import runtime
from runtime import js,sha,output_guard
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from link_renderer import Renderer
from membership import load_binding,evaluated_tint_copy
from run_unit import png

def replay(unit,output,view=None,arm='linked'):
    unit=Path(unit);output=output_guard(output);output.mkdir(exist_ok=False)
    p=json.loads((unit/'PROTOCOL.json').read_text())
    assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    for name,h in p['source_hashes'].items():assert sha(unit/'source_snapshot'/name)==h
    c=next(c for c in p['cameras'] if c['view']==view) if view else next(c for c in p['cameras'] if c['split']=='evaluation')
    a=base.load_source(p['source']['original_ply'],p['source']['sha256'])
    b,meta=load_binding(unit/'results/SOURCE_BINDING.npz',p['source']['sha256'],len(a['means']))
    with np.load(unit/'results/EDIT_SELECTION.npz') as z:
        np.testing.assert_array_equal(z['source_index'],b['source_index'])
        assert str(z['source_sha256'])==p['source']['sha256']
        strength=z[arm];tint=z['tint'];support=z['linked_unscaled']
    r=Renderer(output/'build');orig,_=r.render(a,c,strength=support)
    edit,_=r.render(evaluated_tint_copy(a,c,strength,tint),c)
    baseline=unit/'results'/c['view']/'baseline.npz';expected=unit/'results'/c['view']/(arm+'_edit.npz')
    checks={}
    if baseline.exists() and expected.exists():
        for label,file,data in [('baseline',baseline,orig),('edit',expected,edit)]:
            with np.load(file) as z:
                checks[label]={k:bool(np.array_equal(v,z[k])) for k,v in data.items()}
                assert all(checks[label].values())
    np.savez_compressed(output/'baseline.npz',**orig);np.savez_compressed(output/'edited.npz',**edit)
    png(output/'source.png',orig['rgb']);png(output/'edited.png',edit['rgb'])
    js(output/'REPLAY.json',dict(source_sha256=p['source']['sha256'],binding_sha256=sha(unit/'results/SOURCE_BINDING.npz'),
        edit_selection_sha256=sha(unit/'results/EDIT_SELECTION.npz'),camera=c,arm=arm,checks=checks,
        original_PLY_unchanged=sha(p['source']['original_ply'])==p['source']['sha256'],
        scope='fresh process, original full SH3 load, saved source-ID strengths, actual source-only renderer'))
    print((output/'REPLAY.json').read_text(),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--view');p.add_argument('--arm',choices=['linked','nearest_proxy','shuffled'],default='linked');a=p.parse_args()
    replay(a.unit,a.output,a.view,a.arm)
