# Unit003：固定路径的中心线可见区间对照

冻结实验已完成。新后端小幅恢复自身墨支持，但四个DEV完整物体和九帧短弧未建立可读性收益；**不替换旧默认后端**。

- 唯一主变量：原逐片元绝对锚面深度检查，改为中心线可见区间胶囊，并保留单侧前景深度保护。
- 固定Lego作者region4、交叉层、三维路径及身份、1px线宽、2×采样、0.004容差、M1/UNKNOWN、20122个原核权重、原GS纸底与原ID责任S。
- 四BUILD实际目标墨量配平：旧尺度0.95、新尺度0.9313025763；原强度结果同时保留。
- 241°/24°配平自身缺失长度115.15→103.04px，仅恢复代理可见总长度1.44%。原纸底照片残留和短碎笔触仍明显。
- 全部13份记录墨层远区L1为0；源纸底固定使旧/新远区绝对损伤相同，不能据比例分母变化宣称局部性改善。

证据根目录：`/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_003`。
详细报告见该目录`REPORT_ZH.md`；整物体图为`ALL_DEV_VIEWS.png`和`ALL_ARC_FRAMES.png`，实际相机短弧为`media/visibility_arc_ffv1.mkv`。
逐stroke自身支持、拒绝原因和端点分类在`ATTRIBUTION.json`、`SAMPLES.npz`、`STORED_PATH_ENDPOINTS.json`。不以其他stroke重叠提供支持信用，也不把计划间隙当bug。

3项针对性TDD先RED再GREEN。54个输入、实验/复算/冷重放/媒体源码与相机在评估前冻结；4BUILD和13DEV/arc旧臂逐数组保持历史结果。独立复算像素及原ID alpha×T责任，236°冷重放实际完整GS两次，九帧视频全部解码逐像素一致。初始RED之外科学阶段回执均rc0。旧失败不变，scientific_seal=false。

可重复缓存复放，`--name`必须是尚不存在的`replay_`目录名：

```bash
/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v06/replay_visibility_cache.py --unit /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v06/units/unit_003 --kind dev --index 1 --name replay_user_001
```

CLI重算冻结代理墨层并使用真实GS缓存及S，不重新渲染GS；两次实际GS冷重放单独保存在`cold_replay_001`。本机Python、Open3D、旧只读缓存、原PLY及代理资产仍是外部依赖。

新增渲染比较代码从本工作树`render.py`的胶囊光栅和深度公式适配，旧文件不变；冻结源码与来源哈希在unit003协议中。这里只证明有限代理实现和复现，不证明原生Gaussian墨线、物理附着、语义归属或一般时序稳定性。

NEXT建议同支撑饱和纸底容量对照：仅在既有选核上把纸底权重由q改为1，保留UNKNOWN和原核几何，判断源层照片残留能否减少；不同源效果预算必须明确，不能把上限实验当作选择优势。
