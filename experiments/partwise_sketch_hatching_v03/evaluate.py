"""Saved-raster validation and analytic GT metrics; imports no render producer."""
from runtime import *
from diagnostic import display_metrics
from reference import screen_depth, part_leakage, mask_regions
from scipy import ndimage
from PIL import Image

def read(folder):
    with np.load(folder/'layers.npz',allow_pickle=False) as data:
        result={k:data[k].copy() for k in data.files}
    png=np.asarray(Image.open(folder/'image.png').convert('L'))
    assert np.array_equal(png,np.uint8(np.rint(255*result['image'])))
    assert all(result[k].shape==(512,512) for k in result)
    return result

def ring_reference(mesh,cfg,camera,curves,off,on,labels):
    points,weights,coalesced=[],[],[]
    centers=mesh['tri'].mean(axis=1)
    facing=np.einsum('ij,ij->i',mesh['normals'],camera['eye']-centers)
    for curve in curves:
        a,b=np.asarray(curve['points'])
        length=float(np.linalg.norm(b-a)); n=max(1,int(np.ceil(length/.002)))
        points.append(a+(np.arange(n)[:,None]+.5)/n*(b-a))
        weights.extend([length/n]*n)
        ff=curve['owners']
        contour=len(ff)==1 or len(np.unique(mesh['parts'][ff]))>1 or np.min(facing[ff])<=0<np.max(facing[ff])
        coalesced.extend([contour]*n)
    points=np.concatenate(points); weights=np.asarray(weights); coalesced=np.asarray(coalesced)
    uv,z=core.project(points,camera)
    depth,_=screen_depth(cfg['asset'],camera,uv)
    q=np.rint(uv).astype(int)
    inside=(q[:,0]>=0)&(q[:,0]<512)&(q[:,1]>=0)&(q[:,1]<512)&(z>0)
    residual=z-depth
    visible=inside&np.isfinite(depth)&(np.abs(residual)<=.006)
    hidden=inside&np.isfinite(depth)&(residual>.006)
    unknown=~(visible|hidden)
    edge=core.contour_mask(labels)
    band=ndimage.distance_transform_edt(~edge)<=2
    bounded=np.clip(q,0,511)
    aa=band[bounded[:,1],bounded[:,0]]
    eligible=visible&~coalesced
    weight=lambda m:float(weights[m].sum())
    supports={}
    for name,ink in [('B1_total',1-off['image']),('B2_total',1-on['image']),('B2_rings_only',on['rings'])]:
        dist=ndimage.distance_transform_edt(~(ink>.1)) if (ink>.1).any() else np.full(ink.shape,np.inf)
        supported=inside&(dist[bounded[:,1],bounded[:,0]]<=1.5)
        supports[name]=dict(visible_supported_world=weight(eligible&supported),
                           visible_fraction=weight(eligible&supported)/max(weight(eligible),1e-15),
                           aa_supported_world=weight(eligible&aa&supported),
                           interior_supported_world=weight(eligible&~aa&supported))
    return dict(all_authored_length_world=weight(np.ones_like(eligible)),samples=len(points),
                contour_coalesced_length_world=weight(coalesced),
                eligible_visible_ring_length_world=weight(eligible),
                visible_aa_length_world=weight(eligible&aa),visible_interior_length_world=weight(eligible&~aa),
                expected_hidden_noncontour_length_world=weight(hidden&~coalesced),
                unknown_noncontour_length_world=weight(unknown&~coalesced),
                visible_fraction_of_all_authored=weight(eligible)/weight(np.ones_like(eligible)),
                support=supports,scope='Midpoint quadrature <=.002world; analytic depth oracle. Contour-coalesced edges excluded from incremental ring support. Hidden samples not called leakage; aggregate hatch/contour can overlap ring reference.')

def controls(off,on,labels):
    def score(image,hatch=None):
        return display_metrics(off['image'],image,off['hatch'],on['hatch'] if hatch is None else hatch,
                               off['contours'],on['contours'],on['rings'],labels)
    noop=score(off['image'])
    empty=score(np.ones_like(on['image']),np.zeros_like(on['hatch']))
    drift=np.ones_like(on['image']); drift[:,3:]=on['image'][:,:-3]
    shifted=score(drift)
    assert all(x['status']=='ENGINEERING_INVALID' for x in (noop,empty,shifted))
    return dict(no_edit=dict(status=noop['status'],L1=noop['nonzero_operation_L1']),
                delete_all=dict(status=empty['status'],erased_ink=empty['erased_ink'],hatch_exact=empty['hatch_exact']),
                drift3px=dict(status=shifted['status'],outside_ring_delta=shifted['outside_ring_delta'],erased_ink=shifted['erased_ink']))

