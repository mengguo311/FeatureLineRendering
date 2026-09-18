#!/usr/bin/env python3
"""Execute final administrative checks; never change scientific eligibility."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.multiscene_training import sha256,utc
from src.multiscene_verify import inventory,verify_inventory,verify_png
from src.multiscene_report import check_report
from src.multiscene import seed_eligibility,independent_eligibility,controlled_eligibility

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',action='store_true')
parser.add_argument('--check-manifest',action='store_true')
args=parser.parse_args();root=ROOT/'out/multiscene_foundation'
exclude=['MANIFEST.json','MANIFEST.json.sha256']
def load(path):return json.loads(Path(path).read_text())
def git(*words,cwd=ROOT):return subprocess.check_output(['git',*words],cwd=cwd,text=True).strip()
def verify_record(row,path=None):
    p=Path(path or row['path'])
    assert p.stat().st_size==row['bytes'],str(p)
    assert sha256(p)==row['sha256'],str(p)

if args.check_manifest:
    m=load(root/'MANIFEST.json')
    assert sha256(root/'MANIFEST.json')==(root/'MANIFEST.json.sha256').read_text().strip()
    verify_inventory(root,m['files'],exclude)
    for record in m['external_dependencies']:verify_record(record)
    print('Manifest verified:',len(m['files']),'files',sum(r['bytes'] for r in m['files']),'bytes')
    sys.exit(0)
if args.manifest:
    assert load(root/'VERIFICATION.json')['passed']
    files=inventory(root,exclude)
    source=load(root/'setup/training_source.json')
    external=list(source['runtime']['binaries'])
    for p in [ROOT/'out/point_feature_foundation/setup/composite.so',
              ROOT/'out/vrss/vendor/official_site/diff_gaussian_rasterization/__init__.py']:
        external.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p)))
    method_sources=[ROOT/'src/foundation.py',ROOT/'src/common.py',
        *sorted((ROOT/'src').glob('multiscene*.*')),
        *sorted((ROOT/'scripts').glob('*multiscene*.py')),
        *sorted((ROOT/'tests').glob('test_multiscene*.py'))]
    for p in method_sources:
        external.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p)))
    external={r['path']:r for r in external if not Path(r['path']).is_relative_to(root)}
    tracked=set(git('ls-files').splitlines())
    for row in files:
        row['storage']='git' if str(Path(row['path']).relative_to(ROOT)) in tracked else 'server-side'
    freeze_json(root/'MANIFEST.json',dict(created_utc=utc(),root=str(root),files=files,
        file_count=len(files),total_bytes=sum(r['bytes'] for r in files),external_dependencies=list(external.values()),
        scope='All experiment files including ignored arrays/checkpoints/traces/staged inputs/build artifacts. Git object stores and transient __pycache__ directories are excluded. This manifest and its hash sidecar are excluded to avoid self-reference. Input hashes and source manifests retain original data/upstream provenance. Storage status is measured after staging final artifacts.'))
    print('Manifest written:',len(files),'files');sys.exit(0)

cfg=load(root/'config.json');inputs=load(root/'input_hashes.json')
assert sha256(root/'PREREG.md')==cfg['prereg_sha256']
assert sha256(root/'input_hashes.json')==cfg['input_hashes_sha256']
assert sha256(root/'config.json')=='199f5a65bd8d3cd2a82fc31fc92c03f6508f98be125845792e2e963c52617e6b'
assert git('branch','--show-current')=='multiscene-foundation'
assert git('rev-parse','ab40ec9^')==cfg['start_head']
assert subprocess.check_output(['git','show','ab40ec9:out/multiscene_foundation/config.json'])==(root/'config.json').read_bytes()
prereg_time=git('show','-s','--format=%cI','ab40ec9')
for row in inputs['files']+inputs['prior_reports']:verify_record(row)
dirty=Path('/home/u00134/3dgs_line/ext/gaussian-splatting');before=inputs['external_dirty_source']
assert git('rev-parse','HEAD',cwd=dirty)==before['head']
assert git('status','--porcelain',cwd=dirty)==before['status']
for row in before['files']:verify_record(row)
source=load(root/'setup/training_source.json');gs=root/'vendor/gaussian-splatting'
assert git('rev-parse','HEAD',cwd=gs)==cfg['training']['source_commit']
diff=subprocess.check_output(['git','diff','--binary'],cwd=gs)
assert hashlib.sha256(diff).hexdigest()==source['diff_sha256']
assert diff==(root/'setup/seed_injection.patch').read_bytes()
for name,row in source['files'].items():verify_record(row,gs/name)
for row in source['runtime']['binaries']:verify_record(row)
print('Frozen inputs, dirty source, isolated source and binaries verified',flush=True)

init=[];training=[];quality_count=controlled_count=pair_count=0
for scene in cfg['scene_order']:
    manifests=[];quality=[]
    for seed in cfg['training']['seeds']:
        d=root/'training'/scene/f'seed_{seed}';manifest=load(d/'manifest.json');manifests.append(manifest)
        for row in manifest['staged_data']['files']:verify_record(row,Path(manifest['data'])/row['path'])
        assert not set(cfg['splits']['DEV']+cfg['splits']['TEST']).intersection(cfg['training']['optimization_indices'])
        points=Path(manifest['data'])/'points3d.ply';init.append(dict(scene=scene,seed=seed,sha256=sha256(points)))
        complete=load(d/'completion.json');verify_record(complete)
        status=load(d/'exit_status.json');assert status['exit_code']==0 and complete['complete']
        assert datetime.fromisoformat(prereg_time)<datetime.fromisoformat(status['started_utc'])
        failed=load(d/'attempt_00_runtime_init/exit_status.json')
        assert datetime.fromisoformat(prereg_time)<datetime.fromisoformat(failed['started_utc'])
        assert '30000/30000' in (d/'train.log').read_text()
        resources=[json.loads(s) for s in (d/'resources.jsonl').read_text().splitlines()]
        assert resources[-1]['free_mib']>=cfg['training']['min_free_mib']
        training.append(dict(scene=scene,seed=seed,gpu=manifest['gpu'],**status))
        q=load(d/'quality/measurements/quality.json');quality.append(q)
        expected=seed_eligibility(q['rows'],cfg)
        expected['calibration_pass']=all(c['passed'] for c in q['calibration'])
        expected['passed']=expected['passed'] and expected['calibration_pass']
        assert q['eligibility']==expected
        quality_count+=len(q['rows'])
    assert manifests[0]['staged_data']==manifests[1]['staged_data']
    assert init[-1]['sha256']!=init[-2]['sha256']
    pair=load(root/'scenes'/scene/'independent_relation.json');pair_count+=len(pair['rows'])
    assert pair['eligibility']==independent_eligibility([q['rows'] for q in quality],pair['rows'],cfg)
    controlled=load(root/'controlled'/scene/'measurements/qualification.json')
    for v in controlled['variants']:
        controlled_count+=len(v['rows'])
        expected=controlled_eligibility(v['rows'],v['coverage'],cfg)
        expected['calibration_pass']=all(c['passed'] for c in v['calibration'])
        expected['passed']=expected['passed'] and expected['calibration_pass']
        assert v['eligibility']==expected
        limits=cfg['eligibility']['controlled']
        for row in v['rows']:
            assert row['passed']==bool(row['valid'] and
                (row['psnr_db'] is None or row['psnr_db']>=limits['psnr_min']) and
                row['ssim']>=limits['ssim_min'] and row['p99_max_channel_abs']<=limits['p99_max'])
for gpu in [0,1]:
    jobs=sorted([t for t in training if t['gpu']==gpu],key=lambda t:t['started_utc'])
    assert all(a['finished_utc']<=b['started_utc'] for a,b in zip(jobs,jobs[1:]))
audit=load(root/'access_audit.json');assert audit['passed'] and audit['trace_count']==36
assert audit['forbidden_successes']==audit['unparsed_open_lines']==0
for policy in root.glob('**/allowlist.json'):
    for p,h in load(policy).get('source_hashes',{}).items():assert sha256(p)==h,p
result=load(root/'results.json');check_report(result,(root/'RESULTS.md').read_text())
assert quality_count==result['totals']['quality_view_background_rows']==512
assert controlled_count==result['totals']['controlled_view_background_rows']==1152
assert pair_count==result['totals']['independent_pair_rows']==256
print('Training, source allowlists and all frozen gate computations verified',flush=True)

json_count=sidecars=0
for p in root.rglob('*.json'):
    if {'vendor','inputs'}.intersection(p.relative_to(root).parts):continue
    load(p);json_count+=1
for p in root.rglob('*.sha256'):
    target=Path(str(p)[:-7]);assert sha256(target)==p.read_text().strip(),str(p);sidecars+=1
tracked_media=[ROOT/p for p in git('ls-files','*.png','*.mp4').splitlines()]
new_png=[p for p in root.rglob('*.png') if not {'vendor','inputs'}.intersection(p.relative_to(root).parts)]
pngs=sorted(set(new_png+[p for p in tracked_media if p.suffix=='.png']))
png_rows=[verify_png(p) for p in pngs];mp4_rows=[]
ffprobe=Path('/home/u00134/bin/miniconda3/envs/ts_diffusion/bin/ffprobe')
for p in sorted(p for p in tracked_media if p.suffix=='.mp4'):
    command=[str(ffprobe),'-v','error','-threads','1','-count_frames','-select_streams','v:0','-show_entries',
        'stream=nb_frames,nb_read_frames,width,height,r_frame_rate','-of','json',str(p)]
    stream=json.loads(subprocess.check_output(command))['streams'][0]
    assert int(stream['nb_read_frames'])>0
    if stream.get('nb_frames','N/A')!='N/A':assert stream['nb_frames']==stream['nb_read_frames']
    mp4_rows.append(dict(path=str(p),**stream))
assert not list(root.rglob('*.mp4'))
freeze_json(root/'setup/media_verification.json',dict(png_count=len(png_rows),pngs=png_rows,mp4s=mp4_rows,
    scope='Every tracked repository PNG/MP4 plus every new experiment output PNG; prior artifacts only decoded for integrity, never used for method tuning. No new MP4 stage was reached.'))
npz=list(root.rglob('*.npz'))
for p in npz:
    with zipfile.ZipFile(p) as z:assert z.testzip() is None,str(p)
print('Images, video frame counts, JSON sidecars and native-array CRCs verified',flush=True)
tests=load(root/'setup/final_test_runs.json');assert all(r['exit_code']==0 for r in tests['runs'])
freeze_json(root/'VERIFICATION.json',dict(created_utc=utc(),passed=True,
    prereg_commit=git('rev-parse','ab40ec9'),prereg_committed_utc=prereg_time,
    config_sha256=sha256(root/'config.json'),input_files=len(inputs['files']),prior_reports=len(inputs['prior_reports']),
    upstream_tracked_source_files=len(source['files']),isolated_source_commit=cfg['training']['source_commit'],
    isolated_source_diff_sha256=source['diff_sha256'],external_dirty_source_unchanged=True,
    trained_posteriors=len(training),training=training,initialization_hashes=init,
    no_training_overlap_per_gpu=True,all_launch_memory_checks_passed=True,
    access_audit_sha256=sha256(root/'access_audit.json'),access_trace_count=36,
    forbidden_successes=0,unparsed_open_lines=0,source_allowlist_hashes_unchanged=True,
    quality_rows=quality_count,controlled_rows=controlled_count,pair_rows=pair_count,
    json_files_parsed=json_count,sidecar_hashes_verified=sidecars,results_markdown_consistent=True,
    png_files_decoded=len(png_rows),mp4_frame_counts_verified=len(mp4_rows),new_mp4s=0,
    ffprobe=dict(path=str(ffprobe),sha256=sha256(ffprobe)),
    native_archives_crc_checked=len(npz),tests=tests,
    git_final_equality='Recorded after final commit/push in external report to avoid recursive commit hashes',
    manifest='Generated after this verification and final documentation; then independently rehashed after commit'))
