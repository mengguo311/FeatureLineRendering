# C2L50 8BUILD 原场景 + 线 Gaussian 合并交付

本目录只合并冻结 `c2l50_multiview05_v01/arms/C` 与其 REGISTRY 指定的完整 SH3 原场景。无训练、检线、曲线生成、剪枝、去刺或 GPU 工作。三个场景的 source 和 ink 进入同一 Gaussian 列表、同一次深度排序、同一次前到后 alpha 合成。

## 路径与环境

输出根固定为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_joint_gs_v01`。
只读 Python 为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python`，运行带 `-B`，CPU affinity/BLAS 最多2线程。
源路径和 SHA 见输出根 `SOURCE_MANIFEST.json`；相机和原模型见 `REGISTRY.json`。不能将旧资产替换为 A/B 或其他05结果。

## 命令

在本源码目录执行：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B test_runner.py
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python -B verify.py --readonly --replay
```

`verify.py` 只读检查全部源/导出字段、映射、sealed units、视频哈希，`--replay` 逐场景从实际 merged PLY 重载并在内存重渲染一相机，要求图像数组 bitexact，不写输出。

原生产入口为 `produce.py --scene scan24 --view 0000`（同理scan65/ficus），以及 `batch.py`。已完成封存单元只校验后复用。`movie.py` 会生成新的33帧，不应对封存目录重复执行。`figures.py` 组织交付图。包构建 `package.py` 拒绝覆盖已有下载包。

标准库分块重组（manifest、所有part置于同一目录，目标不得已存在）：

```bash
python3 reassemble.py scan24_C2L50_8BUILD_JOINT_MODELS.zip.SPLIT.json --output rebuilt.zip
```

## 格式和限制

`merged_native.ply` 原source所有字段prefix exact（包括+Inf原opacity/filter_3D/SH）。ink原PLY字段exact，高阶SH补0、filter=0。`merged_portable.ply` 是标准3DGS字段，烘焙源3D filter；group/parent映射在sidecar。详细误差、epsilon和可拆分范围见输出 `FORMAT_ZH.md`、逐模型 `AUDIT.json`/`RANGES.json`。

CPU EWA 使用完整 SH、完整投影协方差、近面0.2、中心深度排序。不是官方CUDA RaDe等价实现。保持旧ink投影floor，Ficus source和ink floor不同，通用viewer使用统一floor时可有视觉差异。未改变world covariance或opacity来“显线”。原C2L50毛刺随文件保留。

## 回退

本次仅在 `gaer-c2l50-8build-joint-gs-v01` 新worktree本地提交。旧 `/home/u00134/3dgs_line/gaer_rade_depth_lift_v01` HEAD/index/全部tracked与untracked源码保持不变，见 `ROLLBACK_RECEIPT.json` 和 `SOURCE_BEFOREAFTER.json`。回到原目录继续使用原成果即可；无需且不得 reset/clean/stash/覆盖旧目录。
