"""Finalize unit012 after actual final-archive cold checks, without a scientific seal."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,datetime,shutil,subprocess,os

unit=OUTPUT_ROOT/'units/unit_012';package=unit/'final_archive/portable_demo'
p=json.loads((unit/'PROTOCOL.json').read_text());lock=json.loads((unit/'INPUT_LOCK.json').read_text())
receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in (unit/'logs').glob('*.receipt.json')}
required=['export_tdd_green','export_behavior','browser_exports','original_chair','original_ficus','media_locality','cold_replay_resume',
          'coordinate_visibility_regression','package_final','final_cli_image','final_viewer_chair','final_viewer_ficus']
assert all(receipts[k]['returncode']==0 for k in required)
assert receipts['export_tdd_red']['returncode']==1
cold=json.loads((unit/'metrics/COLD_REPLAY.json').read_text());assert cold['all_png_exact'] and cold['all_arrays_exact']
assert sha(package/'runs/final_cli_image/frames/frame_000_image.png')==sha(unit/'browser/chair_image.png')
final_checks=[]
for scene in ('chair','ficus'):
    output=package/'validation'/('viewer_'+scene)
    result=json.loads((output/'RESULT.json').read_text());state=result['state']
    expected=json.loads((package/f'imports/{scene}_orbit/asset/asset.json').read_text())
    assert state['display']==expected['display'] and state['camera']==expected['viewer_camera']
    frame=output/'session'/Path(state['images']['image'].removeprefix('/image/'))
    assert sha(frame)==sha(unit/'browser'/(scene+'_image.png'))
    final_checks.append(dict(scene=scene,display_camera_exact=True,png_exact=True,cold_viewer=True))
js(unit/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(CLI_current_png_exact=True,viewers=final_checks))
for scene,files in lock['assets'].items():
    for name,digest in files.items():
        for base in (unit/'portable_demo/assets',package/'assets',OUTPUT_ROOT/'units/unit_011/portable_demo/assets'):
            assert sha(base/scene/name)==digest
for scene,entry in p['scenes'].items():assert sha(entry['original']['original_ply'])==entry['original']['sha256']
branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip();assert branch=='partwise-sketch-hatching-models-v04'
resources=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
    task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),unit_bytes=sum(f.stat().st_size for f in unit.rglob('*') if f.is_file()),
    affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,serial=True,branch=branch,
    previous_four_assets_unchanged=True,original_two_PLY_hashes_unchanged=True)
assert resources['root_free_bytes']>=2**30 and resources['hdd_free_bytes']>=10*2**30 and resources['task_bytes']<=20*2**30
cleanup=[json.loads((unit/'browser/CLEANUP.json').read_text())]
for scene in ('chair','ficus'):cleanup.append(json.loads((package/f'validation/viewer_{scene}/CLEANUP.json').read_text()))
pids=[c['pid'] for c in cleanup[0]['children']]+[c['pid'] for c in cleanup[1:]]
live=subprocess.run(['ps','-o','pid=,comm=','-p',','.join(map(str,pids))],capture_output=True,text=True)
resources['own_server_driver_PID_comm_check']=live.stdout.strip();assert not live.stdout.strip()
js(unit/'metrics/FINAL_RESOURCE_INPUT_CHECK.json',resources)
exports=json.loads((unit/'browser/PRESENTATIONS.json').read_text())['exports'];locality=json.loads((unit/'metrics/LOCAL_EDIT.json').read_text())
videos=[]
for scene in ('chair','ficus'):
    for kind in ('orbit','zoom'):
        r=json.loads((unit/f'browser/{scene}_{kind}/PRESENTATION.json').read_text())
        assert r['all_proxy_vertices_inside'] and r['frame_count']==(12 if kind=='orbit' else 6)
        for video in r['videos']:
            assert video['encode_returncode']==video['decode_returncode']==0
            assert video['decoded_frames']==r['frame_count']
            if video['file'].endswith('.mkv'):assert video['all_frames_exact']
        videos.append(dict(scene=scene,kind=kind,frame_count=r['frame_count'],seconds=r['seconds'],videos=r['videos']))
js(unit/'metrics/VIDEO_VALIDATION.json',dict(motion_frames=36,lossless_frames_exact=36,mp4_frames_decoded=36,records=videos))
started=datetime.datetime.fromisoformat('2026-10-22T05:39:30.124865+09:00')
elapsed=(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()/60
progress=dict(available_models=['chair','lego','drums','ficus'],genuinely_ran_old_model=True,
    original_PLY_render_this_unit=['chair','ficus'],original_gaussians={s:json.loads((unit/f'source_model/{s}/RECEIPT.json').read_text())['original_gaussians'] for s in ('chair','ficus')},
    browser_actual_downloads=6,current_PNG_exact=True,complete_motion_frames=36,lossless_video_frames_exact=36,MP4_frames_decoded=36,
    immutable_export_snapshot=True,all_paths_retained_during_export=True,local_edit_non_target_paths_layers_exact=True,
    strict_pixel_locality='PARTIAL; fixed2px residuals retained',cold_replay_png_and_arrays_exact=36,final_archive_CLI_and_two_viewers_exact=True,
    default_four_assets_unchanged=True,visual_quality='partial',scientific_seal=False,
    reasoning='Users can now export the edited real model directly from the browser, share actual frames/video plus the saved asset, and reproduce every camera in a fresh process. Geometry quality is unchanged.')
next_step='在现有Chair完整模型上增加可保存的单区域交叉排线第二方向层：默认关闭，固定基础路径和非目标区域，新增layer/path IDs并支持开关与交叉角度；冻结一个角度/疏密配置，比较整对象实际墨量与局部变化，并通过浏览器导出和冷重放。不扩模型、不把增加墨量称作几何或H2改善。'
status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
    engineering_execution='PASS_AFTER_SUMMARY_SCRIPT_CORRECTION',scientific_verdict='H1_H2_NOT_TESTED_ENGINEERING_PRESENTATION_EXPORT',demo_progress=progress,
    artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','media/source_proxy_regions_edit.png','media/chair_orbit.mp4','media/ficus_orbit.mp4',
        'browser/PRESENTATIONS.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT012_DIFF.patch'],
    tests=dict(real_HTTP_behavior_tests=2,real_Ficus_export_behavior_tests=5,coordinate_visibility_regression_tests=7,
        actual_Firefox=True,command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in receipts.items()}),
    blockers=[],limitations=['Ficus leaf holes/fragments and uneven Chair contours remain; default appearance unchanged.',
        'Authored regions and proxy-relative attachment, no independent geometry truth or H1/H2 claim.',
        'Non-target paths/layers are exact, but strict fixed2px pixel leakage is not zero.',
        '12/6 frame movies are short demonstrations; MP4 is lossy; no continuous temporal certification or real-time performance claim.',
        'Dependencies are not bundled; current Linux CPU environment only.'],
    failures_preserved=['logs/export_tdd_red.receipt.json','logs/cold_replay.log','EXECUTION_AMENDMENT.json'],
    scientific_seal=False,supervisor_verification='reported_not_independently_verified')
js(unit/'STATUS.json',status)
js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
    reason='Complete-object editing, cold reload and shareable export now work. A bounded optional cross-hatch style is a substantive next step toward the original partwise NPR goal; it can reuse the validated demo instead of further frontend-only work.',
    estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
table='\n'.join(f"| {r['scene']} | {r['target_L1']:.6f} | {r['far_other_L1']:.6f} | {r['background_L1']:.6f} | {(r['far_other_L1']+r['background_L1'])/r['total_L1']*100:.5f}% |" for r in locality['frames'])
timings='\n'.join(f"| {r['scene']} | {r['kind']} | {r['frame_count']} | {r['seconds']:.2f} s |" for r in videos)
report=f'''# Unit012：当前真实模型的图片／短动画导出

执行状态 **completed**（本轮导出工程范围）；整体视觉质量仍为 **partial**。约{elapsed:.1f}分钟，未使用额外恢复窗口。当前可直接在浏览器下载保存的排线PNG或旋转/缩放ZIP；搬移包后新进程重绘36/36帧PNG及全部数组精确。H1/H2未测试，科学封存不是交付条件。

## 阅读、选择与输入

完整读取BRIEF、851行原大纲、P1/P2报告/NEXT与相关源、unit011实际输出。Chair编辑明显，Ficus仍有叶片孔洞、碎线和发白；更密几何未证明更好。选择补齐已有四模型的分享流程，几何/默认风格不变。原GT零余量与旧NO_GO保留，详情READING_REVIEW_ZH.md。

协议在实现/比较前冻结于{p['frozen_utc']}，SHA256 `{sha(unit/'PROTOCOL.json')}`。原始Chair PLY SHA `{p['scenes']['chair']['original']['sha256']}`，Ficus SHA `{p['scenes']['ficus']['original']['sha256']}`；精确绝对路径在PROTOCOL.json。两者本轮从原PLY各实渲染一张512RGB/深度，分别256690/284835高斯；原模型没有训练或改写。保存代理各30000面，人工高度区域，不是自动语义。97°/28°/5.2相机与中区95→45°、轮廓35%在执行前冻结，都是工程演示而非盲测。

## 交付行为与真实验证

导出先复制当前asset和所有固定路径，保存当前相机/显示，随后只从快照重绘。PNG保持当前视角；12帧旋转固定一个距离，6帧缩放固定方位/仰角，必要时按全部代理顶点解析后退以留16px边。512/2xAA/6fps；新export/replay CLI与浏览器共享实现。无逐帧路径重生、几何修复、服务上传或静态播放冒充重渲染。

真实Firefox软件渲染完成四模型切换、局部编辑、轮廓显示/撤销/刷新，并实际点击下载Chair/Ficus各PNG、orbit和zoom，共6个文件。PNG与保存视图精确；ZIP带asset、CAMERAS、所有帧/图层数组、MP4、FFV1和清单。两对象36运动帧完整入框，36帧FFV1解码RGB精确；MP4全36帧解码/计数通过，但明确有损。实际全部接触表及整对象RGB/代理/区域/编辑图已审阅，VISUAL_REVIEW.json只作非盲描述性判断。

| Model | Export | Frames | Render + encode + validation time |
|---|---|---:|---:|
{timings}

导出期间路径字节保留；真实局部中区编辑的非目标路径和分层数组精确不变。但proxy标签定义的固定2px带之外仍有残差：

| Model | Target L1 | Far other L1 | Far background L1 | Far / total change |
|---|---:|---:|---:|---:|
{table}

数值为归一化灰度差之和，完整坐标与分母在metrics/LOCAL_EDIT.json。band包含目标边缘，不能把target与band简单相加当成互斥分区。没有扩大容差或将残差抹零。当前两视图不能替代独立部件真值/全面局部性证明。

HTTP真实Chair测试先因缺少接口404失败(rc1)，实现后2项通过(rc0)；5项真实Ficus边界/拟合/损坏重放/缺失视频依赖测试通过，7项坐标/遮挡回归通过。四份浏览器ZIP搬移到新路径，新Python从保存资产重绘全部36帧，PNG和全部数组精确。最终tar再次解压、核对清单，文档CLI导出PNG与浏览器PNG精确；两个独立viewer从下载资产冷启动，样式、相机、显示和PNG精确。

## 失败与限制

冷重放汇总最初在Chair orbit子进程rc0后因重复scene关键字TypeError失败。外层工具报告143，外层收据未写出；汇总子进程数值退出码未知，不补造1。原日志/收据保留在EXECUTION_AMENDMENT.json。移除重复字段后，复核已完成Chair的PNG而不重绘，仅继续其余三个未启动批次；resume rc0。外层143原因未确定。没有并发数值重跑或候选参数重选。

Ficus侧面叶片仍破碎，35%轮廓会发白；Chair边缘/笔触终止不均。导出解决可操作性，不提升真实几何。短视频不是逐笔触持续可见性或完整时序认证；依赖未打包，仅验证当前Linux CPU环境。旧4默认资产与两原PLY哈希复核一致。CPU≤2、数值单线程、串行、无GPU/安装/凭据/环境dump/嵌套代理/push/merge。自有浏览器/服务器进程均已退出，资源余量见metrics/FINAL_RESOURCE_INPUT_CHECK.json。

## 使用与下一步

`cd {unit}/portable_demo && ./run.sh viewer --scene chair`，打开本机8765。完整参数、导出和冷重放见PACKAGE_README_ZH.md。portable_demo.tar.gz包含4真实模型资产、源、实际下载包和预览。source_snapshot及UNIT012_DIFF.patch记录相对本轮起点差异，继承dirty worktree未清理。精确命令/返回码见REPRODUCE_ZH.md和logs/*.receipt.json。

只对实际检查的交付/源/收据建工程哈希清单，scientific_seal=false。NEXT=continue：{next_step}
'''
(unit/'REPORT_ZH.md').write_text(report)
commands=['# 精确执行命令与返回码\n\n来自实际子进程收据；原冷重放外层143/汇总子退出未知另见EXECUTION_AMENDMENT.json。\n']
import shlex
for name,receipt in sorted(receipts.items()):commands.append('\n## '+name+'\n\n```bash\n'+shlex.join(receipt['command'])+'\n```\n\nReturn code: '+str(receipt['returncode'])+'\n')
(unit/'REPRODUCE_ZH.md').write_text(''.join(commands))
rootreadme=f'''# 真实模型分区排线 Demo — unit012

已实跑Chair/Ficus原检查点与四模型浏览器。现在可下载当前PNG、12帧旋转、6帧缩放；下载包携带可编辑资产与相机。36帧搬移冷重绘逐PNG/数组精确，最终压缩包CLI和两个viewer冷启动通过。导出工程完成；Ficus叶片/薄结构和少量局部像素残差仍有限，H1/H2未测试。

```bash
cd {unit}/portable_demo
./run.sh viewer --scene chair
```

打开 http://127.0.0.1:8765 ，保存编辑后使用Export your result。默认四模型不变。

[操作与重放]({unit}/PACKAGE_README_ZH.md) · [报告]({unit}/REPORT_ZH.md) · [便携包]({unit}/portable_demo.tar.gz) · [真实模型整对象对照]({unit}/media/source_proxy_regions_edit.png)。依赖未打包。NEXT=continue，建议增加可选单区域交叉排线层。
'''
(OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(rootreadme)
Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(rootreadme)
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_012',updated_utc=now(),execution_state='completed',demo_progress=progress,
    package=str(unit/'portable_demo.tar.gz'),entrypoint=str(unit/'portable_demo/run.sh'),report=str(unit/'REPORT_ZH.md'),scientific_seal=False,action='continue'))
paths=[]
for directory in ('source_snapshot','media','metrics','source_model'):
    paths.extend(f for f in (unit/directory).rglob('*') if f.is_file())
paths.extend((unit/'logs').glob('*.receipt.json'))
paths.extend(unit/name for name in ('STATUS.json','REPORT_ZH.md','NEXT.json','PROTOCOL.json','INPUT_LOCK.json','SOURCE_BEFORE.json','SOURCE_SNAPSHOT.json',
    'UNIT012_DIFF.patch','INHERITED_WORKTREE.diff','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','READING_REVIEW_ZH.md','VISUAL_REVIEW.json','EXECUTION_AMENDMENT.json','portable_demo.tar.gz','logs/cold_replay.log'))
for name in ('BROWSER_VALIDATION.json','PRESENTATIONS.json','CLEANUP.json','chair_image.png','ficus_image.png','chair_orbit.zip','chair_zoom.zip','ficus_orbit.zip','ficus_zoom.zip'):
    paths.append(unit/'browser'/name)
files={str(f.relative_to(unit)):sha(f) for f in sorted(set(paths))}
assert all(sha(unit/name)==digest for name,digest in files.items())
js(unit/'SHA256_MANIFEST.json',dict(schema='unit012_engineering_integrity_v1',files=files,scientific_seal=False,
    scope='Validated engineering outputs and explicitly retained failure receipts. No independent scientific seal; browser profiles, mutable runtime output and scratch excluded.'))
js(unit/'ENGINEERING_VALIDATION.json',dict(manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),file_count=len(files),verified=True,
    scientific_seal=False,execution_state='completed',elapsed_minutes=elapsed))
print(json.dumps({'execution_state':'completed','elapsed_minutes':elapsed,'verified_engineering_files':len(files),'next':'continue'}))
