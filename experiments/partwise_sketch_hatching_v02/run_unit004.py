"""One stem-only style replacement on the complete GT lamp; unit004 only."""
from common import *
import argparse
import shutil
import subprocess
import time
from datetime import datetime, timezone
from PIL import Image
from stem_style import STYLE, regenerate_stem
from renderer import render
from run_unit002 import contact, image_array

UNIT001=OUT
PREVIOUS=OUT.parent/'unit_003'
OUT=OUT.parent/'unit_004'

def resources():
    total=sum(p.stat().st_size for p in OUT.parent.rglob('*') if p.is_file())
    root=shutil.disk_usage(WORK).free;hdd=shutil.disk_usage(OUT).free
    assert root>=2**30 and hdd>=10*2**30 and total<20*2**30
    return dict(root_free_bytes=root,hdd_free_bytes=hdd,task_output_bytes=total,
                cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)

def copy(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    assert not dest.exists(),dest
    shutil.copyfile(source,dest)

def inputs():
    a=np.load(OUT/'inputs/lamp_mesh.npz',allow_pickle=False)
    mesh=core.finalize_mesh(a['vertices'],a['faces'],a['parts'])
    return mesh,load_strokes(OUT/'inputs/baseline.npz'),json.loads((OUT/'CONFIG.json').read_text())

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    write_json(OUT/'STATUS_INITIAL.json',dict(stage='stem_style_setup',execution_state='running',
        scientific_verdict='PENDING',tests=[],artifacts=[],blockers=['Inherited whole-object visual NO_GO and missing reconstructed lamp'],
        outline_milestone='P1 complete-object GT software slice',p1_progress='One long/sparse axial stem candidate; no evaluation yet'))
    copy(OUT/'STATUS_INITIAL.json',OUT/'STATUS.json')
    inherited={}
    sources=[(PREVIOUS/'inputs/lamp_mesh.npz',OUT/'inputs/lamp_mesh.npz'),
             (PREVIOUS/'inputs/selected.npz',OUT/'inputs/baseline.npz'),
             (PREVIOUS/'CONFIG.json',OUT/'CONFIG.json')]
    for name in ('NEXT.json','STATUS.json','SEAL.json','PROTOCOL.json','VISUAL_REVIEW.json','REPORT_ZH.md'):
        sources.append((PREVIOUS/name,OUT/'previous_snapshot'/name))
    for az in (30,120,210,300):
        for ext in ('png','npz','json'):
            sources.append((PREVIOUS/'stills'/f'candidate_{az:03}.{ext}',OUT/'stills'/f'baseline_{az:03}.{ext}'))
        sources.append((PREVIOUS/'stills'/f'reference_{az:03}.npz',OUT/'stills'/f'reference_{az:03}.npz'))
    for i in range(24):
        for ext in ('png','npz','json'):
            sources.append((PREVIOUS/'frames/orbit'/f'{i:04}.{ext}',OUT/'frames/baseline'/f'{i:04}.{ext}'))
        sources.append((PREVIOUS/'frames/orbit'/f'reference_{i:04}.npz',OUT/'frames/orbit'/f'reference_{i:04}.npz'))
    for source,dest in sources:
        copy(source,dest);inherited[str(source)]=sha(source)
    write_json(OUT/'INHERITED_INPUTS.json',inherited)
    write_json(OUT/'STYLE.json',STYLE)
    protocol=dict(unit='unit_004',created_utc=datetime.now(timezone.utc).isoformat(),
        question='Does replacing clustered short stem strokes with eight uniformly spaced long axial strokes improve actual complete-lamp readability while preserving isolated control and nonempty hatching?',
        changed_variable='Only stem style placement/count/length:48 random short .55 paths replaced by8 uniform-sector1.35 paths. One compound long/sparse style operation, not a density-only attribution.',
        candidate_count=1,style=STYLE,no_post_evaluation_tuning=True,
        provenance=dict(geometry='Authored analytic GT lamp,868 vertices/1728 faces; not RaDe-GS',parts='GT1 shade/2 stem/3 base',
            directions='Manual circumferential shade, axial stem and short-cross base',
            baseline='unit003 accepted75 base seed pairs,260 shade strokes and48 old stem strokes',
            candidate='Only8 new versioned stem IDs;410 shade/base paths retained exactly; mesh/barycentric anchors; fixed world-light ink formula'),
        inputs={str(OUT/'inputs'/n):sha(OUT/'inputs'/n) for n in ('lamp_mesh.npz','baseline.npz')},
        exposure=dict(train=[],dev=[0],diagnostic_stills=[30,120,210,300],test=[],
            note='One exposed GT object/view family; no blind research TEST. Candidate fixed before DEV and no sweep.'),
        renderer=dict(backend='cpu_supersampled_surface_capsules_v1',contour_visibility='visible_centerline',
            resolution=[512,512],supersample=2,focal_px=600,elevation=20,distance=4.5,
            hatch_width_px=1.,contour_width_px=.8,structure_width_px=.65,depth_tolerance_world=.006,
            limitations=['2x sampled AA','owner-plane extension across hatch width','.4px contour endpoint cap','no near-plane clipping']),
        fixed_controls=['GT mesh/parts,shade260/base150 paths IDs and ink','visible_centerline renderer and fixed light',
            'fixed2px independent analytic-mask band','17 inherited hidden-profile observations, rim-depth failures and nine-ID temporal limitations'],
        evaluation=dict(primary='Actual whole-lamp images, isolated nonzero edit, retained hatch coverage and fully decoded orbit/zoom/edit outputs',
            reference='Independent continuous analytic lathe ray intersections; separate from triangular rendering but shared authored GT recipe',
            gates=dict(inside_edit_L1_min_exclusive=10,far_other_fraction_max=.02,far_background_fraction_max=.02,band_px=2,
                stem_hatch_ink_ratio_min=.15,stem_hatch_ink_ratio_max=.75,stem_hatch_support_ratio_min=.15,
                absolute_stem_mask_support_min=.05,hatch_support_ink_threshold=.1,all_parts_nonempty=True,object_image_margin_min_px=2),
            scope='Apply same numeric gates to4 stills,24 orbit and24 zoom pairs. Deliberate lightness/style change; no equal-darkness claim.',
            controls=['No-edit zero L1 and nonzero gate false','blacken16 brightest far-shade pixels; leakage>.02',
                '3px horizontal actual image drift must increase L1; diagnostic not temporal correspondence'],
            secondary=['410 non-target stroke IDs/anchors/ink fixed','8 stem paths axial length1.35 and attached part2',
                'unchanged contour/ring layers','cold regenerated assets and actual PNG replay'],
            visual_go='Sparse readable nonempty axial stem across all full-lamp views/trajectories; distinct three-part styles, preserved full shape, no new gross defect. Whole-object visual decision separate from stem improvement.',
            no_go='Empty/fragmented stem, visible clutter remains, unexpected other-part changes, frozen numeric failure, or evaluation-driven tuning; retain failure'),
        videos=dict(orbit=dict(frames=24,azimuth='15*i,i0..23',elevation=20,distance=4.5),
            zoom=dict(frames=24,azimuth=30,elevation=20,distance='4.0+1.6*(1-cos(2*pi*i/24))/2'),
            edit=dict(frames=24,azimuth=30,elevation=20,distance=4.5,switch_frame=12,
                      operation='baseline48 stem to candidate8; two actual states; no tween'),
            fps=12,format='FFV1 lossless MKV',decode='All72 frames RGB-exact against512 PNGs; full sheets and first/middle/last'),
        budgets=dict(cpu_affinity=[0,1],numeric_threads=1,ffmpeg_threads=1,gpu=False,invocation_timeout_s=590,
            unit_finish_before_jst='2026-10-21T18:18:56+09:00',unit_max_minutes=45,task_cap_bytes=20*2**30),
        original_outline_sha256=sha(WORK/'docs/partwise_sketch_hatching/experiment_outline_v1.md'),
        brief_sha256=sha(OUT.parent.parent/'orchestration/BRIEF.md'),previous_next_sha256=sha(PREVIOUS/'NEXT.json'),
        historical_failures='Old round001/002 stdout failures,round004/012/013 NO_GO,rim outliers,unit001/002143/UNKNOWN and full visual NO_GO retained; optional planar width audit NOT_RUN',
        claims=dict(software='PENDING',stem_visual='PENDING',whole_object_visual='PENDING',reconstructed_input='BLOCKED',H1_H2='NOT_TESTED'))
    write_json(OUT/'PROTOCOL.json',protocol)
    write_json(OUT/'RESOURCES_INITIAL.json',resources())

def save(folder,name,result,seconds):
    folder=OUT/folder;folder.mkdir(parents=True,exist_ok=True)
    Image.fromarray(image_array(result['image'])).save(folder/f'{name}.png')
    np.savez_compressed(folder/f'{name}.npz',**{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
    write_json(folder/f'{name}.json',dict(seconds=seconds,camera=result['camera'],diagnostics=result['diagnostics']))

def draw(mesh,strokes,cfg,az,distance=4.5):
    t=time.perf_counter();result=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=distance)
    return result,time.perf_counter()-t

def dev():
    mesh,baseline,cfg=inputs()
    candidate,record=regenerate_stem(mesh,baseline,cfg,json.loads((OUT/'STYLE.json').read_text()))
    core.save_strokes(OUT/'inputs/selected.npz',candidate);write_json(OUT/'GENERATION.json',record)
    for name,strokes in [('baseline',baseline),('candidate',candidate)]:
        result,seconds=draw(mesh,strokes,cfg,0);save('dev',name,result,seconds)
    contact([OUT/'dev'/f'{name}.png' for name in ('baseline','candidate')],
        ['Baseline48 short stem | DEV az0','Candidate8 long stem | DEV az0'],OUT/'figures/dev_comparison.png',columns=2,thumb=512)

def freeze():
    assert (OUT/'DEV_DECISION.json').exists()
    paths=[OUT/n for n in ('PROTOCOL.json','CONFIG.json','STYLE.json','DEV_DECISION.json','INHERITED_INPUTS.json','GENERATION.json')]
    paths+=list((OUT/'inputs').glob('*.npz'))
    paths += [WORK/'experiments/partwise_sketch_hatching'/n for n in ('core.py','core_walk_v2.py')]
    paths += [WORK/'docs/partwise_sketch_hatching/round_001/PROTOCOL.json']
    names=['common.py','renderer.py','run_unit002.py','validate_unit003.py','stem_style.py','run_unit004.py','test_stem_unit004.py','receipt_unit004.py','validate_unit004.py']
    paths += [WORK/'experiments/partwise_sketch_hatching_v02'/n for n in names]
    for path in paths:
        if path.is_relative_to(WORK):copy(path,OUT/'source_snapshot'/path.relative_to(WORK))
    mapping={str(p):sha(p) for p in paths};mapping.update(json.loads((OUT/'INHERITED_INPUTS.json').read_text()))
    write_json(OUT/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files=mapping,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))

def check_lock():
    for path,digest in json.loads((OUT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==digest,path
    resources()

def stills():
    mesh,baseline,cfg=inputs();candidate=load_strokes(OUT/'inputs/selected.npz')
    paths=[];labels=[];crops=[];crop_labels=[]
    for az in (30,120,210,300):
        result,seconds=draw(mesh,candidate,cfg,az);save('stills',f'candidate_{az:03}',result,seconds)
        parts=np.load(OUT/'stills'/f'reference_{az:03}.npz')['parts']
        for name in ('baseline','candidate'):
            path=OUT/'stills'/f'{name}_{az:03}.png';paths.append(path);labels.append(f'{name} | az {az}')
            for part,pname in ((1,'shade'),(2,'stem'),(3,'base')):
                y,x=np.where(parts==part);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
                dest=OUT/'figures'/f'{name}_{az:03}_crop_{pname}.png'
                with Image.open(path) as im:im.crop(box).save(dest)
                if part==2:crops.append(dest);crop_labels.append(f'{name} stem | az {az}')
    contact(paths,labels,OUT/'figures/full_lamp_comparison.png',columns=2,thumb=512)
    contact(crops,crop_labels,OUT/'figures/stem_comparison.png',columns=4,thumb=240)

def sequence(name,start,stop):
    mesh,baseline,cfg=inputs();candidate=load_strokes(OUT/'inputs/selected.npz')
    for i in range(start,stop):
        az=15*i if name=='orbit' else 30
        distance=4.5 if name=='orbit' else 4.+.8*(1-np.cos(2*np.pi*i/24))
        result,seconds=draw(mesh,candidate,cfg,az,distance);save(f'frames/{name}',f'{i:04}',result,seconds)
        if name=='zoom':
            result,seconds=draw(mesh,baseline,cfg,az,distance);save('frames/zoom_baseline',f'{i:04}',result,seconds)
            depth,parts=core.analytic_reference(cfg['asset'],core.camera(az,20,distance,512,600))
            np.savez_compressed(OUT/'frames/zoom'/f'reference_{i:04}.npz',depth=depth,parts=parts)
        print(f'{name} {i+1}/24',flush=True);resources()

def encode(name):
    dest=OUT/'videos'/f'{name}.mkv';dest.parent.mkdir(exist_ok=True)
    command=[FFMPEG,'-v','error','-y','-threads','1','-filter_threads','1','-framerate','12','-i',str(OUT/'frames'/name/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(dest)]
    result=subprocess.run(command,capture_output=True,timeout=90)
    (OUT/'runtime'/f'{name}_encode.log').write_bytes(result.stderr)
    write_json(OUT/f'VIDEO_{name}.json',dict(command=command,returncode=result.returncode,frames=24,fps=12,size=[512,512]));assert result.returncode==0

def media():
    for i in range(24):copy(OUT/'stills'/f'{"baseline" if i<12 else "candidate"}_030.png',OUT/'frames/edit'/f'{i:04}.png')
    for name in ('orbit','zoom','edit'):
        paths=[OUT/'frames'/name/f'{i:04}.png' for i in range(24)]
        labels=[f'{name.title()} {i:02}' for i in range(24)]
        contact(paths,labels,OUT/'figures'/f'{name}_all_frames.png',columns=6,thumb=256)
        contact([paths[i] for i in (0,12,23)],[labels[i] for i in (0,12,23)],OUT/'figures'/f'{name}_first_middle_last.png',columns=3,thumb=512)
        trajectory=[dict(frame=i,azimuth=15*i if name=='orbit' else 30,elevation=20,
            distance=float(4.+.8*(1-np.cos(2*np.pi*i/24))) if name=='zoom' else 4.5,
            stem_count=48 if name=='edit' and i<12 else 8,
            asset_sha256=sha(OUT/'inputs'/('baseline.npz' if name=='edit' and i<12 else 'selected.npz'))) for i in range(24)]
        write_json(OUT/f'TRAJECTORY_{name}.json',trajectory);encode(name)

def replay():
    mesh,baseline,cfg=inputs()
    candidate,record=regenerate_stem(mesh,baseline,cfg,json.loads((OUT/'STYLE.json').read_text()))
    result,seconds=draw(mesh,candidate,cfg,30)
    old,old_seconds=draw(mesh,baseline,cfg,30)
    report=dict(regenerated_digest_exact=core.stroke_digest(candidate)==core.stroke_digest(load_strokes(OUT/'inputs/selected.npz')),
        candidate_png_exact=np.array_equal(image_array(result['image']),np.array(Image.open(OUT/'stills/candidate_030.png'))),
        baseline_png_exact=np.array_equal(image_array(old['image']),np.array(Image.open(OUT/'stills/baseline_030.png'))),
        generation_seconds=record['generation_seconds'],candidate_render_seconds=seconds,
        regenerate_and_render_seconds=record['generation_seconds']+seconds,baseline_render_seconds=old_seconds,
        scope='Fresh process from frozen source snapshot, regenerate only8 stem paths and redraw actual full lamp')
    write_json(OUT/'COLD_REPLAY.json',report);assert all(report[k] for k in ('regenerated_digest_exact','candidate_png_exact','baseline_png_exact'))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','dev','freeze','stills','orbit','zoom','media','replay'])
    p.add_argument('--start',type=int,default=0);p.add_argument('--stop',type=int,default=24);a=p.parse_args()
    if a.stage not in ('prepare','dev','freeze'):check_lock()
    if a.stage in ('orbit','zoom'):sequence(a.stage,a.start,a.stop)
    else:globals()[a.stage]()

if __name__=='__main__':main()
