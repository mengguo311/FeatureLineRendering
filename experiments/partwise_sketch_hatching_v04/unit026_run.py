"""Bounded engineering delivery for the existing real-model editor."""
import runtime
from runtime import js, sha, now, output_guard
from pathlib import Path
import argparse, json, shutil, subprocess, sys, time

U=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_models_v04/units/unit_026')
PREV=U.parent/'unit_025'
SOURCE=Path(__file__).resolve().parent

def hashes(path):
    return {str(f.relative_to(path)):sha(f) for f in sorted(path.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}

def command(name,args,expect=0):
    receipt=U/'logs'/f'{name}.receipt.json';assert not receipt.exists()
    started=now();t=time.monotonic()
    with (U/'logs'/f'{name}.log').open('w') as log:
        try:rc=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=540).returncode
        except subprocess.TimeoutExpired:rc=124
    js(receipt,dict(argv=args,cwd=str(Path.cwd()),started_utc=started,finished_utc=now(),seconds=time.monotonic()-t,returncode=rc,expected_returncode=expect))
    print(receipt.read_text(),flush=True)
    if rc!=expect:raise SystemExit(rc or 1)

def freeze():
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (U/'PROTOCOL.json').exists()
    for folder in ('logs','metrics','media'):(U/folder).mkdir(exist_ok=True)
    package=PREV/'portable_demo';catalog=json.loads((package/'CATALOG.json').read_text())
    inputs={}
    for scene,example in [('chair','chair_ink_preview'),('lego','lego_bucket_cross')]:
        asset=package/catalog['examples'][example]['asset'];meta=json.loads((asset/'asset.json').read_text())
        assert sha(meta['original']['original_ply'])==meta['original']['sha256']
        inputs[scene]=dict(example=example,asset=str(asset),files=hashes(asset),original=meta['original'],camera=meta.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)),region=4,ink_strength=.65 if scene=='chair' else .35)
    p=dict(unit='unit_026',frozen_utc=now(),inputs=inputs,catalog_sha256=sha(package/'CATALOG.json'),
        critical_review='Read full BRIEF and outline, P1/P2 report/NEXT and relevant source. Inspected unit025 actual full-object edit/cold image and desktop screenshot. Ink slider is below the visible sidebar, reopening ZIP below preview. Rough contours and thin geometry gaps remain.',
        ranked_next_steps=['First-screen region/ink and Open ZIP action; collapse advanced controls; validate and package','No new geometry comparison after 09:20','No fifth model needed for final delivery'],
        changed='UI organization only: region and ink first; expandable advanced controls; first-screen Open ZIP dialog. Same existing model assets, geometry, hatching, cameras and timers.',
        fixed='Existing four models and eight examples; fixed inherited cameras/styles/labels/path assets. Chair region4 ink .35 to .65; Lego manual bucket region4 ink .8 to .35. No parameter search.',
        region_source='Inherited manually authored partial seat and bucket regions; coarse source regions are rule defined, not learned semantics.',
        expected='Real Firefox red/green test: region and ink visible on desktop/small laptop; primary actions include accessible Open ZIP. Advanced controls reachable and dialogs open/close. Chair and Lego local edits, Undo, PNG/ZIP downloads, page reload, orbit/zoom; fresh server/browser imports both ZIPs and reproduces arrays/PNG without warm cache. Packaged source cold replay.',
        cameras='Inherited exposed cameras fixed before edits; no blind evaluation.',
        scope='Engineering usability only; no H1/H2/H5 claim. Preserve P1 NO_GO/P2 unidentifiability and all earlier failed exits.',
        resources=dict(cpu=2,numerical_threads=1,serial=True,gpu=False,nested_models=False,no_new_science_after_jst='09:20',wrap_jst='09:45'))
    js(U/'PROTOCOL.json',p);shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT026_PROTOCOL.json')
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'STATUS.json',dict(stage='protocol_frozen',execution_state='partial',scientific_verdict=p['scope'],demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['changed']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'))))

def stage():
    source=PREV/'portable_demo';dest=U/'portable_demo';dest.mkdir()
    for name in ('assets','examples'):shutil.copytree(source/name,dest/name)
    for name in ('CATALOG.json','run.sh','requirements.txt'):shutil.copy2(source/name,dest/name)
    meta=json.loads((source/'PORTABLE_DEMO.json').read_text());meta.update(source_unit='unit_026',created_utc=now(),optional_examples=list(json.loads((dest/'CATALOG.json').read_text())['examples']))
    meta.pop('optional_example',None);js(dest/'PORTABLE_DEMO.json',meta)
    shutil.copytree(SOURCE,dest/'source',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'metrics/PRESERVATION.json',dict(default_assets_exact=hashes(source/'assets')==hashes(dest/'assets'),eight_examples_exact=hashes(source/'examples')==hashes(dest/'examples')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.phase=='command':command(a.args[0],a.args[2:],int(a.args[1]))
    else:globals()[a.phase]()
