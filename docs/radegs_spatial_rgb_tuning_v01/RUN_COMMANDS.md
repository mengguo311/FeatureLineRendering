# 实际运行与重放

工作目录：/home/u00134/3dgs_line/gaer_rade_depth_lift_v01
只读解释器：/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python
代码目录：/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_spatial_rgb_tuning_v01
cpu_entry.py固定2核亲和性/数学线程并禁写旧pycache。

以下命令均已真实执行（RED测试第一次因detector尚未实现返回1，GREEN及最终测试返回0）：
```
PY=/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python
CODE=/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_spatial_rgb_tuning_v01
"$PY" -B "$CODE/cpu_entry.py" "$CODE/freeze.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/test_detector.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/run.py" --stage pilot
"$PY" -B "$CODE/cpu_entry.py" "$CODE/selection_boards.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/run.py" --stage rest
"$PY" -B "$CODE/cpu_entry.py" "$CODE/analytic_controls.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/contrast_control.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/restyle_analytic.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/selection_boards.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/verify.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/test_detector.py"
"$PY" -B "$CODE/cpu_entry.py" "$CODE/apply_preset.py" --input /mnt/hdd1/u00134/radegs_paper_reproduction_v01/depth_guided_native_dtu_v01/scenes/scan24/inputs/0000.npz --preset C2U20 --output /mnt/hdd1/u00134/radegs_paper_reproduction_v01/spatial_rgb_tuning_v01/cli_replay/scan24_0000_C2U20
```
freeze与run会拒绝覆盖已有冻结/完成单元。要单图复算，用apply_preset并指定本任务内新的、尚不存在输出目录；可把input换成便携input_rgb_float32.npz。run只生产检测图，不存在3D调用。代码的common.py为当前任务路径适配；异机需指向解包目录/输入路径，不要修改旧实验。
