"""Finalize finite evidence, preserving rejected candidate and interrupted exits."""
import runtime
from runtime import OUTPUT_ROOT,output_guard,sha,js,now
from pathlib import Path
import argparse,json,shutil,subprocess,os,datetime,shlex,importlib.metadata


def finish(unit):
    unit=output_guard(unit);read=lambda f:json.loads((unit/f).read_text())
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    p=read('PROTOCOL.json');v=read('metrics/VALIDATION.json');comparison=read('metrics/SIMPLIFICATION_COMPARISON.json')
    original=comparison['arms']['original'];candidate=comparison['arms']['baseline'];decision=read('DECISION.json')
    assert not decision['promote_candidate']
    for name in ('metrics/EXPORT_REPLAY.json','metrics/PORTABLE_REPLAY.json','metrics/PORTABLE_VIEWER.json',
                 'metrics/EXPORTED_VIEWER_REOPEN.json','browser_recovery/BROWSER_VALIDATION.json'):
        assert read(name)['status']=='PASS',name
    assert all(x['all_decoded_frames_exact'] for x in read('media/VIDEO_VALIDATION.json')['videos'])
    assert all(v['input_hashes_unchanged'].values())
    for f,digest in p['inputs_sha256'].items():assert sha(f)==digest,f
    package_inputs=read('metrics/PACKAGE_INPUTS.json')
    for f,digest in package_inputs['files'].items():assert sha(Path(package_inputs['source'])/f)==digest,f
    for f in (unit/'portable_demo/assets/ficus').iterdir():
        if f.is_file():assert sha(f)==package_inputs['files']['assets/ficus/'+f.name]
    assert sha(unit/'portable_demo/CATALOG.json')==package_inputs['files']['CATALOG.json']
    receipts=[];groups=set()
    for f in sorted((unit/'logs').glob('*.receipt.json')):
        r=json.loads(f.read_text());name=f.name.removesuffix('.receipt.json')
        assert r['returncode']==(1 if name=='fusion_red' else 0),(name,r['returncode'])
        receipts.append(dict(path=str(f.relative_to(unit)),**r))
    missing=[]
    for f in (unit/'logs').glob('*.start.json'):
        r=json.loads(f.read_text());groups.add(r['own_process_group'])
        if not f.with_name(f.name.replace('.start.json','.receipt.json')).exists():missing.append(str(f.relative_to(unit)))
    assert missing==['logs/browser.start.json'],missing
    for folder in ('browser_complete','browser_recovery'):
        groups.update(x['pid'] for x in read(folder+'/CLEANUP.json')['children'])
    groups.add(read('metrics/PORTABLE_VIEWER_START.json')['own_process_group'])
    groups.add(read('relocated/portable_demo/runs/exported_viewer/CLEANUP.json')['pid'])
    checked=[]
    for pid in sorted(groups):
        try:os.killpg(pid,0);exists=True
        except ProcessLookupError:exists=False
        checked.append(dict(own_process_group=pid,exists=exists))
    assert not any(x['exists'] for x in checked),checked
    resource=dict(utc=now(),cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,serial=True,
        gpu=False,nested_models=False,new_dependencies=False,all_checked_groups_empty=True,checked_own_groups=checked,
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
        total_task_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()))
    js(unit/'RESOURCE_FINAL.json',resource)
    js(unit/'DEPENDENCIES.json',dict(python=__import__('platform').python_version(),packages={k:importlib.metadata.version(k)
        for k in ('numpy','scipy','Pillow','open3d','scikit-image','plyfile')},new_dependencies=False))
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T20:03:31.917644+00:00')).total_seconds()/60
    base=v['anchors']['baseline'];edited=v['anchors']['edited']
    negatives=['Ficus canopy remains perforated and cluttered. Higher face count was not adopted; both proxies are exploratory.',
        'Strict locality residual: train_r_7 pixel(y=327,x=254), far-other L1 0.20000002, fraction 0.00023026. Fixed 2px band retained. Non-target paths and layers are exact; no new subpixel diagnosis claimed.',
        'Height regions are authored, not semantic parts; self-proxy attachment and same-model depths are not independent truth. No H1/H2 or full temporal certification.',
        'Outer interactive wrapper rc143; first browser child exit UNKNOWN because its receipt is missing, despite validation/cleanup files. One same-parameter browser recovery passed. Cause/sender unknown.',
        'Python environment is not bundled; other platforms untested. Per-scene drafts/undo last only for the server session.']
    progress=dict(available_models=['chair','lego','drums','ficus'],genuinely_ran_old_model=True,
        original_PLY_render_this_unit=['ficus'],original_gaussians=read('source_model/MODEL_IMPORT.json')['audit']['count'],
        reused_qualified_depths=24,default_ficus_faces=30000,experimental_ficus_faces=candidate['faces'],
        candidate_promoted=False,comparison_complete=True,comparison_views=8,
        candidate_baseline_paths=candidate['total_paths'],candidate_edited_paths=sum(x['paths'] for x in edited.values()),
        retained_non_target_paths=base['1']['paths']+base['3']['paths'],non_target_paths_and_layers_exact=True,
        complete_object_static_views=sum(x['complete_object'] for x in candidate['frames']),orbit_frames=12,zoom_frames=6,
        all_motion_frames_complete=True,all_video_frames_decoded_exact=True,actual_browser_four_model_switch_and_edit=True,
        HTTP_four_style_controls=True,exported_asset_cold_reload_exact=True,relocated_four_model_previews_exact=True,
        relocated_candidate_preview_and_edit_exact=True,exported_asset_reopened_in_portable_viewer_exact=True,
        strict_locality=v['execution_validation'],visual_quality='partial',scientific_seal=False,
        reasoning='Corrected ignored face-budget configuration and ruled out one costly simplification-only quality fix. Preserved usable four-model default; shipped the fully exercised alternative as experimental, with complete-object/edit/reload evidence.')
    next_step='在保留30k真实模型资产与固定3D排线路径的前提下，增加独立的视角轮廓显示/强度控制（保存到资产并支持导出冷重开）；先冻结一个轮廓减弱候选与不变排线墨量控制，在完整Ficus和一个Chair视角组比较可读性，检验是否让局部排线编辑更可见。只改显示层，不补孔/改网格/重新采路径，不称几何修复、结构线恢复或H2成功。若无视觉收益仍保留用户开关和原默认值。'
    status=dict(stage='UNIT010_HANDOFF',execution_state='partial',bounded_comparison_execution='completed',completed_utc=now(),elapsed_minutes=elapsed,
        scientific_verdict='SIMPLIFICATION_CANDIDATE_NOT_ADOPTED; H1_H2_NOT_TESTED; historical P1 NO_GO and P2 ZERO_HEADROOM unchanged',
        engineering_validation='RUNNABLE_WITH_DISCLOSED_LOCALITY_RESIDUAL_AND_RECOVERED_WRAPPER_INTERRUPTION',
        genuinely_ran_old_model=True,demo_progress=progress,blockers=[],limitations=negatives,
        artifacts=['portable_demo.tar.gz','portable_demo/run.sh','DECISION.json','media/simplification_historical_views.png',
            'media/simplification_new_views.png','media/local_edit_all_views.png','media/orbit.mkv','media/zoom.mkv',
            'assets/edited/asset.json','metrics/SIMPLIFICATION_COMPARISON.json','metrics/VALIDATION.json',
            'metrics/PORTABLE_REPLAY.json','metrics/EXPORTED_VIEWER_REOPEN.json','SOURCE_LOCK.json','REPRODUCE_ZH.md'],
        tests_and_command_receipts=[{k:r[k] for k in ('path','returncode','seconds')} for r in sorted(receipts,key=lambda x:x['start_utc'])],
        missing_child_returncodes=missing,failure_records=['logs/fusion_red.receipt.json','tests/fusion_red/RESULT.json','INTERRUPTION.json'],
        next_action='continue',recommended_next_step=next_step,resources=resource,
        source_state='Validated working-tree snapshot; inherited unit009 WIP preserved, no commit/push/merge.',
        supervisor_verification='reported_not_independently_verified')
    js(unit/'STATUS.json',status)
    js(unit/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='Dense geometry doubles CPU cost and increases short fragments without clear readability gain. Contour dominance is visible across actual frames; an independent saved display control is a bounded usability step with unchanged hatch evidence.',
        estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    report=f'''# Unit010 — Ficus face budget and honest partial delivery

执行状态 **partial**；一次有界简化消融已完整执行，用时{elapsed:.1f}分钟。修复融合器忽略协议面数预算的问题；137354面候选未明显改善叶片可读性，成本更高，**不晋级默认目录**。保留原四模型demo，另交付可编辑/导出/冷加载的实验资产。H1/H2未测试。

## Inputs and fixed comparison

完整读取BRIEF/851行大纲/P1与P2报告、NEXT及相关源码，实际审阅unit009图像，理由见READING_REVIEW_ZH.md。原Ficus PLY `{p['original']['original_ply']}`，SHA256 `{p['original']['sha256']}`，284835个原Gaussian。复用unit009的24份冻结qualified depths，逐文件哈希相同；本轮另从原PLY实际渲染8相机RGB/深度。原源渲染器libsource.so复用且记录哈希。

仅把simplify_faces从30000改为150000上限：原148300面，删10946个小连通片面后保留137354面/83023顶点。TSDF voxel .012、截断.036、alpha .95、中心差.06、3x3跳变.08、40面连通片门槛、人工高度区-.4/.4及风格不变。跨网格重新生成所有路径，不把相同整数ID当对应。4历史相机加预先冻结83/173/263/353°虚拟相机，22°仰角/5.1距离；历史曝光与同源深度限制明确，不是盲测或独立几何真值。

## Actual comparison

| Measure | 30k baseline | 137354 candidate |
|---|---:|---:|
| Saved paths | {original['total_paths']} | {candidate['total_paths']} |
| Paths shorter than half requested length | {original['short_paths']} ({original['short_paths']/original['total_paths']:.2%}) | {candidate['short_paths']} ({candidate['short_paths']/candidate['total_paths']:.2%}) |
| Total path length (world) | {original['length_world']:.4f} | {candidate['length_world']:.4f} |
| Median frame time (seconds) | {original['median_render_seconds']:.4f} | {candidate['median_render_seconds']:.4f} |

| View | Hatch ink 30k → 137k | Total ink 30k → 137k | Foreground pixels 30k → 137k |
|---|---:|---:|---:|
'''
    for a,b in zip(original['frames'],candidate['frames']):
        report+=f"| {a['view']} | {a['hatch_ink']:.1f} → {b['hatch_ink']:.1f} | {a['total_ink']:.1f} → {b['total_ink']:.1f} | {a['foreground_pixels']} → {b['foreground_pixels']} |\n"
    report+='''
实际检查全部8组RGB/代理/排线及原生512图。高面数保留更多细碎表面，叶冠仍多孔、边缘拥挤；train_r_7/test_r_1与83/263°没有有说服力的完整对象可读性收益。保留细节不等于叶片拓扑正确；不靠少画抬分，墨量/可见区域/短路径/CPU成本均报告。逐区域覆盖、参考alpha IoU、图像mask孔洞与连通片详见metrics/SIMPLIFICATION_COMPARISON.json；图像空隙包含真实叶间空隙，不能解释成几何误差计数。DECISION.json保留非盲主代理判断，未扫参数。

## Local edit, motion and runnable package

候选中区45→95°，536→481条目标路径，1629条非目标路径、分层数组及网格精确保持。8/8静态和18/18轨迹均完整入框；同代理附着误差≤2.22e-16，只是实现约束。新进程重绘PNG/8组数组精确。12旋转/6缩放FFV1全部18帧逐帧解码RGB精确，全帧接触表已检查；不是全路径时序认证。

严格固定2px带外残差保留：train_r_7的(y327,x254)非目标像素L1=0.20000002，占总变化0.023026%，其他7视角远区/背景0。没有扩大mask或改图过关，也没有声称此次进行了独立子像素归因。

Firefox软件渲染实测四模型切换、候选中区编辑、Orbit/Zoom和刷新恢复；HTTP角度/间距/长度/线宽及相机均改变实际图像，非目标区域路径保持，非法spacing返回422。导出ZIP后服务器停止，新进程和搬移包viewer --asset都精确重现导出前图像/数组。portable_demo.tar.gz解压到新路径后，四默认模型与实验候选冷预览精确；候选CLI角度改回45°重现基线。默认四模型CATALOG和Ficus资产逐文件与unit009相同。依赖环境不打包，其他平台未测。

## Failures, scope and replay

真实Ficus fusion TDD red rc1：请求150000仍输出30000；最小修复后green rc0输出137354。七个非法预算拒绝；默认值仍30000，上限150000。media.py仅阻止非平滑实验被错误标为Chair/smoothing对照。

interactive外层rc143，第一次browser子退出码UNKNOWN，因为run_logged收据未落盘；原浏览器稍后产生PASS及清理文件，不能由此补造退出码。原因/信号发送方未知。确认原自有进程组均为空后，在同一次≤10分钟工程恢复窗口内用同参数browser_recovery重跑rc0，再执行尚未启动的HTTP/export/package。原失败及缺失收据保留在INTERRUPTION.json。没有科学重建重试或候选改选。

所有数值串行、CPU≤2/单线程、无GPU/安装/凭据读取/嵌套模型或代理/push/merge。旧输入、旧包及旧记录重新哈希不变；source_snapshot和SOURCE_LOCK是可重放源，Git diff包含继承WIP，不是假装干净HEAD。只对已检查产物及明确标注失败记录做工程完整性清单，scientific_seal=false；浏览器临时profile与orchestration不封存。

运行：进入portable_demo，执行 `./run.sh viewer --scene ficus`。实验版：`./run.sh viewer --scene ficus --asset "$PWD/assets/ficus_retained137k"`。完整命令/真实退出码在REPRODUCE_ZH.md，操作说明在PACKAGE_README_ZH.md。

NEXT=continue：'''+next_step+'\n'
    (unit/'REPORT_ZH.md').write_text(report)
    (unit/'REPRODUCE_ZH.md').write_text('# Actual commands and return codes\n\n'+''.join(
        f"## {Path(r['path']).name}\n\nReturn code: {r['returncode']}; seconds: {r['seconds']:.3f}.\n\n```bash\n{shlex.join(r['command'])}\n```\n\n"
        for r in sorted(receipts,key=lambda x:x['start_utc']))+
        '\nOriginal interactive wrapper rc143; browser child rc UNKNOWN: see INTERRUPTION.json and logs/browser.start.json. Recovery uses identical parameters and a new output directory. Replay requires a new unit/output path; frozen artifacts must not be overwritten.\n')
    inspected=['media/simplification_historical_views.png','media/simplification_new_views.png','media/local_edit_all_views.png',
        'media/orbit_all_frames.png','media/zoom_all_frames.png','browser_recovery/01_loaded.png','browser_recovery/02b_catalog_restored.png']
    js(unit/'VISUAL_REVIEW.json',dict(utc=now(),reviewer='primary agent, nonblind, not independent human',inspected=inspected,
        decision=decision,quality='partial',negatives=negatives))
    here=Path(__file__).resolve().parent;snapshot=unit/'source_snapshot';snapshot.mkdir()
    for f in here.iterdir():
        if f.is_file() and f.suffix in ('.py','.cpp','.html'):shutil.copy2(f,snapshot/f.name)
    (unit/'red_source').mkdir()
    (unit/'red_source/fuse_cpu.py').write_bytes(subprocess.check_output(['git','show','HEAD:experiments/partwise_sketch_hatching_v04/fuse_cpu.py']))
    js(unit/'SOURCE_LOCK.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        working_source_snapshot={f.name:sha(f) for f in snapshot.iterdir()},red_fuser_sha256=sha(unit/'red_source/fuse_cpu.py'),
        current_unit_changes=['fuse_cpu.py','media.py','simplification_trial.py','package_simplification.py','finish_simplification.py'],
        scope='Other preexisting WIP inherited from unit009; full snapshot is authority, no Git commit made.'))
    readme='当前交付：unit010。保留四模型默认demo；Ficus高面数候选未晋级，实验资产单独提供。\n\n```bash\ncd '+str(unit/'portable_demo')+'\n./run.sh viewer --scene ficus\n```\n\n'+(unit/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    Path('docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    (unit/'SOURCE_DIFF.patch').write_text(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04'],text=True))
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(updated_utc=now(),current_unit=unit.name,execution_state='partial',
        demo_progress=progress,package=str(unit/'portable_demo.tar.gz'),package_sha256=sha(unit/'portable_demo.tar.gz'),
        report=str(unit/'REPORT_ZH.md'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),scientific_seal=False,next_action='continue'))
    files=[f for f in unit.iterdir() if f.is_file() and f.suffix in ('.json','.md','.patch','.gz')]
    for folder in ('assets','proxy','build','metrics','media','renders','source_model','source_snapshot','red_source','portable_demo','logs'):
        files.extend(f for f in (unit/folder).rglob('*') if f.is_file())
    for folder in ('browser_complete','browser_recovery'):
        files.extend(f for f in (unit/folder).iterdir() if f.is_file() and f.suffix in ('.json','.png'))
    files += [unit/'tests/fusion_red/RESULT.json',unit/'tests/fusion_red/proxy/PROXY.json',
        unit/'tests/fusion_red/proxy/mesh.npz',unit/'tests/INVALID_BUDGETS.json']
    entries=[dict(path=str(f.relative_to(unit)),sha256=sha(f),bytes=f.stat().st_size) for f in sorted(set(files))]
    js(unit/'SHA256_MANIFEST.json',dict(utc=now(),files=entries,scope='Validated finite engineering evidence plus preserved failures; no scientific certification; excludes mutable profiles, relocated run sessions and orchestration'))
    for entry in entries:assert sha(unit/entry['path'])==entry['sha256']
    js(unit/'ENGINEERING_SEAL.json',dict(utc=now(),manifest='SHA256_MANIFEST.json',manifest_sha256=sha(unit/'SHA256_MANIFEST.json'),
        files=len(entries),scientific_seal=False,execution_state='partial',scope='Integrity only. Candidate not promoted; strict-locality residual and original unknown exit retained.'))
    print(json.dumps(dict(execution_state='partial',elapsed_minutes=elapsed,files=len(entries),demo_progress=progress)))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',required=True,type=Path);finish(ap.parse_args().unit)
