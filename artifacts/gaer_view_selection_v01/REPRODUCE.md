# 重现 GAER 按视角选核与真实输出

已有原始 PLY、metadata 和上一阶段 VERIFIED 隔离 native 模块是只读依赖。不要运行旧阶段 reproduce.py，不需要 rebuild/install 或修改任何旧 renderer。所有实验写入只在本阶段三个目录中；ignored out 用其内部 `.gitignore` 的 `*` 实现，不改项目原有 `.gitignore` 或共享 Git 配置。

```bash
cd /home/u00134/3dgs_line/gaer_view_selection_v01
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
$PY -B experiments/gaer_view_selection_v01/reproduce.py
```

此命令真实运行 4 个 sparse contracts、2 个 native visibility/flat-texture contracts、2 个实际 deletion/region contracts，并独立进程逐视角重新 native render 8 个相机。验证 baseline RGB、original top-K IDs/weights、raw scores、full-model-T selected contribution、实际 opacity0 deletion RGB/alpha、完整可见质量梯度容差、原始输入与已封存输出 SHA。失败返回非零；不会跳过 GPU 宣布通过。颜色梯度含 FP32 atomics，不要求跨运行归约逐位相同；预置验证容差 rtol=3e−5、atol=2e−5。CPU-ray oracle 使用独立 alpha*T 积分，rtol=2e−5、atol=2e−6；绝对误差与真值一起保留。

```bash
$PY -B experiments/gaer_view_selection_v01/run.py
$PY -B experiments/gaer_view_selection_v01/make_report.py
```

附加的 phase10 连续分数 projection 与四种主方法 selected-only JPEG 逐字节重建验证：

```bash
$PY -B artifacts/gaer_view_selection_v01/EXTRA_VALIDATION.py
```

此补充的源码和配置在 `EXTRA_VALIDATION_FREEZE.json` 单独冻结，不改变主 selector/config/IDs。它重渲染 all 32 primary selected-only 原色 JPG，并保存可对照的 float32 RGB。report 的末尾负结果说明是从 sealed JSON 编写的核对说明，主 make_report.py 可重新生成主要表格；所有原始数值结果独立保留。完整场景不分配 H×W×N；仅 CPU 真值夹具使用小型 9×9×12 穷举数组。

相同配置的已封存 unit 会 SHA 核对后 SEALED_SKIP。runner 按场景/相机逐个 unit 捕获失败，其他视角仍继续；失败目录 `.partial_*` 不覆盖或删除。新目录生成可用 `reproduce.py --generate`；当前规范 evidence 不为重跑而清空。原始 full RGB 与旧阶段 r_1/r_14 的 float32 canonical baseline 同样逐位相等；r_7/r_33 是本阶段新选核视角，按 DATA_FREEZE 文件名匹配 metadata。

PREREGISTRATION.json 在 canonical synthetic calibration/八视角生成前保存 protocol、源码方法 SHA、四相机参数及只读依赖 SHA。其中包含旧树独立重跑后脏 REPRODUCTION.json 的现有字节，不恢复/编辑它。旧 runtime import 会 mkdir 旧 out，本阶段用受控 shim 绑定已有 native.py/scene_io.py 的函数，只读取旧二进制，旧 runtime 本身不执行。没有新 CUDA kernel。

主 δ=2px，预置 δ=1/4 与 ±15°法向诊断；K=8 主、16/32 实际敏感性 rerender，固定 0.1/0.5/1% counts。automatic floor 来自独立共面内部 null，不取 Lego/Chair 或 deletion 最优阈值。自动 REFUSED 时，图上明确显示预注册 0.5% diagnostic，不用预算图代替自动成功。B4 detector/AUROC/AP、depth、后续额外 geometry、训练/艺术 pipeline 均未运行。

每相机 `downloads/{scene}_{camera}_scores_ids.npz` 为小型可下载归档，包含所有原始行 ID、raw、score、完整 visible mass、所有预算/方法/K 原始选中 IDs。原始高分辨率数值 NPY 与端点/unknown residual bound 在 ignored `out/gaer_view_selection_v01/units/`。主图为四视角仅选中核原色 JPG，另有 full RGB 同相机比较、各方法同数量 subset、causal deletion、endpoint/normal/center zoom 与 histogram。MEDIA_MANIFEST.json 记录文件 SHA、尺寸与图义，seals/*.json 封存逐 unit 完整输出。

每 unit 检查 GPU0 的 UUID/PID，只允许自身占用，遇到外来 PID 失败、不 kill、不 overlap。CPU affinity / Torch / BLAS 都为 2；root reserve=4GiB、common Git reserve=1.5GiB、stage cap=8GiB。CUDA forward 3 warmups+5 samples 的 event 和 wall 实测，与 CPU copy/sparse/full-mass backward/end-to-end 分开记录。不存在 H×W×N 分配。

```bash
git rev-parse HEAD
git ls-remote git@github.com:mengguo311/FeatureLineRendering.git refs/heads/gaer-view-selection-v01
git status --porcelain
```

push 使用显式 SSH URL，保持 origin HTTPS 不改，不读取 credentials。发布 receipt 保存在 ignored `out/gaer_view_selection_v01/PUBLISH_RECEIPT.json`，核对远端任务分支 SHA=HEAD、基准分支仍 ee28fdce75b07a2cee5406e60f4be8014aa77336，提交仅含新阶段两个 tracked 根。人类 visual GO 待审核；当前阶段止于 selection/diagnostic。
