# 原生复现（不安装、不构建、不训练）

工作目录固定：`/home/u00134/3dgs_line/gaer_object_contours_v01`，分支`gaer-object-contours-v01`，祖先base`10bf025e3791cea8f4f2e30780ad3cec0681e323`。必须保留原PLY、前序已隔离二进制及元数据位置；所有SHA在INPUT_FREEZE.json。实际会话启动字段确认`gpt-6.1-sol/xhigh`，未仅凭配置声明。

实际执行命令（Python统一为已有vfsdgs环境，脚本自行固定GPU0/两线程/隔离缓存）：

```bash
cd /home/u00134/3dgs_line/gaer_object_contours_v01
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python experiments/gaer_object_contours_v01/freeze.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/run.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/shape_arm.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/evaluate.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/audit.py
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/report.py
```

run/shape/evaluate按逐scene/view/frame原子封印恢复；封印字节变动则拒绝覆盖。默认开发r_7/r_33；DEFAULT_FREEZE在实际r_1/r_14和33帧前保存。最终审计新增完整浮点原SH3导出，不修改已封印研究图或参数。第一次bootstrap失败的freeze/源代码/参考图已保存，不删除以“重新开始”。在已完成的本工作目录重复上述命令以跳过封印单元；ignored out原始帧是封印的一部分，不应删除。

独立进程回归（每条必须等上一条结束，避免不同PID占用GPU0）：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s experiments/gaer_object_contours_v01 -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -u experiments/gaer_object_contours_v01/audit.py
```

单元fixture允许显式的测试失败和数学检验，最终媒体全部真实GPU/native渲染。测试不会调用旧runtime或构建扩展；既有capacity_query_C和capacity_shape_C二进制按hash加载。运行时Python写审计拒绝stage外文件写入。原模型始终全N/fullSH3读入，s=0白核仍遮挡。原A/B/C/P不改opacity/cov/T；S改临时covariance后重算完整native状态。形状covariance携带于S NPZ，而非永久写PLY。

NPZ原生重放过程已在audit.py实现：加载全部原PLY行和camera_json，按strength设置colors_precomp=1-s、白背景；S先从原native geometry读全cov3D，用edited_original_ids替换temporary_covariance_rows，经隔离shape原生流水线投影/compositing。RGB叠加仅为原SH3_RGB × 完整native_RGB的展示，不参与拟合/科学指标。目标图单独标注DIAGNOSTIC_ONLY，未混入native墨线。

视频编码使用已安装imageio_ffmpeg所附的`ffmpeg-linux-x86_64-v7.0.2`，无系统安装。真实命令结构：

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/lib/python3.9/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2 -hide_banner -loglevel error -y -threads 2 -framerate 12 -i artifacts/gaer_object_contours_v01/media/lego/arc/native_ink/%03d.png -frames:v 33 -c:v libx264 -threads 2 -crf 18 -pix_fmt yuv420p -movflags +faststart out/gaer_object_contours_v01/tmp/replay_lego_native.mp4
```

audit.py对全部四个发布视频整段解码到RGB字节流，核对每帧尺寸/总数、实际h264/yuv420p流描述、moov先于mdat、对应完整PNG、33帧条带和每帧原生重放。保留原PNG和portable style，不以视频压缩结果作为拟合目标。

交付的实际Git命令：

```bash
git add experiments/gaer_object_contours_v01 artifacts/gaer_object_contours_v01
git commit -m 'Deliver native original-Gaussian exterior contour styling and audited arcs'
git -c pack.threads=2 push git@github.com:mengguo311/FeatureLineRendering.git HEAD:refs/heads/gaer-object-contours-v01
git ls-remote --heads git@github.com:mengguo311/FeatureLineRendering.git
```

确切最终SHA、干净status和其余远端分支不变核验见ignored `out/gaer_object_contours_v01/GIT_DELIVERY.json`。本阶段C/S容量与自动alpha目标只支持当前相机的风格化，不能替代旧ratio自动选择科学验证。未完成的科学门槛是窄线距离、局部宽度/杂墨与全部帧干净视觉；没有推导“不可能”或进一步救援实验。
