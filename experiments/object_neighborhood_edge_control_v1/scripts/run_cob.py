"""Execute official B4 algorithm, with UID-only instrumentation and training oracle masks.

This is the published foreground/rest baseline, not our RGB-error split. Its
global colour/geometry recovery and final ambiguity pruning are kept intact.
"""
import argparse
import json
import sys
import random
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,ART,atomic_json,resource_guard,sha,code_identity

def run(scene,mask_only=False):
    guard=resource_guard()
    from native import install_cob
    install_cob()
    import torch
    import numpy as np
    import train as upstream
    import scene as scene_module
    from arguments import ModelParams,OptimizationParams,PipelineParams
    from stable_ids import Identity
    from data_access import frames,training_view,config
    from PIL import Image
    cfg=config();seed=cfg['seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    original=upstream.GaussianModel;models=[];events=[]
    meta=json.loads((OUT/'controls'/scene/'identity.json').read_text())
    prob=np.load(OUT/'controls'/scene/'fixed_labels.npz')['probability']
    class Tracked(original):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);models.append(self)
        def restore(self,*a,**kw):
            super().restore(*a,**kw)
            self.identity=Identity(**{k:meta[k] for k in ('uid','label','anchor','parent_uid','next_uid')})
            self.label_probability=prob.copy()
        def mask_and_split(self,threshold,extent,base_num=None,prune_only=False,N=2):
            selected=(self.mask_sign_accum/base_num<threshold).squeeze()
            if not prune_only:selected &=self.get_scaling.max(1).values>self.percent_dense*extent
            select=selected.cpu().numpy();before=len(self.identity.uid)
            parents=self.identity.uid[select].copy()
            super().mask_and_split(threshold,extent,base_num,prune_only,N)
            if prune_only:
                self.identity=self.identity.reorder(np.flatnonzero(~select));self.label_probability=self.label_probability[~select]
            else:
                self.identity=self.identity.split(parents,N)
                self.label_probability=np.concatenate([self.label_probability[~select],np.tile(self.label_probability[select],(N,1))])
            assert len(self.identity.uid)==len(self._xyz)
            events.append({'event':'official_final_ambiguity_prune' if prune_only else 'official_boundary_split',
                'before':before,'selected_parent_uids':parents.tolist(),'after':len(self.identity.uid)})
    upstream.GaussianModel=Tracked;scene_module.GaussianModel=Tracked
    p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p)
    args=p.parse_args([]);args.text='object1';args.source_path=str(OUT/'data'/scene/'native_train')
    method='B4_mask_only' if mask_only else 'B4_official'
    args.model_path=str(OUT/'cob'/scene/method);args.eval=True;args.sh_degree=0;args.resolution=1;args.data_device='cpu'
    args.include_mask=True;args.finetune_mask=not mask_only;args.depth_l1_weight_init=0.;args.depth_l1_weight_final=0.
    args.mask_signals_threshold=.8;args.iterations=cfg['controls']['iterations']
    dataset=mp.extract(args);maskpath=Path(dataset.mask_path);maskpath.mkdir(parents=True,exist_ok=True)
    for frame in frames('train'):
        v=training_view(scene,frame)
        # Official synthetic loader uses Path(...).stem and get_mask appends no extension.
        Image.fromarray(((v['instance']==1)*255).astype(np.uint8)).save(maskpath/frame['id'],format='PNG')
    initial=OUT/'models'/scene/f'chkpnt{cfg["training"]["iterations"]}.pth'
    start=time.monotonic();torch.cuda.reset_peak_memory_stats()
    upstream.training(dataset,op.extract(args),pp.extract(args),14,[],[],[336],str(initial),-1)
    torch.cuda.synchronize();duration=time.monotonic()-start
    m=models[-1];directory=OUT/'controls'/scene
    cap=m.capture(include_mask=True)
    # Export colour/geometry checkpoint to the common stock evaluator; drop only mask latent.
    export=tuple(cap[:7])+tuple(cap[8:])
    torch.save((export,336),directory/f'{method}.pth')
    atomic_json(directory/f'{method}_identity.json',m.identity.as_dict())
    np.savez_compressed(directory/f'{method}_labels.npz',probability=m.label_probability)
    result={'scene':scene,'method':method,'executed_official_training':True,'component_only':False,
        'seed':seed,'iterations':336,'N4views':14,'mask_signals_threshold':.8,'include_mask':True,'finetune_mask':not mask_only,
        'mask_provenance':'nonlearned analytic training instance1 masks; SAM not installed',
        'initial_sha256':sha(initial),'checkpoint_sha256':sha(directory/f'{method}.pth'),
        'count_before':len(meta['uid']),'count_after':len(m._xyz),'events':events,
        'duration_seconds':duration,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
        'fixed_labels_note':'sidecar frozen labels/probabilities/anchors inherited at official splits; labels never enter official loss',
        'baseline_scope':'official global recovery updates xyz/scale/rotation/opacity/colors, final pruning retained; not our constrained edit',
        'RGB_renderer':'official COB newer dr_aa renderer, antialiasing False; calibration must qualify before joint quality claims',
        'actual_config':vars(args),'source':code_identity(),'guard':guard}
    atomic_json(EXP/f'results/manifests/{scene}_{method}.json',result)
    atomic_json(directory/f'{method}_edit.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--mask-only',action='store_true')
    a=p.parse_args();run(a.scene,a.mask_only)
