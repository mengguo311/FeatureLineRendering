# GAER 原始高斯外轮廓 v0.1

**结论：原生外轮廓可辨认且基本连续；“完整、干净、窄线”仍为 PARTIAL，冻结的 CLEAN GO 拒绝。** 工程已完成两场景各四固定视角、A/B/C/P/S 全部实际图像、各33个实际弧线帧与整段解码。没有画2D最终轮廓，没有新增高斯或曲线。

[Lego 四视角完整对照](media/lego/fixed_fourview_all_arms_800.png) · [Chair 四视角完整对照](media/chair/fixed_fourview_all_arms_800.png)；每个面板800×800，行序 r_1/r_14/r_7/r_33。

[Lego 选定原生墨线及RGB展示](media/lego/fixed_fourview_chosen_800.png) · [Chair 选定原生墨线及RGB展示](media/chair/fixed_fourview_chosen_800.png)。目标列仅为诊断，不是提出的渲染结果。

## 方法与谱系

只读使用原始30k全SH3 PLY：Lego310475核、Chair256690核；原始行号就是载体ID。固定相机按 metadata 文件名匹配，索引实际为1/12/5/28。开发仅r_7/r_33；默认封印后才运行r_1/r_14及原 image-space DATA_FREEZE 中33帧相机。全部为既有GS/研究见过的探索视角，非新盲测。

原完整alpha>.5生成证据；8连通组件保留面积≥32且alpha质量≥24者。封闭背景孔洞全部填入“外轮廓证据对象”，但原alpha与最终图不填洞：本轮明确不描这些内轮廓，包括可能真实的Chair封闭开口。外界连通间隙保留，小碎片只从证据排除，核仍参与原生渲染。保存raw alpha、所有掩码、SDF法向/切向。目标为向内1px、2px名义宽度、1px AA过渡的窄带，L=min(alpha,.9*beta)。

A=旧0.5%诊断ratio ID二值黑墨；B=同一批ID联合连续强度；C=全N共同分配（实际beta参与为正的ID可激活）；P=同数量alphaT参与质量二值基线。A/B/C/P均保留所有原核及opacity/T，白背景c=1-s，0≤s≤1。P的支持量不等于干净线。C放宽了ID域，不能声称相同预算下胜过B。旧selected-only SH3图单独展示，因为其删除核并改变T。

复用capacity真实原生颜色前向/伴随，经无旧写入shim加载既有二进制，无安装或新kernel构建。自动目标可从当前相机模型得到，不需要手标、原RGB答案、内部细节投票或学习预测器。对非负真实权重，用D=AT(q*alpha)构造Jensen对角上界，单调有界FISTA在线拟合；每帧零初始化，最多300步。独立FP64接受权重dual及原生白背景公式检查通过，不能据拟合容量宣称选择器已验证。

固定原足迹有A≤alpha，因此低覆盖白背景边缘不能仅靠颜色变得不透明。没有后渲染膨胀、DT拉线、对比增益、掩码或清理。输出是**视角依赖的原始Gaussian风格化**，不是固定持久3D曲线、静态edge Gaussian类别或已证时间稳定性；未连接中心。

## 固定结果与未通过项

|场景/视角|冻结方法|轮廓覆盖|距离p95 px|FWHM p95 px|内部>.2像素|全部干净门槛|
|---|---|---:|---:|---:|---:|---|
|lego/r_1|S|1.0000|2.66|3.07|8|REFUSED|
|lego/r_14|S|1.0000|2.66|2.71|83|REFUSED|
|lego/r_7|S|1.0000|2.66|2.57|1|REFUSED|
|lego/r_33|S|1.0000|2.66|2.63|19|REFUSED|
|chair/r_1|C|1.0000|3.11|4.02|21|REFUSED|
|chair/r_14|C|0.9968|4.50|5.05|267|REFUSED|
|chair/r_7|C|0.9995|3.50|3.88|53|REFUSED|
|chair/r_33|C|1.0000|3.62|3.89|111|REFUSED|

门槛在科学运行前冻结：覆盖≥.95、最长缺口≤12px、墨量距离p95≤2.5px、profile FWHM p95≤4px、内部墨量占比≤.05且>.2内部像素≤32、峰值中位≥.35。统计完整raw native墨迹，并非只算阈值覆盖；孔洞/小组件政策限制目标语义。全部八张选定固定图距离门槛仍失败，Chair r_14的宽尾/脚边晕开与内部杂墨尤其明显。Lego虽接近细线，r_14仍有杂墨。没有放宽门槛。

