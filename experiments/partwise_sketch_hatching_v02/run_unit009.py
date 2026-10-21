"""Source/input locking and cold request for the frozen stem density unit."""
from common import *
import argparse,shutil,subprocess
from datetime import datetime,timezone
U=OUT.parent/'unit_009'
def cp(src,dst):
    assert not dst.exists(),dst
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
def resources():
    count=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
    root=shutil.disk_usage(WORK).free;hdd=shutil.disk_usage(U).free
    assert root>=2**30 and hdd>=10*2**30 and count<20*2**30
    return dict(task_output_bytes=count,root_free_bytes=root,hdd_free_bytes=hdd,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
def freeze():
    names=['common.py','renderer.py','asset_cli.py','direction_cli.py','density_cli.py','test_density_unit009.py','run_unit009.py','media_unit009.py','receipt_unit009.py','validate_unit009.py','validate_unit008.py','validate_unit005.py','validate_unit004.py','validate_unit003.py','run_unit002.py']
    files=[WORK/'experiments/partwise_sketch_hatching_v02'/n for n in names]+[LEGACY/n for n in ('core.py','core_walk_v2.py')]
    files += [U/'PROTOCOL.json']+sorted((U/'inputs').glob('*'))
    for p in files:
        if p.is_relative_to(WORK):cp(p,U/'source_snapshot'/p.relative_to(WORK))
    write_json(U/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in files},git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),numpy_version=np.__version__))
    write_json(U/'RESOURCES_LOCK.json',resources())
def lock():
    for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
    resources()
def cold_request():
    for name in ('recipe.json','mesh.npz','source_strokes.npz','config.json'):cp(U/'outputs/edited'/name,U/'cold_request'/name)
    write_json(U/'COLD_REQUEST.json',dict(files={p.name:sha(p) for p in (U/'cold_request').glob('*')},selected_cache_present=False,
        scope='Fresh selection from original458 source asset, not procedural path regeneration; no saved selected434 path cache'))
def history():
    rows=[]
    for n in (3,4,5,6,7,8):
        old=U.parent/f'unit_{n:03}';seal=json.loads((old/'SEAL.json').read_text());manifest=old/'SHA256_MANIFEST.json'
        assert sha(manifest)==seal['manifest_sha256'];data=json.loads(manifest.read_text())
        for item in data['files']:
            path=Path(data['roots'][item['root']])/item['path'];assert sha(path)==item['sha256'],path
        rows.append(dict(unit=str(old),files=len(data['files']),manifest_sha256=sha(manifest),valid=True))
    write_json(U/'HISTORICAL_SEAL_AUDIT.json',dict(valid=True,checks=rows));write_json(U/'RESOURCES_FINAL.json',resources())
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','cold_request','history']);args=ap.parse_args()
    if args.stage!='freeze':lock()
    globals()[args.stage]();print(json.dumps(dict(stage=args.stage,done=True)))
