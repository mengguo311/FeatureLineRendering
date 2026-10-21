# experiment_001：P2物理边界零余量，固定结构显示诊断

**H2：ZERO_HEADROOM / UNIDENTIFIABLE_FOR_H2；固定结构显示工程验证通过。没有关联机制增益结论，也不是全局方法NO_GO。**

已完成且只完成一个有界实验。用户原话“感觉目前的质量以及足够，直接开始下一步实验”记录为 `USER_ACCEPTED_GT_VISUAL_BASELINE_FOR_P2`。接受 unit010 sealed outputs/edited named434：260灯罩0°、24支杆、150缩短底座；unit011未使用、不续跑，旧NO_GO不改写。当前接受不代表RaDe-GS重建、全时序认证或H1/H2成功。

## 为什么没有伪造U/S/D收益

完整读取851行大纲、BRIEF、P1路线、unit010报告和实际source/assets。601个unit010封存文件校验通过。868顶点/1728面由3个闭合面连通分量组成，各自只含一个部件；共享部件边0、 eligible物理边界长度/面积0，已有114.375330221世界长度排线中错误GT部件长度0。支杆和底座的空间相交不构成网格邻接；没有KNN连接、焊接、虚构链或噪声弱化。

隐性GT审计发现：`core_walk_v2.generate_strokes`在GT部件内采种、`walk`遇GT异部件停止；`renderer.render`在same-ray深度之外还检查visible GT part==owner face GT part。因此这不是粗分部基线，零越界不构成H2改善。renderer/core/walker与unit010 SOURCE_LOCK逐文件相同。没有改标签，mIoU改善不适用。

按brief允许的零余量替代，冻结 **B1-like：排线+原轮廓、物理profile环关闭；B2-existing：排线+原轮廓+已有profile环，即用户接受基线**。唯一变量是 `render(structure=False/True)`，同434路径/种子/墨色/标签/几何/遮挡/相机/后端。既有864条profile边共27.703901807世界长度为人工GT几何结构，不是共享语义边界，不是编辑区边界，也不是普通深度恢复或新B2成果。没有B3、方向引导或边界修正；U/S/D不适用并明确未运行。

## 冻结与真实运行

协议提交 `ef135f45` 在任何候选渲染前；实现提交 `ff6aafd3`，SOURCE_LOCK冻结实际源/输入。512²，2xAA，hatch1px，contour0.8px，ring0.65px，深度容差0.006；固定原始世界光照/墨色，无LOD。静态30/120/210/300°历史已曝光；orbit12帧(7.5+30k°)和zoom8帧(52.5°、仰角25°、距离5.2→4.2)在结果前由metadata选定，只称construction holdout，不称未见重建数据。

24相机×2臂实际调用相同后端，另12张静态隔离部件排线只作评分。全部完整灯罩/支杆/底座在画面内。四张B2与unit010保存PNG像素精确复现；24对hatch、轮廓、labels与depth精确相同。原排线墨量保留100%，无需以少画来换分数。

| 静态方位 | 加环实际L1 | 可见环长/隐藏环长(world) | 环参考支持 B1→B2 | 总可见墨量比 | 近环hatch像素(不变) |
|---:|---:|---:|---:|---:|---:|
| 30° | 240.114646 | 5.5537/9.8583 | 79.32%→100.00% | 1.095364 | 313 |
| 120° | 240.624039 | 5.5537/9.8583 | 80.50%→100.00% | 1.077583 | 366 |
| 210° | 247.444905 | 5.5537/9.8583 | 76.62%→100.00% | 1.099378 | 267 |
| 300° | 248.873633 | 5.5537/9.8583 | 75.02%→100.00% | 1.127714 | 197 |


全部24相机，加环非零L1范围 226.495349–291.386980；总可见墨量比 1.076801–1.129659，增加来自显式结构环。近环hatch重叠、每部件覆盖与distance-to-hatch p50/p95逐帧保存；后者是空白距离代理，不是真实相邻笔触间距。没有裁剪、杂线减少或审美偏好收益证据。原始表与分母见 `metrics/RESULTS.json`、`FRAME_SUMMARY.csv`、`SUMMARY.json`。

