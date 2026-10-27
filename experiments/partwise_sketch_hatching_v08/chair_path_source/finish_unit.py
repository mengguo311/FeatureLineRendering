"""Package the completed frozen experiment; no new renders or scientific changes."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,datetime
from PIL import Image
from run_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_004';CODE=Path(__file__).parent

def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)

def main():
    verify_unit(UNIT)
    summary=json.loads((UNIT/'SAVED_SUMMARY.json').read_text());audit=json.loads((UNIT/'OUTPUT_AUDIT.json').read_text())
    gates=json.loads((UNIT/'SOURCE_GATE_AUDIT.json').read_text());p=json.loads((UNIT/'PROTOCOL.json').read_text())
    copy=json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())
    assert sha(runtime.ROOT/'units/unit_003/delivery/MANIFEST.json')==copy['parent_manifest_sha256']
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T10:27:36.844057+09:00')).total_seconds()/60
    testlog=(UNIT/'logs/003_green_integration.log').read_text();assert 'OK' in testlog
    cold=json.loads((UNIT/'cold_highlight/RELOAD_RECEIPT.json').read_text());assert cold['array_equal']
    next_step='下一次只读审查后，优先把现有Chair的第二作者区域（上背region5）纳入可保存参数编辑，检验一次明确的方向编辑在同一固定整椅底上的可见性与非目标路径隔离，并输出实际换相机图。先核查既有region5源绑定是否足够；若不足，明确采用传统代理控制并保留原GS连接为可选层，不扩UNKNOWN、不宣称完整语义或复制本轮稀疏来源证书。不要继续增加同一路径样本或重开Lego平滑阶梯。'
    why='当前已有座面编辑、真实半周/缩放以及有界路径来源查询；新证据暴露空集合和弱后侧近消失，不能靠证书数量变成画质优势。第二独立作者区域的可操作编辑更接近原始分部资产目标，仍须下一次只读审查和父级冻结。'
    states=[];effects=[];globalrows=[]
    for view,v in summary['views'].items():
        st=v['states'];states.append([view,v['unique_pixels'],v['raw_events'],st.get('supported_sample',0),st.get('depth_rejected',0),st.get('no_eligible_source',0)])
        for stroke,h in v['highlights'].items():
            if not h['selected_original_ids']:continue
            m=h['source_change'];effects.append([view,stroke[-3:],h['selected_original_ids'],f'{m["raw_total_L1"]:.6f}',f'{m["target_full"]["raw_L1_mean"]:.6f}',f'{m["far_other"]["raw_L1_sum"]:.9f}',f'{m["far_background"]["raw_L1_sum"]:.9f}'])
        g=v['global_hybrid_absolute'];globalrows.append([view,f'{g["far_other"]["raw_L1_sum"]:.3f}',f'{g["far_background"]["raw_L1_sum"]:.3f}',f'{100*g["far_raw_fraction"]:.2f}%'])
    errors={k:max(v[k] for v in summary['views'].values()) for k in ('max_trace_RGB_error','max_support_error','max_own_post_error')}
    report=f'''# Unit004：可查询的新座面路径来源与固定原GS核高亮

**执行与资产交付完成；科学范围为PARTIAL的采样来源可用性，不是画质、完整附着或跨视角持续支持认证。** 六条固定座面笔触现在可以按稳定stroke ID、锚点和相机查询原始CPU接受事件，并保存原核高亮后换相机重渲染。四条路径得到非空BUILD集合，两条为空；空集合没有补选。前侧选中的末尾077路径在弱后侧几乎不可见，限制直接保留。

直接查看：[整物体分层](media/WHOLE_LAYERS.png)、[038路径查询定位与高亮](media/PATH_240801725082000038.png)、[077后侧近消失](media/PATH_240801725082000077.png)、[019空集合](media/PATH_240801725082000019.png)、[可运行包](delivery/README_ZH.md)。每个PATH图左列为实际原GS，中列红线仅为明确标注的自身路径定位overlay，右列才是完整原核重新渲染的真实源颜色覆盖。没有对差分加对比度、补画高亮或把overlay当GS结果。

## 实际应用和整物体观感

三个实际相机61°/24°、241°/24°、241°/60°均384×384、距离5.1，全部已经曝光，不称训练未见。原GS、纸底、墨、hybrid及传统proxy均重新渲染；57个正常输出数组逐值恢复unit003首尾及unit002高后侧的已核验结果。当前没有重跑影片或新增视频，unit003半周/缩放仍属于前一单元。

目视检查覆盖整椅分层及全部六条路径的三相机对照。整椅仍可辨，扶手开口和主要腿部保留；弱后背密线、腿部波纹、高后侧小孔和碎线未改善。原GS高亮是稀疏的青蓝色斑点，远非完整连续笔触着色，整图中有的变化很弱。传统代理继续表达同样主要形体，没有提出GS画质优势。本轮的可用性是能查询、定位和重放来源控制，而非改善这些既有图像缺陷。

## 冻结范围与数据契约

复制前核验56份所需文件，评价前冻结98项输入和23份源码、18个材料锚点及三个相机。父级DECISION、科学源码和原输入保持。6条stroke ID继承unit003的座面均匀排序样本，取各自存储线段总弧长0.2/0.5/0.8；缺口不插值。当前座面共97条/1061段，仍有91条路径及每条未采样区段不获认证。高亮不会附着到后续重生成路径；错误资产的CLI调用实际被拒绝，返回码1按预期保留。

原256690零起始PLY行/顺序、位置、协方差、opacity及完整SH不变；27873行座面责任、UNKNOWN170281不变。全部路径/ID/face/bary、样式、owner-only座面支持、其他区域capsule及轮廓规则、1px/AA2/0.004遮挡容差、全局.95纸底和S不变。高亮只在原GS求值颜色的副本中覆盖，未筛掉原核、衰减opacity、重算标签或写回SH/PLY。

每锚点保留所有正权重双线性邻居像素，先去重真正渲染的整数像素，再保存锚点CSR引用。原ID、alpha、T、alpha*T、深度、像素插值权重、原区域强度、自己的AA墨和资格标志均保存。一个像素可被多个锚点引用，这是显式重复引用，不作为独立观测；同一原核也可支持多条路径。前侧四个非空集合的大小93/208/242/157，总计700个不同原行。本轮没有物理所有权或唯一表面绑定。

连续锚点先以当前代理首交和0.004容差判可见；资格另要求该路径自身原生像素AA墨>1/255、整数像素代理region4、源alpha≥.5、源median与同一像素代理深度差≤.08、事件深度差≤.06、原座面区域强度>0。后两个源深度阈值沿用v05诊断，和0.004墨遮挡容差分开记录，不是物理误差界。没有按结果调阈值。未通过的事件仍完整保留；不能因邻近笔触或其他前景高斯有贡献就标支持。

{table(['相机','去重像素','原接受事件','支持锚点','深度拒绝','可见但无合格来源'],states)}

共54个锚点-相机观测不是54条独立路径。当前37个supported_sample只表示上述稀疏代理条件，不替代整条路径证明。区域S继续为sum(alpha*T*s)，未变成逐路径门控；其他部位墨仍只有代理来源。

## 固定集合的真实颜色控制与远区变化

只从前61/24的合格事件取每条路径原ID并集，固定混合强度0.5、颜色[.02,.4,1]；没有top-K、最小曝光优化、后侧补选或逐视角归一。六条集合为末尾000:93、019:0、038:208、058:242、077:157、096:0。两个空集合在三个相机均为实际无变化输出，零泄漏不算成功。

以下为每条非空集合高亮相对原GS的自然强度，末尾编号仅为显示缩写，完整ID在资产和图名中。

{table(['相机','路径末尾','核数','总raw L1','座面mean L1','远其他raw L1','远背景raw L1'],effects)}

077在弱后侧总raw L1只有0.000319762左右，接近不可见；其远区比例约3.9888%来自极小总量，不能靠这个比例或极小绝对值宣布局部控制通过。高后侧077远其他raw L1约0.107253，最大单项远区影响仍如实保留。这里远区使用既有座面作者掩码与固定2px带，并不是v05的稀疏路径意图掩码，也不是独立真值；没有用这些小泄漏数值修复v05稀疏失败。高亮本身不应被解释为完整笔触范围的精确选择。

另列正常全局hybrid相对原彩色GS的绝对远区变化，不能与高亮增量或局部编辑零增量相抵：

{table(['相机','远其他raw L1','远背景raw L1','远区占总变化'],globalrows)}

这些大变化来自已冻结的全局纸底和全物体墨，既不是本轮局部高亮泄漏，也不是自动语义成功。没有匹配预算的邻近/null对照，因此没有关联优越性、独立几何或质量收益主张。

## 独立读回、重载与实际命令

新行为测试实际RED rc1（缺path_source模块），3组GREEN rc0；覆盖双线性重复像素与边缘、无自身墨时不能借其他路径、保留拒绝事件、原ID界限、空集合和未采样查询。科学三相机及保存结果审计全部rc0。错误资产查询的预期拒绝rc1与RED分开记录；未采样的真实第2条座面路径返回not_sampled。

trace开/关每相机6个输出数组逐值相同。alpha/fullSH RGB/S重建均在1e-6内；跨三个相机最大RGB误差{errors['max_trace_RGB_error']:.3g}，S误差{errors['max_support_error']:.3g}，自身post-S墨重建误差{errors['max_own_post_error']:.3g}。独立审计逐项核对18510条CSR事件引用和其自身墨，没有借邻线；另从原T/depth事件链独立恢复整数像素median与资格门，核对原行strength。54个查询读回，66张主要PNG逐像素等于数组。

包内source_query在新进程实际查询并与独立读回完全相同；弱后侧另从原PLY冷重算原GS与93核高亮，图像逐值相同。该冷重载只验证新查询/高亮行为，没有重跑旧bootstrap或整段影片。原source、alpha及几何深度保持。全部编译子返回码、父级run_logged回执和实际命令保存在logs与renders/build/COMPILE.json、cold_highlight/build/COMPILE.json；最终外层engine返回码由父级记录，本单元不伪造为0。

仅本机Linux CPU，最多两核亲和、单数值线程、串行、CUDA为空；无安装、下载、GPU、训练、嵌套模型、旧目录写入、push/merge。没有远程或跨平台认证。源码和包内资产为相对数据路径；输出守卫仍限制v08 HDD。科学seal=false，不用工程通过替代科学验收。

## 保留结论与下一步

v05 far8.044%/31腐蚀像素/4.49%原作者区域变化失败，v07十一轮整物体负结果/H交叉角塌缩/zero_step_cycle，unit001–003的143/UNKNOWN和unit003共同可见自身墨跌落全部保留。当前三静态相机不构成新时序认证。

NEXT=continue。{next_step}

{why}

报告生成时距本轮执行授权约{elapsed:.2f}分钟；12:25禁启新单元、12:45收尾、13:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    docs=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v08/docs/partwise_sketch_hatching_v08')
    (docs/'unit_004.md').write_text(report)
    js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why))
    status=dict(execution_state='completed',stage='sparse_path_query_and_saved_source_highlight_audited',
        scientific_verdict='PARTIAL sampled source-query capability. Four nonempty BUILD selections, two empty; path077 nearly invisible at weak rear. No quality, physical-ownership or temporal superiority.',
        gaussian_link_progress='Original256690 rows/fullSH/geometry/opacity and27873 seat weights/UNKNOWN170281 unchanged.6 paths/18 anchors, full-T CSR and saved original-kernel color highlights;91 seat paths and unsampled intervals uncertified.',
        artifacts=dict(package='delivery',whole_layers='media/WHOLE_LAYERS.png',path_panels='media/PATH_*.png',support='delivery/support',report='REPORT_ZH.md',audit='OUTPUT_AUDIT.json'),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=3,wrong_asset_expected_rejection_returncode=1),
        sampled_paths=6,total_seat_paths=97,anchors_per_view=18,cameras=3,highlight_counts=summary['highlight_counts'],
        highlighted_unique_source_ids=700,normal_arrays_restored=57,raw_CSR_events_checked=18510,png_array_checks=66,
        fresh_process_query_exact=True,cold_highlight_exact=True,new_video=False,
        source_scope='CPU fullSH3 accepted pixel contribution; many-to-many proxy-conditioned support, not native Gaussian hatching',
        actual_commands='EXECUTION_RECORDS.json; logs/*.start.json,*.json,*.log; compiler COMPILE.json files',
        blockers=[],limitations=['Two empty selections','Sparse anchors only','Weak rear path077 nearly absent','Existing whole-object clutter and temporal failures unchanged','Local CPU only'],
        scientific_seal=False,last_engine_exit_code='UNKNOWN',last_engine_note='Outer engine completion belongs to parent; child command receipts are recorded separately.',
        branch='partwise-sketch-hatching-gaussian-link-v08',next_action='continue',report_utc=runtime.now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status)
    readme='''# Chair：局部编辑、路径来源查询与保存高亮

本包包含可运行的Chair整椅座面编辑器，以及6条固定新路径/18个锚点的来源查询。实际输出为PARTIAL：4条路径有非空前侧原ID集合，2条为空；077在弱后侧近乎不可见。来源是CPU原GS接受事件和代理条件，不是物理所有权或整条曲线认证。91条座面路径和未采样区段不获认证。

打开 `evidence/WHOLE_LAYERS.png` 查看实际整物体分层，`evidence/PATH_*.png` 查看原GS、红色路径定位overlay、真实原核高亮。右列是真实完整GS渲染，中列overlay只定位。正常整椅与旧结果逐值相同；稀疏高亮不构成画质改善。

依赖已有Python、NumPy2.2.6、SciPy1.15.3、Pillow12.2.0、plyfile1.1.5、Open3D0.20.0和g++。首次输出须不存在并位于v08 HDD；运行时最多两核、单数值线程、无CUDA。只有Chair数据，本机CPU验证，未认证远程/跨平台。

```bash
CHAIR_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
CHAIR_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_004/delivery
CHAIR_RUN=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_chair_source_001

# 实际按稳定stroke ID查询；另可用fraction 0.2或0.8及三个已保存相机。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/source_query.py" query --asset "$CHAIR_PACKAGE/assets/whole_spacing" --evidence "$CHAIR_PACKAGE/support" --view orbit_61_24_5.1 --stroke-id 240801725082000000 --fraction 0.5 --out "$CHAIR_RUN/query"

# 从保存的同一原ID集合，冷重算弱后侧完整原GS和高亮；原文件/opacity/SH不改。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/source_query.py" highlight --asset "$CHAIR_PACKAGE/assets/whole_spacing" --evidence "$CHAIR_PACKAGE/support" --view orbit_241_24_5.1 --stroke-id 240801725082000000 --out "$CHAIR_RUN/highlight"

# 未采样的真实座面路径返回not_sampled，不借区域S伪造来源。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/source_query.py" query --asset "$CHAIR_PACKAGE/assets/whole_spacing" --evidence "$CHAIR_PACKAGE/support" --view orbit_61_24_5.1 --stroke-id 240801725082000001 --fraction 0.5

# 已有参数编辑器仍可用；支持angle/spacing/length。原非目标路径保留。
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" edit --asset "$CHAIR_PACKAGE/assets/whole_baseline" --spacing 0.0675 --out "$CHAIR_RUN/edited"
"$CHAIR_PY" -B "$CHAIR_PACKAGE/code/whole_asset.py" render --asset "$CHAIR_RUN/edited" --azimuth 241 --elevation 24 --distance 5.1 --size 384 --out "$CHAIR_RUN/edited_image"
```

包内6个采样ID为240801725082000000、240801725082000019、240801725082000038、240801725082000058、240801725082000077、240801725082000096。三个相机名为orbit_61_24_5.1、orbit_241_24_5.1、orbit_241_60_5.1。019和096的前侧高亮集合为空，后侧不会补选。任何后续编辑产生的新身份必须另取样，当前证据绑定资产manifest，不能直接套用。

`support/*.npz`保存原ID/alpha/T/weight/深度/像素插值权重、CSR、资格和拒绝记录。多个锚点可引用同一事件，不能当独立观测。源强度字段表示座面S责任；整物体纸底覆盖全部原行，不能据region strength=0声称UNKNOWN行未被全局纸底覆盖。

原PLY全部256690行及顺序、位置、协方差、opacity、完整SH保持；原区域UNKNOWN170281不变。source_query只对求值颜色作固定0.5混合高亮。座面S仍为区域责任；其他部位和轮廓为代理支持。不同样本的原核可以重叠，不是独占绑定。

本轮没有新视频；unit003原半周/缩放与跌落负证据独立保留。v05稀疏失败、v07全部负结果/H交叉混杂/zero_step_cycle、unit001–003的143/UNKNOWN均未被本轮工程通过修复。详细范围、自然强度和绝对远区变化见 `evidence/REPORT_ZH.md`。
'''
    (UNIT/'delivery/README_ZH.md').write_text(readme)
    ev=UNIT/'delivery/evidence';ev.mkdir(exist_ok=True)
    for f in (UNIT/'media').iterdir():
        if f.is_file():shutil.copy2(f,ev/f.name)
    for name in ('REPORT_ZH.md','STATUS.json','SAVED_SUMMARY.json','OUTPUT_AUDIT.json','SOURCE_GATE_AUDIT.json','PROTOCOL.json','PROTOCOL_LOCK.json','SOURCE_LOCK.json','INPUT_LOCK.json','DECISION.json'):
        shutil.copy2(UNIT/name,ev/name)
    for name in ('QUERY.json',):shutil.copy2(UNIT/'query_reload'/name,ev/'ACTUAL_QUERY.json')
    shutil.copy2(UNIT/'cold_highlight/RELOAD_RECEIPT.json',ev/'COLD_HIGHLIGHT_RELOAD.json')
    # Direct single-view outputs retain full original pixels for inspection.
    for c in p['cameras']:
        folder=UNIT/'renders'/c['view'];dest=ev/c['view'];dest.mkdir(exist_ok=True)
        for f in folder.glob('*.png'):shutil.copy2(f,dest/f.name)
        for name in ('RENDER_RECEIPT.json','PIXEL_GATE_READBACK.json'):shutil.copy2(folder/name,dest/name)
    files={str(f.relative_to(UNIT/'delivery')):sha(f) for f in (UNIT/'delivery').rglob('*') if f.is_file() and f.name!='MANIFEST.json'}
    js(UNIT/'delivery/MANIFEST.json',dict(files=files,created_utc=runtime.now(),scope='Runnable query/highlight and inherited whole editor; science remains PARTIAL'))
    decoded=0
    for f in (UNIT/'delivery').rglob('*.png'):
        with Image.open(f) as im:im.load();decoded+=1
    for rel,h in files.items():assert sha(UNIT/'delivery'/rel)==h
    js(UNIT/'PACKAGING_AUDIT.json',dict(package_files=len(files),all_PNG_decoded=decoded,all_package_hashes_equal=True,
        package_manifest_sha256=sha(UNIT/'delivery/MANIFEST.json'),remote_verification='not performed',elapsed_minutes=elapsed))
    print(json.dumps(dict(report=str(UNIT/'REPORT_ZH.md'),files=len(files),PNG_decoded=decoded,elapsed_minutes=elapsed)),flush=True)
if __name__=='__main__':main()
