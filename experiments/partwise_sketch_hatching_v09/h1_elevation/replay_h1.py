"""Cold original-GS cache check plus a fresh-process saved-config hatch replay."""
import runtime
from runtime import ROOT as UNIT,js,sha
import argparse,json,re
import numpy as np
from linked_asset import npz,source_hashes
from run_h1 import Runner,locks,save,plan

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference-key',default='006');p.add_argument('--output-name',required=True);a=p.parse_args()
    if not re.fullmatch('[A-Z0-9_]+',a.output_name):raise ValueError('simple unique output name required')
    rows={r['key']:r for r in plan()}
    if a.output_name in rows:raise ValueError('cannot overwrite science frame')
    locks();row=rows[a.reference_key];out=runtime.configure_output(UNIT/'replay'/a.output_name)
    runner=Runner();before=source_hashes(runner.source);c=row['camera']
    from link_renderer import Renderer,validate_trace
    from hybrid import paper_copy
    cache=npz(UNIT/row['cache']);xy=npz((UNIT/row['cache']).parent/'TRACE.npz')['xy']
    engine=Renderer(out/'build');source,trace=engine.render(runner.source,c,xy=xy,strength=runner.strength)
    paper,_=engine.render(paper_copy(runner.source,c,np.ones(len(runner.strength)),[.95]*3),c)
    proof=validate_trace(runner.source,c,xy,source,trace)
    for actual,expected in [(source['rgb'],cache['source']),(source['contribution'],cache['support']),(paper['rgb'],cache['paper'])]:np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    assert before==source_hashes(runner.source)
    save(out/'COLD_SOURCE.npz',**source,**{'paper_'+k:v for k,v in paper.items()})
    save(out/'COLD_TRACE.npz',xy=xy,**trace)
    runner.frame(row,key_override=a.output_name)
    checked=[]
    for rel in ['COMMON.npz','TRACE.npz','CENTERLINES.npz','B0_PATHS.npz','CONVENTIONAL.npz']+[f'{mode}/{arm}/FRAME.npz' for mode in ('natural','matched') for arm in ('B0','B1')]:
        old=npz(UNIT/'renders'/a.reference_key/rel);new=npz(UNIT/'renders'/a.output_name/rel)
        assert old.keys()==new.keys()
        for name in old:np.testing.assert_array_equal(old[name],new[name])
        checked.append(rel)
    locks()
    record=dict(reference=a.reference_key,output=a.output_name,cold_source_paper_S_exact=True,source_arrays_unchanged=True,
        trace_validation=proof,array_files_exact=checked,source_hashes=before,
        scope='Original PLY actually cold-rendered to validate the frozen cache; hatch replay then reads that identical cache, regenerates B0 and rasterizes both arms. Main science remains cached-GS, not fifteen cold GS renders.')
    js(out/'REPLAY_CHECK.json',record);print(json.dumps(record),flush=True)

if __name__=='__main__':main()