连续解析lathe ray oracle独立于三角渲染，但共享人工形状定义。环长按≤0.002world中点采样，分开报告可见、预期隐藏、固定2px AA带、unknown和与轮廓合并排除的长度；可见非轮廓环长范围 5.1201–5.5537，仅占全部人工环长约18.48%–20.05%。支持率只在这个可见分母上成立，不代表所有环长均可见或已验证。24帧并非独立对象样本，无显著性或泛化统计。环参考图像支持可包含原hatch/轮廓贡献，因此并非自动提取精度。近环杂线代理使用B2实际ring raster的固定2px邻域，给两臂共用；它不是独立物理边界恢复评分。

12张隔离静态part hatch对独立解析标签，远错误部件墨量总计 0.00000000，远背景 0.00000000，AA带 75.25195796；这些是继承GT条件下有限可见输出结果，不能掩盖隐藏侧或全路径时序问题。renderer原始part/depth拒绝fragment counts也保存，但包含重叠且不等于泄漏像素。

## 验证、失败和恢复

TDD首先真实断言失败：没有连通边界却返回ELIGIBLE，rc1原样保留；最小修复后通过。最终8项行为测试含：真实walker在同标签跨面/异标签停止、invalid/missing evidence→UNKNOWN、分离曲面不KNN相连、固定非目标hatch/轮廓、no-edit/delete-all/3px drift响应和解析隐藏参考已知交点。保存真实图像的4组no-op/delete-all/drift及12组16像素远部件注入控制均有预期反应。

原始git add因sparse checkout拒绝rc1，随后只对授权新目录用--sparse成功；一次只读快照路径猜测rc1，已用SOURCE_LOCK与真实source_snapshot路径核实。首次zoom与isolated阶段发生 1.341840s 调度重叠：两个数值进程各1线程、均限定CPU[0,1]且总量≤2，但违背冻结串行规则。保留两组原产物和原rc0于 `attempt_schedule_overlap/`；执行级恢复仅串行重跑完全相同两阶段，56份PNG/NPZ逐文件SHA完全相同。没有参数重选、第二实验或科学结果重试。完整变更说明见 `EXECUTION_AMENDMENT.json`。

orbit12/zoom8视频逐相机渲染固定3D路径；6fps FFV1离线展示，全部20帧解码RGB与源PNG逐帧精确，相应12/8帧各自全部不同。不是动画静帧、实时性能或完整时序认证。最终48次比较渲染中位 2.694s/P95 2.779s，仅CPU离线；原重叠尝试时延不混入此摘要。

26旧SEAL哈希及两个旧worktree HEAD/干净状态复核相同；没有写原GS/C8/joint/raw data，没有GPU、安装、下载、secret、push或merge。新science只在experiment_001，数值线程1、两核affinity。源/命令/原退出码、完整对象同相机图和近边界放大、所有分母、实际视频SHA均保留。

## 交付和有限结论

- 完整对象同相机对照：`media/static_all_frames.png`；覆盖/墨量/间距代理/重叠/泄漏并列图：`media/static_metrics_comparison.png`；每幅原生512²，不以局部截图替代全灯。
- 边界近景：`media/static_*_shade_top_2x.png`、`*_shade_bottom_2x.png`、`*_base_top_2x.png`；裁剪由固定几何profile投影定义，nearest2x。
- 全帧接触图与视频：`media/orbit_all_frames.png`、`zoom_all_frames.png`、`orbit_comparison.mkv`、`zoom_comparison.mkv`。
- 原始可见/遮挡/覆盖/暗度/近环重叠、oracle掩码、控件响应、源锁定：experiment_001的audit/metrics/renders/isolated目录。

完整静态及全部轨迹接触表已实际审阅，另检查30°灯罩上下口/底座、210°底座近景。最明显变化是底座内部椭圆环；下灯罩边缘因继承轮廓而变化很小。原排线保持，新增环仍与部分交叉排线重叠。没有重启外观改进；细节见 `VISUAL_REVIEW.json`，这不是独立人类或盲偏好评价。

固定结构开关有非零可观测显示效果，保存了接受基线。由于既有完整GT物理分部使H2没有可测交界支持，本轮没有证明关联机制有用、没有证明粗分部或噪声RaDe-GS受益、没有自动曲线恢复/新颖性/H1–H5成功结论。保留简单系统，不把工程完成当作机制成功。

下一步只推荐一个独立、另行授权实验：在同一整灯灯罩的连通曲面上预先定义一条人工编辑区边界、独立regionIDs及oracle来源，冻结共同粗标签误差和无噪声/保墨控制，检验停止/留白是否减少该编辑区越界；明确它不是物理几何棱边或自动语义恢复。当前不执行，详见NEXT.json。
