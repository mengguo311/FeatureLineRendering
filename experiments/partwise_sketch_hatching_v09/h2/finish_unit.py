"""Write the unit report from completed saved evidence; no science reruns."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,datetime,shutil
from run_h2 import UNIT,CODE,VIEWS,ARMS

def main():
    read=lambda name:json.loads((UNIT/name).read_text())
    summary=read('SUMMARY_METRICS.json');lookup={(r['view'],r['mode'],r['arm']):r for r in summary}
    head=read('HEADROOM.json');gen=read('GENERATOR_CHECK.json');dg=read('D_GENERATION.json');geometry=read('GEOMETRY.json');match=read('BUILD_MATCH.json')
    trims={a:read(f'TRIM_{a}.json') for a in ('S','D','sham')}
    receipts=[]
    for f in sorted((UNIT/'logs').glob('*.json')):
        if f.name.endswith('.start.json'):continue
        r=json.loads(f.read_text());receipts.append(dict(file=str(f.relative_to(UNIT)),**r))
    js(UNIT/'EXECUTION_RECORDS.json',dict(receipts=receipts,note='Actual completed subprocess receipts at report time. Later finalization/verification receipts remain authoritative in logs; no synthetic child success.'))
    stops=[r for r in dg['records'] if r['minus_stop']!='requested_length' or r['plus_stop']!='requested_length']
    tables=[]
    for v in VIEWS:
        x=[lookup[v,'natural',a] for a in ARMS]
        tables.append('| '+v.removeprefix('orbit_').removesuffix('_5.1')+' | '+' / '.join(f"{r['boundary_hatch']:.3f}" for r in x)+' | '+' / '.join(f"{100*r['interior_coverage']:.3f}%" for r in x)+' |')
    effectrows=[];farrows=[];lengthrows=[]
    for v in VIEWS:
        x=[lookup[v,'matched',a] for a in ARMS];u=lookup[v,'natural','U']
        effectrows.append('| '+v.removeprefix('orbit_').removesuffix('_5.1')+' | '+' | '.join(f"{r['rgb_effect']:.3f}" for r in x)+' |')
        farrows.append(f"| {v.removeprefix('orbit_').removesuffix('_5.1')} | {u['far_other_absolute']:.3f} | {u['far_background_absolute']:.3f} | 0 / 0 |")
        x=[lookup[v,'natural',a]['visible_length_natural_strength'] for a in ARMS]
        lengthrows.append('| '+v.removeprefix('orbit_').removesuffix('_5.1')+' | '+' / '.join(f"{r['proxy_visible_length']:.6f}" for r in x)+' | '+' / '.join(f"{r['proxy_visible_without_own_ink_length']:.6f}" for r in x)+' |')
    report=f'''# Unit001：Chair上缘的受控U/S/D关联

**执行完成，科学结论PARTIAL：S支持有限的局部风格留白能力；D未显示超越S的整物体收益。** 三臂及等长sham均已实际生成和渲染，结构层始终相同。没有将结构开关、减少总墨量或交叉计数直接当作H2成立。

[自然整图](media/NATURAL_COMPARISON.png) · [BUILD预算匹配整图](media/MATCHED_COMPARISON.png) · [完整墨层](media/WHOLE_LAYERS.png) · [更正后的传统代理参考](media/CONVENTIONAL_PROXY_CORRECTED.png) · [复现命令](REPRODUCE.md)

## 实际整图判断

已查看五相机自然/匹配完整联系图、完整结构与自身排线层、更正前后参考，并检查196/36的U/S/D及弱后侧D原尺寸图。S在上缘留下局部间隙，三个背侧的必要内部排线保持；自然整椅的改善幅度小，没有充分依据宣布整物体质量赢家。sham在内部产生缺口却保留上缘穿越，说明相同删除长度的位置确实影响结果，但这仍不是独立感知偏好试验。

D在196/36上缘产生更明显的弯曲，弱241/24的内部排线更少。它没有显示额外整物体价值，不作为默认替换。开放左返回、平面化框架、下背孔洞和座背空白依旧可见；高后侧仍没有可用上缘结构显示。原v08基线保留，S仅作为可选人工风格操作，不自动升级整个资产的默认版本。

## Headroom与共同基线

BUILD为151/36，选curve_id240807000001的author_edge0..9，仅在现有region5合法面上参与关联，共{head['guide_segments']}个引导线段；全部169段结构显示在每臂保持。实际发现{head['same_face_crossings']}次同面交叉，{head['visible_crossings']}次BUILD可见，涉及{len(head['affected_parent_ids'])}条父路径，总父长度{head['affected_parent_length']:.9f}。逐例face、重心交点、原ID和首交可见性见HEADROOM.json。没有撤掉原标签截断来制造headroom。

同一逐面行走器用于U/S/D，共用原父路径弧长中点种子和保存长度。U对旧路径的最大同父同面距离{gen['max_same_parent_same_face_distance']:.3g}，最大父长度差{gen['max_parent_length_error']:.3g}，无新增保护停止；五相机U自身AA墨层与原资产逐值相同，原参考hybrid也逐值恢复。保存长度本已受旧标签/长度间隙规则裁剪，不能把全部requested_length称为原始请求从未被截断。

原粗标签、原256690行及顺序/geometry/covariance/opacity/fullSH、UNKNOWN170281、27873行座面责任、全部非目标路径、全局.95纸底和结构层保持。当前上背为单层排线，没有新增或压塌交叉层。

## 唯一策略变化及长度代价

S留白半宽固定0.016875；距离由同面有限线段解析距离及真实流形共享边的五点portal路线构成。它是内在表面距离的**上界近似**，不是精确测地线，也不是XYZ最近邻。裁剪为持久face/bary区间，保留父ID与每个删除区间，不闭合开放引导，不逐帧擦墨。只将曲线解释为人工确认的风格界面，不改语义标签。原24点作者成本103.964秒；本轮新增几何控制点0，增加的角色/机制选择仍属于人工设计，不称全自动。

D先在同一表面邻接上传输引导切向，半径0.135、最大转角30°、距离线性衰减，再使用与S完全相同的停止规则。实际{dg['field']['changed_faces']}面发生方向变化，最大{dg['field']['maximum_change_degrees']:.6f}°；这是真实的局部方向风格改变，非仅方向指标优化。

| 策略 | 保存父ID数 | 裁剪前长度 | 留白/对照删除 | 最终长度 | 同面交叉 |
| --- | ---: | ---: | ---: | ---: | ---: |
| U | 108 | {geometry['arms']['U']['length']:.9f} | 0 | {geometry['arms']['U']['length']:.9f} | 7 |
| S | 108 | {trims['S']['raw_length']:.9f} | {trims['S']['trimmed_length']:.9f} | {trims['S']['retained_length']:.9f} | 0 |
| D | 108 | {dg['pretrim_length']:.9f} | {trims['D']['trimmed_length']:.9f} | {trims['D']['retained_length']:.9f} | 0 |
| sham | 108 | {trims['sham']['raw_length']:.9f} | {trims['sham']['trimmed_length']:.9f} | {trims['sham']['retained_length']:.9f} | 7 |

D在留白之前已因原作者标签边界损失{gen['raw_length']-dg['pretrim_length']:.9f}长度：{len(stops)}条父路径、6个端点提前停止，均为authored_region_boundary；没有调宽标签、延长路径或移除失败。D_GENERATION.json完整保存请求/实际长度、种子、每端停止原因。S与sham精确匹配总删除长度，但其逐视角可见删除量并不相同。sham从相同被裁父路径上、距guide至少两倍留白宽度的最长合法弧段中央确定性删除，未按DEV选择。

S/D新裁剪端点对**该实现距离**的留白误差最大约9.02e-17；这是实现自洽，不证明物理边界正确或最终像素间隙完美。固定投影2px带仍有残余排线墨，见下表。

## 必要覆盖、墨预算与负视角

全部相机距离5.1、384×384、1px、AA2及.004遮挡容差不变。目标采用保存的proxy region5；必要内部为固定2px腐蚀目标减去所选guide的固定2px投影带。它是作者标签条件评价，不是独立语义GT。每格顺序均为U/S/D/sham。

| 方位/仰角 | 边界带自身排线墨量 | 必要内部覆盖 |
| --- | --- | --- |
{chr(10).join(tables)}

S在三个有用背侧视角减少带内墨，必要内部像素覆盖及自然内部墨量不变。D在弱后侧把必要内部覆盖从41.701%降至39.950%，不能把少画解释为更干净。高后侧和前侧S自然输出与U相同；零作用是该局部操作不可见/无作用，不是局部控制成功证书。D可沿同一连通表面改变少量前侧/高后侧排线，属于目标内部的附带方向效应，保留其原结果。

BUILD按实际目标排线相对共同固定层的RGB作用量匹配，四臂目标为{match['target_budget']:.6f}；因子U={match['factors']['U']:.9f}、S={match['factors']['S']:.9f}、D={match['factors']['D']:.9f}、sham={match['factors']['sham']:.9f}，仅乘目标排线强度，结构、座面与纸底不动。最大BUILD匹配残差约0.0002，来自float32合成。以下显示固定因子到其他相机后并不等预算，未按DEV重新匹配。

| 方位/仰角 | U RGB作用量 | S | D | sham |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(effectrows)}

可见长度与缺墨必须同时读，不能只看缺墨分子。下表为自然强度，每格U/S/D/sham；matched记录中的visible_length沿用自然强度采样，实际matched像素覆盖/墨量/RGB另算，READBACK中明确此口径。

| 方位/仰角 | 当前保留路径的代理可见长度 | 代理可见但无自身墨长度 |
| --- | --- | --- |
{chr(10).join(lengthrows)}

## 绝对远区变化及Gaussian连接边界

下表是相对原彩色GS的绝对L1，采用本轮上背region5及固定2px带；不是旧座面口径。各策略值相同，包含原有全局纸底和有意的其他部位墨。策略相对原U的远其他/背景增量均为0，仅支持固定作者掩码条件下未增加远区损伤，不能宣称独立语义零泄漏。

| 方位/仰角 | 远其他绝对L1 | 远背景绝对L1 | 策略新增远其他/背景 |
| --- | ---: | ---: | ---: |
{chr(10).join(farrows)}

三臂每相机复用同一已保存source/paper/S，所有策略墨重新按该相机光栅化；不是新相机GS重建。241/60额外从原PLY冷重算，24数组完整恢复原缓存，原源数组不变。17个固定像素捕获1212个接受事件/1211个原ID，alpha和fullSH RGB最大误差约2.98e-8/2.88e-8，S重建误差2.88e-8。该CPU EWA采样连接不等于原生CUDA逐ID全图一致性、语义/物理所有权或上背路径来源证书。上背和guide仍为proxy-only，没有新增Gaussian科学优势。

## 验证、展示更正和复现

实际TDD：001_RED因缺association模块rc1；003_tests四项几何/方向/真实遮挡测试rc0。原反例不删。160张策略PNG逐像素对应数组，五视角固定层完全相同，输入/源代码/派生锁与父级DECISION保持。原始保存路径新进程重载的8个状态逐数组一致；从输入重新生成五份路径（含D裁剪前）也逐数组相同，再渲染8状态一致。

展示更正：最初proxy.png及PROXY_REFERENCE.png错误标为传统代理，但仍含座面S衰减。原文件原样保留，仅能解释为白底hybrid墨。更正结果见conventional/和CONVENTIONAL_PROXY_CORRECTED.png，确实不使用S，目标排线/结构与对应策略相同。DISPLAY_CORRECTION.json记录原因与20帧更正检查。此展示错误不改变U/S/D hybrid科学结果或策略指标；不得引用原误标图作为传统强基线。

每个数值子进程严格串行、两核亲和、单数值线程；无GPU、训练、下载、安装、嵌套模型、旧目录改写或push/merge。原v08 143/UNKNOWN、2.562698秒调度重叠、孔洞、3次自身墨跌落/1次重现，以及v07交叉角塌缩和zero_step_cycle保持历史原义。当前静态S/D无新时序证据，不能借用旧61帧认证。H1与第二物体NOT_RUN。

科学判定保持PARTIAL：完整H2三臂已执行，S局部留白选择性有证据，但整物体感知收益未确立；D有明确覆盖代价，无额外收益结论。父级独立核验待完成。

## 下一步

NEXT=continue。停止本单元的留白/角度调参，下一单元先只读审查后冻结一个有界、标签条件的H1：同一Chair、同一原source/paper/标签/结构层/风格/BUILD墨预算，合理确定性逐视角二维排线对原U持久三维排线，保留无S传统代理参考。建议25帧196/36至241/24的真实连续弧段；二维不得每帧随机重置，须公开方向、间距与相位锚定规则，并同报覆盖与实际对应误差。该问题独立于继续微调D，仍不证明Gaussian特有贡献。遵守15:20不启新科学单元、15:45科学收尾、16:00硬停。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    py='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
    commands=f'''# Unit001 reproduction

Run from `/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v09` on the authorized v09 branch. Existing read-only Python is used; no installation. All requested output directories must be new v09 HDD paths. Runtime sets CUDA empty, CPU affinity <=2 and numerical threads1 before numerical imports.

Regenerate U/S/D/sham from frozen input seeds, guide and styles, then render natural and BUILD-matched policies for one camera and compare every saved array:

```bash
{py} -B experiments/partwise_sketch_hatching_v09/h2/replay_h2.py --regenerate --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/reproductions/unit001_new --view orbit_196_36_5.1
```

This exact command shape was executed with output `units/unit_001/regeneration_check`: all5 path arrays and8 rendered states recovered. It explicitly reuses saved same-camera originalGS source/paper/S. Omit `--regenerate` for saved-path replay (also executed at replay_check). Choose any of the5 frozen camera names in inputs/cameras; use a fresh output folder each invocation. BUILD recomputes the same declared scalar normalization, other cameras retain the saved BUILD factors. No new scientific tuning is performed.

Cold originalGS verification, using all original256690 rows and source-index identity:

```bash
{py} -B experiments/partwise_sketch_hatching_v09/h2/whole_asset.py render --asset {UNIT}/inputs/assets/on --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/reproductions/unit001_cold_new --camera {UNIT}/inputs/cameras/orbit_241_60_5.1.json --reference {UNIT}/inputs/cache/orbit_241_60_5.1
```

The cold command was executed with output `units/unit_001/cold_original`:24 arrays exact; sampled original-row alpha*T/S evidence saved. It is a CPU EWA implementation, not native CUDA validation.

The scientific entry `run_h2.py` stages derive/render was used for the original unit; its default destination is this immutable completed unit and is intentionally not a command to rerun in place. Use replay_h2.py for new destinations. prepare.py records the one-time initial delivered-manifest import; do not rerun it over existing source files.

Configuration: PROTOCOL.json; original parent decision: DECISION.json; source/import/input/derived locks: SOURCE_LOCK.json, IMPORT.json, INPUT_LOCK.json, DERIVED_LOCK.json. Path inputs and surviving intervals: paths/*.npz and TRIM_*.json. Guide and tangent fields: GUIDE.npz, FIELDS.npz. Fixed original-row source and weights: inputs/data/chair/source.ply, SOURCE_BINDING.npz and inputs/assets/on/SOURCE_LINK.npz. BUILD factors: BUILD_MATCH.json. Reference correction: DISPLAY_CORRECTION.json. Actual subprocess commands/return codes: logs/*.json and EXECUTION_RECORDS.json.

Meaning: U retains all preexisting protections; S adds an open style-margin constraint; D adds bounded local guidance before the same S. Source/labels/structure display stay fixed. D's5 boundary-shortened parents and weak-rear coverage loss remain saved. Conventional reference is `media/CONVENTIONAL_PROXY_CORRECTED.png`; older `proxy.png` files are white-background source-gated hybrid ink and must not be cited as ungated proxy.
'''
    (UNIT/'REPRODUCE.md').write_text(commands)
    nextstep=dict(action='continue',recommended_next_step='Read-only review then bounded label-conditioned H1: deterministic per-view2D hatch versus original-U persistent3D hatch on25 real cameras196/36 to241/24; same masks/source/paper/style/structure/BUILD ink budget and conventional3D proxy reference. Freeze a reasonable2D direction/phase/spacing rule before evaluation; no per-frame random sabotage. Report coverage plus actual temporal alignment. No further D/margin tuning.',
        why='Meaningful controlled H2 outputs now exist. S has local conditional utility and D adds weak-rear coverage cost; the original-outline H1 coordinate/carrier question remains independently untested. Time remains before15:20; next unit requires its own read-only review.')
    js(UNIT/'NEXT.json',nextstep)
    artifacts=['PROTOCOL.json','HEADROOM.json','GENERATOR_CHECK.json','GEOMETRY.json','D_GENERATION.json','BUILD_MATCH.json','SUMMARY_METRICS.json','READBACK.json','DISPLAY_CORRECTION.json','REPORT_ZH.md','REPRODUCE.md','media/NATURAL_COMPARISON.png','media/MATCHED_COMPARISON.png','media/WHOLE_LAYERS.png','media/CONVENTIONAL_PROXY_CORRECTED.png','cold_original/RENDER_RECEIPT.json','regeneration_check/REPLAY_CHECK.json']
    status=dict(execution_state='completed',stage='H2_static_four_policy_execution_and_readback_complete',scientific_verdict='PARTIAL: S local style-margin selectivity supported; whole-object perceptual superiority unproven. D adds no demonstrated benefit over S and reduces weak-rear interior coverage. Full U/S/D plus sham actually run.',
        gaussian_link_progress='Preserved256690 original rows/order/fullSH/geometry and27873-row seat S; cold241/60 originalGS recomputation recovers24 arrays and sampled1212 accepted events. Upper-back/guide remain proxy-only; no new per-path source ownership or Gaussian-specific quality gain.',
        decision_sha256=sha(UNIT/'DECISION.json'),H1='NOT_RUN',D='RUN; negative/scoped result preserved',second_object='NOT_RUN',
        artifacts=artifacts,commands_tests=[r['file'] for r in receipts],blockers=[],parent_verification='pending independent parent read',
        preserved_failures=['D5 parents/6 endpoints stop at unchanged authored label boundaries','old high-rear structure-zero and proxy holes/open return','v08 own-ink dropouts3/reappearance1 and143/UNKNOWN','v07 cross-layer collapse/zero_step_cycle','initial proxy reference mislabeled; retained with explicit corrected reference'],
        resources=dict(CUDA_VISIBLE_DEVICES='',numerical_threads=1,affinity_max=2,serial=True,no_download_install_training=True),
        completed_utc=runtime.now(),scientific_seal=False,next=nextstep['action'])
    js(UNIT/'STATUS.json',status)
    docs=CODE.parents[2]/'docs/partwise_sketch_hatching_v09';docs.mkdir(parents=True,exist_ok=True)
    (docs/'UNIT001_REPORT_ZH.md').write_text(f'# Unit001：受控H2静态比较\n\n[完整报告]({UNIT}/REPORT_ZH.md) · [自然整图]({UNIT}/media/NATURAL_COMPARISON.png) · [匹配整图]({UNIT}/media/MATCHED_COMPARISON.png) · [复现]({UNIT}/REPRODUCE.md)\n\nU/S/D及等长sham已执行。U与原资产AA墨逐值一致。S减少局部上缘杂线，固定内部覆盖不变；D在弱后侧减少内部覆盖，未建立额外收益。科学结论PARTIAL，不升级整物体/Gaussian/时序主张。更正过一次代理参考标签，原误标文件保留。\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{p.name:sha(p) for p in sorted(CODE.iterdir()) if p.suffix in ('.py','.cpp')})
    print(json.dumps(dict(execution_state=status['execution_state'],scientific_verdict=status['scientific_verdict'],next=nextstep['action'],report=str(UNIT/'REPORT_ZH.md'))))
if __name__=='__main__':main()
