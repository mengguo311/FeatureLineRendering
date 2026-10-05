import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import ART,OUT,command,sha,atomic_json

files={
 'gaussian-splatting':['README.md','LICENSE.md','train.py','arguments/__init__.py','scene/gaussian_model.py','scene/dataset_readers.py','gaussian_renderer/__init__.py','submodules/diff-gaussian-rasterization/LICENSE.md','submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu','submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu'],
 'gaussian-grouping':['README.md','LICENSE','train.py','arguments/__init__.py','scene/gaussian_model.py','gaussian_renderer/__init__.py','utils/loss_utils.py'],
 'COB-GS':['README.md','LICENSE.md','train.py','arguments/__init__.py','scene/gaussian_model.py','gaussian_renderer/__init__.py','submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu','submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu','submodules/diff-gaussian-rasterization/LICENSE.md']}
records={}
for name,paths in files.items():
    repo=OUT/'vendor'/name;commit=command(['git','-C',str(repo),'rev-parse','HEAD'])
    origin=command(['git','-C',str(repo),'remote','get-url','origin'])
    records[name]={'commit':commit,'origin':origin,'files':{
        p:{'sha256':sha(repo/p),'citation':origin.removesuffix('.git')+'/blob/'+commit+'/'+p} for p in paths},
        'read_entrypoints':True}
records['official_link_verification']={
 'Gaussian_Grouping':'https://arxiv.org/html/2312.00732v2 author code/model link https://github.com/lkeab/gaussian-grouping',
 'COB_GS':'official README links paper https://arxiv.org/abs/2503.19443'}
records['settings']={
 '3DGS_defaults':{'iterations':30000,'lambda_dssim':.2,'densify_until':15000,'densify_from':500,'interval':100,'gradient_threshold':.0002,'opacity_reset':3000},
 'COB_GS_README_exact_mask_flags':'--include_mask --finetune_mask --N4views 14 --mask_signals_threshold 0.8',
 'COB_code_default_N4views':10,
 'COB_signal':'backward.cu: count negative/positive mask pixel gradient signs for accepted Gaussian-pixel entries, unweighted counts',
 'COB_split':'gaussian_model.py:736-779 mean absolute relative foreground/rest counts <0.8; scale > percent_dense*extent; two samples; scale /(0.8*N); final prune_only',
 'Gaussian_Grouping':'identity-feature image CrossEntropy plus periodic 3D neighbour regularization; not equal to one-hot contribution maps',
 'compiler_compatibility':'stock source unchanged; nvcc force-includes cstdint; simple-knn force-includes cfloat'}
atomic_json(ART/'source_bindings/upstream.json',records)
