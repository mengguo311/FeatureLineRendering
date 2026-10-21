"""Freeze one shade-placement candidate before rendering or metric evaluation."""
from common import *
import copy, shutil
from datetime import datetime,timezone
from spacing_cli import PLACEMENT, original_seeds, load_asset
U=OUT.parent/'unit_011';P=U.parent/'unit_010'
def cp(src,dst):
    assert not dst.exists(),dst
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
source=P/'outputs/edited/asset.json';manifest=json.loads(source.read_text())
for key in ('mesh','strokes','config'):
    src=source.parent/manifest[key]['path'];dst=U/'inputs'/src.name
    cp(src,dst);assert sha(dst)==manifest[key]['sha256'];manifest[key]['path']=dst.name
manifest.pop('recipe',None);manifest.pop('path_lineage',None)
manifest['input_parent_asset']=dict(path=str(source),sha256=sha(source))
write_json(U/'inputs/asset.json',manifest)
for name in ('STATUS.json','NEXT.json','SEAL.json','SHA256_MANIFEST.json','PROTOCOL.json','EXECUTION_BATCH_INTERRUPTION.json'):
    cp(P/name,U/'previous_snapshot'/name)
shutil.copytree(P/'inherited_failures',U/'inherited_failures')
cp(U.parent.parent/'orchestration/BRIEF.md',U/'BRIEF_SNAPSHOT.md')
_,_,mesh,_,cfg=load_asset(U/'inputs/asset.json')
seeds=original_seeds(mesh);counts={str(b):sum(s['band']==b for s in seeds) for b in range(4)}
blockers=json.loads((P/'STATUS.json').read_text())['blockers']
p=copy.deepcopy(json.loads((P/'PROTOCOL.json').read_text()))
p.update(unit='unit_011',created_utc=datetime.now(timezone.utc).isoformat(),
    question='Can one band-preserving spatial seed redistribution reduce rendered shade stacks and improve complete-object readability at fixed260 shade paths/length/ink?',
    changed_variable='Only shade seed placement: original area-random -> deterministic per-profile-band anisotropic farthest candidates; no other style or renderer change',
    source_asset=str(source),source_asset_sha256=sha(source),inputs={str(x):sha(x) for x in (U/'inputs').glob('*')})
p['provenance']['paths']='unit010 complete434:260shade24stem150base length.12; retain174non-target, relocate260shade seeds with new geometry revision'
p['operation']=dict(part=1,placement=PLACEMENT,original_per_band_counts=counts,
    band_definition='Triangle vertex radius/height rings match one of four authored shade profile segments; inner and outer separated',
    count=260,angle_deg=0.,length_world=.32,step_world=.015,width_px=1.,seed=1729,
    candidate_rng='numpy.default_rng(SeedSequence([1729,11,band])); per draw face then2bary uniforms',
    candidate_count='max(256,64*original_band_count); face-area probabilities within band',
    metric='(mean_band_radius*min(abs(delta_theta),2pi-abs(delta_theta))/.32)^2 + (band_profile_length*delta_profile_t/.08)^2',
    profile_t='barycentric interpolation of vertex profile fractions on fixed mesh',
    order='nearest to theta0,t.5 first, iteratively max min distance, lowest index ties; assign selected order to sorted original IDs within band',
    ink='Retain original assigned ink per ID without recalculating new-normal lighting; tone uncalibrated',
    walk='Unchanged adjacent-face walker, two.16 halves, no new clipping or band stopping; record any band crossing as scientificNO_GO',
    cold='Fresh process recipe+mesh+retained174+config only, rerun candidate generation/selection/walk; no target cache',
    preserve='174non-target paths/IDs/inks,260target IDs/inks and original per-band seed counts')
