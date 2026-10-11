# v04 冻结实验方案：共享线段/Bezier控制点生成高斯墨线

冻结于实现及新生产之前。仅CPU，两线程；不修改旧实验。来源是原Spatial RGB DEFAULT union，darkness=1-ink(union,1,.5)，marked>.2。整数像素中心(W-1)/2，raw median camera-z，COLMAP场景单位，不使用米/mm。

## 实际看图及文献边界
已经实际查看建筑0012原detector/47balanced/同核strict、头骨0036、水果0048和v03固定ROI0048的放大图：建筑累加变黑、strict严重缺结构；头骨后颅轮廓仍断；水果的真实目标含密果皮纹；v03仅opacity拟合未修复跨view碎窗线。因此本次必须让几何控制点参与优化。
SketchSplat原文§4.2/4.3启发线段/三阶Bezier共享几何、宽度、opacity与高斯采样；其EdgeGS、2DGS-SN、米尺度/5mm/10mm、1000epoch与末尾可见性删除不迁入。Sketch and Patch支持共享参数，但压缩字节不等于减少运行核数。其余文献只作来源，不实现CAD/面/额外网络。本实验不是任何论文的忠实复现。

## 冻结机制
1. 每build原marked的所有像素保留账本。原深度非有限/非正明确拒绝。骨架仅用于有序拓扑播种，原soft全目标用于损失。8邻接去掉有正交替代的对角捷径，degree!=2处切链；在转角>35°(两侧3px)、弧长16px、深度邻接跳变>4个当地像素场景尺度处拆分；不跨缺口补线。孤立像素是显式point残余，不隐藏。横向像素在同view最近骨架且3px内归属，否则标未表示，仍进损失。
2. 每短链按累计弧长参数拟合直线；若最大空间残差<=.6当地像素优先线。至少6点才拟合三阶Bezier，保留端点，接受最大残差<=1像素且比直线减少至少30%；控制点不得跑出原点包围盒2像素。不满足递归拆链，不以大核吸收误差。真实角点/junction不被单Bezier跨过。
3. 多view候选用空间索引、5个有序区间点、深度/切向/重投影检查。允许正反顺序。世界走廊<=1当地像素、方向25°、共同覆盖>=60%，双方重投影中位<=1px、p90<=2px。所有组成员两两相容而非传递并集；每view一个区间；前两候选代价接近20%记录歧义并不强合并。near depth layers不平均；疑似silhouette(邻域深度跳变或alpha不可信)只允许接近完全相同的重复证据融合，其余多假设分别保留。hidden/unknown不参与否决，无globalzero-counter gate。
4. 合并后用view均衡支持拟合短primitive，参数数不随重复同一观测增加。端点共享仅来自同source已观察junction/相邻链端点且几何一致，无盲目端点kNN连接。prototype先固定拓扑，无不受控grow/prune；新可见链可增容量。完整账本保存chain/layer、primitive/arc、歧义/拒绝原因。
5. 按弧长约1个参考像素采样(参考p=来源z/focal中位)，中点采样避免接缝端点重复。主轴切向sigma=.65*实际间距，横轴初始.45p、限[.25,.65]p，另一横轴.25p；全为小SPD高斯，非单个大椭球。point用.45p各向同性。透明度初始来源darkness中位并限制[.02,.95]，不随观测票数加墨。局部坐标基由源相机视向与切线确定，无学来的normal监督。
6. 控制点参数真实可动；每控制点相对初始化的欧氏位移<=.75p，用有界参数及球投影。初始拟合残差单列，不能把这个后续界当raw depth绝对准确。宽度/opacity同primitive共享。损失每camera等权：线上(D>.2)MSE + 线外(D<.05、known alpha>=.5与finite positive depth)MSE + .2中间值MSE + .002归一化控制点anchor + .0001mean opacity + .002(width-.45)^2。所有未解释正目标保留，不只评估已有核足迹。hidden不当负，unknown不当线外负。可见性按真实source depth逐核足迹重建；不对离散visibility求梯度。
7. 稀疏可微EWA使用J R C R^T J^T+.12²I、3sigma和black alpha乘积，torch CPU自动微分通过means、tangent、covariance、width、opacity。每步重建有额外margin的像素候选；真实3sigma、排序/可见性有离散分支，FD仅光滑分支，另留边界负控。最终资产经旧已核验native EWA渲染、二者对照，保存可重生成primitive graph和NPZ/PLY。不把移动silhouette等同固定线身份。

## 冻结数据与预算
构建仅0000/0024/0048，0012/0036在资产封存后只做render/visibility与评价，已见GS训练视角非盲测。先scan24原ROI [324,226,452,354)。其他两build使用v03已冻结投影窗口，仅在窗口内提链，保留对应较大视域的未解释目标；报告其并非同面积等价ROI。三个窗口目标不换成骨架。
ROI最多32步geometry固定width/opacity +32步joint。全帧scan24最多12+12步同损失同参数；随后若数值工程门槛通过可同recipe运行scan65/scan63的3build全帧负/正demo，各12+12。迭代预算不同明确记录，不调holdout。若单次CPU内存/时间过大，记录部分结果而不静默改渲染/分辨率。三场景均不跑47view。

## 证伪与gate
先RED/GREEN：直/曲、近平行、近层、T/X/角点、depth扰动、missing/hidden/unknown、移动轮廓冲突、非传递、3/12/47重复观测、真正新段。几何/尺度/opacity FD rtol1e-4 atol1e-6；native稀疏同渲染max2e-6；坐标roundtrip1e-8；SPD>0；重载重生成逐数组一致。全透明、宽黑片、错误层均值为负控，测试不通过不能宣称有效。
ROI保留原D/allpixel/v03negative/init/final三build面板；全帧保留原D/oldbalanced/init/final五camera。即使ROI视觉仍负，若基础工程gate通过也产出标负的scan24全图，避免漂亮ROI选择。是否改善以线连续和主体完整、重影/黑片/悬浮检查，不用点数和loss单独裁决。
33帧同arc老balanced/新primitive-fixed Gaussian动画，源深度不在novelview可用，明确ink-only/no original-scene occlusion。视频全解码、33count、yuv420p/faststart核查。最终若视觉不达标标HONEST_NEGATIVE；不自动追加生产。
