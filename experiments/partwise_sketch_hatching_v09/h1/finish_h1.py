"""Handoff for actual completed unit002 outputs; no experiment or gate rewrites."""
import runtime
from runtime import ROOT as UNIT,js,sha,CODE,BASECODE
import json,shutil,datetime
from pathlib import Path
from run_h1 import locks

def main():
    locks();report=json.loads((UNIT/'READBACK.json').read_text());temporal=json.loads((UNIT/'TEMPORAL.json').read_text())
    rows=json.loads((UNIT/'SUMMARY_METRICS.json').read_text());by={r['key']:r for r in rows}
    source_pixels=sum(r['visibility']['source_target_pixels'] for r in temporal['pairs']);common=sum(r['visibility']['common_visible_pixels'] for r in temporal['pairs'])
    resolved=[];receipts=[]
    for p in sorted((UNIT/'logs').glob('*.start.json')):
        q=p.with_name(p.name.replace('.start.json','.json'))
        if q.exists():
            r=json.loads(q.read_text());receipts.append(r);resolved.append(dict(start=p.name,final=q.name,actual_child_returncode=r['child_returncode']))
        else:resolved.append(dict(start=p.name,final='MISSING',actual_child_returncode='UNKNOWN',note='004 launch: child not started, FileNotFoundError; current finish receipt remains active until this process exits' if p.name.startswith(('004','019')) else 'Preserved actual missing receipt'))
    ordered=sorted(receipts,key=lambda r:r['started_utc'])
    assert all(a['finished_utc']<=b['started_utc'] for a,b in zip(ordered[:-1],ordered[1:]))
    for root,target in ((CODE,UNIT/'source/h1'),(BASECODE,UNIT/'source/h2')):
        target.mkdir(parents=True,exist_ok=True)
        for p in root.iterdir():
            if p.suffix in ('.py','.cpp'):shutil.copyfile(p,target/p.name)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{str(p):sha(p) for root in (CODE,BASECODE) for p in root.iterdir() if p.suffix in ('.py','.cpp')})
    js(UNIT/'FINAL_READBACK.json',dict(utc=runtime.now(),decision_unchanged=True,input_source_protocol_locks_unchanged=True,
        original_imports_unchanged=True,serial_completed_commands=True,resolved_receipts=resolved,
        prior_READBACK_active_self_receipt='016 was active during READBACK writing; its actual final receipt now exists and is rc0; original snapshot retained',
        common_pixel_observations=common,source_target_pixel_observations=source_pixels,common_fraction=common/source_pixels,
        documented_replay=json.loads((UNIT/'renders/REPRO_BUILD_A/REPLAY_CHECK.json').read_text()),
        unit_bytes=sum(p.stat().st_size for p in UNIT.rglob('*') if p.is_file()),root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(UNIT).free,
        parent_verification='pending independent parent read'))
    intro='''# Unit002：标签条件的二维／三维排线时序对照

**执行完成，科学结论PARTIAL：原U持久三维排线在本次25帧Chair弧段中具有条件性时序优势，但没有建立等评价覆盖下的纯锚定因果优势、整物体质量赢家或Gaussian特有贡献。**

[自然影片](media/natural_orbit.png) · [BUILD匹配影片](media/matched_orbit.png) · [完整关键帧](media/KEYFRAMES.png) · [全部自然帧](media/natural_ALL_FRAMES.png) · [独立墨层](media/WHOLE_LAYERS.png) · [复现](REPRODUCE.md)

已查看完整关键帧与全部25帧联系图、独立结构/排线层，以及BUILD、000、012、弱后侧020/021/022和高后侧原尺寸图。两臂均表达同一整椅；B0在背侧较密，转向弱后侧后笔触数量与相位出现明显变化，020→021上背墨减少，B1保持较好。B0并非没有可用形体，也没有每帧随机重置。B1仍有实际缺墨；开放左返回、原孔洞、座背留白和排线跨内框保持。传统代理表达同样主要形体，没有GS画质优势结论。没有真人实时播放器或独立感知偏好试验。

## 冻结比较与二维基线

父级DECISION原样保存。使用实际Chair冻结vanilla-GS及其代理，未重训RaDe-GS、未换真值网格。目标仅region5；原256690行及顺序、geometry/covariance/opacity/fullSH、UNKNOWN170281、27873行座面责任、原标签/网格、全部原路径、169段开放结构、轮廓和全局.95纸底保持。所有臂结构始终ON，本轮不以结构开关替代H2。

B1就是原U，未引入S或D。B0在每视角首交面上投影同一原始三维无向方向场，以0.5px中点步长在二维积分；符号连续，标签边缘、.035深度断层和投影退化停止。B0获得一个BUILD冻结的部件位置/方向锚点用于整体平移与朝向，而非被迫锁死屏幕方向。每条笔触无持久三维锚点，不复制B1路径，不做光流或逐帧人工修线。固定相位为0.1732050808/0.3819660113；BUILD可见几何Jacobian中位数给出间距5.6739165px、最大长度51.1035858px、间隙4.065058px，之后不随评价结果调节。单层、1px、AA2、自然强度.45、共同首交标签与.004深度容差保持。

因此这是共享标签和方向条件下的两个生成系统比较：二维格点/积分/固定像素尺度与三维路径的透视压缩、种子及断开方式仍有差异，不能把全部结果归为纯坐标锚定因果效应，也不是最佳二维时序NPR或自动二维/三维分割实验。

首个BUILD暴露了中心落在掩码外的合法笔触片段被漏掉的问题，原B0作用量543.073、必要覆盖20.944%，明显少画。该结果及原代码/协议/匹配参数全部保留在failed_attempts/initial_center_only_baseline。新增针对性RED后，改为枚举每条请求格线与掩码/深度连续区间的交集，在每段内选择最接近原中心的种子，保留原周期、相位及两端剩余长度。修复后BUILD为26条二维路径；没有调方向、密度或长度。重新冻结发生在任何DEV渲染之前。该失败不是可引用的主基线。

## 实际相机、预算和覆盖

BUILD为151/36；25帧为方位196+45i/24、仰角36-12i/24、i=0..24，距离5.1、384×384。另渲染241/60静态负视角，共27科学相机。每个相机都实际重算原GS、纸底、S和两臂排线，批次复用已加载源及CPU库，无旧图插帧或新视角缓存冒充。BUILD/000/024/HIGH的原U source/paper/S/hybrid逐值恢复unit001。旧高后侧结构合成增量为零的失败仍在；高后侧不属于本轮动态弧段。

BUILD自然RGB作用量B0/B1为800.1696/758.2520；固定因子0.947614342/0.999999970匹配至758.2520，float32余差小于0.0004。匹配只作用于目标墨，结构、座面与纸底不变。**等BUILD预算不等于等DEV预算或覆盖**；未逐视角重匹配。必要内部为目标2px腐蚀，未扣H2引导带，因此不能直接与unit001的必要覆盖数值混用。

| 帧 | 自然RGB作用量 B0/B1 | 匹配RGB作用量 B0/B1 | 必要内部覆盖 B0/B1 |
| --- | ---: | ---: | ---: |
'''
    table=''
    for key in ('BUILD','000','012','021','024','HIGH'):
        n=by[key]['metrics']['natural'];m=by[key]['metrics']['matched']
        table+=f"| {key} | {n['B0']['target_rgb_effect']:.3f} / {n['B1']['target_rgb_effect']:.3f} | {m['B0']['target_rgb_effect']:.3f} / {m['B1']['target_rgb_effect']:.3f} | {100*n['B0']['regions']['necessary_interior']['coverage_fraction']:.3f}% / {100*n['B1']['regions']['necessary_interior']['coverage_fraction']:.3f}% |\n"
    body='''
弧段内B0自然作用量359.875–879.038，B1为543.071–578.158；B0必要覆盖21.448%–35.437%，B1为18.011%–43.533%。二维臂早期较密、弱角变稀；三维臂随投影压缩覆盖率上升。必须连同实际图像阅读，不把少画自动解释成更干净。

## 双向实际输出时序

所有相邻帧两个方向都评价，共48个方向对。像素主指标从双方共同的native像素中心深度/标签建立对应，双线性深度不跨无效孔洞，.004首交容差固定。中心线指标分别从每个方法自己的中心线按不超过0.5px采样，检查源帧实际自身AA墨及连续首交，再投影到目标帧实际自身墨；B1额外用真实线段深度剔除隐藏投影。不是只在B1锚点取样或只检查保存坐标。目标墨使用双方各自地图，不借结构/座面墨。

| 统计（自然强度） | B0 二维 | B1 三维 |
| --- | ---: | ---: |
| 每共同像素绝对墨误差 | 0.063073 | 0.026640 |
| 逐方向对平均、union墨量归一化误差 | 0.592088 | 0.349214 |
| 共同可见自身中心线累计长度px | 27205.962 | 22310.999 |
| 中心线至目标实际墨的长度加权距离px | 0.370497 | 0.007939 |
| 上述长度中目标无自身墨px | 5871.675 | 16.051 |
| 源代理可见长度累计px | 27207.094 | 22345.589 |
| 源代理可见但无自身墨累计px | 0.000 | 28.080 |
| 像素自身墨→空观测 / 源墨像素观测 | 5173 / 43475 | 37 / 35534 |

BUILD匹配后的每共同像素误差为0.059769/0.026640，union归一化误差仍为0.592088/0.349214。三维误差较低的方向同时出现在像素归一化与双方中心线距离中，但两臂覆盖/可见长度不等，不能用单个原始L1宣布等覆盖质量胜利。最近墨可能属于邻近笔触，中心线数值也不是逐ID真实对应精度；二维路径可重叠，累计路径长度不是去重墨面积。proxy自身参照没有独立物理真值，25帧/像素不是独立物体样本，不能宣称统计显著性。

自然强度下，自身墨存在但合成增量不足的共同像素观测为624/592；自身墨仍在而合成增量跌落为66/8。它们不是同等数量的笔触丢失。目标遮挡拒绝单列在每方向对centerlines记录中。本轮没有计划LOD、H2裁剪或明暗切换。B1的28.080源缺墨累计长度和16.051目标缺墨累计长度不被归零，旧结构3次跌落/1次重现也不能被本轮结果覆盖。

## 远区、来源及实际验证

所有相机、两模式两臂相对原U的固定2px带外其他部位/背景新增L1均为0。相对原彩色GS的绝对远区损伤没有抵消：弧段远其他10175.699–13651.814，远背景588.851–865.362；高后侧为13980.662/965.713。这包括原有全局纸底与有意的其他部位墨，不是独立语义零泄漏证明。

传统参考确实使用原始座面墨、不乘S，四检查相机由独立AA重渲染逐值核对。上背本身及结构仍proxy-only；全部原GS数值数组与原行身份保持。27相机的25577个保存接受事件独立重建fullSH RGB与座面S，最大误差5.7750e-8/2.8776e-8，T链误差0。CPU EWA采样记录不等于原生CUDA逐ID全图一致性、语义所有权或新排线路径来源认证。

实际TDD：001缺模块RED rc1；002四项GREEN；006边缘种子RED rc1；007五项GREEN，包含确定性、方向正负等价、掩码/分离表面停止、已知相机平移与遮挡对应，以及中心在外的合法笔触覆盖。未用同实现自证取代实际Chair。

243张策略/传统PNG逐像素对应数组；自然/匹配APNG各25帧、全部解码逐值等于原整图面板。8fps仅为播放速度，帧计算4.934–6.407秒，循环回起点只是播放重置。012新进程重新加载原PLY、重新生成B0并重渲染，8份数组文件逐值相同；文档CLI的BUILD另一次冷复现也通过。原父级决策、输入、科学源码/协议锁与导入来源保持。父级独立核验仍待完成。

执行偏差均保留：004命令中Python路径拼写错误，wrapper外层rc1、子进程未启动，原start中的UNKNOWN与缺失最终回执不补造；005正确路径恢复。011科学脚本路径拼写错误，实际child rc2，012恢复，未产生该批帧。READBACK写入时016自身最终回执尚未存在，其原快照保留，FINAL_READBACK记录实际最终rc0。没有删除或改写失败为成功。旧v08 143/UNKNOWN、2.562698秒重叠、路径偏差、v07交叉层塌缩与zero_step_cycle继续保留原义。

本轮数值命令严格串行、两核亲和、单数值线程、CUDA空；无GPU、训练、安装、下载、嵌套模型或push/merge。未改任何unit001、旧v04–v08输出或orchestration文件。原科学输出外仅写新的复现目录。没有为了完美美学继续调二维相位/密度或三维样式。

## 下一独立问题

NEXT=continue：下一单元先只读审查，再检验**unit001冻结的H2留白/方向政策能否在真实相机变化中保持局部留白收益而不增加自身墨跌落或必要覆盖损失**。可使用本轮准确同相机的source/paper/S缓存，重新光栅化原U/S/D/sham持久路径，沿用unit001 BUILD匹配因子、引导角色/几何/宽度/方向规则。研究输出须是四政策完整动态对照、同一固定边界带与必要内部覆盖、裁剪父区间与原可见长度的分母、各自墨跌落/合成遮盖/正确遮挡；不是只重播保存影片、重复cold replay或调参。该问题不同于本轮H1，也不借原U时序认证新S/D。若只剩重复展示而无独立可证伪问题，则收尾，不填充微小单元。遵守15:20/15:45/16:00。

H1本轮RUN且仅条件性；H2新政策本轮NOT_RUN，unit001的U/S/D/sham静态PARTIAL原样保留；第二物体、自动分割和Gaussian特有优势NOT_RUN/未证明。
'''
    coverage=f'\n有效共同像素观测为{common}/{source_pixels}（{common/source_pixels:.3%}），每方向对的屏外、标签和深度/孔洞拒绝分母见TEMPORAL.json。\n'
    (UNIT/'REPORT_ZH.md').write_text(intro+table+body+coverage)
    reproduce='''# Unit002 本机冻结输入复现

环境为现有只读Python，入口先限制CPU两核、数值线程1、CUDA为空。所有写入由runtime限制到unit_002；不调用旧输出生产脚本。以下从保存的原PLY/标签/配置重新生成B0并渲染两臂，逐数组比较指定科学帧。请使用一个尚不存在的output-name；已有目录会拒绝覆盖。

```bash
cd /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v09
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v09/h1/replay_h1.py --reference-key BUILD --output-name REPRO_BUILD_B
```

相同CLI已实际执行`--reference-key BUILD --output-name REPRO_BUILD_A`，回执logs/018_documented_replay.json，结果renders/REPRO_BUILD_A/REPLAY_CHECK.json。默认012也已实际冷重算，见logs/017_cold_replay.json和REPLAY_CHECK.json。

可用reference-key为BUILD、000至024及HIGH；对每个相机换一个新output-name即可独立冷复现。source/paper/S全部实际重算，两臂共享相机，B0重新生成，BUILD匹配因子从已冻结BUILD_MATCH.json读入而不再次拟合。此为本机依赖路径完整的复现，并非跨机器可移植包。

实际首次生产命令为`run_h1.py prepare`与`run_h1.py render --keys BUILD`，随后串行批次000–004、005–009、010–014、015–019、020–024加HIGH；原始完整argv、真实退出码和耗时均在logs/。prepare和科学输出目录不可覆盖重跑。初始BUILD的边缘种子失败与修复前协议位于failed_attempts，主结果采用PROTOCOL.json所记的修复后冻结规则。

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B -m unittest discover -s experiments/partwise_sketch_hatching_v09/h1 -p 'test*.py'
```

输入：inputs/assets/on、inputs/data/chair。固定配置：CONFIG.json、RAW_FIELD.npz、CAMERAS.json、BUILD_MATCH.json。科学源码锁：SOURCE_LOCK.json；最终完整代码副本：source/h1、source/h2，后续报告/复现代码锁另见HANDOFF_SOURCE_LOCK.json。所有B0二维路径、B1原三维路径、独立墨、结构、原GS采样事件和实际指标均保存；禁止把初始失败BUILD或unit001旧误标proxy图当主对照。

分析入口analyze_h1.py，展示/读回audit_h1.py；本次已实际执行，不需要再次运行以证明质量。科学结论与限制见REPORT_ZH.md。英文字段B0=per-view2D，B1=unchanged original U persistent3D；matched仅为BUILD预算匹配。
'''
    (UNIT/'REPRODUCE.md').write_text(reproduce)
    next_step=dict(action='continue',recommended_next_step='Read-only review then a bounded temporal H2 falsification on the already frozen unit001 U/S/D/sham paths, guide and BUILD factors over actual cameras. Reuse only verified same-camera source/paper/S from unit002; freshly rasterize policies. Measure whether static S margin benefit survives view change without increased own-ink loss or necessary-interior loss; distinguish planned trims, visibility and max-composite cancellation. No guide/angle/margin tuning, no replay-only unit.',why='Unit001 established genuine same-surface static H2 headroom; unit002 now supplies controlled actual camera/base evidence and shows own-ink versus coverage must be measured separately. S/D have not acquired temporal evidence from original U. This is independent of H1 and remains useful before15:20; require fresh read-only decision.')
    js(UNIT/'NEXT.json',next_step)
    status=dict(execution_state='completed',stage='conditional_H1_actual_27_camera_render_temporal_media_and_cold_replay_complete',
        scientific_verdict='PARTIAL: conditional temporal advantage for persistent3D on25-frame Chair arc versus reasonable deterministic projected-field2D. Unequal DEV coverage/ink and generator differences prevent pure-anchor or whole-object superiority; no Gaussian-specific gain.',
        gaussian_link_progress='All256690 original rows/order/fullSH/geometry retained,UNKNOWN170281 and seat S27873 rows unchanged. All27 science cameras cold originalGS render;25577 accepted events independently reconstruct RGB/S. Upper-back and structure remain proxy-only; no new path ownership or native CUDA parity.',
        H1='RUN; limited temporal subquestion only',H2='unit001 U/S/D/sham static PARTIAL preserved; no new H2 policy run in unit002',second_object='NOT_RUN',
        artifacts=['PROTOCOL.json','CONFIG.json','CAMERAS.json','BUILD_MATCH.json','TEMPORAL.json','SUMMARY_METRICS.json','READBACK.json','FINAL_READBACK.json','REPLAY_CHECK.json','REPORT_ZH.md','REPRODUCE.md','media/KEYFRAMES.png','media/WHOLE_LAYERS.png','media/natural_orbit.png','media/matched_orbit.png'],
        commands_tests=[str(p.relative_to(UNIT)) for p in sorted((UNIT/'logs').glob('*.json')) if '.start.' not in p.name],
        blockers=[],preserved_failures=['initial BUILD center-only2D baseline omitted boundary-intersecting strokes; retained and repaired beforeDEV','004 failed launch missing final receipt/UNKNOWN; child not started','011 actual script-path failure child rc2','B1 nonzero own-ink missing length','unequal DEV ink and coverage','old open curve/holes/high-rear zero/v08 dropouts143UNKNOWN/v07 negatives'],
        decision_sha256=sha(UNIT/'DECISION.json'),parent_verification='pending independent parent read',scientific_seal=False,completed_utc=runtime.now(),
        resources=dict(affinity=sorted(runtime.os.sched_getaffinity(0)),numerical_threads=1,CUDA_VISIBLE_DEVICES='',serial=True),next='continue')
    js(UNIT/'STATUS.json',status)
    print(json.dumps(dict(state=status['execution_state'],verdict=status['scientific_verdict'],common_fraction=common/source_pixels,next='continue')),flush=True)
if __name__=='__main__':main()
