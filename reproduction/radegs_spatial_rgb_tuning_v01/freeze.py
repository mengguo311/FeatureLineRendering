import json,shutil,numpy as np
from common import *
import boundary
assert sha(C/'boundary.py')=='11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30'
assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(T).free>10*2**30
assert not (T/'PRESETS.json').exists(),'Freeze already exists; do not overwrite'
configs={'native':dict(scales=[.7,1.4,2.8]),'medium':dict(scales=[1.,2.,4.]),'coarse':dict(scales=[1.4,2.8,5.6])}
ps=[]
def add(id,field,lam,t,family):ps.append(dict(id=id,analysis=field,detail_lambda=lam,threshold=t,gain=1.,ink_sigma=.5,family=family))
for t in [.10,.15,.20,.30,.40,.50]:add('A'+str(round(t*100)),'native',1.,t,'threshold')
for lam in [.75,.5,.25,0.]:add('B'+str(round(lam*100)).zfill(2),'native',lam,.2,'branch_mix')
add('M75T30','native',.75,.3,'combined');add('M50T30','native',.5,.3,'combined')
for field,id in [('medium','C1'),('coarse','C2')]:
    add(id+'U20',field,1.,.2,'scales');add(id+'L50',field,.5,.2,'scales')
write(T/'PRESETS.json',dict(utc=utc(),presets=ps,analysis_configs={k:{**boundary.DEFAULT,**v} for k,v in configs.items()},expected_presets=16))
registry=[];files={};checks=[]
old=B/'depth_guided_native_dtu_v01'
manifest=json.loads((old/'OUTPUTS_MANIFEST.json').read_text())
def find_hash(obj,path):
    if isinstance(obj,dict):
        if obj.get('path')==str(path) and 'sha256' in obj:return obj['sha256']
        if str(path) in obj:
            v=obj[str(path)];return v if isinstance(v,str) else v.get('sha256')
        for v in obj.values():
            x=find_hash(v,path)
            if x:return x
    elif isinstance(obj,list):
        for v in obj:
            x=find_hash(v,path)
            if x:return x
for scene in ['scan24','scan65','ficus']:
    views=['train_r_80'] if scene=='ficus' else ['0000','0024','0048','0012','0036']
    for view in views:
        root=B/'synthetic_three_gaussian_v01' if scene=='ficus' else old
        p=root/'scenes'/scene/'inputs'/f'{view}.npz'
        h=sha(p);files[str(p)]=h
        with np.load(p) as z:rgb=z['rgb']
        assert rgb.dtype==np.float32 and rgb.ndim==3 and rgb.shape[2]==3 and np.isfinite(rgb).all()
        entry=dict(scene=scene,view=view,path=str(p),sha256=h,shape=list(rgb.shape),dtype=str(rgb.dtype),min=float(rgb.min()),max=float(rgb.max()),rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),split='reference BUILD' if scene=='ficus' else ('BUILD' if view in ['0000','0024','0048'] else 'seen construction holdout; sourceGS train'),condition='vanilla3DGS rendered RGB; separate Ficus reference' if scene=='ficus' else 'official corrected C24 RaDe-GS 30k native rendered RGB')
        if scene!='ficus':
            expected=find_hash(manifest,p);assert expected==h,(p,expected,h)
            original=B/'balanced_multiview_v02'/'evidence'/f'{scene}_{view}.npz'
            prior=json.loads((old/'SOURCE_FREEZE.json').read_text())['files']
            assert sha(original)==prior[str(original)];files[str(original)]=sha(original)
            with np.load(original) as z:assert np.array_equal(rgb,np.moveaxis(z['rgb'],0,-1))
            entry['original_exact_chw_source']=str(original)
        else:
            # The source package seals this generated input in its output manifest.
            found=None
            for name in ['OUTPUTS_MANIFEST.json','RESULTS_MANIFEST.json','REPLAY.json']:
                q=root/name
                if q.exists():
                    expected=find_hash(json.loads(q.read_text()),p)
                    if expected:
                        assert expected==h;found=str(q);files[str(q)]=sha(q);break
            entry['prior_output_manifest_match']=found
        registry.append(entry)
