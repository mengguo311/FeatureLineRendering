import runtime
from runtime import js,sha
from pathlib import Path
import json,statistics,datetime,shutil
import numpy as np
from linked_asset import npz
from structure_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_008';CODE=Path(__file__).parent

def main():
    verify_unit(UNIT);t=json.loads((UNIT/'TEMPORAL.json').read_text());a=json.loads((UNIT/'OUTPUT_AUDIT.json').read_text())
    v=json.loads((UNIT/'FINAL_VERIFICATION.json').read_text());plan=json.loads((UNIT/'delivery/TRAJECTORY.json').read_text())
    coverage=[]
    for i in range(61):
        f=npz(UNIT/'renders'/f'{i:03d}'/'on/FRAME.npz');obj=f['regions']>0;seat=f['regions']==4;back=f['regions']==5
        coverage.append(dict(index=i,object_pixels=int(obj.sum()),object_ink=float((f['combined_ink'][obj]>1/255).mean()),
            seat_ink=float((f['seat_linked_ink'][seat]>1/255).mean()) if seat.any() else None,
            upper_back_ink=float((f['layer_5'][back]>1/255).mean()) if back.any() else None))
    js(UNIT/'COVERAGE.json',coverage)
    ranges={k:[min(r[k] for r in coverage if r[k] is not None),max(r[k] for r in coverage if r[k] is not None)] for k in ('object_ink','seat_ink','upper_back_ink')}
    absolute=a['absolute_damage'];other=[r['on']['far_other']['raw_L1_sum'] for r in absolute];bg=[r['on']['far_background']['raw_L1_sum'] for r in absolute]
    frac=[r['on']['far_raw_fraction'] for r in absolute];times=a['per_camera_seconds']
    # Actual tool wrapper exits observed in this session; UNKNOWN remains explicit.
    observed={f'{i:03d}':(1 if i==1 else 143 if i==7 else 0) for i in range(19)}
    records=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        name=start.name.removesuffix('.start.json');end=UNIT/'logs'/(name+'.json')
        data=json.loads((end if end.exists() else start).read_text())
        records.append(dict(command=name,actual_tool_exit_code=observed.get(name[:3],'UNKNOWN'),
            wrapper_final_receipt_exists=end.exists(),child_returncode=data.get('child_returncode','UNKNOWN'),
            receipt=str((end if end.exists() else start).relative_to(UNIT)),started_utc=data['started_utc'],finished_utc=data.get('finished_utc','UNKNOWN')))
    js(UNIT/'EXECUTION_RECORDS.json',dict(commands=records,compiler_records=v['compile_records'],
        note='000..018 tool exits actually observed. Current/final packaging command owns its later raw receipt. Missing final child status stays UNKNOWN.'))
    status=dict(execution_state='completed',stage='current_saved_structure_asset_61_camera_pair_orbit_cold_reload_and_all_frame_decode_complete',
        scientific_verdict='PARTIAL usable finite whole-Chair browse. Three joint-visible own-structure ink dropouts and one reappearance; not flicker-free. Existing holes, flat frame and hatch crossings remain. No whole-object quality winner or Gaussian advantage.',
        gaussian_link_progress='Original256690 rows/order/geometry/opacity/fullSH and UNKNOWN170281 unchanged. All-row .95 render-time paper and original27873-row seat alpha*T S retained. Structure and upper-back proxy-only; no new-path source ownership certification.',
        artifacts=dict(package='delivery',animation='media/orbit.png',comparison='media/NATURAL_COMPARISON.png',layers='media/WHOLE_LAYERS.png',temporal='TEMPORAL.json',audit='OUTPUT_AUDIT.json',verification='FINAL_VERIFICATION.json'),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=3,saved_switch_and_nonzero_region5_edit_check_returncode=0),
        cameras=61,animation_frames=61,animation_duration_ms=5083,independent_camera_renders=61,cold_reload_additional_renders=1,
        camera_end_reset='Finite trajectory; APNG loops with an end-to-start playback cut, not a continuous360-degree orbit',
        keyframe_exact_arrays=192,cold_reload_exact_arrays=48,png_array_checks=1098,
        temporal={k:t[k] for k in ('observations','joint_visible_pairs','visible_observations','visible_without_own_ink','visible_own_ink_without_increment','occlusion_entries','occlusion_exits','event_counts')},
        coverage_ranges=ranges,frame_seconds=dict(min=min(times),median=statistics.median(times),max=max(times)),
        interruption=dict(tool_exit=143,wrapper_returncode='UNKNOWN',child_returncode='UNKNOWN',completed16_to26_verified=True,incomplete27_preserved=True,resumed_at27=True,cause='UNKNOWN'),
        actual_commands='EXECUTION_RECORDS.json and logs; original compile receipts authoritative',last_engine_exit_code='UNKNOWN',
        last_engine_note='Outer engine completion belongs to parent; never inferred from child rc0',blockers=[],scientific_seal=False,
        branch='partwise-sketch-hatching-gaussian-link-v08',report_utc=runtime.now(),next_action='stop',
        stop_reason='12:25 JST new-unit cutoff passed; finish delivery only. Not exhaustion or an aesthetic-gate stop.')
    js(UNIT/'STATUS.json',status)
    next_record=dict(action='stop',recommended_next_step='本次不再启动新科学单元；完成当前交付并在13:00前停止。若获得新的时间授权，可独立审查确认结构边界的排线停止/留白或有界新曲线来源支持，不能将本轮代理断续直接归因于Gaussian或用调容差掩盖。',why='已超过12:25禁止新单元截止；当前61帧资产交付完成，PARTIAL和旧失败保留。')
    js(UNIT/'NEXT.json',next_record)
    keyrows=[]
    for i in (0,15,30,42,44,48,60):
        p=t['per_frame'][i];row=plan['frames'][i]
        keyrows.append(f'| {i:03d} | {row["azimuth"]:g}/{row["elevation"]:g} | {p["visible"]}/64 | {p["increment_raw_L1"]:.6f} | {p["ink_mass_off"]:.3f}/{p["ink_mass_on"]:.3f} |')
    report=f'''# Unit008：当前Chair结构层资产的真实短轨迹

**工程输出完成；动态整物体应用可行性PARTIAL。** 已交付当前两区域长疏排线与开放内框资产的61帧真实相机输出，包含同帧结构OFF/ON和传统proxy。发现3次共同代理可见时的自身结构墨跌落、1次重现，不认证无闪烁，也不升级整物体画质或Gaussian优势。

[可播放APNG](media/orbit.png) · [完整自然对照](media/NATURAL_COMPARISON.png) · [分层](media/WHOLE_LAYERS.png) · [保存编辑与运行命令](delivery/README_ZH.md)

## 整图判断与应用进展

已目视检查全部61帧hybrid联系图、四关键帧source/OFF/ON/proxy及完整分层、弱后侧与侧面原尺寸图，以及全部六组事件相邻图。整椅、主要椅腿和扶手开口在轨迹中仍可辨；后侧内框能随物体转动，转向前侧后隐藏。可作为有限视角的粗略可浏览资产。

限制很明确：排线仍穿过内框上缘，左侧返回段仍开放，框架体积偏平；背部下缘两个小孔与座背留白保持。接近侧面时背框、轮廓和排线挤成暗窄带，独立结构层逐渐碎裂并隐藏。传统proxy表达同样主要形体；GS混合主要提供淡灰纸底与座面S衰减，未建立画质优势。旧241/60高后侧零增量与孔洞不在本轮24–36度轨迹内，不能称被覆盖或修复。

本轮只增加当前保存资产的动态证据。unit003旧61帧半周/21帧缩放属于另一份密线资产，不能迁移其结果；unit007静态内框改善也不能自动推成时序通过。全帧解码和联系图检查已做，没有独立真人实时播放器或感知偏好实验。

## 冻结轨迹与表示

父级DECISION未修改；评价前冻结输入、源码、61相机及64个曲线弧长中点。384×384、距离5.1、12fps；关键帧0=241/24、15=196/36、30=151/36、60=61/24，间隔内方位和仰角线性插值。APNG总长5083ms，循环末尾回起点是播放重置，不是连续360度闭环。没有图像插帧、逐帧重新选择墨或修线。四关键帧已曝光，其他元数据预先固定，不称GS训练未见。

61个不同相机都实际重算原GS、纸底、S、代理墨和结构层；每帧同一次计算在AA2层合成OFF/ON两个状态，不重复计算两套相同GS。批次内复用已加载原PLY和编译CPU库，非每帧全新进程，也非缓存旧GS图伪造视角。四关键帧两状态共192数组精确恢复unit007。

新入口明确保持active_regions=[4,5]；旧运动入口默认显示全部区域且没有结构层，未直接运行。全部五区路径文件、178条启用路径、169段curve_id=240807000001及face/bary逐字节保持。原256690行、行序、位置/协方差/opacity/完整SH、原代理与作者标签、UNKNOWN170281、27873行座面责任、1px/AA2/.004深度容差不变。全局.95纸底是渲染时颜色覆盖，不是部件标注。结构不套座面S或region5限制；上背和结构仍为代理表示，无逐路径原核或物理所有权证书。

## 自身覆盖与正确隐藏分开

64个固定样本按保存线段弧长取中点，不跨缺口。连续代理首交不加区域门，另从该曲线自身实际AA结构墨做双线性读取；不借其他排线或轮廓。最终ON−OFF自然RGB增量另外记录。1/255仅是冻结描述阈值。

| 观测 | 数量 |
| --- | ---: |
| 样本—帧观测 / 代理可见 | 3904 / 2900 |
| 相邻帧共同代理可见样本对 | 2836 |
| 自身墨跌落 / 重现 | 3 / 1 |
| 可见却无自身墨的观测 | 4 |
| 自身墨存在但合成增量不足的观测 | 43 |
| 自身墨仍在时合成增量跌落事件 | 37 |
| 进入 / 退出代理深度拒绝 | 64 / 2 |

具体自身跌落：41→42样本8为0.136649→0；42→43样本11为0.207925→0；43→44样本7为0.212837→0。1→2样本38从0→0.213371重现。样本11此前合成增量已经为0，说明只看最终差分会漏掉自身墨问题。37次合成增量跌落不等于37次曲线丢失，max并集中的遮盖与自身覆盖必须区别。深度拒绝中的正常隐藏也不计成共同可见跌落。

这些是同一代理上一个作者曲线的采样观察，不是64条独立曲线或3904个独立物体样本。有限像素覆盖、邻域遮挡与连续首交参照可有差异，本轮没有隔离唯一物理原因；不放宽容差或改变曲线来隐藏反证。

| 帧 | 方位/仰角 | 可见样本 | OFF→ON raw L1增量 | 总墨量OFF/ON |
| --- | --- | ---: | ---: | ---: |
{chr(10).join(keyrows)}

ON/OFF增加内容与墨预算不同，仅测试系统能力，不作等预算机制胜负。全轨迹整物体墨覆盖{ranges['object_ink'][0]:.2%}–{ranges['object_ink'][1]:.2%}，座面自身post-S覆盖{ranges['seat_ink'][0]:.2%}–{ranges['seat_ink'][1]:.2%}，上背自身墨覆盖{ranges['upper_back_ink'][0]:.2%}–{ranges['upper_back_ink'][1]:.2%}。覆盖按固定作者标签，只作诊断；侧面区域投影变化不能直接变成质量排名。

相对原彩色GS，ON的远其他部位raw L1范围{min(other):.3f}–{max(other):.3f}，远背景{min(bg):.3f}–{max(bg):.3f}，远区占总变化{min(frac):.2%}–{max(frac):.2%}。口径沿用历史座面region4及2px带，包含全局纸底和有意的整椅墨，不能当背框独立意图掩码或局部泄漏通过。ON/OFF的变化确实限于实际结构墨像素，但这只是自身支持读回，不是独立语义零泄漏认证。

## 验证与中断

实际TDD RED rc1为缺新motion模块；3项GREEN rc0覆盖关键轨迹、隐藏区域与AA合成，以及缺口不桥接/异标签前景首交/不借其他墨。包内toggle新进程保存OFF；包内新运动入口从保存OFF冷重算同帧两状态，48数组和全部观测精确相同。另真实执行+1度region5功能编辑，结构与所有非目标文件不变；没有将其渲染为额外科学候选。原ID查询保留UNKNOWN及原区域证据。

1098张科学层图逐像素对应数组，61帧APNG全部解码逐值等于对应整图。51185条稀疏原接受事件独立核对T链、alpha与S；T误差0，alpha/S最大误差{a['source_alpha_max_error']:.3g}/{a['source_S_max_error']:.3g}。这是CPU采样连接证据，不是全图逐核或新曲线来源认证。单相机计算耗时{min(times):.3f}–{max(times):.3f}秒，中位{statistics.median(times):.3f}秒，12fps仅是播放速度。

007_orbit_16_30工具外层退出143，wrapper/child返回码UNKNOWN，原因UNKNOWN，原最终回执缺失。16–26完整payload核验后保留，027仅scratch的未完成目录移到failed_attempts保留；确认已知wrapper及匹配本任务renderer均不存在后，从27续跑同一冻结轨迹。未重画已验证帧，没有补造007成功。后续缩短批次并严格等待完成；未调用额外时限扩展。所有原始start/log/最终回执及编译子退出码保留。外层engine码仍由父级记录，本单元为UNKNOWN。

仅本机Linux CPU、两核亲和、单数值线程、串行；无GPU/训练/安装/下载/嵌套模型/旧目录改写/push/merge。仅本地SHA和全帧解码核验，无远端或跨平台认证。父级DECISION和科学源码保持，事后读回/报告代码另锁。

v05 far8.044%/31腐蚀像素/4.49%原区域变化失败、v07十一轮整物体负结果/H交叉角塌缩/zero_step_cycle、v08旧143/UNKNOWN与共同可见墨跌落、unit004空集合/077弱后侧近消失，以及unit007串行调度偏差与恢复均原样保留。本轮有限动态资产不能倒推旧任务通过。

## 收尾

NEXT=stop，因为12:25禁止新单元截止已过；完成本轮和总交付，不再启动科学单元。不是由于局部美学门槛或路线穷尽。当前结构层/两区域编辑资产和影片可用作粗略示范，科学结论保持PARTIAL。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    historical=UNIT/'previous_root_summary';historical.mkdir()
    for name in ('DEMO_README_ZH.md','DELIVERY_STATUS.json'):
        if (runtime.ROOT/name).exists():shutil.copy2(runtime.ROOT/name,historical/name)
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_008',units=[f'unit_{i:03d}' for i in range(1,9)],status=status,
        current_package='units/unit_008/delivery',source_evidence_package='units/unit_005/delivery',historical_path_query_package='units/unit_004/delivery',
        root_snapshot_scope='Current asset package plus earlier separately scoped source-control evidence; no transfer of old path certificates.',next=next_record))
    (runtime.ROOT/'DEMO_README_ZH.md').write_text('''# v08：可编辑Chair资产与真实相机输出

