"""Post-evaluation readback of saved layers and own-stroke support; no rerender."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,js
import numpy as np
import json,collections

def load(path):return json.loads(path.read_text())
def npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def main():
    layers={};support=[];match=load(UNIT/'BUILD_MATCH.json')['scales'];views=load(UNIT/'CAMERAS.json')['views']
    for arm in ('F0','H','J'):
        for layer in (0,1):
            lengths=0.;ids=set();stops=collections.Counter();short=0
            for part in ('old','added'):
                paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));sel=paths['layer_id']==layer
                lengths+=float(np.linalg.norm(paths['points'][sel,1]-paths['points'][sel,0],axis=1).sum());ids.update(int(x) for x in paths['stroke_id'][sel])
                for r in load(UNIT/'asset'/(arm+'_'+part+'_SEEDS.json')):
                    if r['layer_id']!=layer:continue
                    stops.update([r['minus_stop'],r['plus_stop']]);short+=r['requested_length']-r['actual_length']>1e-6
            layers[arm+'_layer'+str(layer)]=dict(strokes=len(ids),length=lengths,stops=dict(stops),shortened_strokes=int(short))
    for view in ('orbit_61_24_5.3','orbit_241_24_5.3'):
        for arm in ('F0','H','J'):
            for layer in (0,1):
                row=collections.Counter()
                for part in ('old','added'):
                    s=npz(UNIT/'attribution'/view/(arm+'_'+part+'_SAMPLES.npz'));sel=s['layer_id']==layer;visible=sel&(s['status']==0);w=s['length_weight']
                    row['projected_length']+=float(w[sel].sum());row['proxy_visible_length']+=float(w[visible].sum())
                    for status in (1,2,3,4):row['rejected_'+str(status)]+=float(w[sel&(s['status']==status)].sum())
                    for mode,alpha in [('preS',s['legacy_alpha']),('linked_natural',s['legacy_alpha']*s['original_ID_S']),('linked_matched',s['legacy_alpha']*s['original_ID_S']*match[arm+'_linked'])]:
                        row[mode+'_missing_length']+=float(w[visible&(alpha<=.05)].sum())
                support.append(dict(view=view,arm=arm,layer=layer,**dict(row)))
    pixel=[]
    for v in views:
        kind=v['kind'];name=v['camera']['view']
        f=npz(UNIT/'build'/(name+'.npz')) if kind=='build' else npz(UNIT/kind/name/'FRAME.npz')
        old=npz(ROOT/'units/unit_006/build'/(name+'.npz')) if kind=='build' else npz(ROOT/'units/unit_006'/kind/name/'FRAME.npz')
        # The shared BUILD budget happened to retain all previous baseline scales.
        for arm in ('F0','H'):
            for link in ('linked','ungated'):
                for mode in (('natural',) if kind=='build' else ('natural','matched')):
                    key=arm+'_'+link+'_'+mode;np.testing.assert_array_equal(f[key],old[key])
        if kind=='build' or (kind=='arc' and name=='orbit_241_24_5.3'):continue
        target=f['regions']==4;row=dict(view=name)
        for arm in ('F0','H','J'):
            for layer in (0,1):
                key=arm+'_layer'+str(layer)+'_preS';row[key]=dict(target_mass=float(f[key][target].sum()),covered_pixels=int((f[key][target]>.05).sum()))
        pixel.append(row)
    js(UNIT/'LAYER_READBACK.json',dict(paths=layers,own_support=support,pixel_layers=pixel,F0_H_natural_and_matched_exact_to_unit006=True,
        scope='Separate layers and each stroke own support. Pixel layer masses are not additive because composite is supersampled union/max. H/J primary natural preS is identical; matched primary strength differs only by frozen whole-arm scalar.'))
    rows=[r for r in load(UNIT/'SUMMARY.json') if r['kind']=='dev']
    far=load(UNIT/'FAR_READBACK.json')
    print(json.dumps(dict(layers=layers,DEV=rows,far_max={pair:max(r['far_max_pixel_L1'] for r in far if r['comparison']==pair) for pair in ('F0_vs_H','F0_vs_J','H_vs_J')},target_changes=[r for r in far if r['comparison']=='H_vs_J']),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
