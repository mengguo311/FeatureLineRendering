"""Package audited outputs and an honest scope-limited report; no scene rerender."""
import runtime
from runtime import sha,js
from pathlib import Path
import datetime,json,shutil
from PIL import Image
import numpy as np
from linked_asset import npz
from whole_asset import load_preset

UNIT=runtime.ROOT/'units/unit_002'
CODE=Path(__file__).parent
START=datetime.datetime.fromisoformat('2026-10-27T09:23:40.587102+09:00')

def records():
    result=[]
    for f in sorted((UNIT/'logs').glob('*.start.json')):
        final=f.with_name(f.name.replace('.start.json','.json'))
        a=json.loads(f.read_text());b=json.loads(final.read_text()) if final.exists() else {}
        result.append(dict(start=str(f.relative_to(UNIT)),receipt=str(final.relative_to(UNIT)) if final.exists() else None,
            argv=a['argv'],child_returncode=b.get('child_returncode','UNKNOWN'),seconds=b.get('seconds','UNKNOWN')))
    return result

def main():
    audit=json.loads((UNIT/'AUDIT.json').read_text());protocol=json.loads((UNIT/'PROTOCOL.json').read_text())
    cold=json.loads((UNIT/'cold_reload/RENDER_RECEIPT.json').read_text())
    assert all(cold['reload_comparison'].values())
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    for name,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(name)==h,name
    for state in ('whole_baseline','whole_spacing'):load_preset(UNIT/'delivery/assets'/state)
    query=json.loads((UNIT/'logs/009_query.log').read_text());js(UNIT/'SOURCE_ID_QUERY.json',query)
    assert query['source_count']==256690
    cold_arrays=npz(UNIT/'cold_reload/FRAME.npz');ref=npz(UNIT/'renders/orbit_241_24_5.1/whole_spacing/FRAME.npz')
    for k,v in ref.items():np.testing.assert_array_equal(v,cold_arrays[k])
    checked=0
    for k in ('source','paper','hybrid','proxy','support','combined_ink','other_ink','contour','seat_ink','seat_linked_ink'):
        a=cold_arrays[k] if k in ('source','paper','hybrid','proxy','support') else 1-cold_arrays[k]
        if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
        with Image.open(UNIT/'cold_reload'/(k+'.png')) as im:im.load();np.testing.assert_array_equal(np.asarray(im),np.uint8(np.clip(a,0,1)*255+.5))
        checked+=1
    decoded=[]
    for f in sorted(UNIT.rglob('*.png')):
        if 'delivery/evidence' in str(f):continue
        with Image.open(f) as im:im.load();size=im.size
        decoded.append(dict(path=str(f.relative_to(UNIT)),size=size,sha256=sha(f)))
    verification=dict(input_files_rechecked=len(json.loads((UNIT/'INPUT_LOCK.json').read_text())),
        cold_arrays=len(cold['reload_comparison']),cold_all_equal=True,cold_original_GS=True,cold_seconds=cold['seconds'],
        png_array_checks=audit['png_array_checks']+checked,decoded_pngs=decoded,
        numerical_commands_serial=True,cpu_affinity_count=2,numeric_threads=1,
        outer_view2=dict(actual_tool_exit_code=143,controller_returncode='UNKNOWN',render_child_returncodes=[0,0],independent_payload_audit_returncode=0),
        network_transfer='Not performed; source/copy SHA pairs in INPUT_COPY_RECEIPT.json. No remote acceptance claim.')
    js(UNIT/'FINAL_VERIFICATION.json',verification)
    table=[];absolute=[];budgets=[];shapes=[]
    for x in audit['views']:
        a=x['budgets']['whole_baseline'];b=x['budgets']['whole_spacing'];e=x['spacing_increment'];g=x['absolute_source_difference']['whole_spacing']
        table.append(f"| {x['view']} | {a['seat_ink_coverage']:.2%} → {b['seat_ink_coverage']:.2%} | {e['target_full']['raw_L1_mean']:.6f} | {e['target_full']['useful_fraction_0_05']:.2%} | {e['far_raw_fraction']:.6f} |")
        absolute.append(f"| {x['view']} | {g['paper']['far_other']['raw_L1_sum']:.3f} / {g['paper']['far_background']['raw_L1_sum']:.3f} | {g['hybrid']['far_other']['raw_L1_sum']:.3f} / {g['hybrid']['far_background']['raw_L1_sum']:.3f} | {g['hybrid']['far_raw_fraction']:.2%} |")
        budgets.append(f"| {x['view']} | {a['combined_ink_mass']:.3f} → {b['combined_ink_mass']:.3f} | {a['conventional_black_ink_mass']:.3f} → {b['conventional_black_ink_mass']:.3f} | {a['object_ink_coverage']:.2%} → {b['object_ink_coverage']:.2%} |")
        s=x['shape_support'];shapes.append(f"{x['view']}: GS-only {s['gs_only']}px / proxy-only {s['proxy_only']}px")
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-START).total_seconds()/60
    report=f'''# Unit002：固定整物体Chair呈现与可保存座面编辑

**执行完成；整物体NPR应用可行性为PARTIAL。** 三个实际视角中，统一纸底、已有全物体排线与轮廓把unit001的照片局部贴片变成可辨认的整椅线描，座面变疏仍可见。椅背、主要腿部和扶手开口保留，前后遮挡关系可以辨认；没有观察到整片座面消失或明显新增双轮廓。但弱后侧椅背有密集杂线，腿部轮廓仍波纹化，高后侧仍有小环状缺口及碎线，不能称干净、几何完整或时序稳定。

同相机新绘的传统代理素描已表达相同主要形体；新GS版本主要增加浅灰纸底并衰减座面墨，没有建立优于传统代理的质量证据。传统代理`proxy.png`保留为简单应用参照，`hybrid.png`作为带原源控制的可选输出，不因新方案较晚就升级为算法赢家。这是显示范围与风格的系统能力比较，不是生成器、S门控或Gaussian后端优越性实验。

[完整物体对照](ALL_VIEWS.png)；每个`renders/<camera>/LAYERS.png`包含原GS、全局纸底、墨、真实混合与传统代理图。总图第二列明确标注unit001 REUSED；其余主体图是本次实际渲染。全图自然强度显示，SHAPE_SUPPORT仅为标明的诊断图，不用放大差分冒充结果。

## 冻结变化与来源

DECISION SHA `{sha(UNIT/'DECISION.json')}`；PROTOCOL SHA `{sha(UNIT/'PROTOCOL.json')}`。先验证并复制65份输入/所需源码；评价前冻结161项输入锁和20份源码。复用unit001两套保存路径，未重新生成、调角度、间距、长度、白强度、平滑或逐视图手工修线。

Chair原PLY共256690个零起始原行；原文件、行序、位置、协方差、opacity、完整SH、代理几何、作者区域、27873行座面权重与UNKNOWN170281保持。保存预设仅在渲染时对**全部原行**覆盖颜色[.95,.95,.95]，原SH不写回，UNKNOWN仍未知。其实际纸底满足`paper=1-0.05*source_alpha`，最大误差5.9605e-08；这是全局显示覆盖，不是完整部件识别或局部编辑成功。

region4仍使用`S=Σalpha*T*s[source_index]`；本轮重用固定17像素网格及真实CPU接受事件，S重建最大误差2.878e-08。其他region1/2/3/5墨及视角轮廓明确为代理表示，没有借座面S冒充各自来源支持。SOURCE_ID_QUERY保留原行查询，非路径认证。几何来自历史冻结vanilla-GS的CPU深度/TSDF代理与人工区域，不是本轮RaDe训练、GT或自动语义。

所有已有路径、face/bary、ID、非目标区域文件与复制前逐字节一致；两状态只复用原有座面140条/1577段与97条/1061段，世界长度18.746579/12.960384。原有边界相位重启混杂保持，不将本轮解释为隔离的间距采样算法收益。非座面风格沿用历史配置；没有新增人工标注或方向引导，历史作者成本不记成零。

轮廓及其他区域既有capsule支持保持。AA2下先对各层取max并集再降采样，座面S在每个像素四个子样本内恒定；不把分别降采样再取max产生的差异混入结果。1px宽、0.004遮挡容差、固定2px评价带、三相机384×384及距离5.1保持。传统代理使用原有黑墨白底；新合成墨色.03并带灰纸底，天然墨量也不同，不能据视觉差异归因于门控增益。

## 固定NPR底上的局部编辑

| 相机 | 座面可见墨覆盖 .045→.0675 | 目标mean raw L1 | 目标L1≥.05 | 远区增量占比 |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

三个相机的远其他部位及远背景raw L1增量均为0；边界带另存EVALUATION.json。非目标墨、轮廓、原GS、纸底、S、标签、深度在两状态间逐值一致。变疏的目的就是降低座面墨量，不能用覆盖下降单独判失败，也不能用零泄漏代替可见编辑。

## 全局绝对变化、墨预算与形体缺口

以下相对**原彩色GS**，沿用座面外的固定远区，绝非局部泄漏通过指标：

| 相机 | 全局纸底远其他/远背景raw L1 | 全局混合远其他/远背景raw L1 | 混合远区占总变化 |
|---|---:|---:|---:|
{chr(10).join(absolute)}

全局变化大且有意，未用编辑差分抵消来隐藏。远背景按照代理标签定义，其中包含GS存在、代理未覆盖的真实源轮廓区域，不等同独立背景GT。原色纹理与细小装饰的表达被统一纸底移除，不能称原GS外观完整保留。

| 相机 | 新整物体墨alpha总量 前→后 | 传统代理黑墨量 前→后 | 新方案全代理物体墨覆盖 前→后 |
|---|---:|---:|---:|
{chr(10).join(budgets)}

这些量只描述预算；本轮不提出等预算机制胜负，因此没有配平或DEV拟合。纸底单独只剩淡灰形状，主要内部形体来自既有代理墨和轮廓，不能把更白当作形体恢复。阈值GS alpha>.5与代理hit比较：{'；'.join(shapes)}。该诊断并非真值，显示两种支撑并不完全一致；高后侧代理内的小环与缺口仍可见，没有填孔或改变深度容差来掩盖。

## 实际复放和执行记录

两组针对新预设的测试先RED rc1（缺whole_asset模块），后GREEN rc0，覆盖保存/无操作编辑不变量、非法预设、座面零S不隐藏其他区域/轮廓及子像素并集。没有重复bootstrap或运行旧生产脚本。

在弱后侧241/24启动独立进程，重新读取包内原PLY、计算GS与墨，19数组逐值恢复，实际渲染{cold['seconds']:.3f}秒。六个初次输出也从保存资产读取，换相机不重生成。独立审计核验60张PNG对应实际数组，冷重载另10张；全部{len(decoded)}张当前结果/历史参照PNG完整解码并保存SHA。SOURCE_LINK/原PLY/旧输入与DECISION再次核对保持。

第三组外层exec会话实际退出143，控制器最终回执缺失，返回码保持UNKNOWN。两个真实渲染子命令各有rc0及完成文件，VIEW_2_EXECUTION完整，独立payload审计rc0。保留006_view2.start/log和INTERRUPTION_view2.json，没有补造006_view2.json，没有重跑该视角。冷重载是预定保存能力验证，不覆盖失败。全部其他已完成命令和编译子返回码见EXECUTION_RECORDS及原logs/build/COMPILE。

只用既有Python/NumPy/SciPy/Pillow/plyfile/Open3D/g++，两核亲和、数值单线程、串行、CUDA为空。无安装、下载、训练、GPU、嵌套模型或旧目录写入。包内相对资产/数据路径；输出守卫仍限定v08 HDD，没有跨平台或远程验收认证。

## 交付与继续方向

[实际可运行预设、编辑与查询命令](delivery/README_ZH.md)。本轮展示保存的旧座面编辑对，新CLI复用已验证编辑器并保留整物体预设；未生成新的科学路径候选。全局纸底模式不提供paper-effect旋钮；unit001的局部纸底编辑仍独立保留。

v05 far8.044%/31腐蚀像素/4.49%区域变化失败、v07全部整物体负结果及H交叉角塌缩/zero_step_cycle、unit001的143/UNKNOWN全部保留。97条路径没有逐路径原ID认证，三张静态视图不是连续视频，工程复放不能证明物理表面或时序有效性。

NEXT=continue：下一次只读审查后，冻结这份整物体spacing资产与传统代理参照，做覆盖前侧和弱后侧的真实短相机轨迹，并加入一次缩放，检查实际遮挡切换与持续可见笔触；不逐帧修线或改风格。是否附带小规模新路径来源记录由下一冻结决定限定，避免把视频工作扩成来源认证项目。现在已具备可观看的整物体底，运动检查比继续静态白强度/平滑微调更接近原始应用目标。

写本报告时距执行授权约{elapsed:.2f}分钟。本单元完成后，下一科学单元仍先只读审查与父级冻结；12:25禁启、12:45收尾、13:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    next_step='下一次只读审查后，冻结本轮整物体Chair spacing资产及传统代理参照，交付包含前侧、弱后侧和一次缩放的真实短相机轨迹；固定世界路径/风格，不逐帧修补，区分正确遮挡与异常消失。'
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why='整物体一致显示与可见局部编辑已有实际输出；下一独立应用问题是运动中的可读性/遮挡，不是继续微调静态指标。'))
    status=dict(execution_state='completed',stage='whole_object_preset_three_views_and_cold_reload_audited',
        scientific_verdict='Whole-object application feasibility PARTIAL; coherent presentation and visible seat edit achieved, no advantage over conventional proxy established.',
        gaussian_link_progress='All256690 original rows preserved; global evaluated-color override and unchanged regional S for seat only. Other ink/contours proxy-only; UNKNOWN170281 retained; no new-path ownership certificate.',
        artifacts=dict(report=str(UNIT/'REPORT_ZH.md'),whole_object=str(UNIT/'ALL_VIEWS.png'),package=str(UNIT/'delivery'),audit=str(UNIT/'AUDIT.json'),verification=str(UNIT/'FINAL_VERIFICATION.json')),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=2),cold_reload=dict(arrays=19,all_equal=True,cold_original_GS=True),
        actual_commands='EXECUTION_RECORDS.json; raw logs and per-render build/COMPILE.json; running finalizer receipt remains separate',
        interruptions=[verification['outer_view2']],continuous_video=False,scientific_seal=False,blockers=[],
        limitations=['Wavy contours, crowded rear hatch and small proxy holes remain','Global whitening is not local control or labeling','No Gaussian gating quality advantage or new-path source certificate','Three exposed static cameras; no temporal certification'],
        branch='partwise-sketch-hatching-gaussian-link-v08',next_action='continue',minutes_at_report=elapsed,last_engine_exit_code='UNKNOWN',last_engine_note='Parent completion unobservable inside child; parent retains actual exit code.')
    js(UNIT/'STATUS.json',status)
    readme='''# Chair整物体NPR预设：实际资产与命令

