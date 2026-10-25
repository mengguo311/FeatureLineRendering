"""Independent readback of immutable inputs, curve transport and saved images."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js
import json,collections
from pathlib import Path
import numpy as np
from PIL import Image

def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
    p=json.loads((UNIT/'PROTOCOL.json').read_text());assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    checked=0
    for name,h in json.loads((UNIT/'INPUT_LOCK.json').read_text())['files'].items():assert sha(name)==h,name;checked+=1
    for name,h in json.loads((UNIT/'BOOTSTRAP_INPUTS.json').read_text())['original_files'].items():assert sha(name)==h,name;checked+=1
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():
        assert sha(HERE/name)==h,name;assert sha(UNIT/'source_snapshot'/name)==h,name
    for name,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    target=npz(ROOT/'replay_package/data/lego/unit_008_asset/TARGET.npz');vertices=target['vertices'];faces=target['faces'];tri=vertices[faces]
    seed_records=json.loads((UNIT/'asset/SEEDS_AND_STOPS.json').read_text());transport_errors=[];seed_errors=[];max_anchor=0.;count=0
    direction={};topology={};edge_faces={};vertex_faces={}
    for i,face in enumerate(faces):
        for vertex in face:vertex_faces.setdefault(int(vertex),[]).append(i)
        for j in range(3):edge_faces.setdefault(tuple(sorted(int(face[k]) for k in range(3) if k!=j)),[]).append(i)
    for part in ('old','added'):
        a=npz(UNIT/'asset'/('A_'+part+'.npz'));b=npz(UNIT/'asset'/('B_'+part+'.npz'))
        allowed=target['old_face_regions']==4 if part=='old' else (target['face_regions']==4)&(target['old_face_regions']!=4)
        neighbors={int(i):[] for i in np.flatnonzero(allowed)}
        for incident in edge_faces.values():
            if len(incident)==2 and allowed[incident].all():
                i,j=incident;neighbors[i].append(j);neighbors[j].append(i)
        unseen=set(neighbors);sizes=[]
        while unseen:
            todo=[unseen.pop()];size=0
            while todo:
                i=todo.pop();size+=1
                for j in neighbors[i]:
                    if j in unseen:unseen.remove(j);todo.append(j)
            sizes.append(size)
        selected_vertices=set(int(v) for v in faces[allowed].ravel())
        interior_vertices=[v for v in selected_vertices if allowed[vertex_faces[v]].all()]
        topology[part]=dict(face_components=len(sizes),component_face_counts=sorted(sizes,reverse=True),
                            selected_vertices=len(selected_vertices),vertices_not_touching_partition_boundary=len(interior_vertices),
                            note='Topological diagnostic only; sharp-edge protection would further reduce movable vertices')
        for name,paths in [('A',a),('B',b)]:
            turns=[];lengths=np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1);same_face=0
            for sid in np.unique(paths['stroke_id']):
                ix=np.flatnonzero(paths['stroke_id']==sid);d=(paths['points'][ix,1]-paths['points'][ix,0])/lengths[ix,None]
                for j in range(len(ix)-1):
                    if paths['face'][ix[j]]==paths['face'][ix[j+1]]:same_face+=1;continue
                    turns.append(float(np.rad2deg(np.arccos(np.clip(d[j]@d[j+1],-1,1)))))
            direction[part+'_'+name]=dict(shared_edge_turn_count=len(turns),excluded_same_face_splits=same_face,
              turn_degrees_quantiles=np.quantile(turns,[.5,.9,.95,1]).tolist(),sum_turn_degrees=float(sum(turns)),
              turn_degrees_per_world_length=float(sum(turns)/lengths.sum()),
              scope='Only actual face transitions; no artificial zero-turn credit from splitting each stroke at its seed; shape and noise remain mixed')
        expected=np.einsum('nij,njk->nik',b['bary'],tri[b['face']]);max_anchor=max(max_anchor,float(np.abs(expected-b['points']).max()))
        for rec in (x for x in seed_records if x['partition']==part):
            ai=np.flatnonzero(a['stroke_id']==rec['parent_stroke_id']);bi=np.flatnonzero(b['stroke_id']==rec['stroke_id'])
            oldp=a['points'][ai];length=np.linalg.norm(oldp[:,1]-oldp[:,0],axis=1);arc=np.cumsum(length);half=arc[-1]/2
            j=min(int(np.searchsorted(arc,half,side='right')),len(ai)-1);start=arc[j-1] if j else 0.;fraction=(half-start)/length[j]
            seed=(1-fraction)*oldp[j,0]+fraction*oldp[j,1];seed_errors.append(float(np.linalg.norm(seed-rec['seed_point'])))
            np.testing.assert_allclose((oldp[j,1]-oldp[j,0])/length[j],rec['initial_tangent'],atol=1e-12)
            points=b['points'][bi];newlength=np.linalg.norm(points[:,1]-points[:,0],axis=1)
            assert abs(newlength.sum()-rec['actual_length'])<1e-9
            assert newlength.sum()<=length.sum()+1e-9
            assert np.min(np.linalg.norm(points.reshape(-1,3)-seed,axis=1))<1e-9
            assert (b['parent_stroke_id'][bi]==rec['parent_stroke_id']).all()
            np.testing.assert_allclose(points[:-1,1],points[1:,0],atol=1e-9)
            tangent=(points[:,1]-points[:,0])/newlength[:,None]
            for k in range(len(bi)-1):
                f0,f1=b['face'][bi[k:k+2]]
                if f0==f1:continue
                shared=sorted(set(map(int,faces[f0]))&set(map(int,faces[f1])))
                assert len(shared)==2
                edge=vertices[shared[1]]-vertices[shared[0]];edge/=np.linalg.norm(edge)
                transport_errors.append(abs(float((tangent[k]-tangent[k+1])@edge)))
            count+=1
    assert max_anchor<1e-10 and max(seed_errors)<1e-10 and max(transport_errors)<1e-7
    match=json.loads((UNIT/'BUILD_MATCH.json').read_text());views=json.loads((UNIT/'CAMERAS.json').read_text())['views'];compositor_error=0.;png_count=0
    for v in (v for v in views if v['kind']!='build'):
        folder=UNIT/v['kind']/v['camera']['view'];f=npz(folder/'FRAME.npz');ref=npz(v['cache'])
        for key in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[key],ref[key])
        np.testing.assert_array_equal(f['A_preS'],ref['local_ink']);np.testing.assert_array_equal(f['A_linked_natural'],ref['local_raw'])
        metrics=json.loads((folder/'EVALUATION.json').read_text())['measurements'];mask=f['regions']==4
        for arm in ('A_linked','B_linked','A_ungated','B_ungated'):
            for mode in ('natural','matched'):
                key=arm+'_'+mode;alpha=f[arm[0]+'_preS'].copy()
                if arm.split('_')[1]=='linked':alpha=alpha*f['support']
                if mode=='matched':alpha=alpha*match['scales'][arm]
                im=f['paper']*(1-alpha[...,None])+.03*alpha[...,None]
                error=float(np.abs(im-f[key]).max());compositor_error=max(compositor_error,error);assert error<=2e-7
                measured=float(np.abs(f[key]-f['paper'])[mask].sum())
                assert abs(measured-metrics['ink_effect'][key]['target_full']['raw_L1_sum'])<1e-3
                expected=np.uint8(np.clip(f[key],0,1)*255+.5)
                np.testing.assert_array_equal(np.asarray(Image.open(folder/(key+'.png'))),expected);png_count+=1
        zero=np.zeros_like(f['support']);np.testing.assert_array_equal(f['paper']*(1-zero[...,None])+.03*zero[...,None],f['paper'])
    ends=json.loads((UNIT/'asset/A_ENDPOINTS.json').read_text())
    endpoint_counts=dict(collections.Counter(rec[k] for records in ends.values() for rec in records for k in ('start_class','end_class')))
    js(UNIT/'DIRECTION_TOPOLOGY_READBACK.json',dict(direction=direction,topology=topology,A_endpoint_counts=endpoint_counts))
    receipt=dict(status='pass',input_files_checked=checked,original_files_preserved=True,source_snapshot_preserved=True,stroke_count=count,
      max_anchor_error=max_anchor,max_seed_error=max(seed_errors),max_edge_tangent_component_error=max(transport_errors),
      max_saved_compositor_error=compositor_error,pngs_decoded_and_checked=png_count,all_A_renders_exact=True,
      original_ID_scope='Unchanged full original-row arrays and region S; no new per-path Gaussian certification',audit_source_sha256=sha(__file__))
    js(UNIT/'AUDIT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
