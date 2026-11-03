本次单组demo已完成：**596个目标核的派生几何真实收拢，原版及279020个非目标核受保护；最终DERIVED在双视图出现串珠/虚线状间隔，连续单线视觉目标未通过。** 数值进程退出0不等于科学成功。停止原因为SINGLE_DEMO_COMPLETE，父级独立最终验收仍待完成。

只处理scan65的30579/v21779，完整资产279616行。原行数、顺序、身份及目标的opacity/colors/primitive_id/internal_piece_id/arc_t保持不变。原control参数只作来源，不能解释新中心的位置。本轮没有扩组、删除核或延续旧增长实验。

下图是已有Gaussian渲染：列为ORIGINAL、POSITION_ONLY、DERIVED，行为0012、0036；固定裁剪后4倍最近邻展示。0036有下边界裁切，放大不增加观测分辨率。

![双视图三阶段隔离对照](units/unit_001/BEFORE_AFTER_TWO_VIEWS.png)

[完整竞争背景对照](units/unit_001/FULL_CONTEXT_TWO_VIEWS.png)；[12幅原生图清单及运行结果](units/unit_001/RUN_RESULT.json)；[逐图分析与失败记录](units/unit_001/REPORT_ZH.md)。两相机固定777×581、COLMAP W2C，使用同一份冷载3D资产及CPU Gaussian EWA replica，未画辅助曲线或使用表面遮罩替代墨迹。

全部596个原中心等权参与一次单调主轴三次Legendre图拟合，二/三阶系数正则0.01，保留每核轴向参数与原端点范围。POSITION_ONLY仅改中心；DERIVED沿共同曲线解析切向设置协方差，横向sigma=0.15p，纵向sigma按原最大特征值开方后限制在[0.5p,1.5p]；p=0.001725801957946726为原场景单位。模型、逐核差和原目标备份均保存。Gaussian尾部不是严格有限支持。

保存审计确认两派生阶段各596行means改变，最终596行covariance改变；原7字段dtype/shape/行序保持，非目标全部字段bitwise相等，目标非几何字段相等，canonical源SHA前后相同。最终协方差最小特征值6.7013828956e-08，有限正定；切向主轴绝对点积最低约1。三阶段字段冷载一致，同资产双相机记录一致，隔离图内存/冷载渲染bitwise一致。[保护与冷载审计](units/unit_001/GEOMETRY_AUDIT.json)，[保存结果复核](units/unit_001/ANALYSIS_SAVED_AUDIT.json)。

POSITION_ONLY可见线条较平顺连续；DERIVED同时改变方向与横宽后出现串珠，不把原因唯一归结为宽度。位移中位0.597283p、最大2.074344p，低复杂度平滑可能压掉真实局部弯曲。opacity未改，隔离alpha积分却由0012的64.6805降至27.1463、0036的83.8038降至34.4672；变细/变淡不能等同合束成功。0036目标框y到606而画幅到581，画外段缺证据。背景邻近其他线继续保留。固定模型上零残差和轴向3sigma区间无洞都是构造/代理结果，不证明像素连续或物理真边。

实际数值子进程PID 3552276，2026-11-03T10:09:52.935714+09:00至2026-11-03T10:10:00.368642+09:00，returncode=0、reason=null、actual_child_exit=true；runner计时7.159秒。READINESS、先冷存完整资产、12幅原生图及审计均完成；没有quota、deadline、容量中断。原始[退出收据](orchestration/unit_001/COMPUTE_EXIT.json)和[渲染收据](units/unit_001/RENDER_RECEIPTS.json)保留。

BUILD保留真实vertical RED(rc1)→GREEN(rc0)，最终7项测试通过；额外保护/接口检查诚实标为实现后回归。首次接口验证因旧SH helper路径不在允许根目录失败；仅把字节相同的SH源固定到新源码并修正加载路径，回归通过后执行数值任务。失败及PRE_REPAIR文件仍在。[测试收据](units/unit_001/TESTS_RECEIPT.json)，[原接口失败](orchestration/unit_001/BUILD_VALIDATION_FAILURE.json)。

