import runtime as rt,json,time
def freeze():
 p=rt.ART/'PROTOCOL.json'
 if p.exists():return json.loads(p.read_text())
 x=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),frozen_before_new_source_extraction=True,research_sha256=rt.sha(rt.ART/'RESEARCH_ZH.md'),input_freeze_sha256=rt.sha(rt.ART/'INPUT_FREEZE.json'),
 source='Original SH3 seed1729 iteration30000 PLY; immutable original row IDs',renderer='CPU all-N stock-rule alphaT replica must pass four construction native-cache calibration; no GPU while foreign occupancy',
 roles='24 metadata-only construction, 4 DEV, 8 reserved per scene; reserved and 33arc only after unique scene asset seal',
 evidence=dict(alpha_threshold=.5,min_component_pixels=32,holes='not filled; enclosed-hole participation saved separately; open negative spaces preserved',rim_sigma_pixels=[1.5,3.],all_N=True,topK=False),
 fusion=dict(valid_mass=.1,min_rim_mass=.01,high_relative=.35,high_rim_mass=.05,weak_relative=.12,soft='relative * sqrt(rim_mass/(rim_mass+.05)); max across distinct cameras',rim_used='3px wide map; 1.5px narrow map diagnostic only, not fused',hysteresis='one nearest-high hop with distance <= sum min(2*max_sigma,.025*robust_bbox_diagonal); save weak acceptance/rejection',single_view='allowed and distinctly labelled; no vote duplication'),
 region=dict(type='original full 3D covariance anchored ellipsoid-union edge occupancy proxy, not SDF nor physical surface',grid_resolution_diagonal=224,width_candidates_voxels=[.4,.8,1.2],sigma_multiplier=1.25,level=.1,max_axis_diagonal=.025,min_axis_voxels=.55,closing='one iteration six-neighbor cross; raw support retained; source-neighborhood CSR for each fill',background_veto='once in object space: each construction foreground dilated 2px; outside image unknown; holes not filled',connectivity=6),
 arms=['thin_A_exact_old_graph_world_radius','same_A_widened_DEV_matched_ink','two_source_new_selection_region','multi24_new_selection_region'],control_limit='two/multi change source support plus source silhouette constraints; bbox-derived spacing differs. This is a pipeline source-count control, not isolated selector causality.',
 dev=dict(selection='maximize average coverage3 - .45*background_far_fraction - .30*deep_interior_fraction - .40*negative_space_fill_fraction - .08*ink_over_foreground; lower width wins ties',widened_match='8 bisections of world radius in [old_radius,.025*region_diagonal], match average DEV ink; residual explicit if unmatchable',two_source_width='same selected voxel-width multiplier as multi24; physical width separately reported'),
 visibility='triangle asset self-zbuffer only; x-ray relative to original opaque object; NO perview hide masks; full rear geometry shown',internal_layer='NOT_RUN unless primary delivered with time remaining; primary includes alpha-hole boundaries, no RGB texture edges',
 scientific_status='Engineering pass != GO. Visual decision on readable shape/continuity/stability + width and holes. Invalid calibration/execution = INVALID/UNDETERMINED, not scientific NO_GO. New selection cannot overwrite old REFUSED.',
 cheap_falsification=['calibration fail => INVALID','multi-source supports fail DEV shape coverage => added observations unproven','matched ink widened comparable => fusion representation advantage unproven','near-full black object or merged holes => PARTIAL/NO_GO contour quality'],
 resources=dict(cpu_threads=2,root_min_GiB=4,shared_git_min_GiB=1.5,stage_max_GiB=6,production_guard_GiB=1,no_installs=True,no_training=True),
 method_sha256={p.name:rt.sha(p) for p in rt.EXP.glob('*.py')})
 rt.atomic_json(p,x);return x
if __name__=='__main__':freeze()
