"""Independent saved-pixel and input audit; no method tuning."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
from pathlib import Path
import json
import numpy as np
from scipy import ndimage

def arrays(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());m=json.loads((UNIT/'BUILD_MATCH.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    for f,h in p['source_hashes'].items():assert sha(UNIT/'source_snapshot'/f)==h,f
    for f,h in json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'].items():assert sha(UNIT/f)==h,f
    reference=json.loads((Path(p['previous'])/'results/lego/BINDING_LOCK.json').read_text())['source_array_hashes']
    rows=[]
    for kind,cameras in [('dev',p['scene']['evaluation_cameras']),('arc',p['arc_cameras'])]:
        for c in cameras:
            folder=UNIT/kind/c['view'];a=arrays(folder/'FRAME.npz');e=json.loads((folder/'EVALUATION.json').read_text())
            for f,h in json.loads((folder/'COMPLETED.json').read_text())['files'].items():assert sha(folder/f)==h,f
            target=a['regions']==4;inner=ndimage.binary_erosion(target,iterations=2);near=ndimage.binary_dilation(target,iterations=2)
            domains=dict(target_full=target,target_interior=inner,boundary=near&~inner,far_other=(a['regions']>0)&~near,far_background=(a['regions']==0)&~near)
            if e['provenance']['kind']=='new_complete_original_GS_renders':
                assert e['provenance']['source_array_hashes']==reference
                t=arrays(folder/'TRACE.npz')
                assert np.all((t['source_index']>=0)&(t['source_index']<p['scene']['source_count']))
                np.testing.assert_allclose(t['weight'],t['alpha']*t['T'],rtol=0,atol=1e-14)
                selection=arrays(Path(p['previous'])/'results/lego/SELECTION.npz')['primary']
                mass=np.bincount(t['sample_index'],t['weight']*selection[t['source_index']],minlength=len(t['xy']))
                xy=t['xy'];np.testing.assert_allclose(mass,a['support'][xy[:,1],xy[:,0]],rtol=0,atol=1e-6)
            else:
                old=arrays(e['provenance']['file'])
                for key in ('source','paper','support'):np.testing.assert_array_equal(a[key],old[key])
                np.testing.assert_array_equal(a['cross_raw'],old['hybrid_gated'])
            for arm in ('cross','base'):
                for level,scale in [('raw',1.),('matched',m['scales'][arm])]:
                    key=arm+'_'+level;alpha=a[arm+'_ink']*np.clip(a['support'],0,1)*scale
                    predicted=a['paper']*(1-alpha[:,:,None])+p['ink_color']*alpha[:,:,None]
                    np.testing.assert_array_equal(a[key+'_alpha'],alpha)
                    np.testing.assert_array_equal(a[key],predicted)
                    raw=np.abs(a[key]-a['source']).sum(2);clipped=np.abs(np.clip(a[key],0,1)-np.clip(a['source'],0,1)).sum(2)
                    for name,mask in domains.items():
                        stored=e['metrics'][key][name];assert stored['pixels']==int(mask.sum())
                        np.testing.assert_allclose(stored['raw_L1_sum'],float(raw[mask].sum()),rtol=0,atol=1e-6)
                        np.testing.assert_allclose(stored['clipped_L1_sum'],float(clipped[mask].sum()),rtol=0,atol=1e-6)
                    delta=np.abs(a[key]-a['paper']).sum(2)
                    np.testing.assert_allclose(e['ink'][key]['target_visible_ink_L1'],float(delta[target].sum()),rtol=0,atol=1e-6)
                    mask=(alpha>.05)&target;labels,n=ndimage.label(mask,np.ones((3,3),bool))
                    assert e['shape'][key]['visible']['pixels']==int(mask.sum())
                    assert e['shape'][key]['visible']['components']==n
            rows.append(dict(kind=kind,view=c['view'],compositor_exact=True,source_origin=e['provenance']['kind'],metrics_recomputed=True))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_verified=len(p['input_hashes']),saved_views=len(rows),views=rows,
        limitations='Saved alpha/topology/metrics and original-row trace checked. No independent semantic/native/physical or temporal ground truth.'))
    print('VALIDATED',len(rows),'views and',len(p['input_hashes']),'immutable inputs',flush=True)

if __name__=='__main__':main()
