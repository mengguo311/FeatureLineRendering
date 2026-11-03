# 完整scan65线高斯模型：逐组中心收拢

## 先看结果
`FULL_MODEL_BEFORE_AFTER.png`：两行是0012、0036原相机；左原版，右全模型POSITION_ONLY。每张原生图777×581，没有挑选ROI代替全景。
`VIEW_0012_ALL_QUADRANTS_2X.png`、`VIEW_0036_ALL_QUADRANTS_2X.png`：完整四区均覆盖的2倍最近邻显示，仅放大显示，不改变科学像素。

**实际整体视觉收益有限。** 颅骨轮廓、主要线网保留，局部线束更集中/平顺；密集重复线、交叉与细碎线仍在，不能称为全模型已变成干净单线。最大位移组238627的原有局部拐折被平滑，是必须保留的形状风险。

## 真正可用的完整资产
- `unit/FULL_POSITION_ONLY_GAUSSIANS.npz`：处理后的完整279616核，不是596核局部子集。
- `unit/ORIGINAL_GAUSSIANS.npz`：完整canonical原字节备份，用于回退。
- `unit/MEMBERSHIP.npz`：完整原映射，包含稳定line_kernel_id和edge_id，全部身份字段冻结。
- `unit/GROUP_INDEX.npz`、`GROUP_LEDGER.json`、`group_journal/`：全部3655组的原行集、共同3D拟合模型、状态和紧凑检查点。
- `unit/UPDATED_ROWS.npz`：实际变更原行ID、归属、前后中心与位移。
- `unit/source_snapshot/`、`CONFIG.json`、`DECISION.json`、`RUN_REQUEST.json`：冻结数学/源码/配置与真实Astra评审。

加载示例：
```python
import numpy as np
with np.load('unit/FULL_POSITION_ONLY_GAUSSIANS.npz', allow_pickle=False) as z:
    model = {k: z[k] for k in z.files}
with np.load('unit/MEMBERSHIP.npz', allow_pickle=False) as z:
    membership = {k: z[k] for k in z.files}
# model['means'], model['covariance'], model['opacity'], model['colors']
# membership['line_kernel_id'] 是原行ID，membership['edge_id'] 是原归属。
```
NPZ跨平台读取只需NumPy。原生产CLI和真实CPU Gaussian EWA重渲染依赖记录的服务器Linux环境/旧冻结helper绝对路径；此包不是已经验证的通用GUI或跨平台渲染器安装包。

## 精确范围
- 所有3655个既有edge_id组都已处理，覆盖127152个assigned核；成功3655，数值跳过/失败/未运行均0。
- 实际126477个中心改变，675个重算后原值不变。
- 152464个UNKNOWN核原样保留，既不删除/隐藏，也没有将它们强行合为一组。
- 全部279616核保留；协方差、opacity、颜色、primitive_id、internal_piece_id、arc_t逐位不变；原行序和所有成员映射不变。
- 这一轮是固定既有分组内几何收拢，不新增归属、不跨组再合并。不同edge_id中的重复线仍可能并存。
- 采用前次较连续的POSITION_ONLY，未采用前次有串珠的协方差/横宽规整；30579结果与前次保存副本逐位一致。

## 位移与视觉边界
全部assigned位移中位0.079273p、95%分位0.381080p、最大2.996954p；p=0.001725801957946726为原场景采样尺度，不是像素或米。
0012画内/前向assigned中心的投影位移中位0.0625px，0036为0.0583px，因此“很多核改变”不意味着肉眼全景大幅改善；该投影统计不是表面可见性认证。
相同完整3D派生资产用于两个相机。真实Gaussian CPU EWA出图，无辅助曲线墨、2D描线或源表面遮挡删核；不是本次CUDA运行。固定有限域无外推中心；几何正则化不等于恢复真实物理边，未认证held-out/时间稳定性/逐组尖角保真。原controls/arc_t仅是来源元数据，不是派生中心仍由旧controls产生的证明。

## 验证记录
真实父持有数值进程EXIT=0。新适配的1项真实vertical RED/GREEN及7项后续小型回归通过，后者不冒称都经过独立test-first。
`acceptance/` 保存父级全行属性、全部分组数学重放、原生Gaussian图与固定裁剪重放、视觉边界及保护记录；`parent_scripts/verify_full_model_zip.py` 可对实际ZIP成员重新冷载核验；与ZIP并列保存的 `PACKAGE_VERIFICATION.json` 记录最终容器SHA和真实冷载结果。
原版、v11及历史成果保留，新分支line-kernel-full-bundle-collapse-v12；没有push/merge、GPU、训练或安装。