p['evaluation'].update(primary='Whole-lamp readability, rendered cross-stroke proximity, geometric coverage and nonzero isolated edit; primitive equality secondary')
p['evaluation']['gates']['target_part']=1
p['evaluation']['coverage']=dict(height_edges_world=[1.4,1.7166666666666666,2.033333333333333,2.350000001],
    azimuth_edges_radians=[0,float(np.pi/2),float(np.pi),float(3*np.pi/2),float(2*np.pi)],
    cells='3fixed height bins x4 WORLD atan2(z,x) quadrants, all analytic visible shade pixels assigned; no erosion',
    minimum_eligible_pixels=20,minimum_support_pixels=3,minimum_support_fraction=.01,
    scope='4stills+40orbit/zoom frames; tiny/nonvisible cells explicit abstentions with excluded pixel fractions; hidden surfaces unmeasured')
p['evaluation']['spacing']=dict(distance_manhattan_px=2,close_fraction_ratio_max=.8,
    ink_mass_ratio_min=.8,ink_mass_ratio_max=1.25,
    metric='Each shade isolated actual raster support>.1 inside analytic shade. For every own support pixel count whether another stroke has support within Manhattan2px. Pool numerator/denominator over4stills; candidate<=.8baseline.',
    overlap='Report distinct-stroke exact pixel overlap and sum-isolated minus composite shade ink; low-res sampled raster diagnostic, not exact curve separation',
    accounting='Per-view ink ratio .8..1.25; report support, per-ID visible mass and all coverage denominators',
    instrumentation='Existing renderer_probe_unit007 isolated buffers; require full_image/full_hatch exact production output; no renderer change')
p['evaluation']['controls']=['Noedit must fail nonzero target gate','Blacken16brightest independent far-other pixels: leakagefraction1 fails',
    'White-filled3px raster drift yields nonzeroL1','Zero hatch fails eligible coverage cells',
    'Single raster stroke has0cross-stroke close support; duplicate same raster produces1 and detects stacking']
p['evaluation']['secondary']=['174non-target paths per-field bytes exact','260target IDs/inks and original seed-band counts preserved',
    'All target anchors legal; independently check each path band against seed band; crossing retainedNO_GO',
    'Cold recipe and separate saved-path replay reproduce4PNGviews','Reject corrupt recipe/hash or existing/historical output']
p['evaluation']['visual_go']='Clearly less piled-up shade and more even readable bands in full lamp/crops; all3parts remain recognizable; if visible piles, empty band or branch error remain retainNO_GO; wholevisual separately evaluated'
p['evaluation']['no_go']='Spacing/ink/coverage/isolation/cold failure or visible stacks remain; preserve one candidate and do not sweep or change thresholds'
p['media']['edit']['operation']='12original-seed+12dispersed-seed actual single shade operation; no interpolation'
p['budgets']['finish_before_jst']='2026-10-21T20:18:07+09:00'
p['claims']=dict(software='PENDING',shade_spacing_visual='PENDING',full_visual='NO_GO_RETAINED',reconstructed_input='BLOCKED',full_P1='PARTIAL',H1_H2='NOT_TESTED',temporal='NOT_INDEPENDENTLY_AUDITED_FOR_NEW_SHADE_GEOMETRY')
p['retained_failures']=blockers;p['previous_next_sha256']=sha(P/'NEXT.json')
p['brief_sha256']=sha(U/'BRIEF_SNAPSHOT.md')
write_json(U/'PROTOCOL.json',p);write_json(WORK/'docs/partwise_sketch_hatching_v02/PROTOCOL_unit011.json',p)
s=dict(stage='shade_spacing_protocol_frozen',execution_state='running',scientific_verdict='PENDING',tests={},artifacts=['PROTOCOL.json'],blockers=blockers,
    outline_milestone='P1/W3/W4/W9; outline5.5-5.8,7.1-7.3,9.2,9.5-9.7,11.1,14.3',
    p1_progress='One frozen shade-only seed-placement operation targets whole-object readability; no evaluation yet')
write_json(U/'STATUS_INITIAL.json',s);write_json(U/'STATUS.json',s)
write_json(U/'RESOURCES_INITIAL.json',dict(root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(U).free,cpu_affinity=sorted(os.sched_getaffinity(0)),gpu=False))
print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'),band_counts=counts)))
