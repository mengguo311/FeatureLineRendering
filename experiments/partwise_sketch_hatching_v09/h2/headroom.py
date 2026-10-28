import runtime
from runtime import js,sha
from pathlib import Path
import json,time
import numpy as np
from linked_asset import load_asset,npz
from geometry import project
from association import crossings

UNIT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_001')
def main():
    start=time.monotonic();mesh,paths,meta,link,b=load_asset(UNIT/'inputs/assets/on')
    full=npz(UNIT/'inputs/assets/on/structure.npz');sel=(full['author_edge']<=9)&(mesh['regions'][full['face']]==5)
    guide={k:v[sel] for k,v in full.items()};events=crossings(paths[5],guide)
    camera=json.loads((UNIT/'inputs/cameras/orbit_151_36_5.1.json').read_text())
    import open3d as o3d
    scene=o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    x=np.asarray([e['point'] for e in events]);uv,z=project(x,camera)
    E=np.array(camera['extrinsic']);origin=-np.linalg.inv(E[:3,:3])@E[:3,3]
    direction=(x-origin)/z[:,None]
    hit=scene.cast_rays(o3d.core.Tensor(np.c_[np.broadcast_to(origin,x.shape),direction].astype(np.float32)),nthreads=1)
    zz=hit['t_hit'].numpy();ff=hit['primitive_ids'].numpy()
    for i,e in enumerate(events):
        e.update(build_uv=uv[i].tolist(),build_depth=float(z[i]),first_hit_depth=float(zz[i]),first_hit_face=int(ff[i]),visible=bool(abs(z[i]-zz[i])<=.004),author_edge=int(guide['author_edge'][e['guide_row']]))
    lengths=np.linalg.norm(paths[5]['points'][:,1]-paths[5]['points'][:,0],axis=1)
    ids=sorted(set(e['parent_id'] for e in events))
    record=dict(verdict='HEADROOM' if any(e['visible'] for e in events) else 'UNIDENTIFIABLE',events=events,
        same_face_crossings=len(events),visible_crossings=sum(e['visible'] for e in events),affected_parent_ids=ids,
        affected_parent_length=float(lengths[np.isin(paths[5]['stroke_id'],ids)].sum()),raw_target_length=float(lengths.sum()),
        guide_segments=int(sel.sum()),guide_full_author_edges=list(range(10)),guide_role='Confirmed authored style margin/direction guide only, no semantic relabeling; no closure',
        source_scope='Original GS remains frozen; upper-back paths and guide are proxy-only',seconds=time.monotonic()-start)
    js(UNIT/'HEADROOM.json',record);np.savez_compressed(UNIT/'GUIDE.npz',**guide)
    print(json.dumps({k:v for k,v in record.items() if k!='events'},default=runtime.json_default))
if __name__=='__main__':main()
