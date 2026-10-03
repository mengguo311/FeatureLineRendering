# 固定 Gaussian 边缘贡献资产：字段与使用说明

本资产回答“哪些原始 Gaussian 在给定渲染配方下参与独立二维边缘证据的形成”。分数不是几何边缘真值、类别概率或重建曲线。Gaussian 行 ID 固定，但其可见性、贡献强度和图像覆盖范围随视角变化。

## 文件与命名空间

工作区根为 `/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1`。下述路径相对此根目录。

| 文件 | 含义 |
|---|---|
| `out/gaussian_edge_attribution_v1/{scene}/assets/scores.npz` | 完整逐 ID 资产，含逐 F 数组；原始资产封存后 C/arc 不得修改 |
| 同目录 `selection.npz` | 每个预声明方法、类别、档位的原始 ID 列表 |
| 同目录 `ASSET.json` | checkpoint、配置、核心与驱动代码 SHA、F 清单、类别解释、计数、逐数组 shape/dtype |
| 同目录 `NORMALIZATION.json` | Mic F 学得的独立证据尺度；Materials 原样继承 |
| 同目录 `ASSET_SEAL.json` | 同目录文件逐项 SHA256 与上下文；这是完整源资产的封条 |
| `artifacts/gaussian_edge_attribution_v1/assets/{scene}/scores.npz` | 便于版本控制的紧凑资产：去除 `perview_*`，增加 `support_class_bits` |
| 紧凑目录 `PACKAGE.json` | 紧凑文件 SHA、完整源资产路径/散列、类别位编码及 checkpoint 命名空间 |
| 紧凑目录 `SOURCE_ASSET_SEAL.json` | 源资产封条副本；其 `scores.npz` 散列对应完整源文件，不能直接用于紧凑文件校验 |

`scene` 为 `mic` 或 `materials`；两者 checkpoint 不同，ID 不能混用。每个 ID 是原 PLY 的**零基 vertex 行号**，不是重新编号，也不是空间排序。以 `ASSET.json.identity_namespace`／`PACKAGE.json.original_PLY_namespace` 的 checkpoint SHA256 连同 ID 标识一个核。

## 基础公式与可靠性

记 F 视图为 v，像素为 p，原核为 i，缓存保留集合为 K(v,p)。原始贡献权重是 `w_vi(p)=alpha_i(p)·T_i(p)`，其中 T 包含原完整模型在该核前方的全部透射衰减。只使用原始权重，**不除以 top4 权重和**。

对于独立证据类别 c：

```text
N_vic = Σ_p 1[i∈K(v,p)] · w_vi(p) · E_vc(p)
D_vi  = Σ_p 1[i∈K(v,p)] · w_vi(p)
M_v   = Σ_i D_vi
baseline_c     = [Σ_v N_vic/M_v] / [Σ_v D_vi/M_v]
baseline_raw_c = [Σ_v N_vic] / [Σ_v D_vi]
```

分母覆盖整个 native800 缓存网格，包含可见非边缘像素；不是仅在边缘像素累积。按 M_v 同除分子、分母，使各视图的总可见贡献具有同等影响。缓存只有 top4，因此两种估计都标为 **TOP4-TRUNCATED**。分数高说明在所观测贡献中证据比例高，不表示该核主要位于几何边界。

零分母数值存为 0，并由 `unknown=True` 区分；它不是反证。`eligible=(raw_denominator>=1) & (support_view_count>=2)`；单 F1 对照仅将视图数门槛改为 1。已见但未满足可靠性门槛为 `unreliable`。原连续分数全部保留，主属性投影用 `projection_*` 在不可靠 ID 上弃权归零。

## 独立证据与双侧来源

固定类别顺序为 `[color, geometry, outline, union]`。

| 类别 | 独立证据及限定 |
|---|---|
| `color` | RGB 三通道连续梯度结构张量的最大特征方向和幅度；alpha≥0.5，内部腐蚀 2 像素；颜色边界不等于几何边界 |
| `geometry` | 正中值深度的 log 值经带有效区的归一化 Gaussian 平滑，再求 Gaussian 梯度；有效内部区与前者一致；只是渲染深度证据，无表面 GT |
| `outline` | alpha 的连续梯度，限 alpha≥0.08 的前景；视角相关轮廓，不建立固定几何边缘身份 |
| `union` | 逐像素前三类独立证据的最大值 |

