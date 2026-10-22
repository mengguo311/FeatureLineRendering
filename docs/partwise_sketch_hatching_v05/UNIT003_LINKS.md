# Unit003：完整 footprint 与原始 GS 控制

输出目录：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_003`。

新增 `footprint.py` 和独立 C++ 接受位置统计，保存全部原行在固定路径内、2px边界带及远区的 alpha×T 质量；在原路径支持上增加固定弃权规则。主比较在 Chair/Lego 实际完整源 GS 上按 BUILD 全图 RGB L1配平，包含新选择、原路径选择、同核数最近路径和打乱ID。源 PLY、几何、SH及行序不变。

结果与范围以该目录 `STATUS.json`、`REPORT_ZH.md`、`NEXT.json`、`SEAL_VERIFY.json` 为准。协议核心在 `source_snapshot/`；可运行交付源码在 `delivery_source/`。科学范围仍为 `UNCERTIFIED_CPU_MAPPING`，所有评估相机曾曝光，代理意图掩码不是语义或物理真值。

```bash
experiments/partwise_sketch_hatching_v05/run_footprint.sh \
  /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_003 \
  replay --scene chair --index 2 --operation tint \
  --output /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v05/units/unit_003/new_chair_replay
```

输出必须是新目录。`query`导出全部固定锚点和未删减的原ID支持；`replay --operation opacity`执行保存选择的真实源opacity诊断；改色的`--arm`可选`specific/previous_path/nearest_path/shuffled`。进一步命令见输出目录`REPRODUCE_ZH.md`。

主证据：`results/<scene>/FOOTPRINT_BINDING.npz`、`EDIT_SELECTION.npz`、各相机原始数组与`VALIDATION.json`。`ALL_EVALUATION_VIEWS.png`显示真实源RGB、作者意图、原核贡献、实际编辑及保存3D排线；`ALL_CONTROLS.png`比较四臂；`ALL_DIFFERENCES.png`以统一明确标注的热度尺度显示实际渲染差值。

此前 unit002 的局部性失败及本轮中断记录均保留，不替换或重新解释为成功。
