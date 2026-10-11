"""Original C24 TSDF, with explicit handling of sparse nonempty/empty views.

Sparse fallback ports Open3D v0.18 DepthTouchCPU's four truncated-ray samples
at stride 1. Original native stride-4 allocation is retained whenever nonempty.
Source: Open3D 0f06a149c4fb9406fd3e432a5cb0c024f38e2f0e,
cpp/open3d/t/geometry/kernel/VoxelBlockGridCPU.cpp (MIT; source ledger/license
in HDD full_reproduction_v01/source_evidence/open3d). No TSDF value change.
"""
import numpy as np
import open3d as o3d


def touch_blocks(vbg,depth,intrinsic,extrinsic):
    """Fixed C24 scale=1/max=8/voxel=.002/block=16/trunc=8 throughout."""
    if (depth.ndim!=2 or depth.dtype!=np.float32 or not np.isfinite(depth).all()
        or not np.isfinite(intrinsic).all() or not np.isfinite(extrinsic).all()):
        raise ValueError('nonfinite/invalid TSDF input')
    if intrinsic.shape!=(3,3) or extrinsic.shape!=(4,4) or intrinsic[0,0]<=0 or intrinsic[1,1]<=0:
        raise ValueError('invalid camera matrices')
    valid=(depth>0)&(depth<8);height,width=depth.shape
    sampled=valid[:height//4*4:4,:width//4*4:4]
    info={'valid_pixels':int(valid.sum()),'native_stride4_valid':int(sampled.sum()),
          'depth_scale':1.,'depth_max':8.,'voxel_size':.002,'trunc_voxel_multiplier':8.}
    if not valid.any():
        return None,dict(info,mode='EMPTY_VALID_DEPTH_NO_CONTRIBUTION',blocks=0)
    if sampled.any():
        coords=vbg.compute_unique_block_coordinates(o3d.t.geometry.Image(depth),
            o3d.core.Tensor(intrinsic),o3d.core.Tensor(extrinsic),1.0,8.0)
        return coords,dict(info,mode='C24_NATIVE_STRIDE4',blocks=int(coords.shape[0]))
    # Do not change data, threshold, voxel size, camera convention, or integrate.
    # The four float32 ray samples are the original DepthTouchCPU algorithm.
    y,x=np.nonzero(valid);k=intrinsic.astype(np.float32)
    rays=np.stack(((x.astype(np.float32)-k[0,2])/k[0,0],
                   (y.astype(np.float32)-k[1,2])/k[1,1],np.ones(len(x),np.float32)),axis=1)
    pose=np.linalg.inv(extrinsic).astype(np.float32);origin=pose[:3,3]
    direction=(rays@pose[:3,:3].T+origin)-origin
    d=depth[valid];trunc=np.float32(.002)*np.float32(8)
    t=np.maximum(d-trunc,np.float32(0));upper=np.minimum(d+trunc,np.float32(8))
    step=(upper-t)/np.float32(3);blocks=[]
    for _ in range(4):
        blocks.append(np.floor((origin+direction*t[:,None])/(np.float32(.002)*np.float32(16))).astype(np.int32))
        t=t+step
    coords=o3d.core.Tensor(np.unique(np.concatenate(blocks),axis=0),dtype=o3d.core.int32)
    return coords,dict(info,mode='SPARSE_VALID_DEPTH_STRIDE1_FALLBACK',blocks=int(coords.shape[0]))
