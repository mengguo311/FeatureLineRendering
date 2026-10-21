"""Frozen explicit-asset width-edit experiment; writes only current unit005."""
from common import *
import argparse
import shutil
import subprocess
import time
from datetime import datetime, timezone
from PIL import Image
from run_unit002 import contact

UNIT = OUT.parent / 'unit_005'
PREVIOUS = OUT.parent / 'unit_004'
VIEWS = (30, 120, 210, 300)


def copy(source, destination):
    assert not destination.exists(), destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def resources():
    count = sum(p.stat().st_size for p in UNIT.parent.rglob('*') if p.is_file())
    root = shutil.disk_usage(WORK).free
    hdd = shutil.disk_usage(UNIT).free
    assert root >= 2**30 and hdd >= 10*2**30 and count < 20*2**30
    return dict(task_output_bytes=count, root_free_bytes=root, hdd_free_bytes=hdd,
                cpu_affinity=sorted(os.sched_getaffinity(0)), numeric_threads=1, gpu=False)


def prepare():
    UNIT.mkdir(parents=True, exist_ok=True)
    initial = dict(stage='explicit_asset_cli_preparation', execution_state='running',
        scientific_verdict='PENDING', tests={}, artifacts=[],
        blockers=['Inherited unit004 density NO_GO remains; reconstructed lamp unavailable'],
        outline_milestone='P1 usable complete-object GT asset editing/save/replay',
        p1_progress='Following previous NEXT with one width-only edit; evaluation not started')
    write_json(UNIT/'STATUS_INITIAL.json', initial)
    write_json(UNIT/'STATUS.json', initial)
    inherited = {}
    for number, name in ((3, 'unit003_baseline'), (4, 'unit004_diagnostic_preview')):
        source = UNIT.parent/f'unit_{number:03}'
        status = json.loads((source/'STATUS.json').read_text())
        folder = UNIT/'inputs'/name
        entries = {}
        for key, filename, original in (
                ('mesh', 'mesh.npz', source/'inputs/lamp_mesh.npz'),
                ('strokes', 'strokes.npz', source/'inputs/selected.npz'),
                ('config', 'config.json', source/'CONFIG.json')):
            destination = folder/filename
            copy(original, destination)
            inherited[str(original)] = sha(original)
            entries[key] = dict(path=str(destination), sha256=sha(destination))
        for filename in ('STATUS.json', 'NEXT.json', 'SEAL.json', 'SHA256_MANIFEST.json'):
            copy(source/filename, UNIT/'previous_snapshot'/name/filename)
            inherited[str(source/filename)] = sha(source/filename)
        manifest = dict(schema='partwise_asset_v1', name=name, **entries,
            provenance=dict(geometry='Authored analytic GT lamp; not RaDe-GS reconstruction',
                part_labels='GT:1 shade,2 stem,3 base', directions='Manual circumferential/axial/cross',
                original_unit=str(source), original_input_sha256={k:v['sha256'] for k,v in entries.items()},
                saved_paths_authoritative=True,
                generator_config_warning='Inherited CONFIG is renderer/style provenance, not a complete recipe for the selected path subset. Never regenerate custom paths from legacy counts.',
                style_sources=['unit003 paired base selection75 seeds/150 paths',
                    'unit004 uniform long axial stem8 paths' if number == 4 else 'inherited48 short axial stem paths'],
                exposed=True, reconstructed_input=False),
            verdict_metadata={k:status[k] for k in ('scientific_verdict', 'claim_status', 'blockers')})
        manifest['verdict_metadata']['source_unit'] = f'unit_{number:03}'
        write_json(UNIT/'inputs'/f'{name}.asset.json', manifest)
    for filename in ('FROZEN_GATE_FAILURES.json', 'VISUAL_REVIEW.json', 'PROTOCOL.json', 'REPORT_ZH.md'):
        copy(PREVIOUS/filename, UNIT/'previous_snapshot'/'unit004_diagnostic_preview'/filename)
        inherited[str(PREVIOUS/filename)] = sha(PREVIOUS/filename)
    copy(PREVIOUS/'figures/failure_orbit_019.png', UNIT/'inherited_failures/failure_orbit_019.png')
    inherited[str(PREVIOUS/'figures/failure_orbit_019.png')] = sha(PREVIOUS/'figures/failure_orbit_019.png')
    write_json(UNIT/'INHERITED_INPUTS.json', inherited)
    protocol = dict(unit='unit_005', created_utc=datetime.now(timezone.utc).isoformat(),
        question='Can a user explicitly load the current complete-lamp diagnostic asset, select shade, edit its width, save, and cold replay while preserving inherited quality verdicts and untouched parts?',
        changed_variable='One shade-only screen width edit1.0->1.5px on unit004418-path preview; no path generation or style sweep',
        input_assets=['unit003_baseline:458paths, separate identity/verdict', 'unit004_diagnostic_preview:418paths, density NO_GO retained'],
        input_sha256={str(p):sha(p) for p in sorted((UNIT/'inputs').rglob('*')) if p.is_file()},
        provenance=dict(geometry='Authored GT lathe mesh868 vertices/1728 faces',
            parts='GT fixed1shade/2stem/3base', directions='Manual circumferential,axial,cross',
            reconstruction='NOT_RECONSTRUCTED', paths='Authoritative saved triangle/barycentric arrays with stable IDs and ink'),
        exposure=dict(train=[], dev=[], diagnostic_views=list(VIEWS), test=[],
            note='Previously exposed GT object/views; software usability validation, no independent held-out science'),
        renderer=dict(backend='unchanged CPU supersampled surface capsules', contour_visibility='visible_centerline',
            resolution=[512,512], supersample=2, depth_tolerance_world=.006,
            widths_before={'1':1.,'2':1.,'3':1.}, widths_after={'1':1.5,'2':1.,'3':1.},
            contour_width_px=.8, structure_width_px=.65,
            limitations=['2x sampled antialiasing','owner-plane extension across width','no near-plane clipping']),
        camera=dict(azimuths=list(VIEWS), elevation=20, distance=4.5, focal_px=600, frame_count_per_state=4),
        controls=['Same mesh/parts,all saved paths/IDs/ink,light,contours,rings,seed; no regeneration required for width',
            'Unit003 named baseline is loaded/rendered separately at az30; it is not the before state for the width metric',
            'Width metric pairs unedited unit004 preview vs same preview edited',
            'All pre-existing failure verdicts retained; no automatic preview promotion'],
        evaluation=dict(primary='Actual full-lamp output, nonzero intended local edit, independent-mask isolation, all-part nonempty hatch coverage, full shape, usable saved-config replay and latency',
            reference='Independent continuous analytic lathe ray intersections; shares GT authored recipe, not candidate triangular depth',
            gates=dict(inside_edit_L1_min_exclusive=10, far_other_fraction_max=.02, far_background_fraction_max=.02,
                band_px=2, hatch_support_ink_threshold=.1, all_three_parts_nonempty=True, object_image_margin_min_px=2),
            controls=['No-edit pair total L1=0 and nonzero gate=false',
                'Blacken16 brightest far-other pixels on no-edit image; far-other leakage>2%; edited injection descriptive only',
                'White-filled3px horizontal image shift increases L1; diagnostic only, no temporal claim'],
            secondary=['Unchanged paths fields incl IDs,part,faces,bary,ink','Only target width config changes',
                'Fresh process using source snapshot and saved edited bundle reproduces all4 PNGs',
                'Required input/output,invalid width,hash mismatch,existing or historical destination refused'],
            visual_go='Four before/after complete-lamp views show perceptible shade thickness change, distinct nonempty three-part styles and complete shape, with no new gross cross-part artifact; inherited imperfections retained',
            no_go='Silent old608 input fallback, wrong destination, lost NO_GO metadata, empty edit, leakage failure or visually unusable output; retain evidence, do not tune',
            inapplicable='Unit004 stem thinning0.15..0.75 ratio is a retained failed prior contract, not a shade-width criterion'),
        cold_replay='Separate process from frozen source snapshot loads saved edited config/mesh/path bundle, renders4 views; no path-generation determinism claim',
        media=dict(edit_frames=24, fps=12, azimuth=30, switch_frame=12, resolution=[512,512],
            operation='12 unchanged before+12 unchanged after images, one actual discrete edit, no tween',
            encoding='FFV1 lossless MKV', validation='Full24-frame decode against actual source PNGs; contact sheet and first/middle/last',
            inherited_orbit_zoom='Unit00424+24 frames retained provenance only; no new orbit/zoom or temporal stability claim'),
        timing='Fresh CLI process wall receipt plus process-entry-to-first-preview/all-previews; loading,validation,save,edit/render included; regeneration empty for width-only; no FPS claim',
        budgets=dict(cpu_affinity=[0,1], numeric_threads=1, ffmpeg_threads=1, gpu=False,
            invocation_max_seconds=590, unit_max_minutes=45, finish_before_jst='2026-10-21T18:38:23+09:00', task_cap_bytes=20*2**30),
        history='Unit004 stem density0.7521462443170939>.75 NO_GO,17 hidden observations,rim-depth outliers,nine-ID temporal limits,old rc1/143/UNKNOWN and round004/012/013 NO_GO retained',
        original_outline_sha256=sha(WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md'),
        brief_sha256=sha(UNIT.parent.parent/'orchestration/BRIEF.md'), previous_next_sha256=sha(PREVIOUS/'NEXT.json'),
        claims=dict(software='PENDING', visual='PENDING', inherited_density='NO_GO', reconstructed_input='BLOCKED', full_P1='PARTIAL', H1_H2='NOT_TESTED'))
    write_json(UNIT/'PROTOCOL.json', protocol)
    write_json(WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit005.json', protocol)
    write_json(UNIT/'RESOURCES_INITIAL.json', resources())


def freeze():
    files=[UNIT/'PROTOCOL.json', UNIT/'INHERITED_INPUTS.json']
    files += [p for p in sorted((UNIT/'inputs').rglob('*')) if p.is_file()]
    names=['common.py','renderer.py','asset_cli.py','test_asset_cli_unit005.py','run_unit005.py',
           'receipt_unit005.py','validate_unit005.py','validate_unit003.py','validate_unit004.py','run_unit002.py']
    files += [WORK/'experiments/partwise_sketch_hatching_v02'/name for name in names]
    files += [WORK/'experiments/partwise_sketch_hatching'/name for name in ('core.py','core_walk_v2.py')]
    for path in files:
        if path.is_relative_to(WORK):
            copy(path, UNIT/'source_snapshot'/path.relative_to(WORK))
    write_json(UNIT/'SOURCE_LOCK.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        files={str(p):sha(p) for p in files}, git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))


def check_lock():
    for path,digest in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():
        assert sha(path)==digest, path
    resources()


def media():
    paths=[]; labels=[]
    for az in VIEWS:
        for name,title in [('baseline','Before | shade1.0px'),('edited','After | shade1.5px')]:
            paths.append(UNIT/'outputs'/name/'renders'/f'{az:03}.png')
            labels.append(f'{title} | az{az}')
    contact(paths,labels,UNIT/'figures/full_lamp_comparison.png',columns=2,thumb=512)
    cfg=json.loads((UNIT/'outputs/edited/config.json').read_text())
    crops=[]; crop_labels=[]
    for az in VIEWS:
        _,parts=core.analytic_reference(cfg['asset'],core.camera(az,20,4.5,512,600))
        for part,pname in ((1,'shade'),(2,'stem'),(3,'base')):
            y,x=np.where(parts==part);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
            for name in ('baseline','edited'):
                dest=UNIT/'figures'/f'{name}_{az:03}_{pname}.png'
                with Image.open(UNIT/'outputs'/name/'renders'/f'{az:03}.png') as im:im.crop(box).save(dest)
                if part==1:crops.append(dest);crop_labels.append(f'{name} shade | az{az}')
    contact(crops,crop_labels,UNIT/'figures/shade_comparison.png',columns=2,thumb=384)
    frames=UNIT/'frames/edit';frames.mkdir(parents=True)
    for i in range(24):
        source=UNIT/'outputs'/('baseline' if i<12 else 'edited')/'renders/030.png'
        copy(source,frames/f'{i:04}.png')
    allframes=sorted(frames.glob('*.png'))
    contact(allframes,[f'Edit frame{i:02}' for i in range(24)],UNIT/'figures/edit_all_frames.png',columns=6,thumb=256)
    contact([allframes[i] for i in (0,12,23)],['First | width1.0','Middle | width1.5','Last | width1.5'],UNIT/'figures/edit_first_middle_last.png',columns=3,thumb=512)
    video=UNIT/'videos/edit.mkv';video.parent.mkdir(parents=True)
    command=[FFMPEG,'-v','error','-threads','1','-filter_threads','1','-framerate','12','-i',str(frames/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(video)]
    result=subprocess.run(command,capture_output=True,timeout=90)
    (UNIT/'runtime/media_encode.log').write_bytes(result.stderr)
    write_json(UNIT/'VIDEO_ENCODING.json',dict(command=command,returncode=result.returncode))
    result.check_returncode()
    from validate_unit004 import audit_video
    write_json(UNIT/'VIDEO_VALIDATION.json',audit_video(UNIT,FFMPEG,'edit',allframes))


def history():
    checks=[]
    for number in (3,4):
        source=UNIT.parent/f'unit_{number:03}'
        seal=json.loads((source/'SEAL.json').read_text())
        manifest=source/'SHA256_MANIFEST.json'
        assert sha(manifest)==seal['manifest_sha256']
        data=json.loads(manifest.read_text())
        for item in data['files']:
            path=Path(data['roots'][item['root']])/item['path']
            actual=sha(path)
            assert actual==item['sha256'], path
        checks.append(dict(unit=str(source),files=len(data['files']),manifest_sha256=sha(manifest),valid=True))
    write_json(UNIT/'HISTORICAL_SEAL_AUDIT.json',dict(checks=checks,valid=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','freeze','media','history'])
    args=parser.parse_args()
    if args.stage not in ('prepare','freeze'):check_lock()
    globals()[args.stage]()
    print(json.dumps(native(dict(stage=args.stage,done=True))))