当前交付为PARTIAL的粗略整椅示范，没有整物体画质赢家或Gaussian优势。两个作者区域可保存angle/spacing/length编辑，开放内框可独立开关，现有61帧真实相机影片展示结构OFF/ON和传统proxy。

[运行资产与命令](units/unit_008/delivery/README_ZH.md) · [真实影片](units/unit_008/media/orbit.png) · [自然整图](units/unit_008/media/NATURAL_COMPARISON.png) · [完整报告](units/unit_008/REPORT_ZH.md) · [状态](DELIVERY_STATUS.json)

影片有3次共同代理可见时的自身结构墨跌落和1次重现；跨框排线、开放左侧、平框架和旧孔洞仍在，不认证无闪烁。61帧是有限半周轨迹，循环重置不是连续360度；当前没有新的缩放影片。旧unit003影片属于旧资产。

原256690行与完整SH/geometry/opacity/顺序固定；全局纸底是原核求值颜色覆盖，座面S是原行alpha*T区域责任。上背和结构仍代理支持，不是原生Gaussian排线、语义分部或逐路径所有权。

[unit005原GS区域颜色控制](units/unit_005/delivery/README_ZH.md)是独立、可保存的原行编辑证据；[unit004稀疏路径查询](units/unit_004/delivery/README_ZH.md)只属于其旧路径资产，空集合及弱后侧近消失保留，不迁移到当前178条新路径。unit007结构作者记录、旧高后侧零增量，以及v05/v07全部负结果保持。

12:25禁止新科学单元截止已过，NEXT=stop仅为截止收尾。原143/UNKNOWN及unit007串行偏差没有改写。当前仅本机Linux CPU核验，依赖与准确重放范围见包内说明。
''')
    doc=CODE.parents[2]/'docs/partwise_sketch_hatching_v08/unit008_structure_motion.md';doc.parent.mkdir(parents=True,exist_ok=True)
    doc.write_text(report)
    print(json.dumps(dict(coverage_ranges=ranges,far_other=[min(other),max(other)],far_background=[min(bg),max(bg)],far_fraction=[min(frac),max(frac)],frame_seconds=status['frame_seconds'])),flush=True)
if __name__=='__main__':main()
