# v04 结构 primitive 高斯墨线：已执行实验报告

已完成固定ROI及建筑、骷髅、水果三个3-view全帧实验，最终判定 **HONEST_NEGATIVE**。实现了真正可编辑的线/三阶Bezier共享控制点，几何、宽度、opacity均参与真实优化，并从固定参数生成新3D Gaussian资产。局部笔划可读性改善，但跨视角关联不足，后脑缺失和建筑重影未解决；没有达到“较少重复、完整且有意义的结构线”目标。没有追加训练、47-view生产或mesh。

## 实际范围及来源

仅0000/0024/0048构建和优化；0012/0036在各ASSET_FREEZE写出后读取目标内容用于渲染/评价。它们早已被看过、也是源GS训练视角，**不是盲测或GS heldout**。3场景各5个完整画面，3个33帧真实新相机动画，另有固定ROI三build、公平三source raw控制和9种实际合成资产。未使用heldout调参。

原Spatial RGB DEFAULT union、darkness>.2不变。boundary.py SHA256 `11bbb41a762f252d9eeb4ea3f0a8399ed026139d9490bb8cf161bc815e05dd30`；raw median_camera_z来自封存30k NPZ，不是着色深度。SOURCE_FREEZE含96项逐hash核验记录，包含15份选定NPZ、相机、约定、旧资产/代码和文献。大原始tar没有重hash，沿用作者交付manifest的archive hash声明，此限制单列，不能冒称重新下载验证。native EWA SHA256 `0ab11c21f930446c699ae5fb9dc14f3fe2eefc563a4011b8a14ba9a1627807e3`；scan24与scan65/63源GS native不同，详细保留DATA_NATIVE_PROVENANCE.json。

相机中心为整数像素约定(W−1)/2，外参world→camera、x右/y下/z前；原COLMAP场景单位，**不是米**。9个构建相机roundtrip通过1e−8门槛。alpha仅用于已知遮挡/负证据可信度和疑似轮廓标注，没有near-z剪掉主体。

## 实现：哪些参数真正共享

marked保留全量来源账本；骨架只作为有序拓扑种子，原soft目标仍是损失。degree分叉、35°转角、16px弧长、4pixel尺度深度跳变切短链，不自动跨缺口。优先最大残差≤.6pixel的线；至少6点且误差减少30%、最大残差≤1pixel才选Bezier；否则拆分。point是残余而非冒充结构线。

关联比较有序采样、世界距离、切向、双向重投影和真实区间≥60%重叠；全组两两受界，每view至多一个区间。原同view重复记录保留alias，不能增加票数/墨量；3/12/47次相同观测产生同一资产。端点仅在同source实际观测junction共享，无盲目空间近邻连接。surface与疑似silhouette分开保存，冲突模式保留。最近曲线参数只是来源定位，不证明唯一跨视角曲线身份。

每primitive共享控制节点、横向宽度和opacity，按初始化弧长约1pixel间距中点采样小高斯。优化时mean=B(t)C、切向=B′(t)C真正改变；主轴sigma=.65×采样间隔，横向宽度初值.45p、范围[.25,.65]p，另一横轴.25p。控制节点位移≤.75p，p为来源z/focal的局部尺度。该界是工程代理，**不是统计校准的深度方差**，也不能修复超过该界的深度错配。疑似轮廓的判断仍是深度跨度/alpha启发式。

损失：mean_camera[MSE线上(D>.2)+MSE线外(D<.05且深度/alpha已知)+.2 MSE中间值]+.002归一化几何anchor+.0001平均opacity+.002(width−.45)²。未归属marked仍进入完整soft目标，不删除困难目标。隐藏/未知不能作为线外否决。ROI为32步几何+32步联合，全帧均12+12步，预算预先冻结。

