"""Independently recover pixel depth gates from saved accepted T/depth events."""
import runtime
from runtime import js,sha
import json
import numpy as np
from linked_asset import npz
from source_query import query
UNIT=runtime.ROOT/'units/unit_004'
def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());s=npz(UNIT/'delivery/assets/whole_spacing/SOURCE_LINK.npz')['ink_strength'];checks={}
    high=json.loads((UNIT/'delivery/support/HIGHLIGHTS.json').read_text())
    assert high['build_support_sha256']==sha(UNIT/'delivery/support'/(p['build_view']+'.npz'))
    for c in p['cameras']:
        folder=UNIT/'renders'/c['view'];d=npz(folder/'PATH_SUPPORT.npz');t=npz(folder/'TRACE.npz');n=len(d['xy'])
        median=np.zeros(n);mass=np.zeros(n)
        for i,pixel in enumerate(t['sample_index']):
            mass[pixel]+=t['weight'][i]
            if t['T'][i]>.5 and np.isfinite(t['depth'][i]) and t['depth'][i]>.2:median[pixel]=t['depth'][i]
        np.testing.assert_allclose(mass,d['source_alpha'],rtol=0,atol=1e-6)
        # Original renderer stores float32 depth before applying the saved gate.
        median=median.astype(np.float32)
        ok=(d['pixel_proxy_region']==4)&np.isfinite(d['pixel_proxy_depth'])&(d['source_alpha']>=.5)
        ok&=np.abs(median-d['pixel_proxy_depth'])<=.08
        np.testing.assert_array_equal(ok,d['pixel_sample_ok'])
        np.testing.assert_array_equal(d['region_strength'],s[d['source_index']])
        js(folder/'PIXEL_GATE_READBACK.json',dict(depth_source='Recovered from accepted full-T event chain; last finite accepted depth with T>0.5',
            native_pixels=n,gate_equal=True,source_alpha_max_error=float(np.max(np.abs(mass-d['source_alpha']))),
            median_camera_z=median,pixel_sample_ok=ok))
        checks[c['view']]=dict(native_pixels=n,gate_equal=True,original_row_strength_equal=True)
    q=json.loads((UNIT/'query_reload/QUERY.json').read_text())
    expected=query(UNIT/'delivery/assets/whole_spacing',UNIT/'delivery/support','orbit_61_24_5.1',240801725082000000,.5)
    assert q==expected
    assert json.loads((UNIT/'query_unsampled/QUERY.json').read_text())['state']=='not_sampled'
    rejection=json.loads((UNIT/'logs/010_wrong_asset_expected_failure.json').read_text())
    assert rejection['child_returncode']==1
    assert 'evidence belongs to a different saved asset/source' in (UNIT/'logs/010_wrong_asset_expected_failure.log').read_text()
    js(UNIT/'SOURCE_GATE_AUDIT.json',dict(views=checks,fresh_process_query_exact=True,unsampled_state_exact=True,
        wrong_asset_rejected=True,wrong_asset_expected_returncode=1,highlight_BUILD_source_hash_match=True))
    summary=json.loads((UNIT/'SAVED_SUMMARY.json').read_text())
    for view,row in summary['views'].items():
        print(view,row['states'],'events',row['raw_events'],'eligible_mass',row['eligible_mass'])
        for key,v in row['highlights'].items():
            x=v['source_change'];print(key[-3:],'IDs',v['selected_original_ids'],'total L1',round(x['raw_total_L1'],6),
                'target_mean',round(x['target_full']['raw_L1_mean'],6),'far_other',round(x['far_other']['raw_L1_sum'],9),
                'far_bg',round(x['far_background']['raw_L1_sum'],9),'far_fraction',round(x['far_raw_fraction'],6))
    print('unique IDs',summary['highlighted_unique_source_ids'])
if __name__=='__main__':main()
