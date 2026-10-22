"""Seal validated engineering evidence and write an honest unit017 handoff."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from unit017_run import U,PREV,SOURCE,hashes
from pathlib import Path
import datetime,difflib,json,shutil,subprocess,os

def main():
    output_guard(U)
    protocol=json.loads((U/'PROTOCOL.json').read_text())
    browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())
    cold=json.loads((U/'metrics/COLD_REPLAY.json').read_text())
    relocated=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert browser['status']=='PASS' and relocated['CLI_PNG_exact']
    assert all(v['all_png_exact'] and v['all_arrays_exact'] for v in cold.values())
    assert sha(protocol['original']['original_ply'])==protocol['original']['sha256']
    for name in ('assets','examples'):
        assert hashes(U/'portable_demo'/name)==protocol['inputs'][name]
        assert hashes(PREV/'portable_demo'/name)==protocol['inputs'][name]
    # The portable runnable source must be the reviewed/tested final source.
    assert all(sha(f)==sha(SOURCE/f.name) for f in (U/'portable_demo/source').iterdir() if f.is_file())
    states=json.loads((U/'browser/STATES.json').read_text());framing={}
    for key,s in states.items():
        folder=(U/'browser/session'/s['images']['image'].removeprefix('/image/')).parent
        row=json.loads((folder/'frame_000.json').read_text());assert row['bounds']['all_proxy_vertices_inside']
        framing[key]=row['bounds']
    js(U/'metrics/FRAMING.json',dict(all_eight_saved_views_complete=True,views=framing))
    locality=json.loads((U/'browser/LOCALITY.json').read_text())
    js(U/'metrics/LOCALITY.json',locality)
    # Check only owned child PIDs, never enumerate unrelated process arguments.
    owned=json.loads((U/'browser/CLEANUP.json').read_text())['children']
    owned += [json.loads((U/'logs'/('cold_'+name+'_cleanup.json')).read_text()) for name in ('named','saved')]
    for child in owned:
        try:os.kill(child['pid'],0)
        except ProcessLookupError:pass
        else:raise RuntimeError('owned child still present: '+str(child['pid']))
    js(U/'metrics/OWN_PROCESS_CLEANUP.json',dict(all_owned_children_absent=True,children=owned))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_SNAPSHOT.json',dict(files=hashes(U/'source_snapshot'),git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    diff=[]
    for name in sorted(set(hashes(U/'source_before'))|set(hashes(SOURCE))):
        old=U/'source_before'/name;new=SOURCE/name
        if old.exists() and new.exists() and sha(old)==sha(new):continue
        if (old.exists() and old.suffix not in ('.py','.html','.cpp','.md','.json')) or (new.exists() and new.suffix not in ('.py','.html','.cpp','.md','.json')):continue
        diff.extend(difflib.unified_diff(old.read_text().splitlines(True) if old.exists() else [],new.read_text().splitlines(True) if new.exists() else [],fromfile='a/'+name,tofile='b/'+name))
    (U/'UNIT017_DIFF.patch').write_text(''.join(diff))
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    assert receipts['tdd_red']['returncode']==1
    assert all(r['returncode']==r['expected_returncode'] for r in receipts.values())
    # Wrapper check includes child CLI calls; exclude those nested receipts from the serial interval audit.
    top=[(n,r) for n,r in receipts.items() if n not in ('relocated_cli_edit','relocated_cli_image','wrong_model_example')]
    ordered=sorted(top,key=lambda x:x[1]['started_utc'])
    gaps=[(datetime.datetime.fromisoformat(b[1]['started_utc'])-datetime.datetime.fromisoformat(a[1]['finished_utc'])).total_seconds() for a,b in zip(ordered,ordered[1:])]
    assert all(g>=0 for g in gaps)
    resources=dict(cpu_affinity=sorted(os.sched_getaffinity(0)),serial_top_level_intervals=True,minimum_gap_seconds=min(gaps),
        root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(U).free,
        task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        GPU=False,nested_models=False,credentials_or_environment_dump=False,push_merge=False)
    assert resources['task_output_bytes']<20*2**30
    js(U/'metrics/RESOURCE_CHECK.json',resources)
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-22T07:01:26.668457+09:00')).total_seconds()/60
    progress=dict(genuinely_ran_old_model=True,available_models=browser['models_visited'],new_original_PLY_render='lego',original_gaussians=310475,
        browser_example_selector=True,optional_examples=3,independent_edit_undo_camera=True,draft_isolation_faces=browser['draft_isolation_face_count'],
        stale_example_requests_rejected=6,guarded_asset_download=True,four_defaults_and_inherited_examples_unchanged=True,
        local_ink_edit='.40 -> .60, region1',mesh_and_all_path_bytes_exact=True,non_target_layers_depth_labels_contour_exact=True,
        far_other_L1=locality['far_other_L1'],far_background_L1=locality['far_background_L1'],locality_scope=locality['scope'],
        complete_static_views=len(states),actual_browser_downloads=4,motion_frames=18,lossless_video_frames_exact=18,
        mp4_frames_decoded=18,cold_replay_png_arrays_exact=18,relocated_named_CLI_edit=True,
        cold_named_catalog_and_saved_asset_PNG_exact=True,default_promoted=False,
        visual_quality='partial; inherited hole contours, broken thin parts and dense body hatching remain',scientific_seal=False,
        reasoning='Existing real-model demos and optional Lego states are directly selectable in one browser; edits, drafts and undo stay independent, and saved results survive export and cold relocation.')
    limitations=[
        'Geometry is an exploratory model-derived proxy, not independently measured truth; authored height/manual regions are not learned semantics.',
        'Example selection improves access and state isolation, not the inherited geometry or hatch aesthetic quality.',
        'Only Lego original PLY newly rasterized; all four saved model proxies were newly rendered in Firefox.',
        'Locality measured at one saved camera with proxy labels and fixed2px band; no independent semantic or visibility certification.',
        'Finite18 motion frames and exact replay are not full temporal correspondence or H1/H2/H5 evidence.',
        'Sessions persist only while server is running; ZIP keeps final asset state, not session undo history or uncommitted drafts.',
        'Existing Linux interpreter/dependencies reused; portable source/assets provided, Python dependencies not bundled.'
    ]
    status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS',scientific_verdict='H1_H2_H5_NOT_TESTED_EXAMPLE_SESSION_ENGINEERING_PASS',demo_progress=progress,
        artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','media/catalog_all_models_examples.png','media/local_edit.png',
            'media/source_proxy_regions_edit.png','media/lego_orbit.mp4','media/lego_zoom.mp4','browser/BROWSER_VALIDATION.json',
            'metrics/LOCALITY.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT017_DIFF.patch'],
        tests=dict(real_asset_tests=2,TDD_red_preserved=True,actual_Firefox=True,command_receipts={n:dict(returncode=r['returncode'],path='logs/'+n+'.receipt.json') for n,r in receipts.items()}),
        blockers=[],limitations=limitations,scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    next_step='在浏览器中直接导入已下载资产ZIP并作为独立会话打开，补齐保存→关服务→新服务→浏览器导入→继续编辑闭环。校验scene/mesh/path哈希与ZIP路径，明确保留最终状态而非历史；用本轮真实Lego导出包和一个默认Chair包实测，不新增模型或几何候选。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='完整对象、局部编辑、示例目录和CLI冷重开均运行；用户自己的下载资产仍须解压并输入--asset路径，直接导入可继续减少演示操作成本。',
        estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    (U/'READING_REVIEW_ZH.md').write_text('''# 阅读与选择

完整读取orchestration/BRIEF.md与原大纲851行，读取P1 unit010 REPORT/NEXT和length_cli源、P2 experiment001 REPORT/NEXT和audit_headroom源。保留历史GT整灯NO_GO/PARTIAL与H2零余量不可辨识；旧单单元限制由当前授权覆盖。没有执行旧producer/sealer，没有nested models。

实际查看unit016四全对象视角、原GS/代理/标签/局部墨色面板和12帧环绕接触图。平台变浅可辨，但薄杆/孔洞/车身杂线仍在。读取unit016 STATUS/REPORT/NEXT及viewer、scene_catalog、catalog_demo、presentation、browser测试源。排序：①已有示例直接选择及身份隔离；②进一步几何或轮廓修复；③第五模型。选择①，已有四模型、三种Lego可选状态足以支持实用演示，避免重复视觉扫参。

无适用AGENTS.md。起始dirty工作保留。只读探索中误用小写catalog.json及猜测receipt.py得到文件缺失提示；随即读取实际CATALOG.json并新增当前单元收据器，未运行历史写入助手。主执行唯一非零为预期TDD红灯及错误模型示例负控制，均保存原收据。

本轮实际新图包含所有四默认模型、三可选示例、局部墨色编辑和全部18运动帧。检查后确认对象完整在画内；弱背面、平台孔洞和Ficus叶片破碎仍保留。UI可直接选择来源，.60墨色编辑改变平台强度，不主张更美或几何改善。
''')
    rows='\n'.join('| '+n+' | '+str(r['returncode'])+' | '+f"{r['seconds']:.3f}"+' |' for n,r in receipts.items())
    (U/'REPORT_ZH.md').write_text(f'''# Unit017：真实模型保存示例选择与独立编辑会话

执行状态 **completed**（本轮工程范围），整体视觉仍 **partial**。约{elapsed:.1f}分钟完成；H1/H2/H5未测试。已实际运行四模型代理、原Lego PLY CPU参考、Firefox操作、四次下载、18帧视频全解码、独立冷重绘及最终tar迁移后CLI和两种viewer。

## 改变与固定

浏览器新增 Saved example，在四原默认模型之外提供Lego bucket cross、bucket smoothing、lighter platform三个可选状态。模型ID与示例ID分离，按两者维护独立Editor，隔离已保存编辑、相机、选择草稿、撤销。切换模型会恢复该模型最后的示例。六种过期示例POST请求拒绝，带身份和revision的资产下载也拒绝过期引用。CLI新增--example；不匹配模型的示例在写输出前拒绝。

输入为unit016 portable_demo/assets和examples，哈希写入PROTOCOL.json；协议在实现与候选运行前冻结，SHA `{sha(U/'PROTOCOL.json')}`。四默认及全部既有示例文件逐字节未改。源PLY `{protocol['original']['original_ply']}`，SHA `{protocol['original']['sha256']}`，310475高斯；新原PLY CPU SH3/EWA参考见source_model/。无GT替换或训练。几何和分区继承CPU深度融合代理、人工高度规则和桶面选择；局部平滑并非真实几何恢复。

## 真实行为与图像

两项真实资产测试先红rc1（缺少示例身份），实现后rc0。Firefox依次打开默认及三示例，平台region1 ink .40→.60保存，再切其他示例/全部其他模型/返回/刷新/撤销/重做，状态和PNG一致。另在bucket_cross保留{browser['draft_isolation_face_count']}面可见选择草稿，切到ink示例时不泄漏，返回后token和面数恢复。未替换原默认或提升视觉候选。

同一已曝光相机(-112°,30°,5.1)，局部编辑目标内L1={locality['target_interior_L1']:.6f}，目标层墨量{locality['target_ink_before']}→{locality['target_ink_after']}；全部网格/选择/路径二进制相同。其他区域图层、桶的两层、depth/regions/contour数组精确；固定2px代理标签边界带之外其他区域和背景L1均0。仅单相机工程局部性，不是独立语义真值或墨量匹配审美实验。

media/catalog_all_models_examples.png保留全部八个实际状态，media/source_proxy_regions_edit.png为原GS/代理/区域/编辑对照。Lego原示例PNG与unit016保存PNG精确复现。检查全部运动接触图：平台层次随墨色变化；车辆背面、桶齿、细杆及暗孔洞仍碎，Ficus叶片也明显破碎。本轮没有改善这些视觉问题。

## 导出、冷重开与包

实际Firefox下载资产ZIP、PNG、orbit12帧、zoom6帧共4件。全部18帧完整代理在画内，FFV1全解码逐帧RGB精确，MP4全解码计数18。两个独立新进程顺序冷重绘18PNG和全部分层数组精确。有限帧不构成完整时间稳定性或独立遮挡认证。

最终portable_demo.tar.gz解压到final_archive后，文档CLI使用--example执行相同.60局部编辑，PNG和浏览器一致；原命名示例目录viewer与已下载资产单例viewer都冷启动，PNG、相机、显示、region、styles及示例来源一致。来源元数据和当前值分开；下载保存的是最终资产，不包含会话撤销历史或未提交草稿。Python依赖未打包，只验证当前Linux迁移。

## 收据与资源

| Command | Return code | Seconds |
|---|---:|---:|
{rows}

完整argv和cwd见logs/*.receipt.json与REPRODUCE_ZH.md。预期TDD红灯rc1和错误模型示例rc2保留，未改写为通过。主数值命令串行，两核affinity，数值和视频单线程；无GPU、凭据、环境dump、nested models或push/merge。orchestration只读，临时TMPDIR除外。自有viewer/WebDriver/cold viewer均退出。原dirty工作未清理，source_before/source_snapshot及UNIT017_DIFF.patch提供重放。

入口：`cd {U}/portable_demo && ./run.sh viewer --scene lego --example lego_platform_ink`。本轮仅封存已核验工程证据，scientific_seal=false，监督状态reported_not_independently_verified。NEXT=continue：{next_step}
''')
    commands=[]
    import shlex
    for name,r in receipts.items():commands.append('### '+name+'\n\n```bash\n'+shlex.join(r['command'])+'\n```\n\nreturncode='+str(r['returncode'])+'\n')
    (U/'REPRODUCE_ZH.md').write_text('# 实际执行命令\n\n工作目录：'+str(SOURCE.parents[1])+'。输出已有时需换成当前授权单元内新目录，不覆盖旧证据。\n\n'+'\n'.join(commands))
    readme=(U/'PACKAGE_README_ZH.md').read_text()
    root_readme='# 最新可运行交付：unit017\n\n```bash\ncd '+str(U/'portable_demo')+'\n./run.sh viewer --scene lego --example lego_platform_ink\n```\n\n'+readme
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(root_readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(root_readme)
    delivery=dict(unit='unit_017',execution_state='completed',demo_progress=progress,package=str(U/'portable_demo.tar.gz'),
        readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),status=str(U/'STATUS.json'),scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery);js(U/'DELIVERY_STATUS.json',delivery)
    # Explicit meaningful immutable evidence only. Browser profile/runtime files are excluded.
    roots=['source_before','source_snapshot','source_model','media','metrics','test_red','test_green']
    files=[]
    for name in roots:
        files.extend(f for f in (U/name).rglob('*') if f.is_file())
    files.extend(f for f in U.iterdir() if f.is_file() and f.name not in ('SEAL.json','SHA256_MANIFEST.json'))
    files.extend(f for f in (U/'logs').iterdir() if f.is_file())
    files.extend(f for f in (U/'browser').iterdir() if f.is_file())
    files.extend(f for f in (U/'browser/exported_asset').rglob('*') if f.is_file())
    # Retain the actual before/after layer arrays used for locality and all catalog stills.
    for s in states.values():
        folder=(U/'browser/session'/s['images']['image'].removeprefix('/image/')).parent
        files.extend(f for f in folder.iterdir() if f.is_file())
    package_manifest=json.loads((U/'portable_demo/PACKAGE_FILES.json').read_text())
    files.extend(U/'portable_demo'/name for name in package_manifest['files'])
    files.append(U/'portable_demo/PACKAGE_FILES.json')
    manifest=dict(schema='unit017_validated_engineering_files_v1',scientific_seal=False,
        files={str(f.relative_to(U)):sha(f) for f in sorted(set(files))})
    js(U/'SHA256_MANIFEST.json',manifest)
    assert all(sha(U/name)==digest for name,digest in manifest['files'].items())
    js(U/'SEAL.json',dict(created_utc=now(),manifest_sha256=sha(U/'SHA256_MANIFEST.json'),files=len(manifest['files']),
        scope='Validated engineering evidence only; full scientific seal not claimed.',scientific_seal=False,
        supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,sealed_files=len(manifest['files']),next_action='continue')))

if __name__=='__main__':main()
