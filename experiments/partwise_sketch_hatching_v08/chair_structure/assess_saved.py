"""Independent saved-output checks, budget diagnostics and whole-object panels."""
import runtime
from runtime import js,sha
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import npz,load_asset
from hybrid import edit_metrics
UNIT=runtime.ROOT/'units/unit_007'
VIEWS=['orbit_151_36_5.1','orbit_61_24_5.1','orbit_241_24_5.1','orbit_241_60_5.1','orbit_196_36_5.1']

def main():
    records={};checks=[];payloads={};compilers=[]
    mutable={'hybrid','combined_ink','ungated_ink','proxy','structure'}
    originals={};frames={}
    for view in VIEWS:
        pair={}
        for arm in ('off','on'):
            out=UNIT/'renders'/arm/view;r=json.loads((out/'RENDER_RECEIPT.json').read_text());a=npz(out/'FRAME.npz');pair[arm]=a
            assert r['structure']['config']['enabled']==(arm=='on')
            for name,h in r['files'].items():assert sha(out/name)==h;payloads[str((out/name).relative_to(UNIT))]=h
            for p in sorted(out.glob('*.png')):
                im=Image.open(p);im.load();x=a[p.stem]
                if p.stem in ('combined_ink','other_ink','contour','seat_ink','seat_linked_ink','structure','structure_available'):x=1-x
                if x.ndim==2:x=np.repeat(x[:,:,None],3,2)
                np.testing.assert_array_equal(np.asarray(im),np.uint8(np.clip(x,0,1)*255+.5));checks.append(str(p.relative_to(UNIT)))
            for entry in json.loads((out/'build/COMPILE.json').read_text()):
                assert entry['returncode']==0;compilers.append(dict(view=view,arm=arm,returncode=entry['returncode'],argv=entry['argv']))
            # Independently rebuild sparse S from full original-row strengths.
            trace=npz(out/'TRACE.npz');weights=npz(UNIT/'delivery/assets/on/SOURCE_LINK.npz')
            ids=trace['source_index'];sid=trace['sample_index'];w=trace['alpha']*trace['T']
            np.testing.assert_allclose(w,trace['weight'],atol=1e-14,rtol=0)
            s=np.bincount(sid,w*weights['ink_strength'][ids],minlength=len(trace['xy']))
            x,y=trace['xy'].T;np.testing.assert_allclose(s,a['support'][y,x],atol=1e-6,rtol=0)
        off,on=pair['off'],pair['on'];frames[view]=pair
        assert set(off)==set(on)
        fixed=[]
        for k in off:
            if k not in mutable:np.testing.assert_array_equal(off[k],on[k]);fixed.append(k)
        np.testing.assert_array_equal(off['structure'],np.zeros_like(off['structure']))
        np.testing.assert_array_equal(on['structure'],on['structure_available'])
        np.testing.assert_array_equal(off['hybrid'],off['base_hybrid'])
        np.testing.assert_array_equal(off['proxy'],off['base_proxy'])
        oldpath=UNIT/'inputs/reference'/view/'FRAME.npz';oldcheck=None
        if oldpath.exists():
            old=npz(oldpath);oldcheck={k:bool(np.array_equal(v,off[k])) for k,v in old.items()}
            assert all(oldcheck.values()),oldcheck
        delta=np.abs(on['hybrid']-off['hybrid']).sum(2);mask=on['structure']>0
        assert not np.any(delta[~mask])
        # Independent coarse-pixel union bounds (exact AA union already tested).
        assert np.all(on['combined_ink']>=off['combined_ink']-1e-7)
        assert np.all(on['combined_ink']<=off['combined_ink']+on['structure']+1e-7)
        rendered=on['paper']*(1-on['combined_ink'][:,:,None])+.03*on['combined_ink'][:,:,None]
        np.testing.assert_array_equal(rendered,on['hybrid'])
        per_region={str(i):dict(pixels=int((on['regions']==i).sum()),increment_L1=float(delta[on['regions']==i].sum()),
                     structure_mass=float(on['structure'][on['regions']==i].sum())) for i in range(6)}
        r=json.loads((UNIT/'renders/on'/view/'RENDER_RECEIPT.json').read_text())
        records[view]=dict(fixed_arrays_exact=fixed,off_recovers_unit006=oldcheck,
            structure=r['structure']['diagnostics'],structure_pixels=int((on['structure']>1/255).sum()),
            incremental_raw_L1=float(delta.sum()),changed_pixels=int((delta>1/255).sum()),max_pixel_raw_L1=float(delta.max()),
            original_ink_mass=float(off['combined_ink'].sum()),new_ink_mass=float(on['combined_ink'].sum()),
            per_authored_region=per_region,increment_outside_actual_structure_support_L1=float(delta[~mask].sum()),
            absolute_source_change={arm:edit_metrics(a['source'],a['hybrid'],a['regions'],4) for arm,a in pair.items()},
            scope='Per-region values use inherited rough labels, not independent intent masks. Historical seat-far absolute source difference includes fixed global paper and intentional rear structure; not a local-leakage pass.')
    mesh,paths,meta,link,b=load_asset(UNIT/'delivery/assets/on')
    for r in range(1,6):assert sha(UNIT/f'delivery/assets/on/region_{r}.npz')==sha(UNIT/f'delivery/assets/base/region_{r}.npz')
    out=UNIT/'media';out.mkdir(exist_ok=True)
    def panel(name,cols):
        sheet=Image.new('RGB',(384*len(cols),410*len(VIEWS)),'white');d=ImageDraw.Draw(sheet)
        for j,view in enumerate(VIEWS):
            for i,(label,arm,key,invert) in enumerate(cols):
                a=frames[view][arm][key];a=1-a if invert else a
                if a.ndim==2:a=np.repeat(a[:,:,None],3,2)
                im=Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5));sheet.paste(im,(384*i,410*j+26))
                d.text((384*i+4,410*j+3),view+' | '+label,fill='black')
        sheet.save(out/name)
    panel('NATURAL_COMPARISON.png',[('Original GS','on','source',False),('Structure OFF','off','hybrid',False),('Structure ON','on','hybrid',False),('Conventional proxy ON','on','proxy',False)])
    panel('WHOLE_LAYERS.png',[('Original GS','on','source',False),('Fixed paper','on','paper',False),('Unchanged contour','on','contour',True),('Authored structure','on','structure',True),('Combined ink','on','combined_ink',True),('Hybrid ON','on','hybrid',False)])
    js(UNIT/'OUTPUT_AUDIT.json',dict(views=records,png_array_checks=len(checks),checked_pngs=checks,payload_hashes=payloads,compiler_commands=compilers,
         source_count=link['source_count'],unknown_rows=int(b['unknown'].sum()),scientific_scope='One authored additional detail, unequal ink budget; no geometry/semantic/source-path certification',
         original_paths_unchanged=True,all_old_reference_arrays_recovered=True,new_actual_scene_renders=10,new_video=False))
    print(json.dumps({v:{k:r[k] for k in ('structure_pixels','incremental_raw_L1','changed_pixels')} for v,r in records.items()},indent=2))
if __name__=='__main__':main()
