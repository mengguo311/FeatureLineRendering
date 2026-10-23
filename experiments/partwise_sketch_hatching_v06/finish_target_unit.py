"""Post-result unit008 readback/report; frozen science and older units untouched."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,output_guard,js,sha,now
from pathlib import Path
import datetime,json,shutil
import numpy as np
from scipy import ndimage
from run_hybrid import read_npz
from hybrid import edit_metrics

assert UNIT.name=='unit_008'
p=json.loads((UNIT/'PROTOCOL.json').read_text());summary=json.loads((UNIT/'SUMMARY.json').read_text())
validation=json.loads((UNIT/'VALIDATION.json').read_text());replay=json.loads((UNIT/'cold_replay_001/REPLAY_CHECK.json').read_text())
media=json.loads((UNIT/'MEDIA_VALIDATION.json').read_text());author=json.loads((UNIT/'asset/AUTHORING.json').read_text())
binding=json.loads((UNIT/'BINDING.json').read_text());selection=json.loads((UNIT/'SELECTION.json').read_text())
assert all(media['all_frames_decoded_exact']) and replay['all_links_zero_equals_original_GS']
dev=[x for x in summary['records'] if x['kind']=='dev'];build=summary['build']

# Explicit posthoc mask-accounting readback, not a revised evaluation gate.
scope_rows=[];far_rows=[]
for row in summary['records']:
    f=read_npz(UNIT/row['kind']/row['view']/'FRAME.npz');old=f['old_regions'];new=f['regions']
    if row['kind']=='dev':
        scope_rows.append(dict(view=row['view'],old_target_mask={arm:edit_metrics(f['source'],f[arm+'_raw'],old) for arm in ('old','new')},
            new_target_mask={arm:row['metrics'][arm+'_raw'] for arm in ('old','new')}))
    near=ndimage.binary_dilation(new==4,iterations=2);far=~near
    delta=np.abs(f['new_raw']-f['old_raw']).sum(2)
    far_rows.append(dict(kind=row['kind'],view=row['view'],max_far_RGB_L1=float(delta[far].max()),
        far_pixels_above_1_255=int((delta[far]>1/255).sum()),far_pixels_at_least_0_05=int((delta[far]>=.05).sum()),
        raw_far_other_L1=row['changes']['raw']['far_other']['raw_L1_sum'],raw_far_background_L1=row['changes']['raw']['far_background']['raw_L1_sum']))
js(UNIT/'SCOPE_AND_FAR_READBACK.json',dict(utc=now(),old_scope=scope_rows,new_scope_far=far_rows,
    interpretation='Posthoc saved-output readback only. New target reclassifies some previous far pixels; no old gate is changed or re-passed.'))

sel=read_npz(UNIT/'SELECTION.npz')
np.savez_compressed(UNIT/'asset/SOURCE_LINK.npz',**{k:sel[k] for k in ('source_index','original_strength','completed_strength','old_ink_strength','old_paper_strength','unknown_unchanged','region_id_unchanged','conflict_unchanged')})
js(UNIT/'asset/ASSET.json',dict(name=author['asset_name'],source_count=310475,source=p['scene']['source'],
    target_file='TARGET.npz',path_file='PATHS.npz',old_path_file='OLD_PATHS.npz',added_path_file='ADDED_PATHS.npz',
    source_link_file='SOURCE_LINK.npz',M1_binding=str(UNIT/'SOURCE_BINDING.npz'),style=author['style'],
    old_segments=1904,new_segments=2004,old_strokes=351,new_strokes=375,ink_rows=21006,paper_rows=41058,
    link='source_index=unchanged original PLY row; original_strength=new M1 ink responsibility; completed_strength=new appearance permission. Proxy face/stroke IDs are separate.',
    representation=p['scope'],target_scope='Old authored patch plus91 visible BUILD-selected reconstructed faces; not complete semantic bucket.'))
js(UNIT/'ASSET_LOCK.json',dict(files={str(f.relative_to(UNIT)):sha(f) for f in (UNIT/'asset').iterdir()}))

next_step='下一A阶段审查同一支持集的纸底强度上限：固定unit008目标、41058个已许可原行、M1/UNKNOWN、21006行墨责任及全部2004段路径，只比较当前纸底权重与对同一已许可集合施加strength=1的纸色覆盖。先用保存trace区分残留来自已选行未完全替换还是未选行，再在四BUILD冻结一个源RGB实际效果配平系数，保留自然强度，在四DEV完整物体检查后侧照片残留与绝对远区损伤。不能新增核、放宽许可或把q改成语义真值；若满强度同支持集仍斑驳，则报告该支持集的外观容量限制，不继续追白或扫描权重。此处仅推荐，未执行下一实验。'
why='本轮确认一个显著黄色缺口来自作者面漏选，补选在前侧形成可见纸底与排线；但后侧目标内部纸色残留仍约0.272，整体线条仍杂乱。源码把支持证据q同时当纸底替换强度，而外观补全的UNKNOWN行采用强度1。固定同一许可集合的饱和对照可区分证据混合与真正缺少源支持，区别于继续补选、增加核或复试轮廓/明暗。其收益仍必须由完整物体证伪。'
js(UNIT/'NEXT.json',dict(action='continue',recommended_next_step=next_step,why=why,
    preserve='All old targets, bindings, UNKNOWN, sparse failures, v06 negative comparisons and historical interruptions remain immutable.'))

started=datetime.datetime.fromisoformat('2026-10-23T20:13:34.009920+09:00')
elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
sel_start=json.loads((UNIT/'logs/inspect_build_001.start.json').read_text())['utc']
author_minutes=(datetime.datetime.fromisoformat(author['utc'])-datetime.datetime.fromisoformat(sel_start)).total_seconds()/60
maxfar=max(x['max_far_RGB_L1'] for x in far_rows)
lines=['# Unit008：补选修复一个可见风格缺口，整体NPR仍有限','',
    '**执行完成。前侧遗漏面形成了明显的原GS纸底与原ID关联排线，作为独立作者目标变体保留；完整铲斗语义覆盖、干净排线和多数视角整体可读性优势仍未建立。不升级默认，scientific_seal=false。**','',
    '本轮唯一主变量是作者面集合。四个BUILD源图/首交代理/旧标签检查后，在57°/35°/4.9视角手工画一个五边形，只选原region3中可见的91个首交面；旧2030面变为2121面。无隐藏面扩张、几何补洞或DEV选面。旧选择包含的零散非铲斗面没有借本轮删除，故新名称bucket_surface_completion_v1不等于完整物理/语义铲斗。',
    f'新增代理面积0.071599场景单位²，为旧目标面积的{100*author["added_area_world"]/author["old_area_world"]:.2f}%。BUILD可见新增像素为0/0/0/838。选择由助手完成，非用户点击；从首次BUILD检查到选择文件完成约{author_minutes:.2f}分钟，包含代码实现时间，不能当纯人工标注效率。具体五边形、面ID和投影保存在asset/AUTHORING.json及authoring/SELECTION_CHECK.png。','',
    '旧351条stroke/1904段全部face/bary/world/layer/visibility逐值保留。只在新增面按原35°方向、0.06间距、0.12长度、0.035间隙、1px线宽及原交叉层生成24条/100段，合计375条/2004段。旧路径仍按旧标签处理可见性，新路径按新目标处理；两者在2×子像素取max后降采样，再乘新原ID责任。没有启用unit005补间隙、unit006明暗或unit007轮廓。','',
    f'协议SHA256 `{sha(UNIT/"PROTOCOL.json")}`。{validation["input_hashes_checked"]}份输入、目标、源代码和相机在重算连接和评价前冻结。没有评价后改参数、改目标或修改实现。','',
    '## 原Gaussian连接与旧结果保留','',
    '使用相同12个BUILD的完整已接受alpha×T trace、采样权重、proxy_face和深度资格，只把新增面对应的作者标签3改为4；未复用旧聚合区域分数作为新证据。旧标签分支逐值恢复原M1。新目标重新累积12份全像素footprint，按旧阈值形成外观许可；旧footprint分支逐值恢复unit004选择。',
    '墨责任原行20122→21006；纸底许可39474→41058，其中新M1的UNKNOWN行外观许可20052。新M1 UNKNOWN195600→195279，冲突1755→1545；旧M1与195600个UNKNOWN文件原封保存。合并人工区域能改变冲突，这不是语义准确率提升。外观许可不把UNKNOWN改成标签。原310475行身份、顺序、中心、协方差、opacity、完整SH和PLY文件未改。','',
    '## 完整物体实际观察','',
    '已检查四个完整物体自然/配平面板、独立墨层和全部九相机短弧。61°两前侧视角中，原来大块黄色照片面被纸底和排线替换，风格范围明显更完整；不是仅差分图才看得见。配平后该补选面仍有可见笔触。后侧纸底也略改善，但黄灰斑块、短线和交叉网格仍在；没有形成干净、整体稳定优于旧系统的NPR。这是有限视觉检查，不是独立偏好研究。','',
    '| DEV视角 | 新增面像素 | 新增面纸色残留mean旧/新 | 新增面S均值旧/新 | 新增面可见墨覆盖自然/配平 |',
    '|---|---:|---:|---:|---:|']
for row in dev:
    a=row['paper_residual']['old']['added_target'];b=row['paper_residual']['new']['added_target'];n=a['pixels']
    fmt=lambda v:'不可评分' if v is None else f'{v:.4f}'
    co=row['coverage'];sp=row['support']
    lines.append(f'| {row["view"]} | {n} | {fmt(a["mean"])}/{fmt(b["mean"])} | {fmt(sp["old"]["added_target"]["mean"])}/{fmt(sp["new"]["added_target"]["mean"])} | {fmt(co["new_raw"]["added_target"]["visible_ink_fraction"])}/{fmt(co["new_matched"]["added_target"]["visible_ink_fraction"])} |')
lines += ['', '可见墨采用alpha>0.05；纸色残留为clipped纸底到(0.95,0.95,0.95)的RGB L1。646/556像素的前侧新增面均发生明显源/混合编辑；后侧0或2像素不算新增面覆盖成功。弱241°/24°旧区域内部残留0.391708→0.271514，是区域重定义后原核许可/权重的派生影响，不能归因于后侧看见新增面。','',
    '## 实际预算与损伤','',
    f'四BUILD在相同新目标域的自然墨RGB L1旧{build["natural_target_ink_L1"]["old"]:.4f}、新{build["natural_target_ink_L1"]["new"]:.4f}。全局配平系数旧1、新{build["scales"]["new"]:.10f}，实际读回一致。纸底源编辑量没有随墨预算配平，故不能声称同源编辑预算算法优势。新目标域也包括原来边界处已有的少量墨，旧预算不应与unit007旧目标域的5866.0927直接混用。','',
    '| DEV视角 | 全目标/内部像素 | 墨L1旧/新自然/新配平 | 远其他L1旧/新 | 背景L1旧/新 | 新旧图远区变化L1 |',
    '|---|---:|---:|---:|---:|---:|']
for row in dev:
    mm=row['metrics'];ink=row['ink'];old=mm['old_raw'];new=mm['new_raw'];ch=row['changes']['raw']
    lines.append(f'| {row["view"]} | {new["target_full"]["pixels"]}/{new["target_interior"]["pixels"]} | {ink["old_raw"]["target_full"]["raw_L1_sum"]:.2f}/{ink["new_raw"]["target_full"]["raw_L1_sum"]:.2f}/{ink["new_matched"]["target_full"]["raw_L1_sum"]:.2f} | {old["far_other"]["raw_L1_sum"]:.6f}/{new["far_other"]["raw_L1_sum"]:.6f} | {old["far_background"]["raw_L1_sum"]:.6f}/{new["far_background"]["raw_L1_sum"]:.6f} | {ch["far_other"]["raw_L1_sum"]+ch["far_background"]["raw_L1_sum"]:.8f} |')
lines += ['', '上述远区使用两臂共同的新目标及固定2px带。扩区会把旧远区像素变成目标，例如61°/24°旧图远区总L1在旧掩码下约18.8854，在新掩码下约6.3960；图像未改变。绝不能把这种重分类写成局部性改善。SCOPE_AND_FAR_READBACK保留两种掩码口径，原unit007指标不动。',
    f'新增远区损伤非严格零。全部13记录的单像素最大新增raw RGB L1={maxfar:.8f}，超过1/255的远区像素计数合计{sum(x["far_pixels_above_1_255"] for x in far_rows)}，其中重复相机并非独立样本。完整/腐蚀新目标、旧区域、新增区域、边界、远其他和背景的mean/sum/可见变化保留在逐视角EVALUATION.json。',
    '墨预算在BUILD配平不保证各DEV等量；前侧新配平墨量仍较旧多约9%–15%，后侧则略少，不能把全部观感变化归为方向或结构质量。自然强度两前侧新增面墨RGB L1约239.91和245.74，具有实质可见墨量。','',
    '九帧为231°–251°、仰角24°、距离5.3的实际相机短弧。新增面在全部九帧目标采样中不可见，这条轨迹检验旧区域的副作用，不能认证新增面转台稳定性。全部帧已实际解码且与保存PNG逐像素相同。4DEV+9arc共12个不同相机设置，全部已曝光；不声称泛化或独立时序认证。','',
    '## 验证与交付','',
    '三项针对性TDD先缺实现RED rc1，再GREEN rc0：首交/源区域/隐藏面选择限制；按face而非source ID重映射；真实Lego零增量与旧数组保留、新路径身份和重心附着。旧M1和旧纸底许可的零增量分支均逐值复原；四BUILD旧hatch/alpha逐值恢复缓存，全部13DEV/arc旧混合图逐值恢复unit007 hatch_raw。',
    '独立审计从原事件用bincount重建新M1分数，并从真实原ID alpha×T重建每个视角的源RGB、两种纸底和墨责任；核验完整原行、输入锁、footprint分区、路径和预算。前侧冷重放实际完整GS三次，源/新纸底/S及自然/配平输出逐数组一致；零墨连接等于纸底，全部许可置零等于原GS。不是原生CUDA认证。',
    '预期RED之外全部科学阶段rc0，无中途修参、失败覆盖或科学阶段中断。v05稀疏capsule8.044%远区失败与4.49%区域变化，以及v06单位001–007各负结果均保留。本轮改变目标范围，不倒算旧门槛成功。',
    '交付asset中的TARGET/PATHS/ADDED_PATHS/SOURCE_LINK及独立新SOURCE_BINDING，source_snapshot内可运行冷重放入口，四个完整视角、独立墨层、实际相机短弧和逐视角原始数组。仍依赖输入锁中的外部原PLY、历史缓存及本地Python；不是独立移动包。输出是原GS纸底与原ID关联代理墨，不是原生Gaussian排线、独立物理归属或H1/H2/H3证明。','',
    '## 下一步','', 'NEXT=continue：'+next_step,'',why,'',f'报告生成时本轮执行约{elapsed:.2f}分钟；仅完成unit008，未执行下一科学单元。']
output_guard(UNIT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')

readme=f'''# Unit008：作者目标补选变体

前侧遗漏面已形成可见原GS纸底和关联排线；后侧残留与线条杂乱仍在。不升级默认。详见[报告](REPORT_ZH.md)。

- [四个完整物体视角](ALL_DEV_VIEWS.png)、[独立墨层](ALL_DEV_INK.png)、[全部短弧](ALL_ARC_FRAMES.png)。
- [BUILD选面证据](authoring/SELECTION_CHECK.png)：旧目标粉色，91个新增面青色。
- asset/TARGET.npz：冻结代理几何、旧/新face标签和新增面ID。
- asset/PATHS.npz：375条/2004段；旧351条/1904段另存OLD_PATHS，新24条/100段另存ADDED_PATHS。
- asset/SOURCE_LINK.npz：完整310475原PLY行，旧/新纸底和墨权重；SOURCE_BINDING.npz是新目标的独立M1/UNKNOWN。
- media/target_completion_arc_ffv1.mkv：九个真实相机帧，全部解码核对。
- dev、arc/FRAME.npz及TRACE.npz：实际GS、纸底、原ID支持、代理墨、自然/配平图及贡献事件。
- SCOPE_AND_FAR_READBACK.json：显式保留旧/新目标损伤口径，不能用扩区改写旧失败。

冷重放前侧真实完整GS并检查零连接控制，输出目录必须是unit008内不存在的新目录：

```bash
V06_UNIT_DIR={UNIT} CUDA_VISIBLE_DEVICES='' \\
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B \\
{UNIT}/source_snapshot/audit_target_unit.py replay \\
--out {UNIT}/cold_replay_manual_002
```

CPU两核亲和、数值线程1、禁GPU；编译只写新输出目录。依赖INPUT_LOCK中的外部原PLY、冻结代理/缓存和本地只读Python/C++编译器。非原生Gaussian排线，非独立语义/物理/时序认证。
'''
output_guard(UNIT/'README_ZH.md').write_text(readme)
receipts=[dict(name=f.name,**json.loads(f.read_text())) for f in sorted((UNIT/'logs').glob('*.receipt.json'))]
assert all(x['returncode']==0 for x in receipts if x['name']!='tdd_red_001.receipt.json')
progress=dict(actual_advance='91 visible BUILD faces added as a new authored target; same12 original-row traces relabeled; original-GS paper and linked proxy ink visibly fill the front yellow patch.',
    original_rows=310475,old_target_faces=2030,new_target_faces=2121,old_ink_rows=20122,new_ink_rows=21006,old_paper_rows=39474,new_paper_rows=41058,
    old_UNKNOWN_preserved=195600,new_variant_UNKNOWN=195279,old_paths_retained=1904,new_total_segments=2004,
    visible_outcome='Front patch completion effective at646/556 pixels; rear photo residual and whole-object line clutter remain.',
    representation=p['scope'])
artifacts={n:str(UNIT/n) for n in ['REPORT_ZH.md','README_ZH.md','PROTOCOL.json','CAMERAS.json','INPUT_LOCK.json','SOURCE_LOCK.json','ASSET_LOCK.json','SOURCE_BINDING.npz','SELECTION.npz',
    'SUMMARY.json','VALIDATION.json','SCOPE_AND_FAR_READBACK.json','ALL_DEV_VIEWS.png','ALL_DEV_INK.png','ALL_ARC_FRAMES.png','MEDIA_VALIDATION.json','cold_replay_001/REPLAY_CHECK.json','asset/SOURCE_LINK.npz','asset/PATHS.npz']}
status=dict(execution_state='completed',stage='authored_target_completion_handoff',
    scientific_verdict='VISIBLE_FRONT_PATCH_COMPLETION_VALIDATED; EXPLICIT_TARGET_SCOPE_CHANGE; WHOLE_OBJECT_NPR_STILL_LIMITED; NO_DEFAULT_PROMOTION',
    gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained=True,completed_utc=now(),elapsed_minutes=elapsed,
    artifacts=artifacts,tests_and_actual_commands=receipts,blockers=[],next_action='continue',parent_monitor_verification='pending',
    limitations=['One manually authored visible patch, not complete semantic bucket','Source edit budget differs; ink matched on BUILD only','Old/expanded masks have different far domains','Rear arc cannot see added patch','CPU replica and proxy ink only'],
    preserved_failures=[dict(stage='tdd_red_001',returncode=1,reason='Expected missing implementation; original receipt retained')])
js(UNIT/'STATUS.json',status)

previous=output_guard(UNIT/'delivery_previous');previous.mkdir(exist_ok=False)
old_files={}
for name in ('DEMO_README_ZH.md','DELIVERY_STATUS.json'):
    f=OUTPUT_ROOT/name
    if f.exists():shutil.copyfile(f,previous/name);old_files[name]=sha(f)
js(UNIT/'DELIVERY_PREVIOUS_LOCK.json',dict(files=old_files))
output_guard(OUTPUT_ROOT/'DEMO_README_ZH.md').write_text('# v06：最新unit008局部目标补选结果\n\n'+
    '前侧遗漏面获得可见纸底与原ID关联排线；完整NPR仍有后侧残留和杂乱线条。旧默认未升级，全部旧失败保留。\n\n'+
    '- [报告](units/unit_008/REPORT_ZH.md)\n- [实际完整视角](units/unit_008/ALL_DEV_VIEWS.png)\n- [数据与冷重放命令](units/unit_008/README_ZH.md)\n\n'+
    '相对v05/unit005的稀疏路径编辑，这是显式扩大的作者区域混合资产；不是原生Gaussian排线或旧capsule门槛通过。上一版交付说明逐字保存在unit008/delivery_previous。\n')
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit=str(UNIT),execution_state='completed',scientific_verdict=status['scientific_verdict'],
    gaussian_link_progress=progress,scientific_seal=False,default_promoted=False,variant_retained=True,readme=str(UNIT/'README_ZH.md'),
    report=str(UNIT/'REPORT_ZH.md'),next_action='continue',old_delivery_backup=str(previous),parent_monitor_verification='pending',utc=now()))
print('HANDOFF completed; visible front patch benefit, remaining whole-object failures; NEXT continue',flush=True)
