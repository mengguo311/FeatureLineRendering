"""Record actual engineering progress; do not turn finite replay into science."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,shutil,subprocess,datetime,shlex
U=output_guard(OUTPUT_ROOT/'units/unit_008')
def read(n):return json.loads((U/n).read_text())
def finish():
 if (U/'ENGINEERING_SEAL.json').exists():raise FileExistsError('already sealed')
 p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');s=read('selection/SELECTION_EVIDENCE.json')
 browser=read('browser_complete/BROWSER_VALIDATION.json');export=read('metrics/EXPORT_REPLAY.json');portable=read('metrics/PORTABLE_REPLAY.json')
 assert browser['status']==export['status']==portable['status']==read('metrics/PORTABLE_VIEWER.json')['status']=='PASS'
 assert all(x['far_edit_L1']==0 for x in v['views'])
 assert all(x['all_decoded_frames_exact'] for x in read('media/VIDEO_VALIDATION.json')['videos'])
 assert all(sha(f)==h for f,h in p['input_sha256'].items())
 for source in p['originals'].values():assert sha(source['original_ply'])==source['sha256']
 old=OUTPUT_ROOT/'units/unit_007';manifest=json.loads((old/'SHA256_MANIFEST.json').read_text())
 assert all(sha(old/x['path'])==x['sha256'] for x in manifest['files'])
 receipts=sorted([json.loads(f.read_text())|dict(path=str(f.relative_to(U))) for f in (U/'logs').glob('*.receipt.json')],key=lambda x:x['start_utc'])
 groups={json.loads(f.read_text())['own_process_group'] for f in (U/'logs').glob('*.start.json')}
 for folder in ('browser_complete','browser_interrupted'):
  groups.update(x['pid'] for x in read(folder+'/CLEANUP.json')['children'])
 groups.add(read('metrics/PORTABLE_VIEWER_CLEANUP.json')['pid'])
 proc=subprocess.run(['ps','-g',','.join(map(str,sorted(groups))),'-o','pid=,comm='],capture_output=True,text=True)
 assert not proc.stdout.strip(), 'own process groups still alive'
 branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip();assert branch=='partwise-sketch-hatching-models-v04'
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 snap=U/'source_snapshot';snap.mkdir()
 for f in Path(__file__).parent.iterdir():
  if f.suffix in ('.py','.html','.cpp'):shutil.copy2(f,snap/f.name)
 for f in (U/'portable_demo/source').iterdir():assert sha(f)==sha(snap/f.name)
 js(U/'SOURCE_LOCK.json',dict(commit=commit,branch=branch,protocol_sha256=sha(U/'PROTOCOL.json'),files={str(f.relative_to(U)):sha(f) for f in sorted(snap.iterdir())}))
 (U/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','701f9b01ee88a885c4c20baa6337fc209bc4cf1a','HEAD','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
 failed=[dict(path=x['path'],returncode=x['returncode']) for x in receipts if x['returncode']]
 js(U/'EXECUTION_AMENDMENT.json',dict(failed_commands=failed,expected_TDD='catalog_red: actual ModuleNotFoundError before implementing independent scene sessions',interruption=read('INTERRUPTION.json'),package_batch=read('PACKAGE_BATCH_INTERRUPTION.json'),ancillary='Initial read-only P1/P2 directory guesses produced no listing; actual paths read from runtime source. No old output writes.',science_retries=False,parameter_changes_after_freeze=False))
 elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T19:32:18.997768+00:00')).total_seconds()/60
 limitations=['Rough proxy geometry, perforations and short jagged strokes remain; Lego board hatches are wavy, thin mechanical rods missing.',
  'Manual bucket faces include some support fragments and hidden omissions: 33 indexed-edge components, largest 1948 of2030 faces; full triangles may extend outside rectangles.',
  'Region creation has 0.4 L1 outside the fixed 2px selection band in orbit53; cause not independently resolved. Angle edit far delta is0 in the8 tested views.',
  'Same-proxy masks/anchors and same-model depths are not independent geometry or semantic truth;18 decoded frames are not full temporal certification.',
  'Per-scene drafts/undo histories last only for the current server; export committed assets to preserve them. Python environment not bundled; other platforms untested.']
 progress=dict(available_models=['chair','lego','drums'],unified_portable_viewer=True,genuinely_ran_old_model=True,
  original_PLY_render_this_unit=['lego'],saved_asset_cold_render_this_unit=['chair','lego','drums'],full_original_model_rebuild_this_unit=False,
  scene_sessions_preserve_drafts_and_edits=True,stale_scene_requests_rejected=True,actual_browser_pointer_keyboard_and_model_dropdown=True,
  selected_faces=v['selected_faces'],construction_views=3,selection_operations=3,face_counts=[x['after_faces'] for x in s['steps']],
  selected_components=s['selected_indexed_edge_components'],largest_component_faces=s['component_face_counts'][0],
  original_gaussians=v['original_gaussians'],proxy_vertices=v['vertices'],proxy_faces=v['faces'],
  baseline_paths=sum(x['paths'] for x in v['anchors']['baseline'].values()),edited_paths=sum(x['paths'] for x in v['anchors']['edited'].values()),
  retained_non_target_paths=sum(v['anchors']['baseline'][str(r)]['paths'] for r in (1,2,3)),donor_unselected_segments=v['source_segments_retained'],non_target_paths_and_layers_exact=True,
  static_views=8,complete_object_static_views=sum(x['complete_object'] for x in v['views']),orbit_frames=12,zoom_frames=6,all_trajectory_views_complete=True,all_video_frames_decoded_exact=True,
  exported_three_models_cold_reload_exact=True,relocated_three_models_cold_reload_exact=True,relocated_author_edit_replay_exact=True,relocated_viewer_launch_and_scene_switch=True,
  visual_quality='partial',scientific_seal=False,reasoning='三个真实旧模型现在用同一可搬移入口、同一最新选面与四参数编辑界面；切模型保留各自状态，Lego人工选面、导出和搬移冷加载闭环实跑。')
 next_step='在现有三模型可用入口基础上，做一次有预算的Ficus旧PLY迁移：冻结同一CPU深度/TSDF路线和粗风格区，先出完整对象静态图，再局部编辑/冷加载/短轨迹；将叶片孔洞、断枝和拒绝附着明确记录，若薄结构不足则以partial导入证据返回，不扫描重建参数或要求完美分部。成功资产接入现有catalog。'
 artifacts=['portable_demo.tar.gz','portable_demo/run.sh','portable_demo/CATALOG.json','CATALOG.json','SELECTION_RECIPE.json','assets/baseline/asset.json','assets/edited/asset.json','media/three_models.png','media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv','selection/selection_all_views.png','metrics/VALIDATION.json','metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','browser_complete/BROWSER_VALIDATION.json','SOURCE_LOCK.json','REPRODUCE_ZH.md']
 status=dict(stage='UNIT008_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',engineering_validation='PASS_WITH_AUTHORING_LOCALITY_LIMITATION',genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,artifacts=artifacts,tests_and_command_receipts=[dict(path=x['path'],returncode=x['returncode'],seconds=x['seconds']) for x in receipts],blockers=[],limitations=limitations,failure_records=['INTERRUPTION.json','PACKAGE_BATCH_INTERRUPTION.json','browser_interrupted/','logs/catalog_red.log'],next_action='continue',recommended_next_step=next_step,supervisor_verification='reported_not_independently_verified',resources=dict(cpu_affinity=sorted(__import__('os').sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,nested_models=False,new_dependencies=False,servers_stopped=True))
 js(U/'STATUS.json',status)
 js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,reason='完整对象/局部编辑/冷加载和统一可用入口已覆盖三个实际旧模型；下一独立有用步骤是把同一流程迁移到Ficus，明确薄结构能力边界。',estimated_next_minutes=40,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00'))
 rows='\n'.join(f"| {x['view']} | {x['target_edit_L1']:.2f} | {x['far_edit_L1']:.2f} | {x['authoring_far_L1']:.2f} | {x['target_ink_before']:.2f} / {x['target_ink_after']:.2f} |" for x in v['views'])
 report=f'''# Unit008 — Three-model portable editor

本轮执行 **partial**：统一Chair/Lego/Drums入口、独立模型会话、Lego跨视角选区与局部编辑、真实浏览器、三模型导出与搬移包冷加载均完成。视觉几何仍partial，作者操作有小量远区栅格副作用；H1/H2未测。用时{elapsed:.1f}分钟，源码`{commit}`。

## Review and frozen scope

完整读取BRIEF、大纲、P1/P2报告/NEXT与相关源，以及unit007实际报告、代码和全对象/选面图。Drums细杆碎裂与选区孤岛说明继续追完美部件价值有限。选择统一三个已有模型后验证较清楚的Lego铲斗，保留旧失败，不增加第四模型或几何扫选。详见READING_REVIEW_ZH.md。

SCOPE先冻结三个资产逐文件哈希、构建相机237/327/147°(35°仰角、4.9距离)、四新静态53/143/233/323°(28°、5.1)、12旋转与6缩放。查看三个实际构建代理后，一次确定并冻结三矩形[278,82,409,179]、[250,139,403,256]、[137,79,266,157]，replace/add/add。后续未改选区/风格/几何。原四静态相机已有曝光，新虚拟集不是盲重建评测。

Lego原PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，310475 Gaussian。沿用unit003真实CPU深度TSDF的16543顶点/29999面代理，重新直接渲染原PLY八参考视角。Chair沿用unit002、Drums沿用unit007保存资产；本轮三者均真实冷重绘，但未重建三模型几何，也未重渲染Chair/Drums原PLY。

## Actual behavior and images

新增catalog相对路径入口、Model下拉与逐模型Editor会话；切换保留各模型的草稿/编辑/相机/撤销记录，图片按模型寻址，带错scene的变更请求拒绝。单资产入口保留；CLI同入口支持--scene、--region/--part及四风格参数。尚未提交草稿不能跨服务器重启恢复，需提交并导出。

Lego选面833→1672→2030，较首框新增1197面。最大索引边连通片1948面，共33片；不是完整语义分割，仍含支撑碎片和隐藏遗漏。第二构建视角可见面积2419→12684.5像素，这是选面覆盖，不是语义准确度。原网格顶点/索引未变。

region4角度-25→35，目标210→199条路径，整对象2544→2533条。2334非目标路径与图层保持，来源区未选1785段所有字段精确保留。三角重心自身附着误差最大2.22e-16，不是独立几何正确性。

| View | Target edit L1 | Far edit L1 | Far authoring L1 | Target ink before / after |
|---|---:|---:|---:|---:|
{rows}

mask来自渲染器四子像素任一目标命中，固定2px带。角度编辑八视角远区全部0；创建区域orbit53的远区0.4 L1如实保留，未扩大mask或改渲染器压分。8/8静态与18轨迹完整入框。已查看全部RGB/代理/区域/排线、编辑前后、三选面视角、12/6全帧接触图。铲斗两侧与内侧可分离编辑，车顶保持；底板波浪线、车体孔洞、细杆遗漏与短碎线未改善。

## Tests, cold replay and package

TDD记录真实缺scene_catalog模块失败后，一项真实三模型会话行为通过；另有缺资产/错模型身份/非法scene输入拒绝。Firefox软件渲染通过真实模型下拉、鼠标拾取/三次拖框、键盘命名、跨模型草稿保持、撤销重做/刷新、提交/角度、间距/长度/线宽、资产撤销、Orbit/Zoom及导出。浏览器选面和路径与CLI精确一致。三个模型分别导出，在服务器关闭后新进程重绘PNG和全部数组精确。

portable_demo.tar.gz包含三个实际资产、Lego原三区、配方、精简运行源、预览与视频；搬移解压后用文档入口逐模型preview精确，Lego author→edit→preview也精确，无原PLY依赖。依赖环境未捆绑，其他平台未测。FFV1全部12+6帧解码与PNG精确；不是全路径时序认证或实时性证据。

## Failures and handoff

打包批处理外层143，但stage/archive/extract/portable_replay子收据全部0且冷加载指标完整；未重跑已完成阶段，仅继续原定未启动的包内viewer启动测试并通过。首browser阶段外层143、子进程-2，收到SIGTERM、发送方与原因UNKNOWN；保留browser_interrupted和原日志，自己的浏览器/服务器清理完成。按相同协议重跑浏览器成功，没有科学重试、选区/参数变更或额外时限延长。其余失败/精确返回码见EXECUTION_AMENDMENT与logs。旧unit007清单及输入哈希复核相同；两核/数值单线程/串行，无GPU、凭据、新依赖、嵌套模型、push/merge，自身进程已退出。

运行：`cd {U}/portable_demo && ./run.sh viewer`；三模型冷预览`./run.sh preview --scene chair|lego|drums`，每次选择一个scene。详细命令在包README_ZH和根DEMO_README_ZH，准确实跑命令/返回码在REPRODUCE_ZH。

NEXT=continue：{next_step}
'''
 (U/'REPORT_ZH.md').write_text(report)
 reproduce='# Unit008 — Exact command receipts\n\nCPU-only serial execution. Expected failures and interrupted attempts are retained.\n\n'
 for r in receipts:reproduce+=f"## {r['path']}\n\nReturncode: {r['returncode']}; seconds: {r['seconds']:.3f}\n\n```bash\n{shlex.join(r['command'])}\n```\n\n"
 (U/'REPRODUCE_ZH.md').write_text(reproduce)
 js(U/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent; not independent or blind human',inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit_all_frames.png','media/zoom_all_frames.png','selection/selection_all_views.png','media/three_models.png','browser_complete/01_loaded.png','browser_complete/07_region_saved.png','browser_complete/09_orbit_zoom_export.png'],positives='Complete objects; recognizable bucket surfaces selected across views; actual region angle change, all three scenes usable in one editor.',negatives=limitations,quality='partial'))
 shutil.copy2('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
 js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(current_unit='units/unit_008',execution_state='partial',genuinely_ran_old_model=True,demo_progress=progress,entrypoint=str(U/'portable_demo/run.sh'),package=str(U/'portable_demo.tar.gz'),report=str(U/'REPORT_ZH.md'),next_action='continue',scientific_verdict=status['scientific_verdict'],limitations=limitations,supervisor_verification='reported_not_independently_verified'))
 # Hash only immutable recorded evidence; browser profile/cache/runtime control files are excluded.
 files=[]
 allowed_dirs=('assets','catalog_assets','catalog_reference','construction','renders','source_model','media','selection','metrics','source_snapshot','portable_demo','exported_reload','logs')
 top=['STATUS.json','REPORT_ZH.md','NEXT.json','SCOPE.json','PROTOCOL.json','SELECTION_RECIPE.json','CATALOG.json','SOURCE_LOCK.json','SOURCE_DIFF.patch','REPRODUCE_ZH.md','READING_REVIEW_ZH.md','EXECUTION_AMENDMENT.json','INTERRUPTION.json','PACKAGE_BATCH_INTERRUPTION.json','VISUAL_REVIEW.json','DEPENDENCIES.json','portable_demo.tar.gz']
 candidates=[U/n for n in top]
 for folder in allowed_dirs:candidates.extend(f for f in (U/folder).rglob('*') if f.is_file())
 for folder in ('browser_complete','browser_interrupted'):
  candidates.extend(f for f in (U/folder).iterdir() if f.is_file() and f.suffix in ('.json','.png','.zip','.log'))
 for f in sorted(set(candidates)):files.append(dict(path=str(f.relative_to(U)),sha256=sha(f),bytes=f.stat().st_size))
 js(U/'SHA256_MANIFEST.json',dict(files=files,scope='Finite engineering outputs, failed command receipts and replayable source; excludes mutable browser profile/cache and relocated run scratch.'))
 js(U/'ENGINEERING_SEAL.json',dict(utc=now(),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),files=len(files),execution_state='partial',scientific_seal=False,scope='Three-model usable demo and finite validated replay. Visual quality/semantics/independent geometry/H1/H2 not certified.',reported_not_independently_verified=True))
 print(json.dumps(dict(unit=str(U),execution_state='partial',files=len(files),elapsed_minutes=elapsed,commit=commit)))
if __name__=='__main__':finish()
