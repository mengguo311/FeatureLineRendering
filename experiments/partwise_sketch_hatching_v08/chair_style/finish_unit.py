"""Package the completed style test and its limitations; no new science."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,datetime
from run_view import verify
UNIT=runtime.ROOT/'units/unit_006';CODE=Path(__file__).parent
def main():
    verify(UNIT);a=json.loads((UNIT/'OUTPUT_AUDIT.json').read_text());v=json.loads((UNIT/'FINAL_VERIFICATION.json').read_text());m=json.loads((UNIT/'BUILD_MATCH.json').read_text())
    started=datetime.datetime.fromisoformat('2026-10-27T02:25:00.284855+00:00');elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
    verdict='PARTIAL authored style capability: cleaner selective hatching with recognizable whole Chair, but flatter frame/blank bands and inherited contour holes remain. No whole-object quality winner or Gaussian advantage established.'
    next_step='下一次只读审查优先评估一条有界的固定结构曲线应用路线：从BUILD原GS/代理证据确认椅背内框或座面边缘，记录作者引导成本，保存三维附着曲线并在同一预设及弱后侧/新增视角实际渲染有无曲线。当前轮廓仅含外轮廓和深度跳变，无法表达所有必要结构；不得把粗作者分区边界自动当作真实棱边，不改原GS/代理、不逐DEV修线、不靠删除小孔或继续间距扫描制造收益。若无法获得可信附着，保留UNKNOWN和当前可用资产。'
    status=dict(execution_state='completed',stage='saved_selective_style_four_camera_outputs_cold_reload_and_interruption_readback_complete',
        scientific_verdict=verdict,gaussian_link_progress='Original256690 rows/geometry/opacity/fullSH/order and UNKNOWN170281 unchanged. All-row .95 render-time paper; original27873-row region4 alpha*T S retained. Region5 proxy-only; no new-path source certification.',
        artifacts=dict(package='delivery',natural='media/NATURAL_COMPARISON.png',matched='media/MATCHED_COMPARISON.png',layers='media/WHOLE_LAYERS.png',audit='OUTPUT_AUDIT.json',verification='FINAL_VERIFICATION.json'),
        tests=dict(expected_RED_returncode=1,GREEN_returncode=0,test_groups=3),cold_reload=v['cold_reload'],
        retained_hidden_region_files=[1,2,3],new_active_paths={r:a['paths']['selective'][r] for r in ('4','5')},
        new_scene_outputs=5,reused_reference_views=3,unique_cameras=4,newly_reserved_camera='orbit_151_36_5.1',new_video=False,
        build_match=m,png_array_checks=v['png_array_checks'],compiler_records=v['compiler_records'],
        interruption=dict(tool_outer_exit_code=143,wrapper_returncode='UNKNOWN',child_returncode='UNKNOWN',payload_verified=True,record='INTERRUPTION_008.json'),
        actual_commands='EXECUTION_RECORDS.json and logs/*.start.json/*.json/*.log; each build/COMPILE.json',
        blockers=[],limitations=['Style/scope change, no isolated mechanism gain','Authored regions are not complete semantic frame/upholstery parts','Flatter frame and blank back transition','Inherited proxy contour holes and discontinuities','No temporal/physical/semantic certification','No new-path source certificate'],
        scientific_seal=False,last_engine_exit_code='UNKNOWN',last_engine_note='Outer engine completion belongs to parent; command and compiler statuses remain separate.',
        branch='partwise-sketch-hatching-gaussian-link-v08',next_action='continue',report_utc=runtime.now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status);js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why='The single frozen style is operable but exposes a missing structural-line layer; further density or certificate tuning would not address the observed shape limitation. Requires the next read-only review and parent freeze.'))
    coverage=['| 相机 | 座面覆盖 参照/候选 | 上背覆盖 参照/候选 | 排线增量L1 参照/候选 |', '| --- | --- | --- | --- |']
    absolute=['| 相机 | 候选相对原GS远其他L1 | 远背景L1 | 远区占总变化 | 风格更换远其他增量L1 |','| --- | --- | --- | --- | --- |']
    for view,x in a['views'].items():
        cov=lambda arm,r:x['regions'][arm][r]['coverage']*100
        coverage.append(f"| {view} | {cov('reference','4'):.2f}% / {cov('selective','4'):.2f}% | {cov('reference','5'):.2f}% / {cov('selective','5'):.2f}% | {x['reference_increment']['natural_L1']:.3f} / {x['selective_increment']['natural_L1']:.3f} |")
        g=x['global_absolute']['selective'];d=x['style_scope_delta']
        absolute.append(f"| {view} | {g['far_other']['raw_L1_sum']:.3f} | {g['far_background']['raw_L1_sum']:.3f} | {g['far_raw_fraction']*100:.2f}% | {d['far_other']['raw_L1_sum']:.3f} |")
    paths=['| 区域 | 路径 参照/候选 | 段数 参照/候选 | 世界长度 参照/候选 |','| --- | --- | --- | --- |']
    for r in ('4','5'):
        old=a['paths']['reference'][r];new=a['paths']['selective'][r]
        paths.append(f"| {r} | {old['paths']} / {new['paths']} | {old['segments']} / {new['segments']} | {old['length']:.6f} / {new['length']:.6f} |")
    report='''# Unit006：可保存的轮廓与两区域长疏排线预设

**执行交付完成；科学结论为PARTIAL，不升级为整物体质量赢家。** 这次形成可加载、继续编辑和冷重渲染的独立预设，实际改变整椅表达层次。没有再做Lego载体/方向微调。

[自然完整对照](media/NATURAL_COMPARISON.png) · [BUILD配平诊断](media/MATCHED_COMPARISON.png) · [完整分层](media/WHOLE_LAYERS.png) · [资产及命令](delivery/README_ZH.md)

## 实际整图判断

已查看四相机完整自然/配平面板、完整source/paper/contour/ink/hybrid/proxy分层，以及前侧、弱后侧、高后侧和新增后视角原尺寸图。候选去掉高度区密线后，腿部和扶手的重复波纹明显减少，两个作者区域仍有清楚可见的排线，主要椅腿、扶手开口及座背轮廓仍可辨。作为粗略的选择性排线插画预设可以使用。

代价是框架体积更平、座面侧缘和椅背下半部出现较大空白；这不是恢复完整框架/软包语义。新增151°/36°视角清楚暴露背部下缘两个轮廓小孔，原尺寸源GS中该位置并非相同的清楚孔洞；高后侧座面小孔/断线也仍在。它们已经存在于固定代理轮廓，不能说排线预设修复了几何。长线仍有代理表面弯折，高后侧上背仍近横向短段。自然图看起来更简洁，配平图也将线集中到两个作者区域，但空白与形体简化同时存在，没有足够依据宣称整物体赢家。传统proxy同样表达这些主要形体，GS混合仍主要提供淡灰纸底和座面衰减，未建立质量优势。

## 冻结的风格与作用范围

参照为unit005 angle资产，作为已曝光功能参照，不因它最新就认定最好。新预设关闭region1–3排线显示，三个路径文件逐字节保留；全物体轮廓规则保持。region4保持95°/xy、spacing=.0675、ink_strength=.35，仅length=.22→.44；region5保持25°/xz、ink_strength=.45，spacing=.045→.0675、length=.22→.44。两区width=1、单层、原世界切片相位和gap=.035保持。没有扫描或看DEV后修改参数，也没有新增点击/面标签；使用原作者分区与方向，人工配置为决定中一次固定的显示掩码和两组参数，原历史标注成本没有重新估算为零。

这是STYLE/SYSTEM比较，联合改变显示范围、间距和长度；路径数量、弧长相位及截断的响应不能独立归因于某一个参数。新身份不复用旧来源证书，face/bary仍在原代理面，两个新区域owner-only掩码分别16/32。

'''+ '\n'.join(paths)+'''

原256690行及行序、位置/协方差/opacity/完整SH、代理几何和作者标签不变；UNKNOWN170281、原27873行座面责任权重不变。固定全局.95纸底是所有原核求值颜色的可逆覆盖，不是标签传播；座面S为真实原行alpha*T贡献，region5墨仍只由代理承载。两个启用区域的178条新路径没有逐路径原核所有权证明，也不保证每个视角全部可见。

## 覆盖与实际墨量

以下覆盖按固定作者区域和该区域自身墨计算；座面采用post-S，上背采用代理墨。region1–3显示墨覆盖为零是预先指定的风格范围，不作为自动干净度成功。

'''+ '\n'.join(coverage)+f'''

BUILD实际排线增量为参照{m['natural_increment_raw_L1']['reference']:.6f}、候选{m['natural_increment_raw_L1']['selective']:.6f}，候选仅为参照约{m['factors']['reference']*100:.2f}%。不能把这一大幅少画隐藏成算法改进。附加配平图使用参照系数{m['factors']['reference']:.9f}、候选1.0；仅线性缩放自然合成相对同一paper+contour的RGB残差，轮廓和纸底不缩放。没有重新选择路径或逐DEV归一，也不是原生墨强度参数重渲染。BUILD等总量不保证DEV等量，更不保证相同任务或质量。

## 全局与远区变化

'''+ '\n'.join(absolute)+'''

这里远区沿用座面region4和固定2px带，仅便于与历史口径并列。候选相对源GS的大变化包含固定全物体纸底；风格更换的远其他变化包含有意关闭region1–3及改变region5，不能叫局部编辑泄漏或零泄漏成功。所有旧目标、掩码及旧失败原样保留，未扩大容差带。

## 真实执行与冷重载

评价前冻结DECISION引用、PROTOCOL、科学源码、输入和四个相机；61/24为BUILD，241/24和241/60明确已曝光，151/36在本轮输出前预留，不称GS训练未见。三个参照数组核验后复用并标注reused unit005；候选四相机以及新增相机参照共5次新场景渲染，实际从原PLY重算GS、S和代理墨。没有新视频，也没有跨资产迁移unit003时间稳定证据。

预期RED rc1为缺style_asset模块，随后3组GREEN rc0，覆盖隐藏层与轮廓/S合成、真实资产保存/锚点/新身份、继续编辑非目标文件保持、非法预设拒绝。包内preset在新进程恢复同样五个路径文件；包内edit无操作保存保持预设及路径。非零参数编辑由实际测试验证其目标重生成与其他路径不变，不作为额外画质评价臂。

包内render从原PLY冷重渲染弱后侧，19数组逐值一致。独立读回核对全部6次新渲染（含冷重载）的60张PNG与数组、所有渲染payload哈希和12项实际编译返回码；科学相机的稀疏trace另由完整原行权重重建S/alpha。原source/paper/S/轮廓/标签/深度在各风格间逐值一致。这是CPU采样记录与工程复现，不是全图逐核或新路径物理认证。

高后侧命令008的工具外层实际退出143，wrapper/child返回码UNKNOWN，原start/log及缺失最终回执保持。已有完整渲染receipt、数组、图片和编译回执，经独立核验后采用；没有重画该科学输出，也没有补造008成功记录。原因UNKNOWN，见INTERRUPTION_008.json。父级外层engine最终返回码仍由父级记录。

仅本机Linux CPU，最多两核亲和、数值线程1、串行、CUDA为空；无安装、下载、GPU、训练、嵌套模型、旧目录改写或push/merge。文件SHA与图像全解码为本机核验，未做远程/跨平台认证。科学源码和父级DECISION不变；事后读回/报告代码另列HANDOFF_SOURCE_LOCK。

保留v05 far8.044%/31腐蚀像素/4.49%原区域变化失败、v07十一轮整物体负结果/H交叉角塌缩/zero_step_cycle、v08原143/UNKNOWN及共同可见墨跌落、unit004空集合和077弱后侧近消失。当前全局风格任务不能倒推它们通过。

## 后续

NEXT=continue。'''+next_step+f'''

报告时距执行授权约{elapsed:.2f}分钟；12:25禁止新单元、12:45科学收尾、13:00硬停止。
'''
    (UNIT/'REPORT_ZH.md').write_text(report)
    readme='''# Chair选择性长疏排线预设

本包提供一个可保存、加载、继续编辑及真实换相机渲染的Chair资产。它是粗略插画预设，PARTIAL；框架更简洁但更平，代理轮廓小孔与空白带未修复，不是整物体质量赢家。

[自然对照](media/NATURAL_COMPARISON.png) · [完整分层](media/WHOLE_LAYERS.png) · [配平诊断](media/MATCHED_COMPARISON.png) · [报告](evidence/REPORT_ZH.md)

依赖既有Python、NumPy2.2.6、SciPy1.15.3、Pillow12.2.0、plyfile1.1.5、Open3D0.20.0和g++。入口禁用CUDA、限制最多两核亲和与单数值线程；不安装依赖。包内源码/资产/数据使用相对数据链接，输出必须为v08 HDD内尚不存在的新目录，旧包只读。

```bash
V08_PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python
V08_PACKAGE=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/units/unit_006/delivery
V08_OUT=/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08/user_selective_001

# 从参照生成并保存本轮固定预设（包内CLI已实际验证）
"$V08_PY" -B "$V08_PACKAGE/code/style_asset.py" preset --asset "$V08_PACKAGE/assets/reference" --out "$V08_OUT"

# 从保存资产冷渲染弱后侧；更换camera为0/2/3.json可输出其他冻结相机
"$V08_PY" -B "$V08_PACKAGE/code/style_asset.py" render --asset "$V08_OUT" --camera "$V08_PACKAGE/cameras/1.json" --out "${V08_OUT}_rear"

# 继续只编辑上背长度；这是使用示例，不是本轮额外画质评价臂
"$V08_PY" -B "$V08_PACKAGE/code/style_asset.py" edit --asset "$V08_OUT" --region 5 --length 0.5 --out "${V08_OUT}_edited"
```

edit支持region4/5的angle、spacing、length，保留其他区域路径字节和当前显示预设。region1–3文件仍在，当前预设不显示其排线；不是删除原源或重新分部。长度/间距改变会重生成目标路径和身份，不能继承旧路径证书。要回看完整旧风格，请渲染assets/reference。

原256690个PLY零起始行、位置/协方差/opacity/fullSH/行序和绑定不变，UNKNOWN170281不被重分类。全局.95纸底为全部原GS核的渲染时颜色覆盖；座面仍用27873原行的alpha*T区域S门控代理墨，上背墨为proxy-only。保存的controls/upper_back是独立原行颜色控制，使用parts_asset.py source-render/query，未绑定新路径。本轮未重跑其旧高亮实验，原证据属于unit005。style_asset query保留旧座面绑定查询字段，其中paper_strength为历史区域权重，当前实际全局纸底以WHOLE_PRESET为准。

三个旧参照视角明确复用；候选四视角和新增相机参照均为真实新渲染。冷重载19数组一致；本轮没有影片、原生Gaussian笔触、自动语义、物理所有权、GS画质优势或跨平台认证。科学seal=false。008外层143和子UNKNOWN及独立payload核验全部保留。详细命令回执、输入/源码锁和负结果见evidence。
'''
    (UNIT/'delivery/README_ZH.md').write_text(readme)
    for f in (UNIT/'media').glob('*.png'):
        target=UNIT/'delivery/media'/f.name;target.parent.mkdir(exist_ok=True);shutil.copy2(f,target)
    for name in ('REPORT_ZH.md','STATUS.json','NEXT.json','DECISION.json','PROTOCOL.json','SOURCE_LOCK.json','INPUT_LOCK.json','INPUT_SEAL.json','PROTOCOL_LOCK.json','BUILD_MATCH.json','BUILD_LOCK.json','OUTPUT_AUDIT.json','FINAL_VERIFICATION.json','INTERRUPTION_008.json','INPUT_COPY_RECEIPT.json'):
        dst=UNIT/'delivery/evidence'/name;dst.parent.mkdir(exist_ok=True);shutil.copy2(UNIT/name,dst)
    extra={}
    for name in ('assess_saved.py','finish_checks.py','finish_unit.py'):
        extra[name]=sha(CODE/name);dst=UNIT/'delivery/audit_code'/name;dst.parent.mkdir(exist_ok=True);shutil.copy2(CODE/name,dst)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',extra)
    records=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        end=Path(str(start).replace('.start.json','.json'));record=json.loads((end if end.exists() else start).read_text())
        record['receipt_file']=str(end.relative_to(UNIT)) if end.exists() else None
        if start.name.startswith('008_'):record['tool_outer_exit_code']=143
        records.append(record)
    js(UNIT/'EXECUTION_RECORDS.json',dict(snapshot_utc=runtime.now(),commands=records,compiler_records=v['compiler_records'],final_engine_exit_code='UNKNOWN',note='Current packaging wrapper may still be pending at this snapshot; inspect raw receipt after completion.'))
    for f in (UNIT/'logs').iterdir():
        if f.is_file():dst=UNIT/'delivery/evidence/logs'/f.name;dst.parent.mkdir(exist_ok=True);shutil.copy2(f,dst)
    for name in ('HANDOFF_SOURCE_LOCK.json','EXECUTION_RECORDS.json'):shutil.copy2(UNIT/name,UNIT/'delivery/evidence'/name)
    for rr in list((UNIT/'renders').rglob('RENDER_RECEIPT.json'))+[UNIT/'cold_reload/RENDER_RECEIPT.json']:
        rel=rr.relative_to(UNIT);dst=UNIT/'delivery/evidence'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(rr,dst)
        shutil.copy2(rr.parent/'build/COMPILE.json',dst.parent/'COMPILE.json')
    rootread='''# v08 当前交付：Chair编辑、来源控制与可选插画预设

unit006新增“轮廓＋两作者区域长疏排线”保存预设，实际四视角与冷重载完成。科学PARTIAL：框架密线减少，但体积更平、空白带及代理轮廓小孔仍在，不升级为整物体质量赢家。

[unit006资产/命令](units/unit_006/delivery/README_ZH.md) · [自然对照](units/unit_006/media/NATURAL_COMPARISON.png) · [报告](units/unit_006/REPORT_ZH.md)

[unit005两部位编辑/原GS颜色控制](units/unit_005/delivery/README_ZH.md) · [unit003实际半周/缩放](units/unit_003/delivery/README_ZH.md) · [unit004稀疏路径查询](units/unit_004/delivery/README_ZH.md) · [unit001座面源纸底编辑](units/unit_001/delivery/README_ZH.md)

旧影片和来源证书各属于原资产，没有迁移到新路径。原GS区域连接不等于逐路径所有权；全部旧负结果和143/UNKNOWN保留。后续单元须重新只读审查及父级冻结。
'''
    (runtime.ROOT/'DEMO_README_ZH.md').write_text(rootread)
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_006',units=[f'unit_{i:03d}' for i in range(1,7)],status=status,previous_delivery='units/unit_005/delivery',default_promoted=False))
    doc=CODE.parents[2]/'docs/partwise_sketch_hatching_v08/unit_006.md'
    doc.parent.mkdir(parents=True,exist_ok=True)
    doc.write_text('# Unit006：选择性长疏排线预设\n\nPARTIAL：真实四视角、保存预设与19数组冷重载完成；未建立整物体或GS质量优势。框架更平，旧轮廓孔洞保留。\n\n[完整报告]('+str(UNIT/'REPORT_ZH.md')+') · [运行命令]('+str(UNIT/'delivery/README_ZH.md')+') · [自然对照]('+str(UNIT/'media/NATURAL_COMPARISON.png')+')\n\n008外层143、子UNKNOWN与完整payload独立核验并列保留；非目标路径文件及原源身份固定。\n')
    js(UNIT/'delivery/MANIFEST.json',dict(utc=runtime.now(),scope='Local package content hashes, not scientific seal',files={str(f.relative_to(UNIT/'delivery')):sha(f) for f in sorted((UNIT/'delivery').rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}))
    print(json.dumps(dict(status=status['scientific_verdict'],elapsed_minutes=elapsed,package=str(UNIT/'delivery'))),flush=True)
if __name__=='__main__':main()
