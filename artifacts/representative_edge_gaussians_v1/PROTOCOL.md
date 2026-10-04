# S0 冻结协议：原始 Gaussian ID 的代表性支持组

本轮使用启动日志与 `.codex/config.toml` 明确钉住的 **gpt-6.1-sol / xhigh**。基点为 `20f85a15c3d3c382b94b83e8b6aa501c72009e70`。历史报告、结果及其模型身份不重命名。科学对象是固定原始 PLY 行号组成的代表性支持组；不恢复真实三维边缘、不连中心、不拟合曲线、不重训，不读取 mesh/TEST，不人工标线。只读两个 frozen vanilla30k/seed1729 模型。所有新输出限于本阶段目录；旧代码、数据、模型及 native build 全部只读。

本协议和 `code/config.json`、`INPUT_HASH_MANIFEST.json`、CPU RED→GREEN 日志先提交、SSH 推送并读回，再开始生产像素读取。配置数值及算法定义优先于文字简写。代码工程修复另记变更和测试，不以 C/arc 结果更改预算、阈值、λ 或证据配方。

## 相机与评价范围

Mic 主场景后 Materials，完全相同配方；每场景 F=[1,14,27,41,53,67,79,93]，C=[7,21,33,47,59,73,86,99]，arc0_000..032 使用来源相机。manifest 保存原封存相机内容、canonical hash、camera.json SHA256及源缓存摘要。S0只读取 F 数据的散列/结构；C/arc camera 元数据允许读取，原始像素散列沿用原冻结清单，首次像素读时核验。两个场景全部 F ID/归一化/选择与 coverage-match 前缀封存后才读取 C/arc。它们是归因构造留出视图，但 Gaussian 训练见过这些 TRAIN 相机；旧媒体和 demo C 已被知晓，绝不称盲测或 GS 未见测试。

## S1：更改证据合同

独立 RGB 结构张量梯度方向、masked log median-depth 梯度方向、alpha 梯度方向分别 NMS；不使用 ID 切换生成边缘。沿用已审计梯度和内部 alpha/erosion 定义，sigma 从旧1.0改为0.8/1.6/3.2 px；深度沿用 masked smoothing 后再 derivative smoothing 的双层处理，须明确报告有效尺度差异。各尺度各类别正值ROI P99只从 Mic 八F拟合，Materials/C/arc继承。clip[0,1] 后 NMS >=.1，任意两个尺度在2px欧氏距离内支持的 NMS 像素构成 MAJOR；未持久的原0.8 fine像素全部保存 DETAIL，不因长度删除。

每视图每类别8连通ridge组件按绝对32x32空间格分块；母组件>=3px的每个片段保留，1/2px组件仍在证据与诊断中但不进入chunk目标。每chunk内部按证据强度除该chunk总强度，总权重相同；每F/class总权重1/24，空类保留零权重不转赠。这里均衡的是分块目标，不能宣称真实物理曲线一条一票。color/geometry/outline独立保留，outline视角相关，深度证据不是固定crease真值。保存全部16F RGB/fine/major/detail/类别/chunk预览及计数。旧广union及Mic C alpha容差区81.49%仅历史baseline，保持原意。

## S2：扩展真实贡献

使用只读已审计 TOP32 二进制（SHA256 `df40e7acd2167c2e8bc377644b0982841c571ffb1c55859162840a34d2c8c86c`），所有16F实际运行 native800全模型同一forward。每姿态验证RGB/alpha/depth/median-depth和前4 original IDs/raw alphaT/depth与来源缓存；使用来源冻结容差，绝不放宽。保存前景 compact CSR（pixel IDs、原始ID、原始w、indptr）及全网格每ID质量、前景/类反证/非边缘质量，避免保存重复H/W/K normals。

逐F、逐类、foreground/MAJOR/DETAIL/offedge报告 captured alphaT / full alpha 的weighted mass、均值、p10/p05/min与遗漏残差。完整性门槛是每F平衡MAJOR质量>=.95且MAJOR射线p10>=.90，ROI alpha>=.08；这只是操作门槛，不是数学全贡献。任一TOP32失败则在新out隔离复制、只改容量构建K64；若仍失败再K128，先数值校准。每级审计保留；S3两场景统一使用最后共同可用K。构建/预算失败时保留matched K32/最后可用结果，明确FULL_ATTRIBUTION_UNDETERMINED。未观测核unknown，不是nonedge；原始全网格缓存质量>=1且可见F>=2才eligible。

