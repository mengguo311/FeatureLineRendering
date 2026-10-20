"""Freeze one translation sequence before any sequence rendering."""
import round015_common as c
import json
p=json.loads((c.W/'docs/partwise_sketch_hatching/round_014/PROTOCOL.json').read_text())
spec=p['cases'][1]
protocol={
 'round':'round_015','authority':'Only round014 Astra NEXT; outline 5.8,9.5,14.3',
 'hypothesis':'Fixed planar ribbons under subpixel camera translation follow independent analytic area and correspondence without extra rendered drift/dropout.',
 'study_type':'New frozen sequence of exposed analytic GT fixture; finite planar diagnostic, not blind object generalization',
 'camera':p['camera'],'geometry':p['geometry'],'case':spec,
 'trajectory':[{'frame':i,'eye':[i/64.,-i/128.,0.],'R':[[1,0,0],[0,1,0],[0,0,1]]} for i in range(12)],
 'style':{'ink':.8,'width_output_px':1.,'width_high_px':2.,'scale':2,'depth_separation':.006,'cleanup':1e-12,'quantization':'uint8 truncation then PIL LANCZOS'},
 'reference':'Unchanged physical_area_reference.py piecewise linear cross-section area; independently shifted prescribed projection/bounds at respective z; no core.project or candidate quantities',
 'correspondence':{'samples':257,'rule':'Equal arclength midpoint samples of the fixed straight world path, indices preserved across all frames','margin_output_px':2.,'eligibility':'Analytic centerline inside owner, outside foreground; endpoint, owner, foreground and image boundary distance >=2 output px; all-frame persistent intersection. No candidate-dependent exclusions.','output_mapping':'(high + 0.5) / 2 - 0.5','profile_offsets':[-2.+i/8. for i in range(33)],'interpolation':'bilinear, constant-zero outside','presence_peak_min':8/255.,'min_persistent_samples':32,'min_persistent_fraction':.15,'localization':'Ink-weighted normal-profile centroid relative to known projected centerline; missing flagged, never silently excluded'},
 'gates':{'area_max_abs':1e-10,'area_total_mass_abs':1e-8,'reference_integral_sum_abs':1e-8,'projection_max_abs':1e-12,'quantized_exact':True,'final_exact':True,'full_frame_temporal_residual_max_uint8':0,'extra_profile_centroid_max_px':1e-12,'extra_profile_motion_max_px':1e-12,'extra_dropout_samples':0,'reference_profile_all_present':True,'world_inputs_exact_unchanged':True,'historical_regression_exact':True},
 'injections':{'drift':{'frame':5,'shift_output_pixels':[3,0],'source':'independent reference final sequence','required_full_frame_L1_gt':0,'required_centroid_max_gt_px':.5},'dropout':{'frame':7,'operation':'replace complete ink frame with zero','source':'independent reference final sequence','required_missing_fraction':1.,'required_full_frame_L1_gt':0}},
 'video':{'frames':12,'fps':4,'format':'lossless FFV1 mkv','panels':'candidate and reference full views enlarged 4x nearest; English labels','decode':'all frames; exact RGB against encoded source panels; distinct frames >=2'},
 'resources':{'cpu_affinity':[0,1],'threads_max':2,'GPU':False,'serial_compute':True,'invocation_limit_seconds':600,'round_budget_minutes':20,'deadline_jst':'2026-10-21T07:10:35.316830+09:00'},
 'fixed_sources':{n:c.sha(c.W/'experiments/partwise_sketch_hatching'/n) for n in ['planar_fragments_exact.py','physical_area_reference.py','core.py','mesh_attachment.py','round010_fixture.py']},
 'prior_next_sha256':c.sha(c.P/'NEXT.json'),
 'limits':['Finite straight ribbon, coplanar fronto-parallel owners, separated constant-depth scene triangles only.','No renderer changes, sweeps, threshold tuning, lamp integration, H2 or training.','General orbit, AA quality, effective line width, P1 and RaDe-GS reconstruction remain unproven.','Any frozen sequence gate failure remains NO_GO; invalid reference/control/replay is ENGINEERING_INVALID.']}
c.write(c.D/'PROTOCOL.json',protocol)
c.status('protocol_frozen_awaiting_implementation',artifacts=[str(c.D/'PROTOCOL.json'),'STATUS.json','NEXT.json'])
print(json.dumps({'frames':12,'prior_seal':c.verify_prior(),'resources':c.resources()}))
