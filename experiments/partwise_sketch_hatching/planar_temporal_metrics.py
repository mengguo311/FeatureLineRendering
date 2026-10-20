"""Rendered-image temporal metrics; no renderer imports or anchor-only score."""
import round015_common
import numpy as np
from scipy.ndimage import map_coordinates

def profiles(images, uv, normal, offsets, threshold):
    centers=[];present=[];peaks=[]
    for image, points in zip(images,uv):
        q=points[:,None,:]+np.asarray(offsets)[None,:,None]*normal
        values=map_coordinates(np.asarray(image,float)/255.,[q[...,1],q[...,0]],order=1,mode='constant',cval=0.)
        mass=values.sum(axis=1);peak=values.max(axis=1)
        centers.append(np.divide(values@np.asarray(offsets),mass,out=np.zeros(len(points)),where=mass>0))
        present.append(peak>=threshold);peaks.append(peak)
    return np.array(centers),np.array(present),np.array(peaks)

def translated(image,dx,dy):
    out=np.zeros_like(image);h,w=image.shape
    if abs(dx)>=w or abs(dy)>=h:return out
    xs=slice(max(0,-dx),min(w,w-dx));ys=slice(max(0,-dy),min(h,h-dy))
    out[slice(max(0,dy),min(h,h+dy)),slice(max(0,dx),min(w,w+dx))]=image[ys,xs]
    return out

def stats(values):
    a=np.asarray(values,float)
    return {'count':int(a.size),'mean':float(a.mean()) if a.size else None,'p95':float(np.percentile(a,95)) if a.size else None,'max':float(a.max()) if a.size else None}

def compare(images,reference,uv,normal,eligible,offsets,threshold):
    images=np.asarray(images);reference=np.asarray(reference)
    cc,cp,ck=profiles(images,uv,normal,offsets,threshold)
    rc,rp,rk=profiles(reference,uv,normal,offsets,threshold)
    persistent=np.all(eligible,axis=0);mask=np.broadcast_to(persistent,cp.shape)
    both=mask&cp&rp;missing=mask&rp&~cp
    err=images.astype(int)-reference.astype(int)
    residual=np.diff(err,axis=0)
    frames=[]
    for i in range(len(images)):
        frames.append({'frame':i,'image_L1_uint8':int(abs(err[i]).sum()),'image_max_uint8':int(abs(err[i]).max()),'reference_ink_mass_uint8':int(reference[i].sum()),'candidate_ink_mass_uint8':int(images[i].sum()),'eligible_samples':int(eligible[i].sum()),'persistent_samples':int(persistent.sum()),'reference_present_persistent':int((rp[i]&persistent).sum()),'candidate_present_persistent':int((cp[i]&persistent).sum()),'extra_missing_samples':int(missing[i].sum()),'extra_centroid_abs_px':stats(abs(cc[i]-rc[i])[both[i]]),'reference_abs_centroid_px':stats(abs(rc[i])[mask[i]&rp[i]])})
    pairs=[]
    for i in range(1,len(images)):
        m=both[i]&both[i-1]
        ref_delta=reference[i].astype(int)-reference[i-1].astype(int)
        cand_delta=images[i].astype(int)-images[i-1].astype(int)
        pairs.append({'pair':[i-1,i],'geometric_common_samples':int((eligible[i]&eligible[i-1]).sum()),'reference_frame_change_L1_uint8':int(abs(ref_delta).sum()),'candidate_frame_change_L1_uint8':int(abs(cand_delta).sum()),'extra_frame_change_L1_uint8':int(abs(residual[i-1]).sum()),'extra_frame_change_max_uint8':int(abs(residual[i-1]).max()),'candidate_normal_motion_residual_px':stats(abs(cc[i]-cc[i-1])[m]),'reference_normal_motion_residual_px':stats(abs(rc[i]-rc[i-1])[m]),'extra_normal_motion_abs_px':stats(abs((cc[i]-cc[i-1])-(rc[i]-rc[i-1]))[m])})
    motion_values=[p['extra_normal_motion_abs_px']['max'] for p in pairs if p['extra_normal_motion_abs_px']['max'] is not None]
    report={'frames':frames,'pairs':pairs,'persistent_samples':int(persistent.sum()),'persistent_fraction_all_path':float(persistent.mean()),'reference_all_persistent_present':bool(rp[mask].all()),'extra_dropout_samples':int(missing.sum()),'extra_dropout_fraction':float(missing.sum()/max(1,mask.sum())),'extra_centroid_abs_px':stats(abs(cc-rc)[both]),'reference_abs_centroid_px':stats(abs(rc)[mask&rp]),'extra_normal_motion_max_px':max(motion_values,default=None),'full_frame_max_uint8':int(abs(err).max()),'full_frame_L1_uint8':int(abs(err).sum()),'temporal_residual_max_uint8':int(abs(residual).max()),'temporal_residual_L1_uint8':int(abs(residual).sum())}
    arrays={'candidate_centroid':cc,'candidate_present':cp,'candidate_profile_peak':ck,'reference_centroid':rc,'reference_present':rp,'reference_profile_peak':rk,'persistent_eligible':persistent,'eligible':eligible,'known_correspondence_uv':uv,'full_frame_error':err,'temporal_residual':residual}
    return report,arrays
