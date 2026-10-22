Chair 的人工 region 4 已有真实的原高斯行号关联与局部改色诊断。代码只使用 CPU；原始 PLY、完整 SH3、几何及旧资产保持不变。科学范围为 `UNCERTIFIED_CPU_MAPPING`，不是原生 CUDA 逐核认证、物理附着或原生高斯排线。

本单元数据：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_001`。详细结果见该目录的 `REPORT_ZH.md`、`STATUS.json` 和 `NEXT.json`。

冷启动重放实际原 GS 改色（输出目录必须尚不存在）：

```bash
experiments/partwise_sketch_hatching_v05/run.sh replay \
  --unit /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_001 \
  --view orbit_223_28_4.9 \
  --output /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/replays/chair_new
```

读取一个已保存笔触段的中点锚，并导出全部被原渲染器接受的原高斯 ID／alpha*T 权重，包括深度不合格的记录：

```bash
experiments/partwise_sketch_hatching_v05/run.sh query \
  --unit /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_001 \
  --view orbit_0_65_4.7 --segment-index 0 \
  --output /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/queries/chair_anchor_new
```

`replay --arm nearest_proxy` 或 `--arm shuffled` 重放相同 BUILD 图像变化预算下的控制。保存的操作在原完整 SH3 计算后，对每个原核颜色进行混合；高阶视角外观保留在未替换比例中。每个相机都重新进行原 GS 的前向合成，非图像蒙版涂色。`replay` 对本单元已有评估相机逐数组核验。

数据契约：

| 文件 | 含义 |
|---|---|
| `results/SOURCE_BINDING.npz` | 全部原始 PLY 行；6通道权重分布（0=UNKNOWN，1–5=代理区域）；暴露、冲突、未知、逐视图分数及输入锁 |
| `results/EDIT_SELECTION.npz` | 同一原行序的三个控制强度、蓝色目标、原PLY SHA；不包含新检查点 |
| `results/SELECTED_SOURCE_IDS.csv` | region 4 被支持的原行号、软权重、暴露量、视图数、编辑强度 |
| `results/<view>/trace.npz` | 完整模型在固定样点接受的原ID、局部遍历ID、alpha、T、weight、协方差平面深度；无 top-K |
| `results/<view>/path_support.npz` | 256个固定段中点、120个stroke ID、face/bary、投影／可见状态及CSR原核列表；UNKNOWN不删除 |
| `results/<view>/baseline.npz` | 原始完整 GS；`contribution` 使用完整模型原透射率 |
| `results/<view>/linked_edit.npz` | 原核颜色副本的完整对象重渲染 |
| `selected_only_recomputed_T.*` | 仅显示被选核，透射率重新计算；不能解释为完整模型贡献图 |
| `source_snapshot/` | 预评估冻结代码；`delivery_source/`另含查询、冷重放与交付工具 |

四个 BUILD 视点与三个评估视点在首次运行前冻结。43°评估视点历史已曝光；评估相机只对本次关联保留，不是底层GS训练的盲测声明。同代理区域掩码只能评价作者意图的一致性。

重建本单元实验需在新的输出目录使用冻结的 `PROTOCOL.json`、`PROTOCOL_LOCK.json` 和 `source_snapshot/`，再运行冻结 `run_unit.py --unit 新目录`；新目录位于v05输出根内，且不能已有 `results/`。这些协议固定 Chair unit001，不宣称通用多对象绑定产品。原PLY、只读解释器及依赖位于本机既有路径；未打包原模型或Python环境。

全程两核亲和、数值线程1、CUDA禁用。没有界面工作、训练、增密、剪枝、重排行、写原PLY、push或merge。
