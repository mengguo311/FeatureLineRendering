"""Exact saved row sets for additional-budget acceptances and damaged controls."""
from common import *
from pipeline import load_state
from transfer import group_figures

def budget_contexts(c,out,e,pre,a,groups,display_ids,render,cams,ids):
    z=dict(np.load(Path(c['unit'])/'scenes'/c['scene']/'states/M4/BUDGET_SPLIT.npz'))
    deferred=set(zip(z['a'].tolist(),z['b'].tolist()));gmap={g['edge_id']:g for g in groups}
    events=[ev for ev in e.events if tuple(k[0] for k in ev['inputs']) in deferred]
    ordered=sorted(events,key=lambda ev:(-gmap.get(ev['output'][0],{}).get('supported_length_p',0),ev['output'][0]))
    chosen=ordered[:3];rows={ev['output'][0]:np.concatenate([pre[cid].rows for cid,_ in ev['inputs']]) for ev in chosen}
    for ev in chosen:
        for cid,version in ev['inputs']:assert pre[cid].version==version
    if rows:group_figures(out/'ADDITIONAL_BUDGET',a,rows,{k:display_ids[k] for k in ('M3','M4_CONTROL','M4_VARIANT','PARENTS')},render,cams,ids)
    js(out/'ADDITIONAL_BUDGET_SELECTION.json',dict(rule='Top3 actual accepted events previously fit_cap, output supported length descending then ID; exact M3 rows/versions',accepted_from_deferred=len(events),selected_events=chosen,all_events=events,missing='NO_ADDITIONAL_BUDGET_ACCEPTANCE' if not chosen else None))

def lost_growth_figures(c,out,comparison,a,display_ids,render,cams,ids):
    lost=set(comparison['control_growth_groups_members_not_preserved_together'])
    old=json.loads(Path(c['control_groups']).read_text())['groups'];chosen=sorted((g for g in old if g['edge_id'] in lost),key=lambda g:(-g['supported_length_p'],g['edge_id']))[:3]
    state=load_state(c['control_state']);rows={g['edge_id']:state['carriers'][g['edge_id']].rows for g in chosen}
    if rows:group_figures(out/'LOST_CONTROL_GROWTH',a,rows,{k:display_ids[k] for k in ('M3','M4_CONTROL','M4_VARIANT','PARENTS')},render,cams,ids)
    js(out/'LOST_GROWTH_SELECTION.json',dict(rule='Top3 formerly qualifying control groups no longer assigned together, supported length descending then ID',edge_ids=[g['edge_id'] for g in chosen],all_lost=sorted(lost),missing='NO_DAMAGED_CONTROL_GROWTH' if not chosen else None))
