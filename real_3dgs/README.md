# 真实 3DGS 场景上的画线实验(路线 A,CPU,无 GPU)

**结论:可行性已验证,并已在 3 个真实单物体场景上复现。** Apple M5 Mac(无 CUDA),纯 CPU,单场景 ~1–5 秒。

## 数据(3 个干净的单物体 + 备用场景)
| 文件 | 来源 | Gaussian 数 | 说明 |
|---|---|---|---|
| `nike.splat` | huggingface `cakewalk/splat-data` | 270k | Nike 跑鞋(光滑) |
| `plush.splat` | huggingface `cakewalk/splat-data` | 281k | 毛绒玩具(光滑) |
| `luigi.ply` | huggingface `dylanebert/3dgs` | 14.5k | Luigi 人偶(`.ply` 格式) |
| `train.splat` | 同上 | 1.0M | ⚠ **完整户外大场景**(机车+背景),非单物体,PCA 无法干净取景——留作参考,未用于干净 demo |

> `train` / `truck` / `bonsai` 这些是 Mip-NeRF360 / Tanks&Temples 的**完整 360° 场景**(背景一大堆),不是"简单模型";所以第 3 个单物体我换成了 `luigi`。

格式:`.splat` = 每 splat 32 字节(pos 3×f32 / scale 3×f32 / RGBA 4×u8 / quat 4×u8);`.ply` = 标准 3DGS(scale 取 exp、opacity 取 sigmoid、DC-only SH)。两种都支持。

## 代码(已参数化,可跑任意场景)
- `render.py` —— CPU **EWA splatter** + 加载器(`load_scene` 自动识别 `.splat`/`.ply`)。解析 → covariance Σ → 法线=薄轴 → front-to-back α 合成 → **color/depth/normal G-buffer**。无 GPU/CUDA/PyTorch。
- `preview.py <scene> [opacity_cut] [max_splats]` —— 渲 3 个 PCA 候选视角,用来选相机。
- `experiment.py <scene> [view=mid] [dist] [opacity_cut] [max_splats] [fov]` —— 渲 G-buffer + image-space(Sobel)+ object-space(各向异性自适应过滤 + KNN 法线平滑 + **normal-structure tensor** 按 λ₂/λ₁、λ₃/λ₁ 分类 silhouette/crease/corner,投影+深度可见性测试)。**无 mesh。** 输出 `<scene>_gbuffer.png`、`<scene>_comparison.png`。
- `montage.py` —— 把三物体的对比图叠成一张 `all_objects_comparison.png`。

## 产出图(已分层整理到 `outputs/`)
```
outputs/
├── all_objects_comparison.png      ⭐ 三场景 ×(image-space | object-space)总览(开题一页用)
├── comparison/                     各物体对比图(occlusion 线已加粗,适合投影)
│   ├── nike_comparison.png
│   ├── plush_comparison.png
│   └── luigi_comparison.png
├── gbuffer/                        各物体 color | depth | normal 三联图
│   ├── nike_gbuffer.png ...
└── preview/                        选相机用的 PCA 三视图
    ├── preview_nike.png ...
```
脚本会自动建好这些子目录;`comparison/` 里的 occlusion contour 用了 2px 膨胀加粗、置于最上层。

## 复现各物体所用相机
```bash
cd real_3dgs
P=../figures/.venv/bin/python
$P experiment.py nike.splat  mid  1.35 0.18 220000 45
$P experiment.py plush.splat thin 1.35 0.18 220000 45
$P experiment.py luigi.ply   thin 1.45 0.10 220000 45
$P montage.py
```

## 图像空间画线的正确做法(occlusion vs crease,要分开)
**occlusion contour 不能用"深度梯度幅度 + 全局归一化"去测**(早期版本就是这个错:背景平面贴太近 → 轮廓跳变被压扁 + 强弱不均 + 被噪声法线淹没,导致轮廓断裂)。正确做法 = **(coverage mask 边界) ∪ (物体内部的大相对深度跳变 `(localmax−localmin)/depth`)**,且**与 crease 分离**:
- **occlusion contour ← depth**:干净、完整、可靠(这是 image-space 的**强项**,见 `*_comparison.png` 黑线)。
- **crease ← normal**:vanilla 3DGS 法线噪 → 即便先高斯平滑也不稳(橙色线)。

## 关键发现(对 proposal 有用)
1. **可行性高且可推广**:不训练、不要 GPU,3 个不同来源/格式/规模的场景都跑通。
2. **image-space 的真正弱点不是 occlusion contour**(深度不连续很稳),而是 **① crease(依赖噪声法线)② 时间闪烁 ③ 无 3D 语义**。→ 这直接支撑你的 **signal-specific fusion**:occlusion 以 image-space depth 为主、object-space 只做时间锚定;crease/corner 以 object-space structure tensor 为主、image-space 做定位。
3. **vanilla 3DGS 的 covariance 法线很噪**;自适应各向异性过滤 + KNN 平滑显著降噪(nike crease 候选 67k→9k)。
4. **物体越光滑,crease/corner 越少**(nike/plush/luigi 都偏光滑,corner≈0);silhouette 候选贴合外轮廓。棱角分明的 CAD/机械件会让 crease/corner 明显得多。
5. Gaussian 少(luigi 14k)时多 splat 偏圆胖 → 自适应分位过滤(保留最扁 60%)比固定阈值稳。

## 还能往下做
- 接 **fusion** 原型(投影候选 gate image-space 边)→ 出"融合后"结果;
- **flicker 实验**(渲两帧,量化 object-space 锚定后的时间稳定性);
- 把散点 candidate **聚类成 3D 折线**;
- 找/做一个**棱角分明**的物体让 crease/corner 更突出;
- 实时交互上路线 B(Brush / WebGPU)。
