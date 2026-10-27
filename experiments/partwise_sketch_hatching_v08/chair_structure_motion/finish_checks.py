import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from linked_asset import load_asset,npz,query
from structure import load_structure
from parts_asset import part_edit
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008';CODE=Path(__file__).parent
def main():
    verify_unit(UNIT);on=UNIT/'delivery/assets/on';saved=UNIT/'saved_off'
    mesh,paths,meta,link,b=load_asset(on);_,off_config=load_structure(saved,mesh);assert off_config['enabled'] is False
    for name in ['structure.npz','mesh.npz','SOURCE_LINK.npz']+[f'region_{r}.npz' for r in range(1,6)]:assert sha(on/name)==sha(saved/name)
    equal={}
    for arm in ('on','off'):
        a=npz(UNIT/'renders/000'/arm/'FRAME.npz');c=npz(UNIT/'cold_reload/000'/arm/'FRAME.npz')
        assert set(a)==set(c);equal[arm]={k:bool(np.array_equal(v,c[k])) for k,v in a.items()};assert all(equal[arm].values())
    a=npz(UNIT/'renders/000/OBSERVATIONS.npz');c=npz(UNIT/'cold_reload/000/OBSERVATIONS.npz')
    for k,v in a.items():np.testing.assert_array_equal(v,c[k])
    edited=part_edit(on,UNIT/'engineering_checks/edited_back',5,{'angle':meta['styles']['5']['angle']+1})
    assert sha(edited/'region_5.npz')!=sha(on/'region_5.npz')
    for name in ['structure.npz','WHOLE_PRESET.json','mesh.npz','SOURCE_LINK.npz']+[f'region_{r}.npz' for r in (1,2,3,4)]:assert sha(edited/name)==sha(on/name)
    e,_,_,_,_=load_asset(edited);load_structure(edited,e)
    ids=[0,int(np.flatnonzero((b['region_id']==4)&~b['unknown'])[0]),int(np.flatnonzero((b['region_id']==5)&~b['unknown'])[0]),256689]
    js(UNIT/'SOURCE_QUERY.json',query(on,ids))
    compile_records=[]
    for p in (UNIT/'renders/build/COMPILE.json',UNIT/'cold_reload/build/COMPILE.json'):
        entries=json.loads(p.read_text());assert all(r['returncode']==0 for r in entries)
        compile_records.append(dict(path=str(p.relative_to(UNIT)),returncodes=[r['returncode'] for r in entries]))
    frozen=json.loads((UNIT/'SOURCE_LOCK.json').read_text());package=[]
    for name,h in frozen.items():
        p=UNIT/'delivery/code'/name
        if p.exists():assert sha(p)==h;package.append(name)
    js(UNIT/'FINAL_VERIFICATION.json',dict(cold_pair_arrays=equal,observations_exact=True,package_files_exact=package,
        saved_off_all_hatch_and_structure_bytes_unchanged=True,nonzero_region5_edit_preserves_non_target_and_structure=True,
        editor_test_scope='Functional +1-degree edit only; no scientific render or extra quality candidate',
        source_query_ids=ids,compile_records=compile_records,input_and_decision_unchanged=True,local_only=True))
    verify_unit(UNIT);print('Cold48 arrays and observations exact; save/query/nonzero edit checks passed',flush=True)
if __name__=='__main__':main()
