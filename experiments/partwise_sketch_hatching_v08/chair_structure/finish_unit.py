import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,datetime
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
START='2026-10-27T02:47:49.189115+00:00'
NEXT='下一次只读审查后，优先为当前保存的结构层资产制作一条有界的真实短相机轨迹，覆盖可见背框、弱后侧及转入隐藏的过渡，并展示同帧结构层开/关。冻结世界曲线、全部排线和相机元数据；复用成熟运动入口，逐帧真实相机渲染与全帧解码，不逐帧修线、不补闭合、不改变遮挡容差。重点区分合理隐藏与共同可见曲线的异常断续。unit003旧资产影片不能认证新曲线；已有排线跨框及孔洞作为可见限制保留。须先审查当时剩余时间，将执行限定在12:45前完成；不扩成全周认证或新的参数扫描。'
def main():
    a=json.loads((UNIT/'OUTPUT_AUDIT.json').read_text());v=json.loads((UNIT/'FINAL_VERIFICATION.json').read_text());author=json.loads((UNIT/'AUTHOR.json').read_text())
    projection=json.loads((UNIT/'delivery/assets/on/PROJECTION.json').read_text());recovery=json.loads((UNIT/'SCHEDULING_RECOVERY.json').read_text())
    rows=[];far=[]
    for view,r in a['views'].items():
        rows.append(f"| {view} | {r['structure_pixels']} | {r['incremental_raw_L1']:.6f} | {r['original_ink_mass']:.3f} / {r['new_ink_mass']:.3f} | {r['structure']['segments_with_visible_ink']} / 169 |")
        f=r['absolute_source_change']['on'];far.append(f"| {view} | {f['far_other']['raw_L1_sum']:.3f} | {f['far_background']['raw_L1_sum']:.3f} | {100*f['far_raw_fraction']:.2f}% |")
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(START)).total_seconds()/60
    report='''# Unit007：可保存、可开关的靠背内框结构曲线

**资产交付完成；科学结论PARTIAL。** 固定内框在三个背侧相机可见，给背板增加了明确的内边界；没有建立整物体质量赢家或Gaussian优势。执行中发生一次2.562698秒命令重叠，违反串行协议；原记录保留，受影响的两个结果随后在冻结条件下串行冷重渲染，24数组逐值相同。不能把恢复结果改写为全程串行合规。

[自然完整对照](media/NATURAL_COMPARISON.png) · [完整分层](media/WHOLE_LAYERS.png) · [运行资产与命令](delivery/README_ZH.md) · [作者标记，仅为诊断](AUTHOR_PREVIEW.png)

## 真实整图判断

已查看全部五相机自然整图、source/paper/原contour/独立structure/combined ink/hybrid分层、同曲线传统proxy，以及BUILD、弱后侧、新增后侧和高后侧原尺寸图。151/36和新增196/36能看出内框上缘、右缘与下缘，后者与源GS面板边界的总体走向一致；弱241/24也出现可见内框。新增曲线在前61/24完全隐藏。高241/60仅1个原生像素有结构墨、被原轮廓覆盖后合成增量为0，不能将这一视角称为有效编辑或孔洞修复。

代价与缺陷保留：左侧不清楚的回接没有画，故不是完整闭合框；原region5排线继续跨越新增上内框，尚无结构线—排线关联；弱后侧独立结构层存在可见细碎断续。框架仍偏平，背下缘与高后侧旧孔洞、座背空白未修复。传统proxy带同一曲线也表达主要形体，GS混合仍主要提供淡灰纸底和座面S衰减。当前支持作者结构层的有限应用可行性，不支持整椅赢家、物理贴合或时序稳定性认证。五张静态视图不是新视频。

## 作者成本、附着与保持项

151°/36°/5.1为已曝光原GS作者BUILD；24个控制点一次固定，0次坐标修订，未使用评价图修线。坐标起草耗时{coordinate_seconds:.3f}秒，含原图预览确认的总作者区间为{author_seconds:.3f}秒；这是实际时间记录，不将整轮工程时间冒称作者成本。未增加用户点击、面标签或新方向引导。描绘可见上/右/下内框，不描花纹或小孔；左侧回接不清楚，明确省略。SOURCE图是冻结vanilla-GS输出，不是独立真值。

一条开放折线按投影三角形覆盖及逆深度前后次序精确分段，透视校正face/bary生成169段，世界长度2.318319842811（NeRF场景单位）。请求的230.252916像素作者线段全部有代理首交支持，内部未支持长度0、世界跳变0；这不包含主动未画的左侧回接，也不是整框覆盖100%。独立Open3D检查169个段中点的首交面全部相同，最大深度差1.00904e-6。锚点数不是独立样本，代理自洽不等于真实表面正确。

curve_id=240807000001，固定1px、强度.85、墨色.03、AA2和.004深度容差；在原AA子像素层与原墨作max并集，再降采样。结构层单独保存、独立开关、使用真实首交遮挡，不套座面S，也不强制限制到region5。曲线实际跨越原作者region2/3/5，这是原高度区与手工区域不等于语义内框的结果，没有改标签。

原256690行及行序、位置/协方差/opacity/完整SH、原PLY、代理网格、粗作者标签、UNKNOWN170281与27873行座面责任保持。五个区域路径文件逐字节不变，两个启用区域178条排线路径不重生成；全局.95原核颜色覆盖、原轮廓和排线参数保持。新增结构曲线是代理细节，不具原Gaussian来源/所有权证书，unit004证据不迁移。全局纸底不是局部控制或标签传播。

## 可见效果与墨预算

| 相机 | 结构像素 | 开关增量raw L1 | 总墨量 OFF / ON | 有墨线段 |
| --- | ---: | ---: | ---: | ---: |
{rows}

新增内容和墨量是明确的SYSTEM/STYLE改变，没有做等预算因果胜负主张。前侧的零增量与代理遮挡一致，高后侧零增量只说明该视角没有可观察的开关效果；不能用零变化证明局部控制成功。169段的可见数含不同长度线段，不是可见弧长或物理支持比例。每个视角的变化均位于本次实际结构层像素内，座面与背景增量为0；该自生成支持范围不是独立意图掩码，不能据此声称独立零泄漏认证。

下表为ON相对原彩色GS的绝对远区变化，沿用历史座面region4及固定2px带，仅供对照，不能当本次背框的意图掩码或泄漏门槛。

| 相机 | 远其他raw L1 | 远背景raw L1 | 远区占总变化 |
| --- | ---: | ---: | ---: |
{far}

这些大变化包含固定全局纸底与整椅墨，背框也位于座面远区；不以开关差分抵消来掩盖。完整各作者区域的开关增量另见OUTPUT_AUDIT，region2/3/5的非零增量是已声明曲线范围，不冒称仅region5局部编辑。

## 验证与实际执行

评价前冻结父级DECISION引用、PROTOCOL、输入、源码、作者配置、五相机及生成资产。151/36为作者BUILD；61/24、241/24、241/60均已曝光；196/36为本轮新输出预留，未称GS训练未见。科学十次渲染均从原PLY重算GS/S/代理墨；没有用旧图冒充新结果。

预期RED rc1为缺structure模块；随后3项几何/遮挡/开关测试及3组真实保存资产测试GREEN rc0，覆盖逐面分割、缺口不桥接、分离前景遮挡、首交投射、AA并集、保存恢复、非法开关拒绝及非零region5编辑保留结构与非目标路径。功能测试中的1°编辑不是额外科学候选，没有渲染或选择它。

四个旧相机的OFF全部19数组精确恢复unit006，包含原contour、纸底、S、标签、深度与完整proxy。包内CLI在新进程真实保存OFF状态，与交付OFF路径/配置相同；包内ON弱后侧冷重渲染24数组逐值一致。独立审计重建原行alpha*T的采样S并核对全部13次新渲染（10科学、2串行恢复、1包内冷重载）的169张PNG与数组，以及26个编译命令真实rc0。SOURCE_LOCK及父级DECISION未修改；事后检查/报告代码另列HANDOFF_SOURCE_LOCK。

调度偏差：010_high_rear_on与011_reserved_off在02:59:53.645066–02:59:56.207764 UTC重叠2.562698秒，原child rc均0。原因是root未等前一exec会话完成就启动下一对；两者保留相同两核亲和和各1数值线程，但串行要求仍被违反。012/013随后严格串行，从原PLY冷重算相同冻结输入，各24数组完全恢复。SCHEDULING_DEVIATION、SCHEDULING_RECOVERY及所有原始日志并列保留，不能补造无偏差历史。外层engine返回码由父级记录，本单元保持UNKNOWN。

无GPU、安装、下载、训练、嵌套模型、旧目录改写或push/merge。本机LinuxCPU与本地SHA/全PNG解码核验；没有远程或跨平台认证。上述调度偏差是本轮资源协议的明确例外，不能称全程串行。

v05 far8.044%/31腐蚀像素/4.49%原区域变化失败、v07十一轮整物体负结果/H交叉角塌缩/zero_step_cycle、v08原143/UNKNOWN、共同可见墨跌落、unit004空集合与077弱后侧近消失均保留。当前曲线任务不倒推旧任务通过。

## 后续

NEXT=continue。{next_step}

生成报告时距授权约{elapsed:.2f}分钟；本轮未启动下一科学单元。
'''.format(coordinate_seconds=author['coordinate_authoring_seconds'],author_seconds=author['authoring_total_seconds'],rows='\n'.join(rows),far='\n'.join(far),next_step=NEXT,elapsed=elapsed)
    (UNIT/'REPORT_ZH.md').write_text(report)
    status=dict(execution_state='completed',stage='saved_structural_curve_five_camera_outputs_cold_reload_complete_with_recorded_scheduling_deviation',
        scientific_verdict='PARTIAL authored structural-layer capability: inner rim readable in three rear views, absent in front, no composite change at high rear. Hatch crossings, open left return, flat frame and inherited holes remain. No whole-object or Gaussian quality winner.',
        gaussian_link_progress='Original256690 rows/order/geometry/opacity/fullSH and UNKNOWN170281 unchanged; all-row .95 render-time paper and original27873-row seat alpha*T S preserved. New structural curve is proxy-only and has no per-path source ownership certificate.',
        artifacts=dict(package='delivery',comparison='media/NATURAL_COMPARISON.png',layers='media/WHOLE_LAYERS.png',author='AUTHOR.json',audit='OUTPUT_AUDIT.json',verification='FINAL_VERIFICATION.json'),
        tests=dict(expected_RED_returncode=1,geometry_GREEN_returncode=0,geometry_tests=3,saved_asset_GREEN_returncode=0,saved_asset_groups=3),
        curve=projection,authoring=author,original_path_files_unchanged=True,off_recovers_unit006_arrays_per_view=19,
        cold_reload=dict(arrays=24,exact=True),new_scientific_renders=10,additional_serial_recovery_renders=2,additional_cold_reload_renders=1,
        new_video=False,unique_cameras=5,new_reserved_camera='orbit_196_36_5.1',png_array_checks=v['png_array_checks'],
        protocol_compliance='partial: one retained 2.562698-second scheduling overlap; affected results serially rerendered exactly; no blanket serial-only claim',
        scheduling_deviation=recovery,actual_commands='EXECUTION_RECORDS.json; original logs/*.start.json, *.json, *.log and all build/COMPILE.json are authoritative',
        last_engine_exit_code='UNKNOWN',last_engine_note='Outer engine completion is recorded by parent; never infer it from child rc0',
        blockers=[],limitations=['Open partial inner rim','Existing hatching crosses the rim','Inherited contour holes and flat frame','No continuous video or physical/semantic/path-source certification','Serial scheduling deviation retained'],
        scientific_seal=False,branch='partwise-sketch-hatching-gaussian-link-v08',next_action='continue',report_utc=runtime.now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status);js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=NEXT,why='The new saved structural layer is visibly useful but its side-to-hidden transition has only static evidence. A bounded camera asset tests application behavior without another style/geometry scan.'))
    readme='''# Chair结构层资产：实际运行命令

可加载unit007的固定整椅预设、开关一条作者背框曲线，并继续编辑region4座面或region5上背的angle/spacing/length。原GS纸底与座面S连接保持；新增曲线及上背排线为代理表示，无逐路径原核证书。

[五相机完整对照](media/NATURAL_COMPARISON.png) · [完整报告](evidence/REPORT_ZH.md)。PARTIAL：背框更可辨，但排线跨框、开放左侧、框架偏平及旧孔洞保留；高后侧无合成增量，没有新视频或整物体赢家。串行调度偏差及精确恢复见evidence/SCHEDULING_DEVIATION.json与SCHEDULING_RECOVERY.json。

以下依赖为已有LinuxCPU环境：Python、NumPy2.2.6、SciPy1.15.3、Pillow12.2.0、plyfile1.1.5、Open3D0.20.0及g++。源码与数据使用包内相对路径；运行时输出守卫仍限制v08 HDD。没有跨平台/远程认证。每个输出目录必须不存在；顺序运行，不并发。

```bash
U07_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
U07_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_007/delivery
U07_OUT=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_unit007
export CUDA_VISIBLE_DEVICES=''

# 保存关闭状态，曲线与所有排线路径保持。
"$U07_PY" -B "$U07_PACKAGE/code/structure_asset.py" toggle --asset "$U07_PACKAGE/assets/on" --enabled off --out "$U07_OUT/off"

# 从保存资产实际重算原GS、纸底、S、原排线和结构层。
"$U07_PY" -B "$U07_PACKAGE/code/structure_asset.py" render --asset "$U07_PACKAGE/assets/on" --camera "$U07_PACKAGE/cameras/orbit_241_24_5.1.json" --out "$U07_OUT/rear_on"
"$U07_PY" -B "$U07_PACKAGE/code/structure_asset.py" render --asset "$U07_OUT/off" --camera "$U07_PACKAGE/cameras/orbit_241_24_5.1.json" --out "$U07_OUT/rear_off"

# 继续编辑上背方向，保存结构层及其他区域；此例是功能入口，不是新增质量候选。
"$U07_PY" -B "$U07_PACKAGE/code/structure_asset.py" edit --asset "$U07_PACKAGE/assets/on" --region 5 --angle 26 --out "$U07_OUT/edited_back"
# region 4同样接受--angle、--spacing或--length。

# 原始零起始PLY行查询，返回UNKNOWN与原区域证据，不查询曲线所有权。
"$U07_PY" -B "$U07_PACKAGE/code/structure_asset.py" query --asset "$U07_PACKAGE/assets/on" --ids 0 256689
```

包内render和toggle已在新进程实际运行；render弱后侧24数组精确恢复，非零方向编辑的非目标不变量由真实保存测试验证。assets/off与assets/on均已交付，base为unit006精确继承参照。structure.npz含169段新curve_id/face/bary/世界端点，AUTHOR.json保留24个控制点、耗时和开放区段，PROJECTION.json保留支持诊断。全部五个排线路径文件字节不变，原256690行及UNKNOWN170281不变。

source是原GS，paper是全部原核的.95求值颜色覆盖，support是座面原行alpha*T责任；structure是独立代理结构层。base_hybrid为该相机无结构层结果；hybrid为按保存开关合成的实际输出。原contour和独立structure分开保存。新curve并非原生Gaussian线，不是语义标签传播或物理边界真值。
'''
    (UNIT/'delivery/README_ZH.md').write_text(readme)
    doc=CODE.parents[2]/'docs/partwise_sketch_hatching_v08/unit_007.md'
    doc.write_text('# Unit007：可保存的靠背内框结构层\n\nPARTIAL：五相机开/关与24数组冷重载完成，三个后侧视角有可见内框。排线跨框、开放左侧与旧孔洞保留，无整物体赢家。\n\n[完整报告]('+str(UNIT/'REPORT_ZH.md')+') · [资产命令]('+str(UNIT/'delivery/README_ZH.md')+') · [完整对照]('+str(UNIT/'media/NATURAL_COMPARISON.png')+')\n\n一次2.562698秒命令重叠违反串行协议，原记录保留；受影响两项随后串行冷重算24数组逐值恢复。不能宣称全程串行。\n')
    print('Report/status/NEXT/README written; elapsed minutes',elapsed)
if __name__=='__main__':main()
