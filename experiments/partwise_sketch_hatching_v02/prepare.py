from common import *
import shutil
from datetime import datetime, timezone

assert not (OUT/'PROTOCOL.json').exists(), 'freeze is immutable'
(OUT/'inputs').mkdir(parents=True, exist_ok=True)
inputs = [OLD/'assets/lamp_mesh.npz', OLD/'strokes/mixed.npz', OLD/'strokes/mixed_shade_edit35.npz']
for p in inputs: shutil.copyfile(p, OUT/'inputs'/p.name)
old_evidence = []
for n in ('001','002','016'):
    old_evidence += list((WORK/f'docs/partwise_sketch_hatching/round_{n}').glob('*.json'))
    old_evidence += [WORK/f'docs/partwise_sketch_hatching/round_{n}/REPORT_ZH.md']
    for name in ('STATUS.json','NEXT.json','SEAL.json','metrics.json'):
        old_evidence.append(OLD.parent/f'round_{n}'/name)
protocol = dict(
 unit='unit_001', frozen_utc=datetime.now(timezone.utc).isoformat(),
 question='Can the inherited complete GT lamp run through a per-fragment CPU curve backend with isolated edits and actual rendered temporal probes?',
 changed_variable='Rendering backend; mesh, mixed paths and ink remain round002. Paired shade edits separately change angle +35 or width 1 to 2 px.',
 geometry_provenance='Authored analytic GT lathe lamp; same 868 vertices/1728 triangles; not RaDe-GS or RGB reconstruction.',
 part_provenance='Authored fixed IDs 1 shade / 2 stem / 3 base, not automatic or click segmentation.',
 direction_provenance='Manual rules: shade circumferential, stem axial, base short cross (+/-40 deg).',
 inputs={str(p):sha(p) for p in inputs}, previous_evidence={str(p):sha(p) for p in old_evidence},
 exposure=dict(train=[], dev=[dict(azimuth=0,elevation=20)],
               diagnostic_views=[30,120,210,300], note='All old geometry/views exposed. New backend outputs are frozen engineering diagnostics, not blind research TEST. No output-driven tuning in this unit.'),
 renderer=dict(name='v02 per-fragment screen capsule CPU raster', resolution=512, supersample=2,
               depth='positive optical z; owner plane intersected at the same raster sample as mesh depth',
               tolerance_world=.006, part_check=True, contour_width_px=.8, structure_width_px=.65,
               downsampling='box supersample coverage; no post-dilation',
               limitations=['owner plane extension at facet joins is approximate', '2x sampling is not analytic area integration', 'no LOD', 'no universal renderer claim']),
 style=dict(seed=1729, baseline_paths='round002 mixed.npz', stroke_count=608, widths_by_part={'1':1.,'2':1.,'3':1.},
            angle_edit=dict(part=1,angle_delta_deg=35), width_edit=dict(part=1,before_px=1,after_px=2),
            ink='fixed inherited per-stroke world-light intensity; no calibration'),
 cameras=dict(focal_px=600,look_at=[0,1.17,0],elevation_deg=20,baseline_distance=4.5),
 videos=dict(fps=12,format='lossless FFV1 mkv; all RGB decode compared exactly',
             orbit=dict(frames=36,azimuth='10*i degrees; i=0..35',distance=4.5),
             zoom=dict(frames=24,azimuth=30,distance='4.8 - .8*cos(2*pi*i/23)'),
             edit=dict(frames=24,azimuth=30,distance=4.5,switch_frame=12,edit='shade angle +35; actual two states, no crossfade')),
 metrics=dict(edit='L1 delta with independent continuous-lathe ray mask; fixed 2px external band; far other/background separately',
              nonzero_target_min=10,far_other_fraction_max=.02,far_background_fraction_max=.02,
              no_edit='same image has zero delta and fails nonzero gate',
              leakage_fault='blacken 8x8 patch centered on a non-target stem pixel; must increase far-other delta',
              anchors='all legal barycentric anchors; fixed other-part IDs, coordinates and input bytes; cold generation digest equals historical snapshot',
              temporal='isolated actual rendered hatch for nine prespecified strokes; independent continuous-lathe geometry, not nearest arbitrary stroke',
              probe_ids=[f'p{p}:seed{i:04d}:layer0' for p in (1,2,3) for i in (0,12,24)],
              probe_cameras=[dict(azimuth=a,elevation=20,distance=4.5) for a in range(0,360,30)],
              probe_samples=41,probe_boundary_px=2,probe_depth_tolerance_world=.006,
              probe_profile=dict(extent_px=2,step_px=.25,presence_threshold=.05),
              temporal_gates=dict(min_eligible_observations_per_part=32,centroid_abs_p95_px_max=1.5,missing_fraction_max=.02),
              faults=dict(drift='shift isolated hatch 3px horizontally with zero fill',dropout='zero isolated hatch; every eligible sample missing'),
              temporal_limits='GT and candidate share authored shape definition; finite selected strokes and orbit only; report short/hidden/overlap/boundary coverage, no whole-object temporal claim from nine IDs'),
 tests=['same-ray footprint occlusion on separated surfaces', 'exact part isolation and nonzero edits', 'deterministic cold regeneration', 'drift/dropout/leakage/no-edit metric sensitivity'],
 visual_gate='Inspect full-object before/after, all video contacts and native crops of all three parts. GO only if complete readable lamp and all three styles visible, with no conspicuous clutter/broken hiding; otherwise retain visual NO_GO even when software gates pass.',
 legacy_width_audit=dict(status='NOT_RUN_NOT_REQUIRED_FOR_SELECTED_BACKEND',reason='Exact planar backend is not used; width edit tested directly on complete lamp; old audit never claimed passed.'),
 budgets=dict(cpu_affinity=[0,1],numeric_threads=1,ffmpeg_threads=1,gpu=False,invocation_seconds=590,unit_minutes=45,
              unit_finish_before_jst='2026-10-21T17:18:36+09:00',output_bytes_max=20*2**30),
 claims=dict(coding='pending',software_contract='pending',visual='pending',reconstructed_input='BLOCKED',H1='NOT_TESTED',H2='NOT_TESTED'))
write_json(OUT/'PROTOCOL.json',protocol)
write_json(WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit001.json',protocol)
write_json(OUT/'STATUS.json',dict(stage='protocol_frozen',execution_state='in_progress',scientific_verdict='UNMEASURED',tests=[],artifacts=['PROTOCOL.json','inputs'],blockers=['No trained lamp reconstruction','Whole-lamp temporal and visual checks pending'],outline_milestone='P1 GT engineering integration',p1_progress='Complete lamp mesh and persistent paths copied byte-for-byte; renderer integration begun.'))
write_json(OUT/'SETUP_NOTES.json',dict(non_scientific_failures=[dict(command='python - <<...',returncode=127,reason='Unqualified python absent; switched to specified read-only venv before scientific execution'),dict(command='rg --files .runtime_p0',returncode=2,reason='Current worktree has no .runtime_p0; reused read-only historical ffmpeg binary')],base_commit='47792c93da76783c1cf857c740e0ad36e25db367',starting_commit='95c82bd9278b611585d28ed8b909fd3b2662abab',base_is_ancestor=True))
print(json.dumps(dict(protocol_sha256=sha(OUT/'PROTOCOL.json'), resources=check_resources())))
