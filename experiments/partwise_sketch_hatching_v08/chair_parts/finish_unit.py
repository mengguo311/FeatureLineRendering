"""Package completed outputs and evidence without rerunning scene evaluation."""
import runtime
from runtime import js,sha
from pathlib import Path
import datetime,json,shutil
import numpy as np
from linked_asset import npz
from run_view import verify

UNIT=runtime.ROOT/'units/unit_005'
CODE=Path(__file__).parent
WORK=CODE.parents[2]
def main():
    verify(UNIT);audit=json.loads((UNIT/'OUTPUT_AUDIT.json').read_text())
    # Actual packaged edit/save/query outputs, read back independently.
    for r in range(1,6):
        assert sha(UNIT/'cli_reedit'/f'region_{r}.npz')==sha(UNIT/'delivery/assets/angle'/f'region_{r}.npz')
        assert sha(UNIT/'cli_seat_noop'/f'region_{r}.npz')==sha(UNIT/'delivery/assets/angle'/f'region_{r}.npz')
    for name in ('WEIGHTS.npz','CONTROL.json'):
        assert sha(UNIT/'cli_source_resave'/name)==sha(UNIT/'delivery/controls/upper_back'/name)
    query=json.loads((UNIT/'logs/017_query.log').read_text());b=npz(UNIT/'delivery/data/chair/SOURCE_BINDING.npz')
    for row in query['rows']:
        i=row['source_index'];expected=.5*b['membership'][i,5] if b['region_id'][i]==5 and not b['unknown'][i] else 0.
        assert row['applied_strength']==expected and row['unknown']==bool(b['unknown'][i]) and row['region_id']==int(b['region_id'][i])
    js(UNIT/'CLI_READBACK.json',dict(reedit_path_files_exact=5,seat_noop_path_files_exact=5,source_resave_exact=True,query_rows=len(query['rows']),query=query))
    views=list(audit['views']);edit_rows=[];source_rows=[];global_rows=[];coverage_rows=[];prep_rows=[]
    for view,d in audit['views'].items():
        e=d['edit'];s=d['source_control'];g=d['global_absolute'];q=d['preparation'];cov=d['upper_back_coverage']
        edit_rows.append(f"| {view} | {e['target']['pixels']} | {e['target']['mean']:.6f} | {e['target']['fraction_above_0_05']*100:.2f}% | {e['far_other']['sum']:.6f} | {e['far_background']['sum']:.6f} |")
        source_rows.append(f"| {view} | {s['target']['mean']:.6f} | {s['far_other']['sum']:.6f} | {s['far_background']['sum']:.6f} | {s['far_fraction']*100:.4f}% | {s['far_background']['max']:.6f} |")
        global_rows.append(f"| {view} | {g['far_other']['sum']:.3f} | {g['far_background']['sum']:.3f} | {g['far_fraction']*100:.2f}% |")
        coverage_rows.append(f"| {view} | {cov['history']*100:.2f}% | {cov['baseline']*100:.2f}% | {cov['angle']*100:.2f}% |")
        prep_rows.append(f"| {view} | {q['target']['mean']:.6f} | {q['far_other']['sum']:.6f} | {q['far_background']['sum']:.6f} |")
    maxerror=max(d['delta_error'] for d in audit['views'].values())
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T10:56:22.484967+09:00')).total_seconds()/60
    next_step='下一次只读审查后，优先检验一次明确改变风格/系统范围的整椅长疏主笔触预设，针对实际图中余下高度区域的密线、腿部波纹和轮廓杂线；保持原GS及作者分区，沿用显式作者方向，在BUILD一次冻结整套配置和作者成本，同时展示当前预设、自然墨量与传统代理参照及弱后侧。若轮廓/代理几何才是主因，应把该结果保留为负，不开展角度/间距/平滑扫描。已有两部位编辑、运动和来源查询继续作为应用交付，不再靠增加证书数量推进。'
    report=f'''# Unit005：可选择座面/上背的保存编辑与独立原源颜色控制

**本轮执行与交付完成；应用可行性为PARTIAL，没有整物体画质或GS关联优势结论。** Chair现在可通过同一入口选择region4/5并保存角度、间距、长度编辑。实际完成上背-25°→25°的一次方向编辑，非目标region1–4路径字节保持；另保存并真实渲染11576个原行的区域颜色控制。两项操作独立，方向编辑仍为代理排线。

[实际编辑前后](media/EDIT_COMPARISON.png) · [完整分层](media/WHOLE_LAYERS.png) · [原GS区域高亮](media/SOURCE_CONTROL.png) · [可运行命令与资产](delivery/README_ZH.md)

## 实际整图判断

逐一检查三个相机的原尺寸前后图和完整分层。前侧上背由斜向笔触变为近竖向弯曲笔触；后侧也有方向变化，高后侧窄背区出现横向短段。整椅主要腿部和扶手开口仍可辨，未见整片椅背因编辑消失。座面、腿部及其他部位保持原输出。弱后背下缘密线、腿部波纹、高后侧小孔/碎线仍在；新风格不是自动顺形恢复，也未证明更好。传统proxy与hybrid同样表达主要形体，GS底层不获画质优势主张。

实际源高亮在前后上背均可见，背面呈宽蓝色斑块，前侧保留纹理斑驳；覆盖不均匀且不等于完整椅背选择。高亮图来自完整原Gaussian核重渲染，无overlay、裁掉其他核、opacity衰减或差分增益。右列仅显示原值的加权贡献诊断图。

## 共同基线与真实编辑

历史region5为208条/1695段、世界长19.945529、继承capsule掩码40（region3/5）。历史完整资产与unit004参考数组按清单核验后原样保留，比较图明确标“reused unit004”。共同控制在原-25°上实际重生成，216条/1720段、长20.389662，owner-only掩码32。编辑后185条/1843段、长20.267609，掩码仍32。三组上背路径身份互不相交，face/bary仍落在固定3055个作者面内。

主比较只改上背angle=-25→25；spacing=.045、length=.22、width=1、ink_strength=.45、xz平面保持。笔触数、相位和截断长度的响应属于参数编辑，不是纯方向场或相同笔触预算实验。历史到共同控制还包含重新切片、边界相位及capsule支持变化，单独列出：

| 相机 | 历史→共同控制目标mean raw L1 | 远其他raw L1 | 远背景raw L1 |
| --- | --- | --- | --- |
{chr(10).join(prep_rows)}

主编辑相对同一固定整物体底的变化：

| 相机 | region5目标像素 | 目标mean raw L1 | 目标L1≥.05比例 | 远其他raw L1 | 远背景raw L1 |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(edit_rows)}

这里远区使用原作者region5掩码和固定2px带，不是独立语义GT。零增量来自既有owner-only裁剪和非目标复用，不是新的H2边界约束贡献；也不抵消全局纸底原有变化。自然上背墨覆盖如下，差异不作质量排名或等预算优势：

| 相机 | 历史 | 共同控制 | 方向编辑 |
| --- | --- | --- | --- |
{chr(10).join(coverage_rows)}

尤其不能把更少的墨直接称为更干净：弱后侧上背覆盖79.24%→63.74%，高后侧58.50%→30.58%。高后侧的稀疏横段虽然仍保留窄背区形体，但覆盖下降是明确限制；本轮证明可编辑，不证明连续性修复或新风格胜出。

## 原GS连接的范围与远区影响

原256690个零起始PLY行及行序、位置、协方差、opacity、完整SH保持。座面27873行S、UNKNOWN170281、原绑定、全局.95纸底、轮廓规则、AA2与0.004遮挡容差保持。region5墨没有新增S门控。新增控制另保存完整原行权重向量：仅region_id=5且非UNKNOWN行采用0.5×原membership，其余为零；固定颜色[.02,.4,1]在fullSH3求值后的私有颜色副本中混合，不写回SH/PLY。三个相机复用同一11576行权重，无后侧补选或逐视角归一。

| 相机 | 高亮目标mean raw L1 | 远其他raw L1 | 远背景raw L1 | 远区占总变化 | 远背景最大像素L1 |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(source_rows)}

远区不是严格零：弱后侧远其他约4.026，且高后侧远背景最大单像素L1约0.239。低比例与明显目标变化支持这份有界作者区域控制可操作，不支持精确部件分割或零泄漏；不得以此修复v05的稀疏路径任务。相对原彩色GS，编辑hybrid的全局绝对远区变化另列：

| 相机 | 远其他raw L1 | 远背景raw L1 | 远区占总变化 |
| --- | --- | --- | --- |
{chr(10).join(global_rows)}

这些全局变化来自全物体纸底/墨，不是本轮局部编辑增量或自动标签成功。作者区域来自历史人工选择，原重建为既有NeRF Synthetic Chair冻结vanilla-GS和CPU深度/TSDF代理；不是新实物采集、RaDe训练或真值几何。

## 保存、冷重载与独立读回

实际TDD RED rc1为缺parts_asset模块；随后3组GREEN rc0，覆盖分离作者区域的生成/锚点/新身份/owner-only、无操作保存与非法区域/参数、原行权重/UNKNOWN及控制校验。三个固定相机384×384、距离5.1全部已曝光，不称训练未见；共9次新场景输出（共同控制、编辑、源高亮各三次），没有新视频。

输出审计确认region1–4各路径文件逐字节不变；每相机13项非目标/源/纸底/座面S与墨/轮廓/区域深度数组恢复历史并保持。69张主要PNG逐像素等于对应数组。固定8px格点每视图2304像素，全部{audit['full_T_events']}条真实接受事件保存；独立恢复完整T链、alpha、fullSH RGB、控制权重和颜色增量，增量最大误差{maxerror:.3g}，无top-K截断。这是格点上的CPU事件读回，不是全图逐核认证，更不是新路径来源证明。

包内CLI在新进程从原PLY冷重算弱后侧：编辑19数组、源控制6数组逐值相同；两个实际编译子返回码均记录在各build/COMPILE.json。包内edit再次生成相同五个路径文件；source-save再次保存相同权重/控制；region4无操作保存保持全部路径。8个真实source-ID查询包括UNKNOWN和座面反例，独立读回一致。无额外bootstrap或旧影片重跑。

unit004稀疏来源证书仍只属于其原资产，本包没有迁移它，也没有给185条上背新路径附加伪证书。保存的区域颜色控制仅依赖原source/binding身份，不声称依赖或绑定某条新笔触。

## 执行记录、限制与后续

所有实际子命令、预期RED和编译退出状态在logs、EXECUTION_RECORDS.json及COMPILE.json。本轮科学命令均rc0；外层engine退出码由父级观测，本单元不补造为0。仅本机Linux CPU、最多两核亲和、单数值线程、串行，CUDA为空。无安装、下载、GPU、训练、嵌套模型、旧资产写入、push/merge；无远程或跨平台认证。冻结DECISION、科学源码及输入不变，事后读回/报告脚本另列HANDOFF_SOURCE_LOCK。

保留v05 far8.044%/31腐蚀像素/4.49%原区域变化失败，v07十一轮整物体负结果、H交叉角塌缩和zero_step_cycle，unit001–003的143/UNKNOWN、unit003共同可见自身墨跌落，以及unit004两个空集合和077弱后侧近消失。科学seal=false；工程完成不替代独立科学验收。

NEXT=continue。{next_step}

报告时距执行授权约{elapsed:.2f}分钟；12:25禁启新单元、12:45收尾、13:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    status=dict(execution_state='completed',stage='two_region_editor_saved_source_control_and_cold_reload_audited',
        scientific_verdict='PARTIAL application capability: visible upper-back angle edit and separate original-source region tint. Existing whole-object clutter remains; no quality, physical-ownership or temporal advantage.',
        gaussian_link_progress='Original256690 rows/fullSH/geometry/opacity fixed; original binding and UNKNOWN170281 unchanged. Seat S retained; upper-back ink proxy-only. Separate saved11576-row weighted original-GS color control, not new-path ownership.',
        artifacts=dict(package='delivery',edit='media/EDIT_COMPARISON.png',whole_layers='media/WHOLE_LAYERS.png',source_control='media/SOURCE_CONTROL.png',audit='OUTPUT_AUDIT.json'),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=3),cold_reload=audit['reload'],
        non_target_regions_byte_identical=[1,2,3,4],paths=audit['paths'],source_control_rows=11576,new_cameras=3,new_scene_outputs=9,
        png_array_checks=69,full_T_recorded_events=audit['full_T_events'],new_path_certificates=False,new_video=False,
        actual_commands='EXECUTION_RECORDS.json; logs/*.start.json/*.json/*.log; build/COMPILE.json',
        blockers=[],limitations=['Authored regions only','Region5 ink is proxy-only','High-rear upper-back coverage drops58.50% to30.58%; no style winner','Residual dense back lines, wavy legs and proxy holes','Source tint has nonzero far-region effects','Local CPU only; no temporal certification'],
        scientific_seal=False,last_engine_exit_code='UNKNOWN',last_engine_note='Outer engine completion belongs to parent; command/compiler receipts are separate.',
        branch='partwise-sketch-hatching-gaussian-link-v08',next_action='continue',report_utc=runtime.now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status);js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why='Two authored regions are now operable; the visible remaining bottleneck is whole-object style/contour readability, not lack of another sparse source certificate. Further work requires a new read-only review and parent freeze.'))
    readme='''# Chair：座面/上背参数编辑与独立原源高亮