A/B/C/P逐图全部指标、强度/support/可见质量及泄漏在[固定汇总](results/FIXED_SUMMARY.json)与results/*r_*.json。A固定1553/1284 ID；C实际可参与域Lego28637–34937、Chair15604–21411，活动域Lego14920–19073、Chair8702–12020（s>1e-5），不是紧凑0.5%资产。

唯一条件S保留中心与峰值opacity，只改当前视角轮廓附近原ID临时screen covariance，法向std最多缩2倍；双角normal/tangent聚合、相对原协方差广义特征值裁剪[.25,1]，重算footprint/radii/tiles/遍历/T并同预算重拟合。它确实改变遮挡，不套用固定T上界。开发Lego两图综合违例下降约57.7%，故冻结S；Chair违例增加，冻结C。alpha损伤门槛通过但S没有消除距离问题，不能声称shape充分或必要。全部每ID中心距离、协方差裁剪和alpha损伤保留；[实际足迹边框裁剪审计](tests/SHAPE_FOOTPRINT_CLIPPING.json)另保存全部41个S单元的原生radius/tile重算与保守AABB裁剪数；未做第二shape arm或救援轨迹。

## 实际33帧与时间限制

lego：S，33/33帧；覆盖1.0000–1.0000，全干净0/33。原ID活动Jaccard中位0.745，归一化强度L1变化中位0.146；纯拟合中位0.387s，记录的含证据/渲染/导出耗时中位2.431s。逐帧预算/收敛保留，没有warm start或时间正则。

[原生墨线视频](media/lego/arc/native_ink_33.mp4) · [RGB叠加展示视频](media/lego/arc/RGB_overlay_PRESENTATION_33.mp4) · [全部33帧墨线条带](media/lego/arc/all_frames_native_strip.png) · [实际逐帧指标](media/lego/arc/actual_frame_metrics.png)。

chair：C，33/33帧；覆盖0.9990–1.0000，全干净0/33。原ID活动Jaccard中位0.775，归一化强度L1变化中位0.135；纯拟合中位0.299s，记录的含证据/渲染/导出耗时中位1.814s。逐帧预算/收敛保留，没有warm start或时间正则。

[原生墨线视频](media/chair/arc/native_ink_33.mp4) · [RGB叠加展示视频](media/chair/arc/RGB_overlay_PRESENTATION_33.mp4) · [全部33帧墨线条带](media/chair/arc/all_frames_native_strip.png) · [实际逐帧指标](media/chair/arc/actual_frame_metrics.png)。

全部视频H264/yuv420p/+faststart，独立进程完整解码确认为33帧；33个相机与PNG各自不同，条带包含全部原始帧。弧线短且既有视角见过；churn通过不代表跨帧对应、无闪烁或长期稳定。66帧均有至少一项干净门槛失败，坏帧未省略。

## 审计与交付

共90个实际连续拟合全部在40步结束且通过本阶段FP64数值gap门槛。独立进程重放40个固定arm和66个arc原生图，核对原SH3 RGB、原ID/范围、A/B同ID、全部媒体帧与strip；717个旧/输入保护文件哈希不变。原报告中四个perview未认证、ALL8自动可靠性拒绝仍原样，不能被本轮覆盖。

八组真实RED→GREEN日志及独立回归保留在tdd。首次协议格式比较与质量配置接线失败及部分图像保存在failures，不清理证据。[独立native/media审计](tests/INDEPENDENT_NATIVE_MEDIA_AUDIT.json) · [旧树保护哈希](tests/PROTECTED_AFTER.json) · [工程失败](tests/ENGINEERING_FAILURES.json)。

portable NPZ在downloads/{scene}/{view}/[A/B/C/P/S]_style.npz及downloads/{scene}/arc/{frame}/style.npz，包含原始ID、强度、camera身份与源hash；S含临时covariance原ID行。完整浮点原SH3固定图也导出。arc raw alpha/掩码/normal/target/原RGB/native浮点在ignored out/gaer_object_contours_v01/arc_raw，有逐帧原子封印，可从NPZ/原模型原生重放。所有完整PNG均发布，原生墨线和RGB展示严格分名。

资源仅GPU0同PID所有权，CPU2/MAX_JOBS2；阶段实际体积约1.1GiB，未接近8GiB。未安装、训练、扩数据、改模型/生产guard/旧树/其他分支，也未读凭证。实际Codex CLI gpt-6.1-sol/xhigh已有启动字段证据，配置语义参考[OpenAI官方文档](https://learn.chatgpt.com/docs/config-file/config-reference)。

不宣称相对Hao–Mukai或既有Gaussian NPR的创新。科学仍是部分视觉可行性；工程交付完成。[复现命令](REPRODUCE.md) · [全状态](FINAL.json) · 最终提交与SSH远端验证见[交付记录](../../out/gaer_object_contours_v01/GIT_DELIVERY.json)。
