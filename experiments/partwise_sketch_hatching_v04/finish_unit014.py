"""Unit014 handoff from actual validated files, excluding mutable sessions."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import datetime,json,shutil,difflib,subprocess,os,shlex
from unit014_run import UNIT as u, PREVIOUS, protocol

p=protocol();package=u/'portable_demo';output_guard(u)
assert sha(u/'PROTOCOL.json')=='6e78894678ede4cc20bd1fd4fe804ee8721b3c1aa413dbb356661f88662b79c3'
assert sha(p['original']['original_ply'])==p['original']['sha256']
assert all(sha(Path(p['asset'])/name)==digest for name,digest in p['input_files'].items())
lock=json.loads((u/'INPUT_LOCK.json').read_text())
for scene,files in lock['assets'].items():
    for name,digest in files.items():
        assert sha(package/'assets'/scene/name)==digest
        assert sha(PREVIOUS/'portable_demo/assets'/scene/name)==digest
final=json.loads((u/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
assert final['CLI_PNG_exact'] and final['cold_viewer_PNG_exact']
browser=json.loads((u/'browser/BROWSER_VALIDATION.json').read_text());assert browser['status']=='PASS'
cold={kind:json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text()) for kind in ('orbit','zoom')}
assert all(r['all_png_exact'] and r['all_arrays_exact'] for r in cold.values())
video={kind:json.loads((package/'presentations'/('lego_bucket_'+kind)/'VIDEO_RECEIPTS.json').read_text()) for kind in ('orbit','zoom')}
for kind,rows in video.items():
    assert rows[0]['all_frames_exact'] and all(r['decode_returncode']==0 for r in rows)
    assert all(r['decoded_frames']==cold[kind]['frame_count'] for r in rows)
js(u/'metrics/COLD_REPLAY.json',dict(all_png_exact=True,all_arrays_exact=True,frames=sum(r['frame_count'] for r in cold.values()),
    replays={kind:{k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')} for kind,r in cold.items()}))
js(u/'metrics/VIDEO_VALIDATION.json',dict(videos=video,scope='18 finite cameras; FFV1 every RGB frame exact, MP4 full decode/count only.'))
receipts={f.stem.removesuffix('.receipt'):json.loads(f.read_text()) for f in (u/'logs').glob('*.receipt.json')}
for name in ('freeze','stage','composition_tests','candidate','original_lego','static_views','browser_lego_recovery','import_browser','cold_orbit_recovery','cold_zoom','package','final_archive_check'):
    assert receipts[name]['returncode']==0,name
assert receipts['browser_lego']['returncode']==1
assert receipts['cold_orbit']['returncode']==-15 and receipts['cold_orbit']['interrupt_signals']==[15]
owned=[]
for folder in ('browser','browser_failed'):
    owned.extend(r['pid'] for r in json.loads((u/folder/'OWN_CHILDREN.json').read_text())['children'])
owned.append(json.loads((u/'logs/FINAL_VIEWER_CHILD.json').read_text())['pid'])
resource=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
    task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
    unit_bytes=sum(f.stat().st_size for f in u.rglob('*') if f.is_file()),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,
    original_PLY_hash_unchanged=True,all_four_default_asset_files_unchanged=True,
    owned_PID_comm_still_present={str(pid):Path(f'/proc/{pid}/comm').read_text().strip() for pid in owned if Path(f'/proc/{pid}/comm').exists()})
assert not resource['owned_PID_comm_still_present']
assert resource['root_free_bytes']>=2**30 and resource['hdd_free_bytes']>=10*2**30 and resource['task_bytes']<20*2**30
js(u/'metrics/FINAL_RESOURCE_INPUT_CHECK.json',resource)
local=json.loads((u/'metrics/LOCAL_EDIT.json').read_text());paths=json.loads((u/'metrics/PATHS.json').read_text())
visual=json.loads((u/'VISUAL_REVIEW.json').read_text());assert visual['all_motion_frames_inspected']
source=json.loads((u/'source_model/RECEIPT.json').read_text())
next_step='在本轮真实Lego铲斗区域上做一个有界、保持拓扑的局部代理平滑候选，以减少可见波折/碎线：固定所有非目标区域顶点与区域边界，预冻结位移上限和迭代数，重新生成region4两层路径并记录版本变化。保留本轮原版并用同风格、整对象弱视角、原GS参考检查细节损失/遮挡/局部性和冷重开；不把平滑自身误差称为真实几何改善，不扫参。'
far={name:sum(row['comparisons']['baseline_to_cross']['masks'][name]['L1'] for row in local['frames']) for name in ('far_other','far_background')}
progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],new_composed_cross_model='lego',
    original_PLY_render_this_unit=True,original_gaussians=source['original_gaussians'],proxy_faces=paths['geometry_faces'],manual_bucket_faces=paths['selected_faces'],
    short_base_paths=paths['single']['0']['paths'],cross_paths=paths['cross']['1']['paths'],
    non_target_path_files_exact=True,manual_selection_exact=True,base_arrays_exact_when_adding_cross=True,toggle_path_bytes_exact=True,
    full_object_static_views=4,static_states_per_view=3,browser_actual_downloads=4,motion_frames=18,
    lossless_video_frames_exact=18,MP4_frames_decoded=18,cold_replay_PNG_and_arrays_exact=18,
    relocated_archive_CLI_and_cold_viewer_exact=True,default_four_assets_unchanged=True,
    strict_pixel_locality=dict(scope='four frozen cameras, baseline_to_cross, same proxy labels, fixed2px band',**far),
    visual_quality='partial; bucket short cross style visible, proxy noise and imperfect manual part coverage unchanged',scientific_seal=False,
    reasoning='Second real model now demonstrates a saved manually authored region with composed spacing/length/cross edits, exact preservation of other region files/layers, actual browser downloads and portable cold replay. Remaining major limitation is noisy proxy geometry, not absent local editing or export.')
start=datetime.datetime.fromisoformat('2026-10-22T06:15:50.598755+09:00')
status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),
    elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/60,
    engineering_execution='PASS_AFTER_PRESERVED_HARNESS_AND_COLD_INTERRUPTION_RECOVERY',scientific_verdict='H1_H2_NOT_TESTED_ENGINEERING_SECOND_MODEL_COMPOSITION',demo_progress=progress,
    artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','media/source_proxy_regions_edit.png','media/local_edit_all_views.png','media/isolated_layers_all_views.png','media/lego_orbit.mp4','media/lego_zoom.mp4','assets/cross','browser/BROWSER_VALIDATION.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT014_DIFF.patch'],
    tests=dict(real_Lego_behavior_tests=3,actual_Firefox=True,new_hatch_algorithm=False,
        command_receipts={name:dict(returncode=r['returncode'],path='logs/'+name+'.receipt.json') for name,r in receipts.items()}),blockers=[],
    limitations=['Manual bucket region reuses three authored views/2030 proxy faces; no full semantic part guarantee.',
        'Plane angle/spacing are world-plane controls, not uniform surface angle/distance; short target paths are regenerated revisions.',
        'Proxy/noisy depth contours, thin rods, platform and track line clutter remain; no geometry correction this unit.',
        'Cross increases ink relative to short single, without tone matching or human preference validation.',
        '18-frame cold equality and full video decode are finite engineering checks, not continuous temporal or independent occlusion certification.',
        'Dependencies not bundled; portability exercised by relocation in current Linux CPU environment.'],
    failures_preserved=['logs/browser_lego.receipt.json','browser_failed','failures/crosshatch_browser_before_fix.py','logs/cold_orbit.receipt.json','attempt_interrupted/cold_orbit','EXECUTION_AMENDMENT.json'],
    scientific_seal=False,supervisor_verification='reported_not_independently_verified')
js(u/'STATUS.json',status)
js(u/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
    reason='One complete-object real model and second-model local-style composition are runnable. The actual Lego weak views show proxy roughness as the next visible bottleneck; an isolated bounded region refinement can improve it without replacing the working default.',
    estimated_next_minutes=35,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
table=[]
for row in local['frames']:
    a=row['comparisons']['baseline_to_cross'];b=row['comparisons']['single_to_cross']
    table.append(f"| {row['camera']['azimuth']} | {a['target_L1']:.3f} | {b['target_L1']:.3f} | {row['cross_ink']:.3f} | {row['total_ink']['cross']/row['total_ink']['baseline']:.4f} | {a['masks']['far_other']['L1']:.3f} / {a['masks']['far_background']['L1']:.3f} |")
report=f'''# Unit014：真实Lego手工铲斗区域的短/疏/交叉排线

执行状态 **completed**（本轮工程范围），整体视觉 **partial**。用时{status['elapsed_minutes']:.1f}分钟，真实Lego原PLY重新CPU渲染，三状态×四完整视角、实际Firefox四次下载、18运动帧导出/全解码/冷重放完成。H1/H2未测试。

## 输入、审阅与冻结

完整读取BRIEF、851行原大纲、P1最后完成unit010和P2报告/NEXT及相关源，审阅unit013实际Chair全对象对照和上游Lego/Ficus负视角。Chair交叉有效但更黑；Lego有已保存手工铲斗，代理粗糙明显；Ficus叶片孔洞仍在。选择将现有控件组合迁移到Lego，不重复选面、不增加第五模型、不把工程验证当几何或机制成功。详见READING_REVIEW_ZH。

协议冻结 `{p['frozen_utc']}`，SHA `{sha(u/'PROTOCOL.json')}`。输入 `{p['asset']}`；原Lego PLY SHA `{p['original']['sha256']}`，{source['original_gaussians']}个高斯；代理{paths['geometry_vertices']}顶点/{paths['geometry_faces']}面、mesh SHA `{p['input_files']['mesh.npz']}`。探索性代理由原vanilla GS深度CPU融合而来，不是GT或RaDe训练结果。沿用三次人工矩形选面的region4（2030面）；selection文件与几何/全部标签字节不变，未宣称完整铲斗语义。

## 实际执行和局部性

唯一短疏配置：region4保留基础35°、xz平面、1px；spacing .045→.060、length .22→.12，随后加第二方向+60°、spacing .075。其余region1/2/3路径和风格保留。三状态独立保存为原始、short single、short cross；不是同墨量的审美比较。基础路径199条/1528段/24.1164世界长度变为199条/1087段/16.5169；数量巧合同为199不代表路径坐标不变。第二层152条/817段/12.2806长度。两层最大路径长度均≤.12+数值误差；边界可提前停止。加交叉后短基础层逐字段精确，关/开交叉文件字节精确。

固定512²/2xAA、仰角30°、距离5.1、方位233/323/53/143°，轮廓强度1。所有代理顶点在画内，所有弱视角保留。四视图depth/regions/contour及非目标层精确；L1使用float灰度绝对差，互斥目标内部/固定2px边带/远其他/远背景，原始每区像素分母见metrics/LOCAL_EDIT.json。

| Azimuth | Original→cross target L1 | Single→cross target L1 | Added layer ink | Whole ink cross/original | Far other / background L1 |
|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

原始到最终四视角远其他L1合计{far['far_other']:.6f}，远背景{far['far_background']:.6f}；不改写历史其他相机/配置残差。评分标签来自同代理，非独立语义真值。增加第二层的墨量是操作预期，没有色调校准或审美优越结论。

实际审阅全对象三状态、原GS/代理/区域对照及两独立层：323°铲斗交叉格最清楚，233/143°可见短线交叠；53°侧向弱视角中路径更碎且部分面不可见。平台、履带、驾驶室和杆件粗糙线团不变；铲斗仍有不均匀空隙，交叉不是几何修复。

## 测试、交互、冷重放

3项真实Lego行为测试rc0：组合编辑/选择和非目标保留、关闭层时编辑再开启与新组合一致、丢失/损坏选面拒绝。含实际192²渲染和禁重生成的冷加载。原生成器/编辑器/渲染器未改，不制造无意义红灯；新增的是真实组合验证和参数化浏览器harness。

Firefox实际操作短疏滑块、交叉开关、第二方向参数、保存、撤销、刷新及Lego/Chair切换，实际点击下载asset ZIP、PNG、12帧orbit ZIP、6帧zoom ZIP。浏览器将233°规范成-127°，同一方向且PNG与冻结CLI图精确。两视频全部18帧均已审阅；FFV1全帧RGB精确，MP4全解码/计数通过。有损MP4不称像素精确，18帧不称全时序认证。

实际下载资产和相机在全新Python进程重放18/18 PNG和全部分层数组精确。最终tar解压到新目录后，按文档从默认Lego直接组合CLI编辑/图片/关闭交叉；生成路径与浏览器相同、PNG精确。独立冷viewer恢复选中region4、手工历史、风格/相机/显示和PNG精确。此检查只在当前Linux依赖环境，未捆绑解释器/依赖。

## 失败与恢复

首个浏览器测试rc1：新参数化harness的region key被保存路径字段循环覆盖为stroke_id，应用本身已正常保存探针75°/.09。原目录移存browser_failed、原log/receipt/失败源码保留；两自有进程清理见CLEANUP。仅改harness变量名后同协议恢复rc0，没有更换候选/相机、没有改生成或渲染算法。

首个cold orbit在10.967秒收到外部SIGTERM，wrapper退出143、child=-15、完成三帧后中止，原因未知；原始部分结果保留attempt_interrupted/cold_orbit，不算完整证据。确认自有PID消失后，同一冻结bundle新进程串行重放12帧通过。原收据和恢复见EXECUTION_AMENDMENT。所有数值串行、单数值线程、两核affinity、无GPU/安装/环境dump/凭据/嵌套模型/push/merge；本unit自有浏览器/server均退出。原PLY、上轮四模型默认资产及协议复核不变。

## 交付和下一步

`cd {package} && ./run.sh viewer --scene lego --asset "$PWD/examples/lego_bucket_cross"`；浏览器127.0.0.1:8765。可运行源码、四默认模型、Chair/Lego交叉示例、全对象预览和实际下载运动包位于portable_demo，便携tar及完整命令/returncodes见PACKAGE_README_ZH/REPRODUCE_ZH和logs。SOURCE_SNAPSHOT与UNIT014_DIFF记录回放源及相对起点变化，继承dirty未清理。

只封存已验证工程证据，scientific_seal=false，parent仍为reported_not_independently_verified。NEXT=continue：{next_step}
'''
(u/'REPORT_ZH.md').write_text(report)
repro='# Unit014实际执行命令\n\nCPU2/单数值线程/串行/禁CUDA。原失败保留。\n\n'
for name,r in sorted(receipts.items(),key=lambda x:x[1].get('start_utc','')):
    repro+=f"## {name}\n\nreturncode={r['returncode']}，seconds={r.get('seconds','unknown')}\n\n```bash\n"+shlex.join(r['command'])+'\n```\n\n'
(u/'REPRODUCE_ZH.md').write_text(repro)
snapshot=u/'source_snapshot';shutil.copytree(Path(__file__).parent,snapshot,ignore=shutil.ignore_patterns('__pycache__'))
before=u/'source_before';diff=[]
for name in sorted({f.name for f in before.iterdir() if f.is_file()}|{f.name for f in snapshot.iterdir() if f.is_file()}):
    old=(before/name).read_text().splitlines(keepends=True) if (before/name).is_file() else []
    new=(snapshot/name).read_text().splitlines(keepends=True) if (snapshot/name).is_file() else []
    diff.extend(difflib.unified_diff(old,new,fromfile='before/'+name,tofile='after/'+name))
(u/'UNIT014_DIFF.patch').write_text(''.join(diff))
js(u/'SOURCE_SNAPSHOT.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    source_files={f.name:sha(f) for f in snapshot.iterdir() if f.is_file()},inherited_dirty_worktree=True))
shutil.copy2(u/'PACKAGE_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
shutil.copy2(u/'PACKAGE_README_ZH.md',Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'))
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),latest_unit='unit_014',execution_state='completed',visual_quality='partial',demo_progress=progress,
    entrypoint=str(package/'run.sh'),archive=str(u/'portable_demo.tar.gz'),archive_sha256=sha(u/'portable_demo.tar.gz'),
    report=str(u/'REPORT_ZH.md'),scientific_seal=False,remaining=next_step))
selected=[]
for name in ['PROTOCOL.json','INPUT_LOCK.json','SOURCE_BEFORE.json','SOURCE_SNAPSHOT.json','READING_REVIEW_ZH.md','EXECUTION_AMENDMENT.json','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','REPORT_ZH.md','STATUS.json','NEXT.json','VISUAL_REVIEW.json','UNIT014_DIFF.patch','portable_demo.tar.gz']:
    selected.append(u/name)
for folder in ('metrics','media','source_model','renders','assets','source_snapshot','failures','build'):
    selected.extend(f for f in (u/folder).rglob('*') if f.is_file())
for f in (u/'logs').iterdir():
    if f.is_file() and (f.name.endswith('.receipt.json') or f.name.endswith('.log') or f.name=='FINAL_VIEWER_CLEANUP.json') and f.name!='finalize.log':selected.append(f)
for name in ('BROWSER_VALIDATION.json','CLEANUP.json','EXPORT_STATE.json','02_short_single.png','02_cross_enabled.png','03_export_complete.png','lego_asset.zip','lego_image.png','lego_orbit.zip','lego_zoom.zip'):
    selected.append(u/'browser'/name)
selected.append(u/'browser_failed/CLEANUP.json')
manifest={str(f.relative_to(u)):sha(f) for f in sorted(set(selected))}
js(u/'ENGINEERING_MANIFEST.json',dict(scope='Validated engineering evidence and preserved failure receipts; not independent scientific certification',files=manifest))
assert all(sha(u/name)==digest for name,digest in manifest.items())
js(u/'ENGINEERING_SEAL.json',dict(utc=now(),manifest_sha256=sha(u/'ENGINEERING_MANIFEST.json'),files_verified=len(manifest),
    scientific_seal=False,validation='Integrity of explicitly checked local engineering artifacts',supervisor_verification='reported_not_independently_verified'))
print(json.dumps(dict(execution_state=status['execution_state'],elapsed_minutes=status['elapsed_minutes'],sealed_files=len(manifest),archive_sha256=sha(u/'portable_demo.tar.gz')),ensure_ascii=False))
