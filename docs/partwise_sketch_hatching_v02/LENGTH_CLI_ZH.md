# 完整 GT 台灯的底座长度操作

`length_cli.py` 接受带 SHA256 的完整434路径台灯资产，选择底座后设置绝对世界长度。本轮唯一评价值为0.18→0.12；API有界范围[0.06,0.24]，其他值没有视觉验证。长度是以原种子为中心的请求总弧长，遇到物理/部件边界或方向歧义时可能提前终止。输入为人工GT网格、GT部件与人工方向，不能当作RaDe-GS重建结果。

```bash
PYTHONDONTWRITEBYTECODE=1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python experiments/partwise_sketch_hatching_v02/length_cli.py edit \
  --asset /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/inputs/asset.json \
  --part base --length-world 0.12 \
  --output /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_010/user_length_preview
```

输出目录必须是unit010内尚不存在的目录；已有目录、历史目录均拒绝。CPU affinity[0,1]、数值单线程、无GPU；无需安装依赖。默认保存30/120/210/300°四幅512²完整台灯预览，也可用`--azimuths 30`只输出首幅。屏幕线宽、光照、部件标签、两方向层及原墨色不变。

只对原始150个面积种子中的已选75对行走，生成150条底座路径；260条灯罩与24条支杆从保存资产复用。采样原150个种子的随机序列是重建种子身份，不生成未选中的75对曲线。路径ID代表seed/layer身份，长度改变后其几何版本不同。

冷重生成：`length_cli.py regenerate --recipe <bundle>/recipe.json --output <new-directory>`。冷请求需要recipe、mesh、retained284、config，recipe中保存选中种子和墨色，不依赖已有目标路径。`length_cli.py replay --bundle <bundle> --output <new-directory>`读取已保存完整路径。配方绑定代码/依赖SHA、NumPy版本和输入SHA，版本不一致时拒绝执行。每次操作保存`EDIT.json`与输入/输出谱系；失败保留`FAILURE.json`和已生成文件。命令延迟包括读取、核验、目标重生成、保存及CPU重绘，不是实时性能承诺。

各版本配方仍是有界单部件操作；尚未构成可任意组合方向、密度、长度、交叉和全对象生成的通用编辑器。本轮判定见unit010的STATUS、METRICS、VISUAL_REVIEW和REPORT_ZH；继承的完整视觉NO_GO不会因文件重放相等而自动撤销。