平滑 sigma=1，沿各自独立方向做 NMS。尺度是 Mic 八个 F 中有效区内正梯度幅度的合并 P99，随后幅度除尺度、clip 到 `[0,1]` 并乘 NMS。尺度池在 NMS 前形成。C、arc 和 Materials 不重估全局尺度。主证据提取不读取 Gaussian ID。

双侧使用独立梯度方向的 ±2、±4 像素，原始权重的 weighted Jaccard 对重复 ID 合并后比较：

```text
J = Σ_i min(w_left,i, w_right,i) / Σ_i max(w_left,i, w_right,i)
relative_depth = |z_left-z_right| / max(z_left,z_right)
amplitude = E_center × 0.5 × [1-J + clip(relative_depth/0.02,0,1)]
enhanced_c = 0.5 × baseline_c + 0.5 × side_c
```

深度差仅在两侧都存在有效前景深度时计算。没有独立 E 就没有双侧沉积，ID 切换本身不会生成几何证据。每侧只向**缓存 topK 内最近深度 1% 容差**的核沉积；不能据此认定它是整条光线真正最前面的层。轮廓只沉积到 alpha 较高的前景侧，相等时两侧均可。目标位置碰撞每偏移取 max，两个偏移平均，因此逐核 side 分子不超过整个可见分母。`side_c` 按 baseline 相同的视图质量归一化和全网格分母求比。

`side_union` 先在每个贡献槽位对三个 side 通道取 max，再累积；`enhanced_union` 是 union baseline 与 union side 的均值，因此不应重新用三个 `enhanced_*` 的最大值替代。

## scores.npz 字段

设原模型核数为 N，F 数为 V=8，类别数为 C=4。具体 dtype 以 `ASSET.json.array_fields` 为准。

| 字段 | 形状 | 含义 |
|---|---:|---|
| `original_ids` | N | `arange(N)`，固定原 PLY 行顺序 |
| `baseline_{color,geometry,outline,union}` | N | 视图均衡贡献基线 |
| `baseline_raw_{…}` | N | 原始 `ΣN/ΣD`，不均衡视图 |
| `side_{…}` | N | 双侧沉积率，使用相同全网格分母 |
| `enhanced_{…}` | N | baseline 与 side 各占一半 |
| `raw_denominator` | N | `Σ_v D_vi`，原始可见贡献质量 |
| `normalized_denominator` | N | `Σ_v D_vi/M_v` |
| `support_view_count` | N | `D_vi>0` 的视图数，表示可见而不是正证据 |
| `positive_support_view_count` | N×4 | 每类 `N_vic>0` 的视图数；不同于下方 0.1 门槛质量 |
| `eligible`、`unknown`、`unreliable` | N | 可靠可选、完全未观测、已见但可靠性不足 |
| `positive_mass` | N×4 | 原始 w 在 `E_c>=0.1` 位置的质量总和 |
| `nonedge_mass` | N×4 | 原始 w 在 `E_c<0.1` 的质量；包括低于门槛的弱证据 |
| `soft_nonedge_mass` | N×4 | `Σ_v,p w(1-E_c)`，连续反证量 |
| `front_mass`、`deeper_mass` | N | 保留 topK 中最近层／其余保留层的原始质量 |
| `front_fraction` | N | `front_mass/raw_denominator`，未知时数值为 0 |
| `depth_class` | N | 0 未观测；1 最近保留层质量≥80%；2 混合；3 最近保留层质量≤20% |
| `foreground_mass` | N | alpha≥0.08 位置的质量 |
| `interior_mass` | N | alpha≥0.5 内部腐蚀 2 像素后的质量 |
| `outline_mass` | N | `E_outline>=0.1` 的质量，即 `positive_mass[:,2]` |
| `perview_denominator` | V×N | 每个 F 的完整缓存网格分母 |
| `perview_numerator`、`perview_side_numerator` | V×N×4 | 每 F 每类基线／双侧分子 |
| `perview_normalization_mass` | V | 各 F 全缓存网格总质量 M_v |
| `perview_{positive_mass,nonedge_mass,soft_nonedge_mass}` | V×N×4 | 上述质量的逐 F 版本 |
| `perview_{front_mass,deeper_mass,foreground_mass,interior_mass,outline_mass}` | V×N | 上述质量的逐 F 版本 |
| `projection_baseline_{…}`、`projection_enhanced_{…}` | N | 对应连续分数乘 `eligible`；主投影的可靠性弃权字段 |
| `single_eligible`、`single_score` | N | 仅 F1 的可靠性与 enhanced union 连续分数 |
| `projection_single_union` | N | 单 F1 分数乘 `single_eligible` |
| `null_score`、`projection_null_union` | N | 固定平移 null 的连续分数／可靠性弃权分数 |
| `support_class_bits` | N | 仅紧凑包：任一 F 的正分子存在时置位，1=color、2=geometry、4=outline；支持类可重叠 |

