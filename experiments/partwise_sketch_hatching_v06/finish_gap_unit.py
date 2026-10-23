"""Post-result Chinese handoff; does not change frozen science or old negatives."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now,output_guard
from pathlib import Path
import datetime
import json
import shutil

p=json.loads((UNIT/'PROTOCOL.json').read_text());s=json.loads((UNIT/'SUMMARY.json').read_text())
validation=json.loads((UNIT/'VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text())
assert len(validation['views'])==13 and all(replay['exact'].values()) and replay['actual_zero_link_blank_ink']
assert len(media['all_frames_decoded_exact'])==9 and all(media['all_frames_decoded_exact'])
dev=[r for r in s['records'] if r['kind']=='dev'];weak=dev[1];build=s['build'];stats=s['paths']
verdict='INTERNAL_GAP_CONTINUITY_GAIN; WHOLE_OBJECT_NPR_READABILITY_GAIN_NOT_ESTABLISHED; NO_DEFAULT_PROMOTION'
next_step='固定unit004自然强度纸底、原20122核责任S及未补间隙的351条旧路径，单独测试相机无关的逐stroke明暗墨权重。每条stroke由已存face法线按弧长求固定平均法线，固定世界光照normalize([-0.4,-0.6,0.7])，冻结无向映射tau=0.2+0.8*(1-abs(n dot light))；法线退化回退常量并披露数量。两层采用同一规则，只将常量墨强度乘tau，不改变路径、间隙、线宽、区域、原核选择或遮挡。四BUILD按实际目标可见墨RGB L1配平，并用层内打乱tau的同预算对照检验形体相关性。检查四DEV与弱角度短弧的整物体明暗和形体可读性；若只是变淡或出现斑驳，则保留负结果，不扫描灯光/法线平滑参数。下一单元仍需A阶段重新审查并冻结决策。'
why='填153个内部计划间隙提高局部连续性和覆盖，却未建立整物体可读性收益，故停止间隙/长度扫描。实际源码中的笔触强度仍为常量，表面法线明暗只用于proxy诊断图，未进入关联墨层；原纲要M6的形体明暗是尚未检验的独立应用机制。粗代理法线可能产生错误色调，这也是必须有打乱权重负控并以完整物体证伪的原因。'
js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,
    preserve='v05 sparse failure and unit001-005 negatives, source snapshots, schema failure and historical interruptions remain immutable.'))
lines=['# Unit005：补内部计划间隙，局部连续性改善但整物体收益未建立','',
    '**冻结对照已完成。153个内部间隙得到真实可见补全；相近墨量下仍未形成明确更清楚的铲斗NPR，不升级默认。scientific_seal=false。**','',
    '本轮只改变Lego作者region4内部计划空段是否出墨。沿旧生成器的切平面与真实共享网格边遍历，保留0.12绘制/0.035空白的原周期、相位和1904个旧段的全部数组；仅给同一连接链内有左右父stroke的空段追加几何。新增153个间隙、454段、世界长度5.355，保存face/bary、chain/layer/plane/period及左右父stroke。41个链末端OFF子段被排除，未延长到边界；当前资产歧义节点0。新路径是风格变体，未称为旧路径bug修复。','',
    f'协议SHA256 `{sha(UNIT/"PROTOCOL.json")}`。60份输入、4BUILD/4DEV/9arc相机以及实验、审计、媒体源码在比较前冻结。一次缓存字段错误在任何BUILD比较前失败；窄范围适配修订另见SOURCE_REVISION_002.json，原协议和源码快照未覆盖。','',
    '纸底固定为unit004自然强度补全原GS纸底，使用39474个有外观许可的原核；墨层继续乘旧20122核的原ID责任S。完整310475原行及顺序、源PLY、几何、协方差、opacity、SH、M1与195600个UNKNOWN保持不变。新增段和父stroke ID属于代理笔触，不能当成Gaussian ID；SOURCE_LINK.npz单独保存完整原行映射和原/补全强度。','',
    '## 实际完整物体观察','',
    '已检查全部四个自然/配平完整物体视角、弱角度独立墨层和九帧实际231°–251°短弧。部分短线间的小空白确实接续了；配平墨层覆盖略广。但形体仍由近似均匀交叉网格覆盖，前侧黄色区域、后侧黄灰照片残留和部分杂乱/断续结构仍明显。新增连续线未在完整物体上稳定形成更易读的铲斗面，因此不以连通块减少或像素增加判定NPR可用性成功。此判断是本轮有限视觉检查，不是独立用户偏好实验。','',
    '## BUILD配平与DEV结果','',
    f'四BUILD自然目标墨RGB L1为旧{build["natural_target_ink_L1"]["old"]:.4f}、补全{build["natural_target_ink_L1"]["filled"]:.4f}；补全自然墨量增加{100*(build["natural_target_ink_L1"]["filled"]/build["natural_target_ink_L1"]["old"]-1):.2f}%。公共预算{build["budget"]:.4f}，全局强度系数旧{build["scales"]["old"]:.10f}、补全{build["scales"]["filled"]:.10f}。两臂实际合成读回配平，未在DEV或arc重配。自然强度同时保留。','',
    '表内成对数字为旧/补全；墨像素阈值alpha>0.05。远区为完整混合图相对原GS的绝对RGB L1，不使用分母变化冒充局部性改善。','',
    '| 视角 | 全目标/内部像素 | 配平目标墨L1 | 配平可见墨像素 | 配平内部墨像素 | 图像连通块 | 两臂远其他/背景L1 |',
    '|---|---:|---:|---:|---:|---:|---:|']
for r in dev:
    a=r['arms']['old_matched'];b=r['arms']['filled_matched']
    lines.append(f'| {r["view"]} | {r["target_pixels"]}/{r["interior_pixels"]} | {a["target_ink_L1"]:.2f}/{b["target_ink_L1"]:.2f} | {a["visible_ink_pixels"]}/{b["visible_ink_pixels"]} | {a["interior_ink_pixels"]}/{b["interior_ink_pixels"]} | {a["components"]}/{b["components"]} | {a["far_other_L1"]:.4f}/{a["far_background_L1"]:.4f} |')
gains=[100*(r['arms']['filled_matched']['visible_ink_pixels']/r['arms']['old_matched']['visible_ink_pixels']-1) for r in dev]
ratios=[r['arms']['filled_matched']['target_ink_L1']/r['arms']['old_matched']['target_ink_L1'] for r in dev]
g=weak['gap_support']
lines += ['',f'配平后四DEV墨覆盖增加{min(gains):.2f}%–{max(gains):.2f}%，但实际目标墨量新/旧为{min(ratios):.4f}–{max(ratios):.4f}；不能将稍淡或更多像素单独认作更好。自然补间隙只使全目标约5.4%–6.6%的像素发生clipped L1≥0.05变化，必须与纸底造成的大面积改色区分。完整/腐蚀内部/边界/远其他/背景的mean、sum及覆盖均在EVALUATION.json。','',
    f'弱角度241°/24°新增间隙投影长度{g["projected_length"]:.2f}px，其中代理射线判可见{g["proxy_visible_length"]:.2f}px。间隙墨层在乘S前支持{g["gap_before_S"]["visible_supported_length"]:.2f}px，乘S并配平后支持{g["gap_matched"]["visible_supported_length"]:.2f}px。旧整层在这些间隙位置已有{g["old_raw"]["visible_supported_length"]:.2f}px支持（圆帽及其他笔触重叠），补全自然强度为{g["filled_raw"]["visible_supported_length"]:.2f}px，不能把全部新增段长度算成新增可见收益。','',
    f'样本使用合并墨层，会给其他笔触重叠信用。弱角度gap-only在代理中心线判遮挡处仍采到{g["gap_raw"]["occluded_supported_length"]:.2f}px墨支持，包含像素取整、圆帽/轮廓过渡和其他间隙重叠；这不是逐笔触遮挡真值，也不能宣称完全没有穿透。真实同区域前景夹具验证了当前规则能拒绝已知遮挡，适用范围仍有限。','',
    '全部13份记录中，新增间隙造成的远其他部件与背景绝对变化均为0，墨层远区L1也均为0。纸底不变，所以两臂保留unit004已有远区损伤：四DEV总L1约18.8854、3.2938、20.3460、4.4345。旧损伤未消除；远区比例变化不能算新局部性收益。','',
    '九帧短弧保持同一三维风格变体和原核S，仅相机改变。配平后局部接续与交叉网格观感同时存在，未建立整体形体优势。4DEV+9arc只有12个不同相机设置，均为曝光诊断视角；没有独立共同可见对应，不宣称泛化或时序稳定性改善。','',
    '## 验证、回放与保留失败','',
    '三项针对性TDD先RED缺模块rc1，后GREEN rc0：真实共享边/孔洞/区域边界/歧义节点；双臂与旧渲染器逐值一致、S=0空墨、同区域前景遮挡；真实Lego旧1904段精确重建及小渲染。全部153个间隙逐项读回核对左右父stroke、连续共享边、0.035长度及face/bary；旧路径前缀逐值不变。','',
    '独立读回60个输入哈希和13份结果，使用原Gaussian ID trace重建源RGB、固定补全纸底及旧S，核对配平和目标/远区指标、M1/UNKNOWN。弱角度独立冷重放实际渲染完整原GS三次：原源+S、固定补全纸底、零S控制；source/paper/S/alpha及四个混合结果逐数组一致。零S来自实际完整GS渲染，原RGB不变，墨为空。全部九帧FFV1解码与保存PNG逐像素一致。','',
    'build_001因BUILD缓存没有legacy_raw_alpha而rc1，发生在渲染任何比较之前。旧缓存实际保存legacy_ink和support；修订仅通过原compose求旧alpha。四个真实BUILD缓存适配检查后，冻结source_snapshot_002与SOURCE_REVISION_002_LOCK，build_002成功。保留原PROTOCOL、source_snapshot、失败日志/回执及interrupted_attempt_001中的空目录，未重写失败为成功；未依据结果改变参数。','',
    'v05稀疏弱角度8.044%远区失败与4.49%区域可见变化、unit001门控收益未建立、unit002单层负结果、unit003微小可见性收益、unit004同预算纸底负结果及历史中断均不变。当前是CPU原GS纸底加原ID责任连接的代理排线，不是原生Gaussian排线、独立语义/物理归属或H1/H2/H3证明。','',
    '## 下一步','', 'NEXT=continue：'+next_step,'',why,'',
    '本轮只完成unit005，没有启动下一科学单元。']
started=datetime.datetime.fromisoformat('2026-10-23T19:07:45.083208+09:00')
elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
lines += ['',f'报告生成时执行阶段约{elapsed:.2f}分钟。']
output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')

readme=f'''# Unit005：内部计划间隙风格变体

结论：局部连续性和覆盖改善，完整物体NPR可读性收益未建立，不替换旧默认。

- ALL_DEV_VIEWS.png：四个完整物体自然强度比较。
- ALL_DEV_MATCHED.png：相同BUILD墨预算的四视角与独立墨层。
- ALL_ARC_FRAMES.png / media/internal_gap_arc_ffv1.mkv：全部九相机短弧。
- asset/FILLED_PATHS.npz：原1904段原样前缀和新增454段；asset/GAPS.npz保存153个间隙的代理锚点及父stroke映射。
- asset/SOURCE_LINK.npz：完整310475原PLY行映射、固定纸底许可和旧S权重；不是新笔触的Gaussian ID。
- dev、arc中的FRAME.npz及GAP_SAMPLES.npz保存浮点源/纸底/墨层/混合输出与新增间隙支持，EVALUATION.json保存全量区域统计。

真实完整GS冷重放（将输出目录改为不存在的新目录；默认cold_replay_001已有真实成功回执）：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' \\
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B \\
{UNIT}/source_snapshot_002/audit_gap_unit.py replay \\
--out {UNIT}/cold_replay_manual_002
```

该入口实际渲染原完整GS三次并重渲染两种代理路径，精确比较已保存输出；没有只用截图合成假装冷重放。运行时固定两核、单数值线程、禁GPU，编译目录位于新输出目录内。

外部依赖：PROTOCOL.json列出的原PLY、v05代理asset/绑定及unit003/004不可变缓存；本地只读Python环境、C++编译器。此交付不是独立可移动的完整数据包。源文件和旧实验输出只读。新代码使用v06本地runtime；必须设置上面的V06_UNIT_DIR。

原source_snapshot/PROTOCOL保留；实际比较使用source_snapshot_002，窄缓存修订记录在SOURCE_REVISION_002.json。所有命令、实际退出码见logs；初始RED和build_001失败未覆盖。报告与NEXT说明局限和下一独立候选；scientific_seal=false。
'''
output_guard(UNIT/'README_ZH.md').write_text(readme)
receipts=[]
for f in sorted((UNIT/'logs').glob('*.receipt.json')):
    r=json.loads(f.read_text());receipts.append(dict(name=f.name,argv=r['argv'],returncode=r['returncode'],elapsed_seconds=r['elapsed_seconds']))
artifacts=['REPORT_ZH.md','README_ZH.md','PROTOCOL.json','SOURCE_REVISION_002.json','asset/FILLED_PATHS.npz','asset/GAPS.npz','asset/SOURCE_LINK.npz',
           'SUMMARY.json','VALIDATION.json','BUILD_MATCH.json','ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json',
           'cold_replay_001/REPLAY_CHECK.json','media/internal_gap_arc_ffv1.mkv']
progress=dict(previous_gap='Planned short-stroke gaps remained after paper support and visibility experiments.',
    actual_advance='Preserved all old 1904 segments and appended 153 topology-bounded internal gaps with explicit parent provenance. Actual original-ID S controls their visible ink; source and paper independently reconstructed and cold-replayed.',
    original_rows=310475,paper_permission_rows=39474,ink_S_rows=20122,UNKNOWN_unchanged=195600,
    visible_outcome='More local ink continuity/coverage at comparable effect, zero added far damage; whole-object NPR readability advantage unestablished.',
    representation='Original-GS paper + original-ID-linked proxy paths; not native Gaussian ink or physical/semantic ownership.')
js(UNIT/'STATUS.json',dict(execution_state='completed',stage='internal_gap_comparison_handoff',scientific_verdict=verdict,
    gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,completed_utc=now(),elapsed_minutes=elapsed,
    artifacts={name:str(UNIT/name) for name in artifacts},tests_and_actual_commands=receipts,blockers=[],
    limitations=['Whole-object readability gain not established','Projected gap-support union can credit overlapping strokes; not occlusion truth',
        'Residual photo texture and uniform cross-grid appearance remain','Exposed authored-proxy views and CPU replica only'],
    preserved_failures=[dict(stage='tdd_red_001',returncode=1,reason='expected missing module'),
        dict(stage='build_001',returncode=1,reason='missing BUILD cache field; pre-comparison adapter error; amended and retried with new snapshot')],
    next_action='continue'))
handoff=UNIT/'handoff_source';handoff.mkdir(exist_ok=False)
shutil.copy2(Path(__file__),handoff/Path(__file__).name)
js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in handoff.iterdir()},utc=now()))
science=[]
for name in ('asset','build_match','dev','arc','cold_replay_001','media'):
    science += [f for f in (UNIT/name).rglob('*') if f.is_file()]
science += [UNIT/name for name in ('DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_REVISION_002.json','SOURCE_REVISION_002_LOCK.json',
    'ASSET_LOCK.json','BUILD_MATCH.json','BUILD_LOCK.json','SUMMARY.json','VALIDATION.json','MEDIA_VALIDATION.json','ALL_DEV_VIEWS.png','ALL_DEV_MATCHED.png','ALL_ARC_FRAMES.png')]
js(UNIT/'ARTIFACT_MANIFEST.json',dict(utc=now(),scientific_seal=False,scope='Inventory of verified finite payload, not a scientific certification; mutable status/logs excluded.',
    files={str(f.relative_to(UNIT)):sha(f) for f in science}))
js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),required_artifacts_exist=all((UNIT/name).is_file() for name in artifacts),
    dev_records=4,arc_records=9,independent_camera_settings=12,cold_replay_exact=True,all_video_frames_decoded_exact=True,
    old_negative_results_preserved=True,source_revision_preserved=True,verdict=verdict))
print('HANDOFF',verdict,'elapsed_minutes',elapsed,flush=True)
