"""Finalize unit013 from validated receipts; seal only immutable evidence."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import datetime,json,shutil,difflib,subprocess,os,shlex
u=OUTPUT_ROOT/'units/unit_013';p=json.loads((u/'PROTOCOL.json').read_text());package=u/'portable_demo'
final=json.loads((u/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
assert final['CLI_PNG_exact'] and final['cold_viewer_PNG_exact']
assert sha(p['original']['original_ply'])==p['original']['sha256']
lock=json.loads((u/'INPUT_LOCK.json').read_text())
for scene,files in lock['assets'].items():
    for name,digest in files.items():
        assert sha(package/'assets'/scene/name)==digest
        assert sha(OUTPUT_ROOT/'units/unit_012/portable_demo/assets'/scene/name)==digest
assert all(sha(Path(p['asset'])/name)==digest for name,digest in p['input_files'].items())
assert sha(u/'PROTOCOL.json')=='59b77eb9f968e526f2a502ea39015034c2aec6a0328cfd11cbf04181f1c3180f'
output_guard(u)
resource=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
 task_bytes=sum(file.stat().st_size for file in OUTPUT_ROOT.rglob('*') if file.is_file()),
 unit_bytes=sum(file.stat().st_size for file in u.rglob('*') if file.is_file()),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,
 original_PLY_hash_unchanged=True,all_four_default_asset_files_unchanged=True)
assert resource['root_free_bytes']>=2**30 and resource['hdd_free_bytes']>=10*2**30 and resource['task_bytes']<20*2**30
# Inspect only PID/comm for the owned children recorded by this unit.
owned=[]
for file in (u/'browser/OWN_CHILDREN.json',):
    owned.extend(row['pid'] for row in json.loads(file.read_text())['children'])
owned.extend(row['pid'] for row in json.loads((u/'logs/BROWSER_INTERRUPTED_CLEANUP.json').read_text())['own_child_groups'])
owned.append(json.loads((u/'logs/FINAL_VIEWER_CHILD.json').read_text())['pid'])
resource['owned_PID_comm_still_present']={str(pid):Path(f'/proc/{pid}/comm').read_text().strip() for pid in owned if Path(f'/proc/{pid}/comm').exists()}
assert not resource['owned_PID_comm_still_present']
js(u/'metrics/FINAL_RESOURCE_INPUT_CHECK.json',resource)
local=json.loads((u/'metrics/LOCAL_EDIT.json').read_text());browser=json.loads((u/'browser/BROWSER_VALIDATION.json').read_text())
assert browser['status']=='PASS'
cold={kind:json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text()) for kind in ('orbit','zoom')}
assert all(row['all_png_exact'] and row['all_arrays_exact'] for row in cold.values())
video={kind:json.loads((package/'presentations'/('chair_cross_'+kind)/'VIDEO_RECEIPTS.json').read_text()) for kind in ('orbit','zoom')}
for kind,rows in video.items():
    assert rows[0]['all_frames_exact'] and all(row['decode_returncode']==0 for row in rows)
    assert all(row['decoded_frames']==cold[kind]['frame_count'] for row in rows)
js(u/'metrics/COLD_REPLAY.json',dict(all_png_exact=True,all_arrays_exact=True,frames=sum(row['frame_count'] for row in cold.values()),
 replays={kind:{key:row[key] for key in ('scene','frame_count','all_png_exact','all_arrays_exact')} for kind,row in cold.items()}))
js(u/'metrics/VIDEO_VALIDATION.json',dict(videos=video,scope='FFV1 every decoded RGB frame exact; MP4 full decode/count, lossy; finite 18 cameras only.'))
receipts={file.stem.removesuffix('.receipt'):json.loads(file.read_text()) for file in sorted((u/'logs').glob('*.receipt.json'))}
for name in ('cross_final_tests','coordinate_visibility_regression','legacy_compatibility','original_chair','static_views','browser_crosshatch_recovery','cold_orbit','cold_zoom','package_final','final_archive_check'):
    assert receipts[name]['returncode']==0,name
paths=json.loads((u/'metrics/PATHS.json').read_text())
progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],new_cross_layer_model='chair',
 original_PLY_render_this_unit=True,original_gaussians=256690,proxy_faces=30000,
 base_paths_retained=720,new_cross_paths=590,non_target_paths_and_layers_exact=True,toggle_path_bytes_exact=True,
 full_object_static_views=4,browser_actual_downloads=4,motion_frames=18,lossless_video_frames_exact=18,MP4_frames_decoded=18,
 cold_replay_PNG_and_arrays_exact=18,relocated_archive_CLI_and_cold_viewer_exact=True,legacy_unit012_frame_exact=True,
 strict_pixel_locality='Zero far-other/background change in this four-view cross-addition test; historical unit012 residuals remain valid.',
 visual_quality='partial; cross layer adds controllable ink; rough contours, thin geometry and authored boundaries unchanged',
 default_four_assets_unchanged=True,scientific_seal=False,
 reasoning='A real Chair can now add, edit, disable, save and export a persistent second hatch direction in one region. Base/other-region paths stay exact, and relocated downloads cold-replay. This completes a missing style operation in the original demo outline, without a geometry or H1/H2 claim.')
next_step='在既有Lego完整模型上组合已有多视图选面与新交叉层：保存明确的bucket局部区域，仅给它施加一个预冻结的短/疏交叉配置，固定其余区域路径和默认资产；实际浏览器导出完整弱视角及冷重开。记录人工面选择，不声称自动语义或改善代理几何。若现有Lego人工区域已足够，复用它而不重做选区。'
status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),
 elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T05:55:39.050498+09:00')).total_seconds()/60,
 engineering_execution='PASS_AFTER_PRESERVED_SETUP_AND_BROWSER_INTERRUPTION_RECOVERY',scientific_verdict='H1_H2_NOT_TESTED_ENGINEERING_CROSS_HATCH_LAYER',
 demo_progress=progress,
 artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','media/source_proxy_regions_edit.png','media/local_edit_all_views.png','media/chair_orbit.mp4','media/chair_zoom.mp4','assets/cross','browser/BROWSER_VALIDATION.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT013_DIFF.patch'],
 tests=dict(real_Chair_behavior_tests=7,real_HTTP_invalid_request_test=1,coordinate_visibility_regression_tests=7,actual_Firefox=True,
 command_receipts={name:dict(returncode=row['returncode'],path='logs/'+name+'.receipt.json') for name,row in receipts.items()}),blockers=[],
 limitations=['Cross angle is a world-plane offset, not constant surface intersection angle; spacing is world-plane spacing.',
 'Region2 is authored height band and includes some arm/frame faces, not a semantic seat segmentation.',
 'Optional cross layer increases ink and can be dense; no target-tone matching or human preference result.',
 'Proxy-relative attachments; rough contours, gaps and Ficus thin foliage defects unchanged.',
 '18-frame exact replay and video decode are finite engineering evidence, not continuous temporal certification.',
 'Cross feature visually tested on Chair; other catalog models retain default assets. Dependencies not bundled; current Linux CPU only.'],
 failures_preserved=['logs/cross_tdd_red.receipt.json','logs/stage.receipt.json','logs/stage_corrected_path.receipt.json','logs/candidate.receipt.json','logs/browser_crosshatch.receipt.json','browser_interrupted','EXECUTION_AMENDMENT.json'],
 scientific_seal=False,supervisor_verification='reported_not_independently_verified')
js(u/'STATUS.json',status)
js(u/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
 reason='Complete-object real-model local editing, layer controls, export and cold reload now work. Validate the same composed interaction on an existing second model and a more specific authored region; avoid another UI-only or toy-gate unit.',
 estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
rows='\n'.join('| '+str(r['camera']['azimuth'])+' | '+f"{r['target_L1']:.4f} | {r['cross_total_ink']/r['baseline_total_ink']:.4f} | {r['cross_layer_ink']:.4f} | {r['both_layers_supported_pixels']} | {r['masks']['far_other']['L1']:.4f} / {r['masks']['far_background']['L1']:.4f}"+' |' for r in local['frames'])
report=f'''# Unit013：Chair可保存单区交叉排线

执行状态 **completed**（本轮交叉层工程范围），整体视觉 **partial**。用时约{status['elapsed_minutes']:.1f}分钟，未使用额外超时窗口。浏览器真实下载4文件，18运动帧冷重放PNG及全部数组精确；默认四模型资产不变。H1/H2未测试。

## 选择与冻结

完整读取BRIEF、851行原大纲、P1最后完成unit010/P2报告和NEXT及相关实际源、unit012报告/NEXT/源。unit011 P1目录缺少完成报告，未恢复旧科学任务。实际检查unit012原GS/代理/区域/编辑图及Ficus全部orbit：Chair局部编辑清楚，Ficus孔洞/碎线明显。选择新增可保存第二方向层，优先补齐原大纲的交叉风格；几何修复留独立步骤，不以新模型数或完美toy门槛替代demo。

协议冻结于{p['frozen_utc']}，SHA `{sha(u/'PROTOCOL.json')}`。输入为unit012便携Chair资产：原PLY `13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d`、代理mesh `9220ab7017ab5b64f3f5d6060209fc0f310b0901709bae535a460d543d14fd25`，完整路径/各文件SHA见PROTOCOL。原始256690高斯本轮再次CPU SH3 EWA渲染，源未修改；代理17058顶点/30000面来自冻结vanilla GS深度的探索性融合/平滑，不是真值或RaDe训练结果。区域仍为人工高度阈值，不是自动语义。

## 实现与实际结果

仅给region2新增layer1：原基础角95°、间距0.045、长度0.22、线宽1px不变；第二方向偏转60°、独立间距0.060。720基础路径/7068段逐字段精确保留，新层590路径/5954段；非目标1/3区域文件及网格字节相同。新层保存points/bary/face/stroke_id/layer_id，路径ID与基础层不重叠。角度是切割平面偏转，曲面上并非处处60°。

开关只改变可见性，保存的NPZ路径字节不变；改第二方向角/间距只更新layer1；基础方向/长度影响相关两层，宽度不重生成路径。新分区继承相应风格并保留未选择的两层段；拒绝留下没有基础路径的源区域。CLI/browser共享逻辑，legacy资产默认关闭。显示采用相同深度/区域裁剪及墨量max合成；不是逐帧2D重画。

固定512²/2xAA、轮廓强度1、四方位47/137/227/317°、仰角25°、距离5.2，未扫参数。完整对象与隔离层图已审阅：座面交叉可辨，137/227°背侧也保留；座面后部可能偏黑，侧面有密集网格与原有断线。主张可控制，不宣称更美观或更准几何。

| Azimuth | Target L1 | Total ink after/before | Cross-layer ink | Both-layer supported pixels | Far other / background L1 |
|---:|---:|---:|---:|---:|---:|
{rows}

L1为归一化灰度浮点差总和；表中目标包含其边界，详细json另以互斥的目标内部/固定2px带/远其他/远背景分区，无重叠分母。四视角基础图层、其他区域图层、深度/标签/轮廓精确。远区本次均0；不推翻unit012不同视角/显示配置下的小残差。参考只是同代理标签，非独立部件真值。墨量增加是叠层的预期效果，没有保墨或色调匹配，因此不是H1/H2受控收益实验。

## 可操作性与冷重放

7项真实Chair行为、1项真实HTTP非法请求、7项坐标/遮挡回归通过。TDD先真实失败：旧edit只存参数而未创建层(rc1)，修复后通过。额外一次legacy回归从新源码复现unit012 Chair的原PNG和所有数组；没有机械重跑全历史。

真实Firefox（软件渲染）操作checkbox、角度/间距、保存、关/开、撤销、刷新及Chair/Lego切换，基础/非目标保持；实际点击下载asset ZIP、PNG、12-frame orbit ZIP、6-frame zoom ZIP，共4文件。PNG与CLI冻结视图精确；导出不重生成路径。orbit/zoom全部18完整对象帧已审阅，FFV1全部18解码RGB精确，MP4全部18解码计数通过（有损）。导出约36.35/18.65秒。保存的两层及各相机在新路径、全新Python进程重绘18/18 PNG和全部数组精确。最终tar再次解压验证文件哈希，按文档CLI生成交叉资产/PNG/关闭，另一个冷启动viewer从下载资产恢复style/camera/display和PNG精确。依赖未捆绑，仅当前Linux CPU环境。

## 失败、恢复与范围

stage首次rc2：helper误放当前worktree根，立即移回允许的experiments目录；接着stage/candidate因保留字import用于字典关键字出现SyntaxError，各rc1，未运行候选。修复后对应rc0。原收据保留。

首个浏览器外层收到SIGTERM，29.98秒退出143，子进程-15；原因未确定。保留browser_interrupted，不将其当完成证据。按本次SERVER.json/webdriver.log的独立本地端口确认两个自有进程组并清理；给harness补充立即记录子PID与中断finally。相同协议恢复运行96.53秒rc0，未重选候选。原失败和清理见EXECUTION_AMENDMENT。数值始终串行、affinity两核、无GPU/安装/凭据/环境dump/嵌套模型/push/merge；自有浏览器/server均已退出。

Chair粗轮廓/断线、Ficus孔洞等几何缺陷未修复。人工region2包含部分扶手/框架，不是精确座面语义。短视频不是全时序/隐藏表面认证；新方向参数只在Chair做完整视觉验证。旧GT物理边界零余量、H2不可辨识和历史NO_GO不改写。

## 使用与交付

`cd {package} && ./run.sh viewer --scene chair`，本机8765。要直接打开已交叉的版本：`./run.sh viewer --scene chair --asset "$PWD/examples/chair_cross"`。完整CLI/导出/重放见PACKAGE_README_ZH.md；实际命令和returncodes见REPRODUCE_ZH.md及logs收据。portable_demo.tar.gz包含4默认真实模型、交叉例子、实际下载动画、预览及可运行源码。source_snapshot、UNIT013_DIFF.patch记录相对本轮起点变化；继承dirty不清理。

只对实际验证的immutable交付/媒体/源/收据建工程哈希清单，scientific_seal=false，parent仍标reported_not_independently_verified。NEXT=continue：{next_step}
'''
(u/'REPORT_ZH.md').write_text(report)
repro='# Unit013实际执行命令\n\n所有命令数值串行、runtime两核/单数值线程/禁CUDA。原失败不覆盖。\n\n'
for name,row in sorted(receipts.items(),key=lambda x:x[1].get('start_utc','')):
    repro+=f"## {name}\n\nreturncode={row['returncode']}，seconds={row.get('seconds','unknown')}\n\n```bash\n"+shlex.join(row['command'])+'\n```\n\n'
(u/'REPRODUCE_ZH.md').write_text(repro)
# Snapshot all experiment source, but distribute only runtime modules.
snapshot=u/'source_snapshot';shutil.copytree(Path(__file__).parent,snapshot,ignore=shutil.ignore_patterns('__pycache__'))
before=u/'source_before';diff=[]
for name in sorted({f.name for f in before.iterdir() if f.is_file()}|{f.name for f in snapshot.iterdir() if f.is_file()}):
    old=(before/name).read_text().splitlines(keepends=True) if (before/name).is_file() else []
    new=(snapshot/name).read_text().splitlines(keepends=True) if (snapshot/name).is_file() else []
    diff.extend(difflib.unified_diff(old,new,fromfile='before/'+name,tofile='after/'+name))
(u/'UNIT013_DIFF.patch').write_text(''.join(diff))
js(u/'SOURCE_SNAPSHOT.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 source_files={f.name:sha(f) for f in snapshot.iterdir() if f.is_file()},inherited_dirty_worktree=True))
shutil.copy2(u/'PACKAGE_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
shutil.copy2(u/'PACKAGE_README_ZH.md',Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'))
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),latest_unit='unit_013',execution_state='completed',visual_quality='partial',demo_progress=progress,
 entrypoint=str(package/'run.sh'),archive=str(u/'portable_demo.tar.gz'),archive_sha256=sha(u/'portable_demo.tar.gz'),
 report=str(u/'REPORT_ZH.md'),scientific_seal=False,remaining=next_step))
# Exclude mutable browser profiles, interrupted assets, runtime outputs, and root delivery pointers.
selected=[]
for name in ['PROTOCOL.json','INPUT_LOCK.json','SOURCE_BEFORE.json','SOURCE_SNAPSHOT.json','READING_REVIEW_ZH.md','EXECUTION_AMENDMENT.json','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','REPORT_ZH.md','STATUS.json','NEXT.json','VISUAL_REVIEW.json','UNIT013_DIFF.patch','portable_demo.tar.gz']:
    file=u/name
    if file.is_file():selected.append(file)
for folder in ('metrics','media','source_model','renders','assets','source_snapshot'):
    selected.extend(f for f in (u/folder).rglob('*') if f.is_file())
for file in (u/'logs').iterdir():
    if file.is_file() and (file.name.endswith('.receipt.json') or file.name in ('BROWSER_INTERRUPTED_CLEANUP.json','FINAL_VIEWER_CLEANUP.json')):selected.append(file)
for name in ('BROWSER_VALIDATION.json','CLEANUP.json','02_cross_enabled.png','03_export_complete.png','chair_asset.zip','chair_image.png','chair_orbit.zip','chair_zoom.zip'):
    selected.append(u/'browser'/name)
manifest={str(file.relative_to(u)):sha(file) for file in sorted(set(selected))}
js(u/'ENGINEERING_MANIFEST.json',dict(scope='Validated engineering evidence; not independent scientific certification',files=manifest))
assert all(sha(u/name)==digest for name,digest in manifest.items())
js(u/'ENGINEERING_SEAL.json',dict(utc=now(),manifest_sha256=sha(u/'ENGINEERING_MANIFEST.json'),files_verified=len(manifest),
 scientific_seal=False,validation='Hash integrity of explicitly checked local engineering artifacts',supervisor_verification='reported_not_independently_verified'))
print(json.dumps(dict(execution_state=status['execution_state'],elapsed_minutes=status['elapsed_minutes'],sealed_files=len(manifest),archive_sha256=sha(u/'portable_demo.tar.gz')),ensure_ascii=False))
