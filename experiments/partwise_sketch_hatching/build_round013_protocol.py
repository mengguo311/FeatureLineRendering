"""Freeze one bounded mechanism before evaluating any new fixture."""
import round013_common as c
import copy,json
old=json.loads((c.W/'docs/partwise_sketch_hatching/round_012/PROTOCOL.json').read_text())
g=copy.deepcopy(old['geometry'])
bounds=[31.25,31.25,96.25,96.25]
g['analytic_owner']['bounds_high_xyxy']=bounds
g['vertices']=[[(x-64)/16,(y-64)/16,4.] for x,y in [(bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[2],bounds[3]),(bounds[0],bounds[3])]]
def case(name,uv,sf,extra=None,kind='full',required=None):
    d={'id':name,'projected_path':uv,'path':[[(x-64)/16,(y-64)/16,4.] for x,y in uv], 'segment_faces':sf,'mass_kind':kind,'required_subsets':required or ['visible_interior'],'exposed':False}
    if extra:d['extra']=extra
    return d
ob=[[44.25,50.25],[65.25,65.25],[86.25,80.25]]
edge=[[48.25,31.25],[80.25,31.25]]
new=[case('fragment_oblique_visible',ob,[1,0]),
     case('fragment_oblique_partial_hidden',ob,[1,0],{'z':3.,'bounds_high_xyxy':[59.25,40.25,70.25,88.25],'part_id':2},'strip',['visible_interior','hidden_interior','physical_boundary']),
     case('fragment_oblique_fully_hidden',ob,[1,0],{'z':3.,'bounds_high_xyxy':[30.25,30.25,97.25,98.25],'part_id':2},'hidden',['hidden_interior']),
     case('fragment_axial_owner_edge',edge,[0],kind='half',required=['visible_interior','unsupported_interior','physical_boundary']),
     case('fragment_axial_samepart_unsupported',edge,[0],{'z':3.,'bounds_high_xyxy':[40.25,27.25,88.25,30.25],'part_id':1},'half',['visible_interior','unsupported_interior','physical_boundary']),
     case('fragment_shared_owner_edge',[[45.25,45.25],[80.25,80.25]],[0])]
exposed=copy.deepcopy(old['cases'])
for s in exposed:
    s.update(exposed=True,geometry=old['geometry'],required_subsets=['visible_interior'])
    s['mass_kind']='half' if 'owner_edge' in s['id'] else ('strip' if 'hidden' in s['id'] else 'full')
    if s['mass_kind']=='half':s['required_subsets']+=['unsupported_interior','physical_boundary']
    if s['mass_kind']=='strip':s['required_subsets']+=['hidden_interior','physical_boundary']
p={'round':'round_013','authority':'Only round012 Astra NEXT; outline 5.8,9.4-9.6,14.3',
   'hypothesis':'Triangle-derived disjoint visible fragments remove measured center-site over/under area on finite fronto-parallel straight-ribbon fixtures.',
   'study_type':'New geometric mechanism on six prefrozen analytic diagnostic fixtures; four exposed regression fixtures. No blind object/reconstruction evidence.',
   'prior_next_sha256':c.sha(c.P/'NEXT.json'),'camera':old['camera'],'geometry':g,'cases':new+exposed,
   'primitive':old['primitive'],'coverage':old['coverage'],
   'candidate_sources_preserved':old['candidate_sources'],
   'mechanism':{'input':'Only actual mesh vertices/faces, explicit owner faces, fixed 3D path and camera/style. Attachment adapter also checks explicit per-segment faces. No reference rectangles/masks/areas passed to candidate.',
    'algorithm':'Canonicalize projected CCW triangles. Disjoint union by subtracting previously covered owner triangles from ribbon-owner intersections. Sequentially subtract nearer scene triangles. Integrate each remaining convex fragment over integer-centered pixel squares, sum disjoint areas once.',
    'support':'Owner triangles share one fronto-parallel positive camera depth; every scene triangle constant positive camera depth. Straight finite butt-cap ribbon only. Nonowner triangle depth must differ from owner depth by >0.006; nearer subtract, farther ignored. Co-depth nonowner and near ties rejected conservatively even when disjoint.',
    'planarity_epsilon_world':1e-9,'depth_separation_world':.006,'halfplane_classification':'exact >=0; no dilation or geometric tolerance','area_cleanup_epsilon':1e-12,
    'order':'Canonical triangle winding/start vertex/geometric sorting; order, reversal, winding, duplicate-owner and duplicate-occluder output invariants checked.',
    'limits':'No tilted/depth-crossing faces, general bends, auto owner discovery, lamp integration or general-surface claim.'},
   'reference':{'source':'Unchanged physical_area_reference.py; independent axial interval products or affine vertical cross-section integration; prescribed endpoints and analytic domains only.',
    'controls':['finite/range','raw per-pixel partition R=V+H+U','sum per-pixel equals whole-domain integral','closed-form total ribbon/visible/hidden/unsupported masses','prefrozen nonempty subsets','new fully hidden V=0 with H>0','shared-edge ribbon visible mass=2*length','round012 (60,60) visible sliver retained']},
   'gates':{'raw_area_abs_max':1e-10,'area_abs_max':1e-10,'area_mass_abs':1e-8,'high_ink_abs_max':1e-10,'ink_mass_abs':1e-8,'quantized_and_final':'strict full array equality','ordering':'strict full cleaned area/high/uint8/final equality','replay':'all new arrays/metrics exact; all round012 and inherited science replays exact',
    'GO':'Only finite planar P0 if all candidate/reference/order/shared-edge/rejection/sensitivity/test/replay gates pass.',
    'NO_GO':'Any candidate mismatch retains physical NO_GO; no post-result threshold/phase/budget changes.',
    'ENGINEERING_INVALID':'Any reference, nonempty control, unexpected exception, input mutation or replay failure.'},
   'rejection_controls':['non-frontoparallel scene','noncoplanar owners','co-depth nonowner','near-depth nonowner','nonpositive scene depth','bent path','detached path'],
   'sensitivity':['delete reference visible area','add reference outside ribbon','delete ideal ink','add ideal ink','equal-mass relocation','corrupt final pixel'],
   'resources':{'cpu_affinity':[0,1],'threads_max':2,'GPU':False,'serial_compute':True,'invocation_seconds_max':600,'round_deadline_jst':c.DEADLINE.isoformat(),'output_cap_bytes':12*2**30,'downloads':0},
   'prohibited':['old renderer edits','threshold/phase/supersampling sweeps','post-result choices','owner expansion','lamp integration','H2','training','historical seal/orchestration writes'],
   'limits':['Analytic GT geometry/labels/manual directions only','P1 and RaDe-GS unproven','AA quality, effective line width and temporal stability UNMEASURED','Keep round011 limited area GO and round012 physical NO_GO; retain round004 NO_GO,8 null controls,11 mixed cases,original validation child UNKNOWN']}
# Replace inherited center-site wording; other numeric controls are unchanged.
p['coverage']['visibility']='New disjoint geometric visible-fragment integration; previous center-site backend unchanged.'
p['coverage']['candidate']=p['mechanism']['algorithm']
c.write(c.D/'PROTOCOL.json',p)
c.write(c.R/'PRIOR_SEAL_VERIFY.json',c.verify_prior())
print(json.dumps({'cases':len(p['cases']),'prior_seal':c.verify_prior(),'resources':c.resources()}))
