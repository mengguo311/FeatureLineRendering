# 复现与续跑

在授权worktree `/home/u00134/3dgs_line/representative_edge_gaussians_v1`、分支 `representative-edge-gaussians-v1` 运行。保留sparse checkout，不展开旧路径；已有代码和模型/transport只读。

```bash
bash artifacts/representative_edge_gaussians_v1/run.sh
```

runner调用已安装的 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`，CPU线程2，CUDA_VISIBLE_DEVICES=0；不安装依赖。每个native launch的GPU guard拒绝所有外来compute PID（包括同用户），不停止别的任务。GPU_BUSY应等待空闲后重跑对应阶段。

`bash artifacts/representative_edge_gaussians_v1/run.sh --check-only`验证全部现存封条而不重写F封条、不读取新科学像素。完整runner外层timeout为90分钟。

阶段也可单独调用（已有全F选择封条时不能重跑selection.py；pipeline.py会校验并跳过）：

```bash
python -B code/run.py evidence
python -B code/run.py contributions
python -B code/selection.py
python -B code/audit.py
python -B code/evaluate.py
python -B code/finalize.py
python -B code/ledger.py
```

以上 `code/` 是本阶段代码目录的简写；从workspace使用完整路径或设置工作目录。`audit.py`必须在评价前通过；实际完整runner固定env/Python。S0 freeze.py已完成，**不要重跑**，不要替换冻结文件或封条。`run.py`验证S0原始文件散列；F归一化只Mic八F、Materials继承。TOP32按实际门槛决定容量-only隔离K64/K128，所有scene共享最后可用容量。编译仅写本阶段out/native，来源与差异/库hash保存，不改历史build/env。

已封存单姿态跳过并验证SHA256；缺失姿态atomic写入后封存。只有两个scene F选择全部封存后允许C/arc原始读取；保存读事件。任何失败写ENGINEERING_STOP及实际异常，不补其他视图为零。C评价先固定属性和RGB同camera校准，全一channel≈alpha，所有field的alpha/depth完全相同。所有最终图使用FULL_NATIVE_ORIGINAL_T，缓存CSR仅用于选择/诊断。

代码未实现删核render、人工标线、mesh/TEST、重训或3D中心连接。`selected_ids.json`的identity是checkpoint SHA256 + zero-based original PLY row，`arms.X.prefixes.B.selected_ids`直接取固定原始ID集合；`ordered_original_ids`可切出任意已计算前缀。对新视图必须在全原模型下按这些ID赋field；单独render子集会改变T，不等价。

每次大写入/发布验证新科学输出<=8GiB、root余量>=2GiB、commonGit HDD余量>=1GiB。初始实验最多90分钟；下一次独立续跑也应通过外部wall限制并保留已有所有预算、阈值、λ及S0/F封条。不要回收其他数据、chmod旧文件或调整门槛来“救”负结果。

SOURCE_MAP覆盖原始模型、manifest/source/native代码、每张图/视频/选择/config及大型out数组；视频33帧不剪辑，H264/yuv420p/+faststart，native4000px比较panel与Telegram1600。完整49视图contacts、arc首/中/末及F/C覆盖匹配面板使用原始gain1，未匹配墨量。独立人类科学验收保持PENDING。
