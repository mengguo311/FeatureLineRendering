"""Aggregate actual saved outputs; preserve denominator and parent-ID scope."""
import runtime
from runtime import ROOT as UNIT,js,sha
import json,math
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw
from linked_asset import npz
from observations import frame_summary,transition,THRESHOLD
from run_motion import ARMS,locks

GROUPS=ARMS+['U_on_S','U_on_sham']
def observations(key,mode):
    data=npz(UNIT/f'renders/{key}/OBSERVATIONS.npz');common=npz(UNIT/f'renders/{key}/COMMON.npz')
    factors=json.loads((UNIT/'frozen/BUILD_MATCH.json').read_text())['factors'];out={}
    for g in GROUPS:
        ob={n:data[g+'_'+n] for n in ('visible','inside','depth_rejected','own','increment','uv','depth')}
        if mode=='matched':
            arm='U' if g.startswith('U_on_') else g;factor=factors[arm]
            own=npz(UNIT/f'renders/{key}/matched/{arm}/FRAME.npz')
            inc=np.abs(own['hybrid']-common['baseline']).sum(2)
            ob={**ob,'own':ob['own']*factor,'increment':ndimage.map_coordinates(inc,[ob['uv'][:,1],ob['uv'][:,0]],order=1,mode='constant',cval=0)}
        out[g]=ob
    return out
def sample_for(g,samples):return samples[g[5:]] if g.startswith('U_on_') else samples[g]
def panel(key,mode,own=False,conventional=False):
    height=408;canvas=Image.new('RGB',(384*5,height),'white');draw=ImageDraw.Draw(canvas)
    if own:files=[UNIT/f'renders/{key}/structure.png']+[UNIT/f'renders/{key}/{mode}/{a}/own_ink.png' for a in ARMS];names=['Fixed structure']+[a+' own hatch' for a in ARMS]
    elif conventional:files=[UNIT/f'renders/{key}/source.png']+[UNIT/f'renders/{key}/conventional_{a}.png' for a in ARMS];names=['Original GS']+[a+' conventional proxy, no S' for a in ARMS]
    else:files=[UNIT/f'renders/{key}/source.png']+[UNIT/f'renders/{key}/{mode}/{a}/hybrid.png' for a in ARMS];names=['Original GS']+[a+' '+mode for a in ARMS]
    for i,(f,n) in enumerate(zip(files,names)):
        with Image.open(f) as im:canvas.paste(im.convert('RGB'),(384*i,24))
        draw.text((384*i+4,5),key+' | '+n,fill='black')
    return canvas
