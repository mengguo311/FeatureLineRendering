"""Independent saved-output readback and honest full-object panels; no rendering."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from linked_asset import npz
from run_view import verify
import base_model as base

UNIT=runtime.ROOT/'units/unit_005'
def metrics(a,b,regions):
    delta=np.abs(b-a).sum(2);target=regions==5
    inside=ndimage.binary_erosion(target,iterations=2);near=ndimage.binary_dilation(target,iterations=2)
    masks=dict(target=target,interior=inside,boundary=near&~inside,far_other=(regions>0)&~near,far_background=(regions==0)&~near)
    out=dict(total_raw_L1=float(delta.sum()))
    for k,mask in masks.items():
        out[k]=dict(pixels=int(mask.sum()),sum=float(delta[mask].sum()),mean=float(delta[mask].mean()) if mask.any() else None,
            fraction_above_0_05=float((delta[mask]>=.05).mean()) if mask.any() else None,max=float(delta[mask].max()) if mask.any() else None)
    far=masks['far_other']|masks['far_background'];out['far_fraction']=float(delta[far].sum()/max(delta.sum(),1e-30))
    return out

def rgb8(a):
    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
    return np.uint8(np.clip(a,0,1)*255+.5)

def panel(name,rows):
    w=384;h=412;img=Image.new('RGB',(w*len(rows[0]),h*len(rows)),'white');draw=ImageDraw.Draw(img)
    for j,row in enumerate(rows):
        for i,(label,a) in enumerate(row):
            img.paste(Image.fromarray(rgb8(a)),(i*w,j*h+28));draw.text((i*w+4,j*h+4),label,fill='black')
    img.save(UNIT/'media'/name)

def main():
    verify(UNIT);(UNIT/'media').mkdir(exist_ok=True)
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assets=UNIT/'delivery/assets';records={};counts={};png_checks=0
    for r in range(1,5):
        hashes=[sha(assets/k/f'region_{r}.npz') for k in ('history','baseline','angle')];assert len(set(hashes))==1
    for name in ('mesh.npz','SOURCE_LINK.npz','WHOLE_PRESET.json'):
        assert len({sha(assets/k/name) for k in ('history','baseline','angle')})==1
    for kind in ('history','baseline','angle'):
        data=npz(assets/kind/'region_5.npz');meta=json.loads((assets/kind/'asset.json').read_text())
        counts[kind]=dict(paths=len(np.unique(data['stroke_id'])),segments=len(data['face']),length=float(np.linalg.norm(np.diff(data['points'],axis=1),axis=2).sum()),
            masks=np.unique(data['visibility_mask']).tolist(),style=meta['styles']['5'])
        if kind!='history':assert (data['visibility_mask']==32).all()
    assert counts['baseline']['style']==dict(counts['angle']['style'],angle=-25.)
    ids=[np.unique(npz(assets/k/'region_5.npz')['stroke_id']) for k in ('history','baseline','angle')]
    for i in range(3):
        for j in range(i):assert not np.intersect1d(ids[i],ids[j]).size
    raw=npz(UNIT/'delivery/data/chair/SOURCE_BINDING.npz');control=npz(UNIT/'delivery/controls/upper_back/WEIGHTS.npz')
    expect=np.zeros(256690);ok=(raw['region_id']==5)&~raw['unknown'];expect[ok]=.5*raw['membership'][ok,5]
    np.testing.assert_array_equal(control['strength'],expect);np.testing.assert_array_equal(control['source_index'],np.arange(256690))
    assert int((expect>0).sum())==11576 and int(raw['unknown'].sum())==170281
    chosen=np.flatnonzero(expect>0);query_ids=np.unique(np.r_[0,256689,chosen[np.linspace(0,len(chosen)-1,5).round().astype(int)],np.flatnonzero(raw['unknown'])[0],np.flatnonzero(raw['region_id']==4)[0]])
    js(UNIT/'QUERY_IDS.json',query_ids.tolist())
    original=base.load_source(UNIT/'delivery/data/chair/source.ply','13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d')
    before_rows=[];whole_rows=[];source_rows=[];total_events=0
    for i,c in enumerate(p['cameras']):
        view=c['view'];h=npz(UNIT/'inputs/reference'/str(i)/'FRAME.npz')
        a=npz(UNIT/'renders/baseline'/view/'FRAME.npz');b=npz(UNIT/'renders/angle'/view/'FRAME.npz');s=npz(UNIT/'renders/highlight'/view/'FRAME.npz')
        invariant=['source','source_alpha','paper','support','proxy_depth','regions','contour','seat_ink','seat_linked_ink','layer_1','layer_2','layer_3','layer_4']
        for key in invariant:
            np.testing.assert_array_equal(h[key],a[key]);np.testing.assert_array_equal(a[key],b[key])
        np.testing.assert_array_equal(s['source'],a['source']);np.testing.assert_array_equal(s['regions'],a['regions'])
        for kind,frame in [('baseline',a),('angle',b),('highlight',s)]:
            out=UNIT/'renders'/kind/view;receipt=json.loads((out/'RENDER_RECEIPT.json').read_text())
            for name,digest in receipt['files'].items():assert sha(out/name)==digest,name
            for image in out.glob('*.png'):
                value=frame[image.stem]
                if image.stem in ('combined_ink','seat_ink','seat_linked_ink','other_ink','contour'):value=1-value
                with Image.open(image) as im:
                    im.load();np.testing.assert_array_equal(np.asarray(im),rgb8(value));png_checks+=1
        trace=npz(UNIT/'renders/highlight'/view/'TRACE.npz');xy=trace['xy'];sid=trace['sample_index'];source_ids=trace['source_index'];w=trace['weight'];n=len(xy)
        assert (source_ids>=0).all() and (source_ids<256690).all();total_events+=len(w)
        np.testing.assert_allclose(w,trace['alpha']*trace['T'],atol=1e-14,rtol=0)
        # Reconstruct every recorded full-T chain in its original accepted order.
        order=np.argsort(sid,kind='stable');indices=np.flatnonzero(np.r_[True,np.diff(sid[order])!=0,True]);chain_error=0.
        for lo,hi in zip(indices[:-1],indices[1:]):
            ix=order[lo:hi];expected_T=np.r_[1.,np.cumprod(1-trace['alpha'][ix][:-1])]
            chain_error=max(chain_error,float(np.max(np.abs(expected_T-trace['T'][ix]))))
        assert chain_error<1e-12
        colors=base.source_colors(original,c);mass=np.bincount(sid,w,minlength=n)
        rgb=np.ones((n,3))*(1-mass[:,None]);tint_delta=np.zeros((n,3))
        for j in range(3):
            rgb[:,j]+=np.bincount(sid,w*colors[source_ids,j],minlength=n)
            tint_delta[:,j]=np.bincount(sid,w*expect[source_ids]*(p['source_control']['color'][j]-colors[source_ids,j]),minlength=n)
        x,y=xy.T;rgb_error=float(np.max(np.abs(rgb-s['source'][y,x])));delta_error=float(np.max(np.abs(tint_delta-(s['highlight']-s['source'])[y,x])))
        alpha_error=float(np.max(np.abs(mass-s['source_alpha'][y,x])))
        contribution=np.bincount(sid,w*expect[source_ids],minlength=n)
        support_error=float(np.max(np.abs(contribution-s['region_contribution'][y,x])))
        assert max(rgb_error,delta_error,alpha_error,support_error)<1e-6
        edited=metrics(a['hybrid'],b['hybrid'],a['regions']);preparation=metrics(h['hybrid'],a['hybrid'],a['regions'])
        source_effect=metrics(s['source'],s['highlight'],a['regions'])
        records[view]=dict(edit=edited,preparation=preparation,source_control=source_effect,global_absolute=metrics(b['source'],b['hybrid'],b['regions']),
            non_target_arrays_exact=invariant,trace_events=len(w),trace_samples=n,T_chain_max_error=chain_error,source_rgb_error=rgb_error,
            delta_error=delta_error,alpha_error=alpha_error,support_error=support_error,
            upper_back_coverage={k:float((v['layer_5'][v['regions']==5]>1/255).mean()) for k,v in [('history',h),('baseline',a),('angle',b)]},
            upper_back_natural_ink_mass={k:float(v['layer_5'].sum()) for k,v in [('history',h),('baseline',a),('angle',b)]},
            selected_exposed_lattice_ids=int(len(np.unique(source_ids[expect[source_ids]>0]))),full_image_effect_mass=float(s['region_contribution'].sum()))
        before_rows.append([(view+' | History (reused unit004)',h['hybrid']),('Common -25 deg (new)',a['hybrid']),('Edited +25 deg (new)',b['hybrid']),('Upper-back ink | -25 deg',1-a['layer_5']),('Upper-back ink | +25 deg',1-b['layer_5'])])
        whole_rows.append([(view+' | Original GS',b['source']),('Fixed global paper',b['paper']),('Edited combined ink',1-b['combined_ink']),('Edited hybrid',b['hybrid']),('Conventional proxy',b['proxy'])])
        source_rows.append([(view+' | Original GS',s['source']),('Saved region5 source tint | mix 0.5',s['highlight']),('Actual weighted source contribution',s['region_contribution'])])
    panel('EDIT_COMPARISON.png',before_rows);panel('WHOLE_LAYERS.png',whole_rows);panel('SOURCE_CONTROL.png',source_rows)
    reload={}
    for name,kind in [('cold_edit','angle'),('cold_source','highlight')]:
        cold=npz(UNIT/name/'FRAME.npz');ref=npz(UNIT/'renders'/kind/p['cameras'][1]['view']/'FRAME.npz')
        for key in cold:np.testing.assert_array_equal(cold[key],ref[key])
        reload[name]=dict(arrays=len(cold),exact=True)
    # Check original protected payloads as well as local copies, without writing them.
    inherited=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    for f in inherited['files']:assert sha(Path(f['source']))==f['sha256']
    verify(UNIT)
    js(UNIT/'OUTPUT_AUDIT.json',dict(views=records,paths=counts,non_target_region_files_exact=True,original_binding_unchanged=True,
        selected_rows=11576,unknown_rows=170281,png_array_checks=png_checks,full_T_events=total_events,reload=reload,
        inherited_files_unchanged=len(inherited['files']),decision_unchanged=True,source_lock_unchanged=True,scope='Saved output engineering and application diagnostics; no physical, semantic or quality superiority certification'))
    print(json.dumps(dict(paths=counts,png_checks=png_checks,events=total_events,edit={k:v['edit'] for k,v in records.items()},source_control={k:v['source_control'] for k,v in records.items()})),flush=True)
if __name__=='__main__':main()
