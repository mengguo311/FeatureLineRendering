# 多视角原轮廓核融合为固定三维区域：真实实验报告

**科学结论：NO_GO_CONTOUR_OVERFILL。多视角原核融合明显补足形体覆盖，但宽区域将大面积表面填实，未达到连续、可读的三维轮廓带目标。保留真实固定宽区域草模，不将高覆盖率当成视觉成功。**

本轮完成两场景、各24构建/4开发/8保留视角、四个固定实体三角面控制和各33相机完整视频。所有视角均来自已训练/可能历史曝光的相机域，保留仅指 construction-holdout，不是 GS-unseen 或新盲测。内部 RGB 细节层未实施。

入口：[离线交付索引](INDEX.html) · [研究与作者证据](RESEARCH_ZH.md) · [历史实际审计](history/HISTORY_AUDIT_ZH.md) · [复现](REPRODUCE.md) · [协议](PROTOCOL.json) · [独立审计](results/ARTIFACT_AUDIT.json)。

## 真实结果与可读性

以下覆盖是相对经校准 CPU replica 的原 SH3 alpha 轮廓（包括孔洞边界），容差3px；本轮没有调用 CUDA native。内部指距当前轮廓8px以外的前景。墨面积/前景是全部投影墨像素除以前景面积，包含背景墨量，可能超过100%，不是前景涂覆率。深内部与远背景占墨量的分母均为所有墨像素。它们是诊断，不能代替观看图像，也不是 mesh GT precision/recall。负空间为二维前景 convex hull 内的背景 proxy，另列真正封闭背景孔；没有输入 mesh、扫描或深度传感器。artifact_diameter_p95_px 为投影mask内距离变换的局部内接直径p95，是像素宽度proxy，不是世界管径。

### Lego

Lego 的底板、车体、铲斗和抬升支架比旧稀疏图及两源区域更完整，部分开口仍保留；但车身、铲斗与驾驶室大片填黑，底板出现粗块和后方杂域，轮廓结构被面域吞并。结论为形体恢复 PARTIAL、轮廓带 NO_GO。

[八保留视角完整板](media/lego/reserved_eight_FULL.png) · [预览](media/lego/reserved_eight_preview.jpg) · [完整33帧视频](media/lego/arc/fixed_region_33.mp4) · [所有帧](media/lego/arc/ALL_33_FRAMES.jpg) · [离线旋转](assets/lego/viewer_3d.html)

|固定臂|平均轮廓覆盖3px|墨面积/前景|深内部占墨量|远背景占墨量|负空间填充|
|---|---:|---:|---:|---:|---:|
|thin|13.4%|0.6%|62.0%|0.0%|0.0%|
|widened|72.5%|64.7%|59.2%|17.9%|27.7%|
|two_source|50.8%|31.3%|70.5%|0.3%|4.3%|
|multi24|100.0%|85.2%|76.3%|0.1%|10.9%|

主 multi24 的封闭孔填充率视角均值 33.8%，投影局部内接直径p95的视角均值 91.31px。保留部分开口不代表孔洞恢复完整；负空间错误单独计量。

旧图原样 thin 与 widened 拓扑完全相同。DEV 自动选定宽度参数 0.4 voxel；widened 世界半径 0.0767601，DEV 平均墨量相对匹配误差 22.4%。它不是相同核数/相同世界宽度比较。

新规则两源候选 38,248，24源候选 164,600（原模型 310,475）；其中24源单视角支撑 39,958、多视角支撑 124,642。候选→score level 后支撑 161,460→裁剪后实际 voxel owner 35,940→顶点 owner 23,500，几者不能混用。

主资产 119,704 顶点 / 242,184 三角面；体素六邻接组件 182（不是语义部件数）。支撑椭球各轴直径 p50/p95=0.023005/0.115863 世界单位，顶点到真实 raw-voxel owner 原中心位移 p95=0.0637224。原协方差归一化位移 p95=1.297e+04；薄 Gaussian 经世界宽度膨胀可远超其原法向 sigma，因此绝不能把输出当成原始足迹无损恢复。

主文件：[GLB](assets/lego/multi24/outer.glb) · [OBJ](assets/lego/multi24/outer.obj) · [核支撑 PLY](fusion/lego/multi24_kernel_support.ply) · [区域来源 NPZ](regions/lego/multi24_0p4.npz)。GLB/OBJ 是实体三角面，不是2px屏幕中心线。

### Chair

