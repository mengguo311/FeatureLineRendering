# 30579高斯合束单组demo

用户明确授权：仍用高斯渲染，在派生副本中调整／重建线核，使缠绕束收拢为单线。

## 三个阶段，没有偷偷替换结论
- `unit/ORIGINAL_GAUSSIANS.npz`：原版完整279616核，逐字节canonical备份。
- `unit/POSITION_ONLY_GAUSSIANS.npz`：仅把30579的596个中心放到同一条低复杂度3D曲线上；保留原协方差、opacity和颜色。双视图中更平顺、较连续，是本次可查看的合束预览。
- `unit/DERIVED_GAUSSIANS.npz`：冻结的进一步协方差方向/横宽规整版本。实际出现串珠/虚线，是保留的负例；**没有将它认证为视觉成功，也没有用POSITION_ONLY悄悄冒充它**。

两相机使用同一固定3D资产，实际Gaussian CPU EWA replica渲染；不是描线、管线或2D覆盖。主图每列使用同一固定裁剪，4倍最近邻放大；完整原生777×581图在unit/images。0036部分目标越过画幅底边，该区域未验证。

两个派生副本均仅移动目标596核；其他279020核全部七字段、所有原ID/行序、目标非几何字段逐位保留。POSITION_ONLY不改协方差；最终DERIVED确实改变596个协方差。原controls/arc_t是来源信息，不是派生中心仍由旧controls生成的证明。

## 使用
解压后可直接用NumPy读取对应NPZ。或：
`python3 cold_load_bundle.py 30579_gaussian_bundle_demo.zip`
该命令从实际ZIP成员字节核对SHA、原版回退与目标/非目标字段；返回的是明确标注的POSITION_ONLY预览，不是冻结DERIVED负例。

源码/冻结配置/真实RED-GREEN日志/失败分析均在unit中。native EWA生产渲染使用服务器已有Linux CPU库；此包的NPZ冷载不依赖它。不能把本包称为通用跨平台渲染器安装包。

此例是几何规整，不认证物理真边/held-out或时间稳定性；未扩到旁边其他组。首次helper白名单接口错误与同session修复回执保留；原字节SH代码移入新source，科学参数不变。没有运行另一个合并窗口或第二个科学单元。
