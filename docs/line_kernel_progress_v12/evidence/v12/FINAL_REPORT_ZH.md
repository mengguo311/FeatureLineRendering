完整scan65模型的3655个既有组已执行POSITION_ONLY：**126477个中心实际改变，675个assigned中心原值不变；152464个UNKNOWN（54.5262%）明确未处理。** 原模型279616行全部保留，成员映射和六个非位置字段不变。局部更平顺，但全景重复线、交叉和细碎线仍明显，整体清理收益有限。本单demo已停止，父级独立最终验收待完成。

![完整双视图原版与全组处理后](units/unit_001/FULL_MODEL_BEFORE_AFTER_TWO_VIEWS.png)

图中左列原版、右列FULL_POSITION_ONLY；上行0012、下行0036，均为完整777×581原生帧，不是单组ROI替代全模型。四幅均以279616核提交Gaussian CPU EWA renderer，含所有UNKNOWN及竞争结构。两相机读取同一份固定3D派生资产；原色、原opacity、原covariance、白底、floor=.12²、COLMAP W2C和深度合成协议相同，没有GL翻转、辅助曲线墨迹或表面遮挡删核。图像仍受原相机画幅/投影尺度限制。

|相机|完整原版|完整处理后|全部固定四分区|
|---|---|---|---|
|0012|[原生PNG](units/unit_001/images/ORIGINAL_0012_FULL.png)|[原生PNG](units/unit_001/images/FULL_POSITION_ONLY_0012_FULL.png)|[四区原版/处理后2倍图](units/unit_001/FIXED_FOUR_QUADRANTS_0012_2X.png)|
|0036|[原生PNG](units/unit_001/images/ORIGINAL_0036_FULL.png)|[原生PNG](units/unit_001/images/FULL_POSITION_ONLY_0036_FULL.png)|[四区原版/处理后2倍图](units/unit_001/FIXED_FOUR_QUADRANTS_0036_2X.png)|

固定边界x=[0,388,777]、y=[0,290,581]完整分割原帧；两个相机全部八区、前后16张crop及其2倍最近邻显示均保存。分析实际查看四幅原生整帧、全部八区，以及top3位移组的六幅隔离/六幅完整背景对照，共23个实际查看路径，详见[STATUS](units/unit_001/STATUS.json)。全景和分区没有缺交；细小、遮叠及画外局部仍缺逐组形状保真证据。

|组状态|组数|核数|
|---|---:|---:|
|SUCCESS|3655|127152|
|SKIPPED_NUMERICAL|0|0|
|FAILED|0|0|
|NOT_RUN|0|0|

每个组至少有一个中心改变；675个原值未变核不是漏跑组。完整成员表按非负edge_id枚举，已独立核验组行集互斥并精确覆盖127152 assigned行；没有把只含13个复合组的旧MODELS误当全组清单，也没有把UNKNOWN合成一组。本轮不改变归属、不增加观测、不扩并组。

全部组调用字节一致的v11 core.py数学：组内中心等权、确定性PCA主轴/横向基、保留原轴向参数及min/max域、三次Legendre横向拟合，二三阶ridge=.01，p=.001725801957946726（原场景单位）。仅取position_only.means并scatter，未采用v11最终细宽度/切向协方差规整。原控制点/arc_t只作来源。30579的596行输出与v11保存POSITION_ONLY逐位一致、最大差0；它只是集成回归，3655组覆盖由独立总账验证。

实际内存记录为一次全局means副本、3655次组内调用、累计127152局部行、最大单组596行，其他六字段共享只读。29批紧凑事务保存全部3655组模型/状态/行集与更新；完整NPZ冷载checkpoint在渲染前落盘。原版及失败证据保持原位，没有每组复制完整资产。

assigned位移[0,50,90,95,99,100]%分位为[0,0.079273449,0.289637008,0.381079943,0.683872113,2.996953933]p。最差组238627（489核）最大2.996954p，156151（169核）2.260554p，84607（184核）2.224945p。它们的弯头、浅凹或局部抖动变平顺，既可能有视觉收拢收益，也可能丢失真实局部形状；不能无参照地断言恢复了真实边。最大位移原行199137归属238627。

[238627双视图隔离之一](units/unit_001/WORST_238627_0012_ISOLATED_2X.png)、[另一视图](units/unit_001/WORST_238627_0036_ISOLATED_2X.png)、[完整背景](units/unit_001/WORST_238627_0012_CONTEXT_2X.png)；[156151局部](units/unit_001/WORST_156151_0012_ISOLATED_2X.png)；[84607局部](units/unit_001/WORST_84607_0012_ISOLATED_2X.png)。全部坏例路径见[分析报告](units/unit_001/REPORT_ZH.md)。

全景主要线网仍密集，组内平滑不会合并不同edge_id的重复线，也未处理54.5%的UNKNOWN。0012总alpha由27128.1875到27039.8203（-0.3257%），非白像素78424到78213；0036由31523.0488到31404.7305（-0.3753%），95881到95588。opacity未改变，但位置/重叠/合成会影响图像密度；减少像素、降低alpha、低拟合残差及SUCCESS计数都不是准确率或清理成功的证据。个别小图标题受尺寸限制；worst crop收据中的旧模板文字“all three”并非第三阶段，本轮实际只有两阶段，原始收据未改写。

