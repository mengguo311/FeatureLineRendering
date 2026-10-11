# RaDe-GS 深度驱动固定三维高斯线：研究成果快照

## 结论

**HONEST_NEGATIVE。工程实现已完成，但视觉上可靠、完整的多视角结构融合尚未完成。** 不应以损失下降、通过合成测试或 primitive 数量称为重建成功。

源 GS 冻结；原 Spatial RGB union 提供二维 soft 线证据，同相机 median camera-z 回投。新方法组织有序短链，拟合直线 / 三阶 Bézier，沿共享控制点派生固定 object-space Gaussian 墨核，实际优化几何、线宽与透明度。不是逐帧二维画线，不是挑选原 GS IDs，也不是 SketchSplat 的忠实复现。

## 已执行

- 原 Spatial RGB Gaussian demo；balanced 更多视角实验部分完成；strict 对照会随视角增加删除大量主体。
- v03 bounded diagnosis：只调 opacity 的局部控制不能修复跨视角缺口。
- v04：建筑 scan24、头骨 scan65、水果 scan63 三个全帧场景＋固定 ROI，9 个合成场景，初始/优化可编辑参数和派生高斯。
- v04 构建/优化仅 0000/0024/0048；0012/0036 未参与构建，但已被看过且属于源 GS 训练视角，不是盲测或 GS held-out。
- 父级重新运行 v04 26 个 CPU 测试全部通过；下载核验 458 个打包文件哈希；3 段固定三维资产动画共99帧完整解码。
- 父级生成3场景×5同相机 RGB 叠加：原 GS RGB、黑色新墨核合成、红色对齐诊断。合成公式 RGB*T；不调每视角透明度。不是两套 GS 统一深度排序的联合渲染，源场景遮挡继承 exact-camera 墨核渲染近似。

## 失败与限制

约98%–99%的派生核仍仅单视角来源，跨视角曲线身份不足。建筑屋顶纹理/重影、头骨0036后脑轮廓缺失、水果纹理/漂浮线仍明显。三个全帧场景派生核均多于旧3view balanced，参数共享不等于运行核压缩。novel动画没有原场景深度遮挡，不证明时间稳定。未实现长链全局对应、自适应 grow/prune、统计深度不确定度、随视角变化的轮廓生成模型。

## 仓库内容

- `reproduction/`：隔离实验代码和测试，保留历史修复与负结果路线。
- 本目录 `REPORT_ZH.md` / `ASSET_FORMAT_ZH.md` / `RUN_COMMANDS.md`：v04实际报告、资产格式与执行入口。
- `fusion_v03/`：此前深度诊断与负结果报告。
- `literature/`：六篇文献的机制/迁移限制与引用账本。
- `previews/`：建筑/头骨/水果的同相机 RGB 叠加；三列为原 RGB / 黑墨叠加 / 红墨诊断。
- `make_rgb_overlays.py`：父级合成脚本，路径相对于本地交付布局；需先取得交付中的 RGB / optimized ink 图。
- `PARENT_TEST_VERIFICATION.log`：独立复测记录。
- `RESULTS_MANIFEST.json`：远端完整输出来源/哈希清单，不代表其列出的所有大资产都在 Git 内。

代码带原隔离工作树和HDD绝对路径，完整从头复算需原模型/输入、相机及专用Python环境；这不是零依赖即开即用工具。随包native为Linux x86_64，其他平台需重建。报告含远端路径仅用于定位来源。

## 大资产保留位置（不入Git）

远端根：`/mnt/hdd1/u00134/radegs_paper_reproduction_v01/structure_primitive_demo_v04/`。

- `DELIVERABLE.tar.gz` SHA256 `be6b780129b032a19817c730aa74c01d9e93623581fb4eb12e2ef3878a478091`，完整代码/资产/证据，290496934 bytes。
- `PREVIEWS.tar.gz` SHA256 `dcda575dc9baafd989d0ef2a2199d44a38b6584ed3f9f6fcc969a5b965f26f7f`，24684872 bytes。
- 本地已核验副本：`/Users/menakuniay/next_npr_results/radegs_structure_primitive_demo_v04/`。

Git不收训练数据、checkpoint、环境、原始NPZ/PLY、大包、逐帧PNG、凭据或全量运行日志。旧证据不删除、不覆盖。此快照推送研究分支，不合并主分支。没有自动追加47view生产、源GS训练或mesh工作。
