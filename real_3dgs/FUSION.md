# Fusion 原型(signal-specific)— `fuse.py`

把 object-space(covariance 候选)与 image-space(G-buffer)特征线**按信号类型融合**,在真实场景上验证。复用 `lib.py` + `render.py`,纯 CPU。设计规范来自一次多 agent 设计编排(5 方案 → 5 对抗评审 → 综合)。

## 方法(signal-specific routing)
- **OCCLUSION / silhouette**:image-space **depth 主导**(深度不连续本就干净),直接透传;object-space 的作用是**确认/时间锚定**,不加像素。
- **CREASE / corner**:object-space **structure-tensor 主导**。把投影后的 3D crease/corner 候选(带软置信度,由 r2/r3 ramp 加权)splat 成置信度图 `C_struct`;**只保留有 3D 支持的那部分图像 normal-ridge**:`crease_fused = crease_im ∩ (C_struct > 0.08)`。→ 删掉无 3D 支持的假边,线仍是细的(严格 ⊆ baseline)。
- 详见 `fuse.py` STEP 0–5 与 `outputs/fused/*_conf.png`(可见 E 满屏噪声、3D 支持稀疏局部 → gate 后只剩有背书的子集)。

## 结果(4 个场景,见 `outputs/fused/`)
| 场景 | 类型 | crease 抑制 | 抖动线量(baseline→fused) | occlusion |
|---|---|---|---|---|
| nike  | 光滑 | **删 70%**(99% 无 3D 支持) | 192→93 px (−52%) | 3% |
| plush | 光滑 | **删 64%**(98% 无支持) | 389→170 px (−56%) | 7% |
| luigi | 光滑 | **删 98%**(100% 无支持) | 1150→23 px (−98%) | 1% |
| **primitives** | **棱角(cube+sphere+cylinder)** | **只删 15%**(97% 无支持) | 250→191 px (−24%) | 6% |

**核心对比 = 统一的 thesis**:光滑物体的 image crease 几乎全是噪声 → fusion **删掉 64–98%**;棱角物体(primitives)的 image crease 大多是**真实棱边** → fusion **保留 85%**,只删掉 15% 的噪声(其中 97% 无 3D 支持)。→ **object-space 的 3D 支持本质上是一个"真实特征线 vs 噪声"的判别器**:该删的删、该留的留。

primitives 的 object-space 面板是**最强的图**:cube 的边被 crease 完整描出 + 顶点是 corner、sphere 只有 silhouette(光滑,正确)、cylinder 上下 rim 是 crease + 侧面 silhouette——干净地三类分离。

(flicker 用精确重投影 + 1px 匹配;已自检:零位移时 self-flicker = 0.000%。)

每场景产出:`*_fused3.png`(image-space \| object-space \| FUSED 三联图)、`*_conf.png`(置信度图)、`*_flicker.png`(灰=线、红=逐帧抖动像素);总览 `all_fused.png`。

## 诚实的发现与局限(重要)
1. **抑制假边是真实、可靠的赢点**:fusion 删掉 64–98% 的 image-space crease 像素,其中 98–100% 确实无 3D 支持(= 平坦区的噪声假边)。luigi 这种纯光滑物体,fused 正确地收敛到**只剩干净的 occlusion 轮廓**——这正是光滑物体应有的线稿。
2. **总抖动线量大幅下降(−54%~−97%)**:因为假边被删,可抖动的线少了很多。这是诚实的时间收益。
3. **但 per-pixel flicker 率并未改善**(nike 3%→6%、plush 7%→10%):保留下来的 crease 仍骑在抖动的 normal ridge 上;而且**有 3D 支持 = 高曲率区,这些特征随视角移动更大、反而 per-pixel 更不稳**(早期等量对比中 supported 明显高于 unsupported)。→ **"3D 支持挑出更稳子集"这一假设在光滑物体上不成立。**
4. **加入棱角物体(primitives)后,得到统一且诚实的结论**:
   - 光滑物体:image crease ≈ 噪声、会闪 → fusion **删**(64–98%)。
   - 棱角物体:image crease ≈ 真实棱边、**本来就稳**(primitives 实测 baseline crease 仅 4%/px flicker,因为落在真实几何边上)→ fusion **留**(85%),只删 15% 噪声;并删掉了 sphere 那条会闪的"假 crease"(球无折痕)。
   - **所以"image-space 会闪、object-space 锚定使其稳"这个原始命题,只对噪声/假边成立;对真实特征线,image-space 本身就干净且稳定。** Hybrid 的真正价值 = **(a) 判别真实 vs 噪声(该留留、该删删)+ (b) 提供 3D 语义(crease/silhouette/corner 分类,纯 image-space 给不了)+ (c) occlusion 由 depth 保证干净**。这是比"object-space 稳定 crease"更准确、更可辩护的定位。

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
