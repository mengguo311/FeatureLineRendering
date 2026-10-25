# Unit008：边界留白与等长非边界留白

在固定Lego载体、H方向场及原GS纸底/S上，59条父路径分别生成边界留白B和非边界留白C；每条切除0.035世界弧长，共2.065，两个新子路径均非空。321条父路径保持；B/C各439条路径。新身份与即时H父路径、原父路径和face/bary均保存。

**完整物体收益未建立，不升级默认。** B将排除边跨面178→105、钝角20→12，但四DEV覆盖均低于原H，未稳定优于C。弱后侧linked覆盖A/B/C=31.93%/31.04%/30.91%，有支持长度661.536/603.828/606.755px。不能把少墨或较少转折当作成功。

- [完整中文报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/REPORT_ZH.md)
- [四DEV完整物体对照](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/ALL_DEV_MATCHED.png)
- [执行状态](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/STATUS.json)
- [配对独立审计](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/PAIR_READBACK.json)

3组针对性TDD先RED后GREEN，真实场景、独立审计和新进程41数组复放通过。原310475行与纸底/墨权重、M1/UNKNOWN不变；新路径仅有区域S关联，非逐路径Gaussian所有权。全部相机EXPOSED，三帧相机序列不证明时序稳定。

冻结复制脚本的循环名误替换在评估前发现；原源码保留，`execute_boundary.py`提供哈希固定别名用于evaluate/attribution，不改科学参数。原预期RED及所有旧负结果保持。

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B /home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v07/experiments/partwise_sketch_hatching_v07/boundary_unit/replay_boundary.py --out /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v07/units/unit_008/user_replay_001 --view orbit_241_24_5.3
```

输出目录须不存在。入口复用哈希固定GS source/paper/S并实际重画墨，不是重复cold GS。CPU两核、单数值线程、CUDA为空，使用现有环境。NEXT=continue：后续只读审查后，在Chair简单座面基线上验证一次标准编辑及新路径原ID支持，不继续扫描Lego留白参数。
