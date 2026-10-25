"""Post-evaluation visibility diagnosis on paired material points.

Uses exactly A's saved centerline samples and projected-length weights for both
carriers, avoiding a changed denominator or independent resampling of T.
No image, geometry, visibility threshold or scientific protocol is changed.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js
import numpy as np
from geometry import project
from visibility_fixed import cast_points,TOLERANCE
from hatching import visibility_masks
from run_embedding import protocol,check_assets,load_assets,npz

def main():
    p=protocol();check_assets();refs,_,_,_=load_assets();rows=[]
    for v in (v for v in p['views'] if v['kind']=='dev' and v['camera']['view'] in ('orbit_61_24_5.3','orbit_241_24_5.3')):
        c=v['camera'];totals=np.zeros((5,5),float);counts=np.zeros((5,5),np.int64)
        for part,ref in zip(('old','added'),refs):
            a=npz(UNIT/'asset'/('A_'+part+'.npz'));t=npz(UNIT/'asset'/('T_'+part+'.npz'))
            s=npz(UNIT/'attribution'/c['view']/('A_'+part+'_SAMPLES.npz'));seg=s['segment_index']
            material=np.empty(len(seg));uv_end,z_end=project(a['points'].reshape(-1,3),c);z_end=z_end.reshape(-1,2)
            for i in np.unique(seg):
                ix=np.flatnonzero(seg==i);screen=(np.arange(len(ix))+.5)/len(ix);z0,z1=z_end[i]
                material[ix]=screen*z0/((1-screen)*z1+screen*z0)
            xyzA=a['points'][seg,0]*(1-material[:,None])+a['points'][seg,1]*material[:,None]
            uvA,zA=project(xyzA,c)
            np.testing.assert_allclose(uvA,s['uv'],atol=1e-9,rtol=0);np.testing.assert_allclose(zA,s['center_depth'],atol=1e-9,rtol=0)
            xyz=t['points'][seg,0]*(1-material[:,None])+t['points'][seg,1]*material[:,None];uv,z=project(xyz,c)
            hit_z,hit_face,hit_region=cast_points(ref,c,uv)
            status=np.zeros(len(seg),np.uint8);inside=(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<c['width'])&(uv[:,1]<c['height'])
            status[~inside|~np.isfinite(hit_z)]=1
            bits=np.left_shift(np.uint64(1),hit_region.astype(np.uint64));support=visibility_masks(t,4)[seg]
            status[(status==0)&((bits&support)==0)]=2;status[(status==0)&(np.abs(z-hit_z)>TOLERANCE)]=3;status[z<=.2]=4
            np.add.at(totals,(s['status'],status),s['length_weight']);np.add.at(counts,(s['status'],status),1)
        rows.append(dict(view=c['view'],status_order=['visible','outside_or_no_surface','region_rejected','depth_rejected','near_plane'],
            A_status_rows_T_status_columns_A_projected_px=totals,sample_counts=counts,
            A_visible_length=float(totals[0].sum()),T_visible_with_fixed_A_weights=float(totals[:,0].sum()),
            both_visible=float(totals[0,0]),visible_to_depth_rejected=float(totals[0,3]),depth_rejected_to_visible=float(totals[3,0]),
            scope='Identical material samples and fixed A projection weights; original proxy visibility reference, not physical truth or temporal evidence.'))
    js(UNIT/'MATERIAL_VISIBILITY.json',rows)
    for r in rows:print(r['view'],r['A_visible_length'],r['T_visible_with_fixed_A_weights'],r['visible_to_depth_rejected'],r['depth_rejected_to_visible'],flush=True)

if __name__=='__main__':main()
