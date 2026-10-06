"""Enrich edge observations separately, keeping already fixed labels/checkpoint intact."""
import sys
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,atomic_json,resource_guard,sha

def record(scene):
    resource_guard()
    import numpy as np
    import torch
    from data_access import frames,training_view,config
    from renderer_adapter import load_checkpoint,make_camera,rgb,contribution
    from metrics import profiles,visible_band
    cfg=config();d=OUT/'controls'/scene;identity=json.loads((d/'identity.json').read_text());selection=json.loads((d/'selection.json').read_text())
    label_sha=sha(d/'fixed_labels.npz');m=load_checkpoint(OUT/'models'/scene/'chkpnt7000.pth')
    labels=np.array(identity['label']);weights=[];views=[]
    for frame in frames('train'):
        camera=make_camera(frame);view=training_view(scene,frame);band,_=visible_band(view['instance'])
        diag=contribution(m,camera,labels,torch.tensor(band,device='cuda'))
        weights.append(diag['band_mass'].cpu().numpy())
        with torch.no_grad():im=rgb(m,camera).cpu().permute(1,2,0).numpy()
        views.append({'id':frame['id'],'visibility':'visible' if band.any() else 'unknown',
                      'observed_profile':profiles(im,view['instance']),'target_A_profile':profiles(view['rgb'],view['instance'])})
    np.savez_compressed(d/'per_view_band_contribution.npz',uid=identity['uid'],band_mass=weights)
    uids=np.array(identity['uid']);chosen=np.isin(uids,selection['selections']['C1']['uids'])
    record={'pair_id':scene+'/1:2','object_a':1,'object_b':2,'candidate_uids':uids[chosen].tolist(),
        'relation_type':'near_Gaussian_proxy_not_physical_contact','spatial_confidence':None,
        'anchor_positions':np.asarray(identity['anchor'])[chosen].tolist(),'anchor_provenance':'trained GS positions, not oracle surface',
        'per_view_visibility':views,'per_view_width':'in per-view observed_profile; null means not measurable',
        'per_view_contrast':'DeltaE76 D65/2deg and linear colour separation in profiles',
        'per_view_profile_confidence':'confidence and reason in profiles','continuity_field':None,
        'diagnosis_hypotheses':selection['diagnosis_hypotheses'],
        'target_width':'separate target_A_profile measured from fixed training RGB; not crossing gradient',
        'target_contrast':'fixed reference_RGB','target_emphasis':None,'edit_history':'separate immutable method edit logs',
        'fixed_labels_sha256_before_after':label_sha,'per_view_weights_sha256':sha(d/'per_view_band_contribution.npz')}
    assert sha(d/'fixed_labels.npz')==label_sha
    atomic_json(d/'edge_record_enriched.json',record)
    atomic_json(EXP/f'results/manifests/{scene}_edge_record.json',{'record_sha256':sha(d/'edge_record_enriched.json'),
        'fixed_labels_unchanged':True,'view_count':len(views),'profile_widths_null_preserved':True})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('scene');record(p.parse_args().scene)
