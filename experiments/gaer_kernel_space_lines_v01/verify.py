"""Independent delivery audit: source rows, serialized geometry, cameras and all media."""
import hashlib,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from plyfile import PlyData
import trimesh
import runtime as rt
from core import parse_glb,project

def read_obj(path):
    v=[];f=[];lines=[]
    for row in path.read_text().splitlines():
        a=row.split()
        if not a:continue
        if a[0]=='v':v.append([float(x) for x in a[1:]])
        if a[0]=='f':f.append([int(x.split('/')[0])-1 for x in a[1:]])
        if a[0]=='l':lines.append([int(x)-1 for x in a[1:]])
    return np.asarray(v).reshape(-1,3),np.asarray(f,dtype=np.int64).reshape(-1,3),np.asarray(lines,dtype=np.int64).reshape(-1,2)

def main():
    rt.guard('independent_audit_start')
    freeze=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());protocol=json.loads((rt.ART/'PROTOCOL.json').read_text());algorithm=json.loads((rt.ART/'ALGORITHM_FREEZE.json').read_text())
    assert rt.sha(rt.EXP/'core.py')==algorithm['core_sha256']
    assert rt.sha(rt.ART/'INPUT_FREEZE.json')==algorithm['input_freeze_sha256']
    assert rt.sha(rt.ART/'PROTOCOL.json')==algorithm['protocol_sha256']
    assert rt.sha(rt.ART/'PROTOCOL_ZH.md')==protocol['protocol_zh_sha256']
    mismatches=[p for p,h in freeze['protected_before'].items() if rt.sha(p)!=h];assert not mismatches,mismatches
    audits={}
    for scene,rec in freeze['scenes'].items():
        rt.guard(scene+'_independent_audit')
        v=PlyData.read(rec['model'])['vertex'];model=np.stack([v[x] for x in ['x','y','z']],axis=1)
        original=np.load(rt.ROOT/rec['selected_npz']);ids=original['original_ids'];xyz=original['xyz'];mask=original['source_view_mask']
        np.testing.assert_array_equal(xyz,model[ids]);assert len(model)==rec['model_count']
        selected=[]
        for src in rec['sources']:
            z=np.load(rt.ROOT/src['preserved_copy'],allow_pickle=False)
            assert rt.sha(rt.ROOT/src['preserved_copy'])==src['sha256']
            assert len(z['automatic_accepted_ids'])==0
            selected.append(z['gaer_ratio_0.005_ids'])
        np.testing.assert_array_equal(ids,np.unique(np.concatenate(selected)))
        np.testing.assert_array_equal(mask,np.isin(ids,selected[0]).astype(np.uint8)+2*np.isin(ids,selected[1]).astype(np.uint8))
        asset=rt.ART/'assets'/scene;g=np.load(asset/'FULL_GRAPH.npz')
        np.testing.assert_array_equal(g['xyz'],xyz);np.testing.assert_array_equal(g['ids'],ids)
        for name in ['selected-kernel-centers.ply','PCA-field.ply']:
            p=PlyData.read(str(asset/name))['vertex'];np.testing.assert_array_equal(p['original_id'],ids)
            np.testing.assert_array_equal(np.stack([p[x] for x in ['x','y','z']],axis=1),model[ids])
        arms={}
        for arm in ['A','B']:
            dst=asset/arm;edges=g[arm];ep=np.load(dst/'EDGE_PAIRS.npz')
            np.testing.assert_array_equal(ep['original_id_pairs'],ids[edges]);np.testing.assert_array_equal(ep['endpoints_xyz'],model[ids[edges]])
            np.testing.assert_array_equal(ep['original_ids'],ids)
            j=json.loads((dst/'EDGE_PAIRS.json').read_text())
            np.testing.assert_array_equal(np.asarray(j['original_id_pairs']).reshape(-1,2),ids[edges])
            np.testing.assert_array_equal(np.asarray(j['endpoints_xyz']).reshape(-1,2,3),model[ids[edges]])
            distance=np.linalg.norm(xyz[edges[:,0]].astype(float)-xyz[edges[:,1]],axis=1)
            assert np.all(distance>float(g['eps']))
            scale_limit=3*np.minimum(g['local_scale'][edges[:,0]],g['local_scale'][edges[:,1]])
            assert np.all(distance<=scale_limit)
            degree=np.bincount(edges.ravel(),minlength=len(ids))
            if arm=='B':
                assert degree.max()<=2
                assert np.all(g['linearity'][edges]>=.45)
                unit=(xyz[edges[:,1]].astype(float)-xyz[edges[:,0]])/distance[:,None]
                for end in [0,1]:assert np.all(np.abs(np.einsum('ij,ij->i',g['tangent'][edges[:,end]],unit))>=np.cos(np.pi/4))
                for a,b in edges:
                    assert a in g['neighbors'][b] and b in g['neighbors'][a]
            vertices,faces,doc=parse_glb((dst/'candidate_graph.glb').read_bytes())
            assert 'animations' not in doc
            assert all(not any(k in n for k in ['matrix','translation','rotation','scale']) for n in doc['nodes'])
            ov,of,ol=read_obj(dst/'tube.obj')
            np.testing.assert_array_equal(ov.astype(np.float32),vertices);np.testing.assert_array_equal(of,faces);assert not len(ol)
            lv,lf,ll=read_obj(dst/'centerline.obj')
            np.testing.assert_array_equal(lv.astype(np.float32),model[ids]);np.testing.assert_array_equal(ll,edges);assert not len(lf)
            centroid_error=0.;radius_error=0.
            if len(edges):
                rings=vertices.reshape(-1,2,8,3).astype(float);centers=rings.mean(2)
                centroid_error=float(np.max(np.abs(centers-xyz[edges])))
                radius_error=float(np.max(np.abs(np.linalg.norm(rings-xyz[edges][:,:,None,:],axis=3)-float(g['radius']))))
                assert centroid_error<2e-7 and radius_error<2e-7
                loaded=trimesh.load(dst/'candidate_graph.glb',force='scene',process=False)
                mesh=next(iter(loaded.geometry.values()));np.testing.assert_array_equal(np.asarray(mesh.vertices,dtype=np.float32),vertices);np.testing.assert_array_equal(mesh.faces,faces)
                assert mesh.is_watertight
                assert faces.min()>=0 and faces.max()<len(vertices) and np.isfinite(vertices).all()
            s=json.loads((dst/'GRAPH_STATS.json').read_text())
            assert len(edges)==s['edges'] and int((degree==0).sum())==s['isolated_count']
            assert s['geometry_sha256']==hashlib.sha256(xyz.tobytes()+edges.tobytes()+np.float64(g['radius']).tobytes()).hexdigest()
            assert rt.sha(dst/'candidate_graph.glb')==s['glb_sha256']
            arms[arm]=dict(edges=len(edges),max_degree=int(degree.max()),exact_original_id_endpoints=True,GLB_accessor_readback=True,independent_trimesh_readback=True,
                OBJ_readback=True,static_no_animation_or_node_transform=True,closed_tubes=True,tube_end_ring_centroid_max_error=centroid_error,tube_world_radius_max_error=radius_error)
        camera_errors=[]
        for c in rec['cameras']:
            metadata=json.loads(Path(c['metadata_path']).read_text());frame=metadata['frames'][c['metadata_index']]
            assert frame['file_path']==c['frame_file']
            m=np.asarray(frame['transform_matrix']).copy();m[:3,1:3]*=-1
            error=float(np.max(np.abs(np.linalg.inv(m)-c['w2c'])));assert error<=1e-10
            # Independent homogeneous K/w2c projection, native centered pixel convention.
            q=np.column_stack([xyz,np.ones(len(xyz))])@np.asarray(c['w2c']).T
            K=np.array([[800/(2*np.tan(c['FoVx']/2)),0,399.5],[0,800/(2*np.tan(c['FoVy']/2)),399.5],[0,0,1]])
            h=q[:,:3]@K.T;expected=h[:,:2]/h[:,2,None];uv,z=project(xyz,c)
            pe=float(np.max(np.abs(expected-uv)));assert pe<1e-9
            bg=rec['backgrounds'][c['key']];assert rt.sha(rt.ART/'media'/scene/c['key']/'original_RGB_SH3.png')==bg['sha256']
            camera_errors.append(dict(view=c['key'],metadata_w2c_error=error,independent_projection_error_px=pe,unwarped_source_RGB_exact=True))
        arc=rt.ART/'media'/scene/'arc';manifest=json.loads((arc/'FRAME_MANIFEST.json').read_text());proj=np.load(arc/'ALL_CAMERA_PROJECTIONS.npz')
        np.testing.assert_array_equal(proj['xyz'],model[ids]);np.testing.assert_array_equal(proj['original_ids'],ids)
        assert len(manifest['frames'])==33 and len(set(a['matrix_sha256'] for a in manifest['frames']))==33
        for i,(item,record) in enumerate(zip(rec['arc'],manifest['frames'])):
            camera=item['camera'];source_result=json.loads(Path(item['source_result']).read_text())
            assert source_result['camera']['camera_sha256']==camera['camera_sha256']
            np.testing.assert_array_equal(source_result['camera']['w2c'],camera['w2c'])
            np.testing.assert_array_equal(proj['w2c'][i],camera['w2c'])
            q=np.column_stack([xyz,np.ones(len(xyz))])@np.asarray(camera['w2c']).T;h=q[:,:3]@np.asarray(camera['K']).T;uv=h[:,:2]/h[:,2,None]
            assert np.max(np.abs(uv-proj['uv'][i]))<1e-9
            for arm in ['A','B']:
                s=json.loads((asset/arm/'GRAPH_STATS.json').read_text());assert record[arm+'_geometry_sha256']==s['geometry_sha256']
            assert record['no_reselection'] and record['no_deformation'] and record['fixed_vertex_count']==len(ids)
            assert rt.sha(arc/'frames'/f'{i:03d}.png')==record['frame_sha256']
        video=manifest['video'];assert video['decoded_frames']==33 and video['decoded_unique_frames']==33 and video['full_decode'] and video['faststart']
        assert rt.sha(rt.ROOT/video['path'])==video['sha256']
        audits[scene]=dict(selected_nodes=len(ids),model_rows=len(model),source_budget_ids_only=True,automatic_selector_status='REFUSED',exact_original_rows=True,
            source_view_provenance=True,arms=arms,fixed_camera_checks=camera_errors,arc_actual_distinct_cameras=33,video_full_decode_pass=True,graph_constant_all_frames=True)
    mismatches=[p for p,h in freeze['protected_before'].items() if rt.sha(p)!=h];assert not mismatches
    rt.write_json(rt.ART/'VERIFICATION.json',dict(status='PASS',utc=rt.utc(),independent_process=True,scenes=audits,protected_input_count=len(freeze['protected_before']),protected_mismatches=mismatches,
        scientific_certification=False,checks_do_not_feedback_geometry=True))
    rt.guard('independent_audit_complete')
    print(json.dumps(dict(status='PASS',scenes=list(audits),protected_files=len(freeze['protected_before']))),flush=True)
if __name__=='__main__':main()
