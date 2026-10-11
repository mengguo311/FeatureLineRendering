"""Report the native default-threshold extraction result, including emptiness."""
import open3d as o3d


def extract_mesh(vbg):
    try:
        mesh=vbg.extract_triangle_mesh().to_legacy()
    except RuntimeError as exc:
        message=str(exc)
        # v0.18.0 VoxelBlockGrid.cpp:469-474 calls SetVertexColors only if
        # colors.GetLength()==vertices.GetLength(). colors shape {0} proves
        # vertices length 0 here. Preserve the negative geometry outcome.
        if (o3d.__version__=='0.18.0' and 'TriangleMesh::SetVertexColors' in message
            and 'Tensor has shape {0}' in message and '{None, 3}' in message):
            return o3d.geometry.TriangleMesh(),{'empty':True,'weight_threshold':3.,
                'native_error':message,'status':'NEGATIVE_GEOMETRY_EMPTY_NATIVE_SURFACE'}
        raise
    return mesh,{'empty':len(mesh.vertices)==0,'native_error':None,'weight_threshold':3.}
