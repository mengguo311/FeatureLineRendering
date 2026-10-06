import ast,json,shutil,subprocess
from pathlib import Path
import numpy as np
from plyfile import PlyData
import runtime as rt
from core import PARAMETERS,REASONS,selected_rows

def main():
    rt.guard('input_freeze_before_real_graph')
    old=Path('/home/u00134/3dgs_line/gaer_object_contours_v01/artifacts/gaer_object_contours_v01')
    sources=Path('/home/u00134/3dgs_line/gaer_view_selection_v01/artifacts/gaer_view_selection_v01/downloads')
    commit=subprocess.check_output(['git','-C',str(sources.parents[2]),'rev-parse','HEAD'],text=True).strip()
    assert commit=='e682614a7fedcb529102f67efcf78f7905d3d519'
    camera_file=old/'INPUT_FREEZE.json';camera=json.loads(camera_file.read_text())
    shutil.copyfile(camera_file,rt.scoped(rt.ART/'CAMERA_SOURCE.json'))
    protocol=dict(utc=rt.utc(),frozen_before_real_graph=True,parameters=PARAMETERS,reasons=REASONS,protocol_zh_sha256=rt.sha(rt.ART/'PROTOCOL_ZH.md'),covariance_used=False,
                  graph_inputs=['original selected xyz','original ids'],inspection_feedback=False,source_selection_key='gaer_ratio_0.005_ids')
    rt.write_json(rt.ART/'PROTOCOL.json',protocol)
    protected={str(camera_file):rt.sha(camera_file)}
    scenes={}
    for name,rec in camera['scenes'].items():
        assert name in ['lego','chair']
        model=Path(rec['model']);assert rt.sha(model)==rec['model_sha256']
        protected[str(model)]=rt.sha(model)
        v=PlyData.read(str(model))['vertex'];xyz=np.stack([v[q] for q in ['x','y','z']],axis=1)
        assert len(xyz)==rec['count'] and xyz.dtype==np.float32
        ids_by_view=[];source_records=[]
        for view in ['r_7','r_33']:
            src=sources/f'{name}_{view}_scores_ids.npz';dst=rt.ART/'sources'/src.name
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,rt.scoped(dst))
            z=np.load(src,allow_pickle=False);ids=z['gaer_ratio_0.005_ids'];ids_by_view.append(ids)
            assert len(ids)==(1553 if name=='lego' else 1284)
            assert len(z['automatic_accepted_ids'])==0
            assert str(z['scene'])==name
            np.testing.assert_array_equal(z['original_ids'],np.arange(rec['count']))
            protected[str(src)]=rt.sha(src)
            source_records.append(dict(view=view,path=str(src),preserved_copy=rt.rel(dst),sha256=rt.sha(src),selected_count=len(ids),selected_original_ids=ids.tolist(),automatic_accepted_count=0,automatic_status='REFUSED'))
        ids,selected,mask=selected_rows(xyz,ids_by_view)
        dst=rt.ART/'inputs'/name;dst.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(rt.scoped(dst/'SELECTED_ORIGINAL.npz'),original_ids=ids,xyz=selected,source_view_mask=mask)
        rt.write_json(dst/'SELECTED_ORIGINAL_IDS.json',[dict(original_id=int(i),source_views=[v for v,b in [('r_7',1),('r_33',2)] if m&b]) for i,m in zip(ids,mask)])
        backgrounds={}
        for c in rec['cameras']:
            p=old/'media'/name/c['key']/'original_RGB_SH3.png'
            backgrounds[c['key']]=dict(path=str(p),sha256=rt.sha(p),camera_sha256=c['camera_sha256'],native_size=[800,800],source='prior original full SH3 native RGB; no geometric resampling')
            protected[str(p)]=rt.sha(p)
            for key,hash_key in [('metadata_path','metadata_sha256'),('original_image','original_image_sha256')]:
                q=c[key];assert rt.sha(q)==c[hash_key];protected[q]=rt.sha(q)
        arc=[]
        for j,c in enumerate(rec['arc']):
            p=old/'media'/name/'arc'/'original_RGB_SH3'/f'{j:03d}.png'
            result=old/'results'/f"{name}_arc_{c['key']}.json"
            r=json.loads(result.read_text());assert r['index']==j
            # The source result contains the exact camera actually used by native rendering.
            if 'camera' in r:assert r['camera']['w2c']==c['w2c']
            arc.append(dict(index=j,path=str(p),sha256=rt.sha(p),camera=c,source_result=str(result),source_result_sha256=rt.sha(result)))
            protected[str(p)]=rt.sha(p);protected[str(result)]=rt.sha(result)
        scenes[name]=dict(model=str(model),model_sha256=rt.sha(model),model_count=len(xyz),selected_count=len(ids),sources=source_records,
                          selected_npz=rt.rel(dst/'SELECTED_ORIGINAL.npz'),selected_npz_sha256=rt.sha(dst/'SELECTED_ORIGINAL.npz'),selected_original_ids=ids.tolist(),
                          selected_xyz_sha256=__import__('hashlib').sha256(selected.tobytes()).hexdigest(),source_view_mask=mask.tolist(),
                          cameras=rec['cameras'],inspection_only_views=['r_1','r_14'],backgrounds=backgrounds,arc=arc,formal_blind=False)
        print(name,'frozen original-ID union',len(ids),'source overlap',int((mask==3).sum()),flush=True)
    for p in [sources.parent/'REPORT_ZH.md',rt.ROOT/'experiments'/'gaer_fixed_contour_asset_v01'/'core.py']:
        protected[str(p)]=rt.sha(p)
    reuse=rt.ROOT/'experiments'/'gaer_fixed_contour_asset_v01'/'core.py'
    tree=ast.parse(reuse.read_text())
    rt.write_json(rt.ART/'REUSE_PROVENANCE.json',dict(path=str(reuse),sha256=rt.sha(reuse),functions={n.name:rt.digest(ast.dump(n)) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['tube_mesh','glb_bytes']},run_py_imported=False,legacy_runtime_imported=False))
    rt.write_json(rt.ART/'INPUT_FREEZE.json',dict(utc=rt.utc(),source_commit=commit,camera_source_path=str(camera_file),camera_source_sha256=rt.sha(camera_file),
                 protocol_sha256=rt.sha(rt.ART/'PROTOCOL.json'),scenes=scenes,protected_before=protected,all_views_prior_GS_research_exposed=True))
    rt.guard('input_freeze_complete')
if __name__=='__main__':main()
