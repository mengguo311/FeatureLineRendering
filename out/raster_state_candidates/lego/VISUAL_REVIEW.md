# Primary visual decision: NO-GO

这是本轮助手对生成图像的内部审阅，不是盲评、用户研究或多人评分。
实际打开检查：Step1 TRAIN53 通道图、Step2 TRAIN53 回投图、Step3 全部四个
TRAIN 视角、Step4 TRAIN53 raw/new-only/all-arms、三个预标区域放大图、
数量匹配 cluster 图；DEV 三种版本的固定四帧、线长匹配五-arm panel、
四个 held-out 相机；native 和 area-matched 的全部 6 页 contact sheet
（各覆盖 0–119，每帧展示）。三段视频均完整解码 120 帧。

观察：

- R1 驾驶舱顶框确有局部正收益：D 的横跨顶框线比 A 连续，TRAIN53、
  DEV 侧向视角都能看出。此前 Step4.md 的保守初看不能抹掉这个局部结果。
  但新增候选也改变旧 seed 的 kNN/链化，尚不能将顶框改善全部归因于某一来源。
- R2 履带/轮组的大块形状仍没有进入清楚的 raw 或 final 线画。新增一些
  零散弧段不足以恢复该结构，也没有让主体底部更可读。
- R3 铲斗下缘 raw 有额外短线，final 仍分成几段，未形成有表达价值的下缘。
- 所以三处最多一处明显改善；G1 和 G3 的 >=2/3 门槛均失败。
- Native D 多出约 6% 墨长/墨面积，不能据此称成功。两种实际墨量匹配后，
  顶框仍有局部价值，但底板杂线、悬臂小碎段与主体大片空缺仍主导画面。
  从另一些视角看，D 增加散落短线，整体不比 A 明显更干净或更可读。
  G4 失败，不以 P/R 代替这一判断。
- Count-matched 的真实 D 比 shifted null 更集中于部分顶框/悬臂边界；
  但两者都主要是碎片。B/C 的小量子集难以构成可辨认结构。
  G2 的描述性重复率阈值通过，强视觉非-null 的主张未建立。
- 固定 3D 路径随物体投影运动，运行时无 2D evidence 读取。contact sheet
  没有显示整套新增线独立于物体游移；细碎线的可见性显隐仍然存在。
  不能由 persistent ID 推导无闪烁，也未做受控的人类时间稳定性评价。

结论只针对这组冻结参数下的 **disc raster-state 代理 + ID 聚合 + 现有下游**。
它不能否定尚未实验的官方各向异性 fragments，也不能泛化为所有 RGB/ID
锚定方法都无效。下一步仅执行预注册 chair 四 TRAIN 视角 cheap transfer；
停止完整第二场景与阈值救援，不改变本轮 NO-GO。
