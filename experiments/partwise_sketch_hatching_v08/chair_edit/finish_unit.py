"""Package existing completed outputs and write an evidence-scoped report."""
import runtime
from runtime import sha,js
from pathlib import Path
import json
import shutil
import numpy as np
from PIL import Image
from linked_asset import npz

UNIT=runtime.ROOT/'units/unit_001'
CODE=Path(__file__).parent
WORKTREE=CODE.parents[2]

def main():
    audit=json.loads((UNIT/'AUDIT.json').read_text());p=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    reloads={}
    for state in ('spacing','paper_half'):
        path=UNIT/'cold_reload'/state;r=json.loads((path/'RENDER_RECEIPT.json').read_text())
        assert r['cold_original_GS'] and all(x['array_equal'] for x in r['reload_comparison'].values())
        reloads[state]=dict(arrays=len(r['reload_comparison']),all_equal=True,seconds=r['seconds'],receipt=str(path/'RENDER_RECEIPT.json'))
    # Decode every final frame and independently check its published PNG quantization.
    pngs=[]
    for path in sorted(UNIT.rglob('*.png')):
        with Image.open(path) as im:im.load();size=im.size
        pngs.append(dict(path=str(path.relative_to(UNIT)),sha256=sha(path),size=size))
    checks=0
    for framefile in list((UNIT/'renders').rglob('FRAME.npz'))+list((UNIT/'cold_reload').rglob('FRAME.npz')):
        f=npz(framefile)
        for key in ('source','paper','hybrid','support','ink','linked_ink'):
            expected=(1-f[key]) if key in ('ink','linked_ink') else f[key]
            if expected.ndim==2:expected=np.repeat(expected[:,:,None],3,2)
            expected=np.uint8(np.clip(expected,0,1)*255+.5)
            with Image.open(framefile.parent/(key+'.png')) as im:actual=np.asarray(im)
            np.testing.assert_array_equal(actual,expected);checks+=1
    query=json.loads((UNIT/'logs/013_query.log').read_text())
    assert query['source_count']==256690 and any(x['unknown'] for x in query['rows']) and any(x['paper_strength']>0 for x in query['rows'])
    js(UNIT/'SOURCE_ID_QUERY.json',query)
    command_records=[]
    for path in sorted((UNIT/'logs').glob('*.json')):
        if path.name.endswith('.start.json'):continue
        r=json.loads(path.read_text());command_records.append(dict(receipt=str(path.relative_to(UNIT)),**r))
    missing=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        receipt=start.with_name(start.name.replace('.start.json','.json'))
        if not receipt.exists():missing.append(dict(start=str(start.relative_to(UNIT)),receipt=str(receipt.relative_to(UNIT)),child_returncode='UNKNOWN'))
    js(UNIT/'EXECUTION_RECORDS.json',dict(completed=command_records,missing_final_receipts=missing,
        outer_tool_failure=json.loads((UNIT/'INTERRUPTION_view2.json').read_text()),
        note='This snapshot includes the currently running finish command as pending UNKNOWN; later its actual receipt is separate. No success is inferred from missing fields.'))
    verification=dict(cold_reloads=reloads,decoded_pngs=pngs,png_array_checks=checks,
        actual_numerical_commands_serial=True,cpu_affinity_count=len(runtime.os.sched_getaffinity(0)),numeric_threads=1,
        source_copy_and_old_input_audit='AUDIT.json',query='SOURCE_ID_QUERY.json',outer_controller='143 with controller status UNKNOWN; all three render children rc0, saved payload audit rc0')
    js(UNIT/'FINAL_VERIFICATION.json',verification)
    views=audit['views'];table=[];damage=[];caps=[];samples=[]
    for v in views:
        d=v['comparisons'];ink=v['ink'];a=v['absolute_source_difference']
        table.append(f"| {v['view']} | {100*ink['baseline']['target_visible_fraction']:.2f}% → {100*ink['spacing']['target_visible_fraction']:.2f}% | {d['spacing_increment']['target_full']['clipped_L1_mean']:.5f} | {100*d['spacing_increment']['target_full']['useful_fraction_0_05']:.2f}% | {100*d['paper_increment']['far_raw_fraction']:.4f}% |")
        row=[]
        for state in ('baseline','spacing','paper_half'):
            m=a[state]['hybrid'];far=m['far_other']['raw_L1_sum']+m['far_background']['raw_L1_sum']
            row.append(f"{far:.6f} / {100*m['far_raw_fraction']:.4f}%")
        damage.append('| '+v['view']+' | '+' | '.join(row)+' |')
        cap=d['cap_normalization_increment'];caps.append(dict(view=v['view'],raw_total_L1=cap['raw_total_L1'],far_raw_fraction=cap['far_raw_fraction']))
        r=v['source_proofs'][0];samples.append(dict(view=v['view'],samples=r['trace_samples'],target_samples=r['target_samples'],unsupported_samples=r['unsupported_samples']))
    worst_support=max(r['support_reconstruction_max_error'] for v in views for r in v['source_proofs'])
    worst_delta=max(r['paper_delta_reconstruction_max_error'] for v in views for r in v['source_proofs'])
    elapsed=(runtime.datetime.datetime.now(runtime.datetime.timezone.utc)-runtime.datetime.datetime.fromisoformat('2026-10-26T23:57:46.100444+00:00')).total_seconds()/60
    next_step='下一次只读审查后，冻结本轮Chair spacing资产与全部风格，交付包含前侧和弱后侧的真实短相机轨迹及一次缩放；固定世界路径和身份，不逐帧修线。对预先固定的一小组新路径锚点同时保存完整alpha*T原ID支持与无支持样本，使视频可定位区域门控、真实遮挡和新路径支持缺口。保持这是应用/来源证据任务；不重开Lego微调，不以更多样本宣称质量改善。'
    report=f'''# Unit001：Chair 可保存的原GS关联座面编辑

**应用编辑里程碑完成；整体NPR观感仍为PARTIAL，没有建立新方法或整物体画风优势。**

本次实际CLI将座面间距0.045改为0.0675，另独立将纸底系数1改为0.5；保存为三个资产，从包内原始PLY重新渲染三个已曝光相机。三视图都能辨认变疏的座面排线，纸底减半则使原绿色织物显露。扶手前后遮挡仍可见，座面没有因本次操作整体消失。高后视图仍有短段、空隙、织物纹理残留和明显的局部纸底区域；这是一项可用的局部编辑示例，尚非完整素描物体，也没有用户偏好或连续时序认证。

[整物体前后图](ALL_VIEWS.png)；各相机目录内的LAYERS.png分别显示原GS、纸底、墨及真实混合结果。所有图为本次实际输出，不用旧图冒充新结果。

## 操作与不变量

父级DECISION保持：`{p['decision_sha256']}`；冻结PROTOCOL：`{sha(UNIT/'PROTOCOL.json')}`。源码与输入在评价前锁定。实际复制28份所需源码/资产，按v05/v06/v07保存锁核对；另核验三份旧v06相机数组以作来源参照。全部{audit['input_hashes_verified']}份输入锁在审计时保持。

保留Chair256690个原PLY零起始行号、原PLY/位置/协方差/opacity/完整SH/行序，代理mesh和作者标签不变。非目标region1/2/3/5文件逐字节保持；27873行区域权重与v06 primary逐值相同，UNKNOWN170281保持。标签是作者区域证据，不是语义概率。

原140条/1577段路径、世界长度18.746579；新间距97条/1061段、12.960384。新路径有独立身份及face/bary，锚点独立重建最大误差1.11e-16；这只证明贴在自身代理上。变疏本来就降低墨量，不作等预算质量胜负判断。基线继承父路径的弧长相位，而重新生成会在区域边界重新开始相位，因此没有声称隔离了纯间距采样机制。

旧座面visibility_mask=20，生成器默认16。两份v08比较资产统一为owner-only16；原路径点、face/bary和ID在这一步不变，旧资产完整保留。端帽变化单独呈现CAP_NORMALIZATION.png，并记录：`{json.dumps(caps,ensure_ascii=False)}`。这些边界差异不算间距编辑收益。

纸底是fullSH3求值后的逐原行颜色混合：c'=(1-paper_effect*s)c+paper_effect*s*[.95,.95,.95]，原SH不写回。墨来自保存的三维代理路径，乘S=Σalpha*T*s；paper-effect不改变S、墨路径或墨alpha。只有region4进入当前混合显示，其他区域路径保存在资产中，未假称全物体已经排线。

## 可见效果与绝对远区损伤

固定384×384、1px线宽、AA2、0.004代理遮挡容差和2px评价带；相机61/24、241/24、241/60，距离5.1，均EXPOSED。以下是描述量，不是审美通过阈值。

| 相机 | 目标可见墨覆盖 基线→间距编辑 | 目标编辑mean clipped L1 | 目标像素L1≥0.05 | 纸底编辑增量远区占比 |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

间距编辑三个相机的固定远区raw L1增量均为0，边界带单列于EVALUATION.json；这不等于原纸底没有既有影响。下表为相对原GS的绝对混合远区raw L1总量/占比：

| 相机 | 基线 | 间距编辑 | 纸底减半 |
|---|---:|---:|---:|
{chr(10).join(damage)}

纸底及墨层分别报告，没有通过差分抵消隐藏源改色影响，也没有扩大边界带。保留自然强度；本轮是不同用户参数的能力演示，未提出门控优于未门控的机制主张。

## 原ID证据与真实冷重载

每相机固定17个像素，含背景样本；记录所有真实CPU接受事件的source_index/alpha/T/weight，无top-K截断。样本范围：`{json.dumps(samples,ensure_ascii=False)}`。没有按渲染效果追加样本。S重建最大误差{worst_support:.3e}，纸底RGB变化重建最大误差{worst_delta:.3e}。SOURCE_ID_QUERY.json含已支持行和UNKNOWN原行；paper_strength随保存参数变为原值一半，ink_strength保持。这是实际源颜色/区域责任连接证据，不是97条新路径的逐核附着认证。

间距资产和纸底资产在241/24各启动独立进程，重新从原PLY计算GS与墨，共18个数组逐值恢复；没有复用GS图层缓存。每个初次输出也是从保存资产加载，换相机不重生成路径。三份原GS source/paper/S与旧v06对应数组恢复。{len(pngs)}张PNG完整解码，{checks}张主图另与实际数组量化结果逐像素核对。

3组针对新编辑行为的测试先RED（缺linked_asset模块，rc1）后GREEN（rc0）；覆盖区域隔离、无操作、纸底参数与路径分离、新路径身份、锚点、非法参数和旧目录写保护。angle/length仅在工程检查中执行，没有生成额外科学候选或选择参数。

第三相机外层工具会话实际退出143，外层最终回执缺失，controller退出码UNKNOWN；三个渲染子命令各有rc0回执和完成文件，后续独立读回审计rc0。原start/log、INTERRUPTION_view2.json及VIEW_2_EXECUTION.json均保留，没有补造009_view2.json或重跑该场景。后续冷重载是预定保存能力验证，不覆盖这个失败。

## 交付范围与后续

[可运行包与命令](delivery/README_ZH.md)，含原PLY、完整绑定、三份资产和实际CLI；无新UI。沿用现有NumPy2.2.6/SciPy1.15.3/plyfile1.1.5/Pillow12.2.0/Open3D0.20.0/g++，CPU最多2核、数值单线程串行，CUDA为空。没有安装、GPU、训练、下载、嵌套模型或旧目录写入。当前输出守卫限定v08 HDD；未认证跨平台。

v05 far8.044%、31腐蚀像素、4.49%原作者区域变化失败，v07无整物体赢家、H交叉角混杂及zero_step_cycle全部保持。三张图不是连续视频；没有完整语义分部、物理表面或原生Gaussian排线认证。

NEXT=continue：{next_step}

写本报告时距执行授权约{elapsed:.2f}分钟；本单元只完成上述编辑交付，下一科学单元仍先只读审查和父级冻结。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    readme='''# Chair 原GS关联座面编辑资产