## S3：固定ID联合选择

需求为每MAJOR像素原始full alpha的0.5倍，探索性需求不是表面GT。稀疏矩阵存每像素每类原始w/demand，不对topK权重归一化。效用 U=Σomega min(Σselected w/demand,1)。逐核漏出成本是每视图所有foreground、离MAJOR或DETAIL union超过2px的射线上 mean(w/fullalpha)，再平均八F；不存在ID贡献为零。保留各class反证及完整原始质量，未知不罚。

A原历史TOP4 baseline_union独立排名；B新MAJOR+expanded K的独立比率，分子Σomega*w/fullalpha、分母每F完整foreground mean(w/fullalpha)均值；C/D/E分别U−λΣcost，λ=[0,.1,.3]全部报告，不选英雄λ。自适应lazy heap逐次重新算真实剩余需求的增益，tie按original ID升序；<=1e-15停止，不填未知核。目标有泄漏惩罚可能非单调，不声称经典单调greedy保证或算法新颖性。

Mic预算336/1007/3356；Materials722/2164/7213，来自历史实际核数，不按扩展资格人数重算。各arm保存有序最大前缀、每步utility/gain、独立scorebank、raw mass、eligible/unknown/unreliable/residual标志、类字段与ID JSON。早停另在joint实际数量评价A/B。coverage匹配仅用F：以A中档预算U为目标，取各arm达到目标的最短可用前缀，否则null；全F全场景完成封存后禁止修改选择。

## S4：封存后原生评价

保留全原模型不透明度和遮挡次序，指示量作为固定RGB属性黑底完整native投影Q=Σselected原始alphaT；没有删核、view mask、projection clipping或重新合成。全一field校准alpha；所有field bank的alpha/深度需与原RGB原封不动。原生alpha clamp .99、低于1/255跳过，transmittance<1e-4提前终止；“完整native”只指这些定义下有效贡献。SH0 clipped DC，45个高阶SH系数保留在模型但不用于本渲染，不称完整反射验证。

优先全部8C三预算、全部F三预算与F选定count/coverage匹配点；33arc完整中档5arm，首中末和全视图contacts、native与Telegram1600 H264/yuv420p/faststart视频。比较MAJOR/DETAIL需求覆盖、类/chunk、offedge alpha贡献比例、ink area及可见ink宽度诊断；保存原始gain1灰度，非匹配墨量。指标不是mesh P/R或真实边缘准确率。数量减少本身不是成功；预声明诊断要求同预算覆盖不崩塌且漏出下降（报告连续相对差，不posthoc造门槛）。成功还须实际首/中/末及全视图/video独立人工复核，本轮人工科学结论PENDING。整核足迹宽可能导致负结果，应如实报告。

## 工程、预算与来源

最多初始wall90min（起始UTC 2026-10-04 23:11:34），CPU线程2，GPU0优先，每次launch检查所有外来compute PID包括同用户，拒绝重叠；不kill/重启外部Claude/tmux。不安装全局依赖。新科学输出<=8GiB，每次大写/发布检查root余量>=2GiB与commonGit HDD余量>=1GiB，不回收其他文件。atomic per-pose输出/seals/STATUS JSON及plain runner可续跑；未跑字段null，坏视图工程停止不冒充其他为0。

工程GO需可复现ID、校准权重、匹配控制和真实完整媒体；G0合成pixel/world单元测试与native/media校验单独记录，不能代替人类科学GO。报告实际S0..S4计数、所有负结果/阻碍/范围限制。SOURCE_MAP SHA256覆盖全部输入绑定、模型、源码、config、selection、图片、视频。只显式git add --sparse本阶段及config，小媒体入Git，大数组留out；SSH推送并读回commit和选定文件hash。

方法受weighted coverage/set-cover式饱和效用与已有贡献提升思路启发，不提出新颖性。实际native内核来源是第三方RaDe分支，历史项目独立插桩；本轮仅复用/容量扩展，并非原创RaDe或原论文复现。旧 audited core/native/media只复制到本阶段并标记来源；本轮新科学是MAJOR/DETAIL合同、balanced chunks、expanded contributors和joint selector。无未经核对的文献/研究博客主张。
