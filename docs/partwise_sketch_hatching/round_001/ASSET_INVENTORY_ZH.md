# Round 001 本地资产盘点

本次只做限定科学目录的只读元数据检查，没有训练、渲染、导入 torch、访问 GPU、下载或修改共享环境。完整路径、版本和小型来源文件 SHA-256 见 `ASSET_INVENTORY.json`。盘点不能代替模型质量验证。

## RaDe-GS 来源与已有训练资产

作者代码位于 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS`，观察到 HEAD 为 `2d4bc087f1b4bd62c96054fbe89d273490526b81`，tracked 工作树无修改。README 标明 Baowen Zhang 等及作者 GitHub 来源，要求 CUDA rasterization 与 simple-knn。此次 CPU-only 约束下，不运行作者训练或 CUDA 提取。

`models/scan{24,37,40,55,63,65}_paper_text_precision_v01_half_30k/point_cloud/iteration_30000/point_cloud.ply` 均存在；文件头含 `filter_3D`，配套 `train_complete.json` 记录 30,000 iterations（15k photo + 15k geometry）以及 source/data manifest 摘要。它们应称为“历史本地修改的 RaDe-GS precision variant 训练资产”，不能称为未修改作者基线，更不能仅凭 PLY 名字判断为训练完成的 RaDe-GS。所有这些 receipt 都保留 `scientificdone: false`。来源目录 `sources/paper_text_precision_v01` 不是 git 仓库，已有 `full_reproduction_v01/precision_v01/candidate_source_frozen_v01.json` 提供文件快照；本次仅记录该快照身份，没有完整重放或逐文件验证。

六个场景各有 49 个 cached depth NPZ 与相机约定文件；深度声明为 `median affine camera-z; raw, not alpha-normalized`，尺寸 777×581。scan63 另有 `recon.ply`，仅 1,936 bytes，文件头为 29 vertices / 22 faces，不能把“文件存在”解释为可用的完整物体重建。其训练视图范围、构建来源和几何质量未审核，不能直接纳入主实验代理或评估真值。

## RGB + cameras 与 lamp 缺口

`data/prepared/scan24, scan37, scan40, scan55, scan63, scan65, scan69` 各有 49 个 RGB 文件，`scan83` 有 64 个；均有 `cameras.npz` 和 COLMAP `sparse/0/cameras.bin, images.bin`。这些是真实存在的后续 RGB+cameras 候选路径，未确认其部件标签或对 lamp 的适用性。prepared 目录同时含 depth、mask、points，必须另行审查来源，不能将评估几何混入主输入。

在三个指定科学根目录进行最大深度 5 的名称搜索，不跟随符号链接，排除 venv/.git/site-packages/orchestration/rounds 等，共访问 9,030 个目录。`lamp` 字符串只命中 5 个 `clamp` 文件，未找到 lamp 数据集或 checkpoint。结论限于这次有界搜索，不等于全机不存在。Round 001 应使用明确标注为 procedural/GT fixture 的 shade/stem/base lamp；不能据此声称 RGB 多视图 RaDe-GS 重建或自动部件分割成功。

## 避免旧 vanilla GS 被误标

`/home/u00134/3dgs_line/hybrid_raster_trained_models_v1/PROTOCOL_HAO_MUKAI.md` 明确声明旧冻结 PLY 是 vanilla GS，disc approximation 不是作者 RaDe-GS，协方差轴不是校准表面法线。该目录 `PROTOCOL.md` 还说明旧 vanilla PLY 缺少 `filter_3D`。此前 Ficus/chair/lego/drums 保留视图已曝光，不能再称 blind TEST。

## CPU 依赖与视频

优先 Python 为给定 venv，版本 3.10.20。仅用包 metadata 确认 numpy 2.2.6、scipy 1.15.3、Pillow 12.2.0、matplotlib 3.10.9、imageio 2.38.0、trimesh 5.1.1、open3d 0.20.0、plyfile 1.1.5、scikit-image 0.25.2；torch 2.5.1+cu124 / torchvision 0.20.1+cu124 的安装不构成使用 GPU 的授权。pytest、opencv-python、imageio-ffmpeg 的对应 distribution metadata 缺失。

PATH 未发现 ffmpeg；限定搜索已知 envs、优先 venv、build、cache 只发现 imageio 的 Python 插件，没有 ffmpeg/ffprobe 二进制。若制作 MP4，应由主代理在授权 worktree 隔离安装依赖并记录版本/来源，不能升级共享 venv。本盘点未安装任何依赖。

建议本轮完成廉价 P0 GT 灯具；后续可做现有 DTU 训练资产/缓存深度/mesh 的来源审计，或准备新的 RGB+cameras 输入。此处没有给出或推测任何实验性能数字。
