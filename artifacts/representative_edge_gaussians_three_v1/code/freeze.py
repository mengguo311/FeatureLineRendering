"""S0 metadata-only binding; F raw hashes checked, C/arc pixels remain closed."""
from pathlib import Path
import json,datetime,subprocess,shutil,difflib
from scene_binding import *
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts/representative_edge_gaussians_three_v1';SRC=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1')
def bind():
 from native_attributes import load_checkpoint,canonical_hash,camera_record
 cfg=json.loads((ART/'code/config.json').read_text());orig=HYBRID/'artifacts/direct_curve_global_fit_probe/INPUTS.json';x=json.loads(orig.read_text());assert x['F']==cfg['F'] and x['C']==cfg['C']
 m=dict(schema='representative-three-input-v1',base_sha=cfg['base_sha'],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_root=str(SRC),frame_source=str(HYBRID/'out/hybrid_raster_evidence_v2/frames'),scenes={},source_files={})
 paths=[orig,HYBRID/'artifacts/hybrid_raster_evidence_v2/ACCESS.json',HYBRID/'artifacts/hybrid_raster_evidence_v2/PARAMETER_LOCK.json',HYBRID/'out/hybrid_raster_evidence_v2/LOCK.json',HYBRID/'out/hybrid_raster_evidence_v2/CONFIG.json',HYBRID/'scripts/run_hybrid_raster_evidence_v2.py',HYBRID/'src/hybrid_raster_io.py',HYBRID/'src/hybrid_raster_native.py',SRC/'native_extension/BUILD_TOP32.json']
 for key,p in [('normalization_source',REFERENCE/'out/representative_edge_gaussians_v1/NORMALIZATION.json'),('A_normalization_source',SRC/'out/gaussian_edge_attribution_v1/mic/NORMALIZATION.json'),('A_config_source',SRC/'artifacts/gaussian_edge_attribution_v1/code/config.json')]:m[key]=dict(path=str(p),sha256=sha(p));paths.append(p)
 paths += [REFERENCE/'artifacts/representative_edge_gaussians_v1'/n for n in ['FINAL.json','REPORT_ZH.md','PROTOCOL.md','INPUT_HASH_MANIFEST.json','SOURCE_MAP.json','REPRODUCE.md']]
 b=capacity64();paths.extend([Path(b['library']),Path(b['build_manifest_path']),Path(b['build_manifest_path']).parent/'capacity.patch'])
 for scene in SCENES:
  cp=dict(x['scenes'][scene]['checkpoint']);g,q=load_checkpoint(cp['path'],cp['sha256']);cp['qualification']=q;del g
  training=Path(cp['path']).parents[3];manifest=training/'manifest.json';completion=training/'completion.json';tr=json.loads(manifest.read_text());assert tr['scene']==scene and tr['seed']==1729 and tr['expected_iteration']==30000 and tr['source'].endswith('/vendor/gaussian-splatting');assert json.loads(completion.read_text())['sha256']==cp['sha256'];paths.extend([manifest,completion])
  records=[]
  for key in [f'F_{i:03d}' for i in cfg['F']]+[f'C_{i:03d}' for i in cfg['C']]+[f'arc0_{i:03d}' for i in range(33)]:
   d=HYBRID/'out/hybrid_raster_evidence_v2/frames'/scene/key;camfile=d/'camera.json';sealf=d/'SEAL.json';v=json.loads(camfile.read_text());seal=json.loads(sealf.read_text());assert v['scene']==scene and v['key']==key and v['checkpoint_sha256']==cp['sha256'];assert v['camera_hash']==canonical_hash(v['camera']);assert seal['files']['camera.json']==sha(camfile);assert seal['context']==v
   expected=x['scenes'][scene]['arcs'][0]['frames'][int(key[-3:])] if key.startswith('arc0_') else x['scenes'][scene]['cameras'][str(int(key[-3:]))];assert expected==v['camera'];camera_record(v['camera']);raw=d/'native.npz'
   if key.startswith('F_'):assert sha(raw)==seal['files']['native.npz']
   records.append(dict(key=key,camera=v['camera'],camera_hash=v['camera_hash'],camera_json_path=str(camfile),camera_json_sha256=sha(camfile),native_camera_hash=canonical_hash(camera_record(v['camera'])),raw_path=str(raw),raw_sha256=seal['files']['native.npz'],raw_hash_verification='S0 checked F only' if key.startswith('F_') else 'inherited seal; verify after all F selection seals',source_seal_path=str(sealf),source_seal_sha256=sha(sealf)))
  m['scenes'][scene]=dict(checkpoint=cp,display=display(scene),frames=records,training_scope='TRAIN cameras exposed to GS training; old C media already known; not blind or GS-unseen',training_provenance=dict(manifest_path=str(manifest),manifest_sha256=sha(manifest),source_commit=tr['source_commit'],source=tr['source']))
 for p in paths:
  if not p.is_file():raise FileNotFoundError(p)
  m['source_files'][str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
 for p in (ART/'code').glob('*'):
  if p.is_file() and (REFERENCE/'artifacts/representative_edge_gaussians_v1/code'/p.name).is_file():m['source_files'][str(REFERENCE/'artifacts/representative_edge_gaussians_v1/code'/p.name)]=dict(sha256=sha(REFERENCE/'artifacts/representative_edge_gaussians_v1/code'/p.name),bytes=(REFERENCE/'artifacts/representative_edge_gaussians_v1/code'/p.name).stat().st_size)
 (ART/'INPUT_HASH_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');return m

def seal_s0():
 m=bind();diff=[];entries={}
 for p in sorted((ART/'code').glob('*')):
  if not p.is_file():continue
  ref=REFERENCE/'artifacts/representative_edge_gaussians_v1/code'/p.name
  entries[p.name]=dict(new_sha256=sha(p),reference_sha256=sha(ref) if ref.exists() else None,byte_identical=ref.exists() and p.read_bytes()==ref.read_bytes())
  if ref.exists():diff.extend(difflib.unified_diff(ref.read_text().splitlines(True),p.read_text().splitlines(True),fromfile='readonly-reference/'+p.name,tofile='newstage/'+p.name))
 for name in ['representative_core.py','legacy_core.py']:assert entries[name]['byte_identical']
 (ART/'ALGORITHM_DIFF.patch').write_text(''.join(diff));(ART/'ALGORITHM_BINDINGS.json').write_text(json.dumps(dict(files=entries,unchanged_scientific_cores=['representative_core.py','legacy_core.py'],allowed_adaptations=['scene binding','new outputs','persisted Mic normalization import','fresh deadline/resources','new historical A generation and scene budget counts','truthful scene counts/report/provenance'],diff_sha256=sha(ART/'ALGORITHM_DIFF.patch')),indent=2)+'\n')
 files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ART.rglob('*')) if p.is_file() and p.name not in ['S0_SEAL.json','TASK.txt','launch.sh'] and '__pycache__' not in p.parts};files['.codex/config.toml']=sha(ROOT/'.codex/config.toml')
 (ART/'S0_SEAL.json').write_text(json.dumps(dict(created_utc=m['created_utc'],files=files,preproduction=True,actual_test_logs=['logs/TDD_RED.log','logs/TDD_RED_SCENE.log','logs/TDD_GREEN.log'],normalization_inherited_no_refit=True,source_binding_frozen=True),indent=2)+'\n');print('S0',sha(ART/'S0_SEAL.json'),'poses',sum(len(x['frames']) for x in m['scenes'].values()))
if __name__=='__main__':
 import sys
 if '--bind-only' in sys.argv:bind()
 else:seal_s0()
