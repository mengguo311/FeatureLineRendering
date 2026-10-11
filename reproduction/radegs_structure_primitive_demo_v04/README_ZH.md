# 共享结构primitive驱动的新Gaussian墨线demo

此目录是独立实验代码，不修改源RaDe-GS。实验根与完整中文报告：

/mnt/hdd1/u00134/radegs_paper_reproduction_v01/structure_primitive_demo_v04

使用该根ENVIRONMENT.json指定的只读Python环境。common.py限制CPU两线程；依赖numpy/scipy/torch CPU/opencv/skimage/Pillow及既有只读EWA native。没有新的包安装或GPU初始化。

主要模块：build.py有序短链/账本/端点图，primitive.py有界关联与line/Bezier模型、Gaussian采样，differentiable.py稀疏EWA及几何梯度，run.py固定预算优化/资产重载/五相机渲染，media.py真实新相机视频，provenance.py原观察到合并primitive弧参数的显式追溯。原Spatial boundary.py不修改，原union和soft目标保留。

精确运行命令、RED/GREEN、失败重放、计划与参数冻结、各场景结果、影片与hash均在实验根。已有sealed单元拒绝覆盖；不得直接重新执行并改旧输出。原始输入与旧代码只读，在SOURCE_FREEZE列明且不打进交付包。

这不是SketchSplat或RaDe-GS作者完整复现；是借鉴结构参数化的新墨线实验。原始NPZ源/相机来自已冻结的RaDe-GS变体，原GS没有再训练。是否视觉达标以REPORT/STATUS中的真实审查为准。