保存输出复核确认：canonical文件SHA前后相同；所有279616行的covariance/opacity/colors/primitive_id/internal_piece_id/arc_t逐位相等；UNKNOWN包括means的全部字段逐位相等；完整MEMBERSHIP文件及所有字段逐位一致，原ID/顺序/总数不变。两个完整NPZ冷载所有字段一致，四次完整视图的内存/冷载rgb、alpha及深度输出逐位一致。[保护审计](units/unit_001/GEOMETRY_AUDIT.json)、[独立保存结果复核](units/unit_001/ANALYSIS_SAVED_AUDIT.json)、[渲染收据](units/unit_001/RENDER_RECEIPTS.json)可追溯。FINAL阶段重新校验封存166文件、源码快照、helper和原输入SHA均通过，未修改封存单元。

实际数值子进程PID3569946于2026-11-03T13:19:51.182643+09:00启动，2026-11-03T13:20:04.420463+09:00结束，returncode=0、reason=null、actual_child_exit=true。runner总13.0286秒，其中readiness0.4904、transform9.0225、render3.3128、audit0.2029秒。正常完成，没有deadline/quota/容量截断。这不是科学成功认证。[实际退出](orchestration/unit_001/COMPUTE_EXIT.json)、[RUN_RESULT](units/unit_001/RUN_RESULT.json)。review/build/analysis模型阶段的实际退出收据逐项保存在DELIVERY_STATUS.phase_exit_receipts。

真实vertical RED(rc1)→GREEN(rc0)保留；最终9项小型测试通过，其余检查诚实标为实现后回归。BUILD未运行完整资产拟合/渲染。[测试收据](units/unit_001/TESTS_RECEIPT.json)。CONFIG SHA256 `86b2751ef0c7c03e00e94d1cdc2155ecd041e3f4855e8ac3d89397554b50f31f`；DECISION SHA256 `32d67324a99bbe5944811416d895779b49912b6d2c36cedec77a606dbb1c9bf8`。11份源码快照及3个helper逐文件SHA绑定见[PARENT_RUN_FROZEN](units/unit_001/PARENT_RUN_FROZEN.json)，数学core SHA仍为`829ca35b9ae2cddb80e6b0d8b75cf181d3eca46eabeb3fc4bcc8a00d786af9fc`。

完整可冷载资产、原版回退、成员映射、实际更新行及每组模型/账本如下。GROUP_LEDGER.groups[].model包含3655个模型及参数；GROUP_INDEX给出每组原行范围，UPDATED_ROWS含实际变动行的新旧means；group_journal可按MANIFEST校验恢复。NPZ无对象pickle，Gaussian保留原7字段；所有报告图片链接为相对路径。

|文件|字节|SHA256|
|---|---:|---|
|[ORIGINAL_GAUSSIANS.npz](units/unit_001/ORIGINAL_GAUSSIANS.npz)|12,351,333|`3690a326224470faa3b673fe1c55f019211e0354f427f7fa86a974c4605dc130`|
|[FULL_POSITION_ONLY_GAUSSIANS.npz](units/unit_001/FULL_POSITION_ONLY_GAUSSIANS.npz)|12,354,309|`677d333965404ba6caa9873bfd17bc9b52abace0453bab25f7baabfce3d9e06c`|
|[MEMBERSHIP.npz](units/unit_001/MEMBERSHIP.npz)|1,030,254|`622a94c235957a788471e3ecea8aded18871058328f85524efa2425b6e9ccb85`|
|[UPDATED_ROWS.npz](units/unit_001/UPDATED_ROWS.npz)|7,099,932|`b1b5b5be68699345fce057bd0493eb147060c8b3034e3f93f30cf968ba4068f8`|
|[GROUP_INDEX.npz](units/unit_001/GROUP_INDEX.npz)|448,330|`3db0e2858e40017e9376bd58bc4870f35effb85a33d583bb8b0d1bcf9967a91a`|
|[GROUP_LEDGER.json](units/unit_001/GROUP_LEDGER.json)|8,790,844|`e2120f226955fde00cacbedbfd6f6527dd66d976b4a6e2c0b4749c4b1ba06d8d`|
|[group_journal/MANIFEST.json](units/unit_001/group_journal/MANIFEST.json)|8,975|`680fd81ac4c4499eb7add475422105ebed96ec537198b8e8832d7840e821673d`|
|[CHECKPOINT.json](units/unit_001/CHECKPOINT.json)|7,282|`68aba14ff70c5017e1b544045e2a6c2563aa98a322db724d3a3d9dd71fcc29d6`|

[运行请求](units/unit_001/RUN_REQUEST.json)、[配置](units/unit_001/CONFIG.json)、[输入绑定](orchestration/INPUT_LOCK.json)、[相机/源路径](orchestration/SOURCE_CONFIG_EXTRACT.json)、[失败分析](units/unit_001/FAILURE_ANALYSIS.json)、[NEXT=stop](units/unit_001/NEXT.json)一并保留。停止原因为SINGLE_DEMO_COMPLETE，不启动第二方法或修改参数救图。原始资产可完整回退。本交付是既有成员组的几何规整，不宣称物理身份、held-out或时间稳定性；父级将独立核验并交付实际模型。
