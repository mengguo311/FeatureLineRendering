# 复现与断点续跑

工作目录为 `/home/u00134/3dgs_line/gaer_multiview_contour_regions_v01`。原模型及历史树只读，不安装软件，不训练。所有派生文件仅写本 stage 的 experiments/artifacts/out 三处。Python 固定 `/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python`；CPU affinity 与 BLAS/OpenMP 为两个线程；无 Python bytecode cache。原模型路径、SHA256、86 条相机 metadata、构建/开发/保留名单均在 `INPUT_FREEZE.json`。

本轮 GPU0 存在外部用户进程，整轮使用经过已有 CUDA-native 缓存校准的 CPU replica。它不是重新运行原 CUDA renderer。原始 SH3、opacity、covariance、tile、深度排序、alpha/T 接收阈值及 full-N feature forward/adjoint 保留；无 top-K。构建仅编译新 stage 自有 C++ CPU rasterizer，不覆盖旧库。编译 flags、源码与二进制 SHA 在 `out/.../cpu_native/BUILD.json` 及 `MESH_RASTER_BUILD.json`。

```bash
cd /home/u00134/3dgs_line/gaer_multiview_contour_regions_v01
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/test_cpu_native.py --calibrate
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s experiments/gaer_multiview_contour_regions_v01 -p 'test_*.py'
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/hydrate_render_cache.py
bash experiments/gaer_multiview_contour_regions_v01/runner.sh all
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/verify_artifacts.py
```

`runner.sh all` 在一个独立生产进程内完成 `extract → fuse → develop → seal → eval → arc`，不需要代理逐单元发起。每一阶段分别尝试 Lego 和 Chair，单场景失败不会阻止另一场景；失败写入 `logs/failures.jsonl`，执行失败标 INVALID_EXECUTION 而非科学 NO_GO。每个视角、fusion arm、区域宽度、开发选择、固定资产、保留评估、arc frame 和视频均有完成 seal。只有 seal 的全部文件 SHA 与当前核心方法 SHA 都通过才跳过；代码变更会拒绝沿用旧产物，不静默复用。中断后再次运行相同命令继续。

Git 不包含138个可重建 `out/.../renders` RGB/alpha 缓存，但原 seal 记录其 hash。新 checkout 首次续跑/完整审计前，先运行上面的 `hydrate_render_cache.py`：只恢复缺失缓存，使用冻结 CPU/CPP 源码、原相机和原模型，精确匹配 seal SHA 后才无覆盖原子放回；已有不匹配文件会拒绝，不重写 seal。Lego r_7 已在独立临时目录实际重渲染并通过字节级 hash 核验，证据为 `results/CACHE_REHYDRATION_AUDIT.json` 和 `tdd/cache_rehydration_verify_one.log`。可用 `--verify-one lego:r_7` 复查该确定性。这不改变任何选择、几何或科学评价。直接打开GLB/OBJ/离线viewer和视频不需要恢复缓存或访问原GS。

也可以单独运行：

```bash
bash experiments/gaer_multiview_contour_regions_v01/runner.sh extract lego chair
bash experiments/gaer_multiview_contour_regions_v01/runner.sh fuse lego chair
bash experiments/gaer_multiview_contour_regions_v01/runner.sh develop lego chair
bash experiments/gaer_multiview_contour_regions_v01/runner.sh seal lego chair
bash experiments/gaer_multiview_contour_regions_v01/runner.sh eval lego chair
bash experiments/gaer_multiview_contour_regions_v01/runner.sh arc lego chair
```

`freeze.py` 只在没有本轮 INPUT_FREEZE 时从旧冻结文件/metadata 生成划分；已经交付的划分不得重写。`protocol.py` 在新来源提取前冻结参数；研究/代码修正历史写在研究审阅与 TDD 日志，不在结果后救门槛。候选宽度固定 `.4/.8/1.2` voxel，唯一选择只用四个 DEV。八 reserved 和33arc仅投影已封印资产。

`assets/{lego,chair}/multi24/outer.glb`、`outer.obj`、`outer.npz` 是主实体三角面；`assets/{scene}/viewer_3d.html` 无服务器/外链，直接用支持 WebGL2 的浏览器打开，拖动旋转、滚轮缩放、切换四臂。viewer 和全部实际图只使用资产自身 z-buffer，相对原不透明物体仍为 x-ray。没有逐视角隐藏 mask，也没有上线重新拟合。关闭内部细节无需操作：本轮没有构建 RGB 内部纹理层，主层包含 native alpha 的孔洞边界。

数据索引：`sources/` 保存每相机原 ID、质量和完整投影足迹；`fusion/` 保存逐源质量、soft score、distinct views、hysteresis 与 kernel-support PLY；`regions/` 保存顶点真实 raw-voxel owner、最近中心诊断、原 covariance 位移、有效各向异性轴长、fill witness CSR、背景 veto 和 merge 候选；`results/` 保存所有计数与评价；`media/` 保存原尺寸图、保留图板、自动错误/负空间裁剪及完整视频。`out/` 为 ignored 的可重建 RGB/alpha 缓存与 CPU 共享库。

视频均为 33 个冻结相机的完整固定资产投影，H264 / yuv420p / +faststart。每个 manifest 保存实际 camera、camera SHA、恒定 geometry SHA、原 PNG SHA 与完整解码的帧 SHA；坏帧不会剔除。`verify_artifacts.py` 再独立解析 GLB/OBJ、核对来源、重解码视频并核对旧树/模型/历史分支哈希。

主协议后的独立诊断和报告可分别运行：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/supplemental_analysis.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/matched_ink_audit.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/verify_artifacts.py
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_multiview_contour_regions_v01/report.py
```

追加墨量诊断只对旧 A 图的世界半径做 DEV 均值匹配，严格标为 post-protocol，不覆盖主四臂和半径上限。reserved 已由主实验读取，不再称新盲测。报告读取独立视觉评审后的 `SCIENTIFIC_VERDICT.json`，不会以 exit0 或 coverage 自动生成 GO。

保留的工程问题：主 thin/widened 的 geometry hash 在导出前使用 int64 面索引，导出 NPZ/GLB 为 int32。原记录未覆盖；审计精确验证数值几何不变、GLB/OBJ/NPZ一致以及 int64 回转 hash 匹配，记录 `HASH_SCHEMA_PREEXPORT_INT64`。主 multi24/two_source 及主视频使用 int32，直接 hash 匹配。追加诊断统一 float32 vertices / int32 faces。不能盲目比较不同 dtype 的字节 hash 后宣称几何变化。

离线 viewer 内嵌全部几何，采用原世界坐标（Z-up）；JavaScript 语法及内嵌几何已静态核验。当前环境没有浏览器，实际拖动交互没有浏览器验收，不能把静态检查描述成完整 UI 测试。内部纹理层为 NOT_RUN。

资源门槛为 root≥4GiB、sharedGit≥1.5GiB、stage<6GiB；生产1GiB守卫未改。后台启动方式受宿主终端生命周期影响，建议从用户自己的长期会话运行同一 `runner.sh all`；所有有效完成单元均可断点续跑。模型或网络中断不影响已封印文件。