CONFIG SHA256 `eb2ddfe67164ee85d5432b0071f396def355576d84c88cc8ce35043e3d1f4105`；DECISION SHA256 `f49f3aaba72a9162c9f79e23001b20759c7715e2955a663732591598b3398460`。8份新源码快照、3个只读helper的逐文件SHA及实际绑定见[PARENT_RUN_FROZEN](units/unit_001/PARENT_RUN_FROZEN.json)，保存复核全部通过。目标596行little-endian int64行号SHA256为`5b0e387c307bc0a02e4737351f8c0eee3e635ea3da5aaa6f087f9eace8d4a9f6`。完整原版和两个派生版本均可冷载，不用仅位置对照悄悄替换失败的最终版本。

|保存文件|字节|SHA256|
|---|---:|---|
|[ORIGINAL_GAUSSIANS.npz](units/unit_001/ORIGINAL_GAUSSIANS.npz)|12,351,333|`3690a326224470faa3b673fe1c55f019211e0354f427f7fa86a974c4605dc130`|
|[POSITION_ONLY_GAUSSIANS.npz](units/unit_001/POSITION_ONLY_GAUSSIANS.npz)|12,351,395|`bda3a03730e856864da7f626a7cc4fa17e52ccb3e384be397827c5d1f4252653`|
|[DERIVED_GAUSSIANS.npz](units/unit_001/DERIVED_GAUSSIANS.npz)|12,376,756|`7401bca470af2ed9bd2080aa3f4279327b25908b29d538183d3de2cc93f7915a`|
|[ORIGINAL_TARGET.npz](units/unit_001/ORIGINAL_TARGET.npz)|26,036|`c905bb169dcc8fe9e85d990ed793f7aef3a5de4da8932a7a4261b568ecc3912a`|
|[TARGET_ROWS.npz](units/unit_001/TARGET_ROWS.npz)|425,901|`d6e064e87b7f2e082032061bdf60e7576b034552c13dd970e6df179ee7e18458`|
|[TARGET_TRANSFORM.npz](units/unit_001/TARGET_TRANSFORM.npz)|116,535|`c6ba8679de62dd138e30536d89e01f711defd5feb3db6a1227e85800cfa2acbe`|
|[MODEL.json](units/unit_001/MODEL.json)|1,018|`ff01794b52d1a7ffdca8d1a8044ad8d9b5838b03268859349c9ede8ba02cbeb0`|
|[GEOMETRY_METRICS.json](units/unit_001/GEOMETRY_METRICS.json)|820|`13eabc7cb313086efea69325776384c36932bc71c5e288b2f8ed18ebb8b91dae`|
|[GEOMETRY_AUDIT.json](units/unit_001/GEOMETRY_AUDIT.json)|10,272|`81d4776684cc0ce7617ae85dd802d318d817cb1ba5e9713ce1231fba9bdaf137`|

[四份分析状态](units/unit_001/STATUS.json)、[失败分析](units/unit_001/FAILURE_ANALYSIS.json)及[NEXT=stop](units/unit_001/NEXT.json)已封存。此实验是允许插值的几何规整，不认证物理身份、held-out效果或时间稳定性；不启动下一单元。所有原结果保持原位，交付仅复制保存证据，父级独立验收随后进行。

可移植保存证据包：[v11_30579_saved_demo.zip](v11_30579_saved_demo.zip)，39,852,179字节，SHA256 `9f4eea6dce25982296b9351ccef04d440bde0e566113908ad8d15efc5a4afcc6`。已校验全部包内文件SHA及ZIP CRC；含完整原版/两个派生NPZ、目标备份、双视图、源码快照、helper和失败收据。[逐文件清单](delivery/MANIFEST.json)；这是数据/证据包，不承诺原机绝对路径runner可直接异地执行。封存单元逐文件哈希未变，总输出约139.91 MiB，小于2 GiB。
