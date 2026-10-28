"""Write an evidence-bound handoff after actual render, readback and replay."""
import runtime
from runtime import ROOT as U,js,sha
import json,datetime,shutil
from run_motion import locks,ARMS

def main():
    locks();m=json.loads((U/'SUMMARY_METRICS.json').read_text());n=json.loads((U/'REPORT_NUMBERS.json').read_text())
    t=json.loads((U/'TEMPORAL.json').read_text())['results'];read=json.loads((U/'READBACK.json').read_text());replay=json.loads((U/'REPLAY_CHECK.json').read_text())
    assert len(m)==39 and len(replay['exact_array_files'])==11
    for rec in json.loads((U/'IMPORT.json').read_text()):assert sha(rec['source'])==rec['sha256']
    for rec in json.loads((U/'BOOTSTRAP_IMPORT.json').read_text())['files']:assert sha(rec['source'])==rec['sha256']
    rows=[]
    for k in ('BUILD','000','024','027','029','032','034','035','036'):
        v=m[k]['metrics']['natural'];band=' / '.join(f"{v[a]['regions']['boundary_band']['own_ink_mass']:.3f}" for a in ARMS) if m[k]['boundary_observable'] else 'NA（无可见引导）'
        cover=' / '.join(f"{100*v[a]['regions']['necessary_interior']['coverage_fraction']:.3f}%" for a in ARMS)
        rows.append(f'| {k} | {band} | {cover} |')
    temporal=[]
    for a in ARMS:
        z=t['natural']['totals'][a]
        temporal.append(f"| {a} | {z['joint_retained_visible_length']:.6f} | {z['own_dropout_length']:.6f} | {100*z['dropout_fraction_of_source_own_joint_length']:.6f}% | {z['composite_cancellation_count']} |")
    began=datetime.datetime.fromisoformat('2026-10-28T05:27:40.691561+00:00');elapsed=(datetime.datetime.now(datetime.timezone.utc)-began).total_seconds()/60
    report='''# Unit003：冻结 H2 关联政策的实际连续视角对照

**39 个科学相机、U/S/D/sham 四政策执行完成；科学结论 PARTIAL。** S 保留有限的上缘风格留白能力，在同一保留父区间没有增加观测到的自身墨跌落，但新增抬高视角出现必要内部覆盖损失。D 没有显示超越 S 的整物体价值，内部覆盖代价更明显。没有升级默认资产或声称完整 H2 成立。

[自然影片](media/natural_orbit.png) · [BUILD 匹配影片](media/matched_orbit.png) · [完整关键帧](media/natural_KEYFRAMES.png) · [全部37帧](media/natural_ALL_FRAMES.png) · [独立墨层](media/WHOLE_LAYERS.png) · [传统代理参考](media/CONVENTIONAL.png) · [复现命令](REPRODUCE.md)

已查看自然/匹配完整关键帧、37帧自然联系图、完整结构/排线层和传统代理图，并检查 BUILD、012、027/028、034/035 原尺寸整图。上缘留白是局部、小幅变化；D 的上缘弯曲与部分内部变稀可见。高仰角时靠背挤成窄带，曲线碎裂并隐藏；原开放左返回、平面框架、下背孔洞、座背空白仍在。传统代理表达相同主要形体。没有独立感知偏好试验或真人播放器认证。

## 冻结机制、公平性与真实来源

父级 DECISION 原样保留。直接使用 unit001 保存的 U/S/D/sham、D_before_stop、GUIDE、父区间裁剪记录及 BUILD_MATCH，没有重生成或调参。关联范围为 curve_id240807000001、author_edge0..9、region5 上52段；所有臂完整169段结构始终 ON。原7次同面交叉的面及父ID在准备阶段重新核对。原作者24点、103.964秒的成本保留，本轮新增几何控制点0；该曲线只被解释为人工确认风格界面，不是独立语义边界、物理真值或自动恢复。

共同生成器 U 的旧公平性记录保留；本轮每一个相机还独立光栅化未改原路径，U自身AA墨逐值相同。BUILD、000、024、036、FRONT的自然/匹配四臂hybrid与目标墨逐值恢复unit001。U在unit002共用相机也精确恢复其B1。没有撤除标签保护、改轮廓或用结构开关替代关联。

S半宽0.016875；D半径0.135、最大转角30°，均为原冻结值。距离是同面有限线段及真实共享边五点portal路径的内在距离上界近似，非精确测地线或跨薄片XYZ近邻。原单层风格保持；D的429面方向改变、最大29.960823°属于公开的局部风格改变。

| 政策 | 裁剪前长度 | 计划删除 | 最终长度 |
| --- | ---: | ---: | ---: |
| U | 14.118902968 | 0 | 14.118902968 |
| S | 14.118902968 | 0.298775285 | 13.820127683 |
| D | 14.019701773 | 0.299801307 | 13.719900466 |
| sham | 14.118902968 | 0.298775285 | 13.820127683 |

D在裁剪前已因原标签边界损失0.099201196长度，5条父路径/6个端点提前停止；没有把这部分当作新时序丢墨。S/sham等世界删除长度，不等逐帧可见删除量。S新视角可见计划删除量0–0.298775285，sham约0.104895–0.197546，不能假定两者删除了相同像素。

全部原256690行、行顺序、geometry/covariance/opacity/fullSH、UNKNOWN170281、27873行座面责任、标签、网格、非目标路径及全局.95纸底保持。上背与引导依然proxy-only；没有新增原Gaussian路径所有权证书。

## 相机、缓存与墨预算

37帧连续有限轨迹：000–024为196/36至241/24，025–036固定方位241、仰角每步3°直到60；另BUILD151/36与FRONT61/24，共39科学相机。距离5.1、384×384、1px、AA2、.004可见性容差固定。28份准确同相机source/paper/S缓存按来源与哈希冻结，025–035的11个新增仰角从原PLY实际重算。所有39相机四臂排线和结构均重新光栅化，无图像插值或逐帧选线。8fps仅为影片播放速度，末尾回起点是播放重置，不是连续360°。

自然强度与原BUILD一次匹配均保留；因子U/S/D/sham为0.947174042/0.968592376/0.999999851/0.974304706，仅作用目标排线。BUILD约718.1965实际RGB作用量，之后绝不逐视角重匹配。新相机等BUILD预算不等覆盖或DEV预算。matched的同ID墨按各固定因子计算，合成增量从该模式真实图像重新读取，不复用自然增量。

## 局部留白、必要形体与失败视角

目标为保存代理region5；必要内部为固定2px腐蚀减去可见guide的固定2px膨胀带。每帧保存面积分母，评价条件是作者标签。下表各格顺序均为 U / S / D / sham。

| 帧 | 固定边界带自身墨量 | 必要内部覆盖 |
| --- | --- | --- |
'''+ '\n'.join(rows)+'''

S在抬高帧027/028/029/032损失必要覆盖，分别约0.1001/0.1099/0.2410/0.1715个百分点；未扩大掩码消除反例。D在37帧中36帧覆盖低于U，最大差为027的5.3053个百分点；终点略高不能抵消整个序列代价。D少画不能被称为更干净。

035=241/57、036=241/60及FRONT无可见guide带，边界结论为NA。034虽有13个带像素，S与U的带墨相同；不是每个可见引导角度均有收益。高后侧原结构合成零增量保持。内在留白端点误差约9e-17仅是对该实现距离的自洽；逐相机带内残余墨和裁剪段投影长度已保存，未把它们当成独立真实像素留白精度。

## 同ID实际墨与共同分母

在评价前对每个裁剪前线段按删除区间端点精确分段，最大世界采样步长.005。U/S/D/sham分别3517/3524/3503/3528个固定样本。计划删除有独立长度与可见分母；渲染器track_ids只读取对应父笔触的AA墨，不能借邻线补足。U_on_S/U_on_sham使用与对应策略完全相同的样本和保留区间。D用自身裁剪前几何，不能将方向移位当作未命中U坐标。

下表累计36个相邻对的两个方向，共72个方向对；长度单位为场景世界单位重复累计，次数是样本—转移观测，不是独立笔触数或物体数。

| 政策 | 共同可见保留长度 | 自身墨跌落长度 | 跌落/源有墨共同长度 | 合成遮盖跌落观测 |
| --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(temporal)+'''

