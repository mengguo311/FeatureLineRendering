"""Freeze the single permitted fallback after cheap headroom audit."""
from runtime import *
import subprocess

def main():
    assert not (ROOT/'renders').exists()
    audit=json.loads((ROOT/'audit/HEADROOM.json').read_text())
    assert audit['headroom_verdict']=='ZERO_HEADROOM'
    frames=[]
    for i,az in enumerate((30,120,210,300)):
        frames.append(dict(id=f'static_{i:02}',sequence='static',index=i,azimuth=az,elevation=20,distance=4.5,exposure='HISTORICALLY_EXPOSED'))
    for i in range(12):
        frames.append(dict(id=f'orbit_{i:02}',sequence='orbit',index=i,azimuth=7.5+30*i,elevation=20,distance=4.5,exposure='CONSTRUCTION_HOLDOUT_ONLY'))
    for i in range(8):
        frames.append(dict(id=f'zoom_{i:02}',sequence='zoom',index=i,azimuth=52.5,elevation=25,distance=5.2-i/7,exposure='CONSTRUCTION_HOLDOUT_ONLY'))
    p=dict(experiment='experiment_001',status='FROZEN_BEFORE_CANDIDATE_RENDER',
        question='Does toggling already-authored fixed profile rings produce a valid observable structure display on unchanged complete unit010 lamp? H2 not identifiable.',
        choice='Brief-authorized ZERO_HEADROOM fallback: B1-like versus existing B2-like GT structure display only; exactly one diagnostic.',
        source_commit_at_design=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        baseline_acceptance='USER_ACCEPTED_GT_VISUAL_BASELINE_FOR_P2',
        baseline_asset=str(ASSET/'asset.json'),baseline_hashes=json.loads((ROOT/'audit/BASELINE_HASHES.json').read_text()),
        headroom_audit_sha256=sha(ROOT/'audit/HEADROOM.json'),authored_curves_sha256=sha(ROOT/'audit/AUTHORED_CURVES.json'),
        inputs=dict(geometry='Authored GT 868 vertices/1728 faces, 3 disconnected closed components; no reconstruction',
                    labels='Unchanged exact GT1shade2stem3base, not coarse/predicted; no new regionIDs or synthetic noise',
                    paths='Sealed unit010 authoritative434 paths:260shade0deg,24stem,150shortenedbase; no regeneration',
                    curves='864 existing authored mesh profile edges (27.703901806854265 world length), no ordinary-depth or image-edge recovery',
                    contours='View-dependent mesh silhouettes retained identically; physical rings coalesced with contours by existing backend',
                    seeds='Original1729 lineage; unchanged saved paths, inks and IDs',
                    gt_use='GT parts already constrain generator AND renderer semantic ownership; identical across both arms. Independent analytic reference is score-only.',
                    hidden_data='No TEST image edges or labels used to tune method; no external data accessed'),
        arms=[dict(id='B1_like',structure=False,meaning='Hatches plus same contours, existing physical profile rings disabled'),
              dict(id='B2_existing',structure=True,meaning='Exact accepted baseline display with existing authored profile rings')],
        changed_term='Only renderer.render(structure=False/True), no new B2 capability or B3 association implemented',
        not_run=dict(U_S_D='No connected physical part boundary / no crossing headroom; not instantiate false U/S/D success',
                     direction='No style-requested additional guidance tested',H2='UNIDENTIFIABLE_FOR_H2',H1='NOT_TESTED',H3_H4_H5='NOT_TESTED'),
        renderer=dict(backend='unchanged cpu_supersampled_surface_capsules_v1',resolution=[512,512],supersample=2,
                      focal_px=600,depth_tolerance_world=.006,widths_px={'1':1.,'2':1.,'3':1.},contour_width_px=.8,ring_width_px=.65,
                      contour_visibility='visible_centerline',hatch_ink='unchanged stored per-stroke ink, max union',ring_ink=.85,contour_ink=.92,
                      LOD=False,visibility='same surface depth AND GT owner semantic part in both arms',
                      limits=['2x sampled AA','owner-plane extension','no near-plane clipping; fixed cameras stay in front']),
        frames=frames,
        exposure='Four az30/120/210/300 views are exposed. New orbit/zoom cameras chosen from metadata before candidate evidence, construction holdout only; not unseen reconstructed-GS data.',
        evaluation=dict(reference='Independent continuous analytic lathe ray intersection (same authored profile parameters); GT diagnostic oracle',
                        aa_band_px=2,hatch_support_threshold=.1,ring_support_tolerance_px=1.5,centerline_sampling_max_step_world=.002,
                        hiding='Analytic optical z residual>.006 means expected hidden; abs residual<=.006 visible; other residual/outside unknown. Separate AA band; do not score expected hiding as crossing.',
                        boundary='Physical shared part boundary support=0; authored profile ring support reported separately. No mIoU/segmentation gain claim.',
                        metrics=['nonzero total operation L1','hatch and contour exact equality','per-part visible area/support/ink','image darkness retained/change',
                                 'distance-to-hatch median/P95 (empty-area proxy, not true inter-stroke spacing)',
                                 'ring-neighborhood2px hatch overlap (clutter proxy, not crossing count)','independent far wrong-part/background ink in isolated static part hatches',
                                 'expected hidden/visible/AA/unknown authored-ring centerline length and support',
                                 'raw accepted/rejected part/depth renderer diagnostics (fragments include overlaps, not leakage metric)'],
                        gates=dict(nonzero_display_L1_min_exclusive=0,hatch_exact=True,contours_exact=True,part_labels_and_depth_exact=True,
                                   erased_ink_max=0,outside_rendered_ring_delta_max=0,every_part_hatch_support_pixels_min_exclusive=0,
                                   full_shape_margin_px_min=2,baseline_static_png_pixel_exact=True,visible_authored_ring_length_min_exclusive=0),
                        controls=['Actual saved-image no-op fails nonzero gate','Delete-all ink fails retention/support','White-filled3px horizontal drift fails localization/retention',
                                  'Far wrong-part injection16bright pixels responds to independent mask metric','Real walker crossing/GT stop unit test',
                                  'Invalid curve/missing evidence -> UNKNOWN','No KNN connection across separated surfaces'],
                        no_matched_ink_control_reason='No hatch clipping or deletion: byte-identical hatch fields are mandatory; display adds declared ring ink. No benefit claim based on reduced ink.',
                        invalid='Missing support/evidence -> UNKNOWN/UNDETERMINED. Engineering contract failure -> ENGINEERING_INVALID. No global method NO_GO.',
                        inherited_gate='Do not use unit004 .75 density threshold or reopen accepted aesthetics; catastrophic loss of accepted structure is regression'),
        media=dict(fps=6,format='FFV1 lossless MKV',orbit_frames=12,zoom_frames=8,size=[1024,544],
                   note='Each source is an actual per-camera render pair with fixed3D paths. No animated stills, realtime, or full temporal certification claim.',
                   validation='Full decode to RGB; exact match each source PNG, expected frame count, unique frames and SHA256. Native512 panels plus32px labels.'),
        resource=dict(affinity=[0,1],numeric_threads=1,ffmpeg_threads=1,CUDA_VISIBLE_DEVICES='',serial_compute=True,invocation_timeout_seconds=590,
                      output_cap_bytes=8*2**30,root_free_min_bytes=2**30,hdd_free_min_bytes=10*2**30,deadline_utc='2026-10-21T15:40:00Z'),
        stop_rule='Single diagnostic. No tuning/retry of scientific parameters; infrastructure failures retained with original exits. No P3 or unit011 continuation.')
    write_json(DOC/'PROTOCOL.json',p)
    write_json(ROOT/'PROTOCOL.json',p)
    write_json(ROOT/'NEXT.json',dict(automatic_continuation=False,current_recovery_step='Commit frozen protocol, implement/run one display comparison, validate before seal.',
               recommended_next_experiment='One explicitly authored edit-region boundary on a connected portion of the same full lamp, additional regionIDs, oracle-only, frozen independent labels and retained-ink control.',
               reason='Physical parts have zero connected boundary support. Requires a separate future authorization, not executed in experiment001.'))
    update_status('PROTOCOL_READY_TO_COMMIT',scientific_verdict='ZERO_HEADROOM_UNIDENTIFIABLE_FOR_H2')
    print(json.dumps(dict(protocol_sha256=sha(DOC/'PROTOCOL.json'),frames=len(frames),arms=2)))

if __name__=='__main__': main()
