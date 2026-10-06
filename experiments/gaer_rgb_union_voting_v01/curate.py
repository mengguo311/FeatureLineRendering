"""Curate actual production sheets, exact tables and limited scientific conclusions."""
import json,csv,time
import numpy as np
from PIL import Image
from runtime import *
from media import sheet

def pooled(evaluations,method):
    rows=[r['metrics'][method] for r in evaluations];total=sum(r['full_T_selected_mass'] for r in rows)
    out=dict(selected_mass=total,leakage=sum(r['nonline']['selected_mass'] for r in rows)/max(total,1e-20))
    for region in ('line','interior_line','outline_line'):
        mass=sum(r[region]['selected_mass'] for r in rows);full=sum(r[region]['full_mass'] for r in rows);pixels=sum(r[region]['pixels'] for r in rows)
        out[region]=dict(mass_recall=mass/max(full,1e-20),pixels=pixels,
            selected_mass=mass,full_mass=full,gt01_rate=sum(r[region]['fraction_gt_01_pixels'] for r in rows)/max(pixels,1),
            gt05_rate=sum(r[region]['fraction_gt_05_pixels'] for r in rows)/max(pixels,1))
    return out

def curate():
    frozen=json.loads((ART/'PRODUCTION_FREEZE.json').read_text());final={};ranklines=[];summary=[];metriclines=[]
    for scene in ('lego','chair'):
        rec=json.loads((ART/'results'/(scene+'_COMPLETE.json')).read_text());vote=rec['vote'];z=np.load(ROOT/vote['vote_archive'])
        views=frozen['protocol']['visualization_views'];mdir=ART/'media'/scene
        panels=[];evidence=[];recurrence=[];baselines=[]
        for key in views:
            d=mdir/'display'/key
            for method in ('top100','top500','top2000','views_ge4'):
                n=vote['sets'][method]['count'];panels.append((key+' '+method+' n='+str(n)+'|same 8-view original-ID set, original SH3',Image.open(d/(method+'_selected_only.png')).copy()))
            for name,label in [('RGB','full original native SH3'),('spatial_union_ink','old RGB spatial union ink'),
                ('top500_selected_only','TOP500 native original SH3 only'),('top500_fullT_overlay','TOP500 original full-model T mass')]:
                evidence.append((key+' '+label+'|eight-view fixed TOP500',Image.open(d/(name+'.png')).copy()))
            for method in ('views_ge2','views_ge4','views_ge6'):
                recurrence.append((key+' '+method+' n='+str(vote['sets'][method]['count'])+'|ALL IDs meeting distinct-view threshold',Image.open(d/(method+'_selected_only.png')).copy()))
            for method in ('top500','center_top500','top2000','center_top2000'):
                baselines.append((key+' '+method+' n='+str(vote['sets'][method]['count'])+'|mandatory D vs mandatory center alphaT',Image.open(d/(method+'_selected_only.png')).copy()))
        sheet(mdir/'fourview_selected_only.png',panels,cols=4,tile=800,title=scene+' SAME FIXED IDs from 8 RGB marked source views | TOP100 / TOP500 / TOP2000 / V>=4')
        sheet(mdir/'fourview_evidence.jpg',evidence,cols=4,tile=800,title=scene+' RGB, old ink, fixed TOP500 native subset, full T contribution overlay')
        sheet(mdir/'fourview_recurrence.png',recurrence,cols=3,tile=800,title=scene+' exact all-ID recurrence sets V>=2 / V>=4 / V>=6 | no percentage cap')
        sheet(mdir/'fourview_mandatory_baseline.jpg',baselines,cols=4,tile=800,title=scene+' same masks, every valid pixel votes: endpoint D+fallback vs largest center alphaT')
        holdouts=[]
        for evaluation in rec['evaluation']:
            key=evaluation['view'];d=mdir/'eval'/key
            for name in ('RGB','spatial_union_ink','top500_fullT_overlay','center_top500_selected_only','top2000_selected_only','center_top2000_selected_only'):
                holdouts.append((key+' '+name+'|selection holdout; rank NOT refitted',Image.open(d/(name+'.png')).copy()))
        sheet(mdir/'two_holdout_views.jpg',holdouts,cols=6,tile=800,title=scene+' r_001 / r_014 reserved from voting | historical GS/research seen')
        fallback={}
        for v in rec['views']:
            for reason,count in v['fallback_reasons'].items():fallback[reason]=fallback.get(reason,0)+count
        pooled_metrics={m:pooled(rec['evaluation'],m) for m in ('top100','top500','top2000','views_ge2','views_ge4','views_ge6',
            'center_top500','center_top2000','random_top500','random_top2000','nofallback_top500','nofallback_top2000')}
        final[scene]=dict(original_N=vote['original_N'],source_views=8,selection_holdout_views=2,marked_pixels=vote['marked_pixels'],
            received_pixels=vote['received_pixels'],unassignable_pixels=vote['unassignable_pixels'],
            eligible_positive_vote_IDs=vote['eligible_positive_vote_IDs'],sets=vote['sets'],fallback_reasons=fallback,
            endpoint_only_best_pixels=sum(v['endpoint_only_best_pixels'] for v in rec['views']),
            unknown_positive_pixels=sum(v['unknown_positive_pixels'] for v in rec['views']),
            source_regions={name:{field:sum(v['regions'][name][field] for v in rec['views']) for field in ('marked','received')} for name in ('line','interior_line','outline_line','exterior_line')},
            pooled_holdout_fullT_metrics=pooled_metrics,main_vs_center_top500_jaccard=vote['main_vs_center_top500_jaccard'],
            main_vs_center_top2000_jaccard=vote['main_vs_center_top2000_jaccard'],random_check=vote['random_check'],
            K_sensitivity_per_view={v['view']:v['K_sensitivity'] for v in rec['views'] if v['K_sensitivity']},K_aggregate=vote['K_four_view_aggregate_sensitivity'],
            drop_one_view_stability=vote['drop_one_view_stability'],
            actual_production_seconds=sum(v['end_to_end_seconds'] for v in rec['views']+rec['display']+rec['evaluation'])+vote['end_to_end_seconds'],
            fullSH3_native_original_verified=True)
        f=final[scene]
        summary.append(f"| {scene} | {f['marked_pixels']:,} | {f['received_pixels']:,} | {f['unassignable_pixels']:,} | {f['eligible_positive_vote_IDs']:,} | {f['sets']['views_ge2']['count']:,} / {f['sets']['views_ge4']['count']:,} / {f['sets']['views_ge6']['count']:,} |")
        for m in ('top500','center_top500','random_top500','nofallback_top500','top2000','center_top2000','random_top2000','nofallback_top2000'):
            p=pooled_metrics[m];metriclines.append(f"| {scene} | {m} | {p['line']['mass_recall']:.4%} | {p['interior_line']['mass_recall']:.4%} | {p['outline_line']['mass_recall']:.4%} | {p['line']['gt01_rate']:.3%} / {p['line']['gt05_rate']:.3%} | {p['leakage']:.2%} |")
        with (ROOT/vote['top100_csv']).open() as file:
            rows=list(csv.DictReader(file))
        for row in rows[:10]:ranklines.append(f"| {scene} | {row['rank']} | {row['original_ID']} | {row['raw_pixel_frequency']} | {row['distinct_views']} | {float(row['fallback_fraction']):.2%} |")
    atomic_json(ART/'FINAL.json',dict(status='COMPLETE_ENGINEERING_EXPLORATORY_VISUALS',scenes=final,
        interpretation='mandatory labeling produces line-support candidates, not permanent physical edges; multiview recurrence not temporal stability or 3D curve proof',
        novelty_claim=False,source_freeze_sha256=sha(ART/'PRODUCTION_FREEZE.json')))
    report='''# RGB 标注像素强制推核与八视角频率统计：实际结果

两场景均已完成：复用此前 RGB spatial union 显示墨迹，每个有中心可见原始 Gaussian 的标注像素投出恰好一票，再按八视角累计原始像素频率选固定核集合。没有沿用旧自动 REFUSED/平面 null floor，也没有把内部线排除。输出是 **line-support candidate（线像素支持候选核）**，不是永久物理边缘核。

## 先看实际图

| 场景 | 四相机原始核子集 TOP100 / TOP500 / TOP2000 / V≥4 | 完整 RGB、旧墨迹、TOP500 子集与 full-T 支持 | V≥2 / 4 / 6 全部核 | 强制中心最大权重对照 | 两个计票保留相机 |
| --- | --- | --- | --- | --- | --- |
| Lego | [四视角 selected-only](media/lego/fourview_selected_only.png) | [完整定位](media/lego/fourview_evidence.jpg) | [跨视角复现](media/lego/fourview_recurrence.png) | [对照](media/lego/fourview_mandatory_baseline.jpg) | [r_001/r_014](media/lego/two_holdout_views.jpg) |
| Chair | [四视角 selected-only](media/chair/fourview_selected_only.png) | [完整定位](media/chair/fourview_evidence.jpg) | [跨视角复现](media/chair/fourview_recurrence.png) | [对照](media/chair/fourview_mandatory_baseline.jpg) | [r_001/r_014](media/chair/two_holdout_views.jpg) |

主集合 TOP500、诊断 TOP100/TOP2000 在实测计票前固定；四行 r_000/r_008/r_018/r_030 使用同一套原始 IDs。V≥4 列包含所有满足四视角出现条件的核，真实数量写在图里。selected-only 图只保留原 SH3/位置/尺度/旋转/透明度，移除其他核会改变 T。full-T contribution 在完整模型不删核时用独立特征通道测量，紫红叠加 gain=6；频率图是 log1p(F)/log1p(maxF) 原始核特征在完整 T 下的贡献，gain=8。它们是诊断展示，不是修改原核颜色，也不是黑色艺术线条。

## 冻结输入与分配

每场景使用 DEV r_007/r_033/r_059/r_086 和固定 r_000/r_008/r_018/r_030，共八个不同外参；没有把 33 个邻近 arc 帧称为独立视角。r_001/r_014 的不同外参在计票前保留，只用于固定集合评价。十个相机均为历史 GS/研究见过的探索性相机，保留相机也不是正式盲测。

标注来自原 float32 `union` 经旧 `ink(gain=1,sigma=.5)` 的显示 darkness>0.2；每个整数像素都保留，没有再侵蚀/NMS/膨胀筛掉标注。弱墨迹 `0<darkness≤.2` 单独保存与计数。旧 RGB-only spatial union 没有混入 temporal 或 alpha 辅助轮廓。八个缓存 RGB 与实际 stock/fullSH3/K8 输出逐位相等，旧四张显示 PNG 对应墨迹逐像素相等；r_000 的同算法重算 union/normal/confidence 逐位相等。完整 K、w2c、800×800 RGBA 与实际 metadata 文件名匹配和哈希在 [生产冻结](PRODUCTION_FREEZE.json)。

使用旧张量 normal（等价旧切线旋转 90°，符号无关），不是二值线图梯度。沿 normal 两侧 δ=2 做四邻居双线性采样，按原始 ID 合并贡献，不插值 top-K 槽位。候选是中心及两侧 ID 并集；主接收核必须在中心有 `w_i(p)>0`。对中心可见候选取最大 `D_i=|w_i(p−2n)−w_i(p+2n)|`。D≤2e−6、旧方向 confidence<.22/不定义、两侧截断残量大于最大 D 或端点越界时，回退到中心最大 alpha·T，等值按最小原始 ID。

这些可靠性条件只决定 D 或回退；不取消有真实贡献的像素的票。中心无可见贡献的标注像素保留在 mask，记 `UNASSIGNABLE_BACKGROUND` 并存坐标/地图。端点最佳核若中心权重为零，只在诊断中记录，不能接收该像素。K8 缺失端点 ID 的质量是未知，所选 D 最优仅针对保留的中心候选，不能宣称全 N 最优或像素因果责任。

## 实际计票

`c_iv=bincount(winnerIDs,minlength=originalN)`；主要排名 `F_i=Σ_v c_iv`，同票按 distinct-view `V_i` 降序再 original-ID 升序。另存 `Σ_v c_iv/marked_pixel_count_v`、曝光次数/可见质量归一化诊断，均不替代主频率。一个核同视角赢一百像素，V 仍只增加一。

| 场景 | 标注像素（8图累计） | 收到一票 | 无中心贡献 | 得票核数 | V≥2 / ≥4 / ≥6 核数 |
| --- | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(summary)+'''

