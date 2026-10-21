"""Create factual Chinese report from validated raw metrics; no render/tuning."""
from runtime import *
import csv
import io
import subprocess
from PIL import Image, ImageDraw, ImageFont

def main():
    result=json.loads((ROOT/'metrics/RESULTS.json').read_text())
    valid=json.loads((ROOT/'DELIVERY_VALIDATION.json').read_text())
    assert result['valid'] and valid['valid']
    audit=json.loads((ROOT/'audit/HEADROOM.json').read_text())
    recovery=json.loads((ROOT/'EXECUTION_AMENDMENT.json').read_text())
    rows=[]; times=[]
    for row in result['frames']:
        f=row['frame']; d=row['display']; r=row['ring_reference']
        ink_off=sum(x['off_total_ink'] for x in d['parts'].values())
        ink_on=sum(x['on_total_ink'] for x in d['parts'].values())
        row['whole_visible_object_total_ink_ratio']=ink_on/ink_off
        rows.append(dict(frame=f['id'],azimuth=f['azimuth'],distance=f['distance'],operation_L1=d['nonzero_operation_L1'],
            hatch_retained_ratio=1.,hatch_exact=d['hatch_exact'],total_visible_ink_ratio=ink_on/ink_off,
            ring_visible_length_world=r['eligible_visible_ring_length_world'],ring_hidden_length_world=r['expected_hidden_noncontour_length_world'],
            B1_ring_reference_support=r['support']['B1_total']['visible_fraction'],B2_ring_reference_support=r['support']['B2_total']['visible_fraction'],
            near_ring_hatch_overlap=d['near_ring_hatch_pixels'],hatch_ring_overlap=d['hatch_ring_overlap_pixels']))
        for arm in ('B1_like','B2_existing'):
            meta=json.loads((ROOT/'renders'/f['sequence']/f['id']/arm/'render.json').read_text())
            times.append(meta['seconds'])
    text=io.StringIO(); writer=csv.DictWriter(text,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    output_path(ROOT/'metrics/FRAME_SUMMARY.csv').write_text(text.getvalue())
    statics=rows[:4]; allink=[r['total_visible_ink_ratio'] for r in rows]
    leak=result['isolated_part_leakage']
    far_wrong=sum(x['metrics']['region_ink']['far_other'] for x in leak)
    far_bg=sum(x['metrics']['region_ink']['far_background'] for x in leak)
    aa=sum(x['metrics']['region_ink']['aa_band'] for x in leak)
    visible=[r['ring_visible_length_world'] for r in rows]
    raw_summary=dict(frames=24,hatch_retained_ratio=1.,all_hatch_contour_geometry_exact=True,
                     structure_display_nonzero_L1_range=[min(r['operation_L1'] for r in rows),max(r['operation_L1'] for r in rows)],
                     total_visible_ink_ratio_range=[min(allink),max(allink)],visible_ring_length_range=[min(visible),max(visible)],
                     isolated_static_part_far_wrong_ink=far_wrong,isolated_static_part_far_background_ink=far_bg,
                     isolated_static_part_aa_band_ink=aa,final_render_seconds_median=float(np.median(times)),final_render_seconds_p95=float(np.quantile(times,.95)),
                     physical_boundary_support_world=0.,H2='UNIDENTIFIABLE_FOR_H2',display='VALID',scope=result['scope'])
    write_json(ROOT/'metrics/SUMMARY.json',raw_summary)
    panels=Image.new('RGB',(1024,4*694),'white')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    for i,(source_row,summary_row) in enumerate(zip(result['frames'][:4],rows[:4])):
        f=source_row['frame']; d=source_row['display']; basey=i*694
        with Image.open(ROOT/'media/frames/static'/f'{i:04}.png') as img: panels.paste(img,(0,basey))
        local=[x for x in leak if x['frame']==f['id']]
        coverage='/'.join(f'{d["parts"][str(p)]["hatch_support_fraction"]:.1%}' for p in (1,2,3))
        spacing='/'.join(f'{d["parts"][str(p)]["distance_to_hatch_p95_px"]:.2f}' for p in (1,2,3))
        lines=[f'Both arms: hatch retained 100%; visible hatch coverage shade/stem/base = {coverage}',
               f'Both arms: distance-to-hatch P95 shade/stem/base = {spacing} px (empty-area proxy)',
               f'Added rings: image L1 = {d["nonzero_operation_L1"]:.3f}; visible total ink ratio = {summary_row["total_visible_ink_ratio"]:.4f}',
               f'Near-ring hatch pixels = {d["near_ring_hatch_pixels"]} unchanged; hatch/ring overlap = {d["hatch_ring_overlap_pixels"]}',
               f'Isolated-part far wrong ink = {sum(x["metrics"]["region_ink"]["far_other"] for x in local):.6f}; AA-band ink = {sum(x["metrics"]["region_ink"]["aa_band"] for x in local):.4f}',
               'Physical boundary support = 0; H2 UNIDENTIFIABLE. Added authored-ring display is not association gain.']
        draw=ImageDraw.Draw(panels)
        for j,line in enumerate(lines): draw.text((8,basey+551+j*23),line,fill='black',font=font)
    panels.save(ROOT/'media/static_metrics_comparison.png')
    table='| 静态方位 | 加环实际L1 | 可见环长/隐藏环长(world) | 环参考支持 B1→B2 | 总可见墨量比 | 近环hatch像素(不变) |\n|---:|---:|---:|---:|---:|---:|\n'
    for r in statics:
        table+=f'| {r["azimuth"]}° | {r["operation_L1"]:.6f} | {r["ring_visible_length_world"]:.4f}/{r["ring_hidden_length_world"]:.4f} | {r["B1_ring_reference_support"]:.2%}→{r["B2_ring_reference_support"]:.2%} | {r["total_visible_ink_ratio"]:.6f} | {r["near_ring_hatch_overlap"]} |\n'
    report=f'''# experiment_001：P2物理边界零余量，固定结构显示诊断

**H2：ZERO_HEADROOM / UNIDENTIFIABLE_FOR_H2；固定结构显示工程验证通过。没有关联机制增益结论，也不是全局方法NO_GO。**

已完成且只完成一个有界实验。用户原话“感觉目前的质量以及足够，直接开始下一步实验”记录为 `USER_ACCEPTED_GT_VISUAL_BASELINE_FOR_P2`。接受 unit010 sealed outputs/edited named434：260灯罩0°、24支杆、150缩短底座；unit011未使用、不续跑，旧NO_GO不改写。当前接受不代表RaDe-GS重建、全时序认证或H1/H2成功。

## 为什么没有伪造U/S/D收益

完整读取851行大纲、BRIEF、P1路线、unit010报告和实际source/assets。601个unit010封存文件校验通过。868顶点/1728面由3个闭合面连通分量组成，各自只含一个部件；共享部件边0、 eligible物理边界长度/面积0，已有114.375330241世界长度排线中错误GT部件长度0。支杆和底座的空间相交不构成网格邻接；没有KNN连接、焊接、虚构链或噪声弱化。

隐性GT审计发现：`core_walk_v2.generate_strokes`在GT部件内采种、`walk`遇GT异部件停止；`renderer.render`在same-ray深度之外还检查visible GT part==owner face GT part。因此这不是粗分部基线，零越界不构成H2改善。renderer/core/walker与unit010 SOURCE_LOCK逐文件相同。没有改标签，mIoU改善不适用。

按brief允许的零余量替代，冻结 **B1-like：排线+原轮廓、物理profile环关闭；B2-existing：排线+原轮廓+已有profile环，即用户接受基线**。唯一变量是 `render(structure=False/True)`，同434路径/种子/墨色/标签/几何/遮挡/相机/后端。既有864条profile边共27.703901807世界长度为人工GT几何结构，不是共享语义边界，不是编辑区边界，也不是普通深度恢复或新B2成果。没有B3、方向引导或边界修正；U/S/D不适用并明确未运行。

## 冻结与真实运行

协议提交 `ef135f45` 在任何候选渲染前；实现提交 `ff6aafd3`，SOURCE_LOCK冻结实际源/输入。512²，2xAA，hatch1px，contour0.8px，ring0.65px，深度容差0.006；固定原始世界光照/墨色，无LOD。静态30/120/210/300°历史已曝光；orbit12帧(7.5+30k°)和zoom8帧(52.5°、仰角25°、距离5.2→4.2)在结果前由metadata选定，只称construction holdout，不称未见重建数据。

24相机×2臂实际调用相同后端，另12张静态隔离部件排线只作评分。全部完整灯罩/支杆/底座在画面内。四张B2与unit010保存PNG像素精确复现；24对hatch、轮廓、labels与depth精确相同。原墨量保留100%，无需以少画来换分数。

{table}

全部24相机，加环非零L1范围 {raw_summary['structure_display_nonzero_L1_range'][0]:.6f}–{raw_summary['structure_display_nonzero_L1_range'][1]:.6f}；总可见墨量比 {min(allink):.6f}–{max(allink):.6f}，增加来自显式结构环。近环hatch重叠、每部件覆盖与distance-to-hatch p50/p95逐帧保存；后者是空白距离代理，不是真实相邻笔触间距。没有裁剪、杂线减少或审美偏好收益证据。原始表与分母见 `metrics/RESULTS.json`、`FRAME_SUMMARY.csv`、`SUMMARY.json`。

连续解析lathe ray oracle独立于三角渲染，但共享人工形状定义。环长按≤0.002world中点采样，分开报告可见、预期隐藏、固定2px AA带、unknown和与轮廓合并排除的长度；可见非轮廓环长范围 {min(visible):.4f}–{max(visible):.4f}。24帧并非独立对象样本，无显著性或泛化统计。环参考图像支持可包含原hatch/轮廓贡献，因此并非自动提取精度。

12张隔离静态part hatch对独立解析标签，远错误部件墨量总计 {far_wrong:.8f}，远背景 {far_bg:.8f}，AA带 {aa:.8f}；这些是继承GT条件下有限可见输出结果，不能掩盖隐藏侧或全路径时序问题。renderer原始part/depth拒绝fragment counts也保存，但包含重叠且不等于泄漏像素。

## 验证、失败和恢复

TDD首先真实断言失败：没有连通边界却返回ELIGIBLE，rc1原样保留；最小修复后通过。最终8项行为测试含：真实walker在同标签跨面/异标签停止、invalid/missing evidence→UNKNOWN、分离曲面不KNN相连、固定非目标hatch/轮廓、no-edit/delete-all/3px drift响应和解析隐藏参考已知交点。保存真实图像的4组no-op/delete-all/drift及12组16像素远部件注入控制均有预期反应。

原始git add因sparse checkout拒绝rc1，随后只对授权新目录用--sparse成功；一次只读快照路径猜测rc1，已用SOURCE_LOCK与真实source_snapshot路径核实。首次zoom与isolated阶段发生 {recovery['overlap_seconds']:.6f}s 调度重叠：两个数值进程各1线程、均限定CPU[0,1]且总量≤2，但违背冻结串行规则。保留两组原产物和原rc0于 `attempt_schedule_overlap/`；执行级恢复仅串行重跑完全相同两阶段，{recovery['bitwise_scientific_files']}份PNG/NPZ逐文件SHA完全相同。没有参数重选、第二实验或科学结果重试。完整变更说明见 `EXECUTION_AMENDMENT.json`。

orbit12/zoom8视频逐相机渲染固定3D路径；6fps FFV1离线展示，全部20帧解码RGB与源PNG逐帧精确，相应12/8帧各自全部不同。不是动画静帧、实时性能或完整时序认证。最终48次比较渲染中位 {np.median(times):.3f}s/P95 {np.quantile(times,.95):.3f}s，仅CPU离线；原重叠尝试时延不混入此摘要。

26旧SEAL哈希及两个旧worktree HEAD/干净状态复核相同；没有写原GS/C8/joint/raw data，没有GPU、安装、下载、secret、push或merge。新science只在experiment_001，数值线程1、两核affinity。源/命令/原退出码、完整对象同相机图和近边界放大、所有分母、实际视频SHA均保留。

## 交付和有限结论

- 完整对象同相机对照：`media/static_all_frames.png`；每幅原生512²，不以局部截图替代全灯。
- 边界近景：`media/static_*_shade_top_2x.png`、`*_shade_bottom_2x.png`、`*_base_top_2x.png`；裁剪由固定几何profile投影定义，nearest2x。
- 全帧接触图与视频：`media/orbit_all_frames.png`、`zoom_all_frames.png`、`orbit_comparison.mkv`、`zoom_comparison.mkv`。
- 原始可见/遮挡/覆盖/暗度/近环重叠、oracle掩码、控件响应、源锁定：experiment_001的audit/metrics/renders/isolated目录。

固定结构开关有非零可观测显示效果，保存了接受基线。由于既有完整GT物理分部使H2没有可测交界支持，本轮没有证明关联机制有用、没有证明粗分部或噪声RaDe-GS受益、没有自动曲线恢复/新颖性/H1–H5成功结论。保留简单系统，不把工程完成当作机制成功。

下一步只推荐一个独立、另行授权实验：在同一整灯灯罩的连通曲面上预先定义一条人工编辑区边界、独立regionIDs及oracle来源，冻结共同粗标签误差和无噪声/保墨控制，检验停止/留白是否减少该编辑区越界；明确它不是物理几何棱边或自动语义恢复。当前不执行，详见NEXT.json。
'''
    # Replace the displayed total with the exact audited sum, not rounded source prose.
    report=report.replace('114.375330241',f'{sum(audit["stroke_length_by_part_world"].values()):.9f}')
    output_path(DOC/'REPORT_ZH.md').write_text(report)
    output_path(ROOT/'REPORT_ZH.md').write_text(report)
    repro='# Reproduction and actual receipts\n\nBranch partwise-sketch-hatching-p2-v03; protocol ef135f45; implementation ff6aafd3. Do not replay into an existing output root. Completed stages are immutable; recover by reading STATUS/NEXT, SOURCE_LOCK and receipts first.\n\nAll actual science commands use the explicit existing venv, CPU affinity0,1, numeric threads1, CUDA_VISIBLE_DEVICES empty, PYTHONDONTWRITEBYTECODE1 and TMPDIR under new orchestration/scratch. No old runner/sealer is called.\n\n'
    for path in sorted((ROOT/'runtime').glob('*.json')):
        if path.name.endswith('.started.json'): continue
        r=json.loads(path.read_text())
        if 'command' in r:
            repro+=f'## {path.name}\n\nReturn code: {r.get("returncode")}\n\n```json\n{json.dumps(r["command"],ensure_ascii=False)}\n```\n\n'
    output_path(ROOT/'REPRODUCE.md').write_text(repro)
    write_json(ROOT/'NEXT.json',dict(automatic_continuation=False,current_stage='COMPLETE',
        recommended_next_experiment='单次完整台灯上的oracle编辑区边界停止/留白诊断',
        reason='现有三物理部件无共享连通边界，H2不可辨识。连通灯罩中的显式编辑区可提供真实可走越界支持，但必须另记regionIDs和人工oracle来源。',
        required_controls=['评价前冻结编辑区边界、相同粗标签扰动及种子','保持完整三部件/同相机/同后端','无噪声强3D基线与匹配保墨控制','GT只能显式评分，不能修复无关联baseline'],
        not_authorized_to_run_now=True,recovery='本experiment001完成后停止；若封存未完成，只完成验证/封存，不重跑科学阶段。'))
    print(json.dumps(native(raw_summary),ensure_ascii=False,allow_nan=False))

if __name__=='__main__': main()
