# Ficus 冻结原核部件先验可行性实验 v03：启动预检（暂停）

**状态：`PREFLIGHT_BLOCKED_GPU_EXCLUSIVE_GATE`，不是科学 NO-GO。** 本分支记录 2026-10-20 03:13 JST 的实际进度；还没有 PartField 或 SAGA 的原核标签、编辑图或性能比较。不要将本报告当作方法验证结果。

## 目标与隔离

- 基于 v02 冻结提交 `1db93f717f86b0f99d2d5d35d34d1775305dcb00` 新建分支 `gaer-c2l50-8build-part-prior-feasibility-v03`，独立 worktree 位于 `/home/u00134/3dgs_line/gaer_c2l50_8build_part_prior_feasibility_v03`。v02 工作树和原始 GS/C8/joint 均未修改；本分支只增加此进度记录。
- 目标是在 Ficus 原始 GS 的每个 `source_index` 上测试大部件（盆／干／冠）的可编辑归属。允许软成员、跨视角冲突和 `UNKNOWN`；输出必须用源 GS 真实移除／改色重渲染，不能只看点云聚类颜色或二维 r04 伪标签。
- 原 PLY：`/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/ficus/seed_1729/checkpoints/point_cloud/iteration_30000/point_cloud.ply`。实读 SHA256 `9afacac137474a50c5db52e41d2f1656b1e5f22ee5b6804e7e819697679cebac` 与 Ficus registry 完全一致；顶点 **284,835**、字段 **62**、XYZ 全有限。原始零基 PLY 行号是 `source_index` 的待验证映射，不能仅用位置近邻重建 ID。

## 已执行

1. 创建并核验独立 worktree/branch，检查原 v02 工作树未变；任务内 materialize 所需的 source-membership 源码（原有提交，非新改动）。
2. 只读审查调用了真实 `gpt-6-astra / ultra`，session `01a1542d-c61f-7a30-9735-2c81fde86bc0`。其本地只读沙箱在 `bwrap: loopback: Failed RTM_NEWADDR` 处失败，**未成功读取本地仓库**；该审查提供的是作者代码/资源门的建议，不可冒充本地审计。审查原文保存在服务器 `/mnt/hdd1/u00134/astra_part_prior_v03_review.txt`，SHA256 `272b22fc183ccfaba29e96de5e943382d686f42b3cddf18ff4a21d1ccae808cf`。此后由主执行者独立核查了上述源 PLY、registry 与分支状态。
3. 作者实现预检：PartField 官方 splat `.ply` 路线读 XYZ 并产逐点特征，但默认推理包含 CUDA、DDP、混合精度/硬编码 GPU 调用；SAGA 的特征训练亦依赖 CUDA rasterizer。未下载或运行 1.24 GB PartField checkpoint；未运行 SAGA。不得用几何聚类/颜色代理冒充这两种发表方法的实验结果。
4. 用户授权**仅在某张 GPU 完全无其他进程时独占运行**；占用则暂停并通知，不准建立等待队列、共享占用或干预其他进程。2026-10-20 03:13 JST 从 `nvidia-smi` XML 核验 GPU 0、1 各有 **26 个进程上下文**，所以没有启动科学任务。

## 继续前的门与预注册方向

- 重新检查单卡进程上下文为零、资源预算和输入哈希；若仍占用，则保持暂停，不自动排队。用户另行授权前不使用他人的设备时间。
- 先在 BUILD 视角冻结一次真正的 PartField 发布权重推理及簇映射；保持原 PLY 行序、重复坐标、参数和所有 `source_index`；不得按 reserved 视角挑簇数或阈值。给无法语义命名/互相混合的核 `UNKNOWN`。r04 只作带缺陷对照，不作独立真值。
- 先真实删除候选盆核并以原 GS 在 BUILD 及历史 reserved 两个弱视角重渲染，若盆仍完整或误伤干冠则如实停止；仅通过后考虑独立干冠编辑或 SAGA 特征臂。`test_r_14`、`test_r_79` 已历史暴露，不称新盲测。应保留全主体并排图、源 ID 对应和资源/输出哈希。
- 每个实施/运行步骤先复核 Astra ultra，再记录 RED→GREEN 测试与真实运行结果。旧 v01/v02 的负结果（v02 仅 553/284835 获标签且去盆失败）不可被新预检覆盖。

**尚未完成：** 方法依赖安装与权重核验、原核特征推理、部件归属、真实编辑、视觉审阅。当前只有启动预检，不能判定 SAGA/PartField 是否可行。
