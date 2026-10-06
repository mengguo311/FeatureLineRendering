"""Assemble a factual report after fixed assets, heldout renders and audit exist."""
import runtime as rt
import json,numpy as np
from pathlib import Path
def read(p):return json.loads(Path(p).read_text())
def pct(v):return f'{100*v:.1f}%'
def main():
 freeze=read(rt.ART/'INPUT_FREEZE.json');verdict=read(rt.ART/'SCIENTIFIC_VERDICT.json');audit=read(rt.ART/'results/ARTIFACT_AUDIT.json');lines=[];summary={}
 lines+=['# 多视角原轮廓核融合为固定三维区域：真实实验报告','',f"**科学结论：{verdict['status']}。{verdict['summary_zh']}**",'',
 '本轮完成两场景、各24构建/4开发/8保留视角、四个固定实体三角面控制和各33相机完整视频。所有视角均来自已训练/可能历史曝光的相机域，保留仅指 construction-holdout，不是 GS-unseen 或新盲测。内部 RGB 细节层未实施。', '',
 '入口：[离线交付索引](INDEX.html) · [研究与作者证据](RESEARCH_ZH.md) · [历史实际审计](history/HISTORY_AUDIT_ZH.md) · [复现](REPRODUCE.md) · [协议](PROTOCOL.json) · [独立审计](results/ARTIFACT_AUDIT.json)。', '',
 '## 真实结果与可读性','', '以下覆盖是相对经校准 CPU replica 的原 SH3 alpha 轮廓（包括孔洞边界），容差3px；本轮没有调用 CUDA native。内部指距当前轮廓8px以外的前景。墨面积/前景是全部投影墨像素除以前景面积，包含背景墨量，可能超过100%，不是前景涂覆率。深内部与远背景占墨量的分母均为所有墨像素。它们是诊断，不能代替观看图像，也不是 mesh GT precision/recall。负空间为二维前景 convex hull 内的背景 proxy，另列真正封闭背景孔；没有输入 mesh、扫描或深度传感器。artifact_diameter_p95_px 为投影mask内距离变换的局部内接直径p95，是像素宽度proxy，不是世界管径。','']
 for n,s in freeze['scenes'].items():
  asset=read(rt.ART/'results'/(n+'_asset.json'));dev=read(rt.ART/'results'/(n+'_develop.json'));reserved=read(rt.ART/'results'/(n+'_reserved_complete.json'));fus={a:read(rt.ART/'results'/(n+'_fusion_'+a+'.json')) for a in ['two_source','multi24']};rp=rt.ROOT/dev['chosen']['path'];region=np.load(rp);metrics=reserved['metrics'];armstats={}
  for arm in ['thin','widened','two_source','multi24']:
   rows=[v[arm] for v in metrics.values()];armstats[arm]={k:float(np.mean([r[k] for r in rows])) for k in rows[0]}
  summary[n]=dict(arms=armstats,selected_width=dev['chosen']['width'],ink_match_error=dev['ink_match_relative_error'],fusion_counts={a:fus[a]['selected_count'] for a in fus},region=dict(level_support_count=len(region['support_ids']),retained_owner_count=len(region['retained_owner_ids']),vertex_anchor_count=len(np.unique(region['vertex_anchor_ids'])),vertices=len(region['vertices']),triangles=len(region['faces']),six_neighbor_components=int(region['component_count']),axis_diameter_p50=float(2*np.median(region['support_axes'])),axis_diameter_p95=float(2*np.quantile(region['support_axes'],.95)),displacement_p95=float(np.quantile(region['vertex_displacement'],.95)),original_mahalanobis_p95=float(np.quantile(region['vertex_original_mahalanobis'],.95))))
  lines += [f'### {n.title()}','',verdict['scenes'][n]['assessment_zh'],'',f'[八保留视角完整板](media/{n}/reserved_eight_FULL.png) · [预览](media/{n}/reserved_eight_preview.jpg) · [完整33帧视频](media/{n}/arc/fixed_region_33.mp4) · [所有帧](media/{n}/arc/ALL_33_FRAMES.jpg) · [离线旋转](assets/{n}/viewer_3d.html)','',
   '|固定臂|平均轮廓覆盖3px|墨面积/前景|深内部占墨量|远背景占墨量|负空间填充|', '|---|---:|---:|---:|---:|---:|']
  for arm,m in armstats.items():lines.append(f"|{arm}|{pct(m['coverage3'])}|{pct(m['ink_over_foreground'])}|{pct(m['deep_interior_fraction'])}|{pct(m['background_far_fraction'])}|{pct(m['negative_space_fill_fraction'])}|")
  mm=armstats['multi24'];rr=summary[n]['region'];lines+=['',f"主 multi24 的封闭孔填充率视角均值 {pct(mm['hole_fill_fraction'])}，投影局部内接直径p95的视角均值 {mm['artifact_diameter_p95_px']:.2f}px。保留部分开口不代表孔洞恢复完整；负空间错误单独计量。",'',f"旧图原样 thin 与 widened 拓扑完全相同。DEV 自动选定宽度参数 {dev['chosen']['width']} voxel；widened 世界半径 {dev['widened']['radius']:.6g}，DEV 平均墨量相对匹配误差 {pct(dev['ink_match_relative_error'])}。它不是相同核数/相同世界宽度比较。",'',
   f"新规则两源候选 {fus['two_source']['selected_count']:,}，24源候选 {fus['multi24']['selected_count']:,}（原模型 {s['count']:,}）；其中24源单视角支撑 {fus['multi24']['selected_single_source']:,}、多视角支撑 {fus['multi24']['selected_multi_source']:,}。候选→score level 后支撑 {rr['level_support_count']:,}→裁剪后实际 voxel owner {rr['retained_owner_count']:,}→顶点 owner {rr['vertex_anchor_count']:,}，几者不能混用。",'',
   f"主资产 {rr['vertices']:,} 顶点 / {rr['triangles']:,} 三角面；体素六邻接组件 {rr['six_neighbor_components']:,}（不是语义部件数）。支撑椭球各轴直径 p50/p95={rr['axis_diameter_p50']:.6g}/{rr['axis_diameter_p95']:.6g} 世界单位，顶点到真实 raw-voxel owner 原中心位移 p95={rr['displacement_p95']:.6g}。原协方差归一化位移 p95={rr['original_mahalanobis_p95']:.4g}；薄 Gaussian 经世界宽度膨胀可远超其原法向 sigma，因此绝不能把输出当成原始足迹无损恢复。",'',
   f"主文件：[GLB](assets/{n}/multi24/outer.glb) · [OBJ](assets/{n}/multi24/outer.obj) · [核支撑 PLY](fusion/{n}/multi24_kernel_support.ply) · [区域来源 NPZ]({rp.relative_to(rt.ART)})。GLB/OBJ 是实体三角面，不是2px屏幕中心线。",'']
 extra=read(rt.ART/'post_protocol_dev_ink_diagnostic/SUMMARY.json')
 lines += ['## DEV 等墨量追加诊断','',
 '主协议 widened 的半径上限不能达到目标墨量，原误差保留。随后单独冻结追加协议，只用原四个 DEV 扩大同一个旧 A 图的固定世界半径并二分匹配；没有修改主规则、主资产或主评价。它是主协议后的诊断，reserved 已被主实验使用，不称新的盲测。仅匹配 DEV 平均墨量，不保证逐相机或 reserved 等墨量。', '',
 '|场景|追加 DEV 匹配误差|固定世界半径|主/追加 reserved 墨像素均值|主/追加 coverage3|主/追加远背景占墨量|主/追加负空间填充|',
 '|---|---:|---:|---:|---:|---:|---:|']
 for n,e in extra.items():
  m=e['mean_reserved_metrics']['multi24'];b=e['mean_reserved_metrics']['post_protocol_matched']
  lines.append(f"|{n}|{100*e['DEV_relative_ink_error']:.6f}%|{e['DEV_radius']:.6g}|{m['ink_pixels']:.1f}/{b['ink_pixels']:.1f}|{pct(m['coverage3'])}/{pct(b['coverage3'])}|{pct(m['background_far_fraction'])}/{pct(b['background_far_fraction'])}|{pct(m['negative_space_fill_fraction'])}/{pct(b['negative_space_fill_fraction'])}|")
 lines += ['', '本轮 multi24 pipeline 相对该旧图描粗对照的定位收益真实存在：相近 DEV 墨量下，旧碎图描粗仍遗漏结构，并把墨量放到背景与负空间。来源、选核、表示和背景约束同时不同，不能把收益单因子归给更多来源。主 multi24 的大片填面仍然是失败，不能由这项对照救成 GO。Chair 在 reserved 的平均墨量差尤其明显，不能把表中结果解释为逐图公平等面积比较。详见 [追加协议](PROTOCOL_MATCHED_INK_AUDIT.json)、[完整分析与图板](post_protocol_dev_ink_diagnostic/REVIEW_ZH.md)。', '',
 '## 来源覆盖与最早失败假设','',
 'construction 全 N 数据显示，24源所选核在各构建视角捕获的轮廓贡献质量中位数约 Lego 98.56% / Chair 98.43%；两源为42.99% /25.28%。按 raw 排名前0.5%的诊断为33.01% /44.53%，按 relative 排名为6.88% /6.67%。这是捕获质量及不同预算的诊断，不是等预算算法优势，也不能反写旧 accepted 空与 ALL8 REFUSED。所有核均在同一完整原 T 下测量，未以 K 截断的未知量冒充零。', '',
 '原核空间覆盖、被选候选数量、有效椭球、裁剪后体素 owner 与实际顶点 owner 有显著区别；详细空间分布与多视角重复见 [相机覆盖](supplemental/CAMERA_DIRECTION_DOMAIN.png)、[两源/24源原中心](supplemental/TWO_VS_24_SELECTED_WORLD_CENTERS.png)、[贡献和 distinct views](supplemental/MASS_BUDGET_AND_DISTINCT_VIEWS.png)、[支撑缩减](supplemental/SUPPORT_DOMAIN_REDUCTION.png)。空间散点图每组至多确定性抽样12000个ID，样本列表保存，不把显示样本伪称全量。', '',
 '最早被实际结果否定的假设是：把多方向强轮廓参与核的完整椭球并成一层较宽区域，可以同时改善连贯性并保持轮廓可读。max-over-views 没有惩罚同一个核在其他可见视角处于形体内部，滚动轮廓的并集因此可能铺开为表面域；foreground veto 只能拒绝背景，不能阻止形体内的大片覆盖。输出还包含世界宽度扩张和体素 closing，不能把所有问题唯一归因于选核。这里是与代码和观察一致的机制解释，未经独立因果消融。', '',
 '区域表示确实避免了仅以稀疏中心短链表现形体，但这次容许支撑域过大，以表面占据替代了可读轮廓。该失败只否定本轮冻结模型和参数域，不证明原 Gaussian 不含相对轮廓支撑，也不证明任何固定宽区域都不可能成功。后续若研究局部 sheet/ridge 或对跨视角内部响应作约束，应另行冻结新规则与评价域；本轮没有结果后重调或补画答案。', '',
 '## 方法、控制与适用域','',
 '输入是两个只读 seed1729/iteration30000/SH3 原 PLY。先由原生 alpha=.5 的自动轮廓（不填封闭孔）构造1.5/3px带，用完整 accepted alphaT 的全N伴随提取原ID参与与可见质量。1.5px只是诊断；实际融合使用3px带，不能称两个尺度共同融合。每源 soft=relative×sqrt(raw/(raw+.05))，跨源取最大；高阈值种子与一次短距弱支撑 hysteresis 取代旧0.5%预算。重复像素质量和 distinct views 分开保存。','',
 '以原 Gaussian 中心、完整旋转/scale 与 soft score 构造椭球占据并集；加入固定世界宽度、极值轴裁剪、一个六邻接 closing。所有 construction alpha 前景约束只在物空间执行一次，允许2px容差，画面外为unknown。输出为 edge occupancy proxy，不是 SDF、真实表面或经认证的物理棱边。原协方差轴仅作为来源支撑，不是边切向/表面法向。','',
 '候选宽度仅 .4/.8/1.2 voxel，按冻结 DEV 目标选一次，随后封印。width_world_floor字段是协方差膨胀参数，不等于最终管半径；真实轴长在region NPZ。two_source与multi24都使用同一新表示，但同时改变来源支持、2/24视角背景约束与bbox得到的网格间距；它是整个pipeline的源数量对照，不能纯因果归因给选核器。thin与widened使用旧A完整原拓扑，thin世界几何经逐bit核对。','',
 '顶点主anchor是全局最近保留raw体素的真实owner，另存最近中心诊断；不暗示全部顶点与owner体素已验证网格相邻。每个closing填补有原始邻域owner CSR、最近支撑距离和方向，背景拒绝保存首次视角及体素位置。merge图含占据交叠候选和裁剪后接口，不把所有裁剪前候选冒称最终拓扑。没有手画部件/路径、独立2D描边lift、逐相机调位或隐藏mask。','',
 '相机只投影固定mesh并做资产自z-buffer。没有得到独立校准的原不透明物体表面遮挡，因此全部图和旋转器相对原物体均为x-ray，后方杂带完整显示。没有把高斯中心期望/中位深度冒充真实表面深度。','']
 for n,s in freeze['scenes'].items():
  c=s['coverage'];lines.append(f"- {n}: 86 metadata相机中构建24、DEV4、reserved8；最远相机距最近构建方向 {c['max_nearest_construct_deg']:.2f}°，方向z范围 {c['camera_z_range']}。构建名单：{', '.join(s['roles']['construction'])}；DEV：{', '.join(s['roles']['dev'])}；reserved：{', '.join(s['roles']['reserved'])}。")
 lines += ['', '相机域在物体上半球；底部和超出已有方向域的完整性未验证。33arc是历史已见、较短弧段，仅检验这一段固定投影与媒体完整性，不是全面稳定性或新视角泛化证书。','',
 '## 校准、复现和保护','',f"独立全产物审计状态 **{audit['status']}**；详细数量和各项证据见 [ARTIFACT_AUDIT.json](results/ARTIFACT_AUDIT.json)。原模型、历史报告/negative evidence、旧branch heads均不因本轮改变。旧 automatic accepted空/ALL8 REFUSED、NO_GO_FRAGMENTED和capacity证书状态保持原样。",'',
 'GPU0有外来占用，所以本轮没有调用GPU。经过四个历史construction native缓存实际校准的CPU replica：RGB MAE≤3e-7、全核mass相对L1误差≤1.06e-5、top1% mass ID Jaccard=1；feature forward和adjoint亦逐项核对。个别近深度并列核有贡献转移，尾差与未确认原因保留；不宣称bit-exact，也不称本轮执行了CUDA native。校准JSON绑定实际CPU代码SHA。','',
 '核心11项合成/契约测试通过，真实RED→GREEN与中间失败见 tdd；实际renderer/export、相机、来源与heldout、固定几何和完整视频另有独立验证。媒体helper只声称新增后实际33帧验收。执行问题见 [EXECUTION_NOTES_ZH.md](EXECUTION_NOTES_ZH.md)。所有资源守卫未降低：root4GiB/sharedGit1.5GiB/stage6GiB，生产1GiB守卫未改。','',
 '独立审计验证309个完成seal、1652条文件hash引用、11项当前核心代码hash，原输入/历史保护文件417个、历史branch heads19个未变。两段交付H264均完整独立解码33/33，帧hash匹配，faststart通过。离线viewer的内嵌几何与JavaScript语法已静态核验；环境没有浏览器，未声称实际拖动交互已经浏览器验收。','',
 '发现并保留一个导出hash口径缺陷：旧图 thin/widened 记录的geometry hash在导出前使用int64索引，NPZ/GLB导出为int32。独立核验按数值逐一验证GLB/OBJ/NPZ相等，并验证转回int64后精确匹配原记录；未覆盖主seal掩盖错误。multi24/two_source使用int32，主视频的固定geometry hash直接匹配。追加诊断统一为float32顶点/int32索引。详见执行说明和独立审计的 HASH_SCHEMA_PREEXPORT_INT64。','',
 '本轮没有新训练、新网络、安装或第三方方法代码执行；文献只读实际作者全文。没有相对Hao–Mukai、EdgeGaussians、EMAP或CurveGaussian的新颖性声明。研究先行约20分钟并行墙钟，实际读取5篇primary全文并完成历史审查/校准后冻结协议；这是早于30–40分钟研究目标预算完成，并非声称耗满该时长。','',
 '## 未实现与结论边界','',verdict['limitations_zh'],'',
 '最终提交与远端读回记录放在 ignored `out/gaer_multiview_contour_regions_v01/DELIVERY.json`，在push之后生成，避免自引用commit循环。']
 rt.atomic_json(rt.ART/'RESULT_SUMMARY.json',summary);(rt.ART/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
 cards=[]
 for n in ['lego','chair']:
  cards.append(f'''<section><h2>{n.title()}</h2><p><a href="assets/{n}/viewer_3d.html">离线旋转 · 四臂切换</a>　<a href="assets/{n}/multi24/outer.glb">GLB</a>　<a href="assets/{n}/multi24/outer.obj">OBJ</a>　<a href="fusion/{n}/multi24_kernel_support.ply">原核 PLY</a></p><div class="images"><figure><img src="media/{n}/reserved/r_1/RGB_SH3.png"><figcaption>r_1 · construction-holdout · 原 SH3</figcaption></figure><figure><img src="media/{n}/reserved/r_1/multi24_fixed_mesh.png"><figcaption>唯一固定区域 · 相对 GS 为 x-ray</figcaption></figure></div><p>{verdict['scenes'][n]['assessment_zh']}</p><video controls preload="metadata" src="media/{n}/arc/fixed_region_33.mp4"></video><p><a href="media/{n}/reserved_eight_FULL.png">原尺寸八视角完整对照</a>　<a href="media/{n}/arc/ALL_33_FRAMES.jpg">完整33帧条带</a></p></section>''')
 html='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>固定三维轮廓区域 · 实验交付</title><style>body{max-width:1180px;margin:36px auto;padding:0 24px;font:17px/1.65 system-ui;background:#fafafa;color:#202733}a{color:#155eb0}section{margin:36px 0;border-top:1px solid #ccd3db;padding-top:16px}.images{display:flex;gap:12px}figure{margin:0;flex:1}img{width:100%;background:white}video{width:100%;max-height:600px}strong{color:#a03624}figcaption{font-size:14px}</style><h1>多视角原核 → 固定三维轮廓区域</h1><p><strong>'''+verdict['status']+'''</strong> · '''+verdict['summary_zh']+'''</p><p><a href="REPORT_ZH.md">完整中文报告</a>　<a href="RESEARCH_ZH.md">作者原文研究</a>　<a href="REPRODUCE.md">复现</a>　<a href="results/ARTIFACT_AUDIT.json">独立核验</a></p><p>两场景各24构建 / 4开发 / 8保留；每个视频33相机、同一个geometry hash。未输入扫描或GT mesh，未训练网络。资产是实体三角面，始终固定；内部纹理层未实施。</p>'''+''.join(cards)+'''<p>图像与视频保留所有后方轮廓区域，没有逐相机隐藏mask。打开离线旋转器无需服务器或原Gaussian模型。</p></html>'''
 (rt.ART/'INDEX.html').write_text(html)
 print('REPORT_WRITTEN',flush=True)
if __name__=='__main__':main()
