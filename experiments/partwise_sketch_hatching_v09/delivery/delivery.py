"""Assemble and check an in-place evidence delivery; never run science again."""
import runtime
from runtime import ROOT, UNIT, WORK, CODE, js, sha, now
from catalog import file_record, check_records
from pathlib import Path
import argparse
import json
import shutil
import shlex
import re
import importlib.metadata

OLD = Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/delivery_final_20261027')
UNITS = [ROOT / f'units/unit_{i:03d}' for i in range(1, 5)]
MEDIA = [
    ('H2_static_natural.png',1,'NATURAL_COMPARISON.png',1),
    ('H2_static_matched.png',1,'MATCHED_COMPARISON.png',1),
    ('H2_static_layers.png',1,'WHOLE_LAYERS.png',1),
    ('H2_static_conventional_corrected.png',1,'CONVENTIONAL_PROXY_CORRECTED.png',1),
    ('H2_motion_natural.png',3,'natural_orbit.png',37),
    ('H2_motion_matched.png',3,'matched_orbit.png',37),
    ('H2_motion_keyframes.png',3,'natural_KEYFRAMES.png',1),
    ('H2_motion_matched_keyframes.png',3,'matched_KEYFRAMES.png',1),
    ('H2_motion_all_frames.png',3,'natural_ALL_FRAMES.png',1),
    ('H2_motion_layers.png',3,'WHOLE_LAYERS.png',1),
    ('H1_azimuth_natural.png',2,'natural_orbit.png',25),
    ('H1_azimuth_matched.png',2,'matched_orbit.png',25),
    ('H1_azimuth_keyframes.png',2,'KEYFRAMES.png',1),
    ('H1_azimuth_layers.png',2,'WHOLE_LAYERS.png',1),
    ('H1_elevation_natural.png',4,'natural_orbit.png',13),
    ('H1_elevation_matched.png',4,'matched_orbit.png',13),
    ('H1_elevation_keyframes.png',4,'KEYFRAMES.png',1),
    ('H1_elevation_layers.png',4,'WHOLE_LAYERS.png',1),
]
OLD_EVIDENCE = [
    'CONTENTS.json',
    'history/unit_007/REPORT_ZH.md', 'history/unit_007/PROTOCOL.json',
    'history/unit_007/SCHEDULING_DEVIATION.json', 'history/unit_007/SCHEDULING_RECOVERY.json',
    'history/unit_008/REPORT_ZH.md', 'history/unit_008/PROTOCOL.json',
    'history/unit_008/TEMPORAL.json', 'history/unit_008/INTERRUPTION_007.json',
    'history/unit_008/PATH_SCOPE_DEVIATION.json',
]
RECEIPTS = [
    (1,'011_regenerate_replay.json','U/S/D/sham shared-generator regeneration; exact-camera GS caches'),
    (1,'007_cold_original.json','Original PLY cold check at high rear'),
    (2,'018_documented_replay.json','Original PLY and H1 BUILD saved-config cold replay'),
    (3,'022_cold_replay025.json','Original PLY and U/S/D/sham cold replay at241/27'),
    (4,'011_cold_replay006.json','Original PLY cold check then H1 saved-cache replay at241/42'),
]

def read(p):
    return json.loads(Path(p).read_text())

def files_under(folder):
    for p in sorted(folder.rglob('*')):
        if p.is_file() and not any(x in ('scratch','build','__pycache__') for x in p.relative_to(folder).parts):
            yield p

