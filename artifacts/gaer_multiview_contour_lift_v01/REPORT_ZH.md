# 多视角二维轮廓升维 → 固定细三维轮廓线

**结论：PARTIAL_THIN_FIXED_CURVES；NO_GO_COMPLETE_CONTOUR。** 两场景均交付真正固定的1D控制图和细实体管线，并执行跨视角控制点融合与重复edge消除；不再是椭球支撑填面。但Lego形体大量缺线，Chair也有断口、重线和后方线；没有完成可靠、较完整且连续的固定三维轮廓恢复。

入口：[离线交付索引](INDEX.html) · [方法设计](METHOD_DESIGN_ZH.md) · [事前协议](PROTOCOL.json) · [融合冻结](FUSION_FREEZE.json) · [复现](REPRODUCE.md) · [执行边界与已知缺陷](EXECUTION_NOTES_ZH.md)。

本轮从二维有序alpha边界沿校准射线升维，不使用旧面域网格、不缩小或改名旧面、不作ellipsoid/voxel union、closing、全物体黑剪影、GTmesh/depth/scan输入、训练或安装。主GLB/OBJ是新生成的世界坐标三角管线；centerline OBJ/PLY/JSON是固定1D控制点与连接。XYZ、拓扑、radius及path IDs封印后，所有相机只投影它们。

所有媒体均为**资产自身z-buffer、相对原GS的x-ray**。原物体表面独立遮挡没有校准，因此后方线完整保留；未用深度proxy、前景mask、逐帧重选或二维修正隐藏错误。

## Lego

[推荐 fused GLB](assets/lego/fused/tubes.glb) · [实体tube OBJ](assets/lego/fused/tubes.obj) · [中心线OBJ](assets/lego/fused/centerlines.obj) · [带24单source切换的离线3D查看器](assets/lego/viewer_with_sources.html)

[8 reserved完整800px板](media/lego/reserved_eight_FULL.png) · [轻量预览](media/lego/reserved_eight_preview.jpg) · [三臂完整33相机视频](media/lego/arc/three_arms_33.mp4) · [全部33帧](media/lego/arc/ALL_33_FRAMES.jpg) · [宽尾原样与单管隔离检查](media/lego/WIDTH_TAILS.png)

实际观察：底板外周和铲斗较稳定边界被恢复成细线；rawunion能看出更多车身与支架，但重线/杂线多。fused大量删去车身、驾驶室和抬升支架的片段，只靠底板与铲斗不能称完整Lego轮廓。源proxy偏移、保守多源筛选以及局部连接不足同时造成缺线；没有独立因果消融把缺陷唯一归于某一项。

下表为8reserved逐视角均值；coverage3相对独立alpha边界，非GTmesh精度。墨量/前景包含背景墨；前景空白只在前景内计算。封闭孔与convex-hull内开放/封闭负空间分别测量。

|固定臂|轮廓覆盖3px|墨量/前景|前景空白|负空间填充|封闭孔填充|全墨迹EDT直径p95|最长缺口px|
|---|---:|---:|---:|---:|---:|---:|---:|
|single|16.5%|2.8%|97.3%|0.2%|0.2%|2.97|640.4|
|rawunion|98.8%|28.2%|73.6%|4.8%|11.1%|6.24|11.1|
|fused|70.2%|7.8%|92.9%|2.2%|1.4%|4.00|125.0|

三个臂世界radius完全相同：**0.003469048**，参考直径约2px；reserved中fused解析投影直径p95最大为2.554px。选择只用了4DEV相机的几何投影，甚至没有用DEV图像挑宽；图像评价在资产seal后才打开。有限候选是0.75/1/1.25倍construction中位世界像素尺度。

实际full-mask候选孤立profile：fused共116条，合并样本p95=3.219px；最差单视角r_89只有6条，p95=9.156px。该筛法只排除9×9窗口中的其他获胜path，**同一path非局部折返/重叠仍可能残留**，所以不是严格独立stroke保证，最差视角超过6px。WIDTH_TAILS把各臂最差4例保留，并将同一根真实管线单独raster验证：单管薄不能否认合图局部变宽。全墨迹EDT、密集墨核等指标独立保留，不以半径平均值救成GO。

全墨迹中内接半径>3px的最大连续密集核面积，rawunion/fused的视角均值为305.4/6.9像素；rawunion的大片交叉墨明显减少，但没有完全消失。这个量不等于整块连通墨迹面积。

