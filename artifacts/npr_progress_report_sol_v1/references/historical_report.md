# 冻结 3DGS 的特征线研究：从物空间资产到双空间高密度线画

**完整图文与视频报告｜2026-10-02｜研究对象：Lego、Chair、Drums、Ficus 的冻结 vanilla 3DGS；另列独立 RGB-D 输入实验。**

![全项目图像索引；仅缩略导航，打开下方原图阅读](images/overview.jpg)

> **一句话结论。** 固定、可编辑的物空间线资产尚未达到完整、干净、跨视角可信的目标；最新四模型**高密度混合视频**把既有固定三维曲线与逐视角二维 RGB／深度／透明度边缘叠在同相机 GS 画面上，明显增加可见线和局部可读性，但主要新增线来自二维层，伴随纹理噪声、错位与未验证的时间稳定性。静帧墨像素数不是质量得分。

## 阅读导航与证据等级

- 本包包含 **21 张历史原实验图、原生 RaDe 状态独立复现图、2 张 F 视角接触图、4 张新方法分层图、四模型完整相机弧的首／中／末原帧及四张派生帧条**；点击图可查看原像素。`SOURCE_MAP.json` 给出每张图／视频的原路径、哈希和大小。`images/overview.jpg` 与 `*_motion_strip.jpg` 仅是对真实图的缩略／拼接。
- [Lego](videos/lego_arc0_overlay.mp4) · [Chair](videos/chair_arc0_overlay.mp4) · [Drums](videos/drums_arc0_overlay.mp4) · [Ficus](videos/ficus_arc0_overlay.mp4)：四个叠线视频；相应 `*_comparison.mp4` 是未修改 GS RGB 与叠线的并排片。每段 33 帧／12 fps，逐帧来自真实相机缓冲，不是静帧平移动画。它们属于**混合视频合同**，不是固定三维线资产的成功展示。
- 下文的 `GO`、`NO-GO`、`STOP`、`INVALID` 均针对当时冻结的场景、输入、预算、视角与门槛。没有独立人类审美 GO，不把某次失败推广成整类方法不可能。

## 1. 研究目标、输入边界与两种输出合同

最初目标是在冻结 vanilla 3DGS 上、无需 mesh 进入算法，自动构造能编辑、能跨视角复用的持久三维线条。视觉标准优先：看清形状、该画的线足够完整、遮挡正确、整段相机运动无刺眼跳变。Mesh 若存在只作评估诊断，不参与候选生成、拟合或渲染。冻结原场景输入、额外 Kinect 实测深度、人工线条标注、重训 RaDe-GS 是不同合同，不能混算成原题成功。

**固定资产合同**：控制点、身份、拓扑固定于物空间，最终墨迹由三维资产投影与可见性决定。**混合画面合同**：允许固定三维结构线与相机相关的二维轮廓／细节同帧出现，必须各自可导出，最终合成不能冒称“全部固定三维”。目前交付的四模型视频属于后者。

## 2. 历史路线：为什么固定三维线仍不够好

### 2.1 早期物空间 linelet 与图像证据

早期从 Gaussian／图像边缘证据生成物空间 linelet，曾在纹理场景展示优于逐帧 Canny 的部分时间稳定性，但线画会碎、漏、错；干净实体上的 Canny 本身也可能稳定，不能将优势外推到所有物体。TEED／DexiNed 一类图像边缘证据能帮助局部排序，却不能自行解决三维线的身份、连续性或正确遮挡。

![历史 linelet 与边缘对照；图内旧宣传文字以本报告收窄结论为准](images/01_linelet_baseline.png)
![TEED 候选原图；图像证据不是三维资产](images/02_teed_seed.png)
![重训方向的候选缺失上限诊断；含 oracle 假设，不是实际可用的方法效果](images/03_retrain_diagnostic.png)

### 2.2 底层表示诊断：Gaussian 不是自带曲面的点云

