"""Frozen relative-gap compression of native CSR prefixes into depth layers."""
import warnings
import numpy as np


def local_depth_scale(front):
    h,w=front.shape;padded=np.pad(front,2);differences=[]
    for dy in range(5):
        for dx in range(5):
            if (dy,dx)==(2,2):continue
            neighbor=padded[dy:dy+h,dx:dx+w]
            differences.append(np.where((front>0)&(neighbor>0),np.abs(front-neighbor),np.nan))
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        median=np.nanmedian(np.stack(differences),axis=0)
    return np.maximum.reduce([.002*front,np.nan_to_num(median),np.full_like(front,1e-12)])


def compress_layers(e,native_alpha):
    off=e['offsets'];sizes=np.diff(off);pixels=len(sizes);valid=sizes>0
    pix=np.repeat(np.arange(pixels),sizes);z=e['z'];w=e['w'].astype('f8')
    front=np.zeros(pixels);front[valid]=z[off[:-1][valid]]
    scale=local_depth_scale(front.reshape(native_alpha.shape))
    start=np.zeros(len(z),bool);start[off[:-1][valid]]=True
    if len(z)>1:start[1:] |= np.diff(z)>3*scale.ravel()[pix[1:]]
    assignment=np.cumsum(start)-1;num=int(start.sum());lpix=pix[start]
    counts=np.bincount(lpix,minlength=pixels);loff=np.r_[0,np.cumsum(counts)]
    mass=np.bincount(assignment,weights=w,minlength=num)
    depth=np.bincount(assignment,weights=w*z,minlength=num)/np.maximum(mass,1e-12)
    rgb=np.stack([np.bincount(assignment,weights=w*e['rgb'][:,c],minlength=num) for c in range(3)],axis=-1)
    rank=np.arange(num)-loff[lpix];keep=rank<4
    dense_mass=np.zeros((pixels,4));dense_depth=np.zeros_like(dense_mass);dense_index=np.full((pixels,4),-1,'i8')
    dense_mass[lpix[keep],rank[keep]]=mass[keep];dense_depth[lpix[keep],rank[keep]]=depth[keep];dense_index[lpix[keep],rank[keep]]=np.flatnonzero(keep)
    A=np.bincount(pix,weights=w,minlength=pixels)
    seed=(mass>=.05*native_alpha.ravel()[lpix])&(mass>=.1)&(A[lpix]>=.5)&keep
    overflow=np.bincount(lpix[~keep],weights=mass[~keep],minlength=pixels).reshape(native_alpha.shape)
    over_rgb=np.stack([np.bincount(lpix[~keep],weights=rgb[~keep,c],minlength=pixels).reshape(native_alpha.shape) for c in range(3)],axis=-1)
    return dict(assignment=assignment,layer_offsets=loff,layer_mass=mass,layer_depth=depth,
                layer_rgb=rgb,layer_seedable=seed,histogram_p=w/np.maximum(mass[assignment],1e-12),
                local_scale=scale,retained_mass=dense_mass.reshape((*native_alpha.shape,4)),
                retained_depth=dense_depth.reshape((*native_alpha.shape,4)),retained_index=dense_index.reshape((*native_alpha.shape,4)),
                layer_count=counts.reshape(native_alpha.shape),overflow_mass=overflow,overflow_rgb=over_rgb,
                tail_alpha=e['tail_alpha'],tail_rgb=e['tail_rgb'])
