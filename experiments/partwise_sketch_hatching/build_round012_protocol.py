"""Freeze exposed-fixture measurement before evaluation."""
import round012_common as c
import json,subprocess
old=json.loads((c.W/'docs/partwise_sketch_hatching/round_011/PROTOCOL.json').read_text())
ids=['area_oblique_visible','area_oblique_partial_hidden','area_axial_owner_edge_background','area_axial_owner_edge_samepart']
p={'round':'round_012','authority':'Only round011 Astra NEXT; outline5.8,9.5,9.6,14.3','study_type':'New physical-visibility metric on exposed analytic fixtures, no blind object evidence',
'hypothesis':'Center-site gating of correct ribbon area can over/under-estimate physical visible area at finite owner and occluder boundaries.',
'prior_protocol_sha256':c.sha(c.W/'docs/partwise_sketch_hatching/round_011/PROTOCOL.json'),
'candidate_sources':{n:c.sha(c.W/'experiments/partwise_sketch_hatching'/n) for n in ['area_coverage.py','visibility_primitive.py','mesh_attachment.py']},
'camera':old['camera'],'geometry':old['geometry'],'cases':[s for s in old['cases'] if s['id'] in ids],
'primitive':old['primitive'],'coverage':old['coverage'],
'physical_reference':{'definition':'area(pixel square intersect finite butt-cap ribbon intersect finite owner rectangle minus strictly nearer occluder rectangle)',
'inputs':'Only frozen prescribed 2D endpoints and analytic rectangle bounds/depths; no candidate projection, coverage, gate or depth arrays',
'axial':'Exact interval intersection products',
'oblique':'Independent 1D vertical cross-section integral from along/cross half-plane inequalities and rectangle bounds; split at all affine-bound crossings, integrate positive linear thickness exactly',
'raw_and_clean':'Save raw fractions, mass partitions and cleaned fractions. Snap <=1e-12 to0 and >=1-1e-12 to1 solely before matched quantization; record raw numerical error.',
'conservation':['ribbon=visible+occluded+unsupported per pixel','sum per-pixel areas equals whole-image-domain integral','ribbon area=endpoint length*2','axial owner-edge visible area=length*1=32','oblique strip occluded area=(70-60)*2*length/abs(dx); no owner/end/y clipping for this frozen fixture','all-visible physical area equals full ribbon area'],
'quantization':'Same .8 ink, uint8 floor then PIL LANCZOS128->64; full arrays saved'},
'subsets':{'physical_boundary':'positive ribbon and 1e-10<visible_area<ribbon_area-1e-10; visibility mixed INSIDE pixel, excludes mere ribbon edge',
'visible_interior':'positive ribbon and abs(visible-ribbon)<=1e-10',
'hidden_interior':'positive ribbon, visible<=1e-10, owned>1e-10',
'unsupported_interior':'positive ribbon, owned<=1e-10',
'required':'visible interior all4; boundary in3 limited-visibility cases; hidden interior occluder case; unsupported interior both owner-edge cases; all-visible boundary empty',
'ribbon_edge':'0<ribbon<1, separately reported overlapping subset, not visibility boundary'},
'metrics':{'full_arrays':['ribbon','owned','occluded','unsupported','visible','candidate_visible_area','candidate_high','reference_high','candidate_quantized_uint8','reference_quantized_uint8','candidate_final_uint8','reference_final_uint8'],
'error':'signed candidate-reference; sum positive and negative separately, L1, max, mismatch count; high-area units and ink units separate; final uint8 errors /255',
'coverage':'subset site counts and ribbon/physical/candidate area and fraction of total ribbon; no excluded difficult pixels'},
'gates':{'fraction_abs_error':1e-10,'mass_abs_error':1e-8,'uint8_and_final':'strict equality',
'measurement_validity':'Independent reference range/partition/mass/closed-form controls, nonempty subsets, all64 inherited tests plus new reference tests, immutable candidate, historical exact replay, new exact replay, sensitivity response. Candidate mismatch does NOT invalidate measurement.',
'physical_promotion':'All4 full physical visible-area arrays and high ink match within1e-10, sums within1e-8, quantized and final exact. Any mismatch is NO_GO; do not repair or tune.',
'engineering_invalid':'Any reference/control/replay failure; preserve partials and no physical conclusion'},
'sensitivity':['reference area deletion breaks mass control','reference area addition outside ribbon breaks partition/range','ideal candidate deletion yields under-ink','ideal candidate addition yields over-ink','matched-total relocation has nonzero L1','final corruption detected'],
'regression':'Replay all7 round011 cases, negative control and earlier historical chain exactly; preserve exact ties, distinct depths, round004 NO_GO,8 null controls,11 mixed cases, original validation child UNKNOWN',
'resources':{'cpu_affinity':[0,1],'threads_max':2,'GPU':False,'serial_compute':True,'invocation_seconds_max':600,'round_deadline_jst':c.DEADLINE.isoformat(),'output_cap_bytes':12*2**30,'downloads':0},
'prohibited':['renderer repair','phase sweep','threshold selection','owner expansion','lamp integration','H2','training','new evaluation scenes','historical seal writes'],
'limits':['No RaDe-GS reconstruction or P1 evidence','No temporal or visual quality inference','Only fronto-parallel finite planar owners/rectangular occluder and straight ribbons','Area ownership does not imply tested general surface visibility']}
assert not (c.D/'PROTOCOL.json').exists();c.write(c.D/'PROTOCOL.json',p)
c.write(c.R/'PRIOR_SEAL_VERIFY.json',c.verify_prior());c.status('protocol_written_awaiting_commit',resources=c.resources())
print(json.dumps({'cases':ids,'prior_seal':c.verify_prior()}))
