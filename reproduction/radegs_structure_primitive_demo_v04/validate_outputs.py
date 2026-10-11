from common import *
import ast,subprocess
def main():
    guard();source=json.loads((T/'SOURCE_FREEZE.json').read_text());checked=0
    for r in source['files']:
        assert sha(Path(r['path']))==r['sha256'],r['path'];checked+=1
    units=[]
    for d in sorted((T/'results').iterdir()):
        if not (d/'SEAL.json').exists():continue
        for r in json.loads((d/'SEAL.json').read_text())['files']:assert sha(d/r['path'])==r['sha256'],str(d/r['path'])
        g=dict(np.load(d/'optimized_primitives.npz'));a=dict(np.load(d/'optimized_gaussians.npz'));meta=json.loads((d/'optimized_graph.json').read_text());s=json.loads((d/'RESULTS.json').read_text())
        np.testing.assert_array_equal(g['control'],g['points'][g['node_index']]);assert np.isfinite(a['means']).all();assert (np.linalg.eigvalsh(a['covariance'])>0).all();assert len(a['means'])==s['derived_gaussians'];assert len(g['control'])==s['primitives'];assert (a['primitive_id']>=0).all() and a['primitive_id'].max()<s['primitives'];assert ((a['arc_t']>=0)&(a['arc_t']<=1)).all()
        assert all(set(p['source_views'])<=set(BUILD) for p in meta['primitives'])
        units.append({'unit':d.name,'primitives':s['primitives'],'gaussians':s['derived_gaussians'],'source_observations':s['all_observations'],'assigned_observations':s['assigned_observations'],'model_seal_verified':True,'fixed_parameter_reload_render_verified_by_unit':s['reload_render_bitexact']})
    videos=[]
    for p in sorted((T/'media_corrected').glob('*/VALIDATION.json')) if (T/'media_corrected').exists() else []:
        a=json.loads(p.read_text());assert a['decoded_frames']==33 and a['rendered_frames']==33 and a['pixel_format']=='yuv420p';videos.append({'scene':p.parent.name,**a})
        for r in json.loads((p.parent/'SEAL.json').read_text())['files']:assert sha(p.parent/r['path'])==r['sha256']
    auxiliary_seals=[]
    for d in [T/'synthetic',T/'roi_fair_comparison']+list((T/'provenance_refined').iterdir()):
        for r in json.loads((d/'SEAL.json').read_text())['files']:assert sha(d/r['path'])==r['sha256'],str(d/r['path'])
        auxiliary_seals.append(str(d.relative_to(T)))
    files=list(W.glob('*.py'));diff=[]
    for p in files:
        ast.parse(p.read_text());r=subprocess.run(['git','diff','--no-index','--check','/dev/null',str(p)],capture_output=True,text=True);assert r.returncode in (0,1) and not r.stdout and not r.stderr,(str(p),r.stdout,r.stderr);diff.append(p.name)
    js(T/'VALIDATION.json',{'source_hashes_rechecked':checked,'units':units,'unit_count':len(units),'full_scene_count':sum(u['unit'].endswith('_full') for u in units),'videos':videos,'auxiliary_seals_rechecked':auxiliary_seals,'code_AST_and_whitespace_checked':diff,'storage_bytes':sum(p.stat().st_size for p in T.rglob('*') if p.is_file()),'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(T).free,'valid_holdout_creation_exclusion':True})
    print('VALIDATION',len(units),'units',len(videos),'videos',checked,'sources')
if __name__=='__main__':main()