完整每视角标注/弱墨迹/回退/未知/内外域数据见 [FINAL.json](FINAL.json) 和 `results/*vote*.json`。八视角出现频率与核投影面积、可见质量、遮挡、纹理和图像细节密度混杂；宽核可赢很多像素。强制完整分配是工程契约，不是算法效果的证据。

| 场景 | raw 排名 | original ID | raw 像素票 | 出现视角数 | 回退票比例 |
| --- | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(ranklines)+'''

[Lego TOP100 CSV](downloads/lego_top100.csv)、[Chair TOP100 CSV](downloads/chair_top100.csv)；[Lego 完整 N 行计数/固定 IDs](downloads/lego_votes_all_original.npz)、[Chair 完整 N 行计数/固定 IDs](downloads/chair_votes_all_original.npz)。`downloads/<scene>/<view>/source_fields.npz` 保存 float32 RGB/union/ink/normal/confidence 和未改二值 mask；`assignment.npz` 保存 int32 winner_map、fallback_map、原始 N 计数、选中中心权重、D、未知残量、端点替代诊断。未保存新模型。

## 保留视角效果与对照

实际 full-model T 支持质量在两保留相机的旧 RGB 标注域上评价；质量召回=所选核在标注域的贡献/完整 alpha 贡献。阈值覆盖率统计 selected/full-alpha>.1 或 .5 的像素比例，独立于质量召回。屏幕内部定义原 alpha>.5 的 SDF>4，轮廓域为 |SDF|≤4，仅区分屏幕覆盖区域，不等于几何或材质语义。

center 对照在每个相同可分配像素强制选最大中心 alpha·T，再按相同 raw 票排名。random 与主集合等数量，按八源视角全模型可见质量的 .1 宽 log bin 逐核匹配，从所有原始核无放回抽样；匹配质量误差和重叠核数如实保留。nofallback 只保留可靠 D 的票，是拒绝/无回退消融，不能满足主强制契约。下表以两个保留视角质量/像素累计计算，未用它们调排名。

| 场景 | 固定集合 | 线域质量召回 | 内部线质量召回 | 轮廓线质量召回 | 线像素覆盖 >.1 / >.5 | 非线域泄漏质量占比 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(metriclines)+'''

