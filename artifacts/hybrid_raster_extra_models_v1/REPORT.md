# 新场景 transport：输入库存阻塞报告

**本次没有完成新场景渲染：已知项目/数据目录的有界发现中，可用的新 frozen vanilla synthetic NeRF checkpoint 为0。** 终态 `BLOCKED_NO_USABLE_NEW_SCENES`；早期审计说明的 `STOP_INPUT_BLOCKED` 只是同一停止原因的描述性别名。用户要求的零模型停止分支已触发；没有重训练、下载大型资产或重跑旧四场景。没有科学 PASS 或 NO_GO，也没有“更多有用细节”的新证据。

## 真实库存与缺失

| 新场景 | TRAIN 元数据 | 原生尺寸证据 | checkpoint 结论 | 本轮生产 |
|---|---|---|---|---|
| hotdog | 100个相机，全部既定F/C索引可用 | F1 PNG前24字节：800×800 | 未发现可用vanilla checkpoint | 未运行，49帧未执行 |
| materials | 100个相机，全部既定F/C索引可用 | F1 PNG前24字节：800×800 | 未发现可用vanilla checkpoint | 未运行，49帧未执行 |
| mic | 100个相机，全部既定F/C索引可用 | F1 PNG前24字节：800×800 | 未发现可用vanilla checkpoint | 未运行，49帧未执行 |
| ship | 100个相机，全部既定F/C索引可用 | F1 PNG前24字节：800×800 | 仅三个2DGS候选，均排除 | 未运行，49帧未执行 |

四个TRAIN元数据的精确路径为 `/home/u00134/cglib/data/full/{hotdog,materials,mic,ship}/transforms_train.json`，各文件SHA、FoV、预定索引的矩阵有效性与F1 header证据见 [库存](inventory/INVENTORY_DISCOVERY.json)。只读取F1尺寸文件头，没有解码像素，也没有打开原C图像。materials 的 `camera_angle_x=0.6194058656692505`，与其他三场景不同；不能套用旧Lego的焦距。由于没有checkpoint，本轮不生成虚假的生产K/w2c、物体中心或arc。

ship候选位于 `/home/u00134/3dgs_line/tier1/out/2dgs_ship/point_cloud/iteration_{7000,15000,30000}/point_cloud.ply`。它们有 `scale_0/scale_1`，缺 `scale_2`，属于二维surfel schema，不能冒充vanilla 3DGS。已保存文件SHA、header SHA、属性列表、点数与排除理由；在schema排除之后没有把它们载入renderer，没有补造第三尺度。其他发现包括旧lego/chair/drums/ficus、自建CAD/几何体及真实Truck，均不符合本轮新synthetic NeRF场景范围。

主要有界搜索如下。深度以根目录为0，不跟随目录symlink，剪枝TEST/mesh/图像帧缓存等目录；完整prune规则、逐项匹配与排除清单在库存中。

| 已知根目录 | 最大目录深度 | 初次匹配项 |
|---|---:|---:|
| `/home/u00134/cglib/outputs` | 6 | 11 |
| `/home/u00134/cglib/logs` | 5 | 1 |
| `/home/u00134/cglib/data/full` | 2 | 0 |
| `/home/u00134/3dgs_line/tier1/out` | 7 | 57 |
| `/home/u00134/3dgs_line/FeatureLineRendering/real_3dgs/outputs` | 6 | 0 |
| `/home/u00134/3dgs_line/FeatureLineRendering/tier1/out` | 6 | 0 |

这证明的是已记录搜索边界内的缺失，不是对整个home或机器的存在性断言。没有全home递归扫描。初次匹配包括 `point_cloud.ply`、`cfg_args`、`.pth`、`.ckpt` 和含asset的文件名；[同边界补查](inventory/SUPPLEMENTAL_FILENAME_CHECK.json)补齐 `.pt`，四类checkpoint扩展名/`chkpnt*.pth`均未找到，新候选为0。原assets定位使用原INPUTS、`src/common.py` 的模型路径、`out/point_feature_foundation/input_manifest.json` 及 `out/multiscene_foundation/{config.json,input_hashes.json,MANIFEST.json}`；这些文件的角色分别是输入资产记录、训练配置/输入哈希及产物清单。没有臆造一个不存在的同名 `ASSETS.json`。

## 冻结继承与科学边界

协议和确定性清单于提交 `f5abb6f44285bfa91104981798855420729386e0` 推送并核对远端，见 [推送回执](PROTOCOL_PUSH.json)。没有新结果图被生成或查看。[INPUTS](INPUTS.json) 明确 `selected_scenes=[]`、`scenes={}`、`expected_production_frames=0`，并逐项记录四个缺失场景与请求中的196帧未执行。空集合不等于196帧任务完成。

