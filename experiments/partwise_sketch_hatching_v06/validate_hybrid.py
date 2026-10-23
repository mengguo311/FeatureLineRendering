"""Read saved results; audit actual pixels, budget matching and frozen inputs."""
import runtime
from runtime import ACTIVE_UNIT,sha,js,now
import json
import numpy as np
from scipy import ndimage
from run_hybrid import protocol,read_npz

def main():
    p=protocol(ACTIVE_UNIT);checks={};rows=[]
    for path,h in p['input_hashes'].items():assert sha(path)==h,path
    for scene,s in p['scenes'].items():
        root=ACTIVE_UNIT/'results'/scene
        lock=json.loads((root/'BINDING_LOCK.json').read_text())
        for name,h in lock['files'].items():assert sha(root/name)==h
        selection=read_npz(root/'SELECTION.npz');binding=read_npz(s['binding'])
        expected=np.where((binding['region_id']==4)&~binding['unknown'],binding['membership'][:,4],0.)
        np.testing.assert_array_equal(selection['primary'],expected)
        np.testing.assert_array_equal(selection['source_index'],np.arange(s['source_count']))
        match=json.loads((root/'BUILD_MATCH.json').read_text());assert match['ink_effect_match_valid']
        for c in s['evaluation_cameras']:
            folder=root/c['view'];complete=json.loads((folder/'COMPLETED.json').read_text())
            for name,h in complete['files'].items():assert sha(folder/name)==h
            f=read_npz(folder/'FRAME.npz');row=json.loads((folder/'EVALUATION.json').read_text())
            target=f['proxy_regions']==4;inner=ndimage.binary_erosion(target,iterations=2)
            near=ndimage.binary_dilation(target,iterations=2)
            pixel_checks={}
            for arm,m in row['metrics'].items():
                raw=np.abs(f[arm]-f['source']).sum(2)
                clipped=np.abs(np.clip(f[arm],0,1)-np.clip(f['source'],0,1)).sum(2)
                assert abs(float(raw.sum())-m['raw_total_L1'])<1e-5
                assert abs(float(raw[~near].sum()/max(raw.sum(),1e-30))-m['far_raw_fraction'])<1e-7
                assert int(inner.sum())==m['target_interior']['pixels']
                if inner.any():assert abs(float((clipped[inner]>=.05).mean())-m['target_interior']['useful_fraction_0_05'])<1e-12
                pixel_checks[arm]=True
            retained=float(f['gated_alpha'][target].sum()/max(f['reference_ink'][target].sum(),1e-30))
            assert abs(retained-row['ink']['gated']['retained_target_ink_fraction'])<1e-7
            # Low source responsibility must not be silently normalized to opaque ink.
            np.testing.assert_allclose(f['gated_alpha'],f['reference_ink']*f['support'],rtol=0,atol=1e-7)
            assert np.all(f['support']<=f['alpha']+1e-6)
            assert np.all(f['unknown_support']<=f['alpha']+1e-6)
            checks[scene+'/'+c['view']]=dict(saved_arrays_and_PNG_hashes=True,actual_RGB_metrics=pixel_checks,
                original_row_strength_exact=True,ink_retention_exact=True,trace=row['trace'])
            rows.append(dict(scene=scene,view=c['view'],target_pixels=int(target.sum()),interior_pixels=int(inner.sum()),
                useful_fraction=row['metrics']['hybrid_gated']['target_interior']['useful_fraction_0_05'],
                paper_target_mean=row['metrics']['paper']['target_full']['clipped_L1_mean'],
                hybrid_target_mean=row['metrics']['hybrid_gated']['target_full']['clipped_L1_mean'],
                paper_far=row['metrics']['paper']['far_raw_fraction'],hybrid_far=row['metrics']['hybrid_gated']['far_raw_fraction'],
                nearest_paper_far=row['metrics']['nearest_paper']['far_raw_fraction'],
                nearest_hybrid_far=row['metrics']['nearest_hybrid']['far_raw_fraction'],
                ink_retained=retained,ink_L1=row['ink']['gated']['raw_visible_ink_L1'],
                matched_ink_L1=row['ink']['matched']['raw_visible_ink_L1'],
                unknown_mass_fraction=row['support']['target_unknown_mass_fraction'],practical_screen=row['practical_screen']))
    js(ACTIVE_UNIT/'VALIDATION.json',dict(utc=now(),frozen_inputs_unchanged=len(p['input_hashes']),checks=checks,
        per_view_summary=rows,scientific_verdict='UNCERTIFIED_CPU_MAPPING; authored-intent hybrid engineering only'))
    print(json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':main()
