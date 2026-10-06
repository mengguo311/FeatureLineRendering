"""File seal before commit; actual remote/clean receipt after explicit SSH push."""
import json,os,subprocess,sys
from pathlib import Path
import runtime as rt

TESTS=[dict(command='bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/test_contracts.py',result='PASS 7/7 after RED 7 NotImplementedError',evidence='artifacts/gaer_kernel_space_lines_v01/TDD_GREEN.log'),
       dict(command='bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/verify.py',result='PASS: both scenes; 159 protected files unchanged',evidence='artifacts/gaer_kernel_space_lines_v01/VERIFICATION.json'),
       dict(command='bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/replay.py',result='PASS: all graph arrays exact and 4 GLBs byte exact',evidence='artifacts/gaer_kernel_space_lines_v01/REPLAY_VERIFICATION.json')]

def verify_manifest():
    manifest=json.loads((rt.ART/'MANIFEST.json').read_text())
    changed=[r['path'] for r in manifest['files'] if rt.sha(rt.ROOT/r['path'])!=r['sha256']]
    assert not changed,changed
    return manifest

def seal():
    rt.guard('final_precommit_seal')
    assert json.loads((rt.ART/'VERIFICATION.json').read_text())['status']=='PASS'
    assert json.loads((rt.ART/'REPLAY_VERIFICATION.json').read_text())['status']=='PASS'
    assert 'Ran 7 tests' in (rt.ART/'TDD_GREEN.log').read_text() and (rt.ART/'TDD_GREEN.log').read_text().rstrip().endswith('OK')
    assert 'FAILED (errors=7)' in (rt.ART/'TDD_RED.log').read_text()
    rt.write_json(rt.ART/'TEST_RESULTS.json',dict(tests=TESTS,RED=dict(exit_code=1,errors=7),GREEN=dict(exit_code=0,passed=7),
        intermediate_negative_logs=['TDD_INTERMEDIATE_FLOAT_ASSERT.log','PREPARE_ATTEMPT1_METADATA_KEY.log'],real_scene_audit='PASS',deterministic_replay='PASS'))
    paths=[p for base in [rt.ART,rt.EXP] for p in base.rglob('*') if p.is_file() and p.name not in ['MANIFEST.json','DELIVERY.json']]
    paths.append(rt.OUT/'.gitignore')
    records=[dict(path=rt.rel(p),bytes=p.stat().st_size,sha256=rt.sha(p)) for p in sorted(paths)]
    rt.write_json(rt.ART/'MANIFEST.json',dict(utc=rt.utc(),files=records,file_count=len(records),total_bytes=sum(r['bytes'] for r in records),
        excludes=['MANIFEST.json (self hash)','DELIVERY.json (post-push receipt)','out caches/logs/replay binaries'],
        scientific_verdict='NO_GO_FRAGMENTED / PHYSICAL_EDGES_UNCERTIFIED',engineering_verdict='PASS'))
    verify_manifest()
    print(json.dumps(dict(status='SEALED',files=len(records),bytes=sum(r['bytes'] for r in records))))

def receipt():
    manifest=verify_manifest()
    resource=rt.guard('final_receipt',record=False)
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=rt.ROOT,text=True).strip()
    assert branch=='gaer-kernel-space-lines-v01'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=rt.ROOT,text=True).strip()
    ssh='git@github.com:mengguo311/FeatureLineRendering.git'
    env=os.environ.copy();env['GIT_SSH_COMMAND']='ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=20'
    remote=subprocess.check_output(['git','ls-remote',ssh,'refs/heads/'+branch],cwd=rt.ROOT,env=env,text=True).strip()
    remote_sha=remote.split()[0];assert remote_sha==head
    changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',head],cwd=rt.ROOT,text=True).splitlines()
    assert changed and all(any(p.startswith(prefix) for prefix in ['experiments/'+rt.STAGE+'/','artifacts/'+rt.STAGE+'/','out/'+rt.STAGE+'/']) for p in changed)
    status=subprocess.check_output(['git','status','--porcelain'],cwd=rt.ROOT,text=True);assert not status,status
    results=json.loads((rt.ART/'RESULTS.json').read_text());media=json.loads((rt.ART/'MEDIA_AUDIT.json').read_text())
    assets={}
    for scene in ['lego','chair']:
        base=Path('artifacts')/rt.STAGE/'assets'/scene
        assets[scene]=dict(selected_centers_ply=str(base/'selected-kernel-centers.ply'),PCA_field_ply=str(base/'PCA-field.ply'),full_graph_npz=str(base/'FULL_GRAPH.npz'),provenance_json=str(base/'PROVENANCE.json'),
            arms={arm:dict(glb=str(base/arm/'candidate_graph.glb'),tube_obj=str(base/arm/'tube.obj'),centerline_obj=str(base/arm/'centerline.obj'),edge_pairs_json=str(base/arm/'EDGE_PAIRS.json'),edge_pairs_npz=str(base/arm/'EDGE_PAIRS.npz'),
                edges=results[scene]['arms'][arm]['edges'],isolated=results[scene]['arms'][arm]['isolated_count']) for arm in ['A','B']})
    delivery=dict(utc=rt.utc(),final_commit=head,remote_sha=remote_sha,branch=branch,push_transport='explicit SSH',remote=ssh,
        clean_status=True,status_porcelain=status,commit_paths_all_within_new_stage=True,committed_file_count=len(changed),manifest_sha256=rt.sha(rt.ART/'MANIFEST.json'),manifest_file_count=manifest['file_count'],
        engineering_verdict='PASS',scientific_verdict='NO_GO_FRAGMENTED / PHYSICAL_EDGES_UNCERTIFIED',old_selector_status='REFUSED (unchanged)',original_kernel_xyz_exact=True,
        assets=assets,media={scene:dict(video=media['scenes'][scene]['video']['path'],full_decoded_frames=33,distinct_actual_cameras=33,four_camera_png=f'artifacts/{rt.STAGE}/media/{scene}/four_camera_inspection_preview.png',
            all_frames_png=f'artifacts/{rt.STAGE}/media/{scene}/arc/ALL_33_FRAMES.png',true_3d_graph_pca_png=f'artifacts/{rt.STAGE}/media/{scene}/true_3d_graph_PCA.png') for scene in ['lego','chair']},
        viewer_3d=f'artifacts/{rt.STAGE}/media/viewer_3d.html',report_zh=f'artifacts/{rt.STAGE}/REPORT_ZH.md',reproduce=f'artifacts/{rt.STAGE}/REPRODUCE.md',tests=TESTS,
        missing_required_assets=[],limitations=['no certified physical edge/contact semantics','fragmented graphs and potential cross-surface connections','2px x-ray centerline presentation; no native tube mesh render or hidden-line verification','all cameras previously GS/research exposed'],
        resource=resource,receipt_tracking='ignored post-push receipt to avoid self-referential commit SHA; assets/media/docs/tests fully committed')
    rt.write_json(rt.ART/'DELIVERY.json',delivery)
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=rt.ROOT,text=True)
    rt.write_json(rt.OUT/'GIT_DELIVERY.json',delivery)
    print(json.dumps(dict(status='DELIVERED',final_commit=head,remote_sha=remote_sha,clean=True,receipt=rt.rel(rt.ART/'DELIVERY.json'))))

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='receipt':receipt()
    else:seal()