def make_media():
    media=UNIT/'media';media.mkdir(exist_ok=True);keys=['BUILD','000','012','024','028','032','036','FRONT']
    for mode in ('natural','matched'):
        frames=[panel(f'{i:03d}',mode) for i in range(37)]
        frames[0].save(media/f'{mode}_orbit.png',save_all=True,append_images=frames[1:],duration=125,loop=0,disposal=0,blend=0)
        contact=Image.new('RGB',(960*3,204*math.ceil(37/3)),'white')
        for i,p in enumerate(frames):contact.paste(p.resize((960,204),Image.Resampling.LANCZOS),((i%3)*960,(i//3)*204))
        contact.save(media/f'{mode}_ALL_FRAMES.png')
        keyframes=Image.new('RGB',(1920,408*len(keys)),'white')
        for i,k in enumerate(keys):keyframes.paste(panel(k,mode),(0,408*i))
        keyframes.save(media/f'{mode}_KEYFRAMES.png')
    for name,own,conv in [('WHOLE_LAYERS',True,False),('CONVENTIONAL',False,True)]:
        chosen=['BUILD','000','024','028','032','036'];im=Image.new('RGB',(1920,408*len(chosen)),'white')
        for i,k in enumerate(chosen):im.paste(panel(k,'natural',own,conv),(0,408*i))
        im.save(media/(name+'.png'))
def main():
    locks();js(UNIT/'ANALYSIS_SOURCE_LOCK.json',{p.name:sha(p) for p in [runtime.CODE/'analyze_motion.py']})
    samples={a:npz(UNIT/f'samples/{a}.npz') for a in ARMS};rows=json.loads((UNIT/'CAMERAS.json').read_text())
    metrics={r['key']:json.loads((UNIT/f'renders/{r["key"]}/METRICS.json').read_text()) for r in rows}
    allresults={};events=[]
    for mode in ('natural','matched'):
        obs={r['key']:observations(r['key'],mode) for r in rows}
        frames={k:{g:frame_summary(sample_for(g,samples),v) for g,v in values.items()} for k,values in obs.items()}
        pairs=[]
        for i in range(36):
            for x,y in [(i,i+1),(i+1,i)]:
                ka,kb=f'{x:03d}',f'{y:03d}';record=dict(source=ka,destination=kb,groups={})
                for g in GROUPS:
                    s=sample_for(g,samples);a,b=obs[ka][g],obs[kb][g];t=transition(s,a,b)
                    w=s['weight'];r=~s['planned'];exit=r&a['visible']&~b['visible']
                    t['offscreen_exit_length']=float(w[exit&~b['inside']].sum());t['proxy_depth_or_label_exit_length']=float(w[exit&b['inside']].sum())
                    record['groups'][g]=t
                    if x<y:
                        for kind in ('own_dropout','own_reappearance','composite_cancellation'):
                            for idx in t[kind+'_sample_indices']:
                                events.append(dict(mode=mode,arm=g,kind=kind,source=ka,destination=kb,sample=idx,parent_id=int(s['parent'][idx]),
                                    segment=int(s['segment'][idx]),segment_t=float(s['t'][idx]),world_weight=float(w[idx]),
                                    own_before=float(a['own'][idx]),own_after=float(b['own'][idx]),increment_before=float(a['increment'][idx]),increment_after=float(b['increment'][idx])))
                pairs.append(record)
        totals={}
        for g in GROUPS:
            keys=[k for k in pairs[0]['groups'][g] if not k.endswith('_sample_indices')]
            totals[g]={k:sum(p['groups'][g][k] for p in pairs) for k in keys}
            q=totals[g];den=q['source_own_joint_length'];q['dropout_fraction_of_source_own_joint_length']=q['own_dropout_length']/den if den else None
            q['scope']='72 directed adjacent pairs; repeated samples within one Chair, not independent observations'
        allresults[mode]=dict(frames=frames,pairs=pairs,totals=totals)
    js(UNIT/'TEMPORAL.json',dict(frames=37,directed_pairs=72,threshold=THRESHOLD,results=allresults,
        scope='Actual same-parent raster ink at fixed world samples; proxy-conditional visibility, no physical GT. Planned intervals excluded but their raw/visible denominators reported. U_on_S and U_on_sham paired supports; D has separate pre-stop geometry.'))
    js(UNIT/'EVENTS.json',events)
    numbers={}
    for mode in ('natural','matched'):
        numbers[mode]={}
        for a in ARMS:
            mm=[metrics[f'{i:03d}']['metrics'][mode][a] for i in range(37)]
            numbers[mode][a]=dict(rgb_range=[min(m['target_rgb_effect'] for m in mm),max(m['target_rgb_effect'] for m in mm)],
                necessary_coverage_range=[min(m['regions']['necessary_interior']['coverage_fraction'] for m in mm),max(m['regions']['necessary_interior']['coverage_fraction'] for m in mm)],
                necessary_coverage_delta_vs_U=[m['regions']['necessary_interior']['coverage_fraction']-metrics[f'{i:03d}']['metrics'][mode]['U']['regions']['necessary_interior']['coverage_fraction'] for i,m in enumerate(mm)],
                boundary_ink_mass=[m['regions']['boundary_band']['own_ink_mass'] if metrics[f'{i:03d}']['boundary_observable'] else None for i,m in enumerate(mm)],
                far_increment_max=max(max(m['regions'][r]['increment_vs_U_L1'] for r in ('far_other','far_background')) for m in mm),
                temporal=allresults[mode]['totals'][a])
    numbers['boundary_observed_frames']=[k for k,m in metrics.items() if m['boundary_observable']]
    numbers['boundary_NA_frames']=[k for k,m in metrics.items() if not m['boundary_observable']]
    numbers['cold_GS_frames']=[k for k,m in metrics.items() if m['source']['cold_original_GS']]
    numbers['seconds']={k:m['seconds'] for k,m in metrics.items()}
    numbers['far_absolute_ranges']={r:[min(m['metrics']['natural']['U']['regions'][r]['absolute_source_L1'] for m in metrics.values()),max(m['metrics']['natural']['U']['regions'][r]['absolute_source_L1'] for m in metrics.values())] for r in ('far_other','far_background')}
    numbers['paired_U_on_S']=allresults['natural']['totals']['U_on_S'];numbers['paired_U_on_sham']=allresults['natural']['totals']['U_on_sham']
    js(UNIT/'REPORT_NUMBERS.json',numbers);js(UNIT/'SUMMARY_METRICS.json',metrics)
    make_media()
    # Preserve full-frame events as observations, not selected successful crops.
    eventkeys=sorted(set((e['source'],e['destination']) for e in events if e['mode']=='natural' and e['arm'] in ARMS and e['kind']=='own_dropout'))
    js(UNIT/'EVENT_FRAME_PAIRS.json',eventkeys)
    print(json.dumps(dict(boundary_NA=numbers['boundary_NA_frames'],cold_frames=len(numbers['cold_GS_frames']),
        natural_totals={g:{k:v for k,v in q.items() if k in ('own_dropout_count','own_dropout_length','joint_retained_visible_length','dropout_fraction_of_source_own_joint_length','composite_cancellation_count')} for g,q in allresults['natural']['totals'].items()})),flush=True)
if __name__=='__main__':main()