不变量是 `positive_mass+nonedge_mass=raw_denominator[:,None]`，以及 `soft_nonedge_mass=raw_denominator[:,None]-Σ_v perview_numerator`。unknown 的两种反证量都是 0，不能解释为“确认为非边缘”。低分也不证明核与所有真实边缘无关，特别是在 top4 漏失下。

## 每 F 证据与来源文件

`out/gaussian_edge_attribution_v1/{scene}/F/F_NNN/` 保存：

- `evidence.npz`：四类 H×W 证据；`orientation_x/y` 为 H×W×3 的独立法向方向；`nms`、`roi` 为同形布尔数组。
- `statistics.npz`：本视图 `denominator`、`numerator`、`side_numerator`、正/反证和层质量；`diagnostics__side_overlap`、`diagnostics__side_depth_contrast`、`diagnostics__side_both_foreground` 为 H×W×3；`diagnostics__side_offset_count` 标明实际可采样偏移数；离证据位置的诊断零值不是测量。
- `diagnostics__front_slot` 为 H×W×4，`diagnostics__front_depth` 为 H×W，均相对于缓存保留层。
- `statistics.json`：frame_id、F split、topk、全图 `raw_cached_mass`/`cached_mass`、`alpha_mass`、`omitted_mass` 等标量；`null_statistics.*` 是唯一一次固定平移证据对照的同预算版本。
- `SEAL.json`：原缓存 SHA、camera_hash、模型及算法来源散列。`INPUTS_FROZEN.json` 给出每视图相机和源文件路径；`READ_EVENTS.jsonl` 记录驱动实际读取事件。

## selection.npz 与 PLY

键为 `{baseline|enhanced}_{color|geometry|outline|union}_{01|03|10|30}`。在同一多 F eligible 集合中按相应分数降序、原 ID 升序打破平局，选 `ceil(eligible_count×比例)` 个核。`single_union_XX`、`null_union_XX` 选与对应多 F union 组相同的数量；若其自身 eligible 不足则实际更少，读取 `ASSET.json.selection_counts`。`random_union_XX` 与多 F enhanced union 同数量，按 F 可见视图数与质量秩十分位分层抽样，种子为 `1729+比例整数`；随机组允许与选择组重叠。

`out/gaussian_edge_attribution_v1/{scene}/ply/` 的 selected PLY 原样保留被选行的全部 vertex properties（包括原 SH、opacity、scale、rotation 等）。对应 `.original_ids.txt` 第 j 行给出该 subset 第 j 行的原模型 ID。`PLY_EXPORT.json` 给出散列和尺度/各向异性等诊断，未从协方差轴推断法线、未拟合中心线。**单独渲染 subset 会改变遮挡，不能替代下述属性投影。**

## 全模型属性投影与 top4 估计必须分开

`frames/{pose}/projection.npz` 的主要 `baseline_P`、`two_sided_P`、`single_P`、`null_P` 与各 `*_Q_XX` 由完整 native 遍历生成：保留所有原核的位置、尺度、旋转、opacity 和透射顺序，以封存逐 ID 字段替换预计算颜色，并使用黑背景。

