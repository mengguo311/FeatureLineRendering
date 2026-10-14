# 先看这些图

已交付16档×11视角。A20是现有检线基线；没有自动替换05。

| 场景 | 建议先比较 | 主要取舍 |
|---|---|---|
| scan24建筑 | C2U20、A40、C1L50 | C2U20屋瓦干扰更少，细窗格有简化；A40细节更多但屋瓦仍密；C1L50更淡 |
| scan65头骨 | A40、C1L50、C2U20 | A40轮廓较明确；C1L50更简淡但部分牙齿变弱；C2U20简化小内部边界 |
| Ficus参考 | A30、C1U20、M75T30 | 保住细叶和枝干优先，不能照搬头骨的强抑制 |

先看selection/*_CHOICES.jpg，再看*_BINARY.jpg排除“只是变淡”的错觉。全5视角在*_ALL5.jpg。原生单图在scenes/<scene>/<view>/presets/<ID>/candidate.png；marked.png为全黑候选，skeleton.png为骨架。

更完整系列：THRESHOLD.jpg为6档阈值，MIX.jpg为分支占比，SCALE.jpg为尺度对照，DIAGNOSTICS.jpg包含原RGB及S/D分支。B00是删除过多的负例，请勿按白色面积选最好。没有GT，不能给出真实SNR第一名。候选ID只是暂定建议，最终由用户根据图选择；本轮到此停止。
