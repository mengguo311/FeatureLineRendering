# 中文复现与验证

在专用树 `/home/u00134/3dgs_line/gaer_kernel_space_lines_v01`，分支 `gaer-kernel-space-lines-v01`。仅写 `experiments/gaer_kernel_space_lines_v01`、`artifacts/gaer_kernel_space_lines_v01`、`out/gaer_kernel_space_lines_v01`。不导入旧 runtime，不运行旧 run.py，不安装、不训练、不使用 mesh 输入或额外几何。原 NPZ/PLY、相机元数据和原生 RGB 路径及 SHA 见 INPUT_FREEZE.json；缺少精确源文件时停止，不能造数据代替。

固定 Python 为 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`。环境脚本已固定 CPU=2，禁 pycache，所有临时/缓存路径置于新 stage；TERM=xterm-256color 在 tmux 操作前设置。无 GPU 路径，不争用或杀外来 PID。每阶段资源守卫 root>=4GiB、sharedGit>=1.5GiB、stage<=2GiB，生产 1GiB 守卫完全未动。

现有交付可以用以下命令验证，第一条无需覆盖历史 TDD 日志：

```bash
cd /home/u00134/3dgs_line/gaer_kernel_space_lines_v01
bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/test_contracts.py
bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/verify.py
bash experiments/gaer_kernel_space_lines_v01/env.sh experiments/gaer_kernel_space_lines_v01/replay.py
```

实际结果：契约 7/7 PASS，独立审计 PASS，159 个受保护源文件未变；两 scene 的所有图数组与四份 GLB deterministic replay 逐字节 PASS，见 REPLAY_VERIFICATION.json。Replay 仅在新 stage `out/.../replay` 生成 GLB，不覆盖已冻结资产。verify / replay 会更新本 stage 审计日志；若运行于已提交工作树，可先查看 `git diff`，不要把重跑时间戳当原交付证据。

最初一次实际运行依次是 `prepare.py` → `build.py` → `media.py` → `verify.py`。`prepare.py` 复制完整源 NPZ、读取全部 PLY XYZ、冻结选核来源和相机；`build.py` 在看真实图前保存 ALGORITHM_FREEZE，然后输出全部固定资产；`media.py` 只读取资产并做相机投影、视频编码/完整解码。上述构建程序用于尚无冻结交付的 stage；现有交付请使用 replay，避免覆盖冻结时间戳或负日志。

算法只取 r_7/r_33 的 gaer_ratio_0.005_ids 并集及对应原 XYZ。k=12、局部线性度>=0.45、双端方向 cos45°、两端距离门控 3×min(local scale)、双端每半轴短边互选，参数无结果后更改。所有候选邻接和失败原因都保留。每场景 r=0.12×median(local scale) 单一世界 tube 半径，八边截面；所有图中心线端点等于原模型行。PCA 轴非表面法线。图像/alpha/depth/协方差不参与构图。

独立 GLB 读取使用新 core.py 的 chunk/accessor 解析器，与生成函数不同；再使用既有 trimesh 库读回作第二实现核对。tube_mesh/glb_bytes 是从上阶段 core.py 的两个函数 AST 只读提取，来源/hash 见 REUSE_PROVENANCE.json。其 ray_points/supported_depth 不执行，旧 run.py/runtime 不导入。没有新增/替换共享二进制。

四相机原 RGB 精确同相机复用；既定 33 实际 arc 矩阵、对应旧 native result 与 RGB hash 全部校验。视频全程相同 XYZ/原 ID edge pairs，只改变相机投影。2px 是展示中心线宽度；x-ray 保留所有隐藏线，不是 tube native mesh render 或隐藏线/宽度测试。帧 PNG 全部在 `media/<scene>/arc/frames/000.png`–`032.png`，完整 H264 解码记录在 FRAME_MANIFEST.json。编码使用已有 imageio_ffmpeg 二进制，两 CPU 线程、yuv420p、+faststart，不安装系统 ffmpeg。

RED 原始 stub 和测试结果记录为 TDD_RED.log（7 个 NotImplementedError）；随后实现，保留一次浮点断言负结果后 TDD_GREEN.log 为 7/7。输入封存字段名失败日志亦保留。真正数据、资产、科学负结果没有删除或换名。

最终只用三个 stage 路径显式 git add/commit；通过 `git push git@github.com:mengguo311/FeatureLineRendering.git HEAD:refs/heads/gaer-kernel-space-lines-v01` SSH 推送，并 `git ls-remote` 读回 SHA。`DELIVERY.json` 是推送后生成且仅本 stage 忽略的最终 receipt，含实际 HEAD/remote SHA/clean status 与真实测试结果；避免对一个含自身 SHA 的文件作不可成立的自引用提交。
