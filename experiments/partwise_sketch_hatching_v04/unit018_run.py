"""Unit018-owned protocol, command receipts and source snapshots."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,time

U=OUTPUT_ROOT/'units/unit_018'
PREV=OUTPUT_ROOT/'units/unit_017'
SOURCE=Path(__file__).resolve().parent

def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}

def freeze():
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert Path.cwd()==SOURCE.parents[1] and not (U/'PROTOCOL.json').exists()
    for name in ('logs','metrics','media'):(U/name).mkdir()
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_BEFORE.json',hashes(SOURCE))
    (U/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    package=U/'portable_demo';package.mkdir()
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREV/'portable_demo'/name,package/name)
    for name in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/name,package/name)
    original=json.loads((package/'assets/lego/asset.json').read_text())['original']
    assert sha(original['original_ply'])==original['sha256']
    protocol=dict(unit='unit_018',frozen_utc=now(),scope='Saved-asset import and cold-session engineering; no new H1/H2/H5 experiment.',
        decision='Import downloaded saved-asset ZIP through the catalog browser into an independent editable session; preserve final state across a stopped server.',
        inputs={name:hashes(PREV/'portable_demo'/name) for name in ('assets','examples')},
        legacy_zip=dict(path=str(PREV/'browser/lego_asset.zip'),sha256=sha(PREV/'browser/lego_asset.zip')),original=original,
        region_provenance='Inherited model-depth proxy, authored height rules and manual bucket face selection; not learned semantics.',
        changed_variable='Archive import/export validation and browser session access. Geometry, labels, path generation, renderer and original assets fixed.',
        cameras='Use saved viewer cameras; imported Lego region1 ink .60 -> .35, Chair region2 ink .80 -> .50. Existing exposed views; no sweep.',
        expected_visual='Cold import matches saved full-object PNG. Subsequent local ink edit changes only the chosen region; non-target binary paths/layers remain exact.',
        checks=['TDD actual legacy Lego ZIP accepted as new independent session, roundtrip checksums, malformed ZIP/arrays/metadata rejected atomically.',
                'Actual Firefox file upload: legacy Lego and newly downloaded Chair; saved state and edits isolated, bad upload leaves current state intact.',
                'Stop server then start a new server, upload newly downloaded edited asset and match PNG/styles/camera; continue editing and undo.',
                'Export actual orbit12/zoom6, decode all frames, cold replay; portable source/assets tar and relocated documented startup.'],
        contract='Flat saved-asset ZIP only, known catalog model identity. Hashes detect corruption, not authenticity. Legacy ZIP has no complete archive manifest; geometry/path anchor validation and computed receipt only.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,finish_by_jst='2026-10-22T08:08:06+09:00'))
    js(U/'PROTOCOL.json',protocol)
    shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT018_PROTOCOL.json')
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='NOT_TESTED',
        demo_progress=dict(genuinely_ran_old_model=False,reasoning=protocol['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'),utc=now())))

def command(name,args,expected=0):
    start=time.monotonic();began=now()
    with (U/'logs'/f'{name}.log').open('w') as f:
        result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=540)
    receipt=dict(command=args,cwd=str(Path.cwd()),started_utc=began,finished_utc=now(),returncode=result.returncode,
        expected_returncode=expected,seconds=time.monotonic()-start,cpu_affinity=sorted(__import__('os').sched_getaffinity(0)))
    js(U/'logs'/f'{name}.receipt.json',receipt);print(json.dumps(receipt),flush=True)
    if result.returncode!=expected:raise RuntimeError('command failed; original log retained: '+name)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','run']);p.add_argument('--name');p.add_argument('--expected',type=int,default=0)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.phase=='freeze':freeze()
    else:command(a.name,a.command,expected=a.expected)
