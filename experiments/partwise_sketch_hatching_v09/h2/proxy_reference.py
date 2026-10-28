"""Correct supplemental conventional reference: no source responsibility gating."""
import runtime
from runtime import js,sha
from pathlib import Path
import numpy as np
import json
from run_h2 import UNIT,CODE,VIEWS,ARMS,low,save
from linked_asset import load_asset,npz,png
from render import render,RenderCache
from structure import raster_structure
from review_outputs import panel

def main():
    mesh,paths,meta,_,_=load_asset(UNIT/'inputs/assets/on');curve=npz(UNIT/'inputs/assets/on/structure.npz');rows=[];checks=[]
    for view in VIEWS:
        c=json.loads((UNIT/f'inputs/cameras/{view}.json').read_text());structure,_=raster_structure(mesh,curve,c,2);row=[]
        for arm in ARMS:
            p=npz(UNIT/f'paths/{arm}.npz');cache=RenderCache()
            result=render(mesh,{4:paths[4],5:p},meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),cache)
            data=cache.value;layers={r:np.maximum.reduce(list(v.values())).astype(np.float32)*np.float32(meta['styles'][str(r)]['ink_strength']) for r,v in data['coverage'].items()}
            ink=low(np.maximum.reduce([layers[4],layers[5],data['contour'],structure]));img=1-ink
            folder=UNIT/f'conventional/{view}/{arm}';folder.mkdir(parents=True,exist_ok=False)
            save(folder/'FRAME.npz',image=img,raw_seat=low(layers[4]),target_ink=low(layers[5]),structure=low(structure),combined_ink=ink)
            png(folder/'image.png',img)
            policy=npz(UNIT/f'renders/{view}/natural/{arm}/FRAME.npz')
            np.testing.assert_array_equal(low(layers[5]),policy['target_ink']);np.testing.assert_array_equal(low(structure),policy['structure'])
            row.append((view+' | '+arm+' | Proxy, no S',folder/'image.png'))
            checks.append(dict(view=view,arm=arm,target_and_structure_exact=True,source_S_applied=False,full_ink_mass=float(ink.sum())))
        rows.append(row)
    panel(UNIT/'media/CONVENTIONAL_PROXY_CORRECTED.png',rows)
    js(UNIT/'DISPLAY_CORRECTION.json',dict(problem='Initial proxy.png and media/PROXY_REFERENCE.png were white-background hybrid ink: seat source S remained applied; label conventional proxy was incorrect.',
        preserved='All original files retained unchanged. Do not cite them as an ungated conventional proxy.',
        corrected='conventional/*/*/FRAME.npz and media/CONVENTIONAL_PROXY_CORRECTED.png use raw seat ink with NO S; identical target hatch, structure, contours, visibility and style.',
        scientific_H2_effect='None: U/S/D/sham hybrid renders, fixed source and reported policy metrics unchanged; this correction concerns the supplemental reference only.',checks=checks))
    print(json.dumps(dict(corrected_frames=len(checks),hybrid_science_unchanged=True)))
if __name__=='__main__':main()
