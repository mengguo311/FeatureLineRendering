"""Freeze one bounded area coverage diagnostic before evaluation."""
import round011_common as c
import copy
import json
p=copy.deepcopy(json.loads((c.W/'docs/partwise_sketch_hatching/round_010/PROTOCOL.json').read_text()))
p.update(round='round_011',authority='Only round010 Astra NEXT; outline3.3,5.6,5.8,9.4-9.6,14.3',hypothesis='One finite-ribbon polygon-square area coverage backend agrees with independent exact axial areas and oblique cross-section integrals, retaining unchanged center-site visibility and attachment.')
paths=[[[48.25,63.75],[63.75,63.75],[80.25,63.75]],[[43.25,51.75],[64.5,64.5],[83.25,75.75]],[[43.25,51.75],[64.5,64.5],[83.25,75.75]],[[48.25,32],[80.25,32]],[[48.25,32],[80.25,32]]]
for spec,uv in zip(p['cases'],paths):
    spec['id']='area_'+spec['id'];spec['projected_path']=uv
    spec['path']=[[(x-64)/16,(y-64)/16,4.] for x,y in uv]
p['coverage']={'screen_width_px':1.,'high_width':2.,'ink':.8,'pixel_square':'[x-.5,x+.5] x [y-.5,y+.5], centered at integer high raster site',
 'rule':'One straight projected finite butt-cap rectangle; collinear intermediate attachment waypoints allowed. No general joins. Canonical lexicographic endpoints; reject noncollinearity, backtracking, zero projected segments.',
 'candidate':'Sutherland-Hodgman polygon clipping to each pixel square; pixel-local shoelace area; no independent reference input.',
 'oracle':'Frozen projected endpoints; axial interval-product exact area, otherwise affine vertical y bounds from along/cross inequalities, split x integral at ALL pairwise line intersections including pixel y bounds and zero-gap crossings. Midpoint integration exact on each linear interval. No candidate clipping or projection reused.',
 'collinearity_epsilon_high_px':1e-9,'zero_length_epsilon_high_px':1e-12,
 'endpoint_area_cleanup': 'Computed fractions <=1e-12 snap0 and >=1-1e-12 snap1 for candidate and reference before uint8; raw oracle fractions also saved. No other rounding.',
 'endpoint_area_cleanup_epsilon':1e-12,'fraction_abs_error_max':1e-10,'area_sum_abs_error_max':1e-8,'ink_sum_abs_error_max':1e-8,
 'projection_check_epsilon':1e-12,'final_gate':'Strict full quantized uint8 and final LANCZOS equality. Any floor discrepancy is retained as NO_GO.',
 'visibility':'Unchanged owner_depth and visibility_gate at positive-area pixel CENTERS only. No within-pixel visibility claim.'}
p['controls']['physical_arrays']=['coverage','footprint','owner_depth','scene_depth','scene_owner','gate','high','quantized_uint8','final_uint8']
p['controls']['tie_controls']='Both round009 straight projected paths; 65 exact shared-edge query rays; nonempty fractional-coverage tie sites retained.'
p['controls']['distinct_depth']='Retain full old negative via historical replay. For new backend validate full historical bent attachment, then render first declared segment alone with unchanged complete owner list; require independently nonempty distinct-depth area footprint and ValueError ambiguous. Not a general bent-ribbon test.'
p['controls']['sensitivity']=['delete_area','add_outside_area','drop_visible_ink','hidden_ink','unsupported_ink','final_corruption','order_difference']
p['go_no_go']={'go':['All5 fixed new scenes and2 exposed tie controls complete', 'Full unclipped fractional coverage error<=1e-10; total area error<=1e-8 and analytic length*width conserved within1e-8', 'Matched high error<=1e-10 and ink sum error<=1e-8; strict uint8 and final equality','Nonempty visible for all and all required hidden/unsupported controls; visible fractions retained and rejected sites zero','Scene/owner finite masks exact and depths<=1e-9; input immutable; all physical order variants exact','Exact tie and first-segment distinct-depth controls; all58 inherited tests plus new RED/GREEN; historical round010 and earlier exact replay','New exact replay and every sensitivity control detected'], 'no_go':'Any frozen gate failure: preserve outputs and stop promotion; no post-exposure phase/threshold/algorithm selection.'}
p['resources']['round_deadline_jst']=c.DEADLINE.isoformat()
p['limits']=['Analytic GT diagnostic only;5 related scenes on one planar patch,2 exposed tie controls','Pixel-square finite area only; center-site visibility does not integrate occlusion or owner boundary inside pixel','No AA-quality/effective visual width/temporal stability, general joins, lamp/P1/RaDe-GS reconstruction claim','Depth tolerance .006 and LANCZOS tails unchanged','Historical round004 NO_GO,8 null controls,11 mixed cases and original validation child UNKNOWN retained']
p['regressions']='Round010 centered backend is exposed point baseline; all earlier scenes remain exposed regression only.'
p['prohibited']=['phase sweep','threshold selection','lamp integration','H2','training/GPU','old source edits','owner expansion','projection repair','orchestration edits','push/merge']
c.write(c.D/'PROTOCOL.json',p)
c.status('protocol_written_awaiting_commit')
