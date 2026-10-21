本入口将已有人工作成的三部件台灯变成合成 RGB＋相机重建输入。它只证明输入准备与接口可读，不代表已训练 RaDe-GS、已得到重建代理或完成 P1。

当前数据根为 `/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_006/dataset`。

- `train/`：36张训练RGB、规范相机以及官方 NeRF 格式的 `transforms_train.json`。`transforms_test.json` 刻意为空。后续重建的 source path 应只指向此目录。
- `evaluation/dev/`：12张开发图及独立相机；`evaluation/test/`：72张测试图及独立相机。测试RGB不得进入几何、分部或风格优化。
- 数据集的兄弟目录 `oracle_only/`：人工作成的原始网格、三部件标签，以及合成视图深度／法线／部件／覆盖。它仅用于诊断，不是重建代理，不得用于初始化训练几何或作为主结果输入。

三仰角固定为10°、25°、40°。训练方位30m°，开发7.5+90m°，测试3.75+15m°，精确互斥。512×512、焦距600、距离4.5、主点255.5；世界y向上，规范相机x右/y下/z前，保存光轴深度z。OpenGL相机到世界矩阵由规范相机的C2W右乘diag(1,-1,-1,1)得到。主点采用官方栅格器ndc2Pix的(size−1)/2约定；首次协议草稿的256值在任何RGB生成前纠正，原稿及修订证据保留。

RGB是固定世界方向的漫反射＋环境光、三种固定材质、白背景的合成渲染，不包含排线、结构描边、纹理、镜面、投影阴影或AO。继承几何轴对称且纹理稀少，这会限制未来重建，不能因为相机／图像检查通过就保证重建成功。所有视图均要查看，只做数据完整性审查，不据测试图修改材料或相机。

可在授权worktree用现有CPU解释器实际加载训练输入：

```bash
taskset -c 0,1 env CUDA_VISIBLE_DEVICES='' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python -B experiments/partwise_sketch_hatching_v02/reconstruction_dataset.py /mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_006/dataset
```

开发／测试读取必须显式指定 `--split dev --purpose evaluate` 或 `--split test --purpose evaluate`。默认只读取训练RGB；返回值仅有RGB和相机字段，无oracle路径。单split loader负责输入路径、字段、哈希、图像、相机一致性；跨split互斥由独立全数据验证器审计，不能把loader的单split检查误称为全局验证。

官方接口初次验证只提取并执行本地原始 `readCamerasFromTransforms`、`CameraInfo` 和FOV函数，不导入训练器或调用GPU。完整 `readNerfSyntheticInfo` 在缺少初始点云时会向输入目录写随机 `points3d.ply`；未来获准训练时需要创建单独可写训练副本，保留sealed输入，不得以GT网格代替初始化。本单元没有训练或生成初始点云。

生产器和封存器固定写unit_006，防止误改历史单元。生产命令与原始退出码见unit_006的执行收据；新单元若需重新生产，必须在新授权输出目录迁移边界并保留本单元。通用只读loader可直接读取本数据，不需要迁移。

实际依赖兼容失败：原始官方相机函数将RGB转成有符号np.byte，当前Pillow拒绝三通道signed数组，原验证返回1及INVALID保留。新 `radegs_camera_compat.py` 仅在抽出的AST中将该单一dtype改成np.uint8；不修改外部官方源码。恢复协议先于适配评测冻结，全部120图验证适配结果与PNG及原signed数组底层字节相同，相机/投影阈值不变。只有本地适配版获得兼容结论；未来完整训练需要在另行授权的可写源码副本集成该dtype修复，不能直接宣称原版在本环境可运行。