已完成实际上背方向编辑、原GS区域颜色控制和保存/冷重载。可用性PARTIAL：密线、腿部波纹与小孔仍在，未建立GS画质优势。上背方向变化是代理排线；原源高亮是另一操作。座面保留既有原行S门控。

[实际编辑](media/EDIT_COMPARISON.png) · [完整层图](media/WHOLE_LAYERS.png) · [真实原核高亮](media/SOURCE_CONTROL.png) · [报告](REPORT_ZH.md)

本包只含Chair。`assets/history`为unit004原资产；`baseline`是上背-25°共同重生成基线；`angle`是+25°编辑结果。`controls/upper_back`保存固定原行权重。历史208条路径/掩码40与共同控制216条/掩码32不同；正式角度比较为共同控制→185条编辑路径。所有region1–4文件字节保持。

依赖：现有Python、NumPy2.2.6、SciPy1.15.3、Pillow12.2.0、plyfile1.1.5、Open3D0.20.0与g++。未安装或修改旧环境。输入数据引用均为包内相对路径；CPU运行时输出守卫仍限定本机v08 HDD根目录，未做任意平台部署认证。

以下入口均已实际运行；复制命令时将`PARTS_PACKAGE`改为本包位置、`PARTS_OUT`改为不存在的新v08 HDD目录。各子输出必须不存在。最多两核亲和、单数值线程、串行，入口在数值导入前禁用CUDA。

