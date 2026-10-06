import json,hashlib
from collections import Counter
import numpy as np
from plyfile import PlyData,PlyElement
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import runtime as rt
from core import build_graph,mesh_and_glb,parse_glb,PARAMETERS,REASONS

def stats(xyz,edges,ids):
    n=len(xyz);degree=np.bincount(edges.ravel(),minlength=n)
    a,b=edges.T if len(edges) else (np.array([],int),np.array([],int))
    adj=coo_matrix((np.ones(2*len(edges)),(np.r_[a,b],np.r_[b,a])),shape=(n,n)).tocsr()
    count,labels=connected_components(adj,directed=False)
    sizes=np.bincount(labels);length=np.linalg.norm(xyz[a].astype(float)-xyz[b],axis=1)
    return dict(nodes=n,edges=len(edges),max_degree=int(degree.max()),degree_histogram={str(k):int(v) for k,v in sorted(Counter(degree.tolist()).items())},
        isolated_count=int((degree==0).sum()),isolated_original_ids=ids[degree==0].tolist(),components=int(count),
        component_sizes_descending=sorted(sizes.tolist(),reverse=True),component_size_histogram={str(k):int(v) for k,v in sorted(Counter(sizes.tolist()).items())},
        component_original_ids=[ids[labels==i].tolist() for i in range(count)],
        length_quantiles_world={str(q):float(np.percentile(length,q)) for q in [0,25,50,75,95,100]} if len(length) else {},
        total_length_world=float(length.sum()),degree=degree.tolist())

def write_ply(dst,ids,xyz,mask,g):
    dtype=[('x','<f4'),('y','<f4'),('z','<f4'),('original_id','<u4'),('source_view_mask','u1'),('red','u1'),('green','u1'),('blue','u1')]
    a=np.empty(len(ids),dtype=dtype)
    for j,key in enumerate(['x','y','z']):a[key]=xyz[:,j]
    a['original_id']=ids;a['source_view_mask']=mask
    color=np.array([[0,0,0],[230,110,25],[25,110,230],[150,40,170]],np.uint8)[mask]
    for j,key in enumerate(['red','green','blue']):a[key]=color[:,j]
    PlyData([PlyElement.describe(a,'vertex')],text=False,comments=['Exact original Gaussian centers; RGB encodes r_7 orange/r_33 blue/both purple.']).write(str(rt.scoped(dst/'selected-kernel-centers.ply')))
    field=np.empty(len(ids),dtype=dtype+[('tx','<f8'),('ty','<f8'),('tz','<f8'),('lambda1','<f8'),('lambda2','<f8'),('lambda3','<f8'),('linearity','<f8'),('local_scale','<f8')])
    for key in a.dtype.names:field[key]=a[key]
    for j,key in enumerate(['tx','ty','tz']):field[key]=g['tangent'][:,j]
    for j,key in enumerate(['lambda1','lambda2','lambda3']):field[key]=g['eigenvalues'][:,j]
    field['linearity']=g['linearity'];field['local_scale']=g['local_scale']
    PlyData([PlyElement.describe(field,'vertex')],text=False,comments=['PCA tangent is an unoriented point-distribution axis, NOT a surface normal.']).write(str(rt.scoped(dst/'PCA-field.ply')))
    obj=['# PCA glyphs only; endpoints are visualization of direction, not graph nodes.']
    for i,(p,t,s) in enumerate(zip(xyz,g['tangent'],g['local_scale'])):
        obj+=['v %.17g %.17g %.17g'%tuple(q) for q in [p-.5*s*t,p+.5*s*t]]
        obj.append(f'l {2*i+1} {2*i+2}')
    rt.scoped(dst/'PCA-direction-glyphs.obj').write_text('\n'.join(obj)+'\n')

