"""Write an evidence-limited handoff and seal current-unit immutable artifacts."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from unit018_run import U,PREV,SOURCE,hashes
from pathlib import Path
import datetime,difflib,json,shutil,subprocess,os,shlex

def main():
    output_guard(U)
    p=json.loads((U/'PROTOCOL.json').read_text())
    browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())
    cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text())
    replay=json.loads((U/'metrics/COLD_REPLAY.json').read_text())
    final=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert browser['status']==cold_browser['status']=='PASS'
    assert final['CLI_saved_PNG_exact'] and final['CLI_continue_edit_PNG_exact']
    assert all(c['PNG_exact'] for c in final['import_checks'])
    assert all(r['all_png_exact'] and r['all_arrays_exact'] for r in replay.values())
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    assert sha(p['legacy_zip']['path'])==p['legacy_zip']['sha256']
    for name in ('assets','examples'):
        assert hashes(U/'portable_demo'/name)==hashes(PREV/'portable_demo'/name)==p['inputs'][name]
    assert all(sha(f)==sha(SOURCE/f.name) for f in (U/'portable_demo/source').iterdir() if f.is_file())
    states=json.loads((U/'browser/STATES.json').read_text());framing={}
    for key,s in states.items():
        folder=(U/'browser/session'/s['images']['image'].removeprefix('/image/')).parent
        row=json.loads((folder/'frame_000.json').read_text());assert row['bounds']['all_proxy_vertices_inside']
        framing[key]=row['bounds']
    local={}
    for scene,before,after in [('lego','legacy_lego_import','lego_local_edit'),('chair','chair_import','chair_local_edit')]:
        a,b=(Path(states[key]['asset']) for key in (before,after))
        binary={f.name:sha(f) for f in a.iterdir() if f.is_file() and f.name!='asset.json'}
        assert all(digest==sha(b/name) for name,digest in binary.items())
        local[scene]=json.loads((U/'browser'/(scene.upper()+'_LOCALITY.json')).read_text())
        local[scene]['all_geometry_selection_path_files_exact']=True
        assert local[scene]['far_other_L1']==local[scene]['far_background_L1']==0
    js(U/'metrics/LOCALITY.json',local)
    js(U/'metrics/FRAMING.json',dict(all_saved_views_complete=True,views=framing))
    owned=[]
    for folder in ('browser','cold_browser'):owned+=json.loads((U/folder/'CLEANUP.json').read_text())['children']
    owned.append(json.loads((U/'logs/relocated_viewer_cleanup.json').read_text()))
    for child in owned:
        try:os.kill(child['pid'],0)
        except ProcessLookupError:pass
        else:raise RuntimeError('owned child still present: '+str(child['pid']))
    js(U/'metrics/OWN_PROCESS_CLEANUP.json',dict(all_owned_children_absent=True,children=owned))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_SNAPSHOT.json',dict(files=hashes(U/'source_snapshot'),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    diff=[]
    for name in sorted(set(hashes(U/'source_before'))|set(hashes(SOURCE))):
        a=U/'source_before'/name;b=SOURCE/name
        if a.exists() and b.exists() and sha(a)==sha(b):continue
        if Path(name).suffix not in ('.py','.html','.cpp','.md','.json'):continue
        diff.extend(difflib.unified_diff(a.read_text().splitlines(True) if a.exists() else [],b.read_text().splitlines(True) if b.exists() else [],fromfile='a/'+name,tofile='b/'+name))
    (U/'UNIT018_DIFF.patch').write_text(''.join(diff))
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    assert receipts['tdd_red']['returncode']==1 and all(r['returncode']==r['expected_returncode'] for r in receipts.values())
    children={'relocated_cli_image','relocated_cli_edit','relocated_cli_edited_image'}
    ordered=sorted(((n,r) for n,r in receipts.items() if n not in children),key=lambda x:x[1]['started_utc'])
    gaps=[(datetime.datetime.fromisoformat(b[1]['started_utc'])-datetime.datetime.fromisoformat(a[1]['finished_utc'])).total_seconds() for a,b in zip(ordered,ordered[1:])]
    assert all(g>=0 for g in gaps)
    resources=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),serial_top_level_intervals=True,minimum_gap_seconds=min(gaps),
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(U).free,
        task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        GPU=False,nested_models=False,credentials_or_environment_dump=False,push_merge=False)
    assert resources['task_output_bytes']<20*2**30;js(U/'metrics/RESOURCE_CHECK.json',resources)
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T07:13:06.740052+09:00')).total_seconds()/60
    source=json.loads((U/'source_model/RECEIPT.json').read_text())
    negative=json.loads((U/'test_final/REJECTIONS.json').read_text())
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_proxies=['lego','chair'],
        original_PLY_render='lego',original_gaussians=source['original_gaussians'],browser_ZIP_import=True,
        legacy_archive_compatible=True,new_download_full_file_SHA256=True,independent_import_sessions=True,
        cold_server_browser_reload_models=['lego','chair'],cold_import_PNG_arrays_exact=True,continue_edit_and_undo=True,
        invalid_archive_cases_rejected=len(negative['cases']),invalid_upload_preserves_active_edit=True,
        four_defaults_and_three_examples_unchanged=True,local_ink_edits=dict(lego='region1 .60 -> .35',chair='region2 .80 -> .50'),
        mesh_selection_all_paths_exact=True,non_target_layers_depth_labels_contour_exact=True,
        far_other_and_background_L1=0.,locality_scope='One saved camera per model; proxy labels, fixed2px band.',
        complete_static_states=len(states),actual_browser_downloads=browser['actual_download_count'],motion_frames=18,
        lossless_video_frames_exact=18,mp4_frames_decoded=18,cold_replay_png_arrays_exact=18,relocated_tar_CLI_and_import=True,
        visual_quality='partial; inherited broken thin parts, holes and wavy/dense hatching remain',default_promoted=False,scientific_seal=False,
        reasoning='Two real saved models now complete save -> stop server -> browser import on new server -> continue editing, without terminal extraction or asset paths.')
    limitations=[
        'Model-derived exploratory proxy and authored regions; no independent reconstructed geometry or learned semantics claim.',
        'Import improves recovery and usability; original visual and geometry defects remain. Only Lego original PLY newly rasterized; Chair saved proxy newly rendered.',
        'One-camera locality and finite18-frame decode/replay do not certify independent semantics, all-view occlusion, full temporal correspondence or H1/H2/H5.',
        'Import accepts flat saved-asset ZIP only, recognized catalog model SHA, max32MiB upload/128MiB expanded arrays/16 import sessions; presentation ZIP uses replay instead.',
        'Legacy ZIP lacks full-archive hashes; current checksum manifests detect corruption, not maliciously forged provenance or physical correctness.',
        'Final saved state persists in downloaded ZIP; undo history, uncommitted selection drafts and unsaved sliders do not.',
        'Existing Linux dependencies reused, not bundled; cross-platform installation and binary compatibility not tested.'
    ]
    artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','media/import_local_edits.png','media/cold_import.png',
        'media/source_proxy_import_edit.png','media/lego_orbit.mp4','media/lego_zoom.mp4','browser/BROWSER_VALIDATION.json',
        'cold_browser/BROWSER_VALIDATION.json','metrics/LOCALITY.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json',
        'portable_demo.tar.gz','source_snapshot','UNIT018_DIFF.patch']
    status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS',scientific_verdict='H1_H2_H5_NOT_TESTED_IMPORT_COLD_SESSION_ENGINEERING_PASS',demo_progress=progress,
        artifacts=artifacts,tests=dict(real_asset_tests=2,TDD_red_preserved=True,actual_Firefox=True,
            command_receipts={n:dict(returncode=r['returncode'],path='logs/'+n+'.receipt.json') for n,r in receipts.items()}),
        blockers=[],limitations=limitations,scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    next_step='回到可见画质瓶颈：在Chair现有中部高度风格区上冻结一个有界局部代理平滑候选，复用现有local_refinement，保留非目标顶点/标签/路径和默认资产，仅重生成目标路径。先对照真实Chair GS与代理确认座面波纹，固定四全对象视角与弱侧面、局部编辑及冷重开；报告墨量/覆盖与轮廓副作用，有改善才作为可选示例，不主张几何恢复或H5。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='完整对象、局部编辑、导出和浏览器冷导入闭环现已实测；下一步应减少Chair座面波纹/密线这一实际可见缺陷，不再增加存取界面或不必要模型。',
        estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    (U/'READING_REVIEW_ZH.md').write_text('''# 阅读、审查与选择

完整读取BRIEF及原大纲851行，读取P1 unit010 REPORT/NEXT/length_cli源码、P2 experiment001 REPORT/NEXT/audit_headroom源码。保留GT整灯NO_GO/PARTIAL与H2零余量不可辨识；新用户授权覆盖旧单单元限制。无适用AGENTS.md，不运行历史producer/sealer，不使用nested models。

实际查看unit017四模型/三Lego示例/原GS与代理及全部12环绕帧，读取STATUS/REPORT/NEXT和viewer、scene_catalog、demo、geometry、hatching、presentation、browser实际源码。Lego完整形状可辨，但桶齿/细杆/孔洞和背面密线仍弱；Chair座面波纹与Ficus碎叶明显。排序：①补保存资产浏览器冷导入，②Chair局部表面/路径改善，③新增模型。选择①完成用户继续操作闭环；原有四模型足够，几何失败不被伪称已修复。

原dirty worktree保留。只读检查曾遇缺失AGENTS和误猜的orbit_contact文件名，随后查看实际all_frames图；没有改写历史目录。当前数值执行唯一非零为预期TDD红灯rc1。新增所有数值命令串行，两核affinity，未使用GPU或环境dump。

本轮实际审阅两模型导入/局部编辑全对象图、新原Lego GS/代理/区域面板、全部18运动帧和冷服务Firefox截图。完整代理均在画内；局部浅墨可辨，Lego细杆/背面孔洞、Chair座面碎波纹仍存在。本轮是存取工程完成，不是画质晋级、语义或几何恢复证据。
''')
    rows='\n'.join('| '+n+' | '+str(r['returncode'])+' | '+f"{r['seconds']:.3f}"+' |' for n,r in receipts.items())
    (U/'REPORT_ZH.md').write_text(f'''# Unit018：真实模型资产ZIP导入、关服务后重开与继续编辑

执行状态 **completed**（工程范围），视觉质量仍 **partial**。约{elapsed:.1f}分钟完成，H1/H2/H5未测试。实际执行Lego/Chair代理、Lego原PLY CPU参考、两轮独立Firefox、18帧视频全解码/冷重绘和最终tar迁移检查。

## 改变与输入

目录浏览器新增Open your saved asset，支持Download saved asset的平坦ZIP。每次导入创建独立示例，自动选择模型，恢复最终styles/camera/display/selected region，原会话继续可切回，撤销从导入状态开始。新导出包新增逐文件SHA256清单；旧unit017下载包兼容，通过网格/选择哈希和路径锚点验证。检查ZIP路径/重复成员、数组大小/形状/数值/索引、已知model SHA；不解压到用户指定路径，不执行包内代码。损坏上传拒绝，活动状态不变。限定32MiB上传、128MiB数组展开、16导入会话；manifest是损坏检测，不是来源认证。

协议先冻结，SHA `{sha(U/'PROTOCOL.json')}`；输入为unit017 assets/examples与browser/lego_asset.zip，逐文件SHA见PROTOCOL。四默认和三既有示例原样保留。实际新渲染原PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`，{source['original_gaussians']}高斯；CPU SH3/EWA参考见source_model。未训练或使用GT替换。Chair仅新渲染已有真实模型派生代理，不宣称本轮重新渲染Chair原PLY。

## 真实测试与局部图像

两项真实资产测试先红rc1（缺少import_archive/模块），实现后rc0。后增加总体展开数组预算，再以最终源码完整通过同两项测试；12类拒绝包括坏ZIP、路径穿越、网格/路径哈希、模型身份、非有限相机/重心、越界索引、缺文件和重复成员。原TDD失败保留。

Firefox实际通过file input上传旧Lego ZIP，PNG与unit017下载PNG精确；Lego region1 ink .60→.35。再下载Chair默认包并上传为独立会话，region2 ink .80→.50。两者的全部网格/选择/路径文件逐字节不变，非目标分层和depth/regions/contour数组精确。两模型单个固定已曝光相机、固定2px代理标签边界带：

| Model | Target interior L1 | Far other/background L1 | Target ink before → after | Boundary band L1 |
|---|---:|---:|---:|---:|
| Lego | {local['lego']['target_interior_L1']:.6f} | 0 / 0 | {local['lego']['ink_before']:.3f} → {local['lego']['ink_after']:.3f} | {local['lego']['boundary_band_L1']:.6f} |
| Chair | {local['chair']['target_interior_L1']:.6f} | 0 / 0 | {local['chair']['ink_before']:.3f} → {local['chair']['ink_after']:.3f} | {local['chair']['boundary_band_L1']:.6f} |

这些是代理标签局部性，不是独立语义真值或保墨审美比较。坏文件实际上传与过期示例上传均拒绝且当前编辑不变。原默认及导入会话切换、刷新、相机旋转/缩放可用。6次实际浏览器下载包括3个资产ZIP、PNG、orbit和zoom。

## 冷重开、运动与迁移

第一轮服务/Firefox退出并回收后，第二个全新服务/Firefox重新上传Lego与Chair保存包，最终参数、相机、PNG及全部分层数组精确。两者均再改回先前墨色并撤销，精确返回导入画面。不是同进程刷新冒充冷启动；收据见browser/CLEANUP和cold_browser/BROWSER_VALIDATION。

Lego orbit12+zoom6共18帧全对象实际重渲染，FFV1全帧RGB精确，MP4全解码计数18；两个独立新进程串行冷重绘18PNG和全部分层数组精确。实际检查所有帧：弱背面、桶齿/细杆、孔洞和密线继续保留。有限18帧不构成独立全路径时间稳定性证明。

最终portable_demo.tar.gz解压后，文档CLI冷绘当前保存资产、继续编辑.35→.60并冷绘，分别与本轮最终图和旧导入图一致；迁移后的目录服务重新导入两模型ZIP也得到相同PNG/参数。源与资产可移植，Python依赖未打包，仅测试当前Linux环境。

## 执行与交付

| Command | Return code | Seconds |
|---|---:|---:|
{rows}

精确argv/cwd/返回码见logs/*.receipt.json与REPRODUCE_ZH.md。原rc1没有覆盖为通过。数值和视频单线程、总两核、命令串行，无GPU/凭据/environment dump/nested models/push或merge；orchestration只读，临时scratch除外。自有两轮viewer/WebDriver与迁移viewer均退出。source_before/source_snapshot、UNIT018_DIFF.patch保留dirty继承与本轮改变。

入口：`cd {U}/portable_demo && ./run.sh viewer --scene lego`。使用Open your saved asset直接选择saved_zips中的包。STATUS/NEXT/REPORT与便携包已写；只封存实际核验工程证据，scientific_seal=false，reported_not_independently_verified。NEXT=continue：{next_step}
''')
    commands=['### '+n+'\n\n```bash\n'+shlex.join(r['command'])+'\n```\n\nreturncode='+str(r['returncode'])+'\n' for n,r in receipts.items()]
    (U/'REPRODUCE_ZH.md').write_text('# 实际执行命令\n\n工作目录：'+str(SOURCE.parents[1])+'。重放请使用新的输出目录，不覆盖旧证据。\n\n'+'\n'.join(commands))
    readme='# 最新可运行交付：unit018\n\n```bash\ncd '+str(U/'portable_demo')+'\n./run.sh viewer --scene lego\n```\n\n'+(U/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(readme)
    delivery=dict(unit='unit_018',execution_state='completed',demo_progress=progress,package=str(U/'portable_demo.tar.gz'),
        readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),status=str(U/'STATUS.json'),scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery);js(U/'DELIVERY_STATUS.json',delivery)
    # Exclude browser profiles and mutable package runs; include reviewed arrays and actual exports.
    files=[]
    for name in ('source_before','source_snapshot','source_model','media','metrics','test_red','test_green','test_final'):
        files.extend(f for f in (U/name).rglob('*') if f.is_file())
    files.extend(f for f in U.iterdir() if f.is_file() and f.name not in ('SEAL.json','SHA256_MANIFEST.json'))
    files.extend(f for f in (U/'logs').iterdir() if f.is_file())
    for folder in ('browser','cold_browser'):
        files.extend(f for f in (U/folder).iterdir() if f.is_file())
        files.extend(f for f in (U/folder/'session').rglob('*') if f.is_file() and f.suffix in ('.json','.npz','.png','.zip','.mp4','.mkv','.txt'))
    for scene in ('lego','chair'):files.extend(f for f in (U/'browser'/('exported_'+scene)).iterdir() if f.is_file())
    files=sorted(set(files))
    manifest={str(f.relative_to(U)):sha(f) for f in files}
    js(U/'SHA256_MANIFEST.json',dict(schema='unit018_engineering_evidence_v1',files=manifest))
    assert all(sha(U/name)==digest for name,digest in manifest.items())
    js(U/'SEAL.json',dict(utc=now(),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),verified_files=len(manifest),
        scope='Validated engineering evidence, including preserved expected failures; not a full scientific seal.',scientific_seal=False,
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='completed',verified_files=len(manifest),elapsed_minutes=elapsed,next_action='continue')),flush=True)

if __name__=='__main__':main()
