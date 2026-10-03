# 独立库存与阻塞复核

结论为 **BLOCKER_CONFIRMED**，不是实验 PASS、NO_GO 或科学效果结论。hotdog、materials、mic、ship 的 TRAIN 元数据均存在、各有 100 个索引相机，所请求的 8 F 与 8 C 索引均可用。库存没有可用的新 frozen vanilla 3DGS checkpoint。ship 的三个候选为 2DGS：独立复读 checkpoint 头部并核对整文件 SHA256，均缺少 vanilla 所需的 `scale_2`，不能作为本实验模型替换。其他三个场景无 checkpoint 候选。

可执行核验器只使用 Python 标准库，未调用渲染器、GPU、图像解码器或训练代码。它独立重算既有 LOCK 的字节 SHA256、canonical lock hash、parameter hash、recipe hash，并对照锁内六个科学源码的 hash，确认 prior worktree 与本 worktree 均一致。同时核对 manifest 所链接库存的实际路径与 SHA256，并核对继承 LOCK 副本、manifest 声明 hash 和 prior 原锁字节 hash 完全一致。新 manifest 的 selected_scenes 与 scenes 为空、expected_production_frames 为零、F/C 列表完全一致。新输出与新 artifact 目录未发现生产图像、raw 字段、视频或 frame seal。缺少输入时不生成占位帧或假 seal。

核验库存缺失的外部范围以 `inventory/INVENTORY_DISCOVERY.json` 声明的有界搜索为准，不声称遍历整个主机或证明未登记目录绝无模型。独立核验复读了四份 TRAIN 元数据和三个已登记 candidate checkpoint，并以同样 root/depth/prune/匹配规则独立重扫已登记六个根的文件名集合；69 个匹配路径与冻结库存完全相同。四个 canonical 预期 checkpoint 路径经独立 stat 仍不存在；不重复全 home 爬取，不读取新增候选内容。任何漏报/新增候选或路径消失都会以 UNDETERMINED 拒绝。没有进行 native calibration、49 帧/scene 生产、same-state A/B/C/AUTHOR 原始字段检查、全分辨率图像评价、视频完整解码或人工评价。这些步骤均是未执行，不得用零计数视为通过。

关于用户所称原 assets manifest：当前、prior、tier1、cglib 与 3dgs_line 的指定可见根下未找到名为 `configs/` 的目录或明确字面命名的 assets manifest。已读并交叉核对明确的资产输入来源 `out/point_feature_foundation/input_manifest.json`、`out/multiscene_foundation/input_hashes.json`，以及覆盖广泛产物的 `out/multiscene_foundation/MANIFEST.json`；这三者不虚称为同一指定文件。`src/common.py` 指向旧 vanilla 资产路径 `/home/u00134/cglib/outputs/{scene}_static/point_cloud.ply`；原 `artifacts/direct_curve_global_fit_probe/INPUTS.json` 只覆盖排除的四个旧场景。对 bcr 与 FeatureLineRendering 的排除 out/test/mesh 的定向文件名搜索也未发现另一个 assets manifest。

新增支持代码有真实行为 RED → GREEN：初版未检查阻塞条件，8 项 fixture 中 7 项测试触发共 10 个失败（包括4个子用例），实施验证后 8 项全绿。初次 import 缺失也单独保留，不把它冒充行为 RED。随后独立复核补强产生第二组真实 RED → GREEN：增加4个针对 manifest hash 链、继承 LOCK 副本变动、未登记新 candidate 与 canonical checkpoint 突然出现的 fixture；RED 12项中4项失败，GREEN 12项全部通过。测试证明 eligible checkpoint、缺失场景、伪 selected scene、伪生产文件/seal、变动源代码/锁参数和变动相机分组均会拒绝。

`logs/VERIFIER_FINAL_OPEN.trace` 记录的最终独立核验进程共 1236 次成功 open（含受限目录枚举）；未成功打开 TEST/mesh、VAL 元数据、图像或视频文件。该结论仅覆盖这一被 strace 记录的进程及其子进程，不扩张为全会话系统调用证明。独立代理没有运行 GPU 任务，没有打开 TEST/mesh 数据，没有查看结果图，没有修改外部文件，没有 commit/push。

复现命令（工作目录为本 worktree）：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s artifacts/hybrid_raster_extra_models_v1/independent_review -p test_verify_blocker.py
PYTHONDONTWRITEBYTECODE=1 strace -f -e trace=open,openat,openat2 -o artifacts/hybrid_raster_extra_models_v1/independent_review/logs/VERIFIER_FINAL_OPEN.trace python artifacts/hybrid_raster_extra_models_v1/independent_review/verify_blocker.py --root /home/u00134/3dgs_line/hybrid_raster_extra_models_v1 --inventory artifacts/hybrid_raster_extra_models_v1/inventory/INVENTORY_DISCOVERY.json --manifest artifacts/hybrid_raster_extra_models_v1/INPUTS.json --output artifacts/hybrid_raster_extra_models_v1/independent_review/VERIFICATION.json
```

若将来获得兼容 checkpoint，必须重新登记库存与相机 manifest 并重新冻结；本零场景核验器会拒绝将新增生产文件归入当前阻塞状态，不能作为真正生产验收器。