def main():
    p=json.loads((ROOT/'PROTOCOL.json').read_text())
    lock=json.loads((ROOT/'SOURCE_LOCK.json').read_text())
    for path,h in lock['files'].items(): assert sha(path)==h,path
    mesh,strokes,cfg=load_asset()
    curves=json.loads((ROOT/'audit/AUTHORED_CURVES.json').read_text())['curves']
    report=dict(frames=[],controls={},isolated_part_leakage=[],engineering_failures=[],H2='UNIDENTIFIABLE_FOR_H2',segmentation='UNCHANGED; no mIoU gain')
    for f in p['frames']:
        folder=ROOT/'renders'/f['sequence']/f['id']
        off=read(folder/'B1_like'); on=read(folder/'B2_existing')
        camera=core.camera(f['azimuth'],f['elevation'],f['distance'],512,600)
        depth,labels=core.analytic_reference(cfg['asset'],camera)
        equal=dict(parts=np.array_equal(off['parts'],on['parts']),depth=np.array_equal(off['depth'],on['depth']))
        assert all(equal.values())
        score=display_metrics(off['image'],on['image'],off['hatch'],on['hatch'],off['contours'],on['contours'],on['rings'],labels)
        ring=ring_reference(mesh,cfg,camera,curves,off,on,labels)
        yy,xx=np.where(labels>0)
        margin=int(min(xx.min(),yy.min(),511-xx.max(),511-yy.max()))
        row=dict(frame=f,display=score,geometry_buffers_exact=equal,shape_margin_px=margin,ring_reference=ring)
        if score['status']!='VALID_DISPLAY' or margin<2 or ring['eligible_visible_ring_length_world']<=0:
            report['engineering_failures'].append(f['id'])
        maskfolder=output_path(ROOT/'metrics/masks'/f'{f["id"]}.npz')
        np.savez_compressed(maskfolder,depth=depth,labels=labels)
        if f['sequence']=='static':
            source=ASSET/'renders'/f'{f["azimuth"]:03}.png'
            same=np.array_equal(np.asarray(Image.open(source).convert('RGB')),np.asarray(Image.open(folder/'B2_existing/image.png').convert('RGB')))
            row['accepted_baseline_pixel_exact']=same
            row['accepted_baseline_png_sha256']=sha(source)
            row['new_baseline_png_sha256']=sha(folder/'B2_existing/image.png')
            if not same: report['engineering_failures'].append(f['id']+'_baseline_mismatch')
            report['controls'][f['id']]=controls(off,on,labels)
            for part in (1,2,3):
                isolated=read(ROOT/'isolated'/f['id']/f'part_{part}')
                leak=part_leakage(isolated['hatch'],labels,part)
                far=mask_regions(labels,part)['far_other']
                ids=np.flatnonzero(far & (isolated['hatch']<.1))[:16]
                assert len(ids)==16
                injected=isolated['hatch'].copy(); injected.flat[ids]=1
                control=part_leakage(injected,labels,part)
                assert control['region_ink']['far_other']>leak['region_ink']['far_other']+14
                report['isolated_part_leakage'].append(dict(frame=f['id'],part=part,metrics=leak,
                    control16_wrong_part_pixels=control,selected_flat_indices=ids))
        report['frames'].append(row)
    report['valid']=not report['engineering_failures']
    report['verdict']='VALID_AUTHORED_STRUCTURE_DISPLAY_H2_UNIDENTIFIABLE' if report['valid'] else 'ENGINEERING_INVALID'
    report['scope']='One GT authored structure display, not association benefit, reconstruction, automatic extraction, preference, novelty or temporal certification.'
    write_json(ROOT/'metrics/RESULTS.json',report)
    update_status('SAVED_OUTPUT_EVALUATION_COMPLETE',execution_state='RUNNING',scientific_verdict=report['verdict'])
    print(json.dumps(dict(valid=report['valid'],frames=len(report['frames']),failures=report['engineering_failures'],verdict=report['verdict'])))
    if not report['valid']: raise SystemExit(2)

if __name__=='__main__': main()
