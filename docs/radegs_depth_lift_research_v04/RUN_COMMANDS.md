# 实际命令与复算入口

工作目录：/home/u00134/3dgs_line/gaer_rade_depth_lift_v01

解释器：/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python

所有脚本common.py强制CPU、OMP/OpenBLAS/MKL/NumExpr各2线程，cv2/torch2线程；不调用CUDA初始化。外部launcher持有旧共享agent.lock，避免重复研究作业。

已执行的核心命令（前置PYTHONDONTWRITEBYTECODE=1）：

```sh
python reproduction/radegs_structure_primitive_demo_v04/audit_sources.py
python -m unittest discover -s reproduction/radegs_structure_primitive_demo_v04 -p 'test_*.py'
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan24 --roi
python reproduction/radegs_structure_primitive_demo_v04/media.py roi
python reproduction/radegs_structure_primitive_demo_v04/synthetic.py
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan24
```

上述`python`应使用本文专属解释器，不是系统共享环境。其他scene/video仅在其真实日志和完成seal存在时才算已执行。RESULTS_MANIFEST列明实际完成。

脚本对已经sealed的单元拒绝覆盖。复跑必须在新的任务根配置下执行，不能去掉防覆盖检查并写旧输出。原始NPZ、camera、boundary、native位置与hash见SOURCE_FREEZE.json；这些旧输入不打进新包。包内代码用于审查，可编辑primitive参数/重采样而无需再访问RGB检测器；原数据用于从头重跑。

## 本轮完整执行补充

工作目录 `/home/u00134/3dgs_line/gaer_rade_depth_lift_v01`。解释器均为 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python`，`PYTHONDONTWRITEBYTECODE=1`。构建脚本依赖SOURCE_FREEZE所列原数据绝对路径；会拒绝覆盖已封存单元。原失败不是当作成功skip。

```text
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan24 --roi
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan24
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan65
python reproduction/radegs_structure_primitive_demo_v04/run.py --scene scan63
python -m unittest discover -s reproduction/radegs_structure_primitive_demo_v04 -p 'test_*.py'
python reproduction/radegs_structure_primitive_demo_v04/media.py scan24
python reproduction/radegs_structure_primitive_demo_v04/media.py scan65
python reproduction/radegs_structure_primitive_demo_v04/media.py scan63
python reproduction/radegs_structure_primitive_demo_v04/provenance.py scan24_full
python reproduction/radegs_structure_primitive_demo_v04/provenance.py scan65_full
python reproduction/radegs_structure_primitive_demo_v04/provenance.py scan63_full
python reproduction/radegs_structure_primitive_demo_v04/diagnostics.py
python reproduction/radegs_structure_primitive_demo_v04/validate_outputs.py
```

每条实际运行的stdout/stderr在logs/，执行版本见CODE_FREEZE和code_versions；media首次建筑标签修正另保留旧版，最终用media_corrected。全帧24步，ROI64步；不是重新训练原GS。

下载解包后，仅重渲染固定资产无需旧RGB/depth（**因此没有原场景遮挡**）：

```text
python code/render_portable.py --root . --scene scan24 --frame 16 --output local_scan24.png
```

同一命令已对scan24/scan65/scan63加`--verify-frame`核对中间帧像素通过，见logs/portable_*.log。依赖numpy/scipy/Pillow与随包Linux x86_64 native；其他平台可据vendor/ewa.cpp自行构建，未宣称跨平台bitexact。
