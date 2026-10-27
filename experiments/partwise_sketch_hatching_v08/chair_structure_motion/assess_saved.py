"""Read saved frames independently; create honest temporal diagnostics and media."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import load_asset,npz
from hybrid import region_strength
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008'

def panel(items,size=384):
    canvas=Image.new('RGB',(size*len(items),size+28),'white');draw=ImageDraw.Draw(canvas)
    for j,(label,img) in enumerate(items):
        if not isinstance(img,Image.Image):img=Image.open(img).convert('RGB')
        canvas.paste(img.resize((size,size)),(j*size,28));draw.text((j*size+4,5),label,fill='black')
    return canvas

def stack(rows):
    canvas=Image.new('RGB',(max(x.width for x in rows),sum(x.height for x in rows)),'white');y=0
    for row in rows:canvas.paste(row,(0,y));y+=row.height
    return canvas

def main():
    verify_unit(UNIT);plan=json.loads((UNIT/'delivery/TRAJECTORY.json').read_text());media=UNIT/'media';media.mkdir(exist_ok=False)
    (media/'frames').mkdir();mesh,paths,meta,link,binding=load_asset(UNIT/'delivery/assets/on');s=region_strength(binding)
    frames=[];observations=[];receipts=[];png_checks=0;trace_events=0;max_s_error=0.;max_alpha_error=0.;max_t_error=0.
    expected_fixed=('source','source_alpha','paper','support','proxy_depth','regions','other_ink','contour','seat_ink','seat_linked_ink',
        'layer_1','layer_2','layer_3','layer_4','layer_5','base_hybrid','base_combined_ink','base_proxy','structure_available')
    for row in plan['frames']:
        i=row['index'];root=UNIT/'renders'/f'{i:03d}';r=json.loads((root/'RENDER_RECEIPT.json').read_text())
        assert r['camera']==row['camera'];assert r['source_arrays_unchanged'];assert r['unknown_rows']==170281
        for name,h in r['files'].items():assert sha(root/name)==h,(i,name)
        off=npz(root/'off/FRAME.npz');on=npz(root/'on/FRAME.npz')
        for key in expected_fixed:np.testing.assert_array_equal(off[key],on[key])
        for key in ('layer_1','layer_2','layer_3'):np.testing.assert_array_equal(on[key],0)
        np.testing.assert_array_equal(off['structure'],0)
        np.testing.assert_array_equal(on['hybrid'],on['paper']*(1-on['combined_ink'][:,:,None])+.03*on['combined_ink'][:,:,None])
        diff=np.abs(on['hybrid']-off['hybrid']).sum(2)
        assert np.all(diff[on['structure']==0]==0)
        for arm,d in [('off',off),('on',on)]:
            for key in ('source','paper','support','hybrid','proxy','combined_ink','seat_linked_ink','contour','structure'):
                a=d[key] if key in ('source','paper','support','hybrid','proxy') else 1-d[key]
                if a.ndim==2:a=np.repeat(a[:,:,None],3,2)
                expected=np.uint8(np.clip(a,0,1)*255+.5)
                with Image.open(root/arm/(key+'.png')) as im:
                    im.load();np.testing.assert_array_equal(np.asarray(im.convert('RGB')),expected)
                png_checks+=1
        trace=npz(root/'TRACE.npz');xy=trace['xy'];sid=trace['sample_index'];ids=trace['source_index'];w=trace['weight']
        assert ids.min()>=0 and ids.max()<256690;trace_events+=len(ids)
        np.testing.assert_allclose(w,trace['alpha']*trace['T'],atol=1e-14,rtol=0)
        for k in range(len(xy)):
            take=sid==k;alph=trace['alpha'][take];T=trace['T'][take]
            expected=np.r_[1.,np.cumprod(1-alph)[:-1]] if len(alph) else np.array([])
            if len(T):max_t_error=max(max_t_error,float(np.max(np.abs(expected-T))))
        mass=np.bincount(sid,w,minlength=len(xy));support=np.bincount(sid,w*s[ids],minlength=len(xy));x,y=xy.T
        max_alpha_error=max(max_alpha_error,float(np.max(np.abs(mass-on['source_alpha'][y,x]))))
        max_s_error=max(max_s_error,float(np.max(np.abs(support-on['support'][y,x]))))
        obs=npz(root/'OBSERVATIONS.npz');assert len(obs['status'])==64
        # Independent bilinear readback from the saved own structure layer, never whole ink.
        for j,(u,v) in enumerate(obs['uv']):
            if not (0<=u<=383 and 0<=v<=383 and obs['z'][j]>.2):continue
            x0=int(np.floor(u));y0=int(np.floor(v));x1=min(x0+1,383);y1=min(y0+1,383);dx=u-x0;dy=v-y0
            weights=[(1-dx)*(1-dy),dx*(1-dy),(1-dx)*dy,dx*dy];pixels=[(y0,x0),(y0,x1),(y1,x0),(y1,x1)]
            own=sum(wt*float(on['structure'][yy,xx]) for wt,(yy,xx) in zip(weights,pixels))
            inc=sum(wt*float(diff[yy,xx]) for wt,(yy,xx) in zip(weights,pixels))
            assert abs(own-obs['own_ink'][j])<1e-7 and abs(inc-obs['increment'][j])<1e-6
        observations.append(obs);receipts.append(r)
        card=panel([(f'{i:03d} Original GS',root/'on/source.png'),('Structure OFF',root/'off/hybrid.png'),('Structure ON',root/'on/hybrid.png'),('Conventional proxy ON',root/'on/proxy.png')])
        card.save(media/'frames'/f'{i:03d}.png');frames.append(card)
    assert max_t_error<1e-12 and max_s_error<1e-6 and max_alpha_error<1e-6
    events=[];joint_count=0;entries=0;exits=0
    for i,(a,b) in enumerate(zip(observations[:-1],observations[1:])):
        joint=(a['status']=='visible')&(b['status']=='visible');joint_count+=int(joint.sum())
        entries+=int(((a['status']=='visible')&(b['status']=='depth_rejected')).sum())
        exits+=int(((a['status']=='depth_rejected')&(b['status']=='visible')).sum())
        ai=a['own_ink']>1/255;bi=b['own_ink']>1/255
        classes={'own_ink_dropout':joint&ai&~bi,'own_ink_reappearance':joint&~ai&bi,
            'composite_increment_dropout_own_ink_present':joint&ai&bi&(a['increment']>1/255)&(b['increment']<=1/255)}
        for kind,mask in classes.items():
            for j in np.flatnonzero(mask):events.append(dict(kind=kind,frames=[i,i+1],sample=int(j),
                own_before=float(a['own_ink'][j]),own_after=float(b['own_ink'][j]),increment_before=float(a['increment'][j]),increment_after=float(b['increment'][j])))
    temporal=dict(frames=61,samples_per_frame=64,observations=3904,joint_visible_pairs=joint_count,
        visible_observations=sum(int((o['status']=='visible').sum()) for o in observations),
        visible_without_own_ink=sum(int(((o['status']=='visible')&(o['own_ink']<=1/255)).sum()) for o in observations),
        visible_own_ink_without_increment=sum(int(((o['status']=='visible')&(o['own_ink']>1/255)&(o['increment']<=1/255)).sum()) for o in observations),
        occlusion_entries=entries,occlusion_exits=exits,event_counts={k:sum(e['kind']==k for e in events) for k in ('own_ink_dropout','own_ink_reappearance','composite_increment_dropout_own_ink_present')},
        events=events,per_frame=[dict(index=i,**r['observations'],increment_raw_L1=r['increment_raw_L1'],ink_mass_off=r['ink_mass_off'],ink_mass_on=r['ink_mass_on']) for i,r in enumerate(receipts)],
        limitations='Fixed same-proxy samples, not independent physical visibility; 64 samples on one authored curve, not independent paths or objects. Threshold events descriptive; proper hiding and composition overlap separate.')
    js(UNIT/'TEMPORAL.json',temporal)
    for start in range(0,61,16):
        subset=plan['frames'][start:start+16];cards=[]
        for row in subset:
            i=row['index'];cards.append(panel([(f'{i:03d} | {row["azimuth"]:g}/{row["elevation"]:g} ON',UNIT/'renders'/f'{i:03d}'/'on/hybrid.png')],256))
        sheet=Image.new('RGB',(1024,math.ceil(len(cards)/4)*284),'white')
        for j,card in enumerate(cards):sheet.paste(card,((j%4)*256,(j//4)*284))
        sheet.save(media/f'CONTACT_{start:02d}_{start+len(cards)-1:02d}.png')
    stack([frames[i] for i in (0,15,30,60)]).save(media/'NATURAL_COMPARISON.png')
    layers=[]
    for i in (0,15,30,60):
        root=UNIT/'renders'/f'{i:03d}'/'on'
        layers.append(panel([(f'{i:03d} Original GS',root/'source.png'),('Fixed paper',root/'paper.png'),('Contour',root/'contour.png'),('Own structure',root/'structure.png'),('Combined ink',root/'combined_ink.png'),('Hybrid ON',root/'hybrid.png')],256))
    stack(layers).save(media/'WHOLE_LAYERS.png')
    event_pairs=sorted({tuple(e['frames']) for e in events});event_dir=media/'events';event_dir.mkdir()
    for i,j in event_pairs:
        items=[]
        for k in (i,j):
            root=UNIT/'renders'/f'{k:03d}'/'on'
            items.extend([(f'{k:03d} Hybrid',root/'hybrid.png'),(f'{k:03d} Own structure',root/'structure.png')])
        panel(items).save(event_dir/f'{i:03d}_{j:03d}.png')
    duration=[round((i+1)*1000/12)-round(i*1000/12) for i in range(61)]
    frames[0].save(media/'orbit.png',save_all=True,append_images=frames[1:],duration=duration,loop=0,disposal=0,blend=0,optimize=False)
    with Image.open(media/'orbit.png') as im:
        assert im.n_frames==61
        for i in range(61):im.seek(i);np.testing.assert_array_equal(np.asarray(im.convert('RGB')),np.asarray(frames[i]))
    audit=dict(png_array_checks=png_checks,apng_frames=61,apng_all_frames_exact=True,apng_duration_ms=sum(duration),
        trace_events=trace_events,trace_T_max_error=max_t_error,source_alpha_max_error=max_alpha_error,source_S_max_error=max_s_error,
        keyframe_reference_equal={str(i):all(all(v.values()) for v in receipts[i]['reference_equal'].values()) for i in (0,15,30,60)},
        per_camera_seconds=[r['seconds'] for r in receipts],fixed_pair_arrays=list(expected_fixed),
        absolute_damage=[dict(index=i,off=r['off_absolute'],on=r['on_absolute']) for i,r in enumerate(receipts)],
        source_inputs_unchanged=True,scientific_source_unchanged=True,local_only=True)
    js(UNIT/'OUTPUT_AUDIT.json',audit);verify_unit(UNIT)
    print(json.dumps(dict(temporal={k:v for k,v in temporal.items() if k not in ('events','per_frame')},png_checks=png_checks,all_frames_decoded=True)),flush=True)
if __name__=='__main__':main()
