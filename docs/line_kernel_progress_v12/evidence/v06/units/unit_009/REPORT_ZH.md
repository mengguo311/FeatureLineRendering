unit009 的执行与交付已完成，但科学结论为 **PARTIAL：联合端口选择没有优于同条件greedy，也未证明新增的实质直线与曲线统一归组**。两臂得到相同39条连接、39个二叶身份；没有三叶路径。完整处理现有图不等于覆盖全部实际续接。

本次仅分析保存结果，没有拟合、重跑、渲染、修改源码或参数。权威退出见[COMPUTE_EXIT](../../orchestration/unit_009/COMPUTE_EXIT.json)：实际子进程rc=0、reason=null，08:53:35.712244至08:54:44.474517 JST；RUN_RESULT耗时67.952秒。没有用launcher退出替代子进程退出。

本轮从v05 unit016的ficus M4恢复285956个原核，使用v05 unit019的M5-on-M4候选。89486条记录中有756条成功endpoint，593条被保存的完整歧义mask排除，余163条形成148个完整分量、310个叶，最大分量4叶。两臂共享原始叶、端口、成本、弃权和整路径守卫；区别只有greedy与MILP选择。原核观测的多重性不占额外端口；本轮没有overlap池化、联合重拟合或新候选，fit_calls=0。

全部148分量完成，joint求解记录均为optimal，累计求解1.437秒；这只表示冻结数学问题中的结果，不表示物理最优。两臂edge_id逐行一致，98张对应PNG逐字节一致。每臂285956行映射、载体、谱系、选择、求解回执先checkpoint，随后保存原生全景；本次重新读取映射并核验两臂MAPPING_COMPLETE与FULL_NATIVE_CHECKPOINT文件哈希，均通过。保存的原字段审计报告数量/顺序及before/after不变；分析阶段没有重载原资产进行第二次数值审计。

|两臂相同的结果|数值|
|---|---:|
|assigned / UNKNOWN|118911 / 167045|
|相对M4新增assigned / 丢失|441 / 0|
|相对M4改变ID行 / 旧组拆分|507 / 0|
|复合身份 / 至少三叶身份|39 / 0|

对照间的撤回必须保留，不能把不同机制当累计改进。相对unit008 overlap greedy、joint，当前两臂均新增441个assigned，却撤回3413个；分别有239、244个参考组被拆回或重新划分。相对封存v05 M5，新增96、撤回3150，174个参考组重新划分。这里的“拆分”针对外部参考；M4前驱旧组拆分为零。原参考文件没有改变。详情见[REFERENCE_COMPARISON](scenes/ficus/REFERENCE_COMPARISON.json)。

实际原核全景是主要证据。两张joint图与greedy相同：碎片化叶片/盆体及长横向尖刺仍明显；固定原核几何无法通过归属改变去除尖刺。

![test_r_1原生全景](scenes/ficus/stages/joint/test_r_1_FULL.png)

![test_r_79原生全景](scenes/ficus/stages/joint/test_r_79_FULL.png)

以下数值来自保存的GROUP_STATISTICS，单位p；“支持”是路径坐标中的观测区间代理，连接器没有观测支持，也没有被画出来。

|身份|核数/叶数|支持并集|最长观测段|总gap / 最大gap|相对最大叶域外支持代理|
|---|---:|---:|---:|---:|---:|
|21870|316 / 2|69.105|1.758|34.676 / 1.414|4.115|
|71920|67 / 2|12.154|4.297|4.049 / 1.305|2.400|
|47878|63 / 2|9.502|7.295|1.008 / 0.695|0.917|
|47914|60 / 2|8.304|2.936|4.319 / 1.102|2.150|

21870虽然包含polyline叶，双视图主要呈长而近直的细线，M4参考已经有相同主体形状；不能当作新增可见曲线。316核中288核来自原parent2147，其余两个达到6核/2p的parent仅12核、9核；来源多样性不等于新物理边。47914是短直片段；其42/60核来自parent7143，其余来源尚未同时达到6核/2p。71920有两个实质来源，47878有四个，但统计本身不能证明延伸或安全统一。支持69.105p而最长段仅1.758p，尤其不能写成连续长边。

![21870新身份79](scenes/ficus/stages/joint/diagnostics/PATH_21870_833682ad_GROUP_test_r_79_CROP4.png)

