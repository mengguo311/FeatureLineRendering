# Fusion 原型(signal-specific)— `fuse.py`

把 object-space(covariance 候选)与 image-space(G-buffer)特征线**按信号类型融合**,在真实场景上验证。复用 `lib.py` + `render.py`,纯 CPU。设计规范来自一次多 agent 设计编排(5 方案 → 5 对抗评审 → 综合)。

## 方法(signal-specific routing)
- **OCCLUSION / silhouette**:image-space **depth 主导**(深度不连续本就干净),直接透传;object-space 的作用是**确认/时间锚定**,不加像素。
- **CREASE / corner**:object-space **structure-tensor 主导**。把投影后的 3D crease/corner 候选(带软置信度,由 r2/r3 ramp 加权)splat 成置信度图 `C_struct`;**只保留有 3D 支持的那部分图像 normal-ridge**:`crease_fused = crease_im ∩ (C_struct > 0.08)`。→ 删掉无 3D 支持的假边,线仍是细的(严格 ⊆ baseline)。
- 详见 `fuse.py` STEP 0–5 与 `outputs/fused/*_conf.png`(可见 E 满屏噪声、3D 支持稀疏局部 → gate 后只剩有背书的子集)。

## 结果(3 个真实场景,见 `outputs/fused/`)
| 场景 | crease 抑制 | 抖动线量(baseline→fused) | occlusion flicker |
|---|---|---|---|
| nike  | **70%**(被删的 99% 无 3D 支持) | 192→93 px (**−52%**) | 3% |
| plush | **64%**(98% 无支持) | 389→170 px (**−56%**) | 7% |
| luigi | **98%**(100% 无支持) | 1150→23 px (**−98%**) | 1% |

(flicker 用精确重投影 + 1px 匹配;已自检:零位移时 self-flicker = 0.000%。)

每场景产出:`*_fused3.png`(image-space \| object-space \| FUSED 三联图)、`*_conf.png`(置信度图)、`*_flicker.png`(灰=线、红=逐帧抖动像素);总览 `all_fused.png`。

## 诚实的发现与局限(重要)
1. **抑制假边是真实、可靠的赢点**:fusion 删掉 64–98% 的 image-space crease 像素,其中 98–100% 确实无 3D 支持(= 平坦区的噪声假边)。luigi 这种纯光滑物体,fused 正确地收敛到**只剩干净的 occlusion 轮廓**——这正是光滑物体应有的线稿。
2. **总抖动线量大幅下降(−54%~−97%)**:因为假边被删,可抖动的线少了很多。这是诚实的时间收益。
3. **但 per-pixel flicker 率并未改善**(nike 3%→6%、plush 7%→10%):保留下来的 crease 仍骑在抖动的 normal ridge 上;而且**有 3D 支持 = 高曲率区,这些特征随视角移动更大、反而 per-pixel 更不稳**(早期等量对比中 supported 明显高于 unsupported)。→ **"3D 支持挑出更稳子集"这一假设在光滑物体上不成立。**
4. **结论**:在这三个**光滑**物体上,fusion 的可证明价值是 **cleanliness / 假边抑制** + **occlusion 干净稳定**;**crease 的时间稳定性无法在此演示**——需要一个**棱角分明、有真实 crease 的物体(CAD/机械件)**,真实的 3D 折痕才会稳定重投影、体现 object-space 锚定的时间优势。(这正是 5 个设计评审一致预警的点。)

## 对 proposal 的意义
- 经验印证了 **signal-specific fusion**:occlusion 让 image-space depth 唱主角,crease/corner 让 object-space 唱主角——不是单一全局 gate。
- 给出明确的下一步实验对象:**找/做一个 CAD/机械件场景**来正面演示 crease 的时间稳定性。

## 复现
```bash
cd real_3dgs
../figures/.venv/bin/python fuse.py                 # 跑 3 场景 + montage
../figures/.venv/bin/python fuse.py nike.splat mid 1.35   # 单场景
```
关键参数在 `fuse.py` 顶部:`C_THR`(3D 支持阈值)、`SIGMA_CONF`(置信度图模糊)、`ROT_DEG`(flicker 两帧夹角)、`DENSITY_FLOOR`(crease-lines 闸门)、`FILL_ON`(可选的 3D 引导补全,默认关)。