Chair 的椅腿、扶手、椅背整体位置和连续外周得到恢复，若干扶手开口仍可辨；但座面与靠背大量填实，俯视接近整物体剪影。结论为形体恢复 PARTIAL、轮廓带 NO_GO。

[八保留视角完整板](media/chair/reserved_eight_FULL.png) · [预览](media/chair/reserved_eight_preview.jpg) · [完整33帧视频](media/chair/arc/fixed_region_33.mp4) · [所有帧](media/chair/arc/ALL_33_FRAMES.jpg) · [离线旋转](assets/chair/viewer_3d.html)

|固定臂|平均轮廓覆盖3px|墨面积/前景|深内部占墨量|远背景占墨量|负空间填充|
|---|---:|---:|---:|---:|---:|
|thin|22.9%|0.7%|48.2%|0.2%|0.0%|
|widened|58.8%|49.8%|54.0%|23.0%|24.8%|
|two_source|56.5%|26.9%|61.8%|1.3%|5.6%|
|multi24|100.0%|101.2%|81.0%|0.1%|13.9%|

主 multi24 的封闭孔填充率视角均值 53.3%，投影局部内接直径p95的视角均值 127.27px。保留部分开口不代表孔洞恢复完整；负空间错误单独计量。

旧图原样 thin 与 widened 拓扑完全相同。DEV 自动选定宽度参数 0.4 voxel；widened 世界半径 0.0713471，DEV 平均墨量相对匹配误差 63.3%。它不是相同核数/相同世界宽度比较。

新规则两源候选 13,227，24源候选 103,617（原模型 256,690）；其中24源单视角支撑 28,773、多视角支撑 74,844。候选→score level 后支撑 100,646→裁剪后实际 voxel owner 32,099→顶点 owner 20,495，几者不能混用。

主资产 116,763 顶点 / 236,678 三角面；体素六邻接组件 138（不是语义部件数）。支撑椭球各轴直径 p50/p95=0.0211952/0.105916 世界单位，顶点到真实 raw-voxel owner 原中心位移 p95=0.0640662。原协方差归一化位移 p95=2.078e+04；薄 Gaussian 经世界宽度膨胀可远超其原法向 sigma，因此绝不能把输出当成原始足迹无损恢复。

主文件：[GLB](assets/chair/multi24/outer.glb) · [OBJ](assets/chair/multi24/outer.obj) · [核支撑 PLY](fusion/chair/multi24_kernel_support.ply) · [区域来源 NPZ](regions/chair/multi24_0p4.npz)。GLB/OBJ 是实体三角面，不是2px屏幕中心线。

## DEV 等墨量追加诊断

主协议 widened 的半径上限不能达到目标墨量，原误差保留。随后单独冻结追加协议，只用原四个 DEV 扩大同一个旧 A 图的固定世界半径并二分匹配；没有修改主规则、主资产或主评价。它是主协议后的诊断，reserved 已被主实验使用，不称新的盲测。仅匹配 DEV 平均墨量，不保证逐相机或 reserved 等墨量。

|场景|追加 DEV 匹配误差|固定世界半径|主/追加 reserved 墨像素均值|主/追加 coverage3|主/追加远背景占墨量|主/追加负空间填充|
|---|---:|---:|---:|---:|---:|---:|
|lego|0.003647%|0.10298|166767.5/164228.4|100.0%/80.2%|0.1%/23.4%|10.9%/38.5%|
|chair|0.005461%|0.201965|138318.2/174788.5|100.0%/78.5%|0.1%/43.0%|13.9%/61.3%|

本轮 multi24 pipeline 相对该旧图描粗对照的定位收益真实存在：相近 DEV 墨量下，旧碎图描粗仍遗漏结构，并把墨量放到背景与负空间。来源、选核、表示和背景约束同时不同，不能把收益单因子归给更多来源。主 multi24 的大片填面仍然是失败，不能由这项对照救成 GO。Chair 在 reserved 的平均墨量差尤其明显，不能把表中结果解释为逐图公平等面积比较。详见 [追加协议](PROTOCOL_MATCHED_INK_AUDIT.json)、[完整分析与图板](post_protocol_dev_ink_diagnostic/REVIEW_ZH.md)。

## 来源覆盖与最早失败假设