自然强度U/S/D/sham的自身墨跌落观测为290/285/284/285，但分母不同。**S与U_on_S的跌落长度1.122668853、计数285及共同长度360.092685980完全相同**；匹配强度下亦相同，跌落长度1.126812330、计数286。支持本次采样的保留部分没有新增跌落，不支持S改善时序。S较小的总缺墨分子主要伴随裁剪缩短分母。

按实际播放方向，U/S/D/sham的跌落为152/146/142/149，重现138/139/142/136；S对应的U_on_S同为146/139。反向评价不是额外独立实验。实际单帧最大可见无同ID墨长度U/S约0.181741，D约0.171260，不能把D较短路径解释为更完整。匹配会改变1/255描述阈值附近的观测，原自然与匹配结果分别保存。

正确的同代理深度/标签拒绝与共同可见跌落分开记录，屏外退出在本轨迹为0；这不是独立物理遮挡真值。自身墨仍在时的合成遮盖来自max并集，不能与自身缺墨合并。原v08结构3次跌落/1次重现继续保持历史范围，本轮上背路径观测不覆盖该历史证据，也不宣称无闪烁。

## 绝对远区、原始失败及验证

相对原彩色GS，39相机远其他绝对L1为10103.270–13980.662，远背景588.851–974.563；包含全局纸底和有意的其他部位墨，不能用差分抵消。自然强度各臂相对自然U的新增远区均0，但匹配不能统称零：030=241/42像素(157,185)在固定native标签中为region4，匹配U/S/sham相对自然U的FAR-other增量为0.016402692/0.009752154/0.007978410；D为0。相对匹配U则S/D/sham为0.006650537/0.016402692/0.008424282。该现有AA目标笔触足迹受全局目标强度因子影响；固定掩码及输出未更改，不声称独立语义零泄漏。