![21870相同行M4参考79](scenes/ficus/stages/M4_reference/diagnostics/PATH_21870_833682ad_GROUP_test_r_79_CROP4.png)

![47914短直片段79](scenes/ficus/stages/joint/diagnostics/PATH_47914_0a65c62b_GROUP_test_r_79_CROP4.png)

最早的实际瓶颈是整路径几何可行性，而非MILP预算。greedy对163条候选接受39条，拒绝包括self_contact 74、vertex_turn 45、window_turn 3、port_capacity 2。joint的cut计数为self_contact 76、vertex_turn 51、window_turn 6；它检查了不同试探路径，不能把两套计数当同分母成功率。

重点64355/65064（record89309）确实进入两臂，但都被window_turn拒绝；112780/116525（record88114）进入后被self_contact拒绝。这两对不属于候选缺失，也没有被593条旧mask排除。两对在两个固定视图中呈短弧或弯曲片段；原像素少，无法据此推翻守卫或确认同一物理边。这里只能提出“独立叶q直接拼接可能限制共同归属”的待测解释，不能宣称守卫错误。

![64355/65064视图1](scenes/ficus/stages/joint/diagnostics/REFERENCE_64355_65064_CONTEXT_test_r_1_CROP4.png)

![64355/65064视图79](scenes/ficus/stages/joint/diagnostics/REFERENCE_64355_65064_CONTEXT_test_r_79_CROP4.png)

![112780/116525视图1](scenes/ficus/stages/joint/diagnostics/REFERENCE_112780_116525_CONTEXT_test_r_1_CROP4.png)

![112780/116525视图79](scenes/ficus/stages/joint/diagnostics/REFERENCE_112780_116525_CONTEXT_test_r_79_CROP4.png)

四个历史负例11/80709、16931/18768、112/205435、33117/201172均保存为上下文，分别关联旧parallel/branch/tangent/gap拒绝，不是真值标签。本次查看前两者的局部图，形状细小或存在多方向结构，不能据此宣称完整parallel/branch/depth安全。后两者未逐图复核，保持未验证。没有新增三叶案例、没有两臂成员差异，四个priority ID未成为选中复合路径；其参考图已保存。12个诊断案例、48个裁剪记录中没有记录为空或触及原生边界，但清晰度不足仍是视觉限制。物理身份、遮挡后的对应及held-out泛化均未验证。

建议继续一个独立实验：在同一ficus M4、同一完整163边图/148分量与旧mask上，检验“完整路径的共同有限辅助参数化”，与本轮不改叶q的拼接表示对照。每条可行端口路径由全部原核共同生成一个有限辅助模型；核、叶成员和原始几何不变，不绘制模型。保持所有残差、切向、平行、分支、转角、接触、gap阈值，且检查各叶投影次序及有限域，防止平滑隐藏错误。两臂继续共享模型与守卫、成本不变，只比较greedy/joint。它改变的是路径表示与其几何见证，不是声称v05不会polyline，也不是放宽守卫。若目标两对仍失败，或只增加同色/内部填充，保存负结果；不扫描阈值。详情与时间条件见NEXT.json，尚未实施。

来源采用父冻结快照，不依赖未来工作树HEAD：本次核对source_snapshot的72个源码文件和2个helper哈希通过；对应清单见[PARENT_RUN_FROZEN](PARENT_RUN_FROZEN.json)。CONFIG SHA256为a1fc0bee29f9440196368c3ded858b655cb86bf0dd794ae74c3665bd4093a6dd，decision SHA256为2930f9fdc870224aae14844d627041143bdac339bed9f5449cbdfc0c21c6c6cb。M4 STATE SHA为7d1457b144b0c58b8a3fe1fd1f1620e967158c1ace8326c64e6d996671378900。renderer.py SHA为ce24cd30d663e6f421064d83006f097b02a5cf6a74b20c177a905ca514caed93，libjoint.so SHA为033a973a71dc5364677a5bf0625f23dc4fe445b70257f04de7cb70cdccca84b0。批准命令及全部输入绑定保留在[RUN_REQUEST](RUN_REQUEST.json)和[CONFIG](CONFIG.json)：批准Python以-B执行port_scene_runner.py --config本单元CONFIG。本报告不重写原退出、配置、源码或科学产物；封存交由parent。