本包实际包含Chair原始PLY、完整原行绑定和baseline/spacing/paper_half三份可重载资产。支持region4的angle、spacing、length及独立paper-effect；输出是原GS纸底加区域责任门控的代理墨，非原生Gaussian排线。其他区域路径保留，但当前混合显示只画座面region4。

依赖现有Python环境：NumPy 2.2.6、SciPy 1.15.3、plyfile 1.1.5、Pillow 12.2.0、Open3D 0.20.0、g++。无需安装。以下设置在本机Linux CPU已验证；运行时强制禁用CUDA、最多2核亲和和单数值线程。

```bash
CHAIR_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
CHAIR_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_001/delivery
CHAIR_OUTPUT=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_chair_edit_001

# 创建一份新的保存资产；输出目录必须不存在。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/linked_asset.py" edit \
  --asset "$CHAIR_PACKAGE/assets/baseline" --out "$CHAIR_OUTPUT" --spacing 0.0675

# 从刚保存的资产和原PLY实际渲染；角度与间距不会随相机重生成。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/linked_asset.py" render \
  --asset "$CHAIR_OUTPUT" --out "${CHAIR_OUTPUT}_rear" \
  --azimuth 241 --elevation 24 --distance 5.1 --size 384

# 独立源纸底参数操作，保持全部笔触不变。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/linked_asset.py" edit \
  --asset "$CHAIR_PACKAGE/assets/baseline" --out "${CHAIR_OUTPUT}_paper" --paper-effect 0.5

# 查询真实原PLY零起始行号，保留UNKNOWN及曝光信息。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/linked_asset.py" query \
  --asset "$CHAIR_PACKAGE/assets/paper_half" --ids 0 1 121080 256689
```

