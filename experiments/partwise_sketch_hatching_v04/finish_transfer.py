"""Report verified finite engineering results; integrity seal is not a scientific seal."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,datetime,shlex,os

def finish(unit):
    unit=output_guard(unit);read=lambda name:json.loads((unit/name).read_text())
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');proxy=read('proxy/PROXY.json')
    media=read('media/VIDEO_VALIDATION.json');source=read('metrics/SOURCE_DIAGNOSTICS.json')
    for name in ['metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','metrics/PORTABLE_VIEWER.json',
                 'metrics/EXPORTED_VIEWER_REOPEN.json','browser_complete/BROWSER_VALIDATION.json']:
        assert read(name)['status']=='PASS',name
    assert all(x['all_decoded_frames_exact'] for x in media['videos'])
    assert all(v['input_hashes_unchanged'].values())
    assert read('RESOURCE_FINAL.json')['all_checked_groups_empty']
    for path,digest in p['inputs_sha256'].items():assert sha(path)==digest,path
    for scene,entry in read('CATALOG_INPUTS.json')['scenes'].items():
        for filename,digest in entry['files'].items():assert sha(Path(entry['source'])/filename)==digest
    receipts=[]
    for f in (unit/'logs').glob('*.receipt.json'):
        row=json.loads(f.read_text());receipts.append(dict(path=str(f.relative_to(unit)),**row))
    receipts.sort(key=lambda r:r['start_utc'])
    for f in (unit/'logs').glob('*.start.json'):assert f.with_name(f.name.replace('.start.json','.receipt.json')).exists()
    expected_failures={'scene_identity_red':1,'viewer_asset_red':1,'viewer_smoke':-15,'exported_cold_reload':1,'portable_replay':-15}
    for row in receipts:
        name=Path(row['path']).name.removesuffix('.receipt.json')
        assert row['returncode']==expected_failures.get(name,0),(name,row['returncode'])
    base=v['anchors']['baseline'];edited=v['anchors']['edited']
    full_static=sum(f['bounds']['all_proxy_vertices_inside'] for f in read('renders/static_edited/RENDER_RECEIPT.json')['frames'])
    counts=dict(baseline_paths=sum(x['paths'] for x in base.values()),edited_paths=sum(x['paths'] for x in edited.values()),
                retained_non_target_paths=base['1']['paths']+base['3']['paths'])
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T19:45:09.784501+00:00')).total_seconds()/60
    negatives=[
        'Ficus leaves/branches are perforated, fragmented and noisy; tall stems and leaf outlines crowd together. Height regions are authored, not pot/trunk/leaf semantics.',
        '1165 of 1422 baseline paths are shorter than half the requested .22 world length; a successful loader does not establish visual quality.',
        'Strict center-label locality has 0.2 L1 residual at orbit251 pixel(204,299); same-proxy 2x reraycast gives labels [[2,2],[3,3]]. Original fixed-2px-band failure retained.',
        'Proxy-relative anchors, source-model depths and label masks are not independent geometry/semantics. Historical views are exposed; no H1/H2 or full temporal certification.',
        'Per-scene drafts/undo last only for the server session. Committed exported assets can now reopen through run.sh viewer --asset. Python environment is not bundled; other platforms untested.'
    ]
    progress=dict(available_models=['chair','lego','drums','ficus'],genuinely_ran_old_model=True,
        original_PLY_render_this_unit=['ficus'],saved_asset_cold_render_this_unit=['chair','lego','drums','ficus'],
        new_model='ficus',original_gaussians=read('INVENTORY.json')['count'],build_cameras=len(p['build_cameras']),
        proxy_vertices=proxy['vertices'],proxy_faces=proxy['faces'],**counts,
        non_target_paths_and_layers_exact=True,static_views=len(v['static']),complete_object_static_views=full_static,
        orbit_frames=12,zoom_frames=6,all_trajectory_views_complete=True,all_video_frames_decoded_exact=True,
        actual_browser_four_model_switch_and_ficus_edit=True,all_four_HTTP_style_controls=True,
        exported_asset_cold_reload_exact=True,relocated_four_models_cold_reload_exact=True,
        exported_asset_reopened_in_portable_viewer_exact=True,standalone_edit_scene_identity_guard=True,
        visual_quality='partial',strict_locality=v['execution_validation'],scientific_seal=False,
        reasoning='Fourth actual old model now runs through fixed 3D paths, local edit, orbit/zoom, unified browser and portable cold reload. Explicit saved/exported asset reopen is fixed and actually tested.')
    next_step='在Ficus上做一次有预算的简化消融：复用本轮24份冻结qualified depths和同一TSDF/门控，仅把30k面简化替换为保留清理后的约137k面（硬上限150k）的单个候选；先把fuse_cpu硬编码预算改成可校验的显式参数。固定风格/高度区规则/已有对照，预先冻结新的展示视角，比较完整对象叶片孔洞、轮廓碎裂、短路径比例与墨量/覆盖及CPU代价；保留当前30k基线，只有实际图像有用才接入目录，再验证局部编辑/导出/冷加载。禁止扫参数、补GT或把同源深度当独立真值。'
    status=dict(stage='UNIT009_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
        engineering_validation='RUNNABLE_WITH_DISCLOSED_LOCALITY_RESIDUAL_AND_RECOVERED_INTERRUPTION',
        genuinely_ran_old_model=True,demo_progress=progress,blockers=[],limitations=negatives,
        source_state='Validated working-tree changes; source_snapshot and SOURCE_LOCK are replay authority, not an unmodified parent Git commit.',
        artifacts=['portable_demo.tar.gz','portable_demo/run.sh','CATALOG.json','assets/baseline/asset.json',
            'assets/edited/asset.json','media/four_models.png','media/reference_proxy_regions_hatch.png',
            'media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv','metrics/VALIDATION.json',
            'metrics/LOCALITY_RESIDUAL_DIAGNOSTIC.json','metrics/PORTABLE_REPLAY.json',
            'metrics/EXPORTED_VIEWER_REOPEN.json','SOURCE_LOCK.json','REPRODUCE_ZH.md'],
        tests_and_command_receipts=[{k:r[k] for k in ('path','returncode','seconds')} for r in receipts],
        failure_records=['INTERRUPTION.json','HTTP_INTERRUPTION.json','PACKAGE_INTERRUPTION.json','tests/scene_identity_red/RESULT.json',
                         'tests/viewer_asset_red/RESULT.json','viewer_smoke_interrupted/'],
        next_action='continue',recommended_next_step=next_step,supervisor_verification='reported_not_independently_verified',
        resources=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,
                       nested_models=False,new_dependencies=False,servers_stopped=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='Complete-object/edit/cold-reload/usability now cover all four available real models. Ficus quality is the main new negative; the 137354→30000 face reduction is a concrete single-variable candidate before attempting a new reconstruction method.',
        estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00'))
    report=f'''# Unit009 — Ficus and portable saved-asset reopen

执行状态 **partial**，用时{elapsed:.1f}分钟。新增第四个真实旧模型Ficus，完成全对象、局部编辑、12旋转/6缩放、四模型浏览器、导出与搬移包冷加载。修复独立edit场景身份检查及portable viewer忽略--asset两个实际缺陷。几何外观仍partial，H1/H2未测试。

## Inputs and protocol

已完整读BRIEF、851行大纲、P1/P2报告/NEXT及相关源；实际审阅unit008全对象与局部编辑图后选择单次Ficus迁移，理由见READING_REVIEW_ZH.md。原PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，284835 Gaussian。没有GT替换、训练或旧ink输入；原vanilla GS不是新训练的RaDe-GS。

冻结24训练相机，从train_r_7起按方向最远点选择；4原数据相机加71/161/251/341°新虚拟视角，22°仰角/5.1距离。原视角历史曝光，新相机也不是独立重建留出数据。固定alpha≥.95、中心深度差≤.06、3x3跳变≤.08，voxel .012、TSDF截断.036、删<40面连通片、简化30k。一次构建71.93秒，18314顶点/30000面；清理前148300面，删10946面后137354面再简化。高度阈值-.4/.4是人工风格区，不是盆/干/叶语义。

## Actual outputs and locality

{full_static}/8静态与18/18运动帧均完整入框。baseline1422→edited1425路径，中区角度45→95、330→333路径，1092非目标路径/分层精确保持。所有固定路径按面索引与重心坐标保存；自身附着误差≤2.22e-16，不是独立表面精度。1165/1422基线路径短于请求长度一半，说明碎片严重。4个参考RGB轮廓IoU范围0.7161–0.7365，仅描述代理与参考mask差异。

| View | Target edit L1 | Far other L1 | Far background L1 |
|---|---:|---:|---:|
'''
    for r in v['static']:report+=f"| {r['view']} | {r['target_delta']:.2f} | {r['far_other_delta']:.2f} | {r['far_background_delta']:.2f} |\n"
    report+='''
orbit251的固定2px带外0.2 L1（占总变化0.0404%）严格失败保留，未扩大mask。原分数用每像素一个label，而同一代理原2xAA射线诊断显示该像素四子像素标签[[2,2],[3,3]]；中区层变化，上区层仍相同。此解释不是独立语义证明，也不覆盖原测试失败。

实际查看全部八组RGB/代理/区域/排线、八组前后编辑、12/6全帧接触图、四模型和浏览器截图。盆形及大轮廓可辨，叶片打洞、断枝、线条纠缠和短碎线很明显；局部角度效果被轮廓噪声部分遮住。18帧FFV1全部解码RGB精确；没有全笔触时序对应/实时性结论。

## Tests and usable delivery

两个真实TDD red→green：Chair资产在--scene ficus下被错误接受；Ficus viewer --asset edited被忽略而加载baseline。最小修复后分别在输出前拒绝、实际加载显式资产及其保存相机。Firefox软件渲染实测Ficus角度、四模型切换后恢复编辑、Orbit/Zoom/刷新。HTTP四风格控制及相机操作均改变真实图像、保留其他区；单次约2.0–2.2秒，非法spacing返回422。

导出ZIP在服务器退出后新进程重绘PNG/所有数组精确。portable_demo.tar.gz解压到新路径后四模型冷预览精确，Ficus高层CLI改回45°重现基线。搬移包实际四模型viewer启动/切换通过；实际HTTP导出资产复制至包内，经run.sh viewer --asset冷打开，与导出前PNG/数组精确。依赖环境未打包，其他平台未测。

## Failures and reproducibility

保留stills外层143而source子rc0、静态尚未启动的记录，仅续跑未启动静态。HTTP控件首轮外层143/子-15，收到SIGTERM，发送方/原因UNKNOWN；误执行的依赖export因ZIP未生成rc1。保留原收据和中断输出，确认原进程组为空后仅一次同参数HTTP恢复成功，再完成导出；总时限未延长。恢复重新打开了共享viewer_server.log，首轮服务器stdout未保留，此限制已披露。新增SIGTERM处理只清理本测试子服务器。两个TDD rc1是预期失败，均保留。详见INTERRUPTION.json、HTTP_INTERRUPTION.json和logs。

包内replay批处理也收到SIGTERM（外143/子-15），仅留下Chair/Lego完整输出，内部各子退出码未落盘UNKNOWN。原输出存runs_interrupted；仍在同一次≤10分钟工程恢复窗口中，四模型按独立收据执行并验证，再继续未完成的edit/preview/viewer测试。没有几何重建、参数重选或科学重试。PACKAGE_INTERRUPTION保留原失败。

所有数值任务串行、两核/数值单线程，无GPU/新依赖/凭据/嵌套模型/push/merge。旧输入与unit008记录及被复制资产逐文件哈希复核相同。源码快照和SOURCE_LOCK保存完整可重放源；工程hash清单只表达完整性，不是科学seal。精确实跑命令/退出码在REPRODUCE_ZH.md。

运行：进入本unit的portable_demo目录，执行 `./run.sh viewer --scene ficus`。显式重开保存资产用 `./run.sh viewer --scene ficus --asset /绝对路径/资产目录`；详细操作见根DEMO_README_ZH.md及包README_ZH.md。

NEXT=continue：'''+next_step+'\n'
    (unit/'REPORT_ZH.md').write_text(report)
    (unit/'REPRODUCE_ZH.md').write_text('# Actual commands and return codes\n\n'+''.join(
        f"## {Path(r['path']).name}\n\nReturn code: {r['returncode']}; seconds: {r['seconds']:.3f}.\n\n```bash\n{shlex.join(r['command'])}\n```\n\n" for r in receipts)+
        '\n外层143另见INTERRUPTION/HTTP_INTERRUPTION。重放须用新unit目录；同名输出保护会拒绝覆盖，不能顺次重跑故意red到green的历史版本。\n')
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent; not independent or blind human',
        inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit_all_frames.png',
                   'media/zoom_all_frames.png','media/four_models.png','browser_complete/01_loaded.png','browser_complete/02b_catalog_restored.png'],
        positives='Recognizable complete Ficus, persistent saved asset, all four models operable and reloadable.',negatives=negatives,quality='partial'))
    # Runtime/source snapshots are immutable copies; exclude browser profiles and mutable orchestration.
    here=Path(__file__).resolve().parent;snapshot=unit/'source_snapshot';snapshot.mkdir(exist_ok=False)
    for f in here.iterdir():
        if f.is_file() and f.suffix in ('.py','.cpp','.html'):shutil.copy2(f,snapshot/f.name)
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    diff=subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True)
    (unit/'SOURCE_DIFF.patch').write_text(diff)
    js(unit/'SOURCE_LOCK.json',dict(git_head=head,working_source_snapshot={f.name:sha(f) for f in snapshot.iterdir()},
        replay_source='source_snapshot, including new untracked unit scripts; Git diff alone is not the full snapshot'))
    readme='当前交付：unit009，四真实模型，Ficus外观partial。\n\n```bash\ncd '+str(unit/'portable_demo')+'\n./run.sh viewer --scene ficus\n```\n\n'+(unit/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),current_unit=unit.name,execution_state='partial',
        demo_progress=progress,package=str(unit/'portable_demo.tar.gz'),package_sha256=sha(unit/'portable_demo.tar.gz'),
        report=str(unit/'REPORT_ZH.md'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),scientific_seal=False,next_action='continue'))
    names=['STATUS.json','REPORT_ZH.md','NEXT.json','PROTOCOL.json','ENGINEERING_ADDENDUM.json',
           'READING_REVIEW_ZH.md','INVENTORY.json','DEPENDENCIES.json','REPRODUCE_ZH.md','VISUAL_REVIEW.json',
           'SOURCE_LOCK.json','SOURCE_DIFF.patch','CATALOG.json','CATALOG_INPUTS.json',
           'INTERRUPTION.json','HTTP_INTERRUPTION.json','PACKAGE_INTERRUPTION.json','EXECUTION_AMENDMENT.json',
           'RESOURCE_FINAL.json','portable_demo.tar.gz','PACKAGE_README_ZH.md']
    files=[unit/n for n in names]
    for folder in ('assets','metrics','media','renders','source_snapshot','portable_demo'):
        files.extend(f for f in (unit/folder).rglob('*') if f.is_file())
    files.extend(unit/r['path'] for r in receipts)
    files.extend(unit/f'logs/{Path(r["path"]).name.removesuffix(".receipt.json")}.log' for r in receipts)
    files.extend([unit/'browser_complete/BROWSER_VALIDATION.json',unit/'browser_complete/CLEANUP.json'])
    entries=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(files))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),files=entries,scope='Integrity of validated finite evidence plus explicitly preserved failure records; excludes mutable browser profiles and orchestration'))
    for entry in entries:assert sha(unit/entry['path'])==entry['sha256']
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),manifest='SHA256_MANIFEST.json',manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
        files=len(entries),scientific_seal=False,execution_state='partial',scope='Finite engineering evidence/integrity only; strict locality residual and visual limitations retained'))
    print(json.dumps(dict(execution_state='partial',elapsed_minutes=elapsed,manifest_files=len(entries),demo_progress=progress)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);finish(p.parse_args().unit)