最小 covariance 轴只是未定向候选轴，Gaussian 混合密度也只是后验占用代理；都不自动等于真实曲面法线或 SDF。四场景的多层、碎片与局部不稳定，使“先算局部几何，再连线”的底层前提可疑。中心 KDE／Hessian ridge 的宽线响应有**有限二维诊断 GO**，并未得到稳定、可编辑三维线。

![四场景后验场与候选轴原图](images/04_posterior_fields.png)
![混合密度切片；非真实曲面拓扑](images/05_gaussian_density.png)
![四场景 ridge 通道与带状响应](images/06_ridge_feasibility.png)
![不同墨量阈值：补充结构也会增加杂线](images/07_ridge_thresholds.png)

### 2.3 扩候选、组路径与补桥不能修复错误底层

图像／raster-state 代理的候选扩充、WV-PC 全局路径组织、固定三维端点桥接以及 VRSS 子集选择都做过受控视觉比较；个别局部缺口能补上，但完整结构和最差视角没有达到各自冻结门槛。旧圆盘 raster-state 代理与郝—向井作者的原生 RaDe 输入／合成器不等价，**其失败不能判作者方法失败**。固定 top-8 contributor 曾因覆盖不够为工程 `INVALID`；质量完整的自适应 contributor G0 通过后，分层检测 G1 四场景仍 `0/4 NO-GO`。

![旧圆盘代理候选六臂；不是作者官方方法](images/08_raster_state.png)
![物空间路径组织等墨量对照](images/09_stroke_organization.png)
![补桥成功与失败缺口同时可见](images/10_gap_recovery.png)
![Chair 子集选择的固定视角](images/11_vrss.png)
![Top-8 工程覆盖失败；不是科学否证](images/12_top8_invalid.png)
![自适应质量完整贡献者分层候选](images/13_adaptive_layered.png)

### 2.4 直接对应与固定三维曲线的边界

多视图二维线身份对应在 Lego／Chair 保留的可靠轨迹太少，判 `STOP_CORRESPONDENCE`。绕过局部对应、直接全局拟合固定三维 Bézier 曲线的 D／I／L 三臂，在四场景均 `NO-GO`；I 有局部改善，仍不够完整，并有不支持的错线。下面四幅真实盲标列序已解码为 **RGB｜D（固定三维深度）｜depth2d（逐视角二维）｜I（固定三维全局图像证据）｜L（固定三维局部对照）**。depth2d 的单帧优势不能拿来证明固定资产成功。最新混合实验里的橙线正是复用这个**失败过的 I 分支**，没有新拟合三维资产。

![跨视角身份与拒绝图](images/14_correspondence.png)
![Lego：冻结曲线多臂与二维参考](images/15_direct_lego.png)
![Chair：冻结曲线多臂与二维参考](images/16_direct_chair.png)
![Drums：冻结曲线多臂与二维参考](images/17_direct_drums.png)
![Ficus：冻结曲线多臂与二维参考](images/18_direct_ficus.png)

## 3. 两个独立分叉：二维视频与额外实测深度

**二维视频路线：**既有 depth2d 逐视角基线比较时间运输的首个候选。Lego 完整轨迹、等墨量控制下首个候选 `NO-GO`；不能因此说所有二维视频路线已失败。图 19 是原始固定分位帧；[完整对比视频](videos/comparison_forward.mp4) 可单独播放。

![时序二维线首轮：GS／基线／候选的真实分位帧](images/19_temporal_video.png)

**额外传感器路线：**TUM `fr1/desk` 的 Kinect 深度和位姿提供了 vanilla GS 之外的几何输入，产出固定三维 ID 并完成工程视频检验；科学上仍 `NO-GO`，结构短碎、遮挡错显。这个结果不能计入原四场景 vanilla-GS-only 合同。

![独立 RGB-D 输入的固定资产中位帧](images/20_rgbd_asset.png)
![显隐局部观察图；不等于已验证完整显—隐—显](images/21_rgbd_occlusion.png)

