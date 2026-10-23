"""Post-result unit007 handoff, preserving all frozen science and prior negatives."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,sha,js,now,output_guard
from pathlib import Path
import datetime
import json
import shutil

assert UNIT.name=='unit_007'
p=json.loads((UNIT/'PROTOCOL.json').read_text());s=json.loads((UNIT/'SUMMARY.json').read_text())
validation=json.loads((UNIT/'VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text());far=json.loads((UNIT/'FAR_READBACK.json').read_text())
assert len(validation['views'])==13 and all(replay['exact'].values()) and replay['actual_zero_link_blank_ink']
assert len(media['all_frames_decoded_exact'])==9 and all(media['all_frames_decoded_exact'])
assert far['all_far_pixels_contain_target_subpixel']
dev=[r for r in s['records'] if r['kind']=='dev'];weak=dev[1];build=s['build']
verdict='FOREGROUND_OWNED_CONTOUR_AND_ORIGINAL_ID_LINK_VALIDATED; LOCAL_OUTLINE_STRENGTHENED; WHOLE_OBJECT_NPR_ADVANTAGE_NOT_ESTABLISHED; NO_DEFAULT_PROMOTION'
next_step='下一A阶段优先审查一个显式的新目标实验：用BUILD视角人工补全铲斗可见表面的作者face集合，建立独立命名的完整铲斗目标变体，再沿既有冻结规则生成其原Gaussian行证据、纸底许可和同风格代理排线。先以BUILD原GS/代理/标签投影确认遗漏来自未选择face还是代理缺面；只补有实际重建面的可核验铲斗面，记录新增face、选择视角、人工操作及耗时，不补几何、不按DEV输出挑核。主变量是作者部件范围；风格、原源几何、证据阈值和渲染规则不调。旧region4、M1/UNKNOWN、路径、选择及全部结果原封保存，新证据和UNKNOWN另存。新目标必须在评价前冻结，并分别报告旧目标、新增区域、完整新目标及远区的实际源编辑/墨覆盖与整物体效果，不把扩区写成旧门槛通过或同目标算法优势。若BUILD表明主要是代理缺面，停止该补选路线并明确表示层限制，不再增加轮廓或明暗参数。仍需新的A阶段决策与父级授权，当前没有执行此实验。'
why='轮廓层增加了可见边线，但不能移除明显的未风格化黄色面或内部照片残留。读取原asset.json发现region4只是三个手工矩形选出的2030个face，原记录明确不保证完整部件；完整物体intent图也存在铲斗附近未选灰面。因此应先把用户要编辑的完整部件定义作为显式新目标验证，区别于继续调整旧局部片区的笔触或责任。不是把所有黄灰残留都归因于漏选：BUILD投影仍需区分未选、缺面及原核外观容量。'
js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,
    preserve='v05 sparse failure and all v06 units001-007 negative results, original source rows and historical interruptions remain unchanged.'))
ratios=[r['arms']['outlined_matched']['target_ink_L1']/r['arms']['hatch_raw']['target_ink_L1'] for r in dev]
coverage=[r['arms']['outlined_matched']['visible_ink_pixels']/r['arms']['hatch_raw']['visible_ink_pixels']-1 for r in dev]
retention=[r['contour']['target_mass_after_S']/r['contour']['target_mass_before_S'] for r in dev]
internal=[1-r['arms']['outlined_matched']['interior_ink_L1']/r['arms']['hatch_raw']['interior_ink_L1'] for r in dev]
raw_changed=[r['changes']['raw']['target_full']['useful_fraction_0_05'] for r in dev]
matched_changed=[r['changes']['matched']['target_full']['useful_fraction_0_05'] for r in dev]
far_raw=max(r['changes']['raw']['far_other']['raw_L1_sum']+r['changes']['raw']['far_background']['raw_L1_sum'] for r in s['records'])
far_matched=max(r['changes']['matched']['far_other']['raw_L1_sum']+r['changes']['matched']['far_background']['raw_L1_sum'] for r in s['records'])
lines=['# Unit007：前景归属轮廓生效，整物体收益仍有限','',
    '**冻结两臂比较完成。局部外缘更明确，但相近BUILD墨预算下没有建立稳定的整物体NPR优势；保留结果，不升级默认，scientific_seal=false。**','',
    '唯一主机制为旧常量排线上加入当前视角轮廓。沿完整代理2倍采样首交深度生成：外轮廓沿用hit的两子像素内侧带；有限深度邻接差大于0.035时，只归给较近像素，并检查其region4身份。邻接不跨图像两端；区域标签变化本身不生成线。强度固定0.85，与旧排线在2倍采样取max后降采样，再乘旧原ID责任S。深度差只是代理启发式，不是已确认结构线。','',
    '旧351条stroke/1904段、face/bary/world/layer/visibility数组、两方向层、间隙、线宽和0.004排线遮挡容差全部保持。未使用unit005补间隙或unit006明暗。纸底使用unit004自然强度的39474核外观许可，墨责任仍为20122核原权重；完整310475原行、原PLY、几何、协方差、opacity、完整SH、M1和195600个UNKNOWN均未改变。视角轮廓与代理stroke均不是Gaussian ID。','',
    f'协议SHA256 `{sha(UNIT/"PROTOCOL.json")}`。{validation["input_hashes_checked"]}份输入、相机、协议和测试/运行/审计/媒体源码先冻结。按照协议预声明的TDD流程，保留source_snapshot中的缺模块RED，再仅新增linked_contours.py到source_snapshot_002，EXECUTION_SOURCE_LOCK记录新增一文件、已有文件零修改；随后GREEN及全部BUILD/DEV。协议未改，BUILD后无实现或参数修订。','',
    '## 实际完整物体观察','',
    '已检查四个完整物体自然/配平面板、独立轮廓层以及全部九相机短弧。弱241°/24°的上缘、侧缘和铲齿附近多出可见线，外形略明确；其他角度部分外缘也加强。原ID责任使轮廓明显变淡但并未消失。新增内部深度线也带入部分粗代理形状，交叉网格、短线、前侧黄色大面和后侧黄灰照片残留仍支配观感；配平时内部旧线变淡。未观察到足以支持多数视角整体更清楚的稳定优势。该判断为有限实际视觉检查，未进行独立偏好实验。','',
    '## 真实墨预算、覆盖及远区变化','',
    f'四BUILD自然目标墨RGB L1：旧排线{build["natural_target_ink_L1"]["hatch"]:.4f}，加入轮廓{build["natural_target_ink_L1"]["outlined"]:.4f}，增加{100*(build["natural_target_ink_L1"]["outlined"]/build["budget"]-1):.2f}%。公共预算就是旧自然墨量{build["budget"]:.4f}；旧臂系数1，新臂{build["scales"]["outlined"]:.10f}，实际合成读回配平。不沿用unit006的57.61%低预算，不做DEV或逐帧再配平。','',
    '下表为旧自然排线/加轮廓BUILD配平。可见墨阈值alpha>0.05，远区为实际完整混合图相对原GS的raw RGB L1。','',
    '| 视角 | 目标/内部像素 | 目标墨L1旧/新 | 可见墨像素旧/新 | 内部墨L1旧/新 | 新远其他/背景L1 |',
    '|---|---:|---:|---:|---:|---:|']
for r in dev:
    old=r['arms']['hatch_raw'];new=r['arms']['outlined_matched']
    lines.append(f'| {r["view"]} | {r["target_pixels"]}/{r["interior_pixels"]} | {old["target_ink_L1"]:.2f}/{new["target_ink_L1"]:.2f} | {old["visible_ink_pixels"]}/{new["visible_ink_pixels"]} | {old["interior_ink_L1"]:.2f}/{new["interior_ink_L1"]:.2f} | {new["far_other_L1"]:.6f}/{new["far_background_L1"]:.6f} |')
lines += ['',f'四DEV可见墨覆盖增加{100*min(coverage):.2f}%–{100*max(coverage):.2f}%，但内部墨量均减少{100*min(internal):.2f}%–{100*max(internal):.2f}%。DEV实际目标墨量新/旧为{min(ratios):.4f}–{max(ratios):.4f}；弱角度仍多{100*(ratios[1]-1):.2f}%，所以边缘更黑不能全部归为结构优势。','',
    f'未衰减新增轮廓让完整目标{100*min(raw_changed):.2f}%–{100*max(raw_changed):.2f}%像素发生clipped RGB L1≥0.05变化；配平比较为{100*min(matched_changed):.2f}%–{100*max(matched_changed):.2f}%，后者同时包含旧排线衰减，不能全算新增轮廓覆盖。','',
    f'独立轮廓目标alpha质量乘S后保留{100*min(retention):.2f}%–{100*max(retention):.2f}%；弱角度{weak["contour"]["target_mass_before_S"]:.4f}→{weak["contour"]["target_mass_after_S"]:.4f}，保留{100*retention[1]:.2f}%。原S全目标平均仍为{weak["support"]["target"]["mean"]:.6f}、S>0.05覆盖{100*weak["support"]["target"]["fraction_above_0_05"]:.2f}%；区域平均覆盖不能代表边界轮廓质量。','',
    f'新增远区变化不是严格零：13记录的最大自然raw L1为{far_raw:.10f}，配平为{far_matched:.10f}；背景新增为0。全部新增远区像素的clipped L1均未超过1/255。61°/24°和241°/24°各有一个变化像素，后者在短弧中心重复一次。FAR_READBACK逐像素确认：2×块含region4轮廓子像素，但原低分辨率标签抽样点属于region3，固定2px近区也没有涵盖该细片。保留原掩码与测得损伤，不扩容差或删失败像素。','',
    '纸底已有远区损伤仍在，四DEV总L1约18.8854、3.2938、20.3460、4.4345。弱角度新墨还略抵消部分原纸底颜色误差，因此最终源差变小不能解释成没有新增墨。所有target/interior/boundary/far other/background的mean、sum、覆盖见逐视角EVALUATION.json。','',
    '九帧为231°–251°、仰角24°、距离5.3的实际相机短弧；固定3D排线，轮廓随相机生成。轮廓在弧中可见，但仍未建立整体风格可读性优势。4DEV+9arc只有12个不同相机设置，全部已曝光，不能声称泛化、闪烁改善或时序认证。','',
    '## 验证与失败保留','',
    '四项针对性TDD先缺模块RED rc1、后GREEN rc0：标签不造边、前景反转归属、无循环邻接、背景内侧轮廓、真实遮挡、max在降采样前、零S、真实Lego身份与旧输出。四BUILD、四DEV和九arc的旧排线逐值恢复unit006自然常量缓存。','',
    f'独立审计{validation["input_hashes_checked"]}份输入及13份结果。用Manhattan距离复算外轮廓内侧带，逐目标子像素检查四邻域前景归属；用实际原ID alpha×T trace重建源RGB、固定纸底和S，核对完整原行、M1、路径、实际预算及区域指标。弱角度冷重放实际完整GS三次：原源+S、固定纸底、零S；四个自然/配平混合输出逐数组一致。零S源RGB不变、墨为空且合成等于固定纸底。九帧FFV1全部解码，与保存PNG逐像素相同。','',
    '本轮预期RED之外所有执行阶段rc0，无科学阶段中断。额外FAR_READBACK只是已保存结果的后验诊断，不修改协议、图像或指标。v05稀疏capsule8.044%远区失败和4.49%区域变化，以及unit001门控、unit002单层、unit003微小可见性、unit004同预算纸底、unit005补间隙、unit006明暗的负结果和历史配额/中断全部保留。','',
    '相对冻结v05/unit005，本轮已是完整作者region4的可见原GS纸底加原ID关联代理墨层，而v05只控制稀疏路径；操作范围不同，不能把本轮大面积变化倒算为旧门槛成功。不是原生Gaussian排线、独立语义/物理归属或H1/H2/H3证明。','',
    '## 下一步','', 'NEXT=continue：'+next_step,'',why,'',
    '本轮只完成unit007，未执行目标补全或下一科学单元。']
started=datetime.datetime.fromisoformat('2026-10-23T19:51:05.223534+09:00')
elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
lines += ['',f'报告生成时执行阶段约{elapsed:.2f}分钟。']
output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
readme=f'''# Unit007：前景归属轮廓对照

局部外缘加强；整物体NPR优势未建立，不升级默认。完整结论见[报告](REPORT_ZH.md)。

- [全部整物体视角](ALL_DEV_VIEWS.png)、[独立墨层](ALL_DEV_INK.png)、[九相机短弧](ALL_ARC_FRAMES.png)。
- media/owned_contour_arc_ffv1.mkv：实际相机运动，九帧全部解码验证。
- asset/PATHS.npz：未改变的351条stroke/1904段。
- asset/SOURCE_LINK.npz：310475个原PLY行、纸底许可和原墨责任权重，M1/UNKNOWN不变。
- dev、arc的FRAME.npz：原GS、纸底、独立墨/轮廓/责任S及自然/配平输出；RASTER.npz：2×首交depth/face/region、前景轮廓和旧排线，支持归属读回。
- EVALUATION.json：完整/内部/边界/远其他/背景指标；FAR_READBACK.json保留两个相机的微小新增远区像素。
- PROTOCOL/INPUT_LOCK/CAMERAS/SOURCE_LOCK在RED前冻结；source_snapshot_002及EXECUTION_SOURCE_LOCK是协议预声明的仅新增实现、GREEN前冻结版本；原RED和初始源码保留。

真实完整GS冷重放（输出目录必须为unit007内不存在的新目录）：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' \\
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B \\
{UNIT}/source_snapshot_002/audit_contour_unit.py replay \\
--out {UNIT}/cold_replay_manual_002
```

实际渲染完整GS三次并重新生成轮廓/排线，核对自然/配平数组。CPU两核亲和、数值线程1、禁GPU，C++编译只写新输出目录。

依赖输入锁中的原PLY、v05冻结代理/绑定、既有v06不可变缓存、本地只读Python和C++编译器；不是可独立移动的数据包。输出是原GS纸底与原ID责任关联的代理墨层，不是原生Gaussian排线或独立语义/物理证明。所有旧负结果保留，scientific_seal=false。
'''
output_guard(UNIT/'README_ZH.md').write_text(readme)
receipts=[]
for f in sorted((UNIT/'logs').glob('*.receipt.json')):
    r=json.loads(f.read_text());receipts.append(dict(name=f.name,argv=r['argv'],returncode=r['returncode'],elapsed_seconds=r['elapsed_seconds']))
    assert r['returncode']==(1 if f.name=='tdd_red_001.receipt.json' else 0),f.name
artifacts=['REPORT_ZH.md','README_ZH.md','PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','EXECUTION_SOURCE_LOCK.json',
    'asset/PATHS.npz','asset/SOURCE_LINK.npz','SUMMARY.json','VALIDATION.json','BUILD_MATCH.json','FAR_READBACK.json',
    'ALL_DEV_VIEWS.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json','media/owned_contour_arc_ffv1.mkv']
progress=dict(previous_gap='The linked hybrid omitted view contours, while tone/gap changes did not establish readability.',
    actual_advance='Added foreground-owned nonwrapping view contours, high-resolution owner evidence, fixed original-row S and complete-GS zero-link replay; old hatch paths and output exact.',
    original_rows=310475,paper_permission_rows=39474,ink_S_rows=20122,UNKNOWN_unchanged=195600,
    visible_outcome='Local outline strengthened; matched coverage increased15.96%-28.67%, interior ink reduced6.66%-12.64%; whole-object advantage not established.',
    added_far_RGB_L1_max_raw=far_raw,added_far_RGB_L1_max_matched=far_matched,
    representation='Original-GS paper + original-ID-linked proxy ink, not native Gaussian ink or semantic/physical ownership.')
js(UNIT/'STATUS.json',dict(execution_state='completed',stage='foreground_owned_contour_comparison_handoff',scientific_verdict=verdict,
    gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,completed_utc=now(),elapsed_minutes=elapsed,
    artifacts={name:str(UNIT/name) for name in artifacts},tests_and_actual_commands=receipts,blockers=[],
    limitations=['Whole-object readability advantage not established','BUILD matching does not equalize individual DEV effects',
        'Residual photo texture and partial authored target persist','Heuristic proxy contours, exposed cameras and CPU replica only'],
    preserved_failures=[dict(stage='tdd_red_001',returncode=1,reason='expected missing implementation; initial source snapshot retained')],
    next_action='continue',parent_monitor_verification='pending'))
handoff=UNIT/'handoff_source';handoff.mkdir(exist_ok=False)
for name in ('finish_contour_unit.py','readback_contour_far.py'):shutil.copy2(Path(__file__).parent/name,handoff/name)
js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in handoff.iterdir()},utc=now()))
science=[]
for name in ('source_snapshot','source_snapshot_002','asset','build_match','dev','arc','cold_replay_001','media','handoff_source'):
    science += [f for f in (UNIT/name).rglob('*') if f.is_file()]
science += [UNIT/name for name in ('DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json',
    'EXECUTION_SOURCE_LOCK.json','ASSET_LOCK.json','BUILD_MATCH.json','BUILD_LOCK.json','SUMMARY.json','VALIDATION.json','MEDIA_VALIDATION.json',
    'ALL_DEV_VIEWS.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png','FAR_READBACK.json','HANDOFF_SOURCE_LOCK.json')]
js(UNIT/'ARTIFACT_MANIFEST.json',dict(utc=now(),scientific_seal=False,scope='Finite payload inventory; not scientific certification; mutable status/logs excluded.',
    files={str(f.relative_to(UNIT)):sha(f) for f in science}))
js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),required_artifacts_exist=all((UNIT/name).is_file() for name in artifacts),dev_records=4,arc_records=9,
    independent_camera_settings=12,cold_replay_exact=True,all_video_frames_decoded_exact=True,old_negatives_preserved=True,
    predeclared_TDD_implementation_addition=True,no_post_BUILD_revision=True,verdict=verdict))
# Update the mutable root entrypoint; preserve its previous exact contents locally.
prior=UNIT/'delivery_previous';prior.mkdir(exist_ok=False)
for name in ('DEMO_README_ZH.md','DELIVERY_STATUS.json'):
    if (OUTPUT_ROOT/name).exists():shutil.copy2(OUTPUT_ROOT/name,prior/name)
js(UNIT/'DELIVERY_PREVIOUS_LOCK.json',dict(files={f.name:sha(f) for f in prior.iterdir()}))
output_guard(OUTPUT_ROOT/'DEMO_README_ZH.md').write_text('''# v06 当前实验交付

最新完成：[unit007说明](units/unit_007/README_ZH.md) · [整物体对照](units/unit_007/ALL_DEV_VIEWS.png) · [实际报告](units/unit_007/REPORT_ZH.md) · [短弧视频](units/unit_007/media/owned_contour_arc_ffv1.mkv)。

原Gaussian行关联的纸底与代理墨层可真实重放；本轮前景归属轮廓加强局部外缘，但整物体NPR优势尚未建立，不升级默认。新增微小远区变化完整保留。不是原生Gaussian排线或独立语义/物理证明。

历次报告：[unit001](units/unit_001/REPORT_ZH.md) · [unit002](units/unit_002/REPORT_ZH.md) · [unit003](units/unit_003/REPORT_ZH.md) · [unit004](units/unit_004/REPORT_ZH.md) · [unit005](units/unit_005/REPORT_ZH.md) · [unit006](units/unit_006/REPORT_ZH.md)。这些负结果和原v05稀疏控制失败均未改写。

NEXT=continue，建议下一A阶段审查显式完整铲斗作者目标变体，当前尚未执行。每个新科学单元仍需独立A阶段及父级授权；本交付不表示整晚任务结束。重放CLI和外部依赖见unit007说明。
''')
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_completed_unit='unit_007',execution_state='completed',scientific_seal=False,
    scientific_verdict=verdict,gaussian_link_progress=progress,next_action='continue',report=str(UNIT/'REPORT_ZH.md'),
    updated_utc=now(),parent_monitor_verification='pending',prior_delivery_preserved_at=str(prior)))
print('HANDOFF',verdict,'elapsed_minutes',elapsed,flush=True)