质量支持来自真实 native 特征渲染，不用投影中心当覆盖。删除其他核后的 selected-only 图不能当 full-T 覆盖图。即使 D 很大，核仍可能支持广阔平面；泄漏和可见质量归一化诊断用来显示这一点。此阶段应以保留视角实际视觉和对照表判断用途，不把 100% 可分配像素投票称为成功。

## 验证、限制与复现

先做 RED 缺接口，再通过九项 CPU 契约测试和独立 CPU 原生射线/full-T 特征检查。每场景 original PLY 解码与官方 GaussianModel 的位置、全 16×3 SH3、opacity/scale/rotation 逐位相等。每视图 stock/K8/fullSH3 RGB 逐位相等；每种渲染后完整原 RGB 再检查。四源视角 r_007/r_000/r_018/r_030 实跑 K16/32，保存每像素赢家变化、票数变化和同四图 TOP500/2000 Jaccard；未把四图敏感性说成八图 K32 实验。drop-one-view 仅从已存计数重排。

独立脚本用保存的原始 ID 缓冲区、标量字典采样和全 N 计数审计，不依赖主 assignment 实现；所有 source/display/eval 单元原子写文件并封 SHA，可恢复验证。运行秒数是每单元真实 wall time，详情见 FINAL。旧模型、metadata、源代码和旧目录已有 dirty reproduction/verification 文件保留原字节；保护审计见 `tests/PROTECTED_AFTER.json`。GPU0 按 PID 检查独占，CPU2、root 4GiB/Git 1.5GiB reserve、新阶段 8GiB cap 固定；无安装、新 kernel、训练、协方差优化或新增 primitives。

