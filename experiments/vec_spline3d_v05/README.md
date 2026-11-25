# `vec_spline3d` — 独立三维参数曲线、曲率带状、视点轮廓生成元与平面正交线框管线（v01–v05）

本项目将从 3DGS 图像空间恢复的三维碎片线段连接、聚拢并优化为紧凑的**混合三维几何原语网络（`LINE_3D` + `ARC_3D` + `COAXIAL_RING_FAMILY`（含任意三维轴向 $\mathbf{a}\in\mathbb{S}^2$） + `CUBIC_BSPLINE_3D` + `RIBBON_3D` Darboux 标架 + `LATHE_ENVELOPE_3D` / `SWEPT_TUBE_ENVELOPE_3D` 视点相关轮廓生成元 + `planar_patches` 建筑共面/曼哈顿正交线框 + `JunctionNode` 拓扑交点）**。

## 核心架构
1. **Stage 1A (`stage1_ray_clean.py`)**：全训练视角视锥安全视壳空域雕刻 + 逐位一致 RaDe-GS 中值深度（`middepth`）自由空间门控 + `state=2` 切平面外推节点沿原相机射线的多视角边缘距离场重三角化（Viterbi DP 去刺保尖）。
2. **Stage 1B (`multiview_seed.py`, v02)**：从球面最远点采样的补充训练视角渲染源表面 3DGS 与精确 C2L50 多尺度边缘骨架，通过真三维 `cKDTree` 盲区检测主动补种内冠与侧剖边缘。
3. **Stage 2 (`stage2_scms_consolidate.py`)**：视线不确定度各向异性子空间约束均值漂移（Ray-Anisotropic SCMS）+ 带 Y 分叉保护的侧向交错重影合并 + $>50^\circ$ 直角折点保真切分。
4. **Stage 3 (`coaxial_rings.py` + `contour_generators.py` + `co_circular_arcs.py` + `planar_wireframe_reg.py` + `stage3_spline_topology.py` + `ribbon_geometry.py`)**：
   - **任意三维轴向同轴旋转环/圆盘族先验（`COAXIAL_RING_FAMILY`, v03→v05）**：从早期竖直旋转体自动扩展至任意三维轴向 $\mathbf{a}\in\mathbb{S}^2$（倾斜镲片、鼓圈、水平底鼓与竖直花盆），融合 36 扇区圆盘外边界拟合、三维圆弧假设与 360° 多视角边缘切向印证；
   - **视点相关遮挡轮廓生成元（`LATHE_ENVELOPE_3D` & `SWEPT_TUBE_ENVELOPE_3D`, v04→v05）**：针对光滑旋转体与广义圆柱木质主干建立解析透视轮廓生成元 $\mathbf{N}(\mathbf{x})\cdot(\mathbf{o}_{\text{cam}}-\mathbf{x})=0$（含多视角轮廓边缘距离门控防误检），实时生成连续闭合外轮廓并导出 `contour_envelopes_mesh.obj`；
   - **建筑平面共面与曼哈顿正交线框正则化（`planar_wireframe_reg.py`, v05 新增）**：融合有向表面法向模态与直线交点发现主结构平面及 $4\theta$ 正交主轴，拉直浅弧伪圆、将共面/二面角节点投影至结构平面或交线，并焊接窗框共线缺口；
   - **有向曲率带状原语与物理边缘解耦（`RIBBON_3D`, v03）**：构建正交 Darboux 标架 $(\mathbf{T}, \mathbf{B}, \mathbf{N})$，解耦物理边缘语义并导出 `ribbons_mesh.obj`。
5. **Stage 4 (`stage4_diff_refine.py`)**：PyTorch + CUDA 联合精修共享拓扑节点、曲线控制点、多族任意轴向同轴环流形参数、建筑平面共面/主轴平行正则项（`loss_planar`）、视点轮廓包络半径 $(\Delta\rho_{\text{lathe}}, \Delta r_{\text{tube}})$ 及三轴 Darboux 带状核半宽。

## 快速运行
```bash
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python
$PY -W error::SyntaxWarning -m unittest discover -s tests -v
$PY scripts/run_roi_pilot.py
$PY scripts/run_full_scene.py      # v01: 8 构建视角 + LINE_3D / CUBIC_BSPLINE_3D
$PY scripts/run_full_scene_v02.py  # v02: 32 视角三维盲区补种 + ARC_3D 共圆聚合
$PY scripts/run_full_scene_v03.py  # v03: 同轴旋转环族 COAXIAL_RING_FAMILY + 有向带状原语 RIBBON_3D
$PY scripts/run_full_scene_v04.py  # v04: + 旋转体与管状主干视点相关轮廓生成元 (Occluding Contour Envelopes)
CUDA_VISIBLE_DEVICES=0 $PY scripts/run_cross_scene_benchmark.py --scene scan24 --device cuda:0 --extra-views 16  # v05 跨场景评测 (scan24/scan65/drums/chair/ficus)
```
