"""Finite real-model selection coverage and complete-object construction previews."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
from PIL import Image
from demo import load_asset
from geometry import ray_surface
from selection_draft import SelectionDraft
from media import contact

def run(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text());mesh,_,meta=load_asset(unit/'assets/original')
    draft=SelectionDraft(mesh,meta['mesh_sha256'],3);states=[]
    for step in p['selection']['steps']:
        draft.apply(step['camera'],step['rectangle'],step['operation']);states.append(draft.face_ids.copy())
    selected=states[-1];first=states[0]
    out=unit/'selection';out.mkdir()
    np.savez_compressed(out/'STEPS.npz',**{f'step_{i}':s for i,s in enumerate(states)})
    items=[];views=[]
    for i,c in enumerate(p['construction_cameras']):
        proxy=np.asarray(Image.open(unit/f'construction/view_{i:02d}_proxy.png').convert('RGB'),float)/255
        _,face,_,_=ray_surface(mesh,c,2)
        items.append((c['view']+' | fixed proxy',Image.fromarray(np.uint8(proxy*255+.5))))
        counts=[]
        for name,ids in [('First rectangle only',first),('Final multi-view selection',selected)]:
            mask=np.isin(face,ids).reshape(512,2,512,2).mean((1,3))
            overlay=proxy*(1-.75*mask[:,:,None])+np.array([.85,.16,.55])*(.75*mask[:,:,None])
            im=Image.fromarray(np.uint8(overlay*255+.5));im.save(out/f'view_{i:02d}_{"first" if name.startswith("First") else "final"}.png')
            items.append((name,im));counts.append(float(mask.sum()))
        views.append(dict(view=c['view'],first_visible_pixel_coverage=counts[0],final_visible_pixel_coverage=counts[1]))
    contact(out/'selection_all_views.png',items,cols=3,size=512,title='Drums | same proxy | manual add/subtract across three construction views')
    # Exact indexed-edge topology diagnostic; no repair, weld or nearest-neighbor expansion.
    parents={int(f):int(f) for f in selected};owners={}
    def root(f):
        while parents[f]!=f:
            parents[f]=parents[parents[f]];f=parents[f]
        return f
    for f in selected:
        f=int(f);tri=mesh['faces'][f]
        for i in range(3):
            edge=tuple(sorted((int(tri[i]),int(tri[(i+1)%3]))))
            if edge in owners:parents[root(f)]=root(owners[edge])
            else:owners[edge]=f
    _,counts=np.unique([root(int(f)) for f in selected],return_counts=True)
    areas=np.linalg.norm(np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0]),axis=1)/2
    record=dict(utc=now(),steps=draft.steps,first_faces=len(first),final_faces=len(selected),
        newly_included_faces=len(np.setdiff1d(selected,first)),removed_first_faces=len(np.setdiff1d(first,selected)),
        first_area_world2=float(areas[first].sum()),final_area_world2=float(areas[selected].sum()),
        selected_indexed_edge_components=len(counts),component_face_counts=sorted(map(int,counts),reverse=True),
        views=views,scope='manual selected proxy faces; coverage is not independent semantic completeness or accurate reconstructed geometry')
    js(out/'SELECTION_EVIDENCE.json',record)
    print(json.dumps(record))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unit',required=True,type=Path);run(parser.parse_args().unit)
