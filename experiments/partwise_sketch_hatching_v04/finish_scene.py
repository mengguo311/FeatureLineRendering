"""Unit003 engineering handoff; seal only explicitly selected immutable evidence."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,datetime,shlex
import numpy as np

def finish(unit):
    unit=output_guard(unit);root=runtime.OUTPUT_ROOT
    if (unit/'ENGINEERING_SEAL.json').exists():raise FileExistsError('unit already sealed')
    read=lambda f:json.loads((unit/f).read_text())
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');diag=read('metrics/SOURCE_DIAGNOSTICS.json')
    build=read('metrics/BUILD_REPLAY.json');export=read('metrics/EXPORT_REPLAY.json');portable=read('metrics/PORTABLE_REPLAY.json')
    browser=read('browser_complete/BROWSER_VALIDATION.json');video=read('media/VIDEO_VALIDATION.json')
    assert v['execution_validation']=='PASS'
    assert all(x['status']=='PASS' for x in [build,export,portable,browser])
    assert all(x['all_decoded_frames_exact'] for x in video['videos'])
    assert all(sha(f)==h for f,h in p['inputs_sha256'].items())
    receipts=[]
    for f in sorted((unit/'logs').glob('*.receipt.json')):
        r=json.loads(f.read_text());receipts.append(dict(path=str(f.relative_to(unit)),returncode=r['returncode'],seconds=r['seconds']))
    failures=[r for r in receipts if r['returncode']!=0]
    assert {Path(r['path']).name for r in failures}=={'tdd_red.receipt.json','source_model.receipt.json','viewer_smoke.receipt.json'}
    source=Path(__file__).parent
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-models-v04'
    snap=unit/'source_snapshot';snap.mkdir()
    for f in source.iterdir():
        if f.suffix in ['.py','.cpp','.html']:shutil.copy2(f,snap/f.name)
    js(unit/'SOURCE_LOCK.json',dict(commit=commit,branch=branch,
        files={str(f.relative_to(unit)):sha(f) for f in sorted(snap.iterdir())},protocol_sha256=sha(unit/'PROTOCOL.json')))
    (unit/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','41c6a5cfa98e6dbfc47fc4ad0c524248786d8491','HEAD','--',
        'experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
    for f in (unit/'browser_complete').glob('*.png'):shutil.copy2(f,unit/'media'/('editor_'+f.name))
    prefix=[]
    for f in sorted((unit/'attempt_interrupted/source_model').glob('frame_*.npz')):
        g=unit/'source_model'/f.name
        prefix.append(dict(file=f.name,recovered_sha_same=sha(f)==sha(g)))
    js(unit/'EXECUTION_AMENDMENT.json',dict(utc=now(),failed_commands=failures,
        interruption='source and HTTP attempts received SIGTERM in runner and child (-15), outer143; external sender/cause UNKNOWN',
        recovery='same source/cameras/styles; original outputs preserved in attempt_interrupted; fresh complete serial attempts rc0',
        completed_source_prefix_comparison=prefix,
        cleanup='only own known child groups; ps PID/comm found no remaining members of interrupted groups',
        ancillary='one read-only rg path miss; one documentation apply_patch rejected before mutation; neither used as scientific evidence',
        cache_replay=read('proxy/CACHE_REPLAY.json')['max_abs_errors'],
        cache_interpretation='RGB/alpha/median z/center depth exactly match old source-only arrays; unused expected z differs by 9.536743e-7; not all-arrays exact'))
    review=dict(utc=now(),reviewer='primary agent visual inspection; not independent human evaluation',
        inspected=['media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit_all_frames.png',
                   'media/zoom_all_frames.png','browser_complete/05_reloaded.png','renders/first/frame_000_image.png'],
        all_static_views=8,all_orbit_frames=12,all_zoom_frames=6,
        positives='complete recognizable Lego excavator and base; middle edit visible; upper/lower appearance retained; actual UI usable',
        negatives='side views and rear views reveal missing thin rods, holes and coarse cabin; wavy crowded ground/base hatch and short fragments; height cuts do not isolate bucket from roof',
        decision='usable second-model engineering demo, visual quality partial; no threshold or style sweep')
    js(unit/'VISUAL_REVIEW.json',review)
    baseline=v['anchors']['baseline'];edited=v['anchors']['edited']
    nextstep='在现有Chair/Lego资产和CPU编辑器上增加可保存的人工区域选择/修正（以实际网格face ID和显式空间范围为依据），先让Lego铲斗/车身等指定区域可以独立编辑；保持几何与非目标路径，做一次局部编辑、导出冷加载和完整对象验证。不要把人工区域作者工具称为自动语义分割，不必先扩展第三模型。'
    progress=dict(scene='lego',genuinely_ran_old_model=True,available_models=['chair','lego'],
        original_gaussians=310475,proxy_vertices=16543,proxy_faces=29999,
        baseline_paths=sum(a['paths'] for a in baseline.values()),edited_paths=sum(a['paths'] for a in edited.values()),
        complete_object_comparison_views=8,non_target_paths_and_layers_exact=True,far_edit_delta_all_views=0.,
        actual_browser_test=True,actual_HTTP_controls=6,cold_reload_exact=True,exported_zip_cold_reload_exact=True,
        relocated_package_cold_reload_exact=True,full_original_model_rebuild_exact=True,full_rebuild_seconds=build['seconds'],
        orbit_frames=12,zoom_frames=6,all_video_frames_exact=True,
        reasoning='Chair的完整对象/编辑/冷加载能力已迁移至第二真实旧模型Lego，修复固定Chair视角名、分区阈值、界面标题和包入口；无需训练或GT替代。',
        remaining='coarse proxy, thin-part holes, crowded base hatching, short fragments, authored height regions rather than meaningful independent parts')
    started=datetime.datetime.fromisoformat('2026-10-21T18:00:50.981396+00:00')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
    artifacts=['portable_demo.tar.gz','portable_demo/run.sh','REPRODUCE_ZH.md','assets/baseline/asset.json','assets/edited/asset.json',
      'media/reference_proxy_regions_hatch.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
      'media/editor_05_reloaded.png','metrics/VALIDATION.json','metrics/SOURCE_DIAGNOSTICS.json','metrics/BUILD_REPLAY.json',
      'metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','browser_complete/BROWSER_VALIDATION.json']
    for f in artifacts:
        if f!='REPRODUCE_ZH.md':assert (unit/f).is_file(),f
    status=dict(stage='UNIT003_HANDOFF',execution_state='partial',completed_utc=now(),elapsed_minutes=elapsed,
      scientific_verdict='H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
      engineering_validation='PASS for finite complete-object/edit/browser/export/cold/rebuild checks; appearance remains partial',
      genuinely_ran_old_model=True,demo_progress=progress,source_commit=commit,
      geometry_provenance=p['geometry'],region_provenance=p['region_provenance'],artifacts=artifacts,
      tests_and_command_receipts=receipts,failure_records=['EXECUTION_AMENDMENT.json',*[r['path'] for r in failures]],
      blockers=[],limitations=[review['negatives'],'proxy-relative attachment/locality only; no independent geometry/semantic truth',
        '18-frame offline orbit/zoom is not full temporal or occlusion certification',
        'two externally interrupted attempts retained; recovery succeeded without parameter changes',
        'CPU render takes seconds; no realtime claim; portable environment not bundled'],
      next_action='continue',recommended_next_step=nextstep,supervisor_verification='reported_not_independently_verified',
      seal_scope='validated engineering artifacts and explicit failure receipts, not full scientific certification',
      resources=dict(cpu_affinity=sorted(__import__('os').sched_getaffinity(0)),numeric_threads=1,serial=True,gpu=False,
        nested_models=False,new_dependencies=False,servers_stopped=True))
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=nextstep,demo_progress=progress,
      reason='两真实模型均已可运行；人工高度切分会同时编辑多个实际零件，区域作者能力比继续复制第三场景更能提高局部控制的实用性。',
      ranked_alternatives=['persistent manual region authoring','then one bounded hatch readability change with coverage/ink control','third real model only after usability bottleneck'],
      estimated_next_minutes=35,deadline_jst='2026-10-22T10:00:00+09:00',no_new_science_after_jst='2026-10-22T09:20:00+09:00',science_wrap_jst='2026-10-22T09:45:00+09:00'))
    rows=[]
    for a,b in zip(v['static'],diag['views']):
        rows.append(f"| {a['view']} | {a['target_delta']:.2f} | {a['far_other_delta']:.1f}/{a['far_background_delta']:.1f} | {b['source_alpha_proxy_iou']:.5f} | {b['mean_depth_residual']:.6f} |")
    report=f'''# Unit003 — Lego real-model demo

执行状态 **partial**；真实模型上的完整对象、局部编辑、浏览器、导出、冷加载和单命令重建工程检查通过，外观仍粗糙。用时 {elapsed:.1f} 分钟。源码提交 `{commit}`。完整读取BRIEF、851行大纲、最新P1/P2报告/NEXT与相关源，并实际审阅unit002多视角图。Chair平滑降低路径折痕却使8视角几何一致性变差，故本轮不扫平滑参数，选择真实Lego跨模型迁移。

## Inputs and frozen protocol

原检查点 `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，310,475高斯。协议 `PROTOCOL.json` 在新Lego候选输出前冻结；24训练视角CPU渲染、相同深度门控、0.012体素/0.036截断TSDF，未训练、未用GT或旧失败ink。所得16,543顶点/29,999面；代理底面、薄部件有缺失，不是独立测量。

区域由人工世界z阈值 -0.20 / 0.45 按面中心分配并保存face labels，非语义分割；所有切分均先于候选图。沿真实共享网格边连接平面交线，保留面/重心锚点与path IDs；仅中区45°→95°编辑。基线下/中/上区1123/921/351路径，编辑后中区939，其余1474条不变。基线1377/2395路径小于请求0.22长度的一半，碎线问题明显，未删线改善外观。

修复Chair固定高度阈值、train_r_32名称、标题/标签和导出启动入口。12项行为测试rc0；新区域测试先真实TypeError失败rc1再修复，旧相机/锚点/遮挡测试保留。源缓存RGB、alpha、median z、center depth精确，未用于融合的expected z有最大9.536743e-7差异，因此不称所有缓存数组精确。

## Actual outputs

| View | Target edit L1 | Far other/background L1 | Source-alpha/proxy IoU | Mean source-depth residual |
|---|---:|---:|---:|---:|
{chr(10).join(rows)}

非目标region_1/3文件与图层、深度、轮廓在8视角精确相同。固定2px带外变化均0，目标变化均非零；标签掩码来自当前代理，不是独立语义真值。重心附着最大2.22e-16，只证明实现附着于自身代理。源深度诊断使用同整数像素射线、共同合格分母，每视角排除/缺失数在SOURCE_DIAGNOSTICS；这是同模型估计深度，不是独立几何准确度。原4参考RGBA轮廓IoU另列VALIDATION。历史相机已曝光，新虚拟相机输出前冻结，也不称盲评。

已实际查看全部8视角参考/代理/区域/排线、8对局部编辑、12 orbit及6 zoom接触图，以及Firefox刷新截图。车体与铲斗整体可辨，侧面/后方有杆件缺失与破洞，底板波浪线拥挤，许多短片段，铲斗与车顶仍被同高度规则绑定。没有候选参数扫选；完整对象与弱视角均保留。18轨迹帧均不同且代理完整在框内，FFV1全解码与源PNG逐帧精确；无全路径时序认证。

实际HTTP连续完成角度/间距/长度/线宽/orbit/zoom六操作，非法间距返回422。真实Firefox软件渲染验证场景名/区域标签、角度操作、Orbit/Zoom和刷新控件保持。服务器关闭后下载ZIP由新CLI进程冷加载，PNG与全部数组精确；搬移后的tar包 `./run.sh preview` 也精确。`demo.py build --scene lego` 实际从原PLY重新渲染24视角→TSDF→路径→首图，{build['seconds']:.2f}s，mesh、3区域路径和PNG/NPZ逐文件精确。

## Failure receipts and delivery

source_model和viewer_smoke首尝试收到SIGTERM：runner记录signal15、child rc-15、外层143，发送方/原因UNKNOWN。原日志及部分输出保留 `attempt_interrupted/`，检查仅自身进程组无残留；相同参数的完整恢复均rc0。没有更改科学配置、复制另一个模型或改写失败码。运行期间不再开展新的科学候选，恢复与封存均在原55分钟内；没有使用额外延长窗口。

全部精确命令与子返回码在 `logs/*.receipt.json` 和 `REPRODUCE_ZH.md`。可运行包 `portable_demo.tar.gz` 包含真实资产/源码/预览；入口 `portable_demo/run.sh`；浏览器证据 `browser_complete/`，完整对照与视频 `media/`，指标 `metrics/`。CPU两核、数值单线程、串行、无GPU/新依赖/嵌套模型；服务器及浏览器已关闭。源PLY/照片/旧单元/只读orchestration输入哈希复核未变。只封存验证过的工程产物和明确失败收据，不把中断数组列为成功科学证据。

NEXT=`continue`：{nextstep} H1/H2未测试；历史P1 NO_GO、P2 ZERO_HEADROOM不改写，监督状态reported_not_independently_verified。
'''
    (unit/'REPORT_ZH.md').write_text(report)
    commands=['# 实际命令与返回码\n\n以下按启动时间排列；失败尝试原样保留。数值调用均由CPU串行runner执行。\n']
    allreceipts=sorted([json.loads(f.read_text()) for f in (unit/'logs').glob('*.receipt.json')],key=lambda r:r['start_utc'])
    for r in allreceipts:commands.append(f"\n`{r['start_utc']}` — rc `{r['returncode']}`，{r['seconds']:.3f}s\n\n```bash\n{shlex.join(r['command'])}\n```\n")
    (unit/'REPRODUCE_ZH.md').write_text(''.join(commands))
    shutil.copy2(Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md'),root/'DEMO_README_ZH.md')
    delivery=dict(updated_utc=now(),execution_state='partial',working_demo=True,current_unit='units/unit_003',
        available_models={'chair':'units/unit_002/portable_demo.tar.gz','lego':'units/unit_003/portable_demo.tar.gz'},
        start_command='cd '+str(unit/'portable_demo')+' && ./run.sh viewer',demo_progress=progress,
        report='units/unit_003/REPORT_ZH.md',next_action='continue',recommended_next_step=nextstep,
        supervisor_verification='reported_not_independently_verified',scientific_verdict=status['scientific_verdict'])
    js(root/'DELIVERY_STATUS.json',delivery);js(unit/'DELIVERY_STATUS_SNAPSHOT.json',delivery)
    shutil.copy2(root/'DEMO_README_ZH.md',unit/'DEMO_README_ZH_SNAPSHOT.md')
    selected=[]
    for folder in ['assets','proxy','source_model','renders','metrics','media','source_snapshot']:
        selected.extend(f for f in (unit/folder).rglob('*') if f.is_file())
    selected.extend((unit/'logs').glob('*.receipt.json'))
    selected.extend((unit/'logs').glob('*.log'))
    selected.extend((unit/'browser_complete').glob('*.json'))
    selected.extend((unit/'browser_complete').glob('*.png'))
    for name in ['PROTOCOL.json','INVENTORY.json','DEPENDENCIES.json','STATUS.json','REPORT_ZH.md','NEXT.json',
        'SOURCE_LOCK.json','SOURCE_DIFF.patch','EXECUTION_AMENDMENT.json','VISUAL_REVIEW.json','REPRODUCE_ZH.md',
        'DELIVERY_STATUS_SNAPSHOT.json','DEMO_README_ZH_SNAPSHOT.md','portable_demo.tar.gz']:
        selected.append(unit/name)
    files=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(selected))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),scope=status['seal_scope'],files=files,
       excluded='mutable browser profiles/session caches, runner final response, orchestration scratch, interrupted arrays, relocated runtime outputs'))
    for f in files:assert sha(unit/f['path'])==f['sha256']
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),manifest='SHA256_MANIFEST.json',manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
        file_count=len(files),source_commit=commit,execution_state='partial',scientific_seal=False,
        scope=status['seal_scope'],supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(status=str(unit/'STATUS.json'),files=len(files),elapsed_minutes=elapsed,next_action='continue')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);finish(p.parse_args().unit)