三视图和冷重载已完成，应用可行性PARTIAL；轮廓波纹、后侧密集线和代理小孔仍在。传统代理输出保留为简单参照，未证明GS版本更好。

本包仅含Chair原PLY、完整原行绑定、两套继承座面布局和两个整物体预设。`whole_baseline`间距.045；`whole_spacing`间距.0675。region4有原行区域S门控，其他笔触和轮廓只有代理支持。全局纸底覆盖全部原行，包括UNKNOWN，但不修改任何标签或原PLY/SH。无逐路径Gaussian所有权、语义/物理表面或连续时序认证。

下面render及query入口已实际执行；edit入口用新预设无操作回归测试通过，路径再生沿用unit001编辑器。本轮科学图复用保存的两个布局，没有执行新候选扫描。输出目录必须不存在且位于v08 HDD根内。

```bash
CHAIR_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
CHAIR_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_002/delivery
CHAIR_RUN=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_whole_chair_001

# 保存已有预设的座面参数修改；非目标路径字节保持
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" edit --asset "$CHAIR_PACKAGE/assets/whole_baseline" --spacing 0.0675 --out "$CHAIR_RUN/edited"
# 同样支持 --angle 与 --length；全局纸底固定，无paper-effect旋钮
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" render --asset "$CHAIR_RUN/edited" --azimuth 241 --elevation 24 --distance 5.1 --size 384 --out "$CHAIR_RUN/image"
# 固定交付资产的真实冷重放，19数组应逐值恢复
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" render --asset "$CHAIR_PACKAGE/assets/whole_spacing" --camera "$CHAIR_PACKAGE/cameras/orbit_241_24_5.1.json" --reference "$CHAIR_PACKAGE/evidence/renders/orbit_241_24_5.1/whole_spacing" --out "$CHAIR_RUN/replay"
# 原始PLY零起始行查询，含UNKNOWN；不是路径绑定
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" query --asset "$CHAIR_PACKAGE/assets/whole_spacing" --ids 0 1 121080 256689
```

