import json,subprocess,time
from pathlib import Path
from runtime import ROOT,EXP,ART,OUT,sha,source_hashes,atomic_json
def finish():
    data=json.loads((ART/'DATA_FREEZE.json').read_text());scenes={};lines=['# Lego / Chair 实际原生局部边缘编辑报告','',
    '本轮直接加载两份 30000 步 PLY，保留完整 SH degree=3；使用 stock 3DGS 原生 CUDA forward/backward。监督来自实际原始 TRAIN Blender PNG，loss 保持原训练的显示 RGB 编码。仅剖面测量用明确 sRGB EOTF 转到线性 RGB。没有读取原始 TEST 图像，没有重训练底座。','',
    '两场景均是单前景物体；只找到原 PNG 的 AA alpha，未找到可信部件标签。因此执行的是 **label-free relative edge-support/local-control**，不是 object-pair contact / C1。内部 RGB 边缘与外轮廓分别评价。核贡献是可见支持责任，不是物理边缘身份；原 JointLeak 负例未改。','',
    '每场景固定 8 edit-train + 4 dev + 8 edit-holdout；全部属于原 GS TRAIN-seen。F/C/既有 arc 已被旧研究使用，8 个新 edit-holdout 也不能证明此前全研究未见；本轮只有封印后只读的探索性编辑留出评价，**不是独立正式 TEST**。所有优化只读 8 个 edit-train，配置/预算/UID/目标生成规则在评分前冻结，dev 没有触发参数调整。','',
    '原位置、opacity、高阶 SH 固定；仅选中行的 DC 可加有界共享 3D delta，协方差组再开放有界 scale/rotation。DC display delta≤0.15；scale ratio∈[1/1.2,1.2]；raw quaternion 相对 delta norm≤0.08。full SH 仍逐相机原生求值和 clamp_min，不把它假设成共享常数 RGB 的线性算子。零步 DC 投影只是一条独立诊断，未用作训练初始化；不宣称它约束了所有相机的有效 SH 颜色。','',
    '固定预算 min(ceil(0.10N),32768)，TRAIN-only 精确全模型 alpha·T / 颜色 Jacobian 流式统计，无 top-k 截断。relative score 将尺度/连通边段平衡证据除以自身可见质量密度，并考虑训练可见率；对照为原始 band contribution 排序和共同可见率/可见质量分层随机。旧 SH0/top64 排名同 PLY SHA，但目标/SH 语义不同，只作历史引用，不混入本轮公平排名。','',
    '局部目标为 band L1 + 10×outside 相对 B0 MSE；普通目标为全图 0.8 L1+0.2(1−SSIM)。两者共享相同参数权限及 coverage/协方差正则。coverage 实际走原生 alpha 到 scale/rotation 梯度，不开放 opacity。每满 8 步均另计算全部 8 训练相机的真实目标并保存；336 步为 42 个完整 epoch。同优化墙钟普通对照另外保存，初始化和候选选择成本分开。','',
    '宽度来自固定参考的边界法向，斜线/圆弧/等亮度/低对比/纹理 fixture 已实测。参考不合格剖面与结果不合格剖面均记录拒绝；低对比 W=null，不使用 17 条水平线。主指标始终覆盖完整固定 band。共同有效宽度按相机先平均再宏平均，不用缺测剖面制造改善。','']
    for scene,v in data['scenes'].items():
        statuspath=ART/f'{scene}_FINAL.json'
        if not statuspath.exists():continue
        state=json.loads(statuspath.read_text());scenes[scene]=state
        lines += [f'## {scene.title()}','',f'原模型 SHA256 `{v["model_sha256"]}`，N={v["ply"]["count"]}，45 个高阶 SH 系数/核；源训练 commit `{v["training_source_commit"]}`。原数据有 {len(v["original_TRAIN_indices"])} 个 TRAIN 相机，实际底座 GS 训练用了 {len(v["actual_GS_TRAIN_indices"])} 个。','']
        if state.get('phase')=='FAILED':lines += [f'场景失败：{state.get("error")}; 已完成产物与可续跑状态见 FINAL。',''];continue
        lines += ['| 方法 | 步数 | 优化秒 | heldout band MSE | 全图 PSNR | outside变化 MSE | 全前景孔洞 | AA outline MSE |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for arm,m in state['holdout'].items():
            x=m['mean_per_view'];op=state['optimization'].get(arm,{})
            lines.append(f'|{arm}|{op.get("steps",0)}|{op.get("optimizer_seconds",0):.3f}|{x["band_mse"]:.7g}|{x["whole_psnr"]:.3f}|{x["outside_damage"]:.7g}|{x["foreground_holes"]:.7g}|{x["outline_alpha_mse"]:.7g}|')
        base=state['holdout']['B0']['mean_per_view'];ours=state['holdout']['relative_cov']['mean_per_view'];ordinary=state['holdout']['relative_cov_ordinary']['mean_per_view']
        imp=1-ours['band_mse']/max(base['band_mse'],1e-20);adv=1-ours['band_mse']/max(ordinary['band_mse'],1e-20)
        lines += ['',f'固定主臂 relative_cov 相对 B0 的 heldout band MSE 改变：{imp:.2%} 改善；相对同权限 336 步普通微调：{adv:.2%} 改善（负数表示更差）。该单种子探索性结果不支持正式方法优势。开发与训练逐视角表、所有剖面、权限审计和完整 epoch 保存在 results。',f'候选选择实测 {state["selection"]["selection_seconds"]:.3f} 秒，编辑 {state["selection"]["budget"]} 个原 UID；relative 的 TRAIN band 贡献覆盖 {state["selection"]["selectors"]["relative"]["band_contribution_coverage"]:.2%}，这是可见贡献覆盖，不是错误核召回。','',f'[四个开发视角同相机对比](figures/{scene}_dev_fourview_contactsheet.jpg)；[四个编辑留出视角](figures/{scene}_edit-holdout_fourview_contactsheet.jpg)。每行均是原参考/B0/普通颜色/relative颜色/普通协方差/relative协方差/全模型T候选叠加；原生像素边缘裁剪及放大均单独保存。','',f'既有完整33帧开发 arc：[B0](videos/{scene}_B0_arc0_33.mp4)、[颜色](videos/{scene}_relative_color_arc0_33.mp4)、[协方差](videos/{scene}_relative_cov_arc0_33.mp4)。另保存新的完整360°原生可视化 orbit33；它没有参考照片、不参与优化或质量选优。所有视频为 H264/yuv420p/faststart，逐帧完整解码并核对33个不同frame与camera SHA；没有2D墨线替换原生RGB。','']
    lines += ['## 结论边界','',
    '本轮完成两实际底座的原生可见贡献选择、自然 TRAIN RGB 的受限编辑、同权限普通对照、等数量选择对照、只读编辑留出评分及完整媒体。若指标接近原始基线误差底限，不能把微小变化包装成明显自然修复；失败图与视频原样交付。','',
    'R1 颜色能力认证、R4 已知UID尺度探针和 Task B 未执行；没有把自然编辑失败称为表示不可达定理，没有加入平面 oracle，没有完整作者 COB-GS 运行，也没有声称新颖性、独立 split、三种子或正式 GO。独立人工视觉 GO 仍待用户审阅。完整360°视频只证明实际渲染完成，不证明时间重投影优势。','']
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    deps=data['read_only_dependencies'];after={p:sha(p) for p in deps};integrity={p:deps[p]==after[p] for p in deps}
    old_changes=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT,text=True).splitlines()
    unrelated=[p for p in old_changes if not p.startswith(('experiments/edge_control_lego_chair_v1/','artifacts/edge_control_lego_chair_v1/','out/edge_control_lego_chair_v1/'))]
    final={'phase':'COMPLETE' if len(scenes)==2 and all(s.get('phase')=='COMPLETE' for s in scenes.values()) else 'PARTIAL_SCENE_FAILURE','scenes':{k:{'phase':v['phase'],'holdout_views':len(data['scenes'][k]['roles']['edit-holdout']),'actual_native_media':v.get('media',[])} for k,v in scenes.items()},'model_and_read_only_dependency_integrity':integrity,'integrity_pass':all(integrity.values()),'unrelated_tracked_changes':unrelated,'independent_human_visual_GO':'PENDING','original_TEST_images_read':False,'formal_independent_TEST':False,'remaining':'Independent human visual review; scientific replication / official baselines if pursuing method claims'}
    if not all(integrity.values()) or unrelated:raise AssertionError('source/old file integrity')
    atomic_json(ART/'FINAL.json',final)
    paths=[p for p in ART.rglob('*') if p.is_file() and p.name not in ('SOURCE_MAP.json','PUBLISH_READBACK.json')]
    atomic_json(ART/'SOURCE_MAP.json',{'original_read_only_dependencies':deps,'new_code':source_hashes(),'curated_artifacts':{str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths},'source_data_freeze_sha256':sha(ART/'DATA_FREEZE.json'),'actual_production_runner':'experiments/edge_control_lego_chair_v1/scripts/runner.py'})
    return final