`edit`还接受`--angle`和`--length`；它们是代理路径参数，paper-effect才改变原GS逐行求值颜色。保存的SOURCE_LINK.npz保持全部256690行，27873行有座面责任，UNKNOWN170281。改路径会获得新身份；无操作和仅纸底操作保留路径字节。资产中的数据依赖为相对路径，请整体保留data与assets目录；单独移走一个资产目录需同时维护相对数据依赖。

每次render输出source/paper/support/ink/linked_ink/hybrid PNG、FRAME.npz、真实接受事件TRACE.npz、SOURCE_WITNESS.npz和RENDER_RECEIPT.json。传入`--reference`指定已完成渲染目录可做冷重载逐值比较。`--camera`可读取保存的相机JSON。所有新输出只能在授权v08 HDD根下且位于orchestration之外；不允许覆盖已有目录。

已完成的前后整物体图在evidence/ALL_VIEWS.png，报告在evidence/REPORT_ZH.md，原行查询在evidence/SOURCE_ID_QUERY.json。自然强度下变疏可见，但仍有织物残留、短段和局部纸底边界；没有整物体NPR优势或连续视频认证。端帽从继承mask20统一到owner-only16的变化单独保存，不能算间距编辑收益。原v05/v07负结果保持。

唯一承诺的应用入口是code/linked_asset.py。setup_inputs/prepare_unit/test等是本机实验溯源工具，含历史只读输入路径；不要把它们当便携重建入口。核心源码按SOURCE_LOCK固定，后续报告工具另列HANDOFF_SOURCE_LOCK。
'''
    (UNIT/'delivery/README_ZH.md').write_text(readme)
    (UNIT/'delivery/requirements.txt').write_text('numpy==2.2.6\nscipy==1.15.3\nplyfile==1.1.5\nPillow==12.2.0\nopen3d==0.20.0\n')
    evidence=UNIT/'delivery/evidence';evidence.mkdir(exist_ok=True)
    for name in ('ALL_VIEWS.png','REPORT_ZH.md','SOURCE_ID_QUERY.json','FINAL_VERIFICATION.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_LOCK.json','INPUT_COPY_RECEIPT.json','INTERRUPTION_view2.json'):
        shutil.copy2(UNIT/name,evidence/name)
    for c in p['cameras']:
        folder=evidence/c['view'];folder.mkdir(exist_ok=True)
        for name in ('LAYERS.png','CAP_NORMALIZATION.png','EVALUATION.json'):shutil.copy2(UNIT/'renders'/c['view']/name,folder/name)
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why='真实可保存的单部件编辑已有可见结果；下一独立问题是实际相机运动与新路径来源支持，非继续优化静态小指标。'))
    status=dict(execution_state='completed',stage='linked_chair_edit_saved_cold_reloaded_and_three_camera_outputs_audited',
        scientific_verdict='Application editing milestone completed; whole-object NPR appearance remains PARTIAL; no superiority claim.',
        gaussian_link_progress='Complete original256690 rows preserved, selected27873 and UNKNOWN170281 unchanged; actual per-original-row evaluated-color edit plus full-T regional S proxy ink. New97 paths have stable identities and anchors, not per-path Gaussian ownership certification.',
        branch='partwise-sketch-hatching-gaussian-link-v08',scientific_seal=False,
        artifacts=dict(package=str(UNIT/'delivery'),whole_object=str(UNIT/'ALL_VIEWS.png'),report=str(UNIT/'REPORT_ZH.md'),audit=str(UNIT/'AUDIT.json'),verification=str(UNIT/'FINAL_VERIFICATION.json')),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=3),actual_commands='EXECUTION_RECORDS.json and logs/*.json; running finalizer receipt is separate',
        interruptions=[dict(stage='view2 outer tool',actual_tool_exit_code=143,controller_returncode='UNKNOWN',render_children_returncodes=[0,0,0],payload_audit_returncode=0)],
        cold_reloads=reloads,continuous_video=False,blockers=[],limitations=['Patch-over-photo appearance, texture remnants and fragmented strokes remain','No new-path original-ID attachment certification','No temporal or cross-platform certification','Outer view2 controller exit remains UNKNOWN'],
        next_action='continue',minutes_at_report=elapsed,last_engine_exit_code='UNKNOWN',last_engine_note='Parent engine completion is not observable inside this child; parent retains its actual exit code.')
    js(UNIT/'STATUS.json',status)
    docs=WORKTREE/'docs/partwise_sketch_hatching_v08';docs.mkdir(parents=True,exist_ok=True)
    (docs/'unit_001.md').write_text(report)
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(**status,current_unit='unit_001',research_window='active until 2026-10-27 13:00 JST; no new units12:25/wrap12:45',final_research_delivery=False))
    (runtime.ROOT/'DEMO_README_ZH.md').write_text('# v08 当前交付：Chair 可保存关联编辑\n\n单元001完成。座面间距与原GS纸底参数可独立编辑、保存、冷重载，并已输出三个真实相机。整体NPR仍为PARTIAL；研究窗口继续，NEXT=continue。\n\n[实际图](units/unit_001/ALL_VIEWS.png) · [命令与资产](units/unit_001/delivery/README_ZH.md) · [完整报告](units/unit_001/REPORT_ZH.md) · [状态](units/unit_001/STATUS.json)\n\n保留全部旧负结果及第三相机外层143/UNKNOWN；三个渲染子命令成功且完成读回审计。无连续视频或逐路径Gaussian所有权认证。\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',{f.name:sha(f) for f in CODE.iterdir() if f.is_file() and f.name not in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files']})
    print(json.dumps(dict(status='completed',visual='PARTIAL',minutes=elapsed,decoded_pngs=len(pngs),png_array_checks=checks,reloads=reloads),ensure_ascii=False))

if __name__=='__main__':main()
