"""Finalize only validated Unit019 evidence; preserve the interrupted attempt."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,shutil,subprocess,datetime,difflib
from unit019_run import U,PREV,SOURCE,protocol,hashes

def main():
    output_guard(U);p=protocol()
    assert sha(U/'PROTOCOL.json')=='e356c82e20a62b84517bed0bc2b11ed94d6ff5eb20483e237a60cb50abdba4a7'
    for f in ['browser/BROWSER_VALIDATION.json','cold_browser_recovery/BROWSER_VALIDATION.json']:
        assert json.loads((U/f).read_text())['status']=='PASS'
    final=json.loads((U/'metrics/FINAL_ARCHIVE_REPLAY.json').read_text())
    assert final['CLI_candidate_PNG_exact'] and final['CLI_refinement_mesh_paths_exact'] and final['CLI_local_edit_PNG_exact'] and final['cold_catalog_and_import_PNG_exact']
    cold=json.loads((U/'metrics/COLD_REPLAY.json').read_text())
    assert all(r['all_png_exact'] and r['all_arrays_exact'] for r in cold.values())
    assert hashes(Path(p['asset']))==p['inputs']
    assert sha(p['original']['original_ply'])==p['original']['sha256']
    core='runtime.py demo.py geometry.py hatching.py render.py local_refinement.py refine_proxy.py model_adapter.py scene_catalog.py asset_archive.py viewer.py viewer.html presentation.py media.py'.split()
    core_exact={n:sha(SOURCE/n)==sha(U/'source_before'/n) for n in core};assert all(core_exact.values())
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    docs=U/'docs_snapshot';docs.mkdir()
    for n in ('UNIT019_PROTOCOL.json','UNIT019_DEMO_README_ZH.md'):shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04'/n,docs/n)
    source_hashes=hashes(U/'source_snapshot')
    js(U/'SOURCE_FINAL.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),files=source_hashes,material_algorithms_unchanged=core_exact))
    diff=[]
    before=U/'source_before';after=U/'source_snapshot'
    for name in sorted(set(hashes(before))|set(source_hashes)):
        a=(before/name).read_text(errors='replace').splitlines(True) if (before/name).exists() else []
        b=(after/name).read_text(errors='replace').splitlines(True) if (after/name).exists() else []
        diff.extend(difflib.unified_diff(a,b,fromfile='before/'+name,tofile='after/'+name))
    (U/'UNIT019_DIFF.patch').write_text(''.join(diff))
    r=json.loads((U/'metrics/REFINEMENT.json').read_text());local=json.loads((U/'metrics/LOCALITY.json').read_text())
    receipts={f.name.removesuffix('.receipt.json'):json.loads(f.read_text()) for f in sorted((U/'logs').glob('*.receipt.json'))}
    assert all(v['returncode']==0 for k,v in receipts.items() if k!='cold_browser_outer')
    assert receipts['cold_browser_outer']['returncode']==143
    amend=json.loads((U/'EXECUTION_AMENDMENT.json').read_text());amend['recovery_completed']=dict(receipt='logs/cold_browser_recovery.receipt.json',returncode=0,seconds=receipts['cold_browser_recovery']['seconds'])
    js(U/'EXECUTION_AMENDMENT.json',amend)
    cleanup=[]
    for name in ('browser','cold_browser_recovery'):
        row=json.loads((U/name/'CLEANUP.json').read_text());cleanup.extend(row['children'])
    cleanup.append(json.loads((U/'logs/relocated_viewer_cleanup.json').read_text()))
    cleanup.extend(json.loads((U/'logs/cold_browser_owned_cleanup.json').read_text())['children'])
    still=[x['pid'] for x in cleanup if Path('/proc',str(x['pid']),'comm').exists()]
    assert not still,still
    js(U/'metrics/RESOURCE_FINAL.json',dict(utc=now(),root_free_bytes=shutil.disk_usage('/').free,
        hdd_free_bytes=shutil.disk_usage(OUTPUT_ROOT).free,total_task_output_bytes=sum(f.stat().st_size for f in OUTPUT_ROOT.rglob('*') if f.is_file()),
        all_recorded_owned_viewer_driver_PIDs_absent=True,pids=[x['pid'] for x in cleanup],cpu_affinity=[0,1],numerical_threads=1,gpu=False,serial=True))
    progress=dict(genuinely_ran_old_model=True,available_models=['chair','lego','drums','ficus'],newly_rendered_model='chair',
        original_PLY_newly_rendered=True,original_gaussians=256690,original_GS_views=4,complete_static_states=12,
        local_geometry_candidate=dict(region=2,moved_vertices=r['moved_vertices'],displacement_max=r['displacement_max'],
            non_target_vertices_paths_exact=True,faces_labels_exact=True,target_path_length_retention=r['target_paths_after']['0']['length_world']/r['target_paths_before']['0']['length_world']),
        local_style_edit='region2 angle95->65; mesh and non-target paths/layers exact',
        style_far_other_L1_by_view=[v['style_probe']['far_other']['L1'] for v in local['views']],
        geometry_other_layer_changes_reported=True,actual_browser_save_edit_undo=True,cold_new_server_browser_import_exact=True,
        motion_frames=18,lossless_video_decoded_exact_frames=18,mp4_decoded_frames=18,cold_replay_png_arrays_exact_frames=18,
        relocated_tar_CLI_refine_edit_export_and_import=True,four_defaults_catalog_and_prior_examples_unchanged=True,
        visual_quality='partial; marginal smoothing benefit, core seat waves/density and thin-part defects remain',
        candidate_promoted=False,scientific_seal=False,
        reasoning='Bounded Chair geometry edit now exercised through real model reference, whole-object comparison, local style edit, download, stopped-server import and portable regeneration. Visual improvement was insufficient for promotion; next work should target seat-only style rather than further smoothing.')
    limitations=['Model-derived exploratory proxy; authored height regions; not a measured surface, automatic semantics or original Gaussian IDs.',
        'Chair proxy was already smoothed before this unit; one additional bounded pass has marginal visible benefit and is not promoted.',
        'Non-target geometry/path preservation does not imply unchanged visibility: lower-layer L1 changes1.2/0.4 in two views and contour changes are retained.',
        'Style edit has one fixed-mask far-other pixel L1 .4 at az17. Same-proxy AA diagnosis finds2/4 target samples there; original mask scores remain unchanged.',
        'Four exposed views and18-frame decode/replay are finite engineering evidence, not independent geometry, semantics, all-view occlusion, temporal stability or H1/H2/H5.',
        'Initial cold-browser outer exit143 retained with inner exit unknown; completed recovery is separate. Cause undetermined.',
        'Portable code/assets tested on current Linux CPU environment only; dependencies and original PLY are not bundled.']
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-21T22:26:49.825553+00:00')).total_seconds()/60
    status=dict(stage='UNIT_COMPLETE_CANDIDATE_NOT_PROMOTED',execution_state='completed',updated_utc=now(),elapsed_minutes=elapsed,
        engineering_execution='PASS_AFTER_ONE_RECORDED_ENGINEERING_RECOVERY',scientific_verdict='H1_H2_H5_NOT_TESTED; VISUAL_UPGRADE_NOT_ESTABLISHED',demo_progress=progress,
        artifacts=['PROTOCOL.json','metrics/REFINEMENT.json','metrics/LOCALITY.json','metrics/LOCALITY_RESIDUAL.json','metrics/VISUAL_REVIEW.json',
            'media/source_reference_all_views.png','media/full_object_before_after.png','media/middle_detail_supplement.png',
            'media/chair_orbit.mp4','media/chair_zoom.mp4','browser/BROWSER_VALIDATION.json','cold_browser_recovery/BROWSER_VALIDATION.json',
            'metrics/COLD_REPLAY.json','metrics/FINAL_ARCHIVE_REPLAY.json','portable_demo.tar.gz','PACKAGE_README_ZH.md','source_snapshot','UNIT019_DIFF.patch','EXECUTION_AMENDMENT.json'],
        tests=dict(real_asset_tests=2,TDD='existing material algorithm unchanged; real contracts tested, no artificial red step',actual_Firefox=True,
            command_receipts={k:dict(returncode=v['returncode'],path='logs/'+k+'.receipt.json') for k,v in receipts.items()}),
        blockers=[],limitations=limitations,scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(U/'STATUS.json',status)
    step='不再追加Chair平滑。在原默认Chair代理上，用现有多视角选区工具冻结一个人工座垫风格区（保留原中部剩余区、原几何和全部非目标路径）；基线保持原angle95，再只改该新座垫区angle65，固定spacing/length/width/ink。保留四全对象与弱侧/背视图、覆盖墨量、局部变化、保存后冷导入；只有观察到有用外观变化才作为可选示例。明确这是人工艺术控制，不是分割或H2/H5收益。'
    js(U/'NEXT.json',dict(action='continue',recommended_next_step=step,demo_progress=progress,
        reason='完整对象、局部修改、保存和冷重开已运行；额外几何平滑收益弱。当前高度区把座垫和椅背一起改，细化人工可编辑区域后改变方向，比继续平滑或新增模型更直接改善demo。',
        estimated_next_minutes=30,no_new_science_after_jst='2026-10-22T09:20:00+09:00',wrap_jst='2026-10-22T09:45:00+09:00',hardstop_jst='2026-10-22T10:00:00+09:00'))
    rows=[]
    for v in local['views']:
        a,b=v['coverage']['baseline'],v['coverage']['refined']
        rows.append(f"| {v['camera']['azimuth']} | {a['ink']:.3f} → {b['ink']:.3f} | {100*a['visible_target_support_fraction']:.3f}% → {100*b['visible_target_support_fraction']:.3f}% | {v['baseline_mask']['far_background']['L1']:.4f} | {v['contour_L1']:.4f} |")
    table='\n'.join(rows)
    commands='\n'.join(f"| {k} | {v['returncode']} | "+(f"{v['seconds']:.3f}" if 'seconds' in v else 'unknown')+' |' for k,v in receipts.items())
    report=f'''# Unit019：Chair局部平滑已实测，视觉收益不足，不晋级默认

执行状态 **completed**（工程范围），视觉仍 **partial**；约{elapsed:.1f}分钟。完成原Chair检查点四视角、一个有界中部平滑候选、四视角前后与局部改角、真实Firefox保存/撤销/导出、独立新服务导入、18帧完整视频解码/冷重绘以及最终tar迁移。没有H1/H2/H5结论，没有增加推荐示例。

## 选择与输入

已完整读取BRIEF、原大纲851行、P1 unit010/P2源与报告/NEXT，并实际检查unit018完整对象产物。unit018保存→关服务→导入→继续编辑已可用；当前瓶颈是Chair座面波纹与密线。源码显示Chair代理已做过一次整体有界平滑，因此本轮只冻结一个额外局部候选，避免重复扫参。保留旧P1视觉NO_GO和P2不可辨识结论，不把它们冒称本轮失败或成功。

协议SHA `{sha(U/'PROTOCOL.json')}`，在候选和四视角运行前冻结。输入 `{p['asset']}`，逐文件SHA见PROTOCOL。原PLY `{p['original']['original_ply']}`，SHA `{p['original']['sha256']}`，256690个原高斯，CPU SH3/EWA实际重绘az17/107/197/287、elev25、distance4.7。原GS图像不是独立表面真值或GPU等价认证。完整对照 `media/source_reference_all_views.png`。

## 实际改变与视觉决定

复用已有local_refinement/refine_proxy，10次正负步(.5/-.53)、最大位移.018世界单位。目标region2为人工 `-0.35 <= z <0.20` 中部区，包含座垫、扶手和部分椅背，不是语义座面。17058顶点/30000面中6375顶点移动，最大位移约包围盒对角线0.635%。非目标顶点/路径文件、全部面与标签精确；开放边/区域交界锁定，面积方向保护通过。原GS不变，没有填孔/焊接/GT替代。

目标路径720→722，总长72.743643→72.467318（保留99.620%）。目标邻面法线平均夹角21.7957°→20.0641°，这是平滑直接施加的代理诊断，不是恢复精度。四组完整对象与同框局部补图实际检查：少量折线略柔和，但整椅尺度几乎看不出变化，座面后缘堆线、主要波纹、缺损细杆和背面交界仍在。**不加入推荐catalog；候选仅在candidates中供复现。** 没有凭数值变好来晋级画质。

| Az | Target ink before → after | Visible target hatch support before → after | Baseline-mask far background L1 | Contour L1 |
|---:|---:|---:|---:|---:|
{table}

覆盖为全部可见目标代理像素上hatch>.1，分母/非零覆盖/空白距离见metrics/LOCALITY.json；不是独立语义、均匀间距或保墨审美评分。几何变化使两视图非目标lower-layer L1出现1.2/0.4，不能说所有非目标栅格精确不变。基线掩码保留7个远背景变化像素，总L1=2.55；union掩码该量为0，两套掩码都公开，未用后者覆盖前者。

局部编辑探针只将候选region2 angle95→65，四视角目标内变化非零，mesh/非目标paths与layers/depth/contour精确。az17固定2px标签带以外有1像素L1=.4，其余远其他/背景为0。额外同代理2xAA检查发现该像素4个子样本中2个属目标区域；原掩码分数原样保留，不宣称独立语义无泄漏。Angle65只是编辑演示，不把其不同墨量/方向当成平滑收益。图见media/full_object_before_after.png。

## 测试、冷重开与运行恢复

两项真实资产测试rc0：边界/非目标/位移/有向面积/重心锚点冷载入及继续改角，错误region与无界配置拒绝且不创建输出。本轮未改变算法，不制造无意义TDD红灯；只新增执行/验证脚本和浏览器测试回调。核心源码逐文件保持source_before一致，见SOURCE_FINAL.json。

第一轮实际Firefox对候选执行angle95→65→撤销、刷新、orbit/zoom按钮和4个实际下载（资产ZIP/PNG/orbit/zoom）。原冷重开外层exec session50181退出143、内层退出未知、无完成收据，保留cold_browser与logs/cold_browser_outer.receipt.json。原因未确定；仅终止其OWN_CHILDREN登记的viewer/WebDriver组969872/969877，两PID随后不存在。一次同会话工程恢复在cold_browser_recovery完成rc0；候选、参数、科学运行不重试。新服务/新Firefox上传保存ZIP，PNG、全部分层数组和styles/camera/display/selection精确，再编辑及撤销成功。

12 orbit +6 zoom全部实际重绘，FFV1共18帧解码RGB精确，MP4全解码18帧。完整接触表已检查：侧背弱视图和高密度座线继续保留。两个独立新进程串行冷重绘18帧PNG与全部数组精确。有限18帧不是独立持续路径对应或全时序/遮挡认证。

最终tar解压后，文档CLI冷绘候选、从原默认重新refine、局部angle65编辑与冷绘都通过，几何/路径及参考PNG精确；解压目录的新catalog服务导入浏览器下载ZIP同样精确。四默认/原catalog/既有示例逐文件保持原样。只有当前Linux依赖环境得到验证，不包含Python二进制或原始PLY。

| Command | Return code | Seconds |
|---|---:|---:|
{commands}

精确argv/cwd/起止/返回码见logs/*.receipt.json与REPRODUCE_ZH.md；原143及unknown内层码未覆盖。一次代码补丁上下文匹配失败也记录于logs/EDIT_ATTEMPTS.json，发生在交付执行前、无文件改变。CPU两核、数值与FFmpeg单线程、串行、无GPU/credentials/environment dump/nested models/push/merge；orchestration只读（临时scratch例外）。最终记录的本轮viewer/WebDriver PID均不存在。

## 交付与下一步

`portable_demo.tar.gz` 包含可运行四模型目录、未晋级Chair候选、原始预览、资产与源码。入口：`cd {U}/portable_demo && ./run.sh viewer --scene chair`。候选用 `--asset "$PWD/candidates/chair_middle_refined"`，或在目录viewer导入saved_zips/chair_saved_asset.zip。完整命令见PACKAGE_README_ZH.md。

STATUS/NEXT/REPORT与源码快照已写。只哈希实际验证证据，不给科学成功seal；scientific_seal=false，reported_not_independently_verified。NEXT=continue：{step}
'''
    (U/'REPORT_ZH.md').write_text(report)
    reproduce=['# 实际执行命令与返回码\n']
    for name,receipt in receipts.items():
        reproduce.append('## '+name+'\n\n```json\n'+json.dumps(receipt,ensure_ascii=False,indent=2)+'\n```\n')
    (U/'REPRODUCE_ZH.md').write_text('\n'.join(reproduce))
    root_readme=f'# 最新可运行交付：unit019（候选未晋级）\n\n```bash\ncd {U}/portable_demo\n./run.sh viewer --scene chair\n```\n\n'+(U/'PACKAGE_README_ZH.md').read_text()
    (OUTPUT_ROOT/'DEMO_README_ZH.md').write_text(root_readme)
    (SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/DEMO_README_ZH.md').write_text(root_readme)
    js(OUTPUT_ROOT/'DELIVERY_STATUS.json',dict(unit='unit_019',execution_state='completed',demo_progress=progress,
        package=str(U/'portable_demo.tar.gz'),readme=str(OUTPUT_ROOT/'DEMO_README_ZH.md'),status=str(U/'STATUS.json'),
        recommended_defaults_unchanged=True,candidate_promoted=False,scientific_seal=False,supervisor_verification='reported_not_independently_verified'))
    # Mutable runtime/profile/session logs and supervisor responses are deliberately excluded.
    files=[]
    for folder in ('source_snapshot','docs_snapshot','assets','renders','source_model','media','metrics'):
        files.extend(f for f in (U/folder).rglob('*') if f.is_file())
    for name in ['PROTOCOL.json','STATUS.json','NEXT.json','REPORT_ZH.md','PACKAGE_README_ZH.md','REPRODUCE_ZH.md','SOURCE_BEFORE.json','SOURCE_FINAL.json',
                 'UNIT019_DIFF.patch','EXECUTION_AMENDMENT.json','portable_demo.tar.gz','browser/BROWSER_VALIDATION.json','browser/CLEANUP.json',
                 'browser/EXPORT_STATE.json','browser/chair_saved_asset.zip','cold_browser_recovery/BROWSER_VALIDATION.json','cold_browser_recovery/CLEANUP.json']:
        files.append(U/name)
    manifest={str(f.relative_to(U)):sha(f) for f in sorted(set(files))}
    js(U/'EVIDENCE_SHA256.json',dict(utc=now(),scope='Validated finite engineering artifacts and their honest limitations; not full scientific certification.',
        scientific_seal=False,files=manifest,excluded_interrupted_attempt='cold_browser; remains available unsealed with outer143/innerunknown'))
    assert all(sha(U/name)==digest for name,digest in manifest.items())
    print(json.dumps(dict(execution_state='completed',elapsed_minutes=elapsed,validated_hashed_files=len(manifest),next='continue',candidate_promoted=False)))

if __name__=='__main__':main()