投影协方差 S=J R C Rᵀ Jᵀ+.12²I，3σ截断及alpha合成。torch CPU用于几何导数，原native CPU EWA用于最终出图；黑色墨线的透射率乘积与前后alpha合成等价。visibility/q截断是离散分支，FD只检验光滑分支，不能声称穿越遮挡切换处也可微。原场景depth仅给定相机用于遮挡；novel arc没有原场景depth，视频明确标注。

## 真实数量及优化

|场景|原marked观察|line / Bezier / point残余|primitive|派生高斯|旧3view balanced高斯|短段合并比例|
|---|---:|---|---:|---:|---:|---:|
|scan24_full|208442|63122 / 2410 / 10596|76128|275312|182893|1.049%|
|scan63_full|76359|14820 / 1226 / 5125|21171|80232|68990|1.287%|
|scan65_full|155400|34136 / 2223 / 9261|45620|168864|147432|0.476%|


|单元|目标值初始→最终|实际移动的有效控制节点|节点触及位移上限|完成进程耗时 / 峰值RSS|
|---|---|---:|---:|---|
|scan24_full|0.119600 → 0.033332|94620/95192|26121|1068.9s / 3462.6MiB|
|scan24_roi|0.125685 → 0.028837|8289/8314|3736|130.3s / 3953.6MiB|
|scan63_full|0.081961 → 0.028306|32871/33086|6899|215.1s / 1150.7MiB|
|scan65_full|0.072222 → 0.026112|71813/72096|11956|241.9s / 1744.2MiB|


primitive减少不等于运行Gaussian减少：三个全帧场景的派生核都多于旧balanced，且关联比例低。COUNTS.csv与NUMERICAL_DIAGNOSTICS.json另列有效控制节点、单view核比例、未归属原因和完整camera诊断。耗时是本机CPU完成进程的实际耗时，不含之前中断/失败、动画和测试，不作训练性能对比。

ROI目标值 .125685→.028837，优化前/后确实移动控制点；固定窗口0000线上MSE .090558→.018947、线外 .050099→.007248。ROI不是heldout。v03只用0000，v04用三个固定窗口；因此额外来源是重要混杂因素，不能把相对v03全部改善归因于几何。另存roi_fair_comparison的同三source全marked raw控制。三个窗口原封不动，未挑更漂亮ROI。

## 实际视觉判读

已实际查看0000、0012、0036全帧对照。0000与0012的窗框和屋檐较初始化明显减轻黑团；相对旧balanced，笔划从粒点变成短曲线，屋顶纹理仍密。0036后侧窗户仍缺损、断线，前侧立面与塔楼仍有重影和悬浮笔划；不能认为已恢复完整唯一3D结构。整体不达到最终视觉验收。数值/重载门槛通过，按冻结方案迁移骷髅、水果作为泛化失败分析，不调整holdout参数。

已实际查看0000/0036/0048全帧。构建视角眉骨、眼眶、鼻骨的笔划更连续，比初始化黑线减少；但仍有错位双轮廓和桌面纹理。0036后脑顶部大段轮廓依然缺失、额顶处断开，未解决旧balanced的核心弱视角。有限控制点移动没有补入不存在于三build的观测；不能说头骨完整恢复。数值工程通过，以同冻结参数执行水果最后一个限定demo，之后停止生产。

已实际查看0000/0012/0024/0036/0048全部全帧。构建视角水果外形可辨、原始后方水果未按近景硬cut删除；优化比初始化减轻果皮黑团，但果皮纹理仍大量转为短曲线。0036的梨柄下出现错误横线、背侧外轮廓断续，局部不如原detector清楚；0012也有投影重影与漂浮线，不能算稳定融合。没有用heldout图作参数调整。原exact camera中主体本来部分超出画面，保留原全帧未另裁剪；novel动画另按冻结build相机姿态取景。

逐一看过三个场景的全部5个同相机对照及动画首/中/末帧。动画为同资产33个真实投影相机，不重新跑检测器，不是图像warp。完整主体在动画画面内，但没有原场景遮挡，背面线可透出；没有据此宣称时间稳定或唯一3D线。

