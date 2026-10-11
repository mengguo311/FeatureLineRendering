# 本轮实际执行与验证边界

本轮为诊断/有界证伪，状态HONEST_NEGATIVE指局部pilot尚未解决线稿问题；分析和交付已完成。没有启动v02剩余场景、47view新生产或任何GPU任务。

实际完成：128条旧证据hash校验；7张旧关键图实际视觉审查；六个build有向pair的旧vote精确重放；3个完整单源控制（60150/89512/58780高斯）；1个固定ROI内3个资产变体（all-pixel3626、skeleton初始2651、opacity拟合2651）；15张原生实数据Gaussian渲染（单源6、ROI9），加4幅合成重复观测渲染。6份新Gaussian NPZ及6份PLY是控制/局部变体，不是6个完整场景重建。完整source-GS模型没有改变。

9项核心TDD：先RED（7个缺实现错误、1个旧层距离控制通过），再8项GREEN。发现unknown负项语义缺失后，新增第9项真RED（错误损失.64），实现negative_known后9项GREEN。另加实际宽Gaussian的线外退化控制，最终10/10通过。原fixture与tolerance没有改到能过，RED/GREEN日志分别保留。实图三个相机的稀疏合成和native重渲染max abs约4.47e-8，小于预定2e-6。NPZ重载native渲染逐像素相同。

真实执行命令工作目录：`/home/u00134/3dgs_line/gaer_rade_depth_lift_v01`。每个Python科学命令设 `PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2`；OpenCV=2。Python为只读既有独立环境 `/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/env/bin/python`。

```sh
python3 reproduction/radegs_fusion_redesign_v03/audit.py
python -m unittest discover -s reproduction/radegs_fusion_redesign_v03 -p test_inverse_ink.py -v
python reproduction/radegs_fusion_redesign_v03/prototypes.py
python reproduction/radegs_fusion_redesign_v03/presentation.py
python -m unittest discover -s reproduction/radegs_fusion_redesign_v03 -p 'test_*.py' -v
git diff --check -- reproduction/radegs_fusion_redesign_v03
```

这里的python指上述绝对解释器。对应stdout和测试结果在logs。`prototypes.py`已完成时会主动拒绝覆盖RESULTS，不应直接重跑覆盖；验证可直接运行测试，复现实验须另建允许的独立输出子目录并显式配置路径。数值实验只有一次，没有参数扫描、heldout调参或好看ROI选择。

ROI依据画面中心固定 `[324,226,452,354)`。另两view的窗口由源ROI全部点投影bbox+8px生成，因此会包含源字典未覆盖的新表面/纹理。三个窗口全景参考和边框都保留，crop是明确的局部实验图。最初crop面板复用旧layout使文字挤压，未删除；后来新增`*_readable_3x.png`用最近邻3倍显示并重排标题，只改展示。不能把显示放大后的线宽当原生渲染宽度。

已实际用view_image查看三个单源全画面对照、三个ROI原crop及可读3倍对照、0000全景窗口参考、重复核合成负控。实图拟合损失虽小降，另两build仍颗粒/断线，判定no-go。没有查看新视频，因为本轮没有生成新视频；也没有新的0012/0036模型评估。

素材来源：v02原样提取的scan24三个30k NPZ；其字节与已有交付manifest一致。整个archive SHA沿用已冻结v02记录，本轮没有重哈整份1.7GB tar；逐个将要使用的NPZ/camera/cache/pair/model字节重新hash。原boundary和native EWA都未改，输入不是相机实拍RGB而是源GS渲染RGB。单位、相机、训练native来源见evidence中的相机/PROVENANCE副本。

尚未执行：有序chain跨view匹配、多模式geometry优化、曲率/宽度联合拟合、grow/prune、真实silhouette类别判定、已知fold的完整几何实验、全帧v03融合、新视角v03遮挡与泛化检验。FUSION_REDESIGN列的是这些步骤的具体方案，不能从本轮小损失下降推断它们已经可用。