实际TDD：001缺observations模块RED rc1，002七项GREEN，覆盖计划裁剪、同ID墨、真实遮挡、同面交叉、近邻分离片、共享边及开放端点。首次审计020把“所有远区必为零”误作断言，实际rc1及代码保留failed_attempts/audit_zero_far_assumption。021改为核验真实数值并明确记录失败，科学零远区门槛没有被改成通过。

首批005工具外层rc143，wrapper/child UNKNOWN、最终回执缺失、原因UNKNOWN；五帧000–004已完整写出。确认本批进程不在后，核验数组及80张策略PNG并保留原输出，后续缩短批次续跑，没有重画或伪造005成功。后续实际回执均另存。旧v08 rc143/UNKNOWN、2.562698秒调度重叠与路径偏差、unit002错误路径及原失败二维基线全部保留。

780张策略/公共层PNG逐值对应数组；两个APNG各37帧全部解码，与实际整图面板逐值相同。传统代理不使用座面S，三个检查相机12张图由独立光栅化核验。38相机37559个保存接受事件按原行ID重建fullSH RGB/S，最大误差5.7750e-8/2.9289e-8，T链误差0；FRONT未导入trace，不计入38。CPU稀疏事件验证不是原生CUDA逐ID全图一致性或上背来源认证。

保存源码入口新进程在025从原PLY重算source/paper/S，重载四政策路径，11份数组文件（公共层、观测、trace与8政策状态）逐值恢复。源/输入/协议/父决策锁及本轮导入的旧文件哈希保持。报告的工程核对不是研究胜利，父级独立核验待完成。

本轮严格两核亲和、单数值线程、串行CPU；无GPU、训练、下载、安装、嵌套模型、push/merge或旧目录改写。实际渲染约3.8–10.6秒/相机，不是8fps实时性能。H1本轮NOT_RUN，unit002条件性结果保留；第二对象NOT_RUN。

## 下一独立问题

NEXT=continue。下一单元先只读审查再冻结：unit002的合理二维B0与持久三维U，在本轮新增241/24→241/60的13帧抬高弧段中，先前条件性H1时序差异是否仍存在，还是在投影压缩/首交隐藏下反转？使用原B0配置、方向、相位、BUILD因子和原U，复用准确同相机GS缓存，实际重新生成二维排线与渲染两臂，保留传统3D参考并报告相同可见分母、覆盖及原始缺墨。不得调整二维密度/相位或三维样式来维持旧结论。该问题检验新的失效条件，不是追加影片、改进D或宣称纯锚定因果效应；若不能形成合理受控对照则诚实NOT_RUN并收尾。仍须父级冻结下一决策，遵守15:20/15:45/16:00。
'''
    (U/'REPORT_ZH.md').write_text(report)
    reproduce='''# Unit003 reproduction

This is the actual Linux CPU experiment, with fixed authored proxy labels and guide. It is not a relocatable or cross-platform certification. All original sources and previous outputs remain read-only.

