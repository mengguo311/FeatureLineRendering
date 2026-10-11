# v04 可编辑结构图与派生高斯

所有坐标沿原 camera-to-world 反投影定义，COLMAP 场景单位；没有米制换算。最终 primitive graph 和 Gaussian asset 都是新建墨线，不是源GS IDs。

## 每个 results/scanXX_full（ROI单独目录）

- `initial_graph.json` / `optimized_graph.json`：每primitive的type（line、bezier、point残余）、surface/suspected-silhouette标签、4个存储控制点、控制节点索引、来源短段ID/来源view、宽度、opacity、初始拟合误差。line只有0/3两个控制点参与曲线；bezier四个；point只用0号。内部1/2号line槽不作为额外曲率参数。
- `*_primitives.npz`：control[P,4,3]，全局points[K,3]、node_index[P,4]，节点bounds[K]（初始化后最大位移，.75当地像素的场景单位），type、pixel、normal、width、opacity、kind。相同node_index是真共享端点；沿一条primitive所有派生核共享这些几何/外观参数。normal是源相机视向的局部坐标基辅助，不是真值表面法线。
- `sampling_layout.npz`：primitive_id[M]、arc_t[M]、basis[M,4]、derivative_basis[M,4]、spacing[M]。初始化弧长中点采样后冻结离散参数，优化时控制点实际移动、切向实际改变。不是每高斯各自自由漂移。
- `*_gaussians.npz`：means[M,3]、covariance[M,3,3]，opacity[M]，黑colors[M,3]，primitive_id、arc_t、view_votes（不同来源视角数，不是identity证明）、source_count（关联短段数）、source_anchor（primitive ID，不是原GS ID）。float64为canonical。
- `*_gaussians.ply`：binary little endian，float32 xyz/cov_xx,xy,xz,yy,yz,zz/opacity，uchar RGB/view_votes，ushort source_count，int source_anchor。这是文档化自定义协方差PLY，不是能直接丢进标准3DGS查看器的SH/logscale格式；NPZ保留完整精度。
- `observations.npz`：所有原D>.2观测，uv、source_view（0/1/2映射0000/0024/0048）、raw camera-z、darkness、confidence、alpha、segment_id、primitive_id、arc、reason。reason0 assigned；1无效深度；2仅ROI实验域外；3无近骨架表示；4不同深度层/离骨架深度过远。未表示像素仍留在原soft目标与评价中。
- `ordered_segments.npz`：source_ids+indptr保存真正有序短链节点，view、chain、layer、segment_to_primitive。layer是局部短段假设ID，非语义对象标签，非已识别跨view表面ID。横向像素的最近骨架归属不是跨view曲线对应。
- `ambiguities.json`、`topology.json`：有界候选歧义与同source观测端点的共享关系。没有盲目缺口补全，没有后续自适应grow/prune。

## 重载和重渲染

`run.reload_graph`读取primitive参数，`primitive.sample_graph(graph, layout)`重新生成核；每个完成单元已检查canonical Gaussian数组完全一致，并用相同native EWA重渲染逐像素一致。保留layout用于完全复算；若编辑控制点后重新按弧长采样，那是一个新版本，应另外保存。

渲染是透视一阶协方差投影S=JRCRᵀJᵀ+.12²I，3σ截断，front-to-back alpha。CPU可微版本用黑色墨线的等价transmittance乘积；native实现也支持彩色排序测试。源depth/alpha只在给定exact camera渲染时做遮挡。novel arc未提供源场景深度，必须看显式缺遮挡标注。

canonical建模完整性不等于已恢复唯一物理3D线：局部layer、view-dependent silhouette、原纹理及单视图假设仍存在。

## provenance_refined 补充映射

原observations.npz的arc是source-chain参数。合并后正确的primitive局部参数见provenance_refined/<unit>/source_to_optimized_primitive.npz中的optimized_primitive_arc；保留source_chain_arc与每个raw观察到优化曲线的残差。两者不能混同。-1表示未归属。最近曲线参数只用于来源账本，未参与优化，也不证明唯一跨view线身份。
