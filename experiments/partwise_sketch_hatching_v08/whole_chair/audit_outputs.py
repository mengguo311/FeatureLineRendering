"""Read saved real renders, verify invariants, and present full objects at natural strength."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import npz
from hybrid import edit_metrics

UNIT=runtime.ROOT/'units/unit_002'
def panel(rows,path,footer=''):
    size=384;header=26;cols=len(rows[0]);canvas=Image.new('RGB',(cols*size,len(rows)*(size+header)+30),'white');draw=ImageDraw.Draw(canvas)
    for j,row in enumerate(rows):
        for i,(name,a) in enumerate(row):
            a=np.asarray(a)
            if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
            im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5))
            assert im.size==(384,384)
            canvas.paste(im,(i*size,j*(size+header)+header));draw.text((i*size+5,j*(size+header)+5),name,fill='black')
    draw.text((5,canvas.height-24),footer,fill='black');canvas.save(runtime.output_guard(path))

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    inputs=json.loads((UNIT/'INPUT_LOCK.json').read_text())
    for f,h in inputs.items():assert sha(f)==h,f
    sources=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for name,h in sources['files'].items():
        assert sha(Path(sources['source'])/name)==h
        assert sha(UNIT/'source_snapshot'/name)==h
    for name,h in sources['cli_files'].items():assert sha(UNIT/'delivery/code'/name)==h
    isolation={}
    for state in ('baseline','spacing'):
        root=UNIT/'delivery/assets';raw=root/state;whole=root/('whole_'+state)
        names=['mesh.npz','SOURCE_LINK.npz',*[f'region_{r}.npz' for r in (1,2,3,4,5)]]
        isolation[state]={n:sha(raw/n)==sha(whole/n) for n in names};assert all(isolation[state].values())
    for r in (1,2,3,5):assert sha(UNIT/f'delivery/assets/whole_baseline/region_{r}.npz')==sha(UNIT/f'delivery/assets/whole_spacing/region_{r}.npz')
    summaries=[];allrows=[];png_checks=0
    for c in p['cameras']:
        view=c['view'];root=UNIT/'renders'/view;frames={};proofs=[]
        for state in p['states']:
            d=root/state;f=npz(d/'FRAME.npz');frames[state]=f
            receipt=json.loads((d/'RENDER_RECEIPT.json').read_text());proofs.append(receipt)
            for name,h in receipt['files'].items():assert sha(d/name)==h
            old=npz(UNIT/'inputs/historical_patch'/view/state.removeprefix('whole_')/'FRAME.npz')
            for k in ('source','source_alpha','support','regions','proxy_depth'):np.testing.assert_array_equal(f[k],old[k])
            np.testing.assert_array_equal(f['seat_ink'],old['ink'])
            np.testing.assert_allclose(f['seat_linked_ink'],old['linked_ink'],atol=1e-7,rtol=0)
            for k in ('source','paper','hybrid','proxy','support','combined_ink','other_ink','contour','seat_ink','seat_linked_ink'):
                a=f[k] if k in ('source','paper','hybrid','proxy','support') else 1-f[k]
                if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
                with Image.open(d/(k+'.png')) as im:
                    im.load();np.testing.assert_array_equal(np.asarray(im),np.uint8(np.clip(a,0,1)*255+.5));png_checks+=1
        before=frames['whole_baseline'];after=frames['whole_spacing'];same={}
        for key in ('source','source_alpha','paper','support','regions','proxy_depth','other_ink','contour','layer_1','layer_2','layer_3','layer_5'):
            same[key]=bool(np.array_equal(before[key],after[key]));assert same[key],key
        increment=edit_metrics(before['hybrid'],after['hybrid'],before['regions'])
        proxy_increment=edit_metrics(np.repeat(before['proxy'][:,:,None],3,axis=2),np.repeat(after['proxy'][:,:,None],3,axis=2),before['regions'])
        absolute={};budget={}
        for state,f in frames.items():
            absolute[state]={k:edit_metrics(f['source'],f[k],f['regions']) for k in ('paper','hybrid')}
            object_mask=f['regions']>0;seat=f['regions']==4
            budget[state]=dict(combined_ink_mass=float(f['combined_ink'].sum()),seat_preS_mass=float(f['seat_ink'].sum()),
                seat_linked_mass=float(f['seat_linked_ink'].sum()),other_ink_mass=float(f['other_ink'].sum()),contour_mass=float(f['contour'].sum()),
                object_ink_coverage=float((f['combined_ink'][object_mask]>1/255).mean()),seat_ink_coverage=float((f['seat_linked_ink'][seat]>1/255).mean()),
                conventional_black_ink_mass=float((1-f['proxy']).sum()),whole_ink_rgb_L1=float(np.abs(f['hybrid']-f['paper']).sum()))
        gs=before['source_alpha']>.5;proxy=before['regions']>0
        shape=dict(description='Descriptive GS alpha>0.5 versus proxy hits; neither is GT. No topology repair.',
            gs_pixels=int(gs.sum()),proxy_pixels=int(proxy.sum()),gs_only=int((gs&~proxy).sum()),proxy_only=int((proxy&~gs).sum()))
        result=dict(view=view,invariant_layers_equal=same,source_and_seat_match_unit001=True,spacing_increment=increment,
            conventional_spacing_increment=proxy_increment,absolute_source_difference=absolute,budgets=budget,shape_support=shape,
            source_proofs=[{k:r[k] for k in ('source_count','selected_rows','unknown_rows','global_override_rows','cold_original_GS','support_reconstruction_max_error','constant_paper_reconstruction_max_error')} for r in proofs])
        js(root/'EVALUATION.json',result);summaries.append(result)
        rows=[]
        for state,f in frames.items():
            rows.append([(state+' | Original GS',f['source']),('All-row GS paper',f['paper']),('Combined ink',1-f['combined_ink']),('Actual whole hybrid',f['hybrid']),('Conventional proxy',f['proxy'])])
        panel(rows,root/'LAYERS.png','Fixed whole-object preset | seat S gating only; other ink and contours are proxy-only | natural strength')
        historical=npz(UNIT/'inputs/historical_patch'/view/'spacing/FRAME.npz')['hybrid']
        allrows.append([(view+' | Original GS',before['source']),('unit001 patch REUSED',historical),('Whole | spacing .045',before['hybrid']),('Whole | spacing .0675',after['hybrid']),('Proxy | spacing .0675',after['proxy'])])
        overlay=np.ones((*gs.shape,3),np.float32);overlay[gs&proxy]=.8;overlay[gs&~proxy]=[.9,.2,.2];overlay[proxy&~gs]=[.2,.3,.9]
        panel([[('Original GS',before['source']),('Global paper: natural',before['paper']),('SUPPORT DIAGNOSTIC red=GS-only',overlay),('Proxy contour',1-before['contour'])]],root/'SHAPE_SUPPORT.png','Diagnostic masks only, not a result or independent geometry truth; natural output is in LAYERS')
    panel(allrows,UNIT/'ALL_VIEWS.png','Same cameras, fixed world paths; new whole-object scope, not equal-task superiority | three static views, no video')
    decoded=[]
    for f in sorted(UNIT.rglob('*.png')):
        with Image.open(f) as im:im.load();size=im.size
        decoded.append(dict(path=str(f.relative_to(UNIT)),sha256=sha(f),size=size))
    result=dict(input_hashes_verified=len(inputs),source_files_verified=len(sources['files']),asset_isolation=isolation,
        png_array_checks=png_checks,decoded_pngs=decoded,views=summaries,continuous_video=False,per_path_source_certification=False)
    js(UNIT/'AUDIT.json',result)
    print(json.dumps(dict(views=len(summaries),png_array_checks=png_checks,decoded_pngs=len(decoded),far_spacing=[x['spacing_increment']['far_raw_fraction'] for x in summaries])))
if __name__=='__main__':main()
