RaDe-GS v2 严格复现准备审计（第 1 阶段，2026-10-07）

本报告只完成源码、论文、数据和环境的准备审计。没有启动训练、渲染、mesh、GPU 测试或数值科学实验，没有安装包、下载大数据集、排队、创建 cron、委派 agent、commit 或 push。**不代表科学复现完成，也不代表已可直接运行完整 suite。** 最终文件校验状态见 [STATUS.json](STATUS.json)；本轮在第 1 阶段结束后停止，等待用户下一步。

工作树为 `/home/u00134/3dgs_line/gaer_rade_depth_lift_v01`，分支 `gaer-rade-depth-lift-v01`，基线 `52a409b806fd5d326ccce0d5657e25336beb68d5`。保留了本轮开始时已有的 LAUNCH／PROMPT／日志；这些启动文件不是完成证据。本轮新增内容仅在用户允许的两个工作树目录和指定 HDD 隔离根中。

**论文与源码版本已实取核验。** [原始 v2 PDF](https://arxiv.org/pdf/2406.01467v2) 首页标注 2024-06-24，共 12 页。浏览工具因 PDF 太大失败后，以 urllib 在内存获取 20,699,410 字节，再用 `pdftotext -layout - -` 提取文本；PDF SHA256 为 `7940677b85007b76d0285fa87a5782ee7a8e060d5c8db526853743950a3c4f24`。没有把 PDF 大文件存入 root。可复核 [文本](evidence/paper_v2.txt) 和 [获取回执](evidence/web_acquisition.json)。项目页当前仍保留 v1 的 2DGS 实验勘误说明；本轮以指定 v2 为准，不将网站的“latest”自动当作同一版本。[作者项目页](https://baowenz.github.io/radegs/)

| 标识 | 实际 SHA／提交日期 | 审计判定 |
| --- | --- | --- |
| C24 | `2d4bc087f1b4bd62c96054fbe89d273490526b81`／2024-06-21 | 论文同期候选主线；本轮干净克隆的 detached HEAD。**未证实生成作者所有表格。** |
| C25 | `0b1fe5fe2d7655d3bfbd584862788cd449e24ef6`／2025-01-24 | 历史扩展版本；深度公式改变、移除 distortion，新增 TNT／tetrahedra／NVS 入口，不能替代 C24 训练。 |
| C26 | `d72f20792005ae1d6555a82aa2d15345f247604e`／2026-03-19 | 本轮 `ls-remote origin refs/heads/main` 返回的 main。PGSR 多视图、appearance 模式 3、Python 3.12/cu130、Objaverse 属后续扩展。 |

实际克隆目录：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS`。上游为 `https://github.com/HKUST-SAIL/RaDe-GS.git`，项目页旧 `BaowenZ/RaDe-GS` 链接会跳转到该仓库。保留 `.git`、上游 remote、许可证和原始源码；主仓库及两个依赖均 `git status --porcelain` 为空。使用 blob-filter 和稀疏检出，排除 assets、仓库 paper.pdf、SIBR_viewers；GLM 排除文档／测试资产，仅检出头文件及必要源码元数据。源码树实际约 32 MiB，未构建。

| C24 gitlink | 固定 SHA | 实际状态 |
| --- | --- | --- |
| `submodules/simple-knn` | `44f764299fa305faf6ec5ebd99939e0508331503` | 从原 Inria GitLab 获取，HEAD 匹配且干净 |
| `submodules/diff-gaussian-rasterization/third_party/glm` | `5c46b9c07008ae65cb81ab79cd677ecc1934b903` | 从 g-truc/glm 获取，HEAD 匹配且干净 |

`diff-gaussian-rasterization` 本身是 C24 仓库内跟踪源码，不是另一个未固定的顶层 submodule。三个版本的 gitlinks 相同，不代表 CUDA 实现相同。完整 tree/blob/gitlink、关键文件字节 SHA256、时间和版本差异见 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)、[克隆验证](evidence/clone_verification.json)、[历史](evidence/git_history.txt)、[C24→C25 差异](evidence/C24_C25_core.diff)、[C25→C26 差异](evidence/C25_C26_core.diff)。C25/C26 只保存历史源码文本供审计，未切换 C24 工作树。

