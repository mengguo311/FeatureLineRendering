"""Frozen symmetric actual raster temporal evaluation, including all failures."""
import runtime
from runtime import ROOT as UNIT,js
import json
import numpy as np
from scipy import ndimage
from linked_asset import npz,load_asset
from geometry import project,backproject
from temporal import correspondence,sample,compare

def ray_hit(scene,c,uv):
    import open3d as o3d
    uv=np.asarray(uv);E=np.array(c['extrinsic']);inv=np.linalg.inv(E[:3,:3]);origin=-inv@E[:3,3]
    local=np.column_stack([(uv[:,0]-c['cx'])/c['fx'],(uv[:,1]-c['cy'])/c['fy'],np.ones(len(uv))])
    hit=scene.cast_rays(o3d.core.Tensor(np.c_[np.broadcast_to(origin,(len(uv),3)),local@inv.T].astype(np.float32)),nthreads=1)
    return hit['t_hit'].numpy(),hit['primitive_ids'].numpy()

def center_measure(mesh,scene,centers,arm,a,b,ca,cb):
    uv=centers[arm+'_uv'];weight=centers[arm+'_weight'];za,fa=ray_hit(scene,ca,uv)
    inside=(uv[:,0]>=0)&(uv[:,0]<=383)&(uv[:,1]>=0)&(uv[:,1]<=383)
    valid=inside&np.isfinite(za)&(fa<len(mesh['faces']));label=np.zeros(len(uv),bool);label[valid]=mesh['regions'][fa[valid]]==5;visible=valid&label
    if arm=='B1':visible&=np.abs(za-centers['B1_depth'])<=.004
    own=sample(a['own_aa'],(uv+.5)*2-.5)>1/255
    source=visible&own
    q=np.full_like(uv,-100.);z=np.zeros(len(uv))
    q[source],z[source]=project(backproject(uv[source],za[source],ca),cb)
    zb,fb=ray_hit(scene,cb,q);dest=(q[:,0]>=0)&(q[:,0]<=383)&(q[:,1]>=0)&(q[:,1]<=383)&(fb<len(mesh['faces']))&np.isfinite(zb)
    labelb=np.zeros(len(uv),bool);labelb[dest]=mesh['regions'][fb[dest]]==5
    common=source&dest&labelb&(np.abs(z-zb)<=.004)
    distance=ndimage.distance_transform_edt(b['own_aa']<=1/255)/2
    dist=sample(distance,(q+.5)*2-.5,cval=384.)
    target_ink=sample(b['own_aa'],(q+.5)*2-.5)>1/255
    mass=float(weight[common].sum())
    return dict(raw_projected_length_px=float(weight.sum()),source_proxy_visible_length_px=float(weight[visible].sum()),
        source_visible_without_own_ink_length_px=float(weight[visible&~own].sum()),source_visible_with_own_ink_length_px=float(weight[source].sum()),
        common_visible_with_source_ink_length_px=mass,common_visible_without_destination_ink_length_px=float(weight[common&~target_ink].sum()),
        centerline_to_actual_ink_mean_px=float(np.sum(weight[common]*dist[common])/mass) if mass>0 else None,
        centerline_to_actual_ink_p95_px=float(np.quantile(dist[common],.95)) if common.any() else None,
        proper_destination_rejection_length_px=float(weight[source&~common].sum()),
        scope='Each arm own screen centerline samples at <=.5px, actual own-AA supported, shared continuous first-hit visibility; B1 hidden projected segments rejected by their true depth. Distances are to destination actual own ink, not known stroke identity.')

def main():
    import open3d as o3d
    mesh,_,_,_,_=load_asset(UNIT/'inputs/assets/on');scene=o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    rows=json.loads((UNIT/'CAMERAS.json').read_text());arc=[r for r in rows if 'index' in r];records=[]
    for ra,rb in zip(arc[:-1],arc[1:]):
        for s,t in ((ra,rb),(rb,ra)):
            da=UNIT/'renders'/s['key'];db=UNIT/'renders'/t['key'];ca=npz(da/'COMMON.npz');cb=npz(db/'COMMON.npz')
            uv,ok,diag=correspondence(ca['depth_native'],ca['native_target'],s['camera'],cb['depth_native'],cb['native_target'],t['camera'])
            centers=npz(da/'CENTERLINES.npz');metrics={}
            for mode in ('natural','matched'):
                metrics[mode]={}
                for arm in ('B0','B1'):
                    a=npz(da/mode/arm/'FRAME.npz');b=npz(db/mode/arm/'FRAME.npz')
                    own=compare(a['own_ink'],b['own_ink'],uv,ok)
                    own['centerlines']=center_measure(mesh,scene,centers,arm,a,b,s['camera'],t['camera'])
                    inc_a=np.abs(a['hybrid']-ca['baseline']).sum(2);inc_b=np.abs(b['hybrid']-cb['baseline']).sum(2)
                    own['own_ink_present_no_composite_increment_pixels']=int((ok&(a['own_ink']>1/255)&(inc_a<=1/255)).sum())
                    own['composite_increment_dropout_own_present_pixels']=int((ok&(inc_a>1/255)&(sample(inc_b,uv)<=1/255)&(sample(b['own_ink'],uv)>1/255)).sum())
                    metrics[mode][arm]=own
            records.append(dict(source=s['key'],destination=t['key'],visibility=diag,metrics=metrics))
        print(json.dumps(dict(pair=[ra['key'],rb['key']])),flush=True)
    summary={}
    for mode in ('natural','matched'):
        summary[mode]={}
        for arm in ('B0','B1'):
            rr=[r['metrics'][mode][arm] for r in records];cc=[r['centerlines'] for r in rr]
            mass=sum(c['common_visible_with_source_ink_length_px'] for c in cc)
            summary[mode][arm]=dict(common_pixel_observations=sum(r['common_pixels'] for r in rr),L1_per_common_pixel=sum(r['L1'] for r in rr)/sum(r['common_pixels'] for r in rr),
                mean_pair_union_normalized_L1=float(np.mean([r['L1_per_union_ink'] for r in rr if r['L1_per_union_ink'] is not None])),
                source_ink_pixel_observations=sum(r['source_ink_pixels'] for r in rr),ink_to_empty_pixel_observations=sum(r['ink_to_empty_pixels'] for r in rr),
                common_centerline_length_px=mass,centerline_to_actual_ink_mean_px=sum(c['centerline_to_actual_ink_mean_px']*c['common_visible_with_source_ink_length_px'] for c in cc if c['centerline_to_actual_ink_mean_px'] is not None)/mass,
                common_centerline_without_destination_ink_length_px=sum(c['common_visible_without_destination_ink_length_px'] for c in cc),
                source_visible_without_own_ink_length_px=sum(c['source_visible_without_own_ink_length_px'] for c in cc),
                source_visible_length_px=sum(c['source_proxy_visible_length_px'] for c in cc),
                own_present_no_increment_pixels=sum(r['own_ink_present_no_composite_increment_pixels'] for r in rr),
                increment_dropout_with_own_present_pixels=sum(r['composite_increment_dropout_own_present_pixels'] for r in rr))
    js(UNIT/'TEMPORAL.json',dict(frames=len(arc),directional_pairs=len(records),summary=summary,pairs=records,
        scope='Single fixed Chair arc; symmetric actual own ink, same proxy reference, no physical GT. Pair/sample counts are not independent objects; nearest own ink may belong to a neighboring stroke, so read together with full images and warp L1. No LOD or planned trim in either arm.'))
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