for p in [C/'boundary.py',old/'REGISTRY.json',old/'DATA_NATIVE_PROVENANCE.json',old/'SOURCE_FREEZE.json',old/'OUTPUTS_MANIFEST.json',B/'synthetic_three_gaussian_v01'/'REGISTRY.json',B/'synthetic_three_gaussian_v01'/'SOURCE_FREEZE.json']:
    files[str(p)]=sha(p)
write(T/'REGISTRY.json',dict(views=registry,expected_views=11,build_only_recipe_decisions=True))
write(T/'SOURCE_FREEZE.json',dict(utc=utc(),files=files,source_condition='RGB only. Native float32 values above 1 are NOT clipped before analyze. Preview RGB alone clipped to display range.',model_and_camera_provenance=str(old/'DATA_NATIVE_PROVENANCE.json')))
write(T/'PREFLIGHT.json',dict(root_free_GiB=shutil.disk_usage('/').free/2**30,hdd_free_GiB=shutil.disk_usage(T).free/2**30,task_cap_GiB=3,cpu_threads=2,source_files=len(files),raw_rgb_verified=11))
(T/'METHOD_FREEZE_ZH.md').write_text('''# Spatial RGB 检线预设冻结

这轮只处理 RGB 检线，不创建或修改 3D。参数冻结于查看新 EVAL 结果之前；3 个先行参考是 scan24/0000、scan65/0000、Ficus/train_r_80，随后不改参数应用其余 8 张 DTU 图。EVAL 均已在历史研究看过，不是盲测。

16 预设 × 11 张原生图。A10/A15/A20/A30/A40/A50 只改变严格 darkness>T 的候选门槛，A20 为现有 05 候选基线。B75/B50/B25/B00 使用 max(structural,lambda*detail)，T=.2；A20 是 lambda=1 对照。M75T30/M50T30 同时改混合与门槛，不能归因为单一因素。C1 的尺度为 [1,2,4]，C2 为 [1.4,2.8,5.6]，U20 使用完整 union，L50 使用 lambda=.5，两者 T=.2。这是算法尺度变化，不称为 DEFAULT。

所有图 gain=1、ink_sigma=.5，不做自适应对比度。soft=max(S,lambda D)，darkness=1-ink(soft)[...,0]，marked=darkness>T，skeleton=skeletonize(marked)。候选展示为 1-darkness*marked，不再做第二次模糊；另存二值 marked 和 skeleton，避免把淡化误称拓扑改变。保存未截断 soft 和 darkness，后续用户可重选，但本轮不改 05。

DEFAULT 原始分析器字节不变。weak/strong 只影响 structural 的连通滞后门槛；detail 可绕过 profile 拒绝。本轮不换 Canny、不用语义/深度/alpha、没有 ROI 保留掩码，没有形态闭合。RGB 保持输入 float32，包括渲染值大于1的部分；仅 RGB 显示裁剪到屏幕范围。

判断优先看屋脊/窗框、头骨外轮廓/鼻腔/牙齿/下颌、叶片/叶柄/枝条/花盆。强纹理不等于无用，弱线也不等于噪声。强门槛、纯结构、粗尺度均可能丢主体细节，负例完整交付。没有 GT，候选像素、骨架像素、8邻域分量/端点/结点只是诊断，不是真实信噪比，也不据此选最优。

测试先 RED 后 GREEN：原 union 和 lambda=1 位级相同，lambda=0 等于结构分支；门槛严格且嵌套；RGB-only 接口；有限范围；常量背景与弱真边/纹理合成控制；同图复算与原文件哈希不变。合成图只能证明机制，不能证明真实图中的纹理类别。
''')
status('PREFLIGHT_FROZEN',expected_presets=16,expected_views=11,expected_units=176,completed_units=0,children=[],next_action='RED tests then RGB-only wrapper; three BUILD/reference pilots')
print('FROZEN',len(ps),'presets',len(registry),'views',len(files),'sources')