结论仅支持强制映射与固定多视角候选集合可运行、可视化。它没有证明永久物理边、3D 曲线或时间稳定性；正式语义/几何 GO 尚无证据。旧 RGB detector 的主要外观来自既有颜色结构张量组件，新增双侧 profile 的作用有限。GAER top-K ID/alpha·T 与邻域 raster-state 归因思想与 Hao/Mukai 作者稿有关；本轮是不同的强制像素映射与计票实验，不宣称方法新颖性。

[复现说明](REPRODUCE.md)、[来源映射](SOURCE_MAP.json)、[媒体与下载哈希](MEDIA_MANIFEST.json)、[独立审计](tests/INDEPENDENT_AUDIT.json)。主代理实际图片审阅单独记录在 `tests/VISUAL_REVIEW.json`；它不是独立人工语义真值。
'''
    scoped(ART/'REPORT_ZH.md').write_text(report)
    reproduce='''# Reproduce

Run from this branch/worktree with the existing verified dependencies and Python:

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/tests/test_contract.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/tests/test_native.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/run.py --scene both
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/curate.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -B experiments/gaer_rgb_union_voting_v01/verify.py
```

No installation or build is required. `binding.py` loads the verified attribution binary from `/home/u00134/3dgs_line/gaer_attribution_buffer_v01/out/gaer_attribution_buffer_v01`, the stock binary from the old native foundation, and read-only fullSH3 APIs. Exact float32 source fields/RGB come from `/home/u00134/3dgs_line/image_space_edge_foundation_v1/out/image_space_edge_foundation_v1/{dev_fields,fixed_fields,raw}`. Absolute models/cameras, source field hashes, archival RGBA and metadata hashes are in PRODUCTION_FREEZE.json. These existing datasets/models/binaries are required; no portable model is included.

The runner freezes protocol + every method source hash BEFORE the first production vote. It independently handles both scenes and logs a scene failure without suppressing the other scene. `--scene lego` / `--scene chair` resume separately. Each sealed unit checks config and every output byte before skipping; original arrays accumulate in Python from the eight saved per-view counters. All final files use atomic replacement, and seal completion is atomic. An interrupted unsealed unit can be recomputed under the same freeze; a changed sealed input/method/output is rejected and retained as evidence. Production source must not be edited after freezing.

For a fresh rerun, preserve the existing artifacts and run in a new isolated worktree with the three stage paths absent except TASK/launch. All other dependencies remain read-only. The runner only writes experiments/gaer_rgb_union_voting_v01, artifacts/gaer_rgb_union_voting_v01 and ignored out/gaer_rgb_union_voting_v01. Resource checks fail on foreign GPU0 PIDs and fixed storage reserves/cap; no foreign process termination.

Downloads contain all original-N votes, rankings and fixed set IDs plus native 800x800 per-pixel winners/fallback/source fields. Raw K8 contributor buffers and full-T contribution maps remain in ignored out with seals, not model files. Media include native resolution selected-only originals, contribution diagnostics, two reserved views, mandatory center baseline and visibility-matched random controls. No videos are needed for this stage. SOURCE_MAP and MEDIA_MANIFEST contain SHA256 provenance; verify.py performs independent dictionary scalar checks and decodes exported media.
'''
    scoped(ART/'REPRODUCE.md').write_text(reproduce)
    sources=dict(production=frozen['source_method_files'],read_only_dependencies={p:h for p,h in frozen['protected_before'].items() if '/experiments/' in p or p.endswith('.so')},
        prior_RGB_detector='exact frozen RGB-only spatial union with classical color tensor and limited new normal-profile contribution; no temporal/alpha augmentation',
        native_attribution='existing verified original-ID top-K alpha*T accepted contributions; no binary/kernel changes',
        new_stage='mandatory original visible center receiver, sparse original-ID side differences, fallback, raw multiview frequency and fixed subset evaluation',
        paper_relation='Hao/Mukai SA2026 author preprint top-K primitive attribution/raster states; this is an independent forced-label voting experiment, no novelty claim',
        citations=[dict(title='Hao/Mukai author preprint',url='https://mukai-lab.org/content/SA2026PosterHao.pdf',source='prior attribution stage source attribution'),
            dict(title='Coherent Line Drawing',url='https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf',relation='prior direction-field/flow-based line drawing; no claimed reproduction')],novelty_claim=False)
    atomic_json(ART/'SOURCE_MAP.json',sources)
    manifest=[]
    for path in sorted((ART/'media').rglob('*'))+sorted((ART/'downloads').rglob('*')):
        if path.is_file():
            item=dict(path=relative(path),bytes=path.stat().st_size,sha256=sha(path))
            if path.suffix in ('.png','.jpg'):
                with Image.open(path) as im:item.update(width=im.width,height=im.height)
            manifest.append(item)
    atomic_json(ART/'MEDIA_MANIFEST.json',dict(files=manifest,count=len(manifest),total_bytes=sum(x['bytes'] for x in manifest)))
    print(json.dumps({s:{k:v[k] for k in ('marked_pixels','received_pixels','unassignable_pixels','eligible_positive_vote_IDs','actual_production_seconds')} for s,v in final.items()},ensure_ascii=False),flush=True)

def relative(p):return str(p.relative_to(ROOT))
if __name__=='__main__':curate()