```text
P(p) = Σ_完整原模型 i w_i(p) · projection_score_i
Q(p) = Σ_完整原模型 i w_i(p) · 1[i∈sealed_selection]
```

未选核仍遮挡后方核；没有删除后重新合成。全遍历只使**投影贡献**完整，并没有补齐 TOP4 归因分数训练时遗漏的反证或证据。`top4_baseline_P`、`top4_two_sided_P`、`top4_selected_Q_10` 独立保存缓存截断投影用于遗漏审计。`baseline_conditional`／`two_sided_conditional` 明确是 `P/原始完整alpha`；不除以 top4 质量，也不应视为校准概率。

当前帧 `evidence_*` 用于面板比较和评价，生成 P/Q 时不参与选 ID 或像素门控。`class_{color,geometry,outline}_P` 与 `class_*_Q_10` 分开保存。白底灰度表示贡献强弱，不表示线条或明暗。显示增益仅由 Mic F 的两种 P 正值合并 P99 决定；Materials/C/arc 原样继承，原始数组不改动。

缓存 RGB 沿用冻结 SH0、白背景、native800、kernel_size=0 的配方；不是声称复现所有视角相关高阶 SH 外观。完整属性遍历则把 scalar 字段打包为预计算颜色。alpha/depth 同原遍历校准，详见 `NATIVE_CALIBRATION.json` 与逐帧 `METRICS.json.calibration`。

## 创建可编辑副本，不覆盖最终资产

修改 ID 分数属于新派生资产，必须生成新目录、新 seal 并保留父资产 SHA、checkpoint 命名空间。下面只创建可供 `NativeAttributeRenderer.render_field_bank` 使用的轻量属性字段，不替换研究结果、不重跑选择、不修改完整模型。不要直接将它冒充 `run_experiment.py` 训练输出。

在工作区根目录用主解释器执行；把 `edited_ids` 和对应数值改为已审阅的原 ID 编辑。示例默认无编辑，创建可追溯副本。

```python
from pathlib import Path
import datetime, hashlib, json
import numpy as np

root = Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1')
parent = root / 'artifacts/gaussian_edge_attribution_v1/assets/mic'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
dest = root / 'out/gaussian_edge_attribution_v1/edited_assets' / stamp
dest.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
package = json.loads((parent / 'PACKAGE.json').read_text())
assert sha(parent / 'scores.npz') == package['scores_sha256']
with np.load(parent / 'scores.npz', allow_pickle=False) as z:
    original_ids = z['original_ids'].copy()
    user_attribute = z['projection_enhanced_union'].copy()
assert np.array_equal(original_ids, np.arange(len(original_ids)))
edited_ids = np.array([], dtype=np.int64)  # 使用原 checkpoint 行 ID
edited_values = np.array([], dtype=np.float32)
assert len(edited_ids) == len(edited_values)
assert len(np.unique(edited_ids)) == len(edited_ids)
assert np.all((edited_ids >= 0) & (edited_ids < len(original_ids)))
assert np.all(np.isfinite(edited_values) & (edited_values >= 0) & (edited_values <= 1))
user_attribute[edited_ids] = edited_values
np.savez_compressed(dest / 'attribute.npz', original_ids=original_ids,
                    user_attribute=user_attribute)
meta = dict(parent_scores_sha256=sha(parent / 'scores.npz'),
            checkpoint_sha256=package['original_PLY_namespace'],
            created_utc=stamp, original_id_order_unchanged=True,
            edited_ids=edited_ids.tolist(), edited_values=edited_values.tolist(),
            interpretation='用户编辑派生属性；不代表新观测或原研究固定分数')
(dest / 'ASSET.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
seal = dict(files={name: sha(dest / name) for name in ('attribute.npz', 'ASSET.json')})
(dest / 'SEAL.json').write_text(json.dumps(seal, sort_keys=True, indent=2) + '\n')
print(dest)
```

使用新属性生成图片时仍需完整 checkpoint 行数不变、所有原核保留、GPU guard 通过；应将其新 seal 写入输出来源。编辑副本不继承原实验的未使用 C 评价资格，也不能覆盖最终分数、选择列表、报告或媒体封条。
