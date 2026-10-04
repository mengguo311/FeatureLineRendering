from pathlib import Path
import json, hashlib, datetime, shutil, subprocess
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'artifacts/representative_edge_gaussians_v1'
SRC=Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1');TRANS=SRC.parent/'transport/frames'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 orig=SRC/'artifacts/gaussian_edge_attribution_v1/INPUTS_FROZEN.json';x=json.loads(orig.read_text());cfg=json.loads((ART/'code/config.json').read_text())
 m=dict(schema='representative-input-manifest-v1',base_sha=cfg['base_sha'],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_root=str(SRC),transport=str(TRANS),inherited_manifest=dict(path=str(orig),sha256=sha(orig)),scenes={},source_files={})
 for scene,v in x['scenes'].items():
  cp=v['checkpoint'];assert sha(cp['path'])==cp['sha256'];frames=[]
  for f in v['frames']:
   cam=TRANS/scene/f['key']/'camera.json';assert sha(cam)==f['camera_json_sha256']
   raw=TRANS/scene/f['key']/'native.npz';rec=dict(f,camera_json_path=str(cam),raw_path=str(raw),raw_hash_verification='inherited, verify on read')
   if f['key'].startswith('F_'):assert sha(raw)==f['raw_sha256'];rec['raw_hash_verification']='S0 F-only hash checked'
   frames.append(rec)
  m['scenes'][scene]=dict(checkpoint=cp,frames=frames,training_scope=v['training_lock']['training_access'])
 paths=[orig,SRC/'native_extension/BUILD_TOP32.json',SRC/'native_extension/top32/diff_gaussian_rasterization/_C.cpython-39-x86_64-linux-gnu.so']
 paths += [SRC/'artifacts/gaussian_edge_attribution_v1/code'/n for n in ['core.py','native_attributes.py','run_experiment.py','media.py','config.json']]
 paths += [SRC/'artifacts/gaussian_edge_attribution_v1/assets'/s/n for s in cfg['scenes'] for n in ['scores.npz','selection.npz']]
 for p in paths:m['source_files'][str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
 (ART/'INPUT_HASH_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
 files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ART.rglob('*')) if p.is_file() and p.name!='S0_SEAL.json'}
 files['.codex/config.toml']=sha(ROOT/'.codex/config.toml')
 seal=dict(created_utc=m['created_utc'],files=files,preproduction=True,tests=dict(red='actual import failure before core implementation',green='8 synthetic CPU unittest passed'),runtime=dict(model='gpt-6.1-sol',reasoning_effort='xhigh',evidence='AGENT.log launch header; launch.sh explicit flags'),available_bytes=dict(root=shutil.disk_usage(ROOT).free,git=shutil.disk_usage(subprocess.check_output(['git','rev-parse','--git-common-dir'],text=True).strip()).free))
 (ART/'S0_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps(dict(frames=sum(len(v['frames']) for v in m['scenes'].values()),seal_sha256=sha(ART/'S0_SEAL.json'),available_bytes=seal['available_bytes'])))
if __name__=='__main__':main()
