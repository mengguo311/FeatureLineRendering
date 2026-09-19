"""Administrative preregistration freeze. No images or method outputs are read."""
import hashlib,json,pathlib,subprocess,datetime,collections
R=pathlib.Path(__file__).resolve().parents[3]; O=R/'out/curve_correspondence_foundation'; P=R/'out/multiscene_foundation_corrected'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(name,x):
 p=O/name;b=(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();p.write_bytes(b);pathlib.Path(str(p)+'.sha256').write_text(hashlib.sha256(b).hexdigest()+'\n')
old=json.loads((P/'config.json').read_text());manifest=json.loads((P/'MANIFEST.json').read_text());records=manifest['files'];print('manifest schema',type(records).__name__)
if isinstance(records,list): records={x['path']:x for x in records}
cfg=dict(version=1,branch='curve-correspondence-foundation',start_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),formulation='unique_epipolar_intersection_monotone_triangle_tracks_bounded_polyline_BA',prereg_sha256=sha(O/'PREREG.md'),literature_sha256=sha(O/'LITERATURE.md'),inherited_config_sha256=sha(P/'config.json'),splits=old['splits'],scene_order=['lego','chair'],detector=old['detector'],sampling=old['sampling'],native=old['native'],frozen_posteriors=old['frozen_posteriors'],scenes={})
cfg.update(extraction=dict(min_length=12.,max_length=96.,sample_step=2.,corner_window=4.,corner_degrees=45.,corner_suppression=6.),matching=dict(pair_angle_min=5.,pair_angle_max=110.,endpoint_epipolar_tolerance=1.,intersection_merge_arc=2.,min_crossing_angle=15.,source_gap=4.,target_gap=8.,slope_min=.25,slope_max=4.,min_coverage=.6,min_arc=12.,min_samples=7,descriptor_sigma=1.2,normal_offsets=[2.,4.],descriptor_rms_max=.20,coverage_cost=.10,mutual_arc_p90_max=2.,margin_min=.025,ratio_max=.8,cycle_arc_p90_max=2.),fit=dict(knot_step=4.,min_knots=4,min_arc=12.,inlier_px=2.,min_views=3,baseline_max_min=20.,baseline_second_min=10.,huber=1.,max_nfev=100,anchor_weight=.2,second_difference_weight=.05,local_arc_window=2.,bound_delta=2.,rms_max=1.5,tangent_median_max=15.,gs_knot_fraction=.8),controls=dict(shift_pixels=32,random_seed=20260919,pairwise_min_views=2),gates=dict(min_tracks=12,centroid_separation_delta=4.,projected_length_F_min=300.,spatial_cell_px=32,min_spatial_cells=6,min_spatial_views=4,four_view_fraction_min=.25,fit_rms_max=1.5,fit_tangent_median_max=15.,prediction_median_px=1.5,prediction_p90_px=3.,prediction_median_angle=15.,prediction_p90_angle=30.,joint_px=2.,joint_angle=20.,joint_fraction=.8,C_track_coverage=.8,DEV_track_coverage=.5,min_prediction_views=2,repeat_coverage=.8,repeat_median_delta=.5,repeat_p90_delta=1.,repeat_median_angle=10.,repeat_p90_angle=20.,repeat_length_change=.15,match_max_delta=2.,match_angle=20.,match_margin_delta=.5,null_length_ratio=1/3,ablation_length_ratio=.8,ablation_joint_slack=.05,gs_error_reduction=.25,gs_supported_loss=.10,gs_supported_gain=.20,gs_precision_loss=.02),visuals=dict(old['visuals'],track_cardinality=12,review_seed=20260919),budget=dict(scientific_seconds_per_scene=28800),manual=dict(status='PENDING_INDEPENDENT_REVIEW',independent_review_count=0))
inputs={}
for s in old['scene_order']:
 e=json.loads((P/f'scenes/{s}/eligibility.json').read_text()); cams={k:v for k,v in old['scenes'][s]['cameras'].items() if k in [f'train_{i:03d}' for i in old['splits']['TRAIN']+old['splits']['DEV']]}
 cfg['scenes'][s]=dict(eligibility=e,cameras=cams)
 for c in cams.values():inputs[c['path']]=dict(sha256=c['sha256'],kind='approved_reference',scene=s)
 for rel in [f'scenes/{s}/eligibility.json',f'annotations/{s}_internal.json']:
  inputs[str(P/rel)]=dict(sha256=sha(P/rel),kind='evaluation_metadata')
 if s not in cfg['scene_order']:continue
 assets=['seed_1729']+(['seed_2718'] if e['route_a'] else [])+e['qualified_doses'];cfg['scenes'][s]['assets']=assets
 for asset in assets:
  for i in old['splits']['TRAIN']:
   rel=f'local/{s}/layers/{asset}/view_{i:03d}.npz'
   # Reuse complete archived inventory; actual bytes verified before use and at end.
   if asset!='seed_1729' and i not in old['splits']['F']:continue
   inputs[str(P/rel)]=dict(sha256=records[rel]['sha256'],kind='calibrated_area_layers',scene=s,asset=asset,view=i)
 for rel in [f'local/{s}/F/pca.json',f'evaluation/{s}/visual/DEV_render_equivalence.json']:
  inputs[str(P/rel)]=dict(sha256=sha(P/rel),kind='evaluation_reference')
for x in old['frozen_posteriors'].values():inputs[x['path']]=dict(sha256=x['sha256'],kind='frozen_checkpoint')
for p in [P/n for n in ['PREREG.md','RESULTS.md','results.json','VERIFICATION.json','EXECUTION_NOTES.md','config.json','input_hashes.json','MANIFEST.json','PRESERVED_INPUT_VERIFICATION.json']]+[pathlib.Path('/home/u00134/codex_astra_point_feature_foundation_decision.md'),pathlib.Path('/home/u00134/codex_astra_multiscene_foundation_corrected_report.md')]:inputs[str(p)]=dict(sha256=sha(p),kind='prior_record')
put('input_hashes.json',inputs);cfg['input_hashes_sha256']=sha(O/'input_hashes.json');put('config.json',cfg)
refs=subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads','refs/remotes/origin'],cwd=R,text=True);put('setup/starting_refs.json',dict(line.split() for line in refs.splitlines()))
# Full JSON read audit: every scalar visited, schema grouping is only a display compression.
read={}
for n in ['results.json','VERIFICATION.json']:
 stats=collections.defaultdict(list)
 def visit(x,p=''):
  if isinstance(x,dict):
   for k,v in x.items():visit(v,p+'/'+k)
  elif isinstance(x,list):
   for v in x:visit(v,p+'/*')
  else:stats[p].append(x)
 visit(json.loads((P/n).read_text()));read[n]=dict(sha256=sha(P/n),scalar_count=sum(map(len,stats.values())),fields={k:dict(count=len(v),types=dict(collections.Counter(type(t).__name__ for t in v)),false_count=sum(t is False for t in v),null_count=sum(t is None for t in v)) for k,v in stats.items()})
put('setup/prior_full_read_audit.json',read)
print('frozen inputs',len(inputs),'config',sha(O/'config.json'))
