# TRAIN → FREEZE → NPR 四场景实验

**执行中，不能作为196帧完成证明。** 当前训练与渲染状态见 `STATUS.json`；最终实际计数、资格和文件哈希将写入 `FINAL.json`。所有新产物位于本工作区指定的 `artifacts/hybrid_raster_trained_models_v1` 和 `out/hybrid_raster_trained_models_v1`。

## 实验边界和来源

四个模型均按固定 seed1729、30000步标准 vanilla3DGS 采集，保留7000和30000检查点。训练为原生800、白背景、SH3、原始 L1/SSIM 光度损失及默认增密；没有 normals/depth/mesh/NPR 损失、人工标签或结果驱动重训。初始化随机点及缓存只写本工作区。沿用旧 Lego 实际设置中适用的部分；必要差异是旧流程86个 TRAIN 加16个 VAL诊断，本轮严格用全部100个 TRAIN，禁止 TEST/VAL 读取，并增加 TRAIN-only loader、隔离、日志及可核验恢复。

**C 相机参与 vanilla GS 训练；仅对 NPR 参数拟合留出，不是盲测或泛化评估。** 本轮 NPR 没有任何新参数拟合。TRAIN RGB 对照仅用于检查输入和训练是否灾难性失效，不能作为几何或泛化证明，也未作为线条优劣门槛。

协议、输入哈希、目的地、F/C精确相机和唯一arc算法在任何GPU操作前提交推送。旧arc算法依赖最终检查点中心，故采用明确的两阶段冻结：模型完成后封存checkpoint哈希，再计算并提交推送全部49个精确pose，之后才启动NPR。F为1/14/27/41/53/67/79/93，C为7/21/33/47/59/73/86/99；arc固定C7→C33、33个不同pose。所有渲染800×800、主点399.5；Materials使用其独立FoV。

实际采集源为上游固定提交 `472689c0dc70417448fb451bf529ae532d32c095` 的17个git blob，保留许可证。外部只读工作目录存在未提交renderer改动，合成夹具发现后在最后允许的工程修复轮次中改为从immutable blob提取；真实场景训练均在修正冻结提交 `206b9ebf3e90d4766fb1b3e32ebfba491e390f4e` 推送之后启动。三个明确修复轮次和原始失败证据完整保留，未把夹具失败计为科学负结果。

## 实际采集结果

| 场景 | 迭代 / seed | Gaussian数 | 训练秒数 | 30k PLY SHA256 |
|---|---:|---:|---:|---|
| hotdog | 30000 / 1729 | 148610 | 474.685 | `950a77982449056390a709c097b920c1121da5680fd5602a262a8fc1b6e58765` |
| materials | 30000 / 1729 | 282537 | 486.267 | `9c05502d45a5572ec5d5be80011075a2d09369c2c4c04913f63a79070cfd4945` |
| mic | 30000 / 1729 | 311562 | 496.476 | `13255fd1207c031c5542e25cbbdf9596dbe88a0212fd7e383a9010852d6501ca` |
| ship | 30000 / 1729 | 320284 | 657.632 | `8bbcc880fbe5c57c5d65cc7834caf1e285e87616fb7b3c09dcccae12b45fba8b` |

四场景均为一次fresh训练，无resume或重训；总训练进程墙钟2115.060秒。保留8个PLY、8个完整恢复snapshot、120000条有限loss及24张TRAIN诊断图。独立 `ACQUISITION_FINAL.json` 对四场景重新执行完整核验并PASS；精确路径、CLI、config、资源、timestamps、7000/30000哈希及大文件索引见 `acquisition/results`。

## 冻结的NPR比较

继承旧v2六个科学源和patched/unpatched隔离二进制，均只读、逐字节核验。parameter hash为 `6c4ef4afa648f54794d7094a7b21368a89e14cdbc792766441aa3d3639d487c9`。A为灰度RGB/depth/alpha dense edges，B为OUR dense六通道，C为自动互补；AUTHOR为Hao–Mukai Eq.1–5独立重建，**NOT official**。尺度和作者增益固定，不做新F拟合或逐场景调整。

各臂共用同次native traversal的白底SH0 RGB、原Gaussian行ID及未重归一化alpha*T；fullSH训练后故意只读SH0。缺少filter3D，raster/splat normal不是GT表面法线。每场景先做全部8F patched/unpatched校准；校准无效属于工程资格失败，不可解释为科学负结果。墨量更大或B-only像素更多不代表线条更好，本实验不主张fixed3D或时序收益。

## 当前可见训练缺陷

- Hotdog：固定F1/F41的盘沿、面包和芥末带基本对齐，未见黑屏、整体错位或主要对象缺失；面包细纹和盘面反射略平滑。
- Materials：固定F1/F41的球体、切口和底座基本对齐；镜面环境反射细节变软、局部高光略糊，粗糙金属细颗粒被平滑。反光/折射外观的视角相关近似不能证明几何正确。
- Mic：固定F1/F41中主体、支架与电缆基本对齐，网罩孔格大体保留；局部网格灰度和细高光仍有差别，表面过渡较平滑。
- Ship：固定F1/F41的船体、桅杆及容器整体对齐；F1水面高频波纹明显变软，F41船侧木纹、炮口及部分细索模糊，水面反光仍有差别。保留缺陷，不追加训练。

上述为实现代理对生成的TRAIN in-sample对照图的观察，具体路径及哈希见 `TRAIN_RGB_VISUAL_REVIEW.json`；没有据此调参。NPR图像尚未生成，不能预写线条质量结论。

## 核验与限制

CPU RED→GREEN覆盖严格TRAIN loader、seed、checkpoint/resume和camera适配器；92项最终选定的新/相关旧测试全部通过，另有真实两步合成CUDA训练集成通过，详见 `independent_review/TEST_INDEX.json`。失败夹具与重跑不计入通过总数。独立checker逐字段检查PLY（含NPR忽略的45个full-SH字段）、30k loss记录、唯一fresh launch、GPU归属和实际syscall trace。具体检查以 `independent_review` 下报告为准；早期只验证工作文件身份而未证明git blob身份的证据缺口已明确更正，旧报告仍保留。

访问审计只覆盖记录进程的open/openat/openat2/creat及子进程退出，不声称整个会话均受trace覆盖。标准Scene会无条件打印“Loading Test Cameras”，本轮该列表为空；是否访问TEST由实际trace及严格loader核验，不能从这条打印推断。TRAIN元数据与400个文件hash在GPU前冻结；训练实际允许全部TRAIN像素。NPR阶段不读取数据集源RGB，不接触TEST/VAL/mesh。人类科学评审保持pending。

当前本盘容量有限，外部新目录写入仍待用户授权；未写外部磁盘、未删除旧资产。空间守卫保留至少1GiB余量，若实际产物不能容纳，将保留已封存产物及明确失败计数，不降分辨率、不减帧、不删字段来制造完成状态。