## 4. 他人方法、我们的独立复现与最新混合图：严格分开

**郝唯任—向井智彦方法**在 RaDe-GS 类栅格器的内部统计每像素高斯贡献、top-k 原始身份、深度、法线、颜色和透明度，通过邻域状态差异与可靠性门控输出连续特征线字段；海报明确不是对最终 RGB 做后处理，也没有在论文当前结果中交付持久三维笔画。[1] RaDe-GS 的深度／法线栅格化属于张宝文等作者，非本项目原创。[2]

**我们的独立 F1**：隔离编译 RaDe 原生 CUDA，在同一次前向遍历中导出 top-4 ID、`αT`、深度与法线并计算海报 Eq.1–5，生成真实 Lego 字段图与[8 帧短片](videos/native_f1_short.mp4)。输入是冻结 vanilla 3DGS PLY、仅 SH0，缺 RaDe 训练所得 `filter_3D` 和作者最终风格合成；图中 P99 拉伸是**显示用**而非方程改进。它不是官方重现画面，也不是固定三维线。

![我们的 RaDe 同源栅格状态 F1 字段图；非作者官方合成](images/native_f1_panel.png)

**新混合 v1**并没有把上述 F1 的 top-k 字段接到画线器里。它延用旧 I 分支固定三维线，加入**GS RGB 的双尺度 Canny、旧逐视角深度边缘及 alpha 轮廓**，因此方法谱系主要来自我们之前的 pipeline；郝—向井方法只启发“物空间／视角相关线索应该区别对待”的研究方向，不能说当前图片实现了作者公式。先前 [3Doodle](https://changwoonchoi.github.io/3Doodle/) 已把视角无关三维曲线与视角相关轮廓组合，故“两层合成”本身亦不新。[3]

## 5. 最新高密度混合 pipeline：实际实现了什么

**工程准备（S0/S1）** 曾创建 Lego／Chair 的八视角 TRAIN-F 图、固定点几何诊断工具和空人工模板；未获得人工线意图，未作科学 GO。用户要求减少人工后，最新混合流程**不以人工圈线为前置条件**；这些图仅留作数据来源／视角审计，不当作标注。

![Lego TRAIN-F 原图总览；非人工线条标注](images/lego_F_contact.png)
![Chair TRAIN-F 原图总览；非人工线条标注](images/chair_F_contact.png)

对于每个相机：读取同视角的完整 GS RGB、alpha、旧深度边及固定 I 曲线的可见投影墨迹。二维层取两个 RGB Canny 尺度（σ 0.65、阈值 18/48；σ 1.4、阈值 25/65）、旧二维深度边缘与 alpha 的 25/65 外轮廓之并集；`alpha≥0.08` 的稍扩张前景限定背景。三维投影墨迹以 0.30 二值化；二维线仅在三维线相邻的 3×3 区域让位，其余保留。**没有墨量上限或大范围纹理剔除**，对应“尽量多画线”的取向。

下面四幅依次为 **GS RGB｜旧固定三维 I 墨迹｜逐视角二维墨迹｜高密度合成线画**；它们是 TRAIN-F 静帧，不是留出视角科学测试。可见丰富度主要来自第三栏，不能把第四栏的收益记作三维资产改善。

![Lego F1 四层真实对照](images/lego_F1_layers.jpg)
![Lego F41 四层真实对照](images/lego_F41_layers.jpg)
![Chair F1 四层真实对照](images/chair_F1_layers.jpg)
![Chair F41 四层真实对照](images/chair_F41_layers.jpg)

**模型叠线视频**：逐帧读取历史相机弧归档的**同相机** GS RGB／alpha／深度边与同一固定 I 曲线的可见投影，再逐帧计算二维边。橙色表示固定三维投影，黑色表示逐视角二维墨迹；无手调平移、缩放或静帧动画。下面四张三帧条来自每段视频真实首／中／末帧，横向拼接仅便于肉眼检查。每段完整视频均为 33 帧；原图与叠线并排视频见文末。

![Lego 相机弧：首／中／末同相机叠线](images/lego_motion_strip.jpg)
![Chair 相机弧：首／中／末同相机叠线](images/chair_motion_strip.jpg)
![Drums 相机弧：首／中／末同相机叠线](images/drums_motion_strip.jpg)
![Ficus 相机弧：首／中／末同相机叠线](images/ficus_motion_strip.jpg)

**目测而非独立评审：**Lego 铲斗、车体、底板更易读；Chair 的内部线增加，但存在橙色固定曲线偏离轮廓和孤立背景点；Drums 鼓面／支架清楚，局部有不规则杂线；Ficus 叶冠线多却拥挤，橙线局部错位与背景散点明显。未对完整视频做独立盲评或时间跳变门槛判决；完整解码只证明工程产物可播放。

## 6. 汇总判断与下一步可证伪问题

- **已确认的产物：**旧路线的真实对照图、原生 RaDe 状态独立字段示例、高密度混合四模型静帧及四段模型叠线视频。混合视频所有帧独立生成，同相机叠加；四模型视频各 33 帧、12 fps，解码完整且各帧不同，六项相关新测试通过。
- **未达到的目标：**从冻结 GS 自动得到足够完整、准确、可复用的固定三维线；也未证明混合视频的时序稳定性、与郝—向井官方画面的公平同输入比较、跨视角预测自动分流或真正新颖性。
- **视觉方向：**不要靠继续加曲线数修复错误身份。较有价值的下一个对照是把“稳定可预测的物空间线”与“随视角滚动的轮廓／纹理”自动分流，对比当前简单并集、逐视角二维、旧三维单层及等墨量控制；如引入郝—向井字段，先保证同源栅格状态，再独立标明我们的融合算法与作者原方法。[1][3]

## 7. 视频与复查入口

以下播放器嵌于 HTML 版；Markdown 中可点击紧邻的视频文件链接。视频不会被静帧代替。

<video controls preload="metadata" width="800" src="videos/lego_arc0_overlay.mp4"></video>
<video controls preload="metadata" width="800" src="videos/chair_arc0_overlay.mp4"></video>
<video controls preload="metadata" width="800" src="videos/drums_arc0_overlay.mp4"></video>
<video controls preload="metadata" width="800" src="videos/ficus_arc0_overlay.mp4"></video>

- 混合叠线：[Lego](videos/lego_arc0_overlay.mp4) · [Chair](videos/chair_arc0_overlay.mp4) · [Drums](videos/drums_arc0_overlay.mp4) · [Ficus](videos/ficus_arc0_overlay.mp4)。
- 原 GS／叠线并排：[Lego](videos/lego_arc0_comparison.mp4) · [Chair](videos/chair_arc0_comparison.mp4) · [Drums](videos/drums_arc0_comparison.mp4) · [Ficus](videos/ficus_arc0_comparison.mp4)。
- 郝—向井公式的**我们独立 F1**短片：[native_f1_short.mp4](videos/native_f1_short.mp4)。独立二维时序基线对照：[comparison_forward.mp4](videos/comparison_forward.mp4)。
- 本包的 `SOURCE_MAP.json` 逐一列出原路径和 SHA-256；`images/` 内保留原始可放大图，`videos/` 保留可播放视频。旧 21 图的更细实验说明附于 `HISTORICAL_METHODS.md`。代码和最新四模型结果位于 GitHub [`hybrid-dense-ink-v1`](https://github.com/mengguo311/FeatureLineRendering/tree/hybrid-dense-ink-v1)，提交 `e9b7e59ab109097aca46c374a3544c0eea3b93ab`。项目工作不等于论文作者的官方图或官方实现。

## Sources

[1] https://mukai-lab.org/content/SA2026PosterHao.pdf — Hao and Mukai 2026 poster
[2] https://arxiv.org/abs/2406.01467 — RaDe-GS
[3] https://changwoonchoi.github.io/3Doodle — 3Doodle
