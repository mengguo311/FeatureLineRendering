"""Bounded example-catalog delivery; every output belongs to unit017."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time

U=OUTPUT_ROOT/'units/unit_017'
PREV=OUTPUT_ROOT/'units/unit_016'
SOURCE=Path(__file__).resolve().parent

def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}

def freeze():
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert Path.cwd()==SOURCE.parents[1]
    assert not (U/'PROTOCOL.json').exists()
    for name in ('logs','metrics','media'):(U/name).mkdir()
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_BEFORE.json',hashes(SOURCE))
    (U/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    package=U/'portable_demo';package.mkdir()
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREV/'portable_demo'/name,package/name)
    for name in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/name,package/name)
    examples={
      'lego_bucket_cross':dict(scene='lego',label='Bucket cross-hatching',asset='examples/lego_bucket_cross',
          description='Optional example · unit014 · manually selected bucket, second hatch direction. Original proxy.'),
      'lego_bucket_refined':dict(scene='lego',label='Bucket smoothing',asset='examples/lego_bucket_refined',
          description='Optional example · unit015 · local proxy smoothing on the authored bucket. Limited visual benefit; not recovered geometry.'),
      'lego_platform_ink':dict(scene='lego',label='Lighter platform',asset='examples/lego_platform_ink',
          description='Optional example · unit016 · smoothed bucket and 40% hatch ink in the height-defined lower region. Holes and thin-part noise remain.')}
    cat=json.loads((package/'CATALOG.json').read_text());cat['examples']=examples;js(package/'CATALOG.json',cat)
    original=json.loads((package/'assets/lego/asset.json').read_text())['original']
    assert sha(original['original_ply'])==original['sha256']
    protocol=dict(unit='unit_017',frozen_utc=now(),scope='Engineering usability only; H1/H2/H5 not tested.',
        decision='Expose three validated optional Lego examples, each with isolated edits, camera, draft and undo; preserve four default model assets.',
        inputs={name:hashes(PREV/'portable_demo'/name) for name in ('assets','examples')},original=original,
        region_provenance='Inherited authored height regions and manual bucket face selection; not automatic semantics.',
        changed_variable='Catalog/session identity and browser/CLI example selection only; renderer and generation unchanged.',
        fixed='All source asset bytes, geometry/labels/path IDs, styles and saved cameras. Existing exposed real models.',
        checks=['TDD real saved Lego: two same-scene examples must not share edits or undo; stale example rejected; old catalog stays compatible.',
          'Actual Firefox: default and all 3 examples, edit ink .40 to .60 on platform example, switch/back, refresh, undo/reapply, all 4 models, export.',
          'Asset ZIP and PNG + orbit12 + zoom6 downloads; decode all video frames; new-process cold replay and relocated documented CLI/viewer.'],
        edit=dict(example='lego_platform_ink',region=1,ink_strength=.60),
        cameras='Keep each asset saved viewer_camera; motion uses existing all-vertex fit. No visual parameter search or new science.',
        expected_visual='Existing complete objects are identical at equal saved states; selecting a named example restores its own authored appearance. .60 edit affects only region1 hatches.',
        promotion='Optional examples only; no default replacement or geometry-quality claim.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,deadline_jst='2026-10-22T07:56:26+09:00'))
    js(U/'PROTOCOL.json',protocol)
    shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT017_PROTOCOL.json')
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='NOT_TESTED',
        demo_progress=dict(genuinely_ran_old_model=False,reasoning=protocol['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'),utc=now())))

def command(name,args,expected=0):
    log=U/'logs'/f'{name}.log';start=time.monotonic();began=now()
    with log.open('w') as f:
        result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=540)
    receipt=dict(command=args,cwd=str(Path.cwd()),started_utc=began,finished_utc=now(),returncode=result.returncode,
        expected_returncode=expected,seconds=time.monotonic()-start,cpu_affinity=sorted(__import__('os').sched_getaffinity(0)))
    js(U/'logs'/f'{name}.receipt.json',receipt);print(json.dumps(receipt),flush=True)
    if result.returncode!=expected:raise RuntimeError('command failed; original log retained: '+name)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','run']);p.add_argument('--name');p.add_argument('--expected',type=int,default=0)
    p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.phase=='freeze':freeze()
    else:
        # Options precede `run`; remainder is the exact child command.
        command(a.name,a.command,expected=a.expected)
