"""Write a negative/limited scientific handoff from actual saved results."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js,now
import json,time

def load(p):return json.loads(p.read_text())
def main():
    audit=load(UNIT/'AUDIT.json');assert audit['status']=='pass'
    replay=load(UNIT/'cached_carrier_replay/REPLAY_RECEIPT.json');assert replay['all_equal']
    stats=load(UNIT/'asset/ASSET.json');match=load(UNIT/'BUILD_MATCH.json');summary=load(UNIT/'SUMMARY.json')
    far=load(UNIT/'FAR_READBACK.json');visible=load(UNIT/'VISIBLE_INTERVENTION.json');attr=load(UNIT/'attribution/SUMMARY.json')
    receipts={p.stem:load(p) for p in (UNIT/'logs').glob('*.json')}
    failures={k:v for k,v in receipts.items() if v['child_returncode']!=0}
    assert set(failures)=={'carrier_RED','carrier_GREEN_001','audit'}
    verdict='载体干预有效且路径可见变化，但完整物体可读性收益未建立；不升级默认。'
    inspected=['ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','dev/orbit_241_24_5.3/COMPARISON.png',
        'dev/orbit_241_24_5.3/INK_LAYERS.png','dev/orbit_61_24_5.3/INK_LAYERS.png']
    js(UNIT/'VISUAL_INSPECTION.json',dict(utc=now(),inspected=inspected,verdict=verdict,
       observations='前侧局部路径略有位置/弯折改变，完整物体A/C非常接近；后侧短交叉网格及纸底斑驳仍在。自然和配平、pre-S和linked、同预算ungated均未显示明确整体优势。三帧不是连续视频或时序稳定性认证。',independent_user_study=False))
    next_step='下一次只读审查及父级冻结后，转向原始未降噪载体上的全局相干无向切向场与场引导积分。固定unit001种子、逐笔触长度预算、两层原风格/基底、目标、GS纸底/S和可见性，比较同一个表面行走器使用未平滑的固定引导场与共享边传输后相干化的场；保存原A及unit001直线展开B作参照。方向只能由固定三维几何/既有引导形成，不按相机拟合、不搜角度。若初始切向也改变须明确披露，不能把方向估计与路径积分合并的结果说成单因素改进；优先固定简单引导而不声称自动估计新颖。继续同BUILD墨预算、自然强度、pre-S/linked/ungated和完整前后视图。不得叠加C、放宽遮挡或扫描降噪强度。'
    why='本轮441个顶点和1349个目标面确有变化，完整DEV约67%–74%的目标首交像素落在受影响面上，但两前后方向仍无整物体收益。C是一次保守载体诊断，不排除更大尺度噪声；unit001仅验证逐笔触straightest续接，尚未建立全局相干方向场，因此原载体上的场引导生成仍是独立路线。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,estimated_minutes=30,
       requires_next_read_only_review=True,no_new_units_after_jst='2026-10-25T14:25:00+09:00'))
    rows=[];farrows=[];visrows=[];attrrows=[]
    for r in summary:
        if r['kind']!='dev':continue
        a,c=r['A_linked'],r['C_linked'];f=next(x for x in far if x['view']==r['view'])
        rows.append(f"| {r['view']} | {r['target_pixels']} | {a['ink_L1']:.3f}/{c['ink_L1']:.3f} | {100*a['coverage']:.2f}%/{100*c['coverage']:.2f}% | {100*a['interior_coverage']:.2f}%/{100*c['interior_coverage']:.2f}% | {100*f['target_changed_fraction_005']:.2f}% |")
        farrows.append(f"| {r['view']} | {a['far_other']:.9f}/{c['far_other']:.9f} | {a['background']:.9f}/{c['background']:.9f} | {r['C_ungated']['far_other']:.9f} |")
    for x in visible:
        if x['view'] not in [r['view'] for r in summary if r['kind']=='dev']:continue
        a=x['A_fragments'];c=x['C_fragments']
        visrows.append(f"| {x['view']} | {x['changed_carrier_target_pixels']}/{x['target_pixels']} | {sum(y[0] for y in a)}/{sum(y[0] for y in c)} | {sum(y[1] for y in a)}/{sum(y[1] for y in c)} | {sum(y[3] for y in a)}/{sum(y[3] for y in c)} |")
    for x in attr:
        attrrows.append(f"| {x['view']} {x['arm']} | {x['proxy_visible_length']:.3f} | {x['preS_own_visible_missing_length']:.3f} | {x['linked_matched_own_visible_missing_length']:.3f} | {x['proxy_visible_length']-x['linked_matched_own_visible_missing_length']:.3f} |")
    old=stats['partitions']['old'];added=stats['partitions']['added']
    la=old['A']['length']+added['A']['length'];lc=old['C']['length']+added['C']['length']
    elapsed=(time.time()-min(r['started_unix'] for r in receipts.values()))/60
    report=f'''# Unit002：有界载体降噪真实改变路径，整物体优势未建立

**A/C实际实验完成。{verdict} NEXT=continue，scientific_seal=false，父级验证待完成。**

已直接检查四个完整DEV的自然/配平面板、前后独立墨层、弱后视角linked/ungated对照及231°/241°/251°实际相机序列。前侧少数线段略顺或移位，完整铲斗总体仍像短交叉网格，后侧黄灰纸底与碎乱笔触仍限制形体表达。A/C完整图非常接近，没有足够视觉证据称C更清楚。这是有限目视检查，不是用户偏好研究。

## 单一干预与几何效果

A是unit001保存的A，即unit010局部基底切片路径。原始载体、原生成器及保存FRAME基底重生成后，所有路径字段逐值恢复A；没有退回包内默认XZ或重新估计PCA。C只改变新的载体顶点副本，保留完整16543顶点/29999面拓扑和标签，再以同一生成器产生独立新stroke身份与face/bary锚点。新ID偏移200000000000不表示原Gaussian归属。

冻结方案：一遍共享边一环双边法线滤波，空间尺度为面内边长中位数，法线角尺度30°；无向法线先对齐符号。三次同时顶点回代，松弛0.5；累计位移不超过min(局部初始边长中位数×0.1,0.002世界单位)。非目标、网格/非流形边界、旧/新增分区边界、初始无向二面角超过60°的边端点和退化面顶点固定。未填孔、未跨空间邻近片连接、未改GS、未作参数搜索。锐边识别只是几何启发式，非语义真值。

1327个目标相关顶点中441个可移动且实际移动，653个接触保护边界，425个接触锐边；后两者可重叠。1349个目标面受影响，翻面拒绝顶点0。移动顶点位移中位数0.001003，最大0.002；目标面法线变化中位数1.007°、P95 5.913°、最大18.625°。同分区共享边无向夹角中位数20.003°→16.890°，P95 74.107°→74.672°；高分位并未改善，真实棱边和噪声仍混在一起。不能宣称恢复真实表面或解决大尺度几何缺陷。

A为380条/1946段，C为376条/1937段；世界总长度{la:.9f}→{lc:.9f}（减少{100*(1-lc/la):.3f}%）。两臂存储内部断点均0。旧主分区跨面转角中位数18.817°→16.262°，新增分区9.534°→8.533°。这些是几何效应，不是NPR成功标准。

## 保持项和可见性解耦

原310475行Gaussian身份/行序、PLY、中心、协方差、opacity、完整SH均不改。41058行纸底许可及权重、21006行墨责任及权重、195279 UNKNOWN与M1、2121面作者目标、旧2030/新增91面分别停止、两层35°/95°、spacing0.06/0.075、length0.12、gap0.035、原点/相位/基底手性、线宽1px、2倍采样、0.004绝对深度容差、2px评价带全部固定。

渲染器适配只把原来的一个mesh参数拆成载体与遮挡参照：笔触所在面平面使用各臂载体，首交深度和区域位图始终使用原始完整代理。相同载体输入恢复旧A全部输出；没有用新载体替换遮挡参照，也没有用旧面平面计算新路径深度。原source/paper/S和相机复用锁定缓存，A/C墨层在每个不同视角实际重新栅格化。unit001的一次完整冷重放已成功，本轮没有重复bootstrap或安装依赖。

| DEV相机 | 受影响面首交目标像素/全目标 | 候选片段 A/C | 接受片段 A/C | 深度拒绝 A/C |
|---|---:|---:|---:|---:|
{chr(10).join(visrows)}

受影响面覆盖约67%–74%的完整目标可见像素，故不是仅不可见位置的no-op；但总位移有意保守，不能用此负结果排除所有载体噪声。片段计数含跨笔触重叠，不等于可见像素或物理遮挡真值。

## 实际墨预算和完整DEV

四BUILD自然墨RGB L1：{json.dumps(match['natural_totals'])}。公共预算{match['budget']:.6f}，固定全局系数{json.dumps(match['scales'])}。实际合成读回与预算一致到浮点误差，DEV未重新拟合；自然强度全部保留。A的配平强度本轮略减，不能与unit001的配平图直接当相同基准，A自然图逐值相同。

| DEV相机 | 目标像素 | 目标墨RGB L1 A/C | 目标覆盖 A/C | 内部覆盖 A/C | 明显图像差比例 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

可见墨alpha>0.05及图像差L1≥0.05仅为描述口径，不是新增通过门槛。三个DEV全目标覆盖下降，弱241°/24°持平；内部覆盖一增、一平、两降。变化覆盖约5.0%–7.4%的目标像素，幅度有限。不能把减少笔触或略少覆盖解释成更干净。

## 断裂、深度与S归因

下表按每条stroke自己的墨层采样，不借重叠笔触获得支持。长度是投影像素；可见性参考仍是固定原代理，非独立真实表面。

| 相机/臂 | 参考可见长度 | pre-S自身缺失 | linked配平自身缺失 | linked有支持长度 |
|---|---:|---:|---:|---:|
{chr(10).join(attrrows)}

前侧pre-S缺失26.720→18.969px、后侧23.893→21.124px；linked缺失也减少。但参考可见长度同时960.800→920.983、853.649→842.870px，不能只比较缩小后的缺失分子。linked有支持长度前侧858.679→829.275px、后侧726.061→722.476px，未形成总体连续支持增长。中心线深度拒绝前侧1254.323→1277.786px、后侧1494.091→1497.961px，含原有背面/真实遮挡及干预引入的偏离；不是全部错误裁剪。首交区域拒绝、每笔触样本和完整光栅片段计数均保存，未放宽深度判据。

pre-S本身仍是交叉网格，S另使部分线淡化。相同BUILD墨预算ungated弱后视角目标覆盖A40.57%、C40.54%，更多覆盖也未带来清楚整物体优势。区域S保留为可选连接机制，不宣称有新NPR质量贡献；原GS纸底和原行选择能力独立保留。

## 绝对远区影响与解释边界

| DEV相机 | 远其他部件源差L1 A/C linked | 背景源差L1 A/C linked | C ungated远其他源差L1 |
|---|---:|---:|---:|
{chr(10).join(farrows)}

原纸底既有损伤包含在表内。六个不同评估相机中，两臂配平linked远区差最大单像素L1={max(x['far_max_pixel_L1'] for x in far):.12g}，超过1/255的远区像素合计{sum(x['far_pixels_above_1_255'] for x in far)}；不称严格零，也不借较小远区比例宣称局部性进步。没有扩大评价带或目标。

四DEV与三个后侧arc有六个不同评估相机，241°/24°为明确复用的重复项，全部已曝光。三帧相机序列不是连续视频、无闪烁认证或新独立测试集。新载体附着仅是代理自洽，不是物理/语义真值。这里的Lego是实际冻结GS重建资产，不是本轮新采集真实世界数据。

## 测试、失败保留与复放

针对性TDD先缺carrier模块RED rc1，再完成三组测试：已知噪声平面/曲面、平面恒等/锐折/孔洞/分离片/分区、原光栅等价/独立载体深度/同标签真实前景/零S。首个GREEN尝试因夹具错误要求前景外整列也被遮挡而失败，改为真正前景中央足迹后GREEN；渲染器和参数未因此修改。记录见FIXTURE_FAILURE.json及原日志。

另保留两次初始化错误：系统没有python命令(rc127)，随后日志入口尚不存在(rc2)；切换到既定绝对解释器解决，未安装。首次审计因float32的RGB总体求和与先逐像素L1再求和次序不同而rc1；原审计源码在interrupted_audit_001。修订读回口径后audit_002通过，没有改数值阈值、科学协议或结果。

独立审计核对375个冻结输入（含unit001保存文件）、原行完整身份、拓扑/边界/翻面、每条新路径的face/bary及原切片层位，最大锚点误差{audit['max_anchor_error']:.3g}、层位误差{audit['max_slice_level_error']:.3g}；112张输出PNG完整解码与数组一致，A所有实际渲染逐值恢复旧结果。新进程从保存资产再次实际栅格化弱后视角A/C，全部{replay['arrays']}数组逐值一致。该复放复用固定GS层，不冒称cold GS或独立便携包。

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/carrier_unit/replay_carrier.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_002/user_replay_001 --view orbit_241_24_5.3
```

输出目录须不存在且在unit002内。运行入口固定两核亲和、数值线程1、CUDA为空；沿用现有NumPy2.2.6/SciPy1.15.3/Open3D0.20.0环境，无新包/GPU/训练/网络下载/嵌套模型。新代码全部在授权v07工作树，重数据全部在HDD，旧包/环境/原PLY和DECISION未改。

v05稀疏任务far8.044%、31像素腐蚀区域及4.49%作者区域变化失败，v06各负结果、unit001续接负结果和全部工程失败保持。输出仍是原GS纸底加原ID区域责任门控代理墨，非原生Gaussian排线或逐路径Gaussian认证；不宣称H1/H2/H3成立。

## 下一步

{next_step}

{why}

本单元执行约{elapsed:.2f}分钟，早于35分钟上限。本次只完成unit002；下一科学单元仍需父级只读审查/冻结。14:25禁启新单元，14:45科学收尾，15:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    js(UNIT/'EXECUTION_RECORDS.json',receipts)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={p.name:sha(p) for p in HERE.iterdir() if p.name in ('audit_carrier.py','replay_carrier.py','finish_carrier.py')}))
    js(UNIT/'STATUS.json',dict(execution_state='completed',stage='actual_AC_complete_audited_and_visually_inspected',scientific_verdict=verdict,
       scientific_seal=False,parent_verification='pending',default_promoted=False,
       gaussian_link_progress='Original310475 rows/paper41058/ink21006/M1/UNKNOWN fixed; cached original-GS source/paper/S plus actual C ink. Region linkage only, no new per-path ownership certification.',
       actual_commands=receipts,tests=dict(expected_red='carrier_RED',failed_fixture='carrier_GREEN_001',green='carrier_GREEN_002',audit_failed='audit',audit_pass='audit_002'),
       engineering_failures=['SETUP_FAILURES.json','FIXTURE_FAILURE.json','interrupted_audit_001/EXPLANATION.json'],
       artifacts=['asset/ASSET.json','ALL_DEV_MATCHED.png','ALL_DEV_NATURAL.png','REAR_CAMERA_SEQUENCE.png','attribution/SUMMARY.json','FAR_READBACK.json','VISIBLE_INTERVENTION.json','AUDIT.json','cached_carrier_replay/REPLAY_RECEIPT.json','REPORT_ZH.md','NEXT.json'],
       blockers=[],elapsed_minutes=elapsed,scope='One bounded carrier diagnostic; no whole-object improvement established; useful independent field-generator route remains'))
    print(json.dumps(dict(execution_state='completed',scientific_verdict=verdict,next='continue',elapsed_minutes=elapsed)),flush=True)
if __name__=='__main__':main()
