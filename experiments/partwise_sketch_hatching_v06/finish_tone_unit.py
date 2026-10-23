"""Post-result handoff. Does not mutate frozen science or prior units."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now,output_guard
from pathlib import Path
import datetime
import json
import shutil

assert UNIT.name=='unit_006'
p=json.loads((UNIT/'PROTOCOL.json').read_text());s=json.loads((UNIT/'SUMMARY.json').read_text())
validation=json.loads((UNIT/'VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text())
assert len(validation['views'])==13 and all(replay['exact'].values()) and replay['actual_zero_link_blank_ink']
assert len(media['all_frames_decoded_exact'])==9 and all(media['all_frames_decoded_exact'])
assert all(r['changes'][k][zone]['raw_L1_sum']==0 for r in s['records'] for k in r['changes'] for zone in ('far_other','far_background'))
assert all(a['far_ink_L1']==0 for r in s['records'] for a in r['arms'].values())
dev=[r for r in s['records'] if r['kind']=='dev'];weak=dev[1];build=s['build'];stats=s['weights']
verdict='FIXED_STROKE_TONE_AND_ORIGINAL_ID_LINK_VALIDATED; WHOLE_OBJECT_NPR_READABILITY_GAIN_NOT_ESTABLISHED; NO_DEFAULT_PROMOTION'
next_step='固定unit004自然强度纸底、旧20122原核责任S和未补间隙的常量交叉排线，单独测试加入目标部件的视角轮廓层。现有render.py已计算全代理可见外轮廓和深度不连续线，但关联混合入口只取hatch，未使用contour。沿用已有轮廓定义、2倍采样与深度跳变0.035；在高分辨率可见region4内裁切轮廓，与旧墨层取max后降采样并乘原S。只比较旧排线与排线加轮廓，四BUILD按实际目标可见墨RGB L1配平并保留自然强度；检查四DEV和弱角度短弧是否更易辨认铲斗外形、遮挡与孔洞，是否产生重边、锯齿或新增远区损伤。不把作者region色块边界或三角网格边当成可信结构线；视角轮廓不是固定三维stroke或Gaussian ID。若只是更黑或描出代理噪声，不升级默认，不扫描阈值。下一单元仍需新的A阶段审查与协议冻结。'
why='本轮权重已在21%–26%的目标像素上产生配平后明显变化，但完整物体相对常量和打乱权重未出现明确更好的面向关系；继续调明暗曲线缺少依据。缺失的轮廓层直接涉及原纲要M7的形体辨认，是不同于颜色分配、补间隙和遮挡微调的独立机制；可以利用已有重建深度和已冻结原ID连接进行便宜对照。它仍可能因代理孔洞和粗表面产生杂线，需真实整物体证伪。'
js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,
    preserve='v05 sparse failure, v06 unit001-006 negatives and all historical interruptions remain unchanged; next science not executed here.'))
ratios=[r['arms']['tone_matched']['target_ink_L1']/r['arms']['constant_matched']['target_ink_L1'] for r in dev]
changed=[r['changes']['tone_matched']['target_full']['useful_fraction_0_05'] for r in dev]
lines=['# Unit006：逐笔触表面明暗生效，整物体可读性收益未建立','',
    '**冻结的三条件对照已完成。表面相关权重改变了实际原ID关联墨层，但相对常量及打乱权重，整物体NPR形体优势未建立；不升级默认，scientific_seal=false。**','',
    '仅改变固定stroke的墨强度。351条旧stroke、1904段及全部face/bary/world/layer/visibility数组保持；未使用unit005补间隙变体。世界光照固定normalize([-0.4,-0.6,0.7])，逐面abs(n·l)按段世界弧长平均，再取tau=1-0.8*r。相反法线不会相互抵消；不是归一化平均法线，也不是物理光照。退化面回退tau1，零长度stroke回退tau1。实际退化面/零长度stroke均为0。层内打乱使用固定种子1729，保存每条stroke的置换来源。','',
    f'实际tau范围{stats["tau_min"]:.6f}–{stats["tau_max"]:.6f}，逐stroke均值{stats["tau_mean"]:.6f}、长度加权均值{stats["tau_length_mean"]:.6f}。权重在原2倍采样可见胶囊片元赋值，重叠取max后降采样，再乘原ID责任S；没有在合并图上事后涂明暗。','',
    f'协议SHA256 `{sha(UNIT/"PROTOCOL.json")}`。{validation["input_hashes_checked"]}份输入、CAMERAS/INPUT/SOURCE锁和实验、审计、媒体源码均在BUILD前冻结。实验没有中途参数或源码修订。','',
    '纸底继续使用unit004的39474核外观许可，墨责任S继续使用旧20122核权重；原310475行身份、源PLY、几何、协方差、opacity、完整SH和M1/195600个UNKNOWN保持。STROKE_TONES中的stroke_id属于代理笔触；SOURCE_LINK单独保存完整原PLY行映射与原/纸底强度。','',
    '## 实际完整物体观察','',
    '已检查四个自然强度/配平完整物体视角、弱角度独立墨层以及全部九相机短弧。自然强度表面相关结果更淡，部分线段深浅改变；配平后也可见局部墨色分布变化。但均匀交叉网格、计划短线、前侧明显黄色残留和后侧黄灰斑驳仍在，没有稳定形成比常量或打乱权重更清楚的铲斗面向关系。弱角度表面相关结果稍重，并不能证明更好的明暗。该结论来自有限视觉检查，不是独立偏好实验。','',
    '## 墨预算与DEV结果','',
    f'四BUILD自然目标墨RGB L1：常量{build["natural_target_ink_L1"]["constant"]:.4f}、表面相关{build["natural_target_ink_L1"]["tone"]:.4f}、打乱{build["natural_target_ink_L1"]["shuffled"]:.4f}。公共预算{build["budget"]:.4f}，只有常量自然效果的{100*build["budget_fraction_of_constant_natural"]:.2f}%；配平不能掩盖这种降墨量。三个全局系数依次{build["scales"]["constant"]:.10f}、{build["scales"]["tone"]:.10f}、{build["scales"]["shuffled"]:.10f}，实际合成读回一致，无DEV或逐帧配平。','',
    '下表三联数字为常量/表面相关/打乱，全部为BUILD配平后的真实输出。可见墨采用alpha>0.05。','',
    '| 视角 | 目标/内部像素 | 目标墨L1 | 可见墨像素 | 内部墨像素 | 远其他/背景L1（各臂相同） |',
    '|---|---:|---:|---:|---:|---:|']
for r in dev:
    arms=[r['arms'][k+'_matched'] for k in ('constant','tone','shuffled')]
    effects='/'.join(f'{a["target_ink_L1"]:.2f}' for a in arms)
    pixels='/'.join(str(a['visible_ink_pixels']) for a in arms)
    interior='/'.join(str(a['interior_ink_pixels']) for a in arms)
    lines.append(f'| {r["view"]} | {r["target_pixels"]}/{r["interior_pixels"]} | {effects} | {pixels} | {interior} | {arms[0]["far_other_L1"]:.4f}/{arms[0]["far_background_L1"]:.4f} |')
lines += ['',f'DEV表面相关/常量实际墨量比为{min(ratios):.4f}–{max(ratios):.4f}：61°两视角略少，241°两视角较多。弱角度比值{ratios[1]:.4f}，表面相关还比打乱多{100*(weak["arms"]["tone_matched"]["target_ink_L1"]/weak["arms"]["shuffled_matched"]["target_ink_L1"]-1):.2f}%，故不能把后侧更重归于形体优势。BUILD总量匹配不保证DEV逐视角等量，本轮没有根据结果重新配平。','',
    f'相对同预算常量臂，表面相关臂让完整目标中{100*min(changed):.2f}%–{100*max(changed):.2f}%的像素产生clipped RGB L1≥0.05变化。变化不只是几个像素，但也不代表可读性改善。墨覆盖在四DEV均略低于常量；图像连通块变化没有一致方向，不能据此宣称连续性成功。全目标/腐蚀内部/边界/远其他/背景的mean、sum、覆盖以及纸底、独立墨层、三臂差异均见EVALUATION.json。','',
    f'原S完全固定；弱角度全目标平均S={weak["support"]["target"]["mean"]:.6f}，内部平均S={weak["support"]["interior"]["mean"]:.6f}，全目标S>0.05比例{100*weak["support"]["target"]["fraction_above_0_05"]:.2f}%。这些是原核责任覆盖描述，不是物理部件概率。','',
    '全部13份记录、全部自然/配平条件的墨层远区L1均为0，明暗/打乱相对常量的新增远其他及背景损伤均为0。纸底已有损伤未变：四DEV远区总L1约18.8854、3.2938、20.3460、4.4345。远区比例随目标墨量和颜色抵消变化，不能当作局部性改善。','',
    '九帧为实际231°–251°、仰角24°、距离5.3的相机短弧，所有stroke权重固定。表面相关结果在短弧中有较重墨色，但均未形成明确整物体优势。4DEV+9arc仅12个不同相机设置，全部已曝光；没有独立共同可见对应，不声称泛化、闪烁改善或时序认证。','',
    '## 验证与失败保留','',
    '三项针对性TDD先RED缺模块rc1、后GREEN rc0：不同长度/法线翻转/退化回退/层内打乱；旧渲染逐值复现、统一衰减、零S与同region真实前景遮挡；真实Lego全部身份不变与小尺寸渲染。原1904段和常量臂在四BUILD、四DEV、九arc均逐值恢复旧缓存。','',
    f'独立读回{validation["input_hashes_checked"]}份输入哈希与13份结果，逐stroke重新累积标量法线响应，验证置换多重集及方向层，核对BUILD实际预算与全部区域指标。使用实际原Gaussian ID alpha*T trace重建源RGB、纸底与S，M1/UNKNOWN保持。弱角度冷重放实际渲染完整GS三次：原源+S、固定纸底、零S；六个自然/配平混合结果逐数组一致。零S控制源RGB不变、墨为空。九帧FFV1全部解码，与保存PNG逐像素一致。','',
    '本轮初始RED以外所有科学阶段均有真实rc0；没有失败被覆盖。v05稀疏8.044%远区失败与4.49%区域可见变化、unit001门控负结果、unit002单层负结果、unit003微小可见性收益、unit004同预算纸底负结果、unit005补间隙未建立可读性优势及其缓存适配失败、历史配额/中断记录全部保持。','',
    '这是CPU原GS纸底与原ID责任连接的代理墨层，不是原生Gaussian排线、独立语义/物理归属或H1/H2/H3证明。结果只否定本轮固定逐stroke明暗配置已建立实用收益，不否定所有明暗或NPR路线。','',
    '## 下一步','', 'NEXT=continue：'+next_step,'',why,'',
    '本轮仅完成unit006，未执行下一科学单元。']
started=datetime.datetime.fromisoformat('2026-10-23T19:32:11.670695+09:00')
elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
lines += ['',f'报告生成时执行阶段约{elapsed:.2f}分钟。']
output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
readme=f'''# Unit006：逐stroke表面明暗对照

结论：权重正确作用于原ID连接的墨层；整物体NPR可读性优势未建立，不升级默认。

- ALL_DEV_VIEWS.png / ALL_DEV_MATCHED.png / ALL_DEV_INK.png：四视角自然、配平、独立墨层。
- ALL_ARC_FRAMES.png / media/stroke_tone_arc_ffv1.mkv：全部九实际相机的短弧。
- asset/PATHS.npz：原351条stroke/1904段逐值副本，未补间隙。
- asset/STROKE_TONES.npz：stroke_id、layer_id、长度、面响应、常量/表面相关/打乱tau及打乱来源stroke_id；segment_stroke_index对应PATHS段序。
- asset/SOURCE_LINK.npz：完整310475原PLY行映射、纸底许可、旧墨责任权重及未变M1状态。stroke_id与source_index是不同身份空间。
- dev、arc的FRAME.npz：原源、纸底、三臂独立墨/alpha及六个自然/配平实际混合结果。EVALUATION.json保存完整区域指标。
- PROTOCOL.json / CAMERAS.json / INPUT_LOCK.json / SOURCE_LOCK.json：冻结机制、相机与来源；SUMMARY/VALIDATION及logs记录实际结果和退出码。

真实完整GS冷重放，输出目录须为当前unit内不存在的新目录：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' \\
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B \\
{UNIT}/source_snapshot/audit_tone_unit.py replay \\
--out {UNIT}/cold_replay_manual_002
```

实际渲染完整GS三次并重渲染三个墨条件，与保存数组精确比较；不是截图合成。运行时固定两核、单数值线程、禁GPU，C++编译目录位于新输出目录。

外部依赖为输入锁列出的原PLY、v05代理/绑定与unit003–005不可变缓存、本地只读Python环境及C++编译器。本交付不是可独立移动的数据包。缓存复用、真实冷重放和原Gaussian/代理笔触身份均明确分开。scientific_seal=false；旧科学失败与本轮预期RED保留。
'''
output_guard(UNIT/'README_ZH.md').write_text(readme)
receipts=[]
for f in sorted((UNIT/'logs').glob('*.receipt.json')):
    r=json.loads(f.read_text());receipts.append(dict(name=f.name,argv=r['argv'],returncode=r['returncode'],elapsed_seconds=r['elapsed_seconds']))
    assert r['returncode']==(1 if f.name=='tdd_red_001.receipt.json' else 0),f.name
artifacts=['REPORT_ZH.md','README_ZH.md','PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json',
    'asset/STROKE_TONES.npz','asset/PATHS.npz','asset/SOURCE_LINK.npz','SUMMARY.json','VALIDATION.json','BUILD_MATCH.json',
    'ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json',
    'cold_replay_001/REPLAY_CHECK.json','media/stroke_tone_arc_ffv1.mkv']
progress=dict(previous_gap='Constant linked ink did not encode any surface-orientation tone; prior gap completion did not establish whole-object readability.',
    actual_advance='Added immutable per-stroke camera-independent tone and within-layer shuffled controls; all old paths and complete original source identity retained. Actual S controls every condition, with trace reconstruction and real full-GS zero-link replay.',
    original_rows=310475,paper_permission_rows=39474,ink_S_rows=20122,UNKNOWN_unchanged=195600,
    visible_outcome='Local tone distribution visibly changes; no added far damage; no established whole-object advantage over constant and shuffled weights.',
    representation='Original-GS paper + original-ID-linked proxy ink; not native Gaussian ink or physical/semantic ownership.')
js(UNIT/'STATUS.json',dict(execution_state='completed',stage='fixed_stroke_tone_comparison_handoff',scientific_verdict=verdict,
    gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,completed_utc=now(),elapsed_minutes=elapsed,
    artifacts={name:str(UNIT/name) for name in artifacts},tests_and_actual_commands=receipts,blockers=[],
    limitations=['Whole-object readability gain not established','BUILD budget only57.61% of old natural ink; DEV actual effects differ',
        'Residual photo texture, short strokes and cross-grid remain','Exposed proxy-intent cameras and CPU replica only'],
    preserved_failures=[dict(stage='tdd_red_001',returncode=1,reason='expected missing module; retained')],next_action='continue'))
handoff=UNIT/'handoff_source';handoff.mkdir(exist_ok=False);shutil.copy2(Path(__file__),handoff/Path(__file__).name)
js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in handoff.iterdir()},utc=now()))
science=[]
for name in ('source_snapshot','asset','build_match','dev','arc','cold_replay_001','media'):
    science += [f for f in (UNIT/name).rglob('*') if f.is_file()]
science += [UNIT/name for name in ('DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json',
    'ASSET_LOCK.json','BUILD_MATCH.json','BUILD_LOCK.json','SUMMARY.json','VALIDATION.json','MEDIA_VALIDATION.json',
    'ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png')]
js(UNIT/'ARTIFACT_MANIFEST.json',dict(utc=now(),scientific_seal=False,
    scope='Inventory of finite verified payload, not scientific certification; mutable status/logs excluded.',
    files={str(f.relative_to(UNIT)):sha(f) for f in science}))
js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),required_artifacts_exist=all((UNIT/name).is_file() for name in artifacts),
    dev_records=4,arc_records=9,independent_camera_settings=12,cold_replay_exact=True,all_video_frames_decoded_exact=True,
    old_negative_results_preserved=True,no_midexperiment_revision=True,verdict=verdict))
print('HANDOFF',verdict,'elapsed_minutes',elapsed,flush=True)
