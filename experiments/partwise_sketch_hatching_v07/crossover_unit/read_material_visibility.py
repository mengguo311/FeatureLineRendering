"""Within-family visibility transitions on the same material samples and weights."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js
import numpy as np
from geometry import project
from visibility_fixed import cast_points,TOLERANCE
from hatching import visibility_masks
from run_crossover import protocol,check_assets,load_assets,npz

def main():
    p=protocol();check_assets();refs,_,_,_=load_assets();rows=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        camera=v['camera']
        for source,dest in (('OO','OC'),('CO','CC')):
            totals=np.zeros((5,5),float);counts=np.zeros((5,5),np.int64)
            for part,ref in zip(('old','added'),refs):
                a=npz(UNIT/'asset'/(source+'_'+part+'.npz'));t=npz(UNIT/'asset'/(dest+'_'+part+'.npz'))
                for key in ('face','bary'):np.testing.assert_array_equal(a[key],t[key])
                s=npz(UNIT/'attribution'/camera['view']/(source+'_'+part+'_SAMPLES.npz'));seg=s['segment_index']
                material=np.empty(len(seg));_,z_end=project(a['points'].reshape(-1,3),camera);z_end=z_end.reshape(-1,2)
                for i in np.unique(seg):
                    ix=np.flatnonzero(seg==i);screen=(np.arange(len(ix))+.5)/len(ix);z0,z1=z_end[i]
                    material[ix]=screen*z0/((1-screen)*z1+screen*z0)
                xyzA=a['points'][seg,0]*(1-material[:,None])+a['points'][seg,1]*material[:,None]
                uvA,zA=project(xyzA,camera)
                np.testing.assert_allclose(uvA,s['uv'],atol=1e-9,rtol=0);np.testing.assert_allclose(zA,s['center_depth'],atol=1e-9,rtol=0)
                xyz=t['points'][seg,0]*(1-material[:,None])+t['points'][seg,1]*material[:,None];uv,z=project(xyz,camera)
                hit_z,hit_face,hit_region=cast_points(ref,camera,uv)
                status=np.zeros(len(seg),np.uint8);inside=(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<camera['width'])&(uv[:,1]<camera['height'])
                status[~inside|~np.isfinite(hit_z)]=1
                bits=np.left_shift(np.uint64(1),hit_region.astype(np.uint64));support=visibility_masks(t,4)[seg]
                status[(status==0)&((bits&support)==0)]=2;status[(status==0)&(np.abs(z-hit_z)>TOLERANCE)]=3;status[z<=.2]=4
                np.add.at(totals,(s['status'],status),s['length_weight']);np.add.at(counts,(s['status'],status),1)
            rows.append(dict(view=camera['view'],source=source,destination=dest,
                status_order=['visible','outside_or_no_surface','region_rejected','depth_rejected','near_plane'],
                source_status_rows_destination_status_columns_fixed_source_projected_px=totals,sample_counts=counts,
                source_visible_length=float(totals[0].sum()),destination_visible_with_fixed_source_weights=float(totals[:,0].sum()),
                both_visible=float(totals[0,0]),visible_to_depth_rejected=float(totals[0,3]),depth_rejected_to_visible=float(totals[3,0]),
                scope='Same material points only within one saved layout family; O-embedding projection weights. Fixed original proxy is not physical truth.'))
    js(UNIT/'MATERIAL_VISIBILITY.json',rows)
    for r in rows:print(r['view'],r['source'],r['destination'],r['source_visible_length'],r['destination_visible_with_fixed_source_weights'],r['visible_to_depth_rejected'],r['depth_rejected_to_visible'],flush=True)

if __name__=='__main__':main()
