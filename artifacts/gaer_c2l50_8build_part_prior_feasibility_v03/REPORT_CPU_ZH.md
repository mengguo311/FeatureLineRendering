# Ficus 冻结原核：CPU 绕过 GPU 的实际运行（v03）

截至 2026-10-20 14:33 JST，GPU 0/1 各有 26 个进程上下文，未占用 GPU；08:00 的临时 GPU 授权已到期。本次全程屏蔽 CUDA、CPU 线程上限为 2，在独立 branch 上运行。

## 已实际运行并核验

- 官方 PartField checkout `373025dbd283bb44cc4a6dc78c99994dbc91de32`，公开 checkpoint SHA256 `463efc8a3afd3913142aa025e0125c00f16ef452b8de6a132ebe32bbe7877ee4`，`weights_only=True` 严格加载。CPU 代码未修改官方 checkout；运行时仅将 PVCNN 构造位置参数设备从 CUDA 替换为 CPU，绕开 GPU-only 的预测 wrapper。
- 输入冻结 Ficus PLY SHA256 `9afacac137474a50c5db52e41d2f1656b1e5f22ee5b6804e7e819697679cebac`，共 284,835 原始行；该 PLY 没有单独 `source_index` 字段，因此这里严格定义 `source_index=i` 为原始 PLY 第 i 行。原资产及旧 worktree 未改动。
- 实际 CPU smoke：1,024 个原核中心作为编码器输入；128 个保留原行号的查询，输出 `(128,448)` 特征。实际 CPU full-query：8,192 个确定性原核中心编码；按原行序对全部 284,835 个原核中心分块查询，输出 `(284835,448)` 特征，编码及查询阶段实测 27.08 秒（不含输入/权重校验与环境启动）。该特征文件独立读回，SHA256 `78b6c984898545aaf6a7b38a599e3e873eddce6c5cced14c8c6b7e6107cc0f75` 与 manifest 一致；采样特征非恒定。
- 以官方示例的原始特征 KMeans 思路做 `k=3, random_state=0, n_init=3` CPU 探索性聚类；原行序标签数量 `[54774,192732,37329]`，文件 SHA256 `afdf723cbd781bd40e034454aca1fe7e98b131b2b9e32cfc47c608c6a9ce8248`，读回数量与哈希一致。XZ/YZ 全主体投影图见 `CPU_K3_PROJECTIONS.png`：cluster 2 集中于盆底区域（37,329 核，最高 z=-0.4723），cluster 0 多为一侧树冠；cluster 1 同时包含树干与其余大范围树冠。**三簇未分开盆／干／冠。**

## 边界与判据

8,192 原核中心子集编码器 **不是官方全点云推理**；全部原核只是连续特征场的查询位置。KMeans 的 0/1/2 是无监督簇编号，不是语义标签；散点图不等于真实 3DGS 渲染，也未做 held-out 视角的原核关掉／改色重渲染。因此本阶段证明 **不占 GPU 可做逐原核 PartField 特征推理**，但没有证明盆／干／冠可分别编辑，也不是科学 GO。按 Astra ultra 预审要求，必须先做原外观多视角真实编辑，评估跨部件误带走和覆盖，才可宣布部件编辑成功。

## 可追溯文件

- 源码与测试：`reproduction/radegs_c2l50_8build_overnight_npr_v01/part_prior_v03/{cpu_partfield_probe.py,analyze_cpu_features.py,test_cpu_probe.py,test_analyze_cpu_features.py}`。
- 大数据在 HDD 任务目录：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/cpu_probe_v03/`：`full_features.npy`、`full_manifest.json`、`k3_labels.npy`、`k3_summary.json`、`k3_full_subject_projections.png`。
- GPU runner 在预审中 NO-GO，未执行；本次只提交 CPU 版本。不把先前 v01/v02 的去盆失败冒充为本次结果。
