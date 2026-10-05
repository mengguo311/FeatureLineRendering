# v2 重现与恢复

只在 v2 根目录运行。Python 环境和 v1 的 vendor/native .so 只读复用，不安装或修改全局依赖。v1 `panels_high` 原 checkpoint SHA256 为 `cc440283b70bf62cd98dfedf24bf47383a147b70483deec4f849763f3f7847c6`；输入清单来自 `PRECHECK.json` 和 `INPUT_INTEGRITY.json`。新输出仅进入 `out/object_neighborhood_edge_control_v2`，新 stage ≤16 GiB、根盘留4 GiB、common Git盘留1.5 GiB。GPU0 外来进程存在时 runner 等待，不终止它。

```bash
cd /home/u00134/3dgs_line/object_neighborhood_edge_control_v2
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
research_python=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"$research_python" -m unittest discover -s experiments/object_neighborhood_edge_control_v2/tests -v
"$research_python" experiments/object_neighborhood_edge_control_v2/scripts/launch_production.py
cat out/object_neighborhood_edge_control_v2/STATUS.json
```

首次启动前已实际执行 `scripts/preflight.py`（生成并封印开发数据；原 checkpoint 原生全体/选定算子验证），并冻结 `SOURCE_FREEZE.json`。生产进程使用 `start_new_session=True`，PID 在 `production.pid`；coding agent 结束不会结束生产。禁止同时启动第二实例；已完成单元仅在 source/config/data/input/output/checkpoint SHA 全部一致时跳过。失败单元从该单元起点重算，中间 checkpoint/每轮日志保留；不声称任意迭代精确续训。原输入变化、生产源码变化或已封印输出变化会拒绝恢复。

若进程确已退出，可运行以上 launch 命令恢复；不删除 seal 绕过检查。`runner.py` 顺序执行 R0、F00/F01/F10/F11、可行时 outside 对照、v1 同目标凸求解、G00/G10/G01/G11 全部7000步、O-color/O-cov与同权限普通微调及等墙钟对照；无开发潜力时执行六个 R4 探针。R5 和正式多场景/三种子仍受证据门槛约束。新 TEST 无加载入口、目标未生成。低对比/远背景旧 TEST 未读取。

`tests/RED*.txt` 保存新增接口的真实先失败记录；`GREEN_all.txt` 与原 checkpoint 数值记录保存实际验证。`results/*.json` 保存全部迭代/每 epoch 全相机日志、P/D/gap、各角色逐视角指标与共同剖面。原始大 checkpoint、渲染 PNG 和执行 stderr 仅留忽略 out，不推送。

视频通过只读 v1 stage 的 FFmpeg 二进制编码，完整36帧原生开发渲染，H264/yuv420p/faststart；`results/MEDIA.json` 保存全帧解码SHA。同视角放大图三列为参考/B0/该方法，展示采用 sRGB OETF，数值评价在线性RGB。