## 测试、真实失败及复算

最终26个CPU测试通过（logs/23_FINAL_GREEN_26.log）。覆盖直/曲、近平行、2pixel近层、T/X/角点、扰动深度、missing/hidden/unknown、移动轮廓冲突、重复观测不加黑、真正新段增加容量、非传递关联、资产加载、source-chain到primitive弧参及渲染。近于1pixel的多层仍有歧义；2pixel测试通过不代表任意间距可分。

几何/宽度/opacity FD未放宽rtol1e−4/atol1e−6；Bezier控制点误差3.588e−9，线控制点最大2.096e−9，宽度5.533e−10，opacity6.843e−11。ROI最终torch/native最大差4.47e−8。合成几何-only目标 .109902→.005757，证明不是只调opacity。全真实单元从primitive NPZ重生成全部Gaussian数组完全一致，native重渲染bitexact；打包独立renderer重载中间动画帧也逐像素一致。

真实RED/GREEN保留：部分区间端点平均缩线→公共世界区间；同view重复47次变47组→alias幂等；NPZ反复解压→一次缓存；primitive弧参原字段不等价→保留原字段另算refined；renderer零支撑候选膨胀→零贡献移除。首次全图慢循环主动中断自己进程exit130；第二次出现All-NaN真实failure，捕获segments48353/68574不交叠区间并重放，修复真实60%区间重叠门槛，保持2独立primitive，未填空档。失败保留failed_attempt02、geometry_replay及logs/15、16、19。logs/17名含GREEN但内容确有失败，不能算通过；最终26测试才是验收记录。

CPU候选加速的真实ROI image/control/width/opacity差均严格0；scan24沿原枚举执行，scan65/63用等价加速。各实际执行版本另存code_versions及CODE_FREEZE；未伪改旧seal。首版建筑video副标题误用exact-camera模板，原版保留；media_corrected重渲染仅改字幕，33帧图像区逐像素一致。交付使用修正版。

## 文献启发与未实现

[SketchSplat §4.2–4.3](https://arxiv.org/html/2503.14786v2)启发共享line/Bezier控制点、Gaussian采样和可微拟合；没有复现其EdgeGS、2DGS、毫米阈值或论文训练流程。[Sketch and Patch](https://arxiv.org/html/2501.13045)的共享参数不等于运行核数减少；[LineGS](https://arxiv.org/html/2412.00477v3)的有结构输入也不意味着无序深度像素自动有可靠对应。其余3篇来源保留literature/，没有启动CAD面拟合、额外网络或moment matching大核替代线。

尚未实现：优化后可逆合并/拆分、自适应grow/prune、跨view长链全局身份、统计深度不确定度、轮廓随view移动的生成模型、统一的语义结构/纹理区分。当前多为过短、单view primitive，稠密纹理造成大量分叉，错误depth/轮廓位置又阻止可靠匹配；局部控制点界允许整理笔划却不能跨大错配恢复缺轮廓。这是本次负结果的具体限制，不应用更大opacity或硬票数门槛掩盖。

## 交付与停止点

ASSET_FORMAT_ZH.md说明editable graph、NPZ、自定义协方差PLY、全观察来源账本、optimized primitive arc和颜色/坐标。RUN_COMMANDS.md保留命令。results保留初始/优化两个版本，media_corrected交付3×33帧H264/yuv420p/faststart，完整解码通过。RESULTS_MANIFEST逐文件SHA，DELIVERABLE含代码/配置/测试/参数图/最终资产/图片视频；原大输入、环境、逐帧PNG及大中间cache只保留远端，不能把包中未收录称为删除。PREVIEWS只便于发图，不代替资产包。

本轮CPU任务完成即停止，最终状态HONEST_NEGATIVE、无live child、没有自动后续生产。实验实现和可追溯交付完成，不等于视觉目标或科学重建已完成。
