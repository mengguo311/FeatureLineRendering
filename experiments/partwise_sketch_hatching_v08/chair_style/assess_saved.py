"""Post-evaluation readback and full-object panels; never change frozen assets."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import npz,load_asset,png
from hybrid import edit_metrics,region_strength
from match_build import contour_base
from run_view import verify
UNIT=runtime.ROOT/'units/unit_006'
def image_array(a):
    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
    return np.uint8(np.clip(a,0,1)*255+.5)
def sheet(rows,path):
    w=384;h=410;out=Image.new('RGB',(w*len(rows[0]),h*len(rows)),'white');d=ImageDraw.Draw(out)
    for y,row in enumerate(rows):
        for x,(title,a) in enumerate(row):
            out.paste(Image.fromarray(image_array(a)),(x*w,y*h+26));d.text((x*w+4,y*h+3),title,fill='black')
    out.save(path)
def summary(asset):
    mesh,paths,meta,link,b=load_asset(asset);result={}
    for r,p in paths.items():
        result[str(r)]=dict(paths=len(np.unique(p['stroke_id'])),segments=len(p['face']),
            length=float(np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1).sum()),
            masks=np.unique(p.get('visibility_mask',np.full(len(p['face']),1<<r))).tolist(),style=meta['styles'][str(r)])
    return result
def main():
    verify(UNIT);p=json.loads((UNIT/'PROTOCOL.json').read_text());match=json.loads((UNIT/'BUILD_MATCH.json').read_text())
    assert sha(UNIT/'BUILD_MATCH.json')==json.loads((UNIT/'BUILD_LOCK.json').read_text())['match_sha256']
    media=UNIT/'media';media.mkdir(exist_ok=True);audit=dict(views={},paths={},png_array_checks=0,raw_png_decode_checks=0)
    rows=[];matched=[];layers=[]
    fixed=('source','paper','source_alpha','support','contour','proxy_depth','regions')
    _,_,_,_,binding=load_asset(UNIT/'delivery/assets/selective');strength=region_strength(binding)
    for i,c in enumerate(p['cameras']):
        view=c['view'];dirs=dict(reference=UNIT/'inputs/reference'/str(i) if i<3 else UNIT/'renders/reference'/view,
                               selective=UNIT/'renders/selective'/view)
        frames={k:npz(v/'FRAME.npz') for k,v in dirs.items()}
        for key in fixed:np.testing.assert_array_equal(frames['reference'][key],frames['selective'][key])
        for r in (1,2,3):np.testing.assert_array_equal(frames['selective'][f'layer_{r}'],0)
        entry=dict(fixed_arrays_exact=list(fixed),reference_reused=i<3,regions={},global_absolute={},style_scope_delta={})
        diag={}
        for arm,f in frames.items():
            raw=json.loads((dirs[arm]/'RENDER_RECEIPT.json').read_text())
            assert sha(dirs[arm]/'FRAME.npz')==raw['files']['FRAME.npz']
            if arm=='selective' or i==3:
                for key in ('source','paper','hybrid','proxy','support','combined_ink','other_ink','contour','seat_ink','seat_linked_ink'):
                    arr=f[key] if key in ('source','paper','hybrid','proxy','support') else 1-f[key]
                    with Image.open(dirs[arm]/(key+'.png')) as im:
                        im.load();np.testing.assert_array_equal(np.asarray(im),image_array(arr));audit['png_array_checks']+=1
                t=npz(dirs[arm]/'TRACE.npz');sid=t['sample_index'];ids=t['source_index'];xy=t['xy'];x,y=xy.T
                assert ((ids>=0)&(ids<256690)).all()
                own=np.bincount(sid,t['weight']*strength[ids],minlength=len(xy))
                alpha=np.bincount(sid,t['weight'],minlength=len(xy))
                entry[arm+'_trace_readback']=dict(events=len(ids),samples=len(xy),support_error=float(np.max(np.abs(own-f['support'][y,x]))),alpha_error=float(np.max(np.abs(alpha-f['source_alpha'][y,x]))))
                assert entry[arm+'_trace_readback']['support_error']<1e-6
                assert entry[arm+'_trace_readback']['alpha_error']<1e-6
            base=contour_base(f);scale=match['factors'][arm]
            diag[arm]=base+scale*(f['hybrid']-base)
            np.testing.assert_array_equal(base,contour_base(frames['reference']))
            entry[arm+'_increment']=dict(natural_L1=float(np.abs(f['hybrid']-base).sum(dtype=np.float64)),matched_L1=float(np.abs(diag[arm]-base).sum(dtype=np.float64)),scale=scale)
            entry['regions'][arm]={}
            for r in range(1,6):
                mask=f['regions']==r;ink=f['seat_linked_ink'] if r==4 else f[f'layer_{r}']
                entry['regions'][arm][str(r)]=dict(pixels=int(mask.sum()),visible_hatch_pixels=int((ink[mask]>1/255).sum()),
                    coverage=float((ink[mask]>1/255).mean()) if mask.any() else None,hatch_mass=float(ink[mask].sum(dtype=np.float64)),
                    absolute_source_L1=float(np.abs(f['hybrid']-f['source']).sum(2)[mask].sum(dtype=np.float64)))
            entry['global_absolute'][arm]=edit_metrics(f['source'],f['hybrid'],f['regions'],4)
            png(media/(view+'_'+arm+'_matched.png'),diag[arm])
        a=frames['reference'];b=frames['selective']
        entry['style_scope_delta']=edit_metrics(a['hybrid'],b['hybrid'],a['regions'],4)
        entry['scope_note']='Region4 far-other changes include intentional hiding of regions1-3 and region5 restyling, not single-region edit leakage. Global source differences include fixed all-row paper.'
        if i==0:
            for arm in frames:assert abs(entry[arm+'_increment']['matched_L1']-match['target'])<1e-3
        rows.append([(view+' | '+('Reference reused unit005' if i<3 else 'Reference new camera'),a['hybrid']),('Selective | natural',b['hybrid']),('Conventional proxy | selective',b['proxy']),('Fixed original contour',1-b['contour'])])
        matched.append([(view+' | Reference normalized',diag['reference']),('Selective normalized | BUILD factors',diag['selective'])])
        layers.append([(view+' | Original GS',b['source']),('Fixed global paper',b['paper']),('Contour',1-b['contour']),('Selective combined ink',1-b['combined_ink']),('Selective hybrid',b['hybrid']),('Conventional proxy',b['proxy'])])
        audit['views'][view]=entry
    for arm in ('reference','selective'):audit['paths'][arm]=summary(UNIT/'delivery/assets'/arm)
    ref=UNIT/'delivery/assets/reference';new=UNIT/'delivery/assets/selective'
    audit['unchanged_files']={n:sha(ref/n)==sha(new/n) for n in ['mesh.npz','SOURCE_LINK.npz',*[f'region_{r}.npz' for r in (1,2,3)]]};assert all(audit['unchanged_files'].values())
    oldpaths=load_asset(ref)[1];newpaths=load_asset(new)[1];oldids=np.concatenate([x['stroke_id'] for x in oldpaths.values()])
    for r in (4,5):assert not np.intersect1d(oldids,newpaths[r]['stroke_id']).size
    audit['new_path_ids_disjoint']=True;audit['new_path_certificate']=False
    sheet(rows,media/'NATURAL_COMPARISON.png');sheet(matched,media/'MATCHED_COMPARISON.png');sheet(layers,media/'WHOLE_LAYERS.png')
    for path in media.glob('*.png'):
        with Image.open(path) as im:im.load();audit['raw_png_decode_checks']+=1
    audit['scope']='Engineering and whole-object authored style feasibility; no semantic/physical/temporal or Gaussian-quality advantage certification'
    js(UNIT/'OUTPUT_AUDIT.json',audit);verify(UNIT)
    print(json.dumps(dict(png_array_checks=audit['png_array_checks'],views=len(audit['views']),paths=audit['paths']),default=runtime.json_default),flush=True)
if __name__=='__main__':main()
