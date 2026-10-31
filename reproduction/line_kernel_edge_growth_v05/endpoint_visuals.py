"""Fixed endpoint supplement displays and explicit damaged controls."""
from common import *
from pipeline import load_state
from transfer import group_figures

def new_model_selection(groups,comparison,out):
    eligible=set(comparison['changed_growth_gain_and_outward_ge4_over_control']);chosen=[];missing=[]
    for kind in ('line','polyline'):
        gg=[g for g in groups if g['edge_id'] in eligible and g['model']==kind]
        if gg:chosen.append(min(gg,key=lambda g:(-g['supported_length_p'],g['edge_id'])))
        else:missing.append(kind)
    js(out/'NEW_MODEL_SELECTION.json',dict(rule='Largest changed qualifying group with gain and outward>=4p over control, per model, support descending/ID ascending',edge_ids=[g['edge_id'] for g in chosen],missing_models=missing))
    return chosen

def supplemental_contexts(c,out,e,pre,a,groups,display_ids,render,cams,ids):
    z=dict(np.load(Path(c['unit'])/'scenes'/c['scene']/'states/M4/SUPPLEMENT_CANDIDATES.npz'))
    pairs=set(zip(z['a'].tolist(),z['b'].tolist()));events=[ev for ev in e.events if tuple(k[0] for k in ev['inputs']) in pairs]
    chosen=events[:3];rows={ev['output'][0]:np.concatenate([pre[cid].rows for cid,_ in ev['inputs']]) for ev in chosen}
    for ev in chosen:
        for cid,version in ev['inputs']:assert pre[cid].version==version
    if rows:group_figures(out/'SUPPLEMENT_ACCEPTED',a,rows,{k:display_ids[k] for k in ('M3','M4_CONTROL','M4_VARIANT','PARENTS')},render,cams,ids)
    js(out/'SUPPLEMENT_ACCEPTED_SELECTION.json',dict(rule='First3 accepted supplemental pairs in actual commit order; exact complete predecessor rows/versions',accepted_supplemental=len(events),selected_events=chosen,all_events=events,missing='NO_SUPPLEMENT_ACCEPTANCE' if not chosen else None))

def lost_control_figures(c,out,comparison,a,display_ids,render,cams,ids):
    old=json.loads(Path(c['control_groups']).read_text())['groups'];state=load_state(c['control_state']);damaged=[]
    for g in old:
        rows=state['carriers'][g['edge_id']].rows;labels=np.unique(ids[rows])
        if len(labels)!=1 or labels[0]<0:damaged.append(g)
    chosen=sorted(damaged,key=lambda g:(-g['supported_length_p'],g['edge_id']))[:3]
    rows={g['edge_id']:state['carriers'][g['edge_id']].rows for g in chosen}
    if rows:group_figures(out/'DAMAGED_CONTROL',a,rows,{k:display_ids[k] for k in ('M3','M4_CONTROL','M4_VARIANT','PARENTS')},render,cams,ids)
    js(out/'DAMAGED_CONTROL_SELECTION.json',dict(rule='Top3 control groups whose original members are no longer assigned together; all control groups eligible, not just growth_gate',edge_ids=[g['edge_id'] for g in chosen],all_damaged=[g['edge_id'] for g in damaged],growth_gate_damaged=[g['edge_id'] for g in damaged if g['growth_gate']],missing='NO_DAMAGED_CONTROL_GROUP' if not chosen else None))