`hybrid.png`是实际原GS全局纸底与原行S门控座面/其余代理墨；`proxy.png`是同相机、同路径的传统代理黑墨白底；`paper.png`为实际源核全局颜色覆盖；`source.png`为原GS。两种输出的天然墨量、纸底和墨色不同，不能据图宣称门控优越。

资产和数据使用包内相对路径；运行输出守卫固定v08 HDD范围，未认证任意输出位置或跨平台。现有依赖NumPy2.2.6、SciPy1.15.3、Pillow12.2.0、plyfile1.1.5、Open3D0.20.0、g++；解释器与依赖未打包，无安装步骤。CPU最多2核、单数值线程、CUDA禁用。

[实际整图](evidence/ALL_VIEWS.png) · [报告](evidence/REPORT_ZH.md) · [状态](evidence/STATUS.json)。旧patch列明确复用unit001，其余图本轮真实生成。外层view2的143/UNKNOWN与两个rc0渲染子回执都保留；没有通过重放抹掉失败。三张静态图不是视频。
'''
    (UNIT/'delivery/README_ZH.md').write_text(readme)
    (UNIT/'delivery/requirements.txt').write_text('numpy==2.2.6\nscipy==1.15.3\nPillow==12.2.0\nplyfile==1.1.5\nopen3d==0.20.0\n')
    for f in (UNIT/'cameras').iterdir():
        dst=UNIT/'delivery/cameras'/f.name;dst.parent.mkdir(exist_ok=True);shutil.copy2(f,dst)
    evidence=UNIT/'delivery/evidence';evidence.mkdir(exist_ok=True)
    for name in ('ALL_VIEWS.png','REPORT_ZH.md','STATUS.json','NEXT.json','AUDIT.json','FINAL_VERIFICATION.json','SOURCE_ID_QUERY.json','DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_LOCK.json','INPUT_LOCK.json','INPUT_COPY_RECEIPT.json','INTERRUPTION_view2.json'):
        shutil.copy2(UNIT/name,evidence/name)
    for subtree in ('renders','cold_reload','logs'):
        for f in (UNIT/subtree).rglob('*'):
            if f.is_file() and ('build' not in f.parts and 'scratch' not in f.parts):
                dst=evidence/subtree/f.relative_to(UNIT/subtree);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
    current=records();compile_receipts=[]
    for f in sorted(UNIT.rglob('COMPILE.json')):
        if 'delivery/evidence' not in str(f):compile_receipts.append(dict(path=str(f.relative_to(UNIT)),commands=json.loads(f.read_text())))
    js(UNIT/'EXECUTION_RECORDS.json',dict(commands=current,compile_receipts=compile_receipts,setup=dict(actual_exec_exit_code=0,receipt='INPUT_COPY_RECEIPT.json'),outer_tools=dict(view0=0,view1=0,view2=143),parent_engine_exit_code='UNKNOWN'))
    shutil.copy2(UNIT/'EXECUTION_RECORDS.json',evidence/'EXECUTION_RECORDS.json')
    # Root delivery is an index of completed units, never parent orchestration state.
    (runtime.ROOT/'DEMO_README_ZH.md').write_text('''# v08 当前交付：Chair关联编辑与整物体NPR

