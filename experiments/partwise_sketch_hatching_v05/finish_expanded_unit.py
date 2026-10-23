"""Write an honest bounded-unit handoff from independently validated outputs."""
import runtime
from runtime import js,sha,now,OUTPUT_ROOT
from pathlib import Path
import argparse,json,datetime,subprocess


def finish(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text());summary=json.loads((unit/'SUMMARY.json').read_text())
    launch=json.loads((OUTPUT_ROOT/'orchestration/continuation_001/LAUNCH.json').read_text())
    inventory=json.loads((unit/'continuation_001/RESUME_INVENTORY.json').read_text())
    end=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime.fromisoformat(launch['started_at_jst'])
    assert end<datetime.datetime.fromisoformat(launch['must_end_jst'])
    checks={scene:json.loads((unit/f'VALIDATION_{scene}.json').read_text()) for scene in p['scenes']}
    for scene,v in checks.items():
        assert len(v['checks'])==len(p['scenes'][scene]['cameras']) and v['actual_scaled_matching_valid']
    delivery=unit/'continuation_001/delivery'
    replay={};query={}
    for scene in p['scenes']:
        for operation in ('tint','opacity'):
            key=scene+'_'+operation;r=json.loads((unit/'continuation_001'/('replay_'+key)/'RECEIPT.json').read_text())
            assert all(r['all_arrays_exact'].values());replay[key]=r
        query[scene]=json.loads((unit/'continuation_001'/('query_'+scene)/'RECEIPT.json').read_text())
        assert query[scene]['no_weak_or_occluded_records_pruned']
    media=json.loads((unit/'media/VIDEO_VALIDATION.json').read_text());assert media['all_frames_decoded'] and media['FFV1_frames_exact']
    receiptfiles=sorted((unit/'logs').glob('resume_*.receipt.json'));receipts={f.name:json.loads(f.read_text()) for f in receiptfiles}
    failed_receipts={k:r for k,r in receipts.items() if r['returncode']!=0}
    assert set(failed_receipts)=={'resume_lego_eval3_c001.receipt.json'}
    assert failed_receipts['resume_lego_eval3_c001.receipt.json']['returncode']==-15
    assert receipts['resume_lego_eval3_retry_c001.receipt.json']['returncode']==0
    progress=dict(previous_gap='Four-view bindings left many original rows UNKNOWN; unit004 transfer failed joint locality/coverage in half its scheduled views.',
        actual_advance='Added all eight explicitly exposed unit004 views to the four original BUILD views without changing thresholds; reconstructed original-row M1/path/full-footprint bindings and executed matched original-GS controls at eight separate frozen cameras.',
        milestones=dict(
            M1_region_original_binding=dict(state='partial',scope='Both complete original-row universes retain six-channel evidence/exposure/conflict/UNKNOWN, input hashes and 12-view provenance; no semantic/native calibration.'),
            M2_path_original_support=dict(state='partial',scope='Every frozen Chair/Lego anchor retains stroke/segment/face/bary/world, full accepted original-ID alpha*T CSR, depth eligibility, rejected mass and UNKNOWN at all eight evaluation views.'),
            M3_actual_linked_control=dict(state='finite_CPU_comparison_validated',scope='Actual source-only full-SH tint controls with verified BUILD RGB-effect matching, plus independently rerendered opacity diagnostics; bounded sparse path edits, not whole-part usable style or native Gaussian hatching.'),
            M4_reusable_asset_demo=dict(state='partial',scope='Delivered runnable source/query/replay entrypoint, four exact cold replays, two unpruned path queries, complete-object panels and decoded source arc/tint videos. Original PLY and local Python remain external dependencies.')),
        reasoning='Expanded observations alter real original-ID support and visible source edits, while conflicts and unsupported rows remain explicit. Two scenes and authored-proxy intent do not certify semantics, physical attachment, native rendering, or H1/H2/H3.',
        scenes={scene:{k:v[k] for k in ('source_count','M1_transition','selection_counts','selection_transition','pass_counts','evaluated_and_validated_views')} for scene,v in summary['scenes'].items()})
    history=dict(engine_attempt_0_returncode=1,engine_recovery_1_returncode=1,
        engine_EXIT_reason_field=None,usage_limit_cause_source='Parent continuation BRIEF; original EXIT reason fields remain null.',
        batch_outer_exit=143,last_completed_child_returncode=0,
        interrupted_Chair_view1_child_returncode=-15,interrupted_Chair_view1_signals=[15],
        archived_partial_outputs=['interrupted_chair_view_1','continuation_001/interrupted_lego_view_3'],
        continuation_Lego_view3_original_child_returncode=-15,continuation_Lego_view3_outer_exit=143,
        continuation_Lego_view3_retry_returncode=0,continuation_interruption_cause='UNKNOWN',prior_unit004_unknown_child_code_preserved=True,
        original_TDD_red_returncode=1,original_TDD_green_returncode=0,
        old_Ficus_NO_GO_and_CPU_depth_discrepancy_unchanged=True)
    status=dict(unit='unit_005',stage='expanded_BUILD_original_kernel_comparison_handoff',execution_state='partial',
        frozen_experiment_execution_complete=True,work_in_progress=False,
        scientific_verdict=summary['scientific_verdict'],scientific_seal=False,gaussian_link_progress=progress,
        scenes=progress['scenes'],pass_counts=summary['pass_counts'],
        tests=dict(reused_completed_stages=len(inventory['skipped_stages']),frozen_evaluation_views=8,
            new_vs_old_M1_projections_validated=8,source_tint_arm_renders=32,source_opacity_rerenders=8,
            actual_scaled_BUILD_budget_renders=32,cold_replays_exact=4,unpruned_path_queries=2,
            prior_TDD_tests=3,continuation_targeted_renderer_fixtures=2,
            original_ID_alpha_T_full_SH_RGB_path_CSR_and_saved_metrics_validated=True),
        artifacts=dict(protocol='PROTOCOL.json',summary='SUMMARY.json',resume_inventory='continuation_001/RESUME_INVENTORY.json',
            bindings='results/<scene>/SOURCE_BINDING.npz',paths='results/<scene>/<view>/path_support.npz',
            validation=['VALIDATION_chair.json','VALIDATION_lego.json'],
            panels='results/<scene>/ALL_EVALUATION_VIEWS.png',delivery='continuation_001/delivery',media='media/VIDEO_VALIDATION.json'),
        blockers=['Native CUDA per-ID calibration unavailable','M1 and bounded path support remain incomplete/UNKNOWN',
            'Proxy intent is not independent semantic or physical ground truth','Three-times BUILD evidence volume is not an equal-observation-budget diversity ablation',
            'Local numerical gate passes can involve small visible target patches; full-part style quality not established'],
        original_failure_evidence=history,updated_utc=now(),finished_utc=end.isoformat(),
        continuation_started_jst=launch['started_at_jst'],continuation_deadline_jst=launch['must_end_jst'],
        continuation_elapsed_minutes=(end-start).total_seconds()/60,finished_before_deadline=True,
        resource_discipline=dict(serial=True,cpu_affinity=2,numeric_threads=1,GPU=False,no_nested_models=True),
        next_action='stop')
    future='If separately authorized, audit the saved leaking retained-old Lego IDs (including 49033 and 174330) and unsupported anchors to separate footprint/view-mask mismatch from newly promoted M1 support. Then compare broad-view evidence against denser original-view evidence at a fixed observation budget and matched source-edit effect; no mask widening, gate relaxation, or native/semantic success claim.'
    nxt=dict(action='stop',recommended_next_step=future,recommended_next_step_zh='如另获授权，先审计Lego保留旧核49033、174330及不支持锚点，区分投影掩码不一致与新增M1支持，再做等观察预算的多视角/原视角加密对照；不放宽门槛或掩码。',
        gaussian_link_progress=progress,reasoning='This authorization resumes exactly unit005. Its bounded experiment and handoff are complete; no automatic unit006 or further science launched.',
        stop_reason='bounded_authorization_complete',unit006_started=False)
    js(unit/'STATUS.json',status);js(unit/'NEXT.json',nxt)
    lines=['# Unit005：扩充 BUILD 后的原始 Gaussian 绑定与源编辑',
        '', '**execution_state=partial；冻结实验已完成；UNCERTIFIED_CPU_MAPPING；scientific_seal=false。**', '',
        '本单元在2026-10-23的新授权下续跑。只替换昨日执行截止时间，协议、相机、采样、阈值和输入不变。完成后NEXT=stop，不启动unit006。', '',
        f"协议SHA256：`{sha(unit/'PROTOCOL.json')}`。续跑前核对167份既有文件哈希及冻结输入；跳过Chair BUILD、4个预算、配平和首个评估共7个rc0阶段。仅补齐Chair其余3视角及Lego全部阶段，再独立验证保存证据。", '',
        f"新绑定在8个评估视角的joint通过数为{summary['pass_counts']['specific']['joint']}/8，旧绑定为{summary['pass_counts']['previous_path']['joint']}/8。UNKNOWN有所减少，不代表局部编辑在每个新视角都改善；失败视角与不足覆盖均保留。", '',
        '旧unit004的16视角中只有8个同时通过局部性与覆盖，其失败结论保持不变。本轮把这些已曝光低/高仰角视角明确纳入BUILD，从4视角扩充到12视角；不再称它们为留出测试。新评估为每场景4视角：方位61/241°、仰角24/60°、384²，Chair距离5.1、Lego5.3。相对于已审计v05相机外参不重合；旧v04曝光及源GS训练重合仍未核实。', '',
        'M1仍在真正接受贡献的位置使用原始PLY行ID与alpha×T，保存6通道区域证据、曝光、跨视角冲突及UNKNOWN。路径仍为Chair128段/Lego93段的固定中点锚；完整footprint仍使用3px可见路径capsule及2px边界带。所有门槛不变，新增观察既能增加支持，也能使旧支持退回UNKNOWN。', '',
        '| Scene | 原行数 | 旧UNKNOWN→新UNKNOWN | UNKNOWN→支持 | 支持→UNKNOWN | 旧冲突→新冲突 | 旧选核→新选核 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for scene,s in summary['scenes'].items():
        t=s['M1_transition'];c=s['selection_counts']
        lines.append(f"| {scene} | {s['source_count']} | {t['old_unknown']}→{t['new_unknown']} | {t['unknown_to_supported']} | {t['supported_to_unknown']} | {t['old_conflicts']}→{t['new_conflicts']} | {c['previous_path']}→{c['specific']} |")
    lines += ['', '四臂是扩充BUILD绑定、旧4视角footprint绑定、与新绑定同核数的最近路径中心对照、按新曝光分箱打乱原ID。数组兼容字段`previous_path`在本单元表示**旧footprint**，不是unit002的裸路径选择。旧臂核数不同；另外三臂核数相同。4个原BUILD视角的实际全源raw RGB L1配平至四臂最小完整强度效果的85%；又在保存强度下实际重渲染32次验证预算，无评估视角拟合。', '',
        '改色先求值原完整SH3并下界clamp，再按原行权重混合固定颜色；高阶视角效果保留在(1-strength)部分。源SH、中心、协方差、旋转、行数和顺序不改。opacity是另一个副本的opacity×(1-.5×未缩放strength)，完整重算透射率和贡献；没有跨臂配平，不能拿来宣称比较优势。', '',
        '| Scene / Arm | 局部性/4 | 覆盖/4 | joint/4 |', '|---|---:|---:|---:|']
    for scene,s in summary['scenes'].items():
        for arm,v in s['pass_counts'].items():lines.append(f"| {scene} / {arm} | {v['locality']} | {v['coverage']} | {v['joint']} |")
    lines += ['', '局部性仍要求目标腐蚀内部mean L1≥.02、远区改变量占比≤2%；覆盖要求至少8个支持锚点、至少50%的支持锚点编辑mass>.01、保留加权mass比例≥5%。空内部/不足支持不记成功。以下同时给出像素范围和编辑强度，避免把少数像素通过写成整部件可用。', '',
        '| Scene / View | 区域4像素 / capsule / 内部 | 新目标mean L1 | 新远区% | 新编辑锚点比例 / 保留mass比例 | 新/旧joint |',
        '|---|---:|---:|---:|---:|---|']
    def num(x):return 'UNKNOWN' if x is None else f'{x:.4f}'
    for scene,s in summary['scenes'].items():
        for r in s['views']:
            v=r['visual']['specific'];a=r['arms']['specific'];c=r['coverage']['specific']
            lines.append(f"| {scene}/{r['view']} | {v['authored_region4_pixels']} / {v['path_capsule_pixels']} / {v['eroded_interior_pixels']} | {num(a['target_interior']['L1_mean'])} | {a['far_non_target_fraction']*100:.3f} | {num(c['edited_anchor_fraction'])} / {num(c['retained_mass_fraction'])} | {r['joint']['specific']} / {r['joint']['previous_path']} |")
    lines += ['', '| Scene | 旧UNKNOWN责任质量范围 | 新UNKNOWN责任质量范围 |', '|---|---:|---:|']
    for scene,s in summary['scenes'].items():
        old=s['previous_unknown_responsibility_range'];new=s['new_unknown_responsibility_range']
        lines.append(f'| {scene} | {old[0]*100:.2f}%–{old[1]*100:.2f}% | {new[0]*100:.2f}%–{new[1]*100:.2f}% |')
    failed=next(r for r in summary['scenes']['lego']['views'] if r['view']=='orbit_241_24_5.3')
    d=failed['failure_ID_diagnosis'];ret=d['groups']['retained_old_IDs'];new=d['groups']['new_selected_IDs'];top=d['largest_far_bound_original_IDs'][0]
    fv=failed['visual']['specific'];fc=failed['coverage']['specific']
    lines += ['', '这些投影在同一真实原GS trace上比较新旧M1，分别保存soft_q及整核UNKNOWN全部移入通道0的abstaining_q。UNKNOWN减少表示获得更多作者区域支持证据，不是语义分割准确率提升。新增证据量约为原来的3倍，本轮不能把效果单独归因于视角多样性。', '',
        f"Lego失败视角241°/24°只有{fv['eroded_interior_pixels']}个腐蚀内部像素，整个作者区域4有{fv['authored_region4_pixels']}像素；其变化像素只占区域的{fv['changed_authored_region4_fraction']*100:.2f}%，区域平均clipped RGB L1={fv['authored_region4_mean_clipped_RGB_L1']:.5f}。新绑定远区占比8.044%，旧绑定4.727%；新编辑锚点比例{fc['edited_anchor_fraction']*100:.2f}%、保留mass比例{fc['retained_mass_fraction']*100:.2f}%。因此这是弱覆盖且局部性失败，不能用非零改色美化成可用编辑。", '',
        f"逐ID读回表明：新选择中保留的旧核{ret['selected_IDs']}个，其加权far责任为{ret['weighted_far_responsibility']:.4f}；新加入{new['selected_IDs']}个核为{new['weighted_far_responsibility']:.4f}。最大far颜色上界对应旧核{top['source_index']}，12个BUILD中的worst far={top['expanded_BUILD_worst_far_fraction']*100:.3f}%，该评估视角far={top['evaluation_far_fraction']*100:.3f}%。失败不能简单归因于新增UNKNOWN转支持；有限BUILD投影仍不足以约束新视角。颜色上界不等于精确损伤分摊，此分析仅解释已保存结果，未修改选择。", '',
        '完整对象面板包含原GS RGB、作者区域与固定路径、full-T原核支持诊断、实际源改色、实际opacity编辑、代理上的3D排线。另保存新旧源编辑与放大差分图。实际变化集中于选定的稀疏路径附近，尤其Lego小目标不能被解释为整个铲斗可用的风格化；代理排线图与源改色图始终分开。目标/腐蚀内部像素、整物体和区域内变化比例详见VISIBILITY_READBACK.json。', '',
        '每个评估视角均独立复算原ID近裁剪/排序映射、alpha、T链、质量和完整SH RGB；全部路径锚点包括遮挡/零支持/UNKNOWN均保留，CSR原ID、深度资格和保留质量逐项核对。新旧M1投影、4臂保存RGB指标、覆盖和joint门槛均复算一致；opacity使用修改后的源重新核对trace。4次独立进程冷重放逐数组精确，2次路径查询保留全部锚点。3项原TDD及2项本次针对性渲染夹具均保留回执。', '',
        '另实际渲染4个相机位置的30°短弧和4级源改色，视频全帧解码，FFV1逐像素一致；这是源编辑复放，不是360°转台、交互性能或时序稳定性认证。', '',
        '历史失败未改写：昨日attempt_0与recovery_1引擎EXIT均rc1，原reason字段null；配额原因来自续跑BRIEF。批次外层143与已完成子rc0分开保留。Chair视角1原子rc=-15且记录SIGTERM，残留文件在interrupted_chair_view_1；今日新名称重跑rc0不覆盖它。本次Lego最后视角也有一次外层143/子进程-15，原因UNKNOWN，未完成数组归档continuation_001/interrupted_lego_view_3；新名称重跑rc0与完整验证单独记录。旧unit004的UNKNOWN子退出码、Ficus NO_GO、CPU深度差异及旧证据锁仍保持。', '',
        '局限：CPU EWA replica并非原生CUDA逐ID认证；协方差平面深度不是实测表面，legacy T>.5更新不是条件半质量median。只有两个对象；作者代理自洽不是独立语义/表面真值。保留真实孔洞、薄结构缺失和不支持区域，不宣称H1/H2/H3或原生Gaussian排线。', '',
        f"续跑耗时（生成本报告时）{status['continuation_elapsed_minutes']:.2f}分钟，截止{launch['must_end_jst']}。可运行入口：`continuation_001/delivery/run.sh`；命令见该目录README_ZH.md。数据封存只覆盖经核验的有限工程证据，scientific_seal=false。", '',
        'NEXT=stop。本次授权仅恢复unit005。如另获授权，建议做等观察预算的视角覆盖消融，并检查剩余UNKNOWN与Lego不支持锚点；不直接扩大掩码或降低门槛。']
    (unit/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    js(unit/'continuation_001/HANDOFF_VALIDATION.json',dict(utc=now(),required_fields_present=True,
        execution_state=status['execution_state'],next_action=nxt['action'],scientific_seal=False,
        protocol_unchanged=sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256'],
        completed_success_receipts=len(receipts)-len(failed_receipts),preserved_interrupted_receipts=len(failed_receipts),source_replays=4,path_queries=2,media_frames_decoded=True))
    print(json.dumps(dict(execution_state=status['execution_state'],pass_counts=summary['pass_counts'],next_action='stop',elapsed_minutes=status['continuation_elapsed_minutes'])),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);finish(ap.parse_args().unit)