Use the existing interpreter; no installation or GPU is required. Run commands serially. The entry sets CUDA visibility empty, affinity to two CPUs and numerical threads to one before numerical imports.

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v09
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_003/source/h2_motion/run_motion.py render --keys 025 --replay-key USER_REPLAY_025
```

This single command reloads frozen U/S/D/sham paths and original PLY, genuinely rerenders GS/paper/S at241/27, then rasterizes all four policies in natural and BUILD-matched modes. It writes only a new `unit_003/renders/USER_REPLAY_025` directory. Existing output names are rejected. Use a fresh output name for another replay.

For a saved-source BUILD check, substitute `--keys BUILD --replay-key USER_REPLAY_BUILD`; source/paper/S is explicitly cached there while all policy paths are freshly rasterized. `CAMERAS.json` names all39 science cameras and cache provenance. Do not rerun `prepare` over this populated unit or invoke inherited historical main scripts.

`inputs/assets/on` and `inputs/data/chair` preserve the original mesh/labels/source rows; `frozen/paths`, `frozen/GUIDE.npz`, `frozen/FIELDS.npz`, `frozen/TRIM_*.json`, `frozen/D_GENERATION.json` and `frozen/BUILD_MATCH.json` preserve the association policies, provenance and factors. `samples` preserves fixed interval quadrature. `INPUT_LOCK`, `SOURCE_LOCK`, `PROTOCOL_LOCK`, `IMPORT` and `HANDOFF_SOURCE_LOCK` identify exact files. Read `REPLAY_CHECK.json` for the actual cold025 run that recovered11 array files.

The saved h2_motion runtime overrides inherited imports and confines writes to unit003. Source locks also check the original worktree code; keep it available unchanged. Analysis aggregates saved results; scientific outputs are never rewritten to repair a failure. Videos are37 actual camera frames at8fps playback, with a discontinuous loop reset, not360 degrees or real-time rendering.

Scientific conclusion remains PARTIAL. Read `REPORT_ZH.md`, `INTERRUPTION_005.json`, `FAR_COUNTEREXAMPLE.json` and the preserved failed audit. S has small interior-coverage costs; D has no demonstrated extra whole-object benefit. Neither is silently promoted over the baseline.
'''
    (U/'REPRODUCE.md').write_text(reproduce)
    nextstep=dict(action='continue',recommended_next_step='Read-only review then freeze conditional H1 robustness on the13-camera241/24→241/60 elevation arc: unchanged unit002 deterministic2D B0 versus original persistent3D U, identical source/paper/labels/style/structure and original BUILD factors; actually generate/render B0 at11 new angles using unit003 exact-camera caches, report coverage and same-visibility denominators, conventional3D reference, no retuning.',why='Unit003 establishes only limited H2 margin persistence and reveals high-elevation costs. H1 has only back-azimuth temporal evidence plus isolated high endpoint; the new elevation transition tests an independent failure regime and may reverse the earlier conditional trend. Not a D parameter scan or replay-only unit. Next parent review/freeze required;15:20/15:45/16:00 boundaries remain.')
    js(U/'NEXT.json',nextstep)
    status=dict(execution_state='completed',stage='39_camera_four_policy_render_temporal_media_readback_and_cold_replay_complete',
        scientific_verdict='PARTIAL: S preserves same-ID ink on matched retained parent support, but4 elevation views lose necessary interior coverage (max0.2410 percentage points); D has no added whole-object value and max5.3053-point coverage loss. No overall H2/Gaussian superiority.',
        gaussian_link_progress='Original256690 rows/order/geometry/covariance/opacity/fullSH,UNKNOWN170281,seatS27873 preserved.11 new actual originalGS cameras;28 explicit same-camera caches.38-camera37559 original-row accepted events reconstruct fullSH RGB/S. Upper-back/guide remain proxy-only; no path ownership or nativeCUDA parity.',
        H2='RUN: U/S/D/sham at39 cameras,37-frame trajectory; scoped PARTIAL',H1='NOT_RUN in unit003; conditional unit002 result preserved',second_object='NOT_RUN',
        artifacts=['PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','PROTOCOL_LOCK.json','HANDOFF_SOURCE_LOCK.json','SUMMARY_METRICS.json','TEMPORAL.json','EVENTS.json','REPORT_NUMBERS.json','READBACK.json','REPLAY_CHECK.json','FAR_COUNTEREXAMPLE.json','REPORT_ZH.md','REPRODUCE.md','media/natural_orbit.png','media/matched_orbit.png','media/natural_KEYFRAMES.png','media/WHOLE_LAYERS.png'],
        commands_tests=[str(p.relative_to(U)) for p in sorted((U/'logs').glob('*.json')) if not p.name.endswith('.start.json')],
        blockers=[],preserved_failures=['005 outer143 wrapper/childUNKNOWN missing final receipt;complete000..004 validated and retained','020 audit rc1 zero-FAR assumption; scientific matched FAR nonzero remains','S4 elevation coverage losses;D36/37 lower interior coverage','nonzero own-ink losses for all arms;guideNA035036FRONT','all prior holes/open return/high rear zero/v08 dropouts143UNKNOWN/scheduling deviation/unit002 failures'],
        decision_sha256=sha(U/'DECISION.json'),parent_verification='pending independent parent read',scientific_seal=False,resources=dict(affinity=[0,1],numerical_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),
        completed_utc=runtime.now(),elapsed_minutes=elapsed,next='continue')
    js(U/'STATUS.json',status)
    js(U/'FINAL_READBACK.json',dict(utc=runtime.now(),original_imports_unchanged=True,protocol_source_input_decision_unchanged=True,
        actual_receipts={p.stem:json.loads(p.read_text())['child_returncode'] for p in sorted((U/'logs').glob('*.json')) if not p.name.endswith('.start.json')},
        missing005_final_preserved=not (U/'logs/005_arc000_004.json').exists(),audit020_failure_preserved=True,scientific_zero_far_gate='failed; not relabeled',replay_exact_files=11))
    print(json.dumps(dict(execution_state=status['execution_state'],verdict=status['scientific_verdict'],elapsed_minutes=elapsed,next='continue'),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