```bash
PARTS_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
PARTS_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_005/delivery
PARTS_OUT=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_parts_001
export CUDA_VISIBLE_DEVICES=''

# 实际参数编辑并保存；也支持 --region 4 和 --spacing / --length。
"$PARTS_PY" -B "$PARTS_PACKAGE/code/parts_asset.py" edit --asset "$PARTS_PACKAGE/assets/baseline" --region 5 --angle 25 --out "$PARTS_OUT/angle"

# 冷加载保存资产并实际重渲染弱后侧；cameras/0、1、2为前侧/弱后侧/高后侧。
"$PARTS_PY" -B "$PARTS_PACKAGE/code/parts_asset.py" render --asset "$PARTS_OUT/angle" --camera "$PARTS_PACKAGE/cameras/1.json" --out "$PARTS_OUT/render"

# 独立原GS颜色控制：不改笔触，不更改PLY/SH/opacity，不扩大UNKNOWN。
"$PARTS_PY" -B "$PARTS_PACKAGE/code/parts_asset.py" source-save --asset "$PARTS_OUT/angle" --region 5 --mix 0.5 --color 0.02 0.4 1 --out "$PARTS_OUT/control"
"$PARTS_PY" -B "$PARTS_PACKAGE/code/parts_asset.py" query --asset "$PARTS_OUT/angle" --control "$PARTS_OUT/control" --ids 0 1 11 60898 125939 194591 256684 256689
"$PARTS_PY" -B "$PARTS_PACKAGE/code/parts_asset.py" source-render --asset "$PARTS_OUT/angle" --control "$PARTS_OUT/control" --camera "$PARTS_PACKAGE/cameras/1.json" --out "$PARTS_OUT/source_highlight"
```