construction 全 N 数据显示，24源所选核在各构建视角捕获的轮廓贡献质量中位数约 Lego 98.56% / Chair 98.43%；两源为42.99% /25.28%。按 raw 排名前0.5%的诊断为33.01% /44.53%，按 relative 排名为6.88% /6.67%。这是捕获质量及不同预算的诊断，不是等预算算法优势，也不能反写旧 accepted 空与 ALL8 REFUSED。所有核均在同一完整原 T 下测量，未以 K 截断的未知量冒充零。

原核空间覆盖、被选候选数量、有效椭球、裁剪后体素 owner 与实际顶点 owner 有显著区别；详细空间分布与多视角重复见 [相机覆盖](supplemental/CAMERA_DIRECTION_DOMAIN.png)、[两源/24源原中心](supplemental/TWO_VS_24_SELECTED_WORLD_CENTERS.png)、[贡献和 distinct views](supplemental/MASS_BUDGET_AND_DISTINCT_VIEWS.png)、[支撑缩减](supplemental/SUPPORT_DOMAIN_REDUCTION.png)。空间散点图每组至多确定性抽样12000个ID，样本列表保存，不把显示样本伪称全量。

最早被实际结果否定的假设是：把多方向强轮廓参与核的完整椭球并成一层较宽区域，可以同时改善连贯性并保持轮廓可读。max-over-views 没有惩罚同一个核在其他可见视角处于形体内部，滚动轮廓的并集因此可能铺开为表面域；foreground veto 只能拒绝背景，不能阻止形体内的大片覆盖。输出还包含世界宽度扩张和体素 closing，不能把所有问题唯一归因于选核。这里是与代码和观察一致的机制解释，未经独立因果消融。

区域表示确实避免了仅以稀疏中心短链表现形体，但这次容许支撑域过大，以表面占据替代了可读轮廓。该失败只否定本轮冻结模型和参数域，不证明原 Gaussian 不含相对轮廓支撑，也不证明任何固定宽区域都不可能成功。后续若研究局部 sheet/ridge 或对跨视角内部响应作约束，应另行冻结新规则与评价域；本轮没有结果后重调或补画答案。

## 方法、控制与适用域

输入是两个只读 seed1729/iteration30000/SH3 原 PLY。先由原生 alpha=.5 的自动轮廓（不填封闭孔）构造1.5/3px带，用完整 accepted alphaT 的全N伴随提取原ID参与与可见质量。1.5px只是诊断；实际融合使用3px带，不能称两个尺度共同融合。每源 soft=relative×sqrt(raw/(raw+.05))，跨源取最大；高阈值种子与一次短距弱支撑 hysteresis 取代旧0.5%预算。重复像素质量和 distinct views 分开保存。

以原 Gaussian 中心、完整旋转/scale 与 soft score 构造椭球占据并集；加入固定世界宽度、极值轴裁剪、一个六邻接 closing。所有 construction alpha 前景约束只在物空间执行一次，允许2px容差，画面外为unknown。输出为 edge occupancy proxy，不是 SDF、真实表面或经认证的物理棱边。原协方差轴仅作为来源支撑，不是边切向/表面法向。

候选宽度仅 .4/.8/1.2 voxel，按冻结 DEV 目标选一次，随后封印。width_world_floor字段是协方差膨胀参数，不等于最终管半径；真实轴长在region NPZ。two_source与multi24都使用同一新表示，但同时改变来源支持、2/24视角背景约束与bbox得到的网格间距；它是整个pipeline的源数量对照，不能纯因果归因给选核器。thin与widened使用旧A完整原拓扑，thin世界几何经逐bit核对。

顶点主anchor是全局最近保留raw体素的真实owner，另存最近中心诊断；不暗示全部顶点与owner体素已验证网格相邻。每个closing填补有原始邻域owner CSR、最近支撑距离和方向，背景拒绝保存首次视角及体素位置。merge图含占据交叠候选和裁剪后接口，不把所有裁剪前候选冒称最终拓扑。没有手画部件/路径、独立2D描边lift、逐相机调位或隐藏mask。

相机只投影固定mesh并做资产自z-buffer。没有得到独立校准的原不透明物体表面遮挡，因此全部图和旋转器相对原物体均为x-ray，后方杂带完整显示。没有把高斯中心期望/中位深度冒充真实表面深度。

