"""One base-only paired density edit on the complete inherited GT lamp."""
from common import *
import argparse
import shutil
import subprocess
import time
from datetime import datetime, timezone
from PIL import Image, ImageDraw
from base_density import select_base_pairs
from renderer import render
from run_unit002 import contact, image_array

UNIT001 = OUT
PREVIOUS = OUT.parent/'unit_002'
OUT = OUT.parent/'unit_003'


def resources():
    total = sum(p.stat().st_size for p in OUT.parent.rglob('*') if p.is_file())
    root = shutil.disk_usage(WORK).free; hdd = shutil.disk_usage(OUT).free
    assert root >= 2**30 and hdd >= 10*2**30 and total < 20*2**30
    return dict(root_free_bytes=root, hdd_free_bytes=hdd, task_output_bytes=total,
                cpu_affinity=sorted(os.sched_getaffinity(0)), numeric_threads=1, gpu=False)


def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), destination
    shutil.copyfile(source, destination)


def inputs():
    cfg = json.loads((OUT/'CONFIG.json').read_text())
    a = np.load(OUT/'inputs/lamp_mesh.npz', allow_pickle=False)
    mesh = core.finalize_mesh(a['vertices'], a['faces'], a['parts'])
    return mesh, load_strokes(OUT/'inputs/mixed.npz'), cfg


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT/'STATUS_INITIAL.json', dict(stage='base_pair_density_setup', execution_state='running',
        scientific_verdict='PENDING', tests=[], artifacts=[], blockers=['Inherited full visual NO_GO; reconstructed lamp unavailable'],
        outline_milestone='P1 whole-object GT engineering slice', p1_progress='One base-only density candidate; no evaluation yet'))
    copy(OUT/'STATUS_INITIAL.json', OUT/'STATUS.json')
    for name in ('lamp_mesh.npz', 'mixed.npz'):
        copy(UNIT001/'inputs'/name, OUT/'inputs'/name)
    _, _, cfg = load_inputs()
    cfg['renderer']['contour_visibility'] = 'visible_centerline'
    write_json(OUT/'CONFIG.json', cfg)
    inherited = {}
    for name in ('NEXT.json', 'STATUS.json', 'SEAL.json', 'PROTOCOL.json', 'VISUAL_REVIEW.json', 'HIDDEN_PROFILE_REVIEW.json'):
        source = PREVIOUS/name; copy(source, OUT/'previous_snapshot'/name); inherited[str(source)] = sha(source)
    # Baseline output bytes were already evaluated and remain explicitly exposed.
    for az in (30, 120, 210, 300):
        for ext in ('png', 'npz', 'json'):
            source = PREVIOUS/'stills'/f'base_{az:03}.{ext}'
            copy(source, OUT/'stills'/f'baseline_{az:03}.{ext}'); inherited[str(source)] = sha(source)
        source = PREVIOUS/'stills'/f'reference_{az:03}.npz'
        copy(source, OUT/'stills'/source.name); inherited[str(source)] = sha(source)
    for i in range(24):
        for ext in ('png', 'npz', 'json'):
            source = PREVIOUS/'frames/orbit'/f'{i:04}.{ext}'
            copy(source, OUT/'frames/baseline'/source.name); inherited[str(source)] = sha(source)
        source = PREVIOUS/'frames/orbit'/f'reference_{i:04}.npz'
        copy(source, OUT/'frames/orbit'/source.name); inherited[str(source)] = sha(source)
    write_json(OUT/'INHERITED_INPUTS.json', inherited)
    protocol = dict(unit='unit_003', created_utc=datetime.now(timezone.utc).isoformat(),
        question='Can paired nested base thinning reduce actual whole-lamp crosshatch crowding without emptying the base or editing other parts?',
        changed_variable='Retain75 of150 existing base seed pairs; each retained pair keeps both original layers, paths and ink.',
        candidate_count=1, selection='Euclidean farthest-seed order, seed0000 first, lexical ID tie-break, first75; no geodesic or physical Poisson claim',
        no_post_evaluation_tuning=True,
        provenance=dict(geometry='Authored analytic GT lathe mesh;868 vertices/1728 faces; not reconstructed',
                        parts='GT1 shade/2 stem/3 base', directions='Manual circumferential/axial/short-cross',
                        paths='Original608 mesh/barycentric paths from round002/unit001; seed1729; kept paths never regenerated'),
        inputs={str(OUT/'inputs'/n):sha(OUT/'inputs'/n) for n in ('lamp_mesh.npz','mixed.npz')},
        exposure=dict(train=[], dev=[0], diagnostic_stills=[30,120,210,300], orbit='24 frames azimuth15*i, i0..23',
                      test=[], note='All geometry and view family exposed. Engineering diagnostic, no held-out research claim.'),
        renderer=dict(backend='cpu_supersampled_surface_capsules_v1', contour_visibility='visible_centerline',
                      resolution=[512,512], supersample=2, focal_px=600, elevation=20, distance=4.5,
                      depth_tolerance_world=.006, contour_width_px=.8, structure_width_px=.65, hatch_width_px=1,
                      limits=['2x sampled AA', 'owner plane extended across hatch width', '.4px contour cap at occlusion endpoints', 'no near-plane clipping']),
        fixed_controls=['shade/stem paths, IDs and ink', 'all retained base paths, IDs and ink', 'mesh, geometry, labels, light, seed',
                        'renderer and contour/ring rules', '2px independent-mask band', '17 inherited hidden-profile observations and nine-ID coverage limitations'],
        evaluation=dict(reference='Independent continuous analytic lathe ray intersections from same authored shape; independent implementation, shared GT recipe',
            actual_edit=dict(target=3, inside_delta_min=10, far_other_fraction_max=.02, far_background_fraction_max=.02, band_px=2),
            base_coverage=dict(hatch_only=True, ink_threshold=.1, ink_ratio_min=.35, ink_ratio_max=.8,
                               support_ratio_min=.35, absolute_mask_support_min=.05, each_direction_layer_ink_min_exclusive=0,
                               note='Deliberate density/ink change, not equal-darkness comparison; guards are engineering bounds.'),
            controls=['no edit total delta0 and nonzero gate false','blacken16 brightest far-stem pixels; far-other leakage must exceed.02',
                      '3px horizontal actual raster drift increases L1 diagnostic; not temporal correspondence proof'],
            secondary=['non-target IDs/coordinates/ink fixed', 'retained paths unchanged', 'both layer IDs present',
                       'contour/ring layers unchanged','monotone hatch/image change','cold saved-asset selection/render replay'],
            orbit='All24 actual candidate frames, matched inherited baseline; report every-frame edit/coverage and frame differences descriptively',
            video=dict(orbit_frames=24, edit_frames=24, fps=12, format='FFV1 lossless mkv',
                       edit='az30 fixed; first12 baseline and last12 selected75; two actual configurations, no tween',
                       decode='Full RGB decode every frame exactly against PNG; all-frame and first/middle/last contact sheets'),
            visual_go='Four complete-lamp pairs plus full orbit show less base crowding, visible two-layer cross style and shape, no emptying or new gross defects. Whole-object GO remains separate and fails if stem clutter persists.',
            no_go='Any frozen gate failure retained without retuning; aesthetic failure can coexist with valid software.'),
        budgets=dict(cpu_affinity=[0,1], numeric_threads=1, ffmpeg_threads=1, gpu=False, invocation_timeout_s=590,
                     unit_finish_before_jst='2026-10-21T18:01:11+09:00', unit_max_minutes=45, task_cap_bytes=20*2**30),
        original_outline_sha256=sha(WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md'),
        brief_sha256=sha(OUT.parent.parent/'orchestration/BRIEF.md'), previous_next_sha256=sha(PREVIOUS/'NEXT.json'),
        historical_failures='round001/002 stdout failures, round004/012/013 NO_GO, rim-depth outliers, unit001/002 full visual NO_GO and143/UNKNOWN retained read-only',
        claims=dict(software='PENDING', base_visual='PENDING', whole_object_visual='PENDING; inherited NO_GO', reconstructed_input='BLOCKED', H1_H2='NOT_TESTED'))
    write_json(OUT/'PROTOCOL.json', protocol)
    write_json(OUT/'RESOURCES_INITIAL.json', resources())


def save(folder, name, result, seconds):
    folder = OUT/folder; folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image_array(result['image'])).save(folder/f'{name}.png')
    np.savez_compressed(folder/f'{name}.npz', **{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
    write_json(folder/f'{name}.json', dict(seconds=seconds, camera=result['camera'], diagnostics=result['diagnostics']))


def draw(mesh, strokes, cfg, az):
    start=time.perf_counter(); result=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=4.5)
    return result, time.perf_counter()-start


def dev():
    mesh, strokes, cfg = inputs()
    selected, selection = select_base_pairs(mesh, strokes, cfg, 75)
    core.save_strokes(OUT/'inputs/selected.npz', selected)
    write_json(OUT/'SELECTION.json', selection)
    for name, paths in [('baseline',strokes),('candidate',selected)]:
        result, seconds=draw(mesh,paths,cfg,0); save('dev',name,result,seconds)
    contact([OUT/'dev'/f'{name}.png' for name in ('baseline','candidate')],
            ['Baseline150 pairs | DEV az0','Candidate75 pairs | DEV az0'],OUT/'figures/dev_comparison.png',columns=2,thumb=512)


def freeze():
    assert (OUT/'DEV_DECISION.json').exists()
    paths=[OUT/'PROTOCOL.json', OUT/'CONFIG.json', OUT/'SELECTION.json', OUT/'DEV_DECISION.json', OUT/'INHERITED_INPUTS.json']
    paths += sorted((OUT/'inputs').glob('*.npz'))
    paths += [WORK/'experiments/partwise_sketch_hatching'/n for n in ('core.py','core_walk_v2.py')]
    paths += [WORK/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json']
    paths += [WORK/'experiments/partwise_sketch_hatching_v02'/n for n in ('common.py','renderer.py','run_unit002.py','base_density.py','run_unit003.py','test_density_unit003.py','receipt_unit003.py','validate_unit003.py')]
    for path in paths:
        if path.is_relative_to(WORK): copy(path,OUT/'source_snapshot'/path.relative_to(WORK))
    mapping={str(p):sha(p) for p in paths}
    mapping.update(json.loads((OUT/'INHERITED_INPUTS.json').read_text()))
    write_json(OUT/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files=mapping,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))


def check_lock():
    for path,digest in json.loads((OUT/'SOURCE_LOCK.json').read_text())['files'].items():
        assert sha(path)==digest,path
    resources()


def stills():
    mesh, strokes, cfg=inputs(); selected=load_strokes(OUT/'inputs/selected.npz')
    paths=[];labels=[]; crops=[];crop_labels=[]
    for az in (30,120,210,300):
        result,seconds=draw(mesh,selected,cfg,az);save('stills',f'candidate_{az:03}',result,seconds)
        for layer in (0,1):
            layer_strokes=[s for s in selected if s['part']==3 and s['layer']==layer]
            lr,ls=draw(mesh,layer_strokes,cfg,az);save('stills',f'layer{layer}_{az:03}',lr,ls)
        parts=np.load(OUT/'stills'/f'reference_{az:03}.npz')['parts']
        for name in ('baseline','candidate'):
            path=OUT/'stills'/f'{name}_{az:03}.png';paths.append(path);labels.append(f'{name} | az {az}')
            for part,pname in ((1,'shade'),(2,'stem'),(3,'base')):
                y,x=np.where(parts==part);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
                dest=OUT/'figures'/f'{name}_{az:03}_crop_{pname}.png'
                with Image.open(path) as im:im.crop(box).save(dest)
                if part==3:crops.append(dest);crop_labels.append(f'{name} base | az {az}')
        print(f'stills {az} complete',flush=True)
    contact(paths,labels,OUT/'figures/full_lamp_comparison.png',columns=2,thumb=512)
    contact(crops,crop_labels,OUT/'figures/base_comparison.png',columns=2,thumb=320)


def encode(name):
    dest=OUT/'videos'/f'{name}.mkv';dest.parent.mkdir(exist_ok=True)
    command=[FFMPEG,'-v','error','-y','-threads','1','-filter_threads','1','-framerate','12','-i',str(OUT/'frames'/name/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(dest)]
    run=subprocess.run(command,capture_output=True,timeout=90)
    (OUT/'runtime'/f'{name}_encode.log').write_bytes(run.stderr)
    write_json(OUT/f'VIDEO_{name}.json',dict(command=command,returncode=run.returncode,frames=24,fps=12,size=[512,512]))
    assert run.returncode==0


def orbit(start, stop):
    mesh,strokes,cfg=inputs();selected=load_strokes(OUT/'inputs/selected.npz')
    for i in range(start,stop):
        result,seconds=draw(mesh,selected,cfg,15*i);save('frames/orbit',f'{i:04}',result,seconds)
        print(f'orbit {i+1}/24',flush=True);resources()


def media():
    folder=OUT/'frames/orbit'
    contact([folder/f'{i:04}.png' for i in range(24)],[f'Orbit {i:02} | az {15*i}' for i in range(24)],OUT/'figures/orbit_all_frames.png',columns=6,thumb=256)
    contact([folder/f'{i:04}.png' for i in (0,12,23)],[f'Orbit {i:02} | az {15*i}' for i in (0,12,23)],OUT/'figures/orbit_first_middle_last.png',columns=3,thumb=512)
    trajectory=[]
    for i in range(24):
        trajectory.append(dict(frame=i,azimuth=15*i,elevation=20,distance=4.5,selected_asset_sha256=sha(OUT/'inputs/selected.npz')))
        copy(OUT/'stills'/f'{"baseline" if i<12 else "candidate"}_030.png',OUT/'frames/edit'/f'{i:04}.png')
    write_json(OUT/'TRAJECTORY_orbit.json',trajectory)
    write_json(OUT/'TRAJECTORY_edit.json',[dict(frame=i,azimuth=30,elevation=20,distance=4.5,base_pairs=150 if i<12 else 75) for i in range(24)])
    contact([OUT/'frames/edit'/f'{i:04}.png' for i in range(24)],[f'Edit {i:02} | pairs{150 if i<12 else 75}' for i in range(24)],OUT/'figures/edit_all_frames.png',columns=6,thumb=192)
    contact([OUT/'frames/edit'/f'{i:04}.png' for i in (0,12,23)],[f'Edit {i:02}' for i in (0,12,23)],OUT/'figures/edit_first_middle_last.png',columns=3,thumb=512)
    for name in ('orbit','edit'):encode(name)


def replay():
    mesh,strokes,cfg=inputs();start=time.perf_counter()
    selected,selection=select_base_pairs(mesh,strokes,cfg,75)
    result,seconds=draw(mesh,selected,cfg,30)
    saved=np.asarray(Image.open(OUT/'stills/candidate_030.png'))
    baseline,baseline_seconds=draw(mesh,strokes,cfg,30)
    original=np.asarray(Image.open(OUT/'stills/baseline_030.png'))
    report=dict(selected_digest_exact=core.stroke_digest(selected)==core.stroke_digest(load_strokes(OUT/'inputs/selected.npz')),
                candidate_png_exact=np.array_equal(image_array(result['image']),saved), baseline_png_exact=np.array_equal(image_array(baseline['image']),original),
                selection_seconds=selection['selection_seconds'],candidate_render_seconds=seconds,baseline_render_seconds=baseline_seconds,
                selection_and_candidate_render_seconds=selection['selection_seconds']+seconds,
                scope='Cold process selection from saved original608 paths; no path walking/regeneration was required by this density operation.')
    write_json(OUT/'COLD_REPLAY.json',report);assert report['selected_digest_exact'] and report['candidate_png_exact'] and report['baseline_png_exact']


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','dev','freeze','stills','orbit','media','replay'])
    parser.add_argument('--start',type=int,default=0);parser.add_argument('--stop',type=int,default=24);args=parser.parse_args()
    if args.stage not in ('prepare','dev','freeze'):check_lock()
    if args.stage=='orbit':orbit(args.start,args.stop)
    else:globals()[args.stage]()


if __name__=='__main__':main()
