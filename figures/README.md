# 开题报告示意图 —— 说明与图注

由 `make_figures.py` 生成(纯软件光栅器 + numpy/scipy/matplotlib,无需 GPU/CUDA)。
场景:一个 **flat-shaded 立方体**(提供 crease + corner)+ 一个 **平滑球**(提供纯 silhouette、无 crease)。

> ⚠ 重要(给报告用的诚实表述):**传统 object-space 画线无法直接跑在 3DGS 上**,因为它依赖网格连接性,而 3DGS 没有。所以这两张图是用**有拓扑的网格**演示"两种传统范式各自的特性",作为你研究的 motivation——而非声称已在 3DGS 上跑通 object-space。

## 文件

| 文件 | 内容 | 用途 |
|------|------|------|
| `fig_C_comparison.png` | **主图**:左 image-space(毛糙/断裂,且无法区分线的类型)vs 右 object-space(细脆、按 silhouette/crease/corner 语义分色) | motivation 主幻灯片 |
| `fig_D_flicker.png` | 相邻两帧 image-space 线 + 差异图(红=闪烁像素,**52.5%** 的边缘像素逐帧变化) | 论证你的核心卖点"时间一致性" |
| `fig_A_image_space.png` | 左:depth+normal G-buffer(任何表示都能产,含 3DGS);右:image-space 边 + 角点放大("jagged/broken") | image-space 细节图 |
| `fig_B_object_space.png` | object-space 提取的干净矢量线(隐藏线已消除) | object-space 细节图 |
| `fig_E_pipeline.png` | **hybrid 管线架构图**:3DGS → object-space 分支(covariance→structure tensor→3D 候选)+ image-space 分支(G-buffer→边)→ fusion(投影+signal-specific gate+时间锚定)→ 干净稳定的特征线 | Method 章节核心图(`make_pipeline.py` 生成) |

## 建议图注(可直接用)

**fig_C(主图)**
- 中:图 1. 两种传统特征线范式。(a) **Image-space**(在渲染的 depth+normal G-buffer 上做 Sobel/Canny):适用于任何表示(含 3DGS),但边缘**毛糙、断裂、且无语义**(无法区分轮廓/折痕/角点),且相机移动时闪烁。(b) **Object-space**(由网格连接性提取):**精确、时间稳定、语义清晰**(蓝=silhouette,红=crease,绿=corner),但**需要显式网格拓扑——而 3DGS 不提供**。这一矛盾正是本研究要解决的:在无 mesh、无重训的前提下,把两者融合。
- EN: Fig 1. The two classical feature-line paradigms. (a) Image-space (Sobel/Canny on a rendered depth+normal G-buffer): works for any representation incl. 3DGS, but lines are jagged, broken, semantically flat, and flicker under camera motion. (b) Object-space (from mesh connectivity): precise, temporally stable, semantically labelled (blue=silhouette, red=crease, green=corner), but requires explicit mesh topology that 3DGS does not provide.

**fig_D(闪烁)**
- 中:图 2. 纯 image-space 线无时间一致性。相邻两帧(相机仅转 2.5°)的线绘制叠差:**红色为逐帧变化的像素,约占边缘像素的 52.5%**;灰色为稳定像素。由于没有 3D 结构锚定,边缘是逐帧独立重检测的,因而抖动/闪烁。本研究用投影后的 3D 候选作为锚点来抑制此问题。
- EN: Fig 2. Pure image-space lines lack temporal coherence. Overlaying line maps from two adjacent frames (camera moved 2.5°): red = pixels that change between frames (~52.5% of edge pixels), grey = stable. Without 3D anchoring, edges are re-detected independently each frame and therefore flicker.

## 重新生成 / 调参

```bash
cd figures
./.venv/bin/python make_figures.py
```

常用可调项(都在脚本里):
- 场景:`scene = [...]`(立方体/球的位置、尺寸、细分);相机 `eye / target / 视场`
- image-space 噪声强度/阈值:`image_space_edges(... noise=0.14, thr=0.10 ...)`(噪声被限制在真实边缘带内,所以表面保持干净)
- object-space crease 阈值:`object_space_lines(... crease_deg=25.0)`;隐藏线消除的 bias:`visible_segments(..., bias=...)`
- flicker 两帧夹角:`orbit(eye, target, 2.5)`

> 需要矢量版(SVG/PDF,投影更清晰)或换模型(如茶壶/Stanford bunny/CAD 件)、加第三张"hybrid 预期效果"示意图,告诉我即可。
