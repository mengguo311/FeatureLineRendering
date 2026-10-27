"""Read actual frozen assets/renders, audit isolation, make whole-object panels."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
from linked_asset import npz,load_asset
from hybrid import edit_metrics

UNIT=runtime.ROOT/'units/unit_001'

def panel(path,items,columns,footer):
    size=384;stride=410;rows=(len(items)+columns-1)//columns
    canvas=Image.new('RGB',(size*columns,stride*rows+28),'white');d=ImageDraw.Draw(canvas)
    for i,(label,a) in enumerate(items):
        if a.ndim==2:a=np.repeat(a[:,:,None],3,2)
        x=(i%columns)*size;y=(i//columns)*stride
        canvas.paste(Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)),(x,y+24));d.text((x+5,y+5),label,fill='black')
    d.text((5,rows*stride+5),footer,fill='black');canvas.save(path)

def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    inputs=json.loads((UNIT/'INPUT_LOCK.json').read_text())
    for path,h in inputs.items():assert sha(path)==h,path
    locks=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for name,h in locks['files'].items():
        assert sha(Path(locks['source'])/name)==h and sha(Path(locks['delivery'])/name)==h
    assets={name:load_asset(UNIT/'delivery/assets'/name) for name in ('baseline','spacing','paper_half')}
    path_stats={};isolation={}
    for name,(mesh,strokes,meta,link,b) in assets.items():
        folder=UNIT/'delivery/assets'/name
        for r in (1,2,3,5):assert sha(folder/f'region_{r}.npz')==sha(UNIT/'inputs/historical_asset'/f'region_{r}.npz')
        assert sha(folder/'mesh.npz')==sha(UNIT/'inputs/historical_asset/mesh.npz')
        s=strokes[4]
        # Independent endpoint reconstruction through explicit three-corner sum.
        reconstructed=sum(s['bary'][:,:,j,None]*mesh['vertices'][mesh['faces'][s['face'],j]][:,None,:] for j in range(3))
        error=float(np.max(np.abs(s['points']-reconstructed)));assert error<=1e-9
        path_stats[name]=dict(paths=len(np.unique(s['stroke_id'])),segments=len(s['face']),world_length=float(np.linalg.norm(s['points'][:,1]-s['points'][:,0],axis=1).sum()),
            anchor_max_error=error,paths_sha256=sha(folder/'region_4.npz'),style=meta['styles']['4'],paper_effect=link['paper_effect'])
        isolation[name]=dict(non_target_original_path_files_equal=True,mesh_equal=True,source_link_sha256=sha(folder/'SOURCE_LINK.npz'))
    assert path_stats['baseline']['paths_sha256']==path_stats['paper_half']['paths_sha256']
    assert len({v['source_link_sha256'] for v in isolation.values()})==1
    assert not np.intersect1d(assets['baseline'][1][4]['stroke_id'],assets['spacing'][1][4]['stroke_id']).size
    records=[];whole=[];allproof=[]
    for c in p['cameras']:
        view=c['view'];root=UNIT/'renders'/view
        f={name:npz(root/name/'FRAME.npz') for name in assets}
        base=f['baseline'];spacing=f['spacing'];half=f['paper_half'];regions=base['regions'];target=regions==4
        for name in assets:
            for k in ('source','support','regions','source_alpha'):np.testing.assert_array_equal(f[name][k],base[k])
        np.testing.assert_array_equal(spacing['paper'],base['paper'])
        np.testing.assert_array_equal(half['ink'],base['ink']);np.testing.assert_array_equal(half['linked_ink'],base['linked_ink'])
        old=npz(UNIT/'inputs/v06_frames'/view/'FRAME.npz')
        # v06 saved keys are verified below without inventing correspondence.
        old_keys=list(old)
        historical_check={}
        for newkey,oldkey in [('source','source'),('paper','paper'),('support','support')]:
            if oldkey in old:
                error=float(np.max(np.abs(base[newkey]-old[oldkey])))
                historical_check[newkey]=dict(max_error=error,array_equal=bool(np.array_equal(base[newkey],old[oldkey])))
                assert error<=1e-6
        comparisons={
            'spacing_increment':edit_metrics(base['hybrid'],spacing['hybrid'],regions),
            'paper_increment':edit_metrics(base['hybrid'],half['hybrid'],regions),
            'cap_normalization_increment':edit_metrics(base['historical_hybrid'],base['hybrid'],regions)}
        absolute={name:dict(paper=edit_metrics(frame['source'],frame['paper'],regions),hybrid=edit_metrics(frame['source'],frame['hybrid'],regions)) for name,frame in f.items()}
        ink={name:dict(target_pixels=int(target.sum()),visible_pixels=int((frame['linked_ink'][target]>1/255).sum()),
            target_visible_fraction=float((frame['linked_ink'][target]>1/255).mean()),target_mass=float(frame['linked_ink'][target].sum()),
            target_visible_rgb_L1=float(np.abs(frame['hybrid']-frame['paper'])[target].sum())) for name,frame in f.items()}
        proof=[]
        for name in assets:
            receipt=json.loads((root/name/'RENDER_RECEIPT.json').read_text())
            for file,h in receipt['files'].items():assert sha(root/name/file)==h
            proof.append(dict(state=name,**{k:receipt[k] for k in ('cold_original_GS','target_samples','unsupported_samples','trace_samples','selected_rows','unknown_rows','support_reconstruction_max_error','paper_delta_reconstruction_max_error','seconds')}))
        record=dict(view=view,comparisons=comparisons,absolute_source_difference=absolute,ink=ink,historical_source_checks=historical_check,old_frame_keys=old_keys,source_proofs=proof)
        js(root/'EVALUATION.json',record);records.append(record);allproof+=proof
        whole.extend([(view+' | Original GS',base['source']),(view+' | spacing .045',base['hybrid']),
                      (view+' | spacing .0675',spacing['hybrid']),(view+' | paper effect .5',half['hybrid'])])
        items=[]
        for name,frame in f.items():
            for key,label in [('source','Original GS'),('paper','GS paper'),('linked_ink','Ink only'),('hybrid','Linked hybrid')]:
                a=1-frame[key] if key=='linked_ink' else frame[key]
                items.append((name+' | '+label,a))
        panel(root/'LAYERS.png',items,4,'Original-ID regional support; proxy ink, no per-path source certification')
        panel(root/'CAP_NORMALIZATION.png',[('Historical inherited caps',base['historical_hybrid']),('v08 owner-only caps',base['hybrid'])],2,'Separate baseline preparation; same saved geometry and source weights')
    panel(UNIT/'ALL_VIEWS.png',whole,4,'Three actual static camera renders | fixed world paths | intentional density and paper edits, no quality superiority claim')
    decoded=[]
    for path in sorted((UNIT/'renders').rglob('*.png'))+[UNIT/'ALL_VIEWS.png']:
        with Image.open(path) as im:im.load();size=im.size
        decoded.append(dict(path=str(path.relative_to(UNIT)),sha256=sha(path),size=size))
    summary=dict(paths=path_stats,isolation=isolation,views=records,input_hashes_verified=len(inputs),source_files_verified=len(locks['files']),
        decoded_pngs=decoded,scientific_seal=False,all_three_static_cameras=True,continuous_video=False,
        original_row_universe=256690,selected_rows=27873,unknown_rows=170281,per_path_Gaussian_attachment_certified=False)
    js(UNIT/'AUDIT.json',summary)
    print(json.dumps(dict(paths=path_stats,views=[dict(view=x['view'],ink=x['ink'],spacing_target_change=x['comparisons']['spacing_increment']['target_full'],spacing_far=x['comparisons']['spacing_increment']['far_raw_fraction'],paper_far=x['comparisons']['paper_increment']['far_raw_fraction']) for x in records],decoded_pngs=len(decoded)),indent=2))

if __name__=='__main__':main()