- lego: 86 metadata相机中构建24、DEV4、reserved8；最远相机距最近构建方向 28.23°，方向z范围 [0.15672909526496925, 0.9998509366721238]。构建名单：r_7, r_33, r_26, r_69, r_60, r_59, r_11, r_24, r_13, r_17, r_77, r_46, r_44, r_9, r_67, r_82, r_68, r_34, r_31, r_20, r_70, r_21, r_80, r_49；DEV：r_89, r_58, r_74, r_64；reserved：r_1, r_14, r_16, r_10, r_81, r_50, r_96, r_66。
- chair: 86 metadata相机中构建24、DEV4、reserved8；最远相机距最近构建方向 30.32°，方向z范围 [0.14398972922392833, 0.9999637672298793]。构建名单：r_7, r_33, r_32, r_72, r_6, r_11, r_38, r_80, r_12, r_90, r_79, r_53, r_74, r_93, r_43, r_50, r_10, r_58, r_83, r_64, r_91, r_46, r_67, r_59；DEV：r_39, r_56, r_63, r_99；reserved：r_1, r_14, r_30, r_26, r_88, r_29, r_8, r_89。

相机域在物体上半球；底部和超出已有方向域的完整性未验证。33arc是历史已见、较短弧段，仅检验这一段固定投影与媒体完整性，不是全面稳定性或新视角泛化证书。

## 校准、复现和保护

独立全产物审计状态 **PASS**；详细数量和各项证据见 [ARTIFACT_AUDIT.json](results/ARTIFACT_AUDIT.json)。原模型、历史报告/negative evidence、旧branch heads均不因本轮改变。旧 automatic accepted空/ALL8 REFUSED、NO_GO_FRAGMENTED和capacity证书状态保持原样。

GPU0有外来占用，所以本轮没有调用GPU。经过四个历史construction native缓存实际校准的CPU replica：RGB MAE≤3e-7、全核mass相对L1误差≤1.06e-5、top1% mass ID Jaccard=1；feature forward和adjoint亦逐项核对。个别近深度并列核有贡献转移，尾差与未确认原因保留；不宣称bit-exact，也不称本轮执行了CUDA native。校准JSON绑定实际CPU代码SHA。

核心11项合成/契约测试通过，真实RED→GREEN与中间失败见 tdd；实际renderer/export、相机、来源与heldout、固定几何和完整视频另有独立验证。媒体helper只声称新增后实际33帧验收。执行问题见 [EXECUTION_NOTES_ZH.md](EXECUTION_NOTES_ZH.md)。所有资源守卫未降低：root4GiB/sharedGit1.5GiB/stage6GiB，生产1GiB守卫未改。

独立审计验证309个完成seal、1652条文件hash引用、11项当前核心代码hash，原输入/历史保护文件417个、历史branch heads19个未变。两段交付H264均完整独立解码33/33，帧hash匹配，faststart通过。离线viewer的内嵌几何与JavaScript语法已静态核验；环境没有浏览器，未声称实际拖动交互已经浏览器验收。

发现并保留一个导出hash口径缺陷：旧图 thin/widened 记录的geometry hash在导出前使用int64索引，NPZ/GLB导出为int32。独立核验按数值逐一验证GLB/OBJ/NPZ相等，并验证转回int64后精确匹配原记录；未覆盖主seal掩盖错误。multi24/two_source使用int32，主视频的固定geometry hash直接匹配。追加诊断统一为float32顶点/int32索引。详见执行说明和独立审计的 HASH_SCHEMA_PREEXPORT_INT64。

本轮没有新训练、新网络、安装或第三方方法代码执行；文献只读实际作者全文。没有相对Hao–Mukai、EdgeGaussians、EMAP或CurveGaussian的新颖性声明。研究先行约20分钟并行墙钟，实际读取5篇primary全文并完成历史审查/校准后冻结协议；这是早于30–40分钟研究目标预算完成，并非声称耗满该时长。

## 未实现与结论边界

这次没有完成可读而较完整的固定3D轮廓带，也没有校准原不透明物体的独立遮挡：所有结果只做资产自遮挡，相对原GS仍是x-ray。内部RGB细节层未实施；底部及相机覆盖域外未验证。两源/多源对照同时改变来源和construction背景约束，不能作选核器的单因子因果证据。追加墨量控制仅匹配DEV均值且是主协议后诊断。大面积形体内墨迹是本轮主要代价；并非所有孔洞消失，但残余开口不构成成功。本轮失败不改写历史证书，不否定原核的相对轮廓支持能力，不提出方法新颖性声明。

最终提交与远端读回记录放在 ignored `out/gaer_multiview_contour_regions_v01/DELIVERY.json`，在push之后生成，避免自引用commit循环。