已读取旧PROTOCOL/REPORT/REPRODUCE、原INPUTS、源码及未跟踪out中的LOCK。旧LOCK的文件SHA为 `d5ec038e8ebc8a7160bc9e31ebb6ac8ce755fdbf1677a32ad55102a48c6a0926`；科学parameter hash为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。[锁的字节相同副本](INHERITED_LOCK.json)保留原A/B/C、六通道OUR dense B、作者独立原式、全局尺度及作者显示分母 `0.7533644223213196`。没有新F拟合、逐场景归一化或阈值救援。

[源码审计](source_audit/README.md)确认六个锁定文件与旧目录、LOCK一致；两个旧native二进制及898个两版源码记录均匹配。16个旧primary F seal的digest、context及各27项payload存在性核对通过；没有重新查看旧图像或重渲染旧模型。旧8条arc的264个pose按原构造重算误差为0，每条33 unique。这些是继承完整性检查，**不是新场景patched/unpatched校准**。新场景校准次数为0，不能宣称renderer已在新输入上验证。

若有合法输入，应保持SH0、白背景、同一次native traversal的A/B/C与作者读出；缺少训练时 `filter_3D` 必须披露，normal只能称splat/ray-plane normal。作者列应明确 `AUTHOR independent reconstruction — NOT official`；OUR dense和互补不是作者官方实现。raw original IDs与raw alpha*T、同源字段、有限性、provenance和等墨量控制均是生产前提，本轮未生成这些字段，不能由源码测试替代实测。

## 检查结果与缺失产物

45项相关旧CPU回归通过，涵盖读出/公式、贡献校验、seal损坏拒绝、camera契约、provenance、等墨量、视频fixture及访问审计的拒绝行为。旧测试硬编码临时目录在进程内定向到本轮新out的隔离sandbox，源码文件未改；合成fixture不计为模型帧。未启动3项native GPU fixture及4项旧GPU wrapper测试，原因是输入库存已阻塞。命令、退出码、scope见 [PRIOR_TESTS.json](PRIOR_TESTS.json) 及 [日志](logs/PRIOR_CPU_TESTS.log)。

新独立阻塞检查器采用实际RED→GREEN，拒绝伪造selected scene、漏掉缺失场景、已存在合格checkpoint却声称无模型、改动camera/锁/source、以及空清单藏有生产图像/raw/video/seal。检查器只可输出 `BLOCKER_CONFIRMED`，不能从0/0推出科学PASS。最终测试数、实际重放及访问审计以 [独立审阅](independent_review/REVIEW.md)、[核验](independent_review/VERIFICATION.json) 与 [FINAL.json](FINAL.json) 为准。

| 要求的产物/验证 | 实际数量/状态 |
|---|---|
| 新场景实测 | 0；四场景输入缺失 |
| 8F+8C+33arc | 0生产帧；196请求帧未执行 |
| 新scene原生校准 | 0；未运行 |
| 生产frame/raw seals | 0 |
| raw/continuous/typed/provenance字段 | 0；未生产 |
| 五列全分辨率、overlay、等墨量图 | 0；未生产 |
| contact sheets、首/中/末帧 | 0；未生产 |
| native未剪切视频、Telegram H264版本 | 0；未生产 |
| 实测视频full decode/distinct/hash | 不适用，不能以fixture视频替代 |

每场景的dense interior texture、轮廓连通、细节拥挤等视觉缺陷均为**未评估**。旧实验的面内密纹观察不能移植成这些新场景的观察；更不能推断其有用线条收益。没有人工标注、独立human GO、固定三维成功或时序稳定性结论。若未来具备合格checkpoint，合成场景扩展依然只是transport，不是新blind human evaluation。

访问证据须分范围解释：记录的独立核验进程及子进程有strace，未发现TEST/mesh或图像/视频读取；初次发现和源码审计由逐项读范围及代理记录支持，没有整会话系统调用trace，不能声称整会话完整取证。此次生产未启动，所以没有“production TEST audit PASS”。GPU启动0、GPU进程墙钟0。支持检查器的代码审阅触发1轮工程修复：补清单哈希关联和独立有界搜索集合复查；没有改科学计算或生产输入。时限记录见FINAL。没有中断作业、修改其他worktree/资产或全局配置。

本轮在库存阻塞处停止。恢复实测所缺的是这些场景的真实冻结vanilla checkpoint及可确认训练来源；现有TRAIN元数据、旧锁和只读native构建本身不足以生成合法新增结果。