|图结构|源点/融合点|edges|按分叉切分路径数|≤3点短路径数|近重复诊断对|
|---|---:|---:|---:|---:|---:|
|single|1637|1520|104|22|0|
|rawunion|41671|37129|3688|1004|1957|
|fused|5244|7189|5437|5124|42|

确有跨视角融合：12,813次受约束节点簇合并，消除7,041条重复edge；拒绝22,899条raw edge进入fused。近重复诊断是中点≤0.5wpp、反向等价切向dot≥.96、不共端点、12近邻内的保守计数，不是严格重复几何总数。大量短path也受分叉处切段定义影响，不等于同数量物体部件，但清楚显示连续性代价。

保留的限制有量化证据：3,130/7,189条fused edge仅有一个直接source camera，尽管两端各至少两个来源。相对各原source edge的方向翻转实例26，最终超过初始6wpp边长阈值的edge有69条；长度p95/max=4.546/8.920wpp。每条edge都映射原chain邻接，未显式新增跨链edge；但簇合并会改变连通关系，不能推出负空间绝不会跨接，也不保证方向与边长不变。

全部最终source端点重投影最大1.940447px、位移最大2.499722wpp，确实满足冻结节点界限。然而anchor窗口规则出现40次局部方向符号变化、1005个最终不足3票的accepted pair；不能把它称为严格单调轨迹或已证实物理同一性。详见[逐边审计](results/lego_EDGE_AUDIT.json)及[完整契约审计](results/lego_contract_audit.json)。

外/孔边界均提取，周长<16px的小环在24construction累计排除159个；数量是每视角计数，不是不同物体孔数量。全部被拒绝/未融合源线仍在rawunion和24份sources资产，不因reserved结果裁剪。

前四个预定reserved关键视角均保存800×800原RGB、独立2D参考、三臂tube、overlay及确定性edgezoom：

[r_1全图](media/lego/reserved/r_1/FULL.png) / [fused800](media/lego/reserved/r_1/fused.png) / [edgezoom](media/lego/reserved/r_1/edgezoom.png) · [r_14全图](media/lego/reserved/r_14/FULL.png) / [fused800](media/lego/reserved/r_14/fused.png) / [edgezoom](media/lego/reserved/r_14/edgezoom.png) · [r_16全图](media/lego/reserved/r_16/FULL.png) / [fused800](media/lego/reserved/r_16/fused.png) / [edgezoom](media/lego/reserved/r_16/edgezoom.png) · [r_10全图](media/lego/reserved/r_10/FULL.png) / [fused800](media/lego/reserved/r_10/fused.png) / [edgezoom](media/lego/reserved/r_10/edgezoom.png)

construction：r_7, r_33, r_26, r_69, r_60, r_59, r_11, r_24, r_13, r_17, r_77, r_46, r_44, r_9, r_67, r_82, r_68, r_34, r_31, r_20, r_70, r_21, r_80, r_49。DEV：r_89, r_58, r_74, r_64。reserved：r_1, r_14, r_16, r_10, r_81, r_50, r_96, r_66。86metadata相机到最近construction方向的最大夹角28.23°。

## Chair

[推荐 fused GLB](assets/chair/fused/tubes.glb) · [实体tube OBJ](assets/chair/fused/tubes.obj) · [中心线OBJ](assets/chair/fused/centerlines.obj) · [带24单source切换的离线3D查看器](assets/chair/viewer_with_sources.html)

[8 reserved完整800px板](media/chair/reserved_eight_FULL.png) · [轻量预览](media/chair/reserved_eight_preview.jpg) · [三臂完整33相机视频](media/chair/arc/three_arms_33.mp4) · [全部33帧](media/chair/arc/ALL_33_FRAMES.jpg) · [宽尾原样与单管隔离检查](media/chair/WIDTH_TAILS.png)

实际观察：椅背、座面周界、部分扶手与腿部可读，较rawunion清楚；但断口、双线和后方座椅结构穿出仍很明显。从后方看前侧曲线仍显示，这是未处理原物体遮挡的真实xray，不以此冒充物理可见轮廓。

下表为8reserved逐视角均值；coverage3相对独立alpha边界，非GTmesh精度。墨量/前景包含背景墨；前景空白只在前景内计算。封闭孔与convex-hull内开放/封闭负空间分别测量。

