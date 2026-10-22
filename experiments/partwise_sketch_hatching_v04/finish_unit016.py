"""Record checked engineering evidence; never implies a scientific seal."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import datetime,difflib,json,os,shutil,subprocess
import numpy as np
from demo import load_asset
from unit016_run import UNIT as U,PREVIOUS,SOURCE,protocol

def main():
    output_guard(U);p=protocol()
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    expected=['freeze','tdd_green','candidate','source','static','browser_recovery','stage','cold_orbit','cold_zoom','package_build','package_check','final_cli_edit','final_cli_image','legacy_default_image']
    assert all(receipts[k]['returncode']==0 for k in expected)
    assert receipts['tdd_red']['returncode']==1 and receipts['browser']['returncode']==-2
    # Check observed command intervals, including the interrupted first attempt.
    stages=[r for r in receipts.values() if 'start_utc' in r]
    stages.sort(key=lambda r:r['start_utc'])
    gaps=[(datetime.datetime.fromisoformat(b['start_utc'])-datetime.datetime.fromisoformat(a['end_utc'])).total_seconds() for a,b in zip(stages,stages[1:])]
    assert min(gaps)>=0
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    assert {f.name:sha(f) for f in Path(p['asset']).iterdir() if f.is_file()}==p['inputs']
    assert sha(U/'PROTOCOL.json')==sha('docs/partwise_sketch_hatching_v04/UNIT016_PROTOCOL.json')
    browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text());assert browser['status']=='PASS'
    final=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert final['cold_viewer_PNG_exact'] and final['legacy_unit015_PNG_exact']
    own=[]
    for d in ('browser','browser_interrupted'):
        own += [c['pid'] for c in json.loads((U/d/'OWN_CHILDREN.json').read_text())['children']]
    own.append(json.loads((U/'logs/FINAL_VIEWER_CHILD.json').read_text())['pid'])
    alive=[]
    for pid in own:
        try:os.kill(pid,0);alive.append(pid)
        except ProcessLookupError:pass
    assert not alive,alive
    disk=dict(root_free_bytes=shutil.disk_usage('/').free,hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,
              task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()))
    assert disk['root_free_bytes']>=2**30 and disk['hdd_free_bytes']>=10*2**30 and disk['task_output_bytes']<20*2**30
    js(U/'metrics/FINAL_GUARDS.json',dict(utc=now(),input_hashes_unchanged=True,original_ply_hash_unchanged=True,
        protocol_unchanged=True,serial_command_gap_min_seconds=min(gaps),all_own_child_PIDs_exited=own,resources=disk,
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()))
    mesh,paths,meta=load_asset(U/'assets/ink')
    js(U/'metrics/PATH_INVENTORY.json',dict(regions={str(r):dict(paths=len(np.unique(s['stroke_id'])),segments=len(s['points']),
        arclength=float(np.linalg.norm(s['points'][:,1]-s['points'][:,0],axis=1).sum())) for r,s in paths.items()},
        vertices=len(mesh['vertices']),faces=len(mesh['faces']),same_all_path_bytes=True))
    amendment=json.loads((U/'EXECUTION_AMENDMENT.json').read_text())
    amendment['recovery_completed']=dict(receipt='logs/browser_recovery.receipt.json',returncode=0,seconds=receipts['browser_recovery']['seconds'],unchanged_protocol=True)
    js(U/'EXECUTION_AMENDMENT.json',amendment)
    (U/'READING_REVIEW_ZH.md').write_text('''# 阅读、实际输出审阅与决定

完整读取父级BRIEF和851行原大纲（1–199、200–510、511–851），读取P1最后完成unit010报告/NEXT及length_cli、P2 experiment001报告/NEXT及audit_headroom源。保留GT灯历史NO_GO与H2零余量/不可辨识；用户新授权允许多步真实模型Demo推进，不把旧停止条款用作本轮阻塞。没有调用旧producer/sealer。

实际查看unit015四整对象原版/局部平滑/局部角度面板、原GS/代理/标签和全部orbit接触图，读取STATUS/REPORT/NEXT与demo、render、hatching、viewer、presentation及browser相关源。bucket局部平滑有温和改善，但底板墨线仍竞争注意力；薄侧向、孔洞和车身波折未解决。完整对象、编辑、保存、冷重开已经存在，不应再搭脚手架或新增第五模型。

候选排序：①固定全部路径的局部墨色控件；②进一步几何或轮廓修复；③新增模型。选①，单次预冻结region1从.80到.40，不扫参。region1是z<-.20的人工低区，主要覆盖底板，不保证完美语义平台。其余style有效值、几何、标签、所有路径和轮廓固定；GUI保存时可显式写入原先省略的交叉默认值，但不启用或重生交叉路径。

新四视角248/338/68/158在本轮出图前冻结，资产及历史视角已曝光，不称blind holdout。实际新图与18运动接触图显示底板排线明显变浅，整车相对突出；弱侧面、齿边与暗孔洞轮廓仍突出，不能将减墨量等价为几何或同墨量质量收益。原四默认资产未提升或替换，仅新可选示例。

本轮用户禁止nested models，未启动任何模型代理。数值阶段由同一串行收据执行，两核affinity、数值单线程，无GPU、环境dump、凭据、依赖安装、push/merge或对foreign process的操作。
''')
    rows=json.loads((U/'metrics/LOCALITY.json').read_text())['views']
    table='\n'.join(f"| {v['camera']['azimuth']} | {v['locality']['target_interior']['L1']:.3f} | {v['target_ink']['baseline']:.3f}→{v['target_ink']['ink']:.3f} | {v['target_nonzero_pixels']['baseline']}→{v['target_nonzero_pixels']['ink']} | {v['target_threshold_point1_pixels']['baseline']}→{v['target_threshold_point1_pixels']['ink']} | 0 / 0 |" for v in rows)
    start=datetime.datetime.fromisoformat('2026-10-22T06:49:07.488425+09:00')
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds()/60
    progress=dict(genuinely_ran_old_model=True,scene='lego',available_models=['chair','lego','drums','ficus'],
        original_PLY_render_this_unit=True,original_gaussians=310475,proxy_faces=len(mesh['faces']),
        regional_ink_control=True,selected_region=1,ink_strength_before=.8,ink_strength_after=.4,
        mesh_selection_all_path_files_exact=True,paths_regenerated=False,default_legacy_PNG_exact=True,
        target_layer_ink_ratio=.5,target_nonzero_support_exact=True,non_target_layers_depth_labels_contour_exact=True,
        full_object_static_views=4,actual_browser_downloads=4,motion_frames=18,lossless_video_frames_exact=18,
        mp4_frames_decoded=18,cold_replay_png_arrays_exact=18,relocated_CLI_local_edit=True,cold_viewer_png_exact=True,
        four_defaults_unchanged=True,default_promoted=False,
        strict_pixel_locality=dict(far_other_L1=0.,far_background_L1=0.,scope='four frozen cameras, proxy label masks with fixed2px boundary band'),
        visual_quality='partial; lighter lower-region hatching gives clearer tonal separation, but dark hole contours and thin-part noise remain',
        scientific_seal=False,reasoning='The existing complete-object real-model demo gains a saved local tone control without regenerating any paths; browser and portable cold replay both ran. This is artistic control, not reconstructed-geometry improvement.')
    limitation=['Proxy and labels are not independent truth; region1 is an authored height rule, mainly platform, not learned semantics.',
        'Ink mass reduction is intentional; >.1 threshold support decreases although nonzero hatch support and all 3D paths stay fixed.',
        'Contours retain full strength, making some platform hole boundaries more conspicuous; thin rods, tooth edges and body clutter remain.',
        'No H1/H2/H5, blind aesthetic preference, calibrated tone, lighting/LOD or full temporal/visibility certification.',
        'Only Lego is newly rendered in this unit; Chair/Drums/Ficus available assets are inherited and hash-preserved.',
        'Linux relocation tested with existing Python/dependencies; interpreter/dependencies not bundled.']
    status=dict(stage='UNIT_COMPLETE_WITH_VISUAL_LIMITATIONS',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS_AFTER_PRESERVED_EXTERNAL_BROWSER_INTERRUPTION',scientific_verdict='H1_H2_H5_NOT_TESTED_LOCAL_INK_CONTROL_ENGINEERING_PASS',
        demo_progress=progress,artifacts=['PROTOCOL.json','PACKAGE_README_ZH.md','assets/ink','media/full_object_before_after.png',
        'media/source_proxy_regions_edit.png','media/lego_ink_orbit.mp4','media/lego_ink_zoom.mp4','browser/BROWSER_VALIDATION.json',
        'metrics/LOCALITY.json','metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','source_snapshot','UNIT016_DIFF.patch'],
        tests=dict(real_model_behavior_tests=3,TDD_red_preserved=True,actual_Firefox=True,
            command_receipts={k:dict(returncode=r['returncode'],path='logs/'+k+'.receipt.json') for k,r in receipts.items()}),
        blockers=[],limitations=limitation,failures_preserved=['logs/tdd_red.log','logs/tdd_red.receipt.json','logs/browser.log','logs/browser.receipt.json','browser_interrupted','EXECUTION_AMENDMENT.json'],
        scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    next_step='增加浏览器内的显式示例选择：在原四模型默认资产之外，可直接打开已保存的Lego bucket cross、refined、platform ink示例；每个示例独立保留编辑/撤销状态，切换时明确来源与可选修订，原默认不替换。用实际浏览器切换→局部编辑→回切→导出→冷重开检查身份与参数隔离，不新增几何/风格候选或第五模型。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=next_step,demo_progress=progress,
        reason='Complete-object, local editing and cold replay now work; useful authored examples remain hidden behind --asset paths. Exposing them in the browser improves the actual demo with no further reconstruction speculation.',
        estimated_next_minutes=25,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    (U/'REPORT_ZH.md').write_text(f'''# Unit016：真实Lego局部墨色控制与可迁移Demo

执行状态 **completed**（本轮工程范围），整体视觉 **partial**。从给定06:49:07 JST开始约{elapsed:.1f}分钟。真实原PLY CPU参考、四全对象视角×两状态、实际Firefox控件/四次下载、18运动帧全解码及冷重放、最终tar解压后的CLI和viewer均完成。科学结论H1/H2/H5未测试；没有将局部减墨称为几何改进。

## 决策与冻结

完整BRIEF/原大纲及P1/P2历史源/报告/NEXT已读，实际审阅unit015全对象与运动输出。上轮bucket平滑收益有限，平台排线仍突出。选择唯一候选：region1 ink_strength .80→.40，保留全部几何、标签、路径、其他style有效值与轮廓。协议冻结{p['frozen_utc']}，SHA `{sha(U/'PROTOCOL.json')}`。未扫参。

源资产`{p['asset']}`；原PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`，310475高斯。16543顶点/29999面CPU深度融合代理沿用上轮可选bucket平滑；mesh SHA `{p['inputs']['mesh.npz']}`。region1是z<-.20人工高度低区，主要覆盖底板；region4保留三次人工矩形选的2030面，不是自动语义。source_model/保存本轮新原PLY CPU渲染，未用GT或重新训练。

## 行为与真实图像

新增[0,1]局部墨色，旧资产省略字段时默认.80。CLI `--ink-strength`、浏览器Hatch ink strength与保存/加载共用。墨色直接作用于目标排线层，交叉两层共用强度，先于supersample合成；不改变路径或轮廓。0隐藏排线仍保留路径和轮廓。输入非法/NaN/Inf/bool/字符串拒绝；冷加载亦校验。

四相机248/338/68/158°、仰角30°、距离5.1、512²/2xAA，完整代理全在画内。旧真实模型已曝光，新值在候选前冻结，不称盲测。目标path/mesh/selection文件字节全部相同，非目标region2/3/4各渲染层、两层bucket、depth/regions/contour数组逐项精确。表中L1为[0,1]浮点灰度差，边界按同一代理标签固定2px分带；不是独立语义GT。

| 方位 | 目标内部L1 | 目标hatch墨量 | 非零hatch像素 | hatch>.1像素 | 远其他/背景L1 |
|---:|---:|---:|---:|---:|---:|
{table}

各目标层墨量精确减半、非零覆盖不变；>.1支持减少如表，不能隐瞒减墨的可见性代价。轮廓max合成使整图墨量不等于简单减半。查看四整对象、原GS/代理/区域面板、实际UI和全部18运动接触图：平台略退后，车辆相对突出；338/158°深色小孔边界更明显，68°齿边/侧面仍碎，车身线团/薄杆孔洞未变。未做盲偏好或同墨量质量比较，保留opt-in而不提升默认。

## 实际测试、浏览器与冷重开

3项真实资产行为测试先红rc1：旧renderer忽略墨色，非法参数未拒绝。实现后rc0，覆盖legacy .80、局部.40、双交叉层减半、零/恢复、字节保留、禁止路径重生和非法输入/加载。最终可迁移包另在原相机重画unit015的legacy PNG，实际文件SHA精确，避免仅以新代码两次调用证明兼容。

Firefox实际选region1，.80→.40→save→刷新→切region4检查.80→Undo→再应用，并通过HTTP拒绝5种非法值；完整渲染与CLI一致。Orbit/Zoom按钮图像实际变化；下载asset ZIP、PNG、orbit、zoom共4个文件。12+6帧全对象在画内，FFV1全18帧解码RGB精确、MP4全解码计数18。独立新Python进程按顺序冷重放orbit再zoom，18PNG和全部分层数组精确，未重生成路径。有限帧不证明连续时序或独立遮挡准确性。

最终tar解压到final_archive新目录，按README命令CLI从旧refined资产执行ink .4、导PNG与浏览器逐文件精确；新viewer恢复region1、墨色/相机/轮廓设置/手工历史，PNG精确。四默认资产哈希全部不变。包不包含Python依赖，仅当前Linux迁移验证。

## 原失败、恢复与执行边界

首个浏览器wrapper在12.136s收到外部SIGTERM，wrapper143/child-2；原因未确定。其日志、收据和部分目录browser_interrupted保留，未当作完整通过。finally正常清理其viewer/WebDriver，检查仅这些自有PID均消失后，原协议/候选/参数不变，新目录重试rc0（101.124s）。没有隐藏第一次失败、没有额外科学候选。

数值阶段串行且实际收据时间无重叠（最小间隔{min(gaps):.3f}s），两核affinity、数值单线程；无GPU、凭据、环境dump、安装、nested models、push/merge。只改授权worktree新代码/文档和新输出根；orchestration只读（临时TMPDIR例外），旧输入/原PLY/默认资产哈希复核相同。自有viewer/WebDriver和最终cold viewer已退出。原有dirty工作未清理；source_snapshot与相对启动快照UNIT016_DIFF.patch用于重放。

## 交付与后续

`cd {U}/portable_demo && ./run.sh viewer --scene lego --asset "$PWD/examples/lego_platform_ink"`，地址127.0.0.1:8765。完整文档PACKAGE_README_ZH，便携包portable_demo.tar.gz。精确命令/returncode见REPRODUCE_ZH与logs；media/保留全对象、弱视角、全部运动帧，metrics/保留分层墨量和局部性。

本轮仅封存已验证工程证据，scientific_seal=false，parent仍reported_not_independently_verified。NEXT=continue：{next_step}
''')
    reproduce=['# 实际命令与退出记录\n','包含预期红灯和原外部中断；恢复未改参数。\n']
    import shlex
    for k,r in receipts.items():
        reproduce.append(f"## {k}\n\nreturncode={r['returncode']}；seconds={r['seconds']:.3f}。\n\n```bash\n{shlex.join(r['command'])}\n```\n")
    (U/'REPRODUCE_ZH.md').write_text('\n'.join(reproduce))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    changes=[];diff=[]
    for name in sorted({f.name for f in SOURCE.iterdir() if f.is_file()}|{f.name for f in (U/'source_before').iterdir() if f.is_file()}):
        old=U/'source_before'/name;new=SOURCE/name
        a=old.read_text().splitlines(True) if old.exists() else []
        b=new.read_text().splitlines(True) if new.exists() else []
        if a!=b:
            changes.append(name);diff.extend(difflib.unified_diff(a,b,fromfile='before/'+name,tofile='after/'+name))
    (U/'UNIT016_DIFF.patch').write_text(''.join(diff))
    js(U/'SOURCE_SNAPSHOT.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        changed_this_unit=changes,files={f.name:sha(f) for f in (U/'source_snapshot').iterdir() if f.is_file()},inherited_dirty_preserved=True))
    shutil.copy2(U/'PACKAGE_README_ZH.md',OUTPUT_ROOT/'DEMO_README_ZH.md')
    shutil.copy2(U/'PACKAGE_README_ZH.md','docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md')
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_016',execution_state='completed',updated_utc=now(),demo_progress=progress,
        package=str(U/'portable_demo.tar.gz'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),report=str(U/'REPORT_ZH.md'),
        next_action='continue',scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    # Only immutable reviewed artifacts, not fresh-browser profiles or mutable session directories.
    files=[]
    for name in ('assets','renders','source_model','media','metrics','source_snapshot'):
        files += [f for f in (U/name).rglob('*') if f.is_file()]
    for pattern in ('*.json','*.md','*.patch'):
        files += [f for f in U.glob(pattern) if f.name not in ('SHA256_MANIFEST.json','SEAL.json')]
    files += [U/'portable_demo.tar.gz',U/'browser/BROWSER_VALIDATION.json',U/'browser/CLEANUP.json',U/'browser/EXPORT_STATE.json']
    files += [f for f in (U/'logs').iterdir() if f.is_file()]
    files += [U/'browser'/name for name in ('01_loaded.png','02_legacy_platform.png','03_local_ink_saved.png','04_orbit_zoom.png','05_export_complete.png')]
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'SHA256_MANIFEST.json',dict(scope='validated engineering artifacts and original failures; no scientific seal; mutable browser profiles/sessions excluded',files=manifest))
    assert all(sha(U/name)==digest for name,digest in manifest.items())
    js(U/'SEAL.json',dict(kind='ENGINEERING_EVIDENCE_ONLY',scientific_seal=False,utc=now(),files_verified=len(manifest),
        manifest_sha256=sha(U/'SHA256_MANIFEST.json'),supervisor_verification='reported_not_independently_verified'))
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,sealed_files=len(manifest),package_sha256=sha(U/'portable_demo.tar.gz'))))

if __name__=='__main__':main()