unit001完成座面参数/局部源纸底编辑；unit002完成固定整物体预设及三视图编辑前后输出，独立冷重载19数组一致。应用整体仍PARTIAL，没有证明优于传统代理素描。

[unit002实际整图](units/unit_002/ALL_VIEWS.png) · [整物体预设/命令](units/unit_002/delivery/README_ZH.md) · [完整报告](units/unit_002/REPORT_ZH.md)

[unit001局部源纸底编辑](units/unit_001/delivery/README_ZH.md) · [unit001报告](units/unit_001/REPORT_ZH.md)

整物体模式的全局纸底不是局部控制或部件标注。两单元外层143/UNKNOWN及原负结果均保留；无新路径Gaussian所有权或连续视频认证。研究窗口继续，下一单元仍先只读审查。
''')
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_002',units=['unit_001','unit_002'],status=status,old_negative_results_preserved=True))
    docs=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v08/docs/partwise_sketch_hatching_v08/unit_002.md')
    docs.write_text(report)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{f.name:sha(f) for f in sorted(CODE.iterdir()) if f.is_file()})
    print(json.dumps(dict(execution_state=status['execution_state'],scientific_verdict=status['scientific_verdict'],minutes=elapsed,decoded_pngs=len(decoded))))
if __name__=='__main__':main()