|固定臂|轮廓覆盖3px|墨量/前景|前景空白|负空间填充|封闭孔填充|全墨迹EDT直径p95|最长缺口px|
|---|---:|---:|---:|---:|---:|---:|---:|
|single|32.6%|2.1%|98.0%|0.4%|20.3%|2.83|582.5|
|rawunion|99.8%|29.1%|72.5%|6.2%|43.0%|7.38|2.8|
|fused|83.5%|8.8%|91.8%|2.5%|6.0%|4.18|48.0|

三个臂世界radius完全相同：**0.003542960**，参考直径约2px；reserved中fused解析投影直径p95最大为2.706px。选择只用了4DEV相机的几何投影，甚至没有用DEV图像挑宽；图像评价在资产seal后才打开。有限候选是0.75/1/1.25倍construction中位世界像素尺度。

实际full-mask候选孤立profile：fused共109条，合并样本p95=3.125px；最差单视角r_30只有9条，p95=7.375px。该筛法只排除9×9窗口中的其他获胜path，**同一path非局部折返/重叠仍可能残留**，所以不是严格独立stroke保证，最差视角超过6px。WIDTH_TAILS把各臂最差4例保留，并将同一根真实管线单独raster验证：单管薄不能否认合图局部变宽。全墨迹EDT、密集墨核等指标独立保留，不以半径平均值救成GO。

全墨迹中内接半径>3px的最大连续密集核面积，rawunion/fused的视角均值为498.4/7.2像素；rawunion的大片交叉墨明显减少，但没有完全消失。这个量不等于整块连通墨迹面积。

|图结构|源点/融合点|edges|按分叉切分路径数|≤3点短路径数|近重复诊断对|
|---|---:|---:|---:|---:|---:|
|single|912|792|89|23|0|
|rawunion|31338|28285|2237|681|961|
|fused|4067|5249|3860|3598|32|

确有跨视角融合：9,247次受约束节点簇合并，消除4,785条重复edge；拒绝18,251条raw edge进入fused。近重复诊断是中点≤0.5wpp、反向等价切向dot≥.96、不共端点、12近邻内的保守计数，不是严格重复几何总数。大量短path也受分叉处切段定义影响，不等于同数量物体部件，但清楚显示连续性代价。

保留的限制有量化证据：2,360/5,249条fused edge仅有一个直接source camera，尽管两端各至少两个来源。相对各原source edge的方向翻转实例13，最终超过初始6wpp边长阈值的edge有60条；长度p95/max=4.805/8.342wpp。每条edge都映射原chain邻接，未显式新增跨链edge；但簇合并会改变连通关系，不能推出负空间绝不会跨接，也不保证方向与边长不变。

全部最终source端点重投影最大1.973085px、位移最大2.499773wpp，确实满足冻结节点界限。然而anchor窗口规则出现51次局部方向符号变化、828个最终不足3票的accepted pair；不能把它称为严格单调轨迹或已证实物理同一性。详见[逐边审计](results/chair_EDGE_AUDIT.json)及[完整契约审计](results/chair_contract_audit.json)。

外/孔边界均提取，周长<16px的小环在24construction累计排除44个；数量是每视角计数，不是不同物体孔数量。全部被拒绝/未融合源线仍在rawunion和24份sources资产，不因reserved结果裁剪。

前四个预定reserved关键视角均保存800×800原RGB、独立2D参考、三臂tube、overlay及确定性edgezoom：

[r_1全图](media/chair/reserved/r_1/FULL.png) / [fused800](media/chair/reserved/r_1/fused.png) / [edgezoom](media/chair/reserved/r_1/edgezoom.png) · [r_14全图](media/chair/reserved/r_14/FULL.png) / [fused800](media/chair/reserved/r_14/fused.png) / [edgezoom](media/chair/reserved/r_14/edgezoom.png) · [r_30全图](media/chair/reserved/r_30/FULL.png) / [fused800](media/chair/reserved/r_30/fused.png) / [edgezoom](media/chair/reserved/r_30/edgezoom.png) · [r_26全图](media/chair/reserved/r_26/FULL.png) / [fused800](media/chair/reserved/r_26/fused.png) / [edgezoom](media/chair/reserved/r_26/edgezoom.png)