**C24 的发布承诺小于完整论文。** 同期 README 第 8 行只宣告 DTU 训练／测试已发布；第 36–45 行给出 DTU 数据与三个命令。实查 C24 tree 没有 `scripts/reproduce.sh`、`render.py`、`metric.py`、`metrics.py`、`eval_tnt/run.py`、`mesh_extract_tnt.py`、`mesh_extract_tetrahedra.py`。源码含一般数据加载器、renderer 和部分 integration/tetmesh 辅助代码，但这不足以证明完整实验链已发布。[C24 README](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/README.md#L8-L45)

C25 README 明确改为逐像素 cosine 的深度计算／可选坐标图，并移除 depth distortion。历史中 2024-07-27 的深度反传、2024-08-06 新公式、2024-08-23 二维滤波修复均晚于 C24。C26 又增加 PGSR 多视图项，几何正则起点变为 7000，appearance 参数从布尔变为整数模式；C26 的 `scripts/dtu.sh`、`scripts/tnt.sh` 不能标注成 2024 复现脚本。[C25 Modifications](https://github.com/HKUST-SAIL/RaDe-GS/blob/0b1fe5fe2d7655d3bfbd584862788cd449e24ef6/README.md#L8-L15)，[C26 参数](https://github.com/HKUST-SAIL/RaDe-GS/blob/d72f20792005ae1d6555a82aa2d15345f247604e/arguments/__init__.py#L58-L112)，[C26 DTU 脚本](https://github.com/HKUST-SAIL/RaDe-GS/blob/d72f20792005ae1d6555a82aa2d15345f247604e/scripts/dtu.sh#L1-L7)，[C26 TNT 脚本](https://github.com/HKUST-SAIL/RaDe-GS/blob/d72f20792005ae1d6555a82aa2d15345f247604e/scripts/tnt.sh#L1-L12)

**论文与 C24 存在必须显式裁定的差异。** v2 第 6 页 §4.1.1 写明前 15k 仅 photometric、后 15k 加 geometry，`wd=100`、`wn=5`，detach distortion 的 blending weights，单张 H800。C24 默认 30000 iterations、`lambda_distortion=100`、`lambda_depth_normal=0.05`、`regularization_from_iter=15000`，法线权重相差 100 倍。实际条件为 `iteration >= 15000`，按 1-based 循环是 1–14999 仅 photometric；末次迭代保存但不执行 optimizer step。应记录这些代码语义，不静默“修正”。[v2 第 6 页](https://arxiv.org/pdf/2406.01467v2#page=6)，[C24 defaults](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/arguments/__init__.py#L75-L97)，[C24 loss](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L140-L165)，[optimizer step](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L184-L214)

由实际 CUDA 前向递推与反向代码可静态推出，C24 distortion 对每像素的形式为：

```text
h(d) = (F*d - F*N) / ((F-N)*d),  N=0.2, F=100
M = sum_i w_i
L_dist_code = mean_pixels[ E_RGB * sum_{j<i} w_i*w_j*(h(d_i)-h(d_j))^2 / stopgrad(M^2) ]
M=0 时 Python torch.where 路径取零；distortion 对 w 的梯度在 CUDA 中被停用。
E_RGB = exp(-max(四个邻接方向的 mean_channel |RGB差|))，图像边界填零。
```

前向只对先前累计项加当前项，即 unordered pairs `j<i`，没有 Eq.23 印出的完整 `i,j` 双计数；还存在深度映射、透明度平方归一化与 RGB 边缘权重。这些不是原论文 Eq.23 的逐字同式实现。`M².detach()` 的作用与 CUDA 停用 distortion 的 opacity 梯度应分别说明；不能说全部 loss 都 detach opacity。此处为源码代数审计，未执行数值验证。[forward.cu](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu#L746-L799)，[backward.cu](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu#L826-L861)，[near/far](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h#L20-L21)，[RGB edge](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/scene/cameras.py#L67-L77)

法线项也应保留真实实现语义：C24 先 normalize blended normal，分别与 expected-depth 和 median-depth 的有限差分法线比较，以 0.4／0.6 加权；不能只写成 Eq.24 的单个未经归一化加权和。renderer 输出 RGB、alpha、加权深度、median depth、normal 和 distortion，但 C24 没有完整批量深度／法线导出命令。[C24 train.py](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L147-L155)，[normal computation](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/utils/graphics_utils.py#L117-L125)，[renderer outputs](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/gaussian_renderer/__init__.py#L60-L90)

建议待用户确认后严格分列 `official_default_C24`（100／0.05）与 `paper_text_weights_on_C24`（100／5）。第二列只对齐论文文字权重，**仍使用 C24 的 loss 实现，不能命名为已经实现了字面 Eq.23 的“paper-equivalent”结果**。若要实现字面 Eq.23／24，需要独立审查实现和单列结果。本轮没有改任何 loss 或默认值。两列均不能替代作者发表结果，也不能只挑更接近论文的一列汇报。

**完整目标 suite 保留，证据强弱分开标注。**

| 数据集／论文位置 | 场景清单 | 设置与未决项 |
| --- | --- | --- |
| DTU，p7 Table 1 | scan24、37、40、55、63、65、69、83、97、105、106、110、114、118、122（15） | half 20k、half 30k、full-resolution 三种行均需覆盖。1600×1200 原图的 half 应为 800×600；以下载后实际尺寸核准，不能二次缩放。C24 README `-r 2`、无 `--eval`，使用全部相机。20k 的阶段边界／学习率计划未被 README 说明，不能把 30k 的中途快照自动当作独立 20k 实验。 |
| TNT，p7 Table 2 | Barn、Caterpillar、Courthouse、Ignatius、Meetingroom、Truck（6） | `Our` 为 TSDF，`Our♯` 为 marching tetrahedra；必须分列。v2 没写明全部分辨率／holdout 细节；C25 的 `-r 2 --eval` 只是历史配方，不足以认定 v2 设置。Church 和 Train 不在本表。 |
| Mip-NeRF360，p7 Table 3 | outdoor：bicycle、flowers、garden、stump、treehill；indoor：room、counter、kitchen、bonsai（完整数据集候选 9） | v2 只分室内／室外汇总，未逐场景列出；9 场景来自 3DGS 完整评测清单，不是已证明的 RaDe 作者逐项清单。标准候选为 outdoor `images_4`、indoor `images_2`；C24 本身无对应 reproduce 脚本，需冻结名单和实际尺寸后裁定。 |
| Synthetic NeRF，p8 Table 4 | Mic、Chair、Ship、Materials、Lego、Drums、Ficus、Hotdog（8） | 8 个名字由原表确认；完整 800×800、100 train／100 val／200 test 是需逐包核验的常见协议，不把本机 train-only 子集当完整包。C24 读取独立 train/test，论文该表明确 ours 开启正则。背景黑／白的作者精确选择未从 C24 README 得到证明。 |

DTU／TNT／Synthetic 名单与表格单位见 [v2 p7](https://arxiv.org/pdf/2406.01467v2#page=7)、[v2 p8](https://arxiv.org/pdf/2406.01467v2#page=8)。Mip360 九场景及 `images_4/images_2` 的外部参考固定在 [3DGS full_eval.py](https://github.com/graphdeco-inria/gaussian-splatting/blob/54c035f7834b564019656c3e3fcc3646292f727d/full_eval.py#L15-L59)，其作用仅是完整数据集候选协议。作者原始 NeRF 数据入口与加载器已固定 SHA，见 [NeRF README](https://github.com/bmild/nerf/blob/14c55567a6d0fbd75d3fd12b0411f98160ba3237/README.md#L58-L94) 和 [数据清单](DATA_INVENTORY.json)。

初始化与训练细节不能混用。论文 §4.1.3 的 DTU/TNT 重建用给定 poses 和 COLMAP sparse cloud 初始化。C24 COLMAP loader 按 `image_name` 排序；`--eval` 时序号 `%8==0` 为 test，其余 train；无 `--eval` 时全 train。它支持 PINHOLE／SIMPLE_PINHOLE，并可能在数据目录第一次生成 `points3D.ply`。Synthetic loader 则读取 `transforms_train.json` 与 `transforms_test.json`；即使 `eval=False` 也没有合并 test 的活动代码；若无 `points3d.ply`，随机生成 100000 点于 `[-1.3,1.3]^3`。不能把“所有数据集都 COLMAP 初始化”写入协议，更不能输入既有训练 Gaussian PLY。[COLMAP loader](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/scene/dataset_readers.py#L220-L271)，[Synthetic loader](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/scene/dataset_readers.py#L274-L350)

DTU/TNT 使用 decoupled appearance 是论文明确设置；C24 用布尔 `--use_decoupled_appearance`，不能传 C26 的整数 `3`。其 L1 由 appearance 网络变换后计算，DSSIM 保持原 RGB 路径。Mip360/Synthetic 不擅自启用该项。3D filter 与 GOF densification 已在真代码中确认：filter 为最小有效相机深度／最高焦距乘 `sqrt(0.2)`，renderer 使用 filtered scale/opacity；densification 从大于 500 开始，每 100 次，到小于 15000，opacity reset 每 3000；依据通常梯度及绝对梯度分位阈值 clone/split，再按 opacity 等剪枝。并非冻结 vanilla 轮廓的小改动。[appearance](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/train.py#L35-L57)，[filter](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/scene/gaussian_model.py#L174-L225)，[GOF densification](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/scene/gaussian_model.py#L663-L747)

**paper → code → data → command → eval 的可运行性边界如下。所有研究命令只作未来模板，本轮未运行。**

| 论文对象 | 源码与数据 | 命令／验证边界 | 输出与单位 |
| --- | --- | --- | --- |
| Table 1 DTU | C24 train／mesh_extract／evaluate_dtu_mesh／dtu_eval；2DGS 预处理 RGB+COLMAP+alpha，另配官方 GT | 下方同期命令有真实入口；环境与数据尚未就绪 | `point_cloud/iteration_30000/point_cloud.ply` → `recon.ply` → `recon_culled.ply` → `recon_aligned.ply` → `vis/results.json`；CD 为 mm，双向均距的平均 |
| Table 2 TNT | C24 renderer 可供后续接合；C25 才有 tetra 入口／eval_tnt | 历史命令可审计，不能直接换 C25 训练；C24-compatible TSDF/tetra/eval 链尚待设计 | F1 为 0–1 无量纲分数，按六场景宏平均；TSDF 与 ♯ 分列，不能乘 100 后直接对表 |
| Table 3 Mip360 | C24 COLMAP loader／train；C25 render.py／metric.py 可作为未来桥接来源 | C24 完整 heldout exporter/evaluator 缺失；协议记录拟用 split 和分辨率，不伪造已跑入口 | PSNR dB、SSIM 无量纲、LPIPS 无量纲；按场景平均后分 outdoor／indoor。C25 使用 VGG LPIPS，不能静默换 AlexNet |
| Table 4 Synthetic | C24 transforms loader／train；完整 train/test 与背景协议 | 与 Table 3 相同的导出评测缺口；保留正则；不能从旧 Lego/Chair checkpoint 起步 | 每场景 PSNR dB 与 8 场景均值；附 RGB/depth/normal 可视化 |

C24 README 的原始 DTU 命令如下；`<...>` 是待填的隔离路径，不是已有产物：

```text
python train.py -s <DTU/scanN> -m <output> -r 2 --use_decoupled_appearance
python mesh_extract.py -s <DTU/scanN> -m <output> -r 2
python evaluate_dtu_mesh.py -s <DTU/scanN> -m <output>
```

未来应明确加 `--DTU <HDD_eval_GT/DTU>`，避免向干净源码树塞 GT；训练命令将显式写明 `--lambda_distortion 100 --lambda_depth_normal 0.05` 或 `5`。full-resolution 用 `-r 1` 的含义取决于真实输入尺寸。`-r -1` 会把超过 1600 宽的输入自动缩到 1600，不能当作“原图分辨率”。[C24 resolution](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/utils/camera_utils.py#L20-L40)

C24 mesh 用所有训练视角的 median depth、alpha≥0.5 与可用 alpha mask，Open3D CPU VoxelBlockGrid 的 voxel 为 `0.002`、block resolution 16、block count 50000、depth scale 1／depth max 8。`0.002` 是输入重建坐标单位，不能未经标定叫作 2 mm。相机／depth rasterization 仍使用 CUDA，所以 mesh 命令不是“纯 CPU 可现在执行”。默认加载目录中最大迭代；`--checkpoint_iterations` 的 parser 是 `nargs='+'`，下游却当标量拼路径，因此显式指定 20k 的原 CLI 有静态类型／路径风险，本轮未修补或试跑。[C24 mesh](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/mesh_extract.py#L20-L107)

DTU evaluator 需 `Calibration/cal18/pos_001...064.txt`，用训练相机对齐官方尺度，执行 mask dilation／可见性裁剪、最大连通分量，再与 `Points/stl/stlNNN_total.ply` 比较，读取 `ObsMask/ObsMaskN_10.mat` 和 `ObsMask/PlaneN.mat`。内部 downsample density 0.2、max distance 20；输出 `mean_d2s`、`mean_s2d`、`overall`，应核验实际结果 JSON 与场景编号，而不只看父进程退出码（`os.system` 返回值未检查）。该 wrapper 自身也用 CUDA。[alignment/CLI](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/evaluate_dtu_mesh.py#L149-L214)，[metric](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/dtu_eval/eval.py#L98-L165)

C25 历史 TNT 命令为 `train.py ... -r 2 --eval --use_decoupled_appearance`、`mesh_extract_tetrahedra.py ... -r 2 --eval`、`eval_tnt/run.py --dataset-dir <GT/Scene> --traj-path <输入预处理COLMAP_SfM.log> --ply-path <output>/recon.ply`。evaluator 的目录必须是单场景，包含 `{Scene}.ply/.json/_COLMAP_SfM.log/_trans.txt`；输入轨迹不能用官方 GT 参考轨迹冒充。评测执行轨迹对齐、GT 配准细化、crop 及 P/R/F1。tau 为 Barn .01、Caterpillar .005、Courthouse .025、Ignatius .003、Meetingroom .01、Truck .005，保留 GT 坐标单位并待数据标定核实，不能擅改单位。[C25 数据与命令](https://github.com/HKUST-SAIL/RaDe-GS/blob/0b1fe5fe2d7655d3bfbd584862788cd449e24ef6/README.md#L57-L104)，[TNT evaluator](https://github.com/HKUST-SAIL/RaDe-GS/blob/0b1fe5fe2d7655d3bfbd584862788cd449e24ef6/eval_tnt/run.py#L58-L195)，[tau](https://github.com/HKUST-SAIL/RaDe-GS/blob/0b1fe5fe2d7655d3bfbd584862788cd449e24ef6/eval_tnt/config.py#L32-L41)

C25/C26 README 写的 `python metrics.py` 与实际文件不符：真实入口是单数 `metric.py`；C24 二者皆无。C25 metric 中 LPIPS 使用 VGG，并把异常打印后吞掉，未来必须核对 test 视图数、`results.json` 与 `per_view.json`，不能以退出码 0 视为评测成功。[C25 metric.py](https://github.com/HKUST-SAIL/RaDe-GS/blob/0b1fe5fe2d7655d3bfbd584862788cd449e24ef6/metric.py#L62-L103)

**数据来源已核对到页面／元数据，尚未下载归档。**

| 数据需求 | 实际来源与访问证据 | 许可／完整性限制 |
| --- | --- | --- |
| DTU 训练 | C24 README → 2DGS → [公开 Drive 文件夹](https://drive.google.com/drive/folders/1SJFgt8qhQomHX55Q4xSvYE2C6-8tFll9)。文件夹 HTTP 200，真实列表有 `dtu.tar.gz`（显示 3.32 GB；文件 ID `1ODiOu72tAGPTnhVn0cFZ9MvymDgcoHxQ`），勿误取 `dtu_results.zip`。2DGS README 说明 mask 在 alpha 通道 | 归档未打开，尚未实证包内场景数／分辨率／所有 calibration；未发现独立归档许可证，不能把代码许可证转授数据 |
| DTU GT／校准／可见性 | [DTU 官方页](https://roboimagedata.compute.dtu.dk/?page_id=36) 的 Points.zip 与 SampleSet.zip，HEAD 均 200；实际 Content-Length 分别 6,966,262,016 与 6,905,656,531 bytes。SampleSet 含校准／mask／评测资料，因此仅下载 Points 不够 | 页面称 freely available 并要求引用；不下载全部 Cleaned 136 GB／Rectified 123 GB 等无关包；归档级许可与文件清单后阶段核验 |
| TNT 预处理 | C25 README → [GOF HuggingFace 数据](https://huggingface.co/datasets/ZehaoYu/gaussian-opacity-fields/tree/0c977df91a2cf3a456ee4e84036893a9fd9979aa)，`TNT_GOF.zip` 8,004,621,817 bytes，public 且 gated=false；发布时间 2024-04-25，LFS SHA 已记入 JSON | 这是历史作者数据指针，不是 C24 发布了 TNT 配方的证据。HF 列表没有独立 data card/license；保留原 TNT 条件 |
| TNT GT／poses／alignments／crop | [官方 download 页面](https://www.tanksandtemples.org/download/) 已实际解析六场景全部 GT、camera poses、alignment、crop 链接，见 [六场景链接表](evidence/web/tnt_scene_links.json) | 页面公开，不等于每个大文件都已验证可下载；本轮没有逐个获取 GT 包、注册或绕过访问限制 |
| Mip-NeRF360 | [作者项目页](https://jonbarron.info/mipnerf360/) 的 `360_v2.zip`、`360_extra_scenes.zip`，HEAD 均 200；分别 12,535,427,936 与 4,488,140,217 bytes | 未读归档内文件；不能把 MultiNeRF 的 Apache2.0 代码许可自动当数据许可 |
| Synthetic NeRF | [原作者公开 Drive](https://drive.google.com/drive/folders/1cK3UDIJqKAAm7zyrxRYVFJ0BRMgrwhh4)，HTTP 200，实际可见 `nerf_synthetic.zip` | 归档未下载；代码 MIT 不证明全部渲染资产的数据许可；完整 split／文件数待获取后核验 |

TNT [当前许可页](https://www.tanksandtemples.org/license/) 同时写有 CC BY 4.0 与限制非商业研究／第三方再分发的 License Grant，正文存在不一致；本轮忠实记录，不宣称无限制再分发，也不替用户接受额外条款。当前公开页面／HEAD/API 没出现需要绕过的访问阻挡；这只说明元数据可访问，Drive 大文件配额、确认页、GT 每文件可用性仍未测试。详见 [访问探针](evidence/web/data_access_probes.json)。

**几何 GT 仅用于 evaluation。** DTU STL、TNT laser clouds、官方评测配准／crop 不进入训练初始化或 loss；训练使用 RGB 与相机、COLMAP sparse 初始化以及预测深度／法线正则。DTU 提供的图像 alpha mask 用于官方 mesh/culling 流程，不能冒称深度／法线监督。Synthetic test RGB 仅用于 heldout 评价。v2 没有 Objaverse GT 深度／法线数值表，不把 C26 geometry_metric.py 加入 v2 主结果。

**现有本机数据经过文件数、header 和小 schema 核验。** 初步扫描只在两个允许根内进行，最大深度 4，共访问 2101 个目录；随后沿实际证据对 `tier1/data/realcap`、现有 training 子集、transport 做有限深度定向核查，不做全盘递归，不读取 oldrefs 或他人目录。四个明确的 train 软链接只跟随到本人的 cglib train 文件夹，未遍历其父目录或 val/test 兄弟目录。所有“未找到”只指这个明示范围，不代表全机不存在。

| 实际路径／类型 | 实际检查结果 | 复现用途判定 |
| --- | --- | --- |
| `.../tier1/data/realcap/tandt/truck` | 251 JPEG，全部 979×546 RGB；251 条 COLMAP images 记录，全部文件名可解析；1 个 PINHOLE camera，记录 1957×1091；sparse point header 为 136029 | 真实 RGB+camera+sparse，且 Truck 是论文成员。图像已缩小但相机尺寸不同，需核对处理／内参缩放；未找到 Truck.ply/.json/_COLMAP_SfM.log/_trans.txt，不能认定 GOF 预处理或完整几何评测已就绪 |
| `.../tier1/data/realcap/tandt/train` | 301 JPEG，980×545；301 registered images；相机 1959×1090；sparse 182686 | 是真实数据，但 Train 不在 v2 Table 2 六场景中 |
| `.../tier1/data/realcap/db/playroom` | 225 JPEG，1264×832；225 registered images；sparse 37005 | Deep Blending，排除 v2 定量 suite |
| `.../tier1/data/realcap/db/drjohnson` | 263 JPEG，1332×876；263 registered images；sparse 80861 | Deep Blending，排除 v2 定量 suite |
| `.../hybrid_raster_trained_models_v1/out/hybrid_raster_trained_models_v1/training/{hotdog,materials,mic,ship}/seed_1729/data` | 每场景 100 个 train PNG，全部 800×800、8-bit RGBA；transforms_train 各 100 帧，矩阵均 4×4；Materials FoV 0.6194058657，其他三者 0.6911112070；无 val/test JSON；train 是指向本人源数据的软链接 | 可确认 train-only 归档子集，不能称完整 Synthetic benchmark。按只读素材对待；文件模式并非全部只读，也未将其误写成 OS 强制 readonly |
| 同一四场景的 `checkpoints/point_cloud/iteration_30000/point_cloud.ply` | 只读取 PLY header；vertex 分别 148610／282537／311562／320284；具有已训练 Gaussian 属性 | 既有 vanilla checkpoint；不是新 RaDe 从头训练结果，也不是 GT／raw RGB |
| `tier1/out/2dgs_{lego,chair,ship,truck}` | 保存现有 PLY header／属性 schema；二维 surfel 的尺度字段不等于 RaDe 3D Gaussian | 不复用作 RaDe 初始化，也不把旧 Lego/Chair 模型计为论文复现 |
| HDD `.../transport/raw/{materials,mic,ship}` | 定向目录证据为 `native.npz`、`camera.json`、checkpoint qualification／seal，配套 frames/media 是派生渲染／线条产物 | “raw” 目录名不等于训练原始数据；不代替 RGB/camera/GT suite |

逐场景 38 项目标状态（Mip9 为候选）、实际路径、图片 header 全量尺寸直方图、COLMAP 数目、小 schema、PLY header、缺失状态见 [DATA_INVENTORY.json](DATA_INVENTORY.json) 和 [实际元数据证据](evidence/local_metadata.json)。DTU15、其他 TNT5、Mip3609 在本次范围内未找到完整输入；其官方 GT 也未就绪。Lego/Chair 等旧文档指向本人 cglib 源路径，只作为线索，没有在本轮越过定向范围检查完整源包，因此不宣称其齐全或全机缺失。大型文件 hash、像素完整性／相机数值一致性、完整 archive manifest 均留待获准后阶段。

**环境检查全部只读，没有 import torch 或加载 native extension。** 通过 Python 版本命令、distribution 元数据、torch/version.py 文本及 `.so` 路径取得证据，不能据此宣称 ABI 可用或 CUDA 已验证。详见 [环境快照](evidence/environment_snapshot.json) 与 [包和扩展位置](evidence/python_packages.json)。

| 项目 | 实际观察 | 后续影响 |
| --- | --- | --- |
| shell 默认 Python | `/home/u00134/bin/miniconda3/bin/python3`，3.13.13 | 不是 C24 README 的 Python3.9 |
| 已有 vfsdgs／scgs | Python3.9.25、torch2.3.1+cu121、torchvision0.18.1+cu121、numpy1.23.5；vfsdgs 有 scipy/sklearn/trimesh 等，扫描未见 Open3D distribution | 仅作依赖候选证据，不修改、不继承其共享 rasterizer 作为 C24 |
| 已有 ts_diffusion | Python3.10.20、torch2.5.1+cu124 | 非 C24 历史环境；不采用 |
| native extensions | vfsdgs 的 `.../site-packages/diff_gaussian_rasterization/_C.cpython-39-x86_64-linux-gnu.so` 和 simple_knn `.so` 实在；scgs 亦有 | 同名模块不证明同源码／ABI；未来新 env 内从 C24 编译并记录路径／hash |
| CUDA／compiler | driver560.35.05，`/usr/local/cuda-12.6/bin/nvcc` 为 12.6.85；gcc/g++13.3、glibc2.39；PATH 未找到 nvcc/cmake；标准 gcc11/12 路径未发现 | 与 torch cu121 的 toolkit 不同；未构建验证兼容性。未来把 toolkit／compiler 放隔离 HDD，不能替换共享 binary |
| 空间／内存 | root 约 50 GiB 可用、95% 已用；HDD 约 2.9 TiB 可用；内存 502 GiB，总体 available 195 GiB；swap 已近满 | 大数据、env、cache、构建、模型与临时文件全部在 HDD；这是瞬时系统观察，不是可独占预算 |
| GPU | 两张 RTX A6000，每张 49140 MiB；快照占用约 10052／24409 MiB，既存 compute PID 共 54 个，comm 均为 python | 用户已告知为他人作业；本轮未查询 owner／命令行、未干预。即便 utilization=0 也不算独占空闲 |

隔离预案写入 protocol：新 prefix 为 `<HDD>/envs/c24_py39`，pip/conda/torch_extensions/tmp 都在 HDD；Python3.9/cu121 是同期 README 证据，torch2.3.1 是现机可见的候选版本，**不是作者已发布的精确 lock**。上游 requirements 没有版本固定，也未完整列出评测的 scipy/sklearn/matplotlib/Pillow 等依赖；须后阶段冻结兼容版本和 native build provenance。未来任何 CUDA import、训练、render、mesh、CUDA culling、LPIPS 评测前，都必须重新检查并取得独占空闲 GPU，不能因剩余显存足够与既存任务重叠。[C24 安装说明](https://github.com/HKUST-SAIL/RaDe-GS/blob/2d4bc087f1b4bd62c96054fbe89d273490526b81/README.md#L16-L33)

**预算仅为有出处的工程估算。** 公开 archive HEAD/API 已知 DTU GT+Sample 约 13.87 GB、TNT_GOF 8.00 GB、Mip 两包 17.02 GB，此外还有 DTU 训练包、Synthetic、TNT GT、解压与中间产物。建议先暂留 HDD 250–500 GiB，再据实际获取清单和 pilot 调整；这是规划余量，不是作者存储需求或实测使用量。C24 TSDF 的两个 float32 属性按容量计算为 `50000×16³×2×4 = 1,638,400,000 bytes`，不包括 hash、mesh、depth/color 列表及其他内存，不是实测峰值。

若 Mip 完整 9 场景且每种参数策略独立执行，则基础 38 个 30k 场景，加 DTU15 full30k、DTU15 独立20k，共估算 68 次训练／参数策略；双策略最多按 136 次规划，TNT 两种提取可复用同一训练模型。20k 的独立训练定义仍待裁定。论文 H800 时间为 DTU half20k 5.0 min、half30k 8.3 min、full 20.2 min，TNT 11.5 min／scene；这些只是作者已发表参考值。本机是 A6000，未获准测 throughput，因此 **A6000 用时估计为空，不以 H800 倍乘虚构排期或“已复现速度”**。[v2 Table 1–2](https://arxiv.org/pdf/2406.01467v2#page=7)

**后续执行协议是草案，尚未授权。** [REPRODUCTION_PROTOCOL_DRAFT.json](REPRODUCTION_PROTOCOL_DRAFT.json) 逐阶段给出输入、命令模板、预期产物和门槛，明确未执行状态：先裁定参数／源码桥接／split 等分歧，再获取冻结数据与隔离环境，之后才可能进行获准的构建与独占 GPU smoke、scan24 从头训练、深度法线导出、mesh 与 GT 评价，最后扩展完整 suite。scan24 是明确的论文成员，建议作为首个完整链路的代表场景；本阶段不要求用户现在选场景，也不缩小最终完整 suite 目标。

待用户裁定的问题集中为四项：D1（5 与 .05 的分列策略）、D2（论文公式与 C24 实现差别如何标注，是否另行实现字面式）、D3（C24 缺失的 TNT/tetra/NVS 链如何做可审查来源固定的补全）、D4（20k schedule、Mip 场景/分辨率、TNT split、Synthetic 背景等作者未明示设置）。现阶段不能直接启动 step2，更不能把 C25/C26 的新训练法当作补全快捷路径。

本轮结果由实际 PDF 获取、git HEAD/tree/gitlinks、源码行证据、公开页面/HEAD 元数据以及本机文件 header/schema 支撑。最终校验仅检查文档与 JSON、相对链接、源码固定状态和工作树变更范围；不运行数值检查。等待父 agent 核验及用户下一步，保持 `scientificdone=false`。
