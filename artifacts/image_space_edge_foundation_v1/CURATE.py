"""Curate actual results and public provenance. Never changes production media."""
import json,os,re,shutil,sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,EXP,NATIVE,sha,atomic_json,guard

def read(name):return json.loads((ART/name).read_text())
def run():
    guard('curate_CPU');audit=read('tests/INDEPENDENT_AUDIT.json');assert audit['status']=='PASS'
    freeze=read('PRODUCTION_FREEZE.json');match=read('DEV_MATCHING.json');synth=read('results/synthetic.json')
    fixed={s:read(f'results/{s}_fixed_spatial.json') for s in ['lego','chair']}
    temporal={s:read(f'results/{s}_temporal.json') for s in ['lego','chair']}
    controls={s:read(f'results/{s}_anchored_control_fixed.json') for s in ['lego','chair']}
    anchored=read('results/anchored_control_synthetic.json');lag=read('tests/TEMPORAL_CONTROL_AUDIT.json')
    ablation=read('PROFILE_ABLATION.json')
    # All full raw logs stay in out. Curated text substitutes only workspace/env
    # prefixes, with byte hashes of the original source logs retained below.
    logs={}
    for p in sorted((OUT/'logs').glob('*.txt')):
        if p.name=='CURATE_RUN.txt':continue
        logs[str(p.relative_to(ROOT))]=sha(p)
        text=p.read_text(errors='replace').replace(str(ROOT),'$WORKSPACE').replace('/home/u00134/bin/miniconda3/envs/vfsdgs','$PYTHON_ENV')
        (ART/'logs').mkdir(exist_ok=True);(ART/'logs'/p.name).write_text(text)
    for p in (ART/'tests').glob('*.txt'):
        raw=OUT/'logs'/('original_'+p.name)
        if not raw.exists():shutil.copyfile(p,raw)
        text=raw.read_text(errors='replace').replace(str(ROOT),'$WORKSPACE').replace('/home/u00134/bin/miniconda3/envs/vfsdgs','$PYTHON_ENV')
        p.write_text(text)
    resource=OUT/'logs/RESOURCE_GATE.jsonl'
    if resource.exists():
        shutil.copyfile(resource,ART/'logs/RESOURCE_GATE.jsonl')
        logs[str(resource.relative_to(ROOT))]=sha(resource)
    summaries={}
    for scene,d in fixed.items():
        rows=d['records'];summaries[scene]=dict(fixed_views=4,candidates=sum(r['profiles'] for r in rows),
            valid_profiles=sum(r['valid_profiles'] for r in rows),profile_increased_union_pixels=sum(r['profile_union_change_pixels'] for r in rows),
            total_union_ink_area=sum(r['metrics']['detail_union']['ink_area'] for r in rows),
            total_structural_ink_area=sum(r['metrics']['structural']['ink_area'] for r in rows),
            arc_native_frames=33,temporal=temporal[scene]['aggregate'],failure_frames=temporal[scene]['failure_frames'],
            RGB_control_changed_pixels={a:sum(r['arms'][a]['changed_pixels'] for r in controls[scene]['records']) for a in ['sharpen','soften']})
    decisions={
      'representation_and_native_execution':dict(status='GO',scope='engineering: actual per-view RGB fields, profiles and 2D chains; no 3D selection'),
      'structural_layer_as_complete_line_drawing':dict(status='NO-GO',reason='necessary studs, upholstery pattern, trim/legs often missing; do not replace union with this sparse layer'),
      'RGB_only_generous_union':dict(status='PARTIAL',reason='recognizable complete-object prototype; dense/shading double contours remain and real superiority to classic control is unproven'),
      'analytic_color_profile_interface':dict(status='GO',scope='constructed color step/constant/low contrast/stripes/corners/junctions; not material or geometry semantics'),
      'temporal_regularizer':dict(status='PARTIAL',reason='zero unsupported ghosts under current-evidence guard; motion-corrected error lower but line churn remains high'),
      'temporally_stable_finished_video':dict(status='NO-GO',reason='Chair exceeds frozen .2 spatial motion-error alarm on 31 transitions; perceptual stable-video superiority is not established'),
      'original_RGB_width_candidate':dict(status='NO-GO',reason='25 new clipped channel values across six fixed images and a constructed reverse slope; all original evidence retained'),
      'anchored_guarded_RGB_stylization':dict(status='PARTIAL',reason='known transition monotonic/no overshoot plus fixed exact outside/nonedge/alpha/no-new-clipping guards pass; small local edits, real photorealistic repair not established'),
      'independent_human_semantic_visual_review':dict(status='PENDING',reason='primary agent inspected actual exported media; independent human review pending')}
    media={}
    for p in sorted(ART.rglob('*')):
        if p.is_file() and p.suffix.lower() in ['.png','.jpg','.mp4','.npz']:
            media[str(p.relative_to(ROOT))]=dict(sha256=sha(p),bytes=p.stat().st_size)
    raw={}
    for name in ['raw','dev_fields','fixed_fields','arc_fields','temporal','synthetic','anchored_synthetic','guarded_RGB','guarded_RGB_v2']:
        for p in sorted((OUT/name).rglob('*')):
            if p.is_file():raw[str(p.relative_to(ROOT))]=dict(sha256=sha(p),bytes=p.stat().st_size)
    for scene in ['lego','chair']:
        for p in sorted((OUT/scene/'dev').rglob('*')):
            if p.is_file():raw[str(p.relative_to(ROOT))]=dict(sha256=sha(p),bytes=p.stat().st_size)
    atomic_json(ART/'DEVELOPMENT_HISTORY.json',dict(
        first_pngs={'role':'unsealed pre-freeze development previews, r_007 only; not fixed evaluation or DEV matching inputs',
                    'early_structural_strength':'quality * valid, before the frozen sqrt(quality) presentation',
                    'early_source_hash':None,'reason':'first preview produced before source freeze; retained as development evidence',
                    'native_PNG_encoding':'first preview floor-to-uint8; frozen production uses shared round-to-uint8'},
        errors_retained=['missing initial interface','initial band-mean assertion corrected to within-truth-band ridge peak',
                         'full native profile remap SHRT_MAX limit fixed by chunking without candidate truncation',
                         'original control new clipping and reverse slope; anchored guard separately validated'],
        frozen_production_media='media/<scene>/fixed and arc, fully sealed; first_* PNGs excluded from comparisons'))
    atomic_json(ART/'MANIFEST.json',dict(schema='actual-media-and-raw-fields-v1',media=media,ignored_raw=raw,
        total_media_bytes=sum(v['bytes'] for v in media.values()),media_files=len(media),ignored_raw_files=len(raw),
        no_PLY_or_checkpoints=True,raw_agent_logs_committed=False))
    citations=[dict(title='Coherent Line Drawing',authors=['Henry Kang','Seungyong Lee','Charles K. Chui'],year=2007,
        url='https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf',retrieved='2026-10-06',source='author university PDF',
        relation='prior direction field and flow-based DoG line drawing; this prototype does not reproduce ETF/FDoG'),
        dict(title='Video Watercolorization using Bidirectional Texture Advection',authors=['Adrien Bousseau','Fabrice Neyret','Joelle Thollot','David Salesin'],year=2007,
        url='https://research.adobe.com/publication/video-watercolorization-using-bbidirectional-texture-advection/',retrieved='2026-10-06',source='author research organization publication page',
        relation='prior flow-guided temporal NPR; this prototype only warps evidence-clamped soft response')]
    atomic_json(ART/'CITATIONS.json',citations)
    sources=dict(production=freeze['source_hashes'],postproduction={str(p.relative_to(ROOT)):sha(p) for p in sorted(ART.glob('*.py'))},
       dependencies={'stock_rasterizer_sha256':sha(NATIVE/'build/stock/onec_stock_C.so'),'knn_sha256':sha(NATIVE/'build/knn/onec_knn_C.so'),
                     'data_freeze_sha256':freeze['data_freeze_sha256'],'prior_input_sha256':freeze['prior_input_sha256']},
       model_sha256={s:d['model_sha256'] for s,d in freeze['scenes'].items()},
       layer_provenance={
          'native_RGB':'native.py: stock full SH3, original 30k, immutable model; cameras in PRODUCTION_FREEZE',
          'evidence':'boundary.py tensor_field: Gaussian derivatives, opponent/luminance tensor, scale/directional agreement; raw full fields saved',
          'profiles':'boundary.py fit_profiles: robust sides, signed RGB contrast, plateau variance, monotone width/center and bounded residual; rejected detail retained',
          '2D_chains_and_ink':'boundary.py analyze/chains/ink: screen-space ridge/hysteresis, tangent support; arc-length coherence statistics, no UID/lifting gate',
          'temporal':'boundary.py flow_pair/blend_temporal: actual RGB bidirectional Farneback, confidence/occlusion check and evidence clamp; same spatial OFF/ON',
          'alpha_aux':'native alpha independently rendered with all primitives; alpha_outline; POST_LAYER_CLASSIFICATION is separate auxiliary coverage diagnostic',
          'RGB_control':'POST_CONTROL_ANCHORED: frozen two-side fit inverse composition, endpoint anchoring; clipping/nonedge/exterior reset; no ink recoloring'},
       logs_original_sha256=logs,development_history='DEVELOPMENT_HISTORY.json',prior_artifacts_read_only=True,citations=citations,novelty_claim=False,published_method_reproduction=False)
    atomic_json(ART/'SOURCE_MAP.json',sources)
    final=dict(status='PARTIAL',actual_execution_complete=True,branch='image-space-edge-foundation-v1',base=freeze['base'],start_head=freeze['start_head'],
         counts=dict(native_RGB_inputs=82,DEV_views=8,fixed_views=8,arc_views=66,scenes=2,synthetic_interfaces=7,moving_control_frames=7,
             videos=4,decoded_video_frames=sum(v['decoded_frames'] for v in audit['videos']),foundation_unittests=8,
             independent_audit_checks=audit['checks'],sealed_units=audit['seal_units'],media_files=len(media)),
         decisions=decisions,scenes=summaries,baseline_matching=match['residuals'],profile_ablation=ablation,input_integrity=dict(protected_files=audit['protected_files'],
              changed_files=audit['protected_changes'],model_sha256_after=audit['model_sha256_after'],old_heads_unchanged=audit['old_branch_heads_unchanged']),
         actual_videos=audit['videos'],known_width_control=anchored['records'],moving_lag=lag,
         media_manifest_sha256=sha(ART/'MANIFEST.json'),production_freeze_sha256=sha(ART/'PRODUCTION_FREEZE.json'),
         resume_verification=read('tests/RESUME.json') if (ART/'tests/RESUME.json').exists() else None,
         parameters_frozen_before_fixed_arc=True,RGB_control_fix_post_hoc=True,fresh_blind=False,physical_material_edge_truth=False,
         underlying_3D_geometry_improved=False,photorealistic_repair_established=False,independent_human_review='pending')
    atomic_json(ART/'FINAL.json',final)
    lines=['# 图像空间边界场基础实验：实际结果',
      '', '结论：**PARTIAL**。新表示已实际落地为逐视图二维法向剖面、软线场与笔划链。完整 SH3 冻结 3DGS 只提供 RGB 和独立 alpha 辅助层。两场景完整物体线稿与真实连续相机视频已产出，尚未证明真实场景优于经典图像方法。结构层单独使用为 NO-GO；联合细节层保留了必要图案，但仍繁杂且包含明暗双线。',
      '', '这是一项视图相关的屏幕空间线绘/局部风格化实验。没有修改底层 3D 几何，没有物理材质边界认证，没有建立无目标条件下的照片级修复。3D 方法的其他可能性未在此排除。',
      '', '## 实产物与视角', '',
      f"主运行有 **82 个 800×800 原生 RGB 输入**：8 DEV、8 固定评价、66 arc；每场景固定 r_000/r_008/r_018/r_030 与完整 arc0_000…032。另有开发前预览和 stock Camera 重复校准，不把重复校准算作新的评价相机。4 条 H264/yuv420p/faststart 视频共 **132 解码帧**；每条去掉文字栏的 33 个原生 RGB 都实际不同。独立审核 {audit['checks']} 项通过，{audit['protected_files']} 个保护文件字节不变，旧分支未动。",
      '', '所有相机均为历史 GS/研究见过的探索性视角，不是新盲测。旧 w2c/FoV 原样沿用，K 恢复到原生 800 尺寸；与官方 Camera 的两场景 DEV 校准最大差都是 0。原 TRAIN 图仅为同相机对照，不是物理线真值，未读取原始 TEST 照片。',
      '', '| 场景 | 四视角纯线图 | 同 RGB 叠加 | 33 帧线稿视频 | 33 帧叠加视频 | 每一帧实际图条 |',
      '| --- | --- | --- | --- | --- | --- |']
    for scene in ['lego','chair']:
        lines.append(f'| {scene} | [完整对象六层](media/{scene}/fourview_line_only.png) | [叠加](media/{scene}/fourview_overlays.jpg) | [lines](media/{scene}/arc/lines_33.mp4) | [overlays](media/{scene}/arc/overlays_33.mp4) | [全部33帧](media/{scene}/arc/all33_actual_strip.jpg) |')
    lines+=['', '逐视角 `media/<scene>/fixed/<key>/full_object.jpg` 包含 reference/native/Canny/classic/结构/联合/叠加/alpha 辅助。该目录还有 standalone ink/overlay、320×320 原生 crop、2× 最近邻 zoom、confidence/unknown/width 与法向采样图。视频首/中/末帧保存为 `lines_000/016/032.png`、`overlays_000/016/032.png`；原生 RGB 及全帧联系表也在 arc 目录。MANIFEST 对媒体、float16 公开场、float32 完整 out 场/剖面/2D chains/flow 给出真实哈希。',
      '', '## 基础方法与对照', '',
      '多尺度 display-RGB 亮度/颜色对手通道的结构张量形成无向法/切线场；空间张量积分、沿切线方向支持与尺度方向一致性形成置信度。沿图像法向采样，使用双侧中位颜色、带符号 RGB 对比、平台方差、离散单调 logistic 宽度/中心拟合及颜色残差；局部不可信剖面留在 DETAIL/UNKNOWN。宽软响应、ridge、hysteresis 与切线邻域支持生成线场与二维链。没有 top10%/固定群数、3D lifting 或 Gaussian UID 门槛。',
      '', '主 RGB-only classmap 的“合格颜色过渡”不区分物体外部/内部。独立 `alpha_aux_classes` 用原生覆盖把 alpha 外轮廓、覆盖内部的清晰颜色拟合、detail/unknown 和覆盖不确定分别标出；它不更改 RGB-only 墨迹，内部覆盖也不等于几何/材质语义。方向图在低 confidence 区域没有可信法向含义。所有方法使用同一 stock float32 RGB；PNG/视频共用 display clamp 与编码，未降低 SH 阶数。',
      '', '```mermaid', 'flowchart LR', '  R[冻结 fullSH3 renderer] --> I[RGB]', '  I --> E[多尺度颜色方向证据]', '  E --> P[双侧法向剖面]', '  E --> D[细节与未知软响应]', '  P --> S[合格过渡结构层]', '  D --> U[完整联合软墨迹与2D链]', '  S --> U', '  U --> T[可选光流与当前证据守卫]', '  U --> V[线稿与RGB叠加]', '  T --> V', '  P --> C[可选有界RGB宽度风格化]', '  R --> A[独立native alpha辅助轮廓]', '```',
      '', '对照是 RGB-only Canny 与经典多尺度亮度结构张量梯度；后者是既有组件的简单独立实现，没有冒充 FDoG 论文复现。相同 ink 函数呈现，DEV 只匹配可见墨迹面积与 skeleton 长度。两场景共享 Canny high=60/low=24/gain=.6，classic gain=1.2；匹配后仍有以下残差，并保留 default Canny45、classic raw 和 broad soft 未匹配图。',
      '', '| 对照 | DEV 面积比 | DEV 长度比 |', '| --- | ---: | ---: |']
    for name,m in match['residuals'].items():lines.append(f"| {name} | {m['area_ratio']:.6f} | {m['length_ratio']:.6f} |")
    lines+=['', '这些匹配目标只用于墨迹预算公平性，不认证真实边缘语义。固定真实 ROI 在生产前冻结，整物体图是主要评价，不以少数 patch 的改善替代完整表示。',
      '', f"还直接公开冻结的 RGB 颜色张量/方向支持组件、移除剖面增强的对照（gain=1）。DEV 面积比 {ablation['DEV_area_ratio']:.6f}、长度比 {ablation['DEV_length_ratio']:.6f}，预算本已很接近；8张固定图的平均像素增量仅 {np.mean([r['pixel_MAE'] for r in ablation['records']]):.8f}。[Lego 剖面消融](media/lego/fourview_profile_ablation.png)、[Chair 剖面消融](media/chair/fourview_profile_ablation.png)。这是冻结 detail 层的后审计展示，未调新参数；它明确表明联合线稿的大部分外观来自既有颜色结构组件，剖面新增的视觉作用有限。",
      '', '| 场景固定4图 | 剖面候选 | 合格剖面 | 剖面增加联合强度的像素 | 结构/联合墨迹面积 |', '| --- | ---: | ---: | ---: | ---: |']
    for scene,s in summaries.items():lines.append(f"| {scene} | {s['candidates']} | {s['valid_profiles']} | {s['profile_increased_union_pixels']} | {s['total_structural_ink_area']/s['total_union_ink_area']:.4f} |")
    lines+=['', '主代理看完两场景四视角六层全图、原生 ROI、全部 66 帧图条及证据/控制图。Lego 凸点和 Chair 合法花纹在联合图中保留；结构图遗漏大量凸点、花纹、边饰和腿部。RGB 联合与经典张量外观接近，仍有明暗双边和花纹拥挤；alpha 辅助补充浅色外轮廓。剖面通道在联合图中的实际增量很小，不能把剖面元数据或稀疏“更干净”图当成已获线稿优势。独立人工视觉评审 pending。',
      '', '## 独立界面与时间结果', '',
      '7 个解析界面包含常量、等亮度颜色阶跃、低对比、合法条纹、角点、交汇与已知宽度。构造真值先于检测存在；P/R 是固定 2px 容差诊断，不是 gate。等亮度颜色阶跃在亮度对照中行为 RED，新场能检出并拟合；常量无显著墨迹；低对比无结构拟合而保留弱 detail；条纹不合格的单调剖面不会使联合图丢失合法图案。8 项基础 unittest GREEN。初始缺接口、错误的 5px 平均响应断言、真实整图 OpenCV SHRT_MAX 采样失败与修复日志保留；采样改为分块，没有候选数量截断。',
      '', '| 场景全arc | motion MAE OFF | motion MAE ON | churn OFF | churn ON | 警报帧数 |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for scene,d in temporal.items():
        m=d['aggregate'];lines.append(f"| {scene} | {m['motion_corrected_spatial_MAE']:.6f} | {m['motion_corrected_temporal_MAE']:.6f} | {m['spatial_churn']:.6f} | {m['temporal_churn']:.6f} | {len(d['failure_frames'])} |")
    lines+=['', '误差与 churn 在 forward/backward 有效、当前或 warped ink>.075 的屏幕域计算；二值 churn 门槛为 .2。Farneback 只 warp 软响应，出生/消失与无当前证据处复位，当前证据限制增量；真实两场景 unsupported ghost=0。降低这些数值不能证明感知质量或真实重投影稳定。Chair 的警报仍多，完整稳定视频为 NO-GO；所有帧都展示，没有删掉坏帧。',
      '', f"冻结警报是 edge flow valid fraction<.5、unsupported ghost，或 spatial motion MAE>.2。Lego 警报帧 {temporal['lego']['failure_frames']}；Chair 警报帧 {temporal['chair']['failure_frames']}（0-based；第0帧复位）。没有警报也不表示没有视觉失效。旧 arc 是有限轨迹，累计旋转约 Lego 10.51°、Chair 7.85°，并非360°覆盖；重复图案上的 flow confidence 不认证静态3D对应。",
      '', f"独立移动矩形/遮挡/消失控制展示全部7帧。已知未遮挡两条边的 OFF/ON 定位 MAE 均 {lag['spatial_MAE']:.3f}px，ON-OFF 最大中心偏移 {lag['max_temporal_minus_spatial_center']:.3f}px；3px真值带外 ghost质量最大 {lag['ghost_mass_max']:.3f}。全消失帧复位。它支持守卫行为，不显示时间方法提高定位能力。[移动与遮挡全图](synthetic/moving_disocclusion_all_frames.png)、[已知边位置控制](synthetic/moving_edge_lag_band.png)。",
      '', '## 可选RGB宽度控制及失败修正', '',
      '原候选存在25个新增越界色值（6张固定图）和已知6px界面最小反向斜率 -0.00027275，判 NO-GO。第一次裁剪守卫仍不足以保证单调；初始独立审核失败保存在 `tests/INDEPENDENT_AUDIT_INITIAL.json`。随后只更改可选控制为有限带端点固定的新单调过渡，逆组合保留 RGB 残差、切线置信混合和最大每通道 .08 增量；非边缘、带外、已有裁剪和 alpha 外部处回退。DEV/解析验证后另行冻结，已经看过固定图，明确是 post hoc 工程修正。主空间法、参数、原候选和视频未改。',
      '', '| 解析界面 | 原始离散10–90宽 | 收窄 x.65 | 放宽 x1.50 | 最小新增剖面斜率 |', '| --- | ---: | ---: | ---: | ---: |']
    for r in anchored['records']:lines.append(f"| {r['name']} | {r['original_width']:.4f} | {r['arms']['sharpen']['width']:.4f} | {r['arms']['soften']['width']:.4f} | {min(r['arms']['sharpen']['min_fraction_slope'],r['arms']['soften']['min_fraction_slope']):.6f} |")
    lines+=['', '该有限带约束使实际放宽量小于名义倍率；不能把倍率标签当作真实宽度。最终8张固定图、16个控制臂带外/非边缘差=0、alpha逐值不变、新增裁剪=0、最大delta≤.08；合成无反向梯度/平台越界。真实图仅有少量可信局部变动，主观 halo/照片级修复没有独立目标证明，能力仍标 PARTIAL 局部风格化。',
      '', '[Lego 最终四视角控制](media/lego/guarded_RGB_v2/fixed/fourview_RGB_control.jpg)、[Chair 最终四视角控制](media/chair/guarded_RGB_v2/fixed/fourview_RGB_control.jpg)、[已知宽度](synthetic/anchored_control/width.png)。没有把墨迹黑化叫做 RGB 修复。',
      '', '## 阶段判断与复现', '', '| 阶段 | 判断 | 限定 |', '| --- | --- | --- |']
    for name,d in decisions.items():lines.append(f"| {name} | {d['status']} | {d.get('reason',d.get('scope',''))} |")
    lines+=['', '生产 runner 的实际恢复验证通过：13 个已封印生产单元全部校验后跳过，新增渲染=0（`tests/RESUME.json`）。',
      '', '方向场引导线绘与 flow-based DoG 已由 [CLD 原论文](https://cg.postech.ac.kr/papers/kang_npar07_hi.pdf) 提出；光流引导时间 NPR 可参见 [2007 时间水彩工作](https://research.adobe.com/publication/video-watercolorization-using-bbidirectional-texture-advection/)。本轮为 tensor+双侧剖面+软墨迹+保守 temporal 的独立原型组合，没有宣称新颖性，也没有逐项复现其 ETF/FDoG 或双向纹理输运。',
      '', '[复现](REPRODUCE.md)、[参数与相机冻结](PRODUCTION_FREEZE.json)、[机器结果](FINAL.json)、[来源分层](SOURCE_MAP.json)、[媒体哈希](MANIFEST.json)、[独立审计](tests/INDEPENDENT_AUDIT.json)。固定 GPU0/CPU2、4GiB root/1.5GiB Git reserve/8GiB cap 未放松，无安装、无旧模型编辑、无其他进程终止。后续仍需解决真实场景的线条取舍与完整性、亚像素连续性、Chair 高换变，以及独立人工判断；未把工程 PASS 换成科学 GO。', '']
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status='CURATED',media_files=len(media),raw_files=len(raw),audit_checks=audit['checks'],scientific_status='PARTIAL')))
if __name__=='__main__':run()