def main():
    rt.guard('graph_build_start')
    freeze=json.loads((rt.ART/'INPUT_FREEZE.json').read_text())
    protocol=json.loads((rt.ART/'PROTOCOL.json').read_text());assert protocol['parameters']==PARAMETERS
    rt.write_json(rt.ART/'ALGORITHM_FREEZE.json',dict(utc=rt.utc(),frozen_before_real_graph=True,core_sha256=rt.sha(rt.EXP/'core.py'),build_sha256=rt.sha(__file__),
        protocol_sha256=rt.sha(rt.ART/'PROTOCOL.json'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),tdd_green_sha256=rt.sha(rt.ART/'TDD_GREEN.log')))
    results={}
    for name,rec in freeze['scenes'].items():
        rt.guard(name+'_build')
        z=np.load(rt.ROOT/rec['selected_npz']);xyz=z['xyz'];ids=z['original_ids'];mask=z['source_view_mask']
        g=build_graph(xyz,ids);dst=rt.ART/'assets'/name;dst.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(rt.scoped(dst/'FULL_GRAPH.npz'),**{k:v for k,v in g.items() if isinstance(v,(np.ndarray,float))},source_view_mask=mask)
        write_ply(dst,ids,xyz,mask,g)
        rt.write_json(dst/'CANDIDATE_REASON_LEGEND.json',dict(bitmask=REASONS,accepted='reason==0',all_candidate_adjacency='FULL_GRAPH.npz / candidate_pairs and original_ids; CANDIDATE_ADJACENCY.json',rank='0-based; -1 means not a directed kNN neighbor'))
        candidate=dict(original_id_pairs=ids[g['candidate_pairs']].tolist(),node_index_pairs=g['candidate_pairs'].tolist(),distance=g['distance'].tolist(),distance_limit=g['distance_limit'].tolist(),
            endpoint_alignment=g['alignment'].tolist(),endpoint_knn_rank=g['endpoint_knn_rank'].tolist(),reason_A=g['reason_A'].tolist(),reason_B=g['reason_B'].tolist(),reason_legend=REASONS)
        rt.scoped(dst/'CANDIDATE_ADJACENCY.json').write_text(json.dumps(candidate,separators=(',',':'))+'\n')
        arms={}
        for arm in ['A','B']:
            edges=g[arm];out=dst/arm;out.mkdir(exist_ok=True)
            vertices,faces,glb=mesh_and_glb(xyz,edges,g['radius']);rt.scoped(out/'candidate_graph.glb').write_bytes(glb)
            parsed_v,parsed_f,doc=parse_glb(glb)
            np.testing.assert_array_equal(parsed_v,vertices);np.testing.assert_array_equal(parsed_f,faces)
            tube=['# Fixed world tube mesh; kernel-space candidate graph, physical edges NOT certified.']
            tube+=['v %.9g %.9g %.9g'%tuple(p) for p in vertices]
            tube+=['f %d %d %d'%tuple(f+1) for f in faces]
            rt.scoped(out/'tube.obj').write_text('\n'.join(tube)+'\n')
            lines=['# Fixed original-ID centerlines. XYZ exactly original float32 model rows.']
            lines+=['# original_id %d\nv %.17g %.17g %.17g'%(int(i),*p) for i,p in zip(ids,xyz)]
            lines+=['l %d %d'%tuple(e+1) for e in edges]
            rt.scoped(out/'centerline.obj').write_text('\n'.join(lines)+'\n')
            ep=dict(scene=name,arm=arm,label='kernel-space candidate graph',physical_edges_certified=False,
                original_id_pairs=ids[edges].tolist(),node_index_pairs=edges.tolist(),endpoints_xyz=xyz[edges].tolist(),original_ids=ids.tolist(),
                model_sha256=rec['model_sha256'],selected_xyz_sha256=rec['selected_xyz_sha256'],tube_radius_world=g['radius'],camera_independent=True)
            rt.scoped(out/'EDGE_PAIRS.json').write_text(json.dumps(ep,separators=(',',':'))+'\n')
            np.savez_compressed(rt.scoped(out/'EDGE_PAIRS.npz'),original_id_pairs=ids[edges],node_index_pairs=edges,endpoints_xyz=xyz[edges],original_ids=ids,tube_radius_world=np.array(g['radius']))
            summary=stats(xyz,edges,ids)
            summary.update(tube_radius_world=g['radius'],mesh_vertices=len(vertices),mesh_triangles=len(faces),glb_sha256=rt.sha(out/'candidate_graph.glb'),
                geometry_sha256=hashlib.sha256(xyz.tobytes()+edges.tobytes()+np.float64(g['radius']).tobytes()).hexdigest(),empty_result=not len(edges))
            rt.write_json(out/'GRAPH_STATS.json',summary);arms[arm]=summary
        rt.write_json(dst/'PROVENANCE.json',dict(scene=name,source_commit=freeze['source_commit'],source_selection_key='gaer_ratio_0.005_ids',sources=rec['sources'],
            input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),algorithm_freeze_sha256=rt.sha(rt.ART/'ALGORITHM_FREEZE.json'),reuse_provenance_sha256=rt.sha(rt.ART/'REUSE_PROVENANCE.json'),
            original_xyz_exact=True,covariance_used=False,automatic_selector_status='REFUSED',accepted_kernel_count=0,graph_certified_as_physical_edges=False,tube_radius_world=g['radius']))
        results[name]=dict(selected_count=len(ids),source_overlap=int((mask==3).sum()),candidate_edges=len(g['candidate_pairs']),
            pca_linearity_pass_count=int((g['linearity']>=.45).sum()),scale_quantiles={str(q):float(np.percentile(g['local_scale'],q)) for q in [0,50,95,100]},arms=arms,
            rejection_counts={arm:{text:int(np.sum((g['reason_'+arm]&bit)>0)) for bit,text in REASONS.items()} for arm in ['A','B']})
        print(json.dumps(dict(scene=name,n=len(ids),candidates=len(g['candidate_pairs']),A=len(g['A']),B=len(g['B']),B_isolated=arms['B']['isolated_count'],B_components=arms['B']['components'],radius=g['radius'])),flush=True)
    rt.write_json(rt.ART/'RESULTS.json',results)
    rt.guard('both_scene_assets_complete')
if __name__=='__main__':main()