construction：r_7, r_33, r_32, r_72, r_6, r_11, r_38, r_80, r_12, r_90, r_79, r_53, r_74, r_93, r_43, r_50, r_10, r_58, r_83, r_64, r_91, r_46, r_67, r_59。DEV：r_39, r_56, r_63, r_99。reserved：r_1, r_14, r_30, r_26, r_88, r_29, r_8, r_89。86metadata相机到最近construction方向的最大夹角30.32°。

## 方法和证据应如何解释

单源为本轮重新生成的r_33，与rawunion/fused共用all-accepted条件中位中心z proxy、2px有序采样、孔边界、跳变切段、radius和实体renderer。旧r_33用top32 αT×C_style中心均值，不能把本轮结果冒称旧实现纯增source。single→rawunion增加source；rawunion→fused同时改变同一性筛选、控制点融合、重复边合并和pruning，收益不能唯一归给去重。

每像素完整accepted核ID/αT由新stage稀疏CPU接口得到；条件median沿相机射线升维。q10/q90是支持核中心深度分布，**不是测量surface depth或校准误差区间**。没有统一depth平面，也没有将不同相机的pseudo-depth当物理真值。三角化只用于通过近距、支撑、双向epipolar、切向和夹角检查的候选；共享核与低重投影误差仍不足以证明rolling silhouette的物理同一性。

本轮source回投影数值近零是构造自检；最终多source≤2px是真实几何约束，但不能证明深度正确或完整轮廓。没有实现内部RGB细节层，没有mesh GT评测；不作方法新颖性声明。旧NO_GO_CONTOUR_OVERFILL、旧单源/稀疏图/容量证书均保持原状态。

所有86metadata相机都来自原GS训练/历史研究曝光域。24construction/4DEV/8reserved及33arc完整继承上轮，按真实file_path核对，不按r数字index（r_33实际index28）。reserved仅本轮构线holdout，**不是fresh blind、GS-unseen**。33arc是历史较短弧段，完整视频不代表全方向泛化；下半球和相机域外完整性未验证。

## 工程核验和可复现边界

原模型每scene按冻结SHA核验；48construction缓存逐相机seal/result/input/hash绑定，稀疏accepted和逐采样像素对sealed alpha核对。CPU full-forward CPP与历史已校准源码逐字相同；历史四份native-cache对照仅近似，不宣称CUDA bit-exact，也没有本轮执行CUDA。详见[CPU校准链](CPU_CALIBRATION_LINEAGE.json)。

8项初始tracer真实RED→GREEN发生在批处理前；新增7项实际production路径扩展在asset后、评价前通过；最终10项扩展加入rolling distinct-support拒绝、近平行拒绝及反向轨迹，并在评价后通过。日志和时序完整保留。它们不等于所有更强几何目标已通过；严格monotonic/边方向连续/完整性没有GREEN认证。

全部54个导出图（每scene3主臂+24source）的GLB/实体OBJ/控制点PLY/JSON/路径边逐项读回；真实管径检查通过。独立审计检查每个来源端点界限、edge provenance、所有source→fusion→asset依赖与预冻结代码hash。原导出单source edge IDs与主raw edge IDs命名空间不同，由各scene [PROVENANCE_NAMESPACES](assets/lego/PROVENANCE_NAMESPACES.json) sidecar明确映射，未覆盖旧sealed字节。

两段H264 yuv420p +faststart视频均完整decode33/33，全部帧和camera/geometry hash保存；前后asset seal相同。离线WebGL2查看器内嵌27份实际几何，静态数组及node语法核验通过；环境未进行浏览器交互验收，不能声称实际拖动测试通过。

所有生产顺序执行、CPU-only、2线程，cache/tmp/private binary仅新stage；没有等待或干扰GPU、其他进程/工作树。资源及原模型/1130保护文件/旧branch核验见[PROTECTION_AUDIT](PROTECTION_AUDIT.json)。最终提交、显式SSH push、remote SHA读回及clean状态在ignored `out/gaer_multiview_contour_lift_v01/DELIVERY.json`，不把自身commit SHA写回tracked报告形成循环。

此次最早被结果否定的主张不是“多视角升维完全无用”，而是当前严格有限proxy与局部匹配足以产出完整且连续的固定轮廓。它确实产生了薄、可编辑、可追溯的多源融合候选，也减少了重复墨迹；但覆盖、连续性、局部顺序和物理遮挡仍不足。保持PARTIAL/NO_GO，不用线宽救失败。
