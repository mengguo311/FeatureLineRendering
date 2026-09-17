# VRSS 第一阶段预注册（实现和图像检查前冻结）

仅在 `vrss-experiment` 工作；基线 acd4ab9 不改。结果只写 out/vrss/。

## 问题与唯一 cheap kill-test

chair，一个预定义 120 帧连续 360° DEV 轨迹，一个 40% 平均可见路径长度预算。只选择已有物空间完整路径；不增加、移动或连接路径。候选池在重新生成后封存，对 A/B/C/D 完全相同。

A：独立长线支持/平均视角收益按单位长度排序。B：VRSS 去关系（保留 tail 和重叠惩罚）。C：VRSS 去 tail（保留关系及重叠惩罚）。D：完整 VRSS。D 的 q = 0.5 U + 0.5 R - 0.1 D_overlap，目标为最差 25% 视角均值。B 的 U 权重为 1；A 不使用关系或重叠项。报告所有版本的共同完整 q，另报各自优化目标。

预算 cost 是 TRAIN 证据相机上的平均可见投影长度/图像对角线；每个版本 <=40%，且应 >=39.5% 全池长度。离散笔画无法满足时记为预算比较失败，不通过增加笔宽补偿。DEV 长度、墨面积另外报告，不声称逐视角墨量相同。

## 输入与隔离

见 manifest.json 的精确参数、输入 hash 和 16 个 TRAIN indices。索引定义：i%10==5 为 TEST，i%10==0 为保留 VAL。其余 80 个 TRAIN 中均匀选 16 个用于 fresh seed、pull、selection。旧 seed/cache 无 TRAIN provenance，全部禁用。

重生成沿用现有 M1a fraction .30、DT pull 100 步、标准 consensus prune 和旧 chaining 参数。生成阶段的 DT pull 属于旧候选构建；候选封存后任何 selector 都不能改变几何。运行 seed/pull 前先单帧 GPU smoke。任何故障修复写清楚；不根据视觉结果修改阈值。

只打开这 16 个 TRAIN RGB。DEV 为从 TRAIN 相机和 GS 定义的合成轨迹，不打开 TEST 或 VAL 图像。GS 原先是否包含所有 100 张图训练尚未独立核验：隔离声明仅针对 line module。

方法入口及依赖不得读取 mesh、GT crease/cache 或 2DGS normals。最终像素由固定全局三维路径子集投影和 GS 可见性产生；没有逐帧图像证据或身份切换。

## 关系与约束

双尺度粗边缘上的有限长线臂组成转折/汇合证据；仅在有限线段附近相交、角度足够分离且两尺度复现时保留。固定 32px cell 最多两条关系；枚举 2–3 条候选路径共同支持的关系。不能解释的证据仍计入分母，不把投影 T/L 关系声称为真实 3D junction。R 只在组合成员全部选择时给收益；重叠惩罚抑制重复墨迹。

用 deterministic singleton/combination greedy 与有限局部 swaps；预算余量用可容纳路径补齐，即使收益非正，以防少画获利。资源上限和全部常数在 manifest；无网络、无 retraining、无 mesh gate。

## 官方 RGB 核验

本地 GRAPHDECO 外部仓库有一行返回值 ABI 适配（四输出解包，RGB 路径未改）。必须实际调用官方 render，记录源码与扩展 provenance、单帧结果及耗时。如果不可用，记录 blocker；不能用旧 disc/SH0 renderer 冒充 RGB。旧 disc G-buffer 只作为固定、所有版本共用的可见性近似，局限明确保留。

## 产物与 GO / NO-GO

1. 120 帧不跳帧、不挑帧、无 GT overlay 的官方 RGB | A | D 视频；0/25/50/75% 四帧 panel；B/C/D 消融 panel。
2. 保存选中 ID、输入/候选 hash、预算审计、逐视角 q、最差 25% q、墨面积、可见长度、短碎片和重叠、耗时。代理 q 的改善本身不能 GO。
3. 亲自检查四个固定帧以及完整视频抽样/接触表，记录断裂、噪声、闪现和视角失败。
4. 只有 D 在可比墨量下肉眼保留 A 丢失的至少一个结构关系，且 B 或 C 至少一个有对应可见退化，才允许 GO。不能只展示事后挑选局部；证据必须可在完整片段中定位。
5. 没有上述视觉证据、预算失配或关键输入核验失败即 NO-GO/blocked。区分 detector、候选、目标代理瓶颈，不调候选/加网络救结果；不进入 lego/cadpartA 正式阶段。

本轮无人类盲评参与者；实现测试通过不等于方法有效。
