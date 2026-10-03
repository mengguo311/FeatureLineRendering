"""Fixed two-F top4/16/32 audit; read-only relative to sealed main F asset."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'artifacts/gaussian_edge_attribution_v1'
sys.path.insert(0,str(ART/'code'))
import core
from native_attributes import sha256,atomic_json
KEYS=('F_001','F_041');N=311562

def plain(a):
    if isinstance(a,np.generic):return a.item()
    raise TypeError(type(a))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--normalization',required=True);args=ap.parse_args()
    normpath=Path(args.normalization);norm=json.loads(normpath.read_text());cfg=json.loads((ART/'code/config.json').read_text());normhash=sha256(normpath)
    if 'normalization' in norm:norm=norm['normalization']
    raw={};ev={};strata={}
    for key in KEYS:
        data=dict(np.load(ROOT/'native_extension'/f'{key}_top32.npz'));raw[key]=data
        fields=core.evidence_fields(data,cfg);ev[key]=core.compute_evidence(fields,norm,cfg)
        grid=np.zeros(data['alpha'].shape,bool);grid[4::16,4::16]=True
        fg=data['alpha']>=cfg['foreground_alpha'];pos=ev[key]['union']>=cfg['positive_evidence_threshold']
        strata[key]={'uniform_all':grid,'uniform_foreground':grid&fg,'uniform_edge':grid&fg&pos,'uniform_nonedge':grid&fg&~pos,'full_foreground':fg,'full_edge':fg&pos,'full_nonedge':fg&~pos}
    summary=dict(protocol_seal_sha256=sha256(ART/'PROTOCOL_SEAL.json'),config_sha256=sha256(ART/'code/config.json'),normalization_path=str(normpath.resolve()),normalization_sha256=normhash,core_sha256=sha256(ART/'code/core.py'),script_sha256=sha256(__file__),scope='Fixed Mic F1/F41 only; independent audit, never updates main F asset; identical config+MicF normalization for K=4/16/32',strata={},assets={},comparisons={})
    for key in KEYS:
        data=raw[key];summary['strata'][key]={}
        for name,mask in strata[key].items():
            a=data['alpha'][mask].astype(np.float64);rec=dict(pixel_count=int(mask.sum()),original_alpha_mass=float(a.sum()),coverage={})
            for k in (4,16,32):
                mass=data['topk_w'][...,:k].sum(-1,dtype=np.float64)[mask]
                rec['coverage'][str(k)]=dict(mass_fraction=float(mass.sum()/a.sum()) if a.sum()>0 else None,omitted_mass=float(np.maximum(a-mass,0).sum()),perpixel_mean_fraction=float(np.mean(mass/a)) if len(a) and np.all(a>0) else None)
            summary['strata'][key][name]=rec
    compact={}
    for k in (4,16,32):
        stats=[]
        for key in KEYS:
            data={name:arr[...,:k] if name in ('topk_id','topk_w','topk_depth') else arr for name,arr in raw[key].items()}
            data.update(frame_id=int(key.split('_')[1]),split='F')
            st=core.view_statistics(data,ev[key],N,cfg,with_side=True);st.pop('diagnostics',None);stats.append(st)
        asset=core.aggregate_views(stats,cfg);del stats
        keep=['eligible','raw_denominator','support_view_count','unknown']+['baseline_'+c for c in core.CLASSES]+['enhanced_'+c for c in core.CLASSES]
        compact[k]={name:asset[name] for name in keep};del asset
        summary['assets'][str(k)]=dict(gaussians=N,eligible=int(compact[k]['eligible'].sum()),unknown=int(compact[k]['unknown'].sum()),visible=int((compact[k]['raw_denominator']>0).sum()),raw_visibility_mass=float(compact[k]['raw_denominator'].sum()))
        print('twoF K',k,summary['assets'][str(k)],flush=True)
    for k in (16,32):
        a,b=compact[4],compact[k];common=a['eligible']&b['eligible'];common_ids=np.flatnonzero(common);rec=dict(common_eligible=int(common.sum()),newly_eligible=int((b['eligible']&~a['eligible']).sum()),lost_eligible=int((a['eligible']&~b['eligible']).sum()),arms={})
        for arm in ('baseline','enhanced'):
            for channel in core.CLASSES:
                name=arm+'_'+channel;sa,sb=a[name],b[name]
                rho=spearmanr(sa[common],sb[common]).statistic if common.sum()>1 else np.nan
                ar=dict(spearman_common_eligible=float(rho) if np.isfinite(rho) else None,mae_common_eligible=float(np.mean(np.abs(sa[common]-sb[common]))) if common.any() else None,tiers={})
                ta=core.rank_tiers(a,cfg,name);tb=core.rank_tiers(b,cfg,name)
                oa=common_ids[np.lexsort((common_ids,-sa[common]))];ob=common_ids[np.lexsort((common_ids,-sb[common]))]
                for p in cfg['tiers_percent']:
                    p=str(p);aa=set(ta[p].tolist());bb=set(tb[p].tolist());ct=int(np.ceil(len(common_ids)*int(p)/100));ca=set(oa[:ct].tolist());cb=set(ob[:ct].tolist())
                    ar['tiers'][p]=dict(own_eligible_count4=len(aa),own_eligible_countk=len(bb),own_eligible_jaccard=len(aa&bb)/max(len(aa|bb),1),common_eligible_same_count=ct,common_eligible_same_count_jaccard=len(ca&cb)/max(len(ca|cb),1))
                rec['arms'][name]=ar
        summary['comparisons'][f'4_vs_{k}']=rec
    summary['fixed_top4_groups_added_visible_mass']={}
    for arm in ('baseline','enhanced'):
        tiers=core.rank_tiers(compact[4],cfg,arm+'_union')
        for p,group in tiers.items():
            name=arm+'_union_'+p;summary['fixed_top4_groups_added_visible_mass'][name]={}
            membership=np.zeros(N,bool);membership[group]=True
            for key in KEYS:
                data=raw[key];ids=data['topk_id'];member=(ids>=0)&membership[np.maximum(ids,0)];w=data['topk_w'];masses={str(k):float((w[...,:k]*member[...,:k]).sum(dtype=np.float64)) for k in (4,16,32)}
                summary['fixed_top4_groups_added_visible_mass'][name][key]=dict(selected_count=len(group),mass_by_k=masses,added_mass32_over4=masses['32']-masses['4'],fraction_of_top32_group_mass_missing_top4=(masses['32']-masses['4'])/max(masses['32'],1e-30))
    if sha256(normpath)!=normhash:raise ValueError('Normalization changed during independent audit')
    summary['status']='PASS_ENGINEERING_INCOMPLETE_CONTRIBUTOR_ATTRIBUTION'
    summary['scientific_limitation']='Top32 residual omitted alpha exists. TwoF rank stability cannot prove eightF completeness or unique geometry. Main assets remain TOP4-TRUNCATED.'
    atomic_json(ART/'research/COMPLETENESS_AUDIT.json',summary)
    arrays={f'k{k}_{name}':arr for k,asset in compact.items() for name,arr in asset.items()};np.savez_compressed(ROOT/'native_extension/completeness_twoF_scores.npz',**arrays)
    print('saved COMPLETENESS_AUDIT.json',flush=True)
if __name__=='__main__':main()
