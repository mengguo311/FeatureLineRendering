# 执行记录

实现阶段运行 `CUDA_VISIBLE_DEVICES=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v`：43 tests PASS。

新增10项覆盖：几何平行侧接拒绝、跨深度识别、隐藏不计负/共同见证与局部拼票的区别、角点兼容、非局部奖赏克服负局部收益、转角保护和节点排他、确定性/null预算、cycle拒绝、有界保角简化、真实AA墨量匹配/不足报告。历史完整K、TRAIN-only、ID remap等测试也通过。

smoke 实际执行于 TRAIN1、128px；取前2048边、64个seed的独立小规模工程检查，32条路径，两次确定性相等。官方 renderer 成功；耗时1.85s，记录见 smoke.json。它没有用于改变参数，没有被当作主实验视觉结论。
