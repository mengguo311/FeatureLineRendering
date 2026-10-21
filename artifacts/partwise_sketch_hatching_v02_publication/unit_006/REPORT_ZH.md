本单元完成唯一推荐步骤：完整台灯重建输入桥接。结论为 **SYNTHETIC_INPUT_READY_WITH_LOCAL_ADAPTER_RECONSTRUCTION_BLOCKED**，不是RaDe-GS重建或完整P1成功。

先完整读取BRIEF、原大纲851行，以及round001/002/016的报告、协议、NEXT和unit005交接。限域盘点9,045目录未发现可核验的灯具训练资产；六个历史DTU修改版RaDe-GS的scientificdone=false仍保留，29顶点/22面的scan63代理未准入。没有把vanilla PLY或GT台灯称为训练重建。

初始协议提交e6a54645；任何RGB生成前，源码审查发现官方ndc2Pix主点约定，保留PROTOCOL_INITIAL并将256修正为255.5，详见PRE_EVALUATION_REFINEMENT。最终协议/实现提交7928e342902cc269074f09aec946bb25a922b7d0，SOURCE_LOCK在渲染前绑定源码、输入、官方相机/FOV/像素函数及快照。没有看到新图后调整角度、材料、光照或门槛。

实际生成36训练＋12开发＋72测试，共120张512×512 RGB；仰角10/25/40度，训练30m度、开发7.5+90m度、测试3.75+15m度，精确互斥。RGB为固定世界光照的三材质局部Lambert表面图，不含NPR排线。每个视图均保存原始PNG；网格和每视图光轴深度、世界法线、部件及AA覆盖只放在oracle_only。GT来自已曝光人工作成网格，不是新盲测物体。轴对称、无纹理、无投影阴影等简化会影响未来重建，输入就绪不保证训练质量。

训练source目录dataset/train只有36张RGB和相机；官方transforms_test为空。开发与测试在evaluation独立目录，通用loader默认train，评估必须明确purpose=evaluate；训练输入不含测试RGB、GT标签、深度、网格或初始化点云。读取器的跨split正确性由独立全局验证负责，普通单split加载只检查该输入的路径、字段、哈希与相机。

初始独立验证保留INVALID及rc1：120张PNG完整解码，125/126项记录通过；9项故障控制检查held-out访问、路径逃逸、oracle字段、非PNG、非有限焦距、矛盾矩阵、重合角度和相机翻转。其中7项作用于自有loader，2项作用于全局验证；重合角度首先被冻结角度集合检查拒绝，未单独测试集合交集分支。它不导入生成器/渲染器，用独立球面三角公式核验相机与投影。唯一失败为原始官方相机函数把RGB转np.byte，当前Pillow拒绝signed RGB。随后先提交适配器616f2780和恢复协议3485b408，再评测仅np.byte→np.uint8的本地AST适配，结果RECOVERED_WITH_LOCAL_UINT8_CAMERA_ADAPTER。全部120图与原PNG及原signed数组的底层字节相同；相机/光栅映射最大投影误差3.69e-13px，所有RGB/oracle/相机哈希不变。外部官方源码、原validator、原INVALID与rc1不改写；不能称原版官方读取成功。ndc2Pix仅做CPU公式核验，没有CUDA运行。三部件每视图最小可见像素：{'1': 29160, '2': 638, '3': 7718}；全体顶点最小画面余量76.046993px。部件掩码由生产器输出，因此它们不是独立重建真值；相机/网格界限独立验证不代表光度正确性。

逐一检查三套全视图接触图和各split原尺寸首/中/尾，结论为GO_SYNTHETIC_RGB_INPUT_COVERAGE。具体观察与限制见VISUAL_REVIEW/DELEGATED_VISUAL_REVIEW。实际图像的完整性、部件可辨和可用隔离输入是主门槛；单帧新进程重放像素/PNG相同仅作次要确定性检查。

每帧渲染及保存中位0.567883s，P95 0.582890s，120帧合计68.148332s；包含RGB、oracle中心采样及保存。非24FPS或交互延迟承诺。CPU affinity[0,1]，数值线程1，无GPU、下载、训练、push或merge；旧结果和orchestration只读。unit005完整202项seal文件校验为True，当前task units占用123.57MiB，磁盘底线通过。

报告编辑辅助命令曾因系统无python别名返回127，未执行脚本体或改变科学输出，单独保留AUXILIARY_COMMAND_FAILURE.json。原始退出码保留于EXECUTION_*.json、原始日志在runtime且不纳入科学manifest。继承unit004 frame19支杆墨量比0.7521462443170939超过0.75的NO_GO及原图已复制保留；本单元没有修复或晋级该预览。旧rc1/143/UNKNOWN、round004/012/013 NO_GO、rim离群、17个hidden-profile观察、九ID时序覆盖缺口均未改写。

已把完整三部件GT台灯接到实际生成的36训练/12开发/72测试RGB＋相机输入，隔离GT oracle，并经全部图像解码、独立投影/划分/加载故障测试、本地适配相机读取和全视图目视检查。后续重建不再缺灯具输入与坐标接口；训练、重建代理和完整P1仍未完成。

下一步仅推荐25–35分钟的三部件实际排线时序审计：固定命名unit003资产及视角，独立可见性、明确ID、实际输出和覆盖统计检查旋转/缩放，保留漂移/删线敏感性控制与失败；CPU训练阻塞下仍能缩短完整P1的验证距离。不启动H2、不做参数扫选、不靠坐标哈希宣称稳定。STATUS/NEXT/SEAL和SHA256_MANIFEST位于本单元根目录。