`prepare`可从history显式重建上背共同基线；这是支持规则/生成准备，不是方向编辑收益。不要运行包内冻结/复制脚本重建旧单元。`source-render`输出完整原GS与真实颜色覆盖，不含逐路径定位overlay。

原256690行、UNKNOWN170281及原绑定保持；上背源控制11576行，参数0.5乘原作者membership，不是语义概率。新上背路径无逐Gaussian附着证书，unit004证书没有迁移。三张静态相机不构成新视频。历史v05/v07负结果及unit003时序跌落、unit004空集合与后侧缺失仍保留。没有远端、跨平台或实时性能认证。
'''
    package=UNIT/'delivery';(package/'README_ZH.md').write_text(readme)
    (package/'REPORT_ZH.md').write_text(report.replace('(delivery/README_ZH.md)','(README_ZH.md)'))
    shutil.copytree(UNIT/'media',package/'media',dirs_exist_ok=True)
    evidence=package/'evidence';evidence.mkdir(exist_ok=True)
    for name in ('STATUS.json','NEXT.json','DECISION.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_LOCK.json','INPUT_LOCK.json','INPUT_SEAL.json','INPUT_COPY_RECEIPT.json','OUTPUT_AUDIT.json','CLI_READBACK.json'):
        shutil.copy2(UNIT/name,evidence/name)
    for kind in ('baseline','angle','highlight'):
        for view in views:
            dest=package/'renders'/kind/view;dest.mkdir(parents=True,exist_ok=True)
            for f in (UNIT/'renders'/kind/view).iterdir():
                if f.is_file():shutil.copy2(f,dest/f.name)
    for name in ('cold_edit','cold_source'):
        shutil.copy2(UNIT/name/'RENDER_RECEIPT.json',evidence/(name+'_RECEIPT.json'))
    handoff=package/'handoff';handoff.mkdir(exist_ok=True)
    frozen=json.loads((UNIT/'SOURCE_LOCK.json').read_text());after={}
    for f in CODE.iterdir():
        if f.is_file() and f.name not in frozen:shutil.copy2(f,handoff/f.name);after[f.name]=sha(f)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',after)
    doc=WORK/'docs/partwise_sketch_hatching_v08/unit_005.md'
    doc.write_text('# Unit005：两作者区域的Chair编辑资产\n\n已完成上背方向编辑、独立原GS区域颜色控制与冷重载；应用PARTIAL，无画质优势。\n\n'+f'[完整报告]({UNIT}/REPORT_ZH.md) · [可运行资产]({package}/README_ZH.md) · [实际整图]({UNIT}/media/EDIT_COMPARISON.png)\n\n'+next_step+'\n')
    (runtime.ROOT/'DEMO_README_ZH.md').write_text('''# v08 当前交付：Chair两部位保存编辑、真实浏览与来源控制

最新unit005完成座面/上背可选择编辑，上背方向变化与独立原GS颜色控制均有真实三视图和冷重载。整物体应用仍PARTIAL；后背密线、腿部波纹、小孔及既有时序失败保留，未建立GS画质优势。

[unit005命令与资产](units/unit_005/delivery/README_ZH.md) · [编辑前后](units/unit_005/media/EDIT_COMPARISON.png) · [源控制](units/unit_005/media/SOURCE_CONTROL.png) · [报告](units/unit_005/REPORT_ZH.md)

[unit003实际半周/缩放](units/unit_003/delivery/README_ZH.md) · [unit004稀疏路径查询](units/unit_004/delivery/README_ZH.md) · [unit001座面源纸底编辑](units/unit_001/delivery/README_ZH.md)

unit003视频和unit004证书各属于原资产，未迁移到unit005新路径；本轮无新影片。上背墨为代理控制，原GS染色为单独区域操作。所有旧负结果及143/UNKNOWN保留。后续单元仍须先只读审查。
''')
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_005',units=[f'unit_{i:03d}' for i in range(1,6)],status=status,old_negative_results_preserved=True))
    print('Packaged completed Chair part-edit capability; no new science.',flush=True)
if __name__=='__main__':main()
