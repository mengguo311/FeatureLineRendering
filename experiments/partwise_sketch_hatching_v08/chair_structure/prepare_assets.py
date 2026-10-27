import runtime
from runtime import sha,js
from pathlib import Path
import json
import numpy as np
from linked_asset import load_asset
from structure_asset import author_structure,toggle_structure
UNIT=runtime.ROOT/'units/unit_007'
def main():
    c=json.loads((UNIT/'delivery/cameras/orbit_151_36_5.1.json').read_text())
    on=author_structure(UNIT/'delivery/assets/base',UNIT/'delivery/assets/on',UNIT/'AUTHOR.json',c)
    toggle_structure(on,UNIT/'delivery/assets/off',False)
    mesh,p,_,_,_=load_asset(on)
    # Independent actual Open3D first-hit checks of interval midpoints;
    # this checks the analytic projection, without modifying its selection.
    import open3d as o3d
    from structure import load_structure
    from geometry import project
    curve,_=load_structure(on,mesh);x=curve['points'].mean(1);uv,z=project(x,c)
    E=np.asarray(c['extrinsic']);R=E[:3,:3];origin=-np.linalg.solve(R,E[:3,3])
    directions=np.column_stack([(uv[:,0]-c['cx'])/c['fx'],(uv[:,1]-c['cy'])/c['fy'],np.ones(len(x))])@np.linalg.inv(R).T
    rays=np.column_stack([np.broadcast_to(origin,directions.shape),directions]).astype(np.float32)
    scene=o3d.t.geometry.RaycastingScene(nthreads=1);scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    hits=scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)
    depths=hits['t_hit'].numpy();f=hits['primitive_ids'].numpy()
    error=float(np.max(np.abs(depths-z))) if len(z) else None
    assert len(z)==0 or (np.isfinite(depths).all() and error<1e-4)
    js(UNIT/'PROJECTION_CHECK.json',dict(midpoints=len(z),depth_max_error=error,first_face_equal=int((f==curve['face']).sum()),
        scope='Independent Open3D first-hit numeric check of analytic projection; same proxy, not physical GT'))
    derived={str(f.relative_to(UNIT)):sha(f) for arm in ('off','on') for f in sorted((UNIT/'delivery/assets'/arm).iterdir()) if f.is_file()}
    js(UNIT/'DERIVED_LOCK.json',derived)
    print(json.dumps(dict(projection=json.loads((on/'PROJECTION.json').read_text()),first_hit_error=error)))
if __name__=='__main__':main()