def freeze():
    if shutil.disk_usage('/').free < 2**30 or shutil.disk_usage(ROOT).free < 10*2**30:
        raise RuntimeError('disk reserve')
    records = []
    for unit in UNITS:
        records.extend(file_record(p, unit.name) for p in files_under(unit))
    for name in ('h2','h1','h2_motion','h1_elevation'):
        records.extend(file_record(p,'worktree_science') for p in files_under(CODE.parent/name) if p.suffix in ('.py','.cpp'))
    records.extend(file_record(OLD/p,'immutable_v08_history') for p in OLD_EVIDENCE)
    records.append(file_record(WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md','original_outline'))
    records.append(file_record(ROOT/'orchestration/BRIEF.md','read_only_brief'))
    records.append(file_record(UNIT/'DECISION.json','parent_decision'))
    js(UNIT/'INPUT_MANIFEST.json',dict(schema='in_place_sha256_inventory_v1',files=records,
        exclusions='build, scratch and __pycache__ only; original exclusions remain on disk untouched',
        packaging='Existing unit001..004 data are the in-place package. No relocation/standalone certification. No archive.'))
    camera_refs = []
    for i,u in enumerate(UNITS,1):
        p = u/('PROTOCOL.json' if i==1 else 'CAMERAS.json')
        camera_refs.append(file_record(p,f'unit{i:03d}_frozen_cameras'))
    js(UNIT/'CAMERA_REFERENCES.json',dict(new_cameras=0,references=camera_refs,
        H2_static='151/36,196/36,241/24,241/60,61/24',
        H2_motion='37 frames196/36→241/24→241/60 plus BUILD/FRONT',
        H1_azimuth='25 frames196/36→241/24 plus BUILD/HIGH',
        H1_elevation='13 frames241/24→241/60 plus BUILD/BACK'))
    source = [file_record(p,'delivery_tool') for p in sorted(CODE.glob('*.py'))]
    source.append(file_record(WORK/'docs/partwise_sketch_hatching_v09/DEMO_README_ZH.md','delivery_readme_template'))
    js(UNIT/'SOURCE_MANIFEST.json',dict(files=source))
    js(UNIT/'PROTOCOL.json',dict(schema='unit005_final_delivery_v1',frozen_utc=now(),
        decision_sha256=sha(UNIT/'DECISION.json'),input_manifest_sha256=sha(UNIT/'INPUT_MANIFEST.json'),
        source_manifest_sha256=sha(UNIT/'SOURCE_MANIFEST.json'),camera_references_sha256=sha(UNIT/'CAMERA_REFERENCES.json'),
        scope='Delivery integrity and exact media copies only; no new experiments, renders, metrics or scientific tests.',
        unchanged_science='All source rows, geometry/fullSH, labels, source S, paths, guides, policies, cameras, factors and masks.',
        required_media=[dict(destination=n,source=str(ROOT/f'units/unit_{i:03d}/media'/p),frames=f) for n,i,p,f in MEDIA],
        validation='SHA of immutable prior files, existing scientific locks, actual rc receipts, linked PLY/binding hashes, full decode of delivered media, local documentation links.',
        gates='Any missing/corrupt evidence remains a delivery blocker; scientific PARTIAL cannot become PASS.',
        resources='serial CPU affinity2 threads1 CUDAempty; no scientific module imports',
        deadline='no new science15:20; wrap15:45; hard stop16:00 JST'))
    print(json.dumps(dict(frozen_files=len(records),bytes=sum(r['size'] for r in records),new_science=False)),flush=True)

def assemble():
    protocol=read(UNIT/'PROTOCOL.json')
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    copied=[]
    for row in protocol['required_media']:
        src=Path(row['source']);dst=runtime.guard(UNIT/'media'/row['destination'])
        if dst.exists():raise FileExistsError(dst)
        dst.parent.mkdir(exist_ok=True)
        shutil.copyfile(src,dst)
        assert sha(src)==sha(dst)
        copied.append(dict(**row,copy=str(dst),sha256=sha(dst)))
    js(UNIT/'MEDIA_INDEX.json',dict(exact_byte_copies=copied,new_frames=0,legends='Original English legends unchanged; no enhancement or cropping.'))
    commands=[]
    for i,name,scope in RECEIPTS:
        path=ROOT/f'units/unit_{i:03d}/logs'/name
        r=read(path)
        assert r['child_returncode']==0, str(path)
        commands.append(dict(receipt=str(path),receipt_sha256=sha(path),actual_argv=r['argv'],
            actual_shell=shlex.join(r['argv']),child_returncode=r['child_returncode'],scope=scope,
            execution='Historical actual success, not rerun in unit005. Existing output names cannot be reused.'))
    js(UNIT/'COMMANDS.json',dict(commands=commands,working_directory=str(WORK),
        caution='Use each original REPRODUCE.md with fresh output names. unit003/004 guards write inside those units; do not alter old guards or run prepare/finish. This delivery audit runs no replay.'))
    failure_groups=[
        dict(name='H2 partial and D coverage cost',paths=['units/unit_001/REPORT_ZH.md','units/unit_001/D_GENERATION.json','units/unit_003/REPORT_NUMBERS.json'],meaning='S4 elevation losses; D36/37 lower interior coverage; no whole-object winner.'),
        dict(name='Matched FAR nonzero and failed zero assertion',paths=['units/unit_003/FAR_COUNTEREXAMPLE.json','units/unit_003/failed_attempts/audit_zero_far_assumption','units/unit_003/logs/020_audit.json'],meaning='Original rc1 remains; no enlarged mask or scientific zero-FAR pass.'),
        dict(name='Interrupted serial batch',paths=['units/unit_003/INTERRUPTION_005.json','units/unit_003/logs/005_arc000_004.start.json','units/unit_003/logs/005_arc000_004.log'],meaning='Outer143; wrapper/child/cause UNKNOWN; original final receipt missing.'),
        dict(name='Initial deficient B0 and launch/path failures',paths=['units/unit_002/failed_attempts/initial_center_only_baseline','units/unit_002/logs/004_LAUNCH_FAILURE_NOTE.json','units/unit_002/logs/011_arc_010_014.json'],meaning='Initial center-only B0 is not the main baseline; repaired before DEV. Actual failure receipts retained.'),
        dict(name='Incorrect conventional label',paths=['units/unit_001/DISPLAY_CORRECTION.json','units/unit_001/media/PROXY_REFERENCE.png','units/unit_001/media/CONVENTIONAL_PROXY_CORRECTED.png'],meaning='Old proxy reference contains seat S; only corrected conventional output is cited as ungated proxy.'),
        dict(name='H1 own ink and unequal support',paths=['units/unit_002/REPORT_ZH.md','units/unit_004/REPORT_NUMBERS.json','units/unit_004/FAR_OBSERVATIONS.json'],meaning='H1 conditional only; B1 source-visible missing71.4868px and common79.762% in elevation.'),
    ]
    for g in failure_groups:
        g['paths']=[str(ROOT/p) for p in g['paths']]
        for p in g['paths']:
            if not Path(p).exists():raise FileNotFoundError(p)
    js(UNIT/'FAILURE_INDEX.json',dict(current=failure_groups,
        inherited_v08=[str(OLD/p) for p in OLD_EVIDENCE],
        inherited_scope='Original v08 reports retain v05/v07 negatives, old143UNKNOWN, open return/holes/high rear zero,3own-dropouts/1reappearance,2.562698s overlap and path deviation. Not re-evaluated or repaired here.'))
    versions={n:importlib.metadata.version(n) for n in ('numpy','scipy','Pillow','open3d')}
    js(UNIT/'DEPENDENCIES.json',dict(packaging='In-place local delivery; complete units remain at original absolute paths; no standalone/portable claim.',
        python=str(Path(runtime.sys.executable).absolute()),versions=versions,
        worktree=str(WORK),branch='partwise-sketch-hatching-gaussian-link-v09',
        science_dirs=[str(u) for u in UNITS],source_worktree_dirs=[str(CODE.parent/n) for n in ('h2','h1','h2_motion','h1_elevation')],
        source_lock_dependency='unit002/003/004 SOURCE_LOCK includes original worktree files; saved code alone is insufficient if these are moved.',
        source_data='Each inputs/assets/on/LINKED_ASSET.json resolves ../../data/chair/source.ply and SOURCE_BINDING.npz; original zero-based source_index256690.',
        output_guards={'H2_static':'new v09 HDD path via replay_h2 --out','H1_azimuth':'unit002 new output-name','H2_motion':'unit003 new replay-key','H1_elevation':'unit004 new output-name'},
        historical_v08=str(OLD),environment_write=False,no_gpu=True))
    runtime.write(ROOT/'DEMO_README_ZH.md',(WORK/'docs/partwise_sketch_hatching_v09/DEMO_README_ZH.md').read_text())
    js(ROOT/'DELIVERY_STATUS.json',dict(execution_state='partial',stage='assembled_pending_integrity_audit',
        scientific_verdict='PARTIAL unchanged',parent_verification='pending independent parent read'))
    base=read(UNIT/'INPUT_MANIFEST.json')
    extra=[file_record(p,'unit005_delivery') for p in files_under(UNIT) if p.name not in ('INPUT_MANIFEST.json',) and 'logs' not in p.parts]
    extra.append(file_record(ROOT/'DEMO_README_ZH.md','root_readme'))
    js(ROOT/'DELIVERY_CONTENTS.json',dict(schema='in_place_delivery_manifest_v1',frozen_utc=now(),
        scientific_files=base['files'],delivery_files=extra,
        closure='Final STATUS/REPORT/audit receipts are indexed later in unit005/FINAL_MANIFEST.json to avoid a self-hash cycle.',
        excluded=base['exclusions'],package_semantics=base['packaging']))
    print(json.dumps(dict(media_copied=len(copied),historical_commands=len(commands),new_science=False)),flush=True)

def audit():
    from PIL import Image
    protocol=read(UNIT/'PROTOCOL.json');errors=[]
    for name,key in [('DECISION.json','decision_sha256'),('INPUT_MANIFEST.json','input_manifest_sha256'),('SOURCE_MANIFEST.json','source_manifest_sha256'),('CAMERA_REFERENCES.json','camera_references_sha256')]:
        if sha(UNIT/name)!=protocol[key]:errors.append(dict(kind='frozen_manifest_changed',path=name))
    inventory=read(ROOT/'DELIVERY_CONTENTS.json')
    errors.extend(check_records(inventory['scientific_files']+inventory['delivery_files']))
    errors.extend(check_records(read(UNIT/'SOURCE_MANIFEST.json')['files']))
    lock_checks=[]
    for i,u in enumerate(UNITS,1):
        for name in ('INPUT_LOCK.json','SOURCE_LOCK.json','DERIVED_LOCK.json'):
            p=u/name
            if not p.exists():continue
            records=read(p)
            for key,h in records.items():
                target=Path(key) if Path(key).is_absolute() else ((CODE.parent/'h2'/key) if i==1 and name=='SOURCE_LOCK.json' else u/key)
                if not target.is_file() or sha(target)!=h:errors.append(dict(kind='historical_lock_mismatch',lock=str(p),path=str(target)))
            lock_checks.append(dict(path=str(p),entries=len(records)))
    assets=[]
    for u in UNITS:
        a=u/'inputs/assets/on';link=read(a/'LINKED_ASSET.json')
        for field,hfield in [('source_file','source_sha256'),('binding_file','binding_sha256')]:
            p=(a/link[field]).resolve()
            if not p.is_file() or sha(p)!=link[hfield]:errors.append(dict(kind='linked_asset_mismatch',path=str(p)))
        if link['source_count']!=256690 or link['unknown_rows']!=170281:errors.append(dict(kind='source_identity_metadata',path=str(a)))
        assets.append(dict(unit=u.name,rows=link['source_count'],unknown=link['unknown_rows'],source_sha256=link['source_sha256']))
    decoded=[]
    for r in read(UNIT/'MEDIA_INDEX.json')['exact_byte_copies']:
        if sha(r['source'])!=sha(r['copy']):errors.append(dict(kind='media_copy_changed',path=r['copy']))
        with Image.open(r['copy']) as im:
            count=getattr(im,'n_frames',1);size=im.size
            for frame in range(count):im.seek(frame);im.load()
            if count!=r['frames']:errors.append(dict(kind='frame_count',path=r['copy'],actual=count,expected=r['frames']))
        decoded.append(dict(path=r['copy'],frames=count,size=size,all_decoded=True))
    link_checks=[]
    for doc in [ROOT/'DEMO_README_ZH.md']:
        for dest in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
            if dest.startswith(('https:','http:','#')):continue
            p=Path(dest) if dest.startswith('/') else doc.parent/dest
            if not p.exists():errors.append(dict(kind='broken_document_link',path=str(p)))
            link_checks.append(str(p))
    # Read actual receipts; never infer a successful child from an outer tool result.
    for r in read(UNIT/'COMMANDS.json')['commands']:
        actual=read(r['receipt'])
        if actual.get('child_returncode')!=0 or actual['argv']!=r['actual_argv']:errors.append(dict(kind='receipt_changed',path=r['receipt']))
    report=dict(utc=now(),delivery_integrity='PASS' if not errors else 'FAIL',scientific_verdict='PARTIAL unchanged',
        immutable_files_checked=len(inventory['scientific_files']),delivery_files_checked=len(inventory['delivery_files']),
        historical_locks=lock_checks,original_assets=assets,media=decoded,document_links_checked=len(link_checks),
        errors=errors,new_scientific_runs=0,new_metrics=0,new_cold_renders=0,
        scope='File identity, links and decoding only; not scientific revalidation or independent perceptual assessment.',
        parent_verification='pending independent parent read')
    js(UNIT/'AUDIT.json',report)
    print(json.dumps({k:report[k] for k in ('delivery_integrity','immutable_files_checked','delivery_files_checked','errors')}),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['freeze','assemble','audit']);a=p.parse_args()
    globals()[a.stage]()
