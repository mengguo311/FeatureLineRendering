import runtime
from runtime import sha,js
import numpy as np
from linked_asset import load_asset
from structure import load_structure
from structure_asset import toggle_structure
from parts_asset import part_edit
UNIT=runtime.ROOT/'units/unit_007'
def main():
    on=UNIT/'delivery/assets/on';off=UNIT/'delivery/assets/off';base=UNIT/'delivery/assets/base'
    mesh,paths,meta,_,_=load_asset(on);p,c=load_structure(on,mesh);q,d=load_structure(off,mesh)
    assert c['enabled'] and not d['enabled']
    for key in p:np.testing.assert_array_equal(p[key],q[key])
    for r in range(1,6):assert sha(on/f'region_{r}.npz')==sha(off/f'region_{r}.npz')==sha(base/f'region_{r}.npz')
    restored=toggle_structure(off,UNIT/'tests/restored_on',True)
    assert sha(restored/'structure.npz')==sha(on/'structure.npz')
    _,m=load_structure(restored,mesh);assert m==c
    edited=part_edit(on,UNIT/'tests/edited_upper_back',5,{'angle':meta['styles']['5']['angle']+1.})
    assert sha(edited/'region_5.npz')!=sha(on/'region_5.npz')
    for r in (1,2,3,4):assert sha(edited/f'region_{r}.npz')==sha(on/f'region_{r}.npz')
    assert sha(edited/'structure.npz')==sha(on/'structure.npz')
    e,_,_,_,_=load_asset(edited);load_structure(edited,e)
    try:toggle_structure(on,UNIT/'tests/invalid','yes')
    except ValueError:pass
    else:raise AssertionError('invalid switch accepted')
    js(UNIT/'SAVED_ASSET_TEST.json',dict(groups=3,save_toggle_restore=True,all_hatch_bytes_fixed_on_off=True,nonzero_region5_edit_preserves_structure_and_other_paths=True,
        scope='Functional edit check only; no extra scientific render or quality arm',invalid_switch_rejected=True))
    print('3 saved-asset test groups passed')
if __name__=='__main__':main()
