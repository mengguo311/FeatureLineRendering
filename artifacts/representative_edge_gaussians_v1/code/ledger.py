"""Stable SHA256 ledger for source bindings, generated media/IDs/arrays and checks."""
from io_utils import *
import json,subprocess

def main():
 guard();m={}
 exclude={'LEDGER.log','SOURCE_MAP.json','FINAL.json','AGENT.log','AGENT_FINAL.md','AGENT_EXIT.txt','EVENTS.jsonl','STATUS.json','DELIVERY_VERIFICATION.json'}
 for base in [ART,OUT]:
  for p in sorted(base.rglob('*')):
   if p.is_file() and p.name not in exclude and '.partial' not in p.name and '__pycache__' not in p.parts:
    m[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size)
 inputs={}
 for scene,entry in INPUTS['scenes'].items():
  cp=entry['checkpoint'];inputs[cp['path']]=dict(sha256=cp['sha256'],kind='frozen vanilla30k original PLY, unchanged')
  for f in entry['frames']:
   actualread=[p for p in (OUT/scene).rglob('METRICS.json') if p.parent.name==f['key']]
   inputs[f['raw_path']]=dict(sha256=f['raw_sha256'],camera_hash=f['camera_hash'],camera_json_sha256=f['camera_json_sha256'],actual_pixel_read=bool(actualread) or f['key'].startswith('F_'),binding='inherited frozen digest, checked on every authorized read')
   inputs[f['camera_json_path']]=dict(sha256=f['camera_json_sha256'],kind='source camera identity')
 inputs.update(INPUTS['source_files'])
 model_config=ROOT/'.codex/config.toml';m[str(model_config)]=dict(sha256=sha(model_config),bytes=model_config.stat().st_size)
 old_norm=SRC/'out/gaussian_edge_attribution_v1/mic/NORMALIZATION.json';inputs[str(old_norm)]=dict(sha256=sha(old_norm),bytes=old_norm.stat().st_size,kind='historical F-only normalization metadata')
 from native_attributes import HISTORICAL_BUILD,EXPECTED_PATCHED_SO_SHA256
 native4=json.loads(HISTORICAL_BUILD.read_text());native4lib=Path(native4['variants']['patched']['path']);assert sha(native4lib)==EXPECTED_PATCHED_SO_SHA256
 for p in [HISTORICAL_BUILD,native4lib,SRC/'native_extension/top32/cuda_rasterizer/render_forward.cu']:
  inputs[str(p)]=dict(sha256=sha(p),bytes=p.stat().st_size,kind='audited read-only native source or library')
 figures={}
 for scene in CFG['scenes']:
  path=OUT/scene/'media/MEDIA.json'
  if path.exists():
   media=json.loads(path.read_text());figures[scene]=dict(media=media,F_selection_seal_sha256=sha(OUT/'F_SELECTION_SEAL/SEAL.json'),ordered_pose_camera_hashes=[dict(key=f['key'],camera_hash=f['camera_hash'],raw_sha256=f['raw_sha256']) for f in INPUTS['scenes'][scene]['frames']])
 (ART/'RUNTIME_PROVENANCE.json').write_text(json.dumps(dict(current=dict(model='gpt-6.1-sol',reasoning_effort='xhigh',launch_header=(OUT/'AGENT.log').read_text().split('user\n',1)[0],config_sha256=sha(ROOT/'.codex/config.toml')),historical_base=dict(commit=CFG['base_sha'],config=subprocess.check_output(['git','show',CFG['base_sha']+':.codex/config.toml'],text=True),scope='base config evidence; no relabeling of historical results')),indent=2)+'\n')
 m[str(ART/'RUNTIME_PROVENANCE.json')]=dict(sha256=sha(ART/'RUNTIME_PROVENANCE.json'),bytes=(ART/'RUNTIME_PROVENANCE.json').stat().st_size)
 atomic(ART/'SOURCE_MAP.json',dict(schema='representative-source-map-sha256-v1',created_utc=utc(),input_hash_manifest_sha256=sha(ART/'INPUT_HASH_MANIFEST.json'),files=m,inputs=inputs,scene_media_camera_provenance=figures,notes=['Live AGENT.log/events/status excluded from stable generated-file ledger; launch header separately preserved','Each pose METRICS/SEAL binds camera/raw/fields to projection and panel; contact panels retain all source views','Final JSON intentionally excluded to avoid cyclic hashes; delivery verification hashes FINAL/SOURCE_MAP/report']))
 final=json.loads((ART/'FINAL.json').read_text());final.update(source_map_sha256=sha(ART/'SOURCE_MAP.json'),report_sha256=sha(ART/'REPORT_ZH.md'),budget_final=guard(),code_source_sha256={p.name:sha(p) for p in sorted((ART/'code').glob('*')) if p.is_file()},runtime_provenance_sha256=sha(ART/'RUNTIME_PROVENANCE.json'));atomic(ART/'FINAL.json',final)
 event('LEDGER_COMPLETE',generated_files=len(m),input_bindings=len(inputs),source_map_sha256=sha(ART/'SOURCE_MAP.json'))
if __name__=='__main__':main()
