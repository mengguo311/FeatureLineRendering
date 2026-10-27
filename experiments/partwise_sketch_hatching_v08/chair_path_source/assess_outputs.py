"""Post-evaluation independent saved-output checks and unaltered contact panels."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import npz
from run_motion import verify_unit
from source_query import query
UNIT=runtime.ROOT/'units/unit_004'

def panel(path,rows):
    w=384;h=412;canvas=Image.new('RGB',(len(rows[0])*w,len(rows)*h),'white');draw=ImageDraw.Draw(canvas)
    for y,row in enumerate(rows):
        for x,(file,label) in enumerate(row):
            with Image.open(file) as im:im.load();canvas.paste(im.convert('RGB'),(x*w,y*h+28))
            draw.text((x*w+4,y*h+5),label,fill='black')
    canvas.save(path)

def main():
    verify_unit(UNIT);samples=json.loads((UNIT/'delivery/SAMPLES.json').read_text());support=UNIT/'delivery/support'
    high=json.loads((support/'HIGHLIGHTS.json').read_text());cameras=json.loads((UNIT/'delivery/CAMERAS.json').read_text())
    strokes=[int(v.split(':')[1]) for v in samples['selected_paths']]
    outputs=UNIT/'media';outputs.mkdir(exist_ok=False);rows=[];summary={};pngchecks=0;rawchecks=0
    for ci,c in enumerate(cameras):
        folder=UNIT/'renders'/c['view'];receipt=json.loads((folder/'RENDER_RECEIPT.json').read_text())
        for name,h in receipt['files'].items():assert sha(folder/name)==h,name
        d=npz(folder/'PATH_SUPPORT.npz');trace=npz(folder/'TRACE.npz');frame=npz(folder/'FRAME.npz');obs=npz(folder/'OBSERVATIONS.npz')
        np.testing.assert_array_equal(d['stroke_id'],[a['stroke_id'] for a in samples['anchors']])
        for j,a in enumerate(samples['anchors']):
            cursor=int(d['offsets'][j]);ownmap=obs['own_pre'][samples['selected_paths'].index(a['key'])]
            for ref in range(d['ref_offsets'][j],d['ref_offsets'][j+1]):
                pixel=int(d['ref_pixel_index'][ref]);ix=np.flatnonzero(trace['sample_index']==pixel);sl=slice(cursor,cursor+len(ix))
                for k in ('source_index','alpha','T','weight','depth','center_z','culled_local_index'):
                    np.testing.assert_array_equal(d[k][sl],trace[k][ix])
                np.testing.assert_array_equal(d['pixel_index'][sl],pixel)
                np.testing.assert_array_equal(d['pixel_weight'][sl],d['ref_weight'][ref])
                x,y=d['xy'][pixel];np.testing.assert_array_equal(d['own_ink'][sl],ownmap[y,x])
                eligibility=(np.isfinite(trace['depth'][ix]) & np.isfinite(d['pixel_proxy_depth'][pixel]) &
                    (np.abs(trace['depth'][ix]-d['pixel_proxy_depth'][pixel])<=.06) & bool(d['pixel_sample_ok'][pixel]) &
                    (str(obs['status'][j])=='visible') & (ownmap[y,x]>1/255) & (d['region_strength'][sl]>0))
                np.testing.assert_array_equal(d['eligible'][sl],eligibility)
                cursor+=len(ix);rawchecks+=len(ix)
            assert cursor==int(d['offsets'][j+1])
            lo,hi=map(int,d['offsets'][j:j+2]);w=d['pixel_weight'][lo:hi]*d['weight'][lo:hi]
            np.testing.assert_allclose(w.sum(),d['weighted_mass'][j],rtol=0,atol=1e-12)
            np.testing.assert_allclose(w[d['eligible'][lo:hi]].sum(),d['eligible_mass'][j],rtol=0,atol=1e-12)
        assert np.allclose(d['weight'],d['alpha']*d['T'],rtol=0,atol=1e-14)
        if ci==0:
            for stroke in strokes:
                values=[]
                for k in np.flatnonzero(d['stroke_id']==stroke):
                    lo,hi=d['offsets'][k:k+2];values.extend(d['source_index'][lo:hi][d['eligible'][lo:hi]])
                assert sorted(set(values))==high['paths'][str(stroke)]
        mappings={key:frame[key] for key in ('source','paper','support','hybrid','proxy')}
        mappings.update({key:1-frame[key] for key in ('combined_ink','seat_ink','seat_linked_ink','other_ink','contour')})
        highlights=npz(folder/'HIGHLIGHTS.npz')
        for k,stroke in enumerate(strokes):
            mappings['highlight_'+str(stroke)]=highlights[str(stroke)]
            mask=obs['own_pre'][k]/.35
            mappings['path_'+str(stroke)]=frame['hybrid']*(1-mask[:,:,None])+np.array([.85,.03,.03])*mask[:,:,None]
        for key,arr in mappings.items():
            with Image.open(folder/(key+'.png')) as im:
                im.load();pixels=np.asarray(im.convert('RGB'))
            if arr.ndim==2:arr=np.repeat(arr[:,:,None],3,axis=2)
            np.testing.assert_array_equal(pixels,np.uint8(np.clip(arr,0,1)*255+.5));pngchecks+=1
        rows.append([(folder/(key+'.png'),f'{c["view"]} | {title}') for key,title in
            [('source','Original GS'),('paper','Fixed global paper'),('combined_ink','Combined ink'),('hybrid','Unchanged hybrid'),('proxy','Conventional proxy')]])
        summary[c['view']]=dict(states=receipt['states'],unique_pixels=receipt['unique_trace_pixels'],raw_events=receipt['trace_events'],
            raw_CSR_event_references=receipt['csr_event_references'],eligible_event_references=receipt['eligible_event_references'],
            eligible_mass=receipt['eligible_mass'],raw_bilinear_mass=receipt['raw_bilinear_mass'],
            baseline_arrays_equal=len(receipt['baseline_arrays_equal']),trace_off_arrays_equal=len(receipt['trace_off_equal']),
            max_trace_RGB_error=receipt['trace_validation']['full_SH_rgb_max_error'],max_support_error=receipt['support_error'],
            max_own_post_error=receipt['own_post_reconstruction_max_error'],highlights=receipt['highlights'],
            global_hybrid_absolute=receipt['global_hybrid_absolute'],seconds=receipt['seconds'])
    panel(outputs/'WHOLE_LAYERS.png',rows)
    for stroke in strokes:
        rows=[]
        for c in cameras:
            f=UNIT/'renders'/c['view']
            rows.append([(f/'source.png',c['view']+' | Original GS'),
                (f/f'path_{stroke}.png','Own path location (diagnostic overlay)'),
                (f/f'highlight_{stroke}.png',f'Actual GS tint | {len(high["paths"][str(stroke)])} fixed IDs')])
        panel(outputs/f'PATH_{stroke}.png',rows)
    queries={}
    for c in cameras:
        for stroke in strokes:
            for fraction in (.2,.5,.8):
                q=query(UNIT/'delivery/assets/whole_spacing',support,c['view'],stroke,fraction)
                queries[f'{c["view"]}/{stroke}/{fraction}']={k:v for k,v in q.items() if k not in ('events','highlight_source_ids','pixel_coordinates')}
    js(UNIT/'QUERY_SUMMARY.json',queries)
    js(UNIT/'SAVED_SUMMARY.json',dict(views=summary,highlight_counts={k:len(v) for k,v in high['paths'].items()},
        highlighted_unique_source_ids=len(set(v for ids in high['paths'].values() for v in ids)),
        empty_highlight_paths=[k for k,v in high['paths'].items() if not v],sampled_paths=6,total_seat_paths=97,anchors=18,
        unobserved_seat_paths=91,scope='Sampled pixel/source support and usable saved query/highlight, not whole-path ownership or quality superiority'))
    js(UNIT/'OUTPUT_AUDIT.json',dict(raw_event_references_independently_checked=rawchecks,png_array_checks=pngchecks,
        queries_checked=len(queries),all_input_and_frozen_source_hashes_match=True,
        support_files={f.name:sha(f) for f in support.iterdir() if f.is_file()},
        media_files={f.name:sha(f) for f in outputs.iterdir() if f.is_file()},remote_verification='not performed'))
    print(json.dumps(dict(png_array_checks=pngchecks,raw_event_references=rawchecks,highlight_counts={k:len(v) for k,v in high['paths'].items()})),flush=True)
if __name__=='__main__':main()
