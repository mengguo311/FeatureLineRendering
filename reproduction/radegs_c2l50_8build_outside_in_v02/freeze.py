from env import *
def main():
 assert not (ROOT/'CONFIG_FREEZE.json').exists()
 cfg=dict(version='v02',single_bounded_pilot=True,scenes=SCENES,views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},historically_seen=True,not_GS_heldout=True,
  common=dict(near=.2,alpha_reliable=.5,alpha_unknown=.1,sample_stride=4,max_samples_per_view=24000,seed=1729),
  stageA=dict(isolated_border_fraction_max=.05,isolated_total_coverage_max=.60,border_band=.12,plane_seed_lower_y=.65,plane_hypotheses=768,plane_pool_cap=8000,plane_inlier_worldpixels=2.5,plane_mask_worldpixels=3.,plane_peripheral_fraction_min=.15,plane_min_each_view=40,plane_central_fraction_max=.35,plane_refit_steps=3,plane_min_seed_separation_worldpixels=6.,no_global_z_cut=True,no_component_deletion=True),
  stageB=dict(k_primary=3,k_diagnostic=5,arms=['shared_xyz_lab_width','shared_rgb_only','shared_xyz_only'],max_samples_per_view=16000,kmeans_n_init=5,kmeans_max_iter=100,spatial_scale_fraction=.45,lab_scale=[100.,30.,30.],thickness_scale_fraction=.005,thickness_weight=.35,soft_temperature=.45,minimum_posterior=.55,minimum_margin=.15,anchor_support_radius_worldpixels=12.,anchor_support_radius_fraction=.025,unknown_unseen=True,knn_surface_claim=False),
  visibility=dict(relative_z=.01,worldpixel_z=6.,stride=4,minimum_visible_fraction=.2,minimum_visible_samples=30),
  gates=dict(A_min_fraction=.01,A_max_fraction=.98,A_visible_retention=.90,A_visual_complete_required=True,B_min_stable_regions=2,B_min_region_fraction=.01,B_mutual_fraction=.75,B_max_unknown=.35,B_visual_parts_required=True,C_line_support_margin=.10,C_distance_px=2,C_shift_px=12,C_max_points=1536),
  budget=dict(cpu_threads=2,root_reserve_GiB=1,hdd_reserve_GiB=10,task_cap_GiB=8,unit_seconds=900,no_v03=True),
  meanings=dict(A='geometry-conditioned subject proposal, not semantic GT',B='jointly fitted coarse visible-sample region hypotheses, not physical parts',C='conditional original C8 boundary-support test',D='conditional source responsibility only; no source writes'))
 js(ROOT/'CONFIG_FREEZE.json',cfg)
 text='''# v02假设冻结：共同三维可见样本先生成粗块

这是科学结果前的方案。一次三场景pilot，零预定DEV调参轮，不自动v03。源码工程错误可保留失败日志修复，不改变冻结阈值。

## 为什么v01只呈现一个块，最先错在哪里
已读v01全部大纲、报告、A/B gate、subject/hierarchy/protocol和执行源码，实际查看三场景四视角完整图。建筑亮屋面和头骨暗骨/牙齿与背景外观混淆，主体阶段就错；Ficus外围明确，但先独立网格watershed再配对使大区身份不稳定。v02不重复图cut、网格watershed，也不把二值mask称多区。

## 文献与不同机制
Papon等CVPR2013 VCCS §3.1–3.4在共同RGB-D点云上用26邻接、XYZ/Lab/FPFH及有连通约束的局部kmeans，避免像素近而空间远的跨接；可合并多校准相机输入。原文完整PDF已取读：https://openaccess.thecvf.com/content_cvpr_2013/papers/Papon_Voxel_Cloud_Connectivity_2013_CVPR_paper.pdf 。我们借鉴共同3D样本与外观尺度，不复现VCCS，不使用未经认证normal/FPFH；本任务目标粗部件，不能把它的supervoxel或我们的聚类当语义GT。
Felzenszwalb/Huttenlocher2004 §2指出紧凑特征簇的分段恒定假设会把高变化真区域切碎，简单大边阈值不够：https://www.cs.cornell.edu/~dph/papers/seg-ijcv.pdf 。因此本轮主动保留RGB-only强基线与区域身份视觉否决，不用区域数或一致颜色判成功。v01Arbeláez/GrabCut/GaussianGrouping资料只读复核，未下载神经模型/训练GS。

## 输入、相机与可辨识性
唯一线原C2L50+8BUILD arms/C，源原完整SH/filter/opacity，source ID与line parent严格分离。线只作参照，A/B不读线墨构造mask/特征。DEV=0000/0000/train_r_80，AUX=0024/0024/train_r_7；两者联合生成；reserved=0012/0036及test_r_14/test_r_79，配置冻结后只查询不拟合。全为历史曝光，DTU还是GS训练视角，不是blind。DTU777×581 native RaDe深度；Ficus800² vanilla+CPU plane camera-z代理。完整fx/fy/cx/cy及W2C整数像素中心；不把center-z当表面、不用最小cov轴法线。

## A：多视角承托背景层，而非颜色背景种子
共同样本由两构建相机可靠像素(alpha>=.5/finite z>.2)回投，每4px取样，每相机最多24000，保持view/UV/z/p=z/sqrt(fx fy)。全图小alpha空域继续保留为coverage信息，绝非全scene alpha=主体。
若两视角外围12%可靠覆盖均<5%且全图覆盖<60%，判“孤立覆盖条件”，以source可见覆盖提议主体（Ficus可能适用；条件所有scene相同）。不填洞/不删薄叶/不留最大组件。
否则联合拟合外围承托平面proxy：外围含x两侧12%或底部12%，仅y>.65的点；768个确定性三点假设，pool<=8000，距离按每点worldpixel归一<=2.5。资格须每视角>=40点、外围覆盖>=.15、中央椭圆覆盖<=.35、中央种子距平面>6p；合格最小两视角覆盖最大者，3步SVD精化。它是可见depth样本的背景承托假设，不是源GS中心的真平面。以中央有高度样本多数符号定主体侧，仅距离>3p为candidate；接触带/无效深度/低alpha为UNKNOWN，不宣称物理背景。无候选则A NO_GO，不回退旧颜色cut或硬camera-z截断。可能把斜屋顶误作地台，必须全图gate否决。
同画面对照v01A、全scene alpha、v01RGB基线。冻结所有视角原尺寸，保留屋顶/窗/牙齿/叶间负空间。A数值非空(.01..98)、可比点保留>=.90之外，必须完整主体且无显著桌面/地台误入；视觉否决优先。未通过scene B/C/D NOT_RUN。

## B：共享生成模型真正产生多块，非独立颜色ID凑对应
仅A合格scene。两相机subject可靠样本，每视角同预算<=16000；共同世界坐标与每视角实际Lab外观、局部图像coverage内距离变换的有限宽度构成特征。X以共同1–99%bbox对角D和.45D归一，Lab按[100,30,30]，宽度项.35log(1+DT*p/(.005D))。宽度是投影代理而非真结构厚度，须检查rolling/遮挡误差。
在共同样本一次kmeans(K=3主、K=5诊断，5初始化/最多100次/seed1729)，从生成阶段共享centroid。输出softmax负平方距离(T=.45)；max<.55或top差<.15为UNKNOWN。以全部训练可见样本KD查询仅验证“有观测邻域”，半径max(12p,.025D)以外UNKNOWN，不把最近中心认证表面。不限制原GS到单一类，不输出GS物理标签。相同颜色/ID只是同一模型参数，不能算跨视角认证。
强对照：同样两视角和K预算的共享RGB-only、XYZ-only；另原v01FicusRGB-only层级原样并列（33/38等旧区域预算与新3/5不同，明确不是等K结论）。target使用自己的raw depth/RGB查询冻结模型，不用target更新centroid、阈值或ID。另将AUX标签确定性循环置换作“同颜色数字不是身份”负控，不作为真实算法。
多块验收：两方向可见资格>=20%和30samples、每大区>=1%主体、至少2区双方dominant>=.75且实际identity一致；保留视角也须通过。UNKNOWN不超过35%仅工程诊断。必须可见盆、主干、叶冠未互吞；建筑屋顶/墙体、颅盖/面颌若进入同样检查。颜色/面积相似不是语义GT，部件不完整则PARTIAL/NO_GO，不强制说3块已恢复3部件。多个不连通叶面可同粗叶群，但不称同物理面。不能以最漂亮K5替代预定K3；两级完整保留。

## C/D与停止
只有B实际完整大区门通过，才能同可见预算比较C8/no-line/shift12px的边界支持（最多1536点、2px距离、增益>.10且无错边视觉），不改mask或补线。C不过D NOT_RUN；D如获许仅source alpha*T软责任，不改原源。预算900s/unit、2线程、8GiB、root>=1GiB/HDD>=10GiB，每阶段实际检查。没有大区身份即停止，不制造新Gaussian模型/视频/物理primitive。

## TDD、预期图与可回放证据
先真实RED后GREEN：同色主体/台面可由几何分开；无平面不硬造；同source核可跨区UNKNOWN；投影fx/fy/W2C；遮挡/前方未知不负票；盆/干/叶解析toy保持多标签不吞；模型预测相机ID不可直接当对应；共享多块却不稳定仍NO_GO；源/线排除；固定源hash与字节。保留真实工程失败日志，不放宽容差。
每scene四全图RGB/C8真line/joint/v01/v02候选；A层失败不把其画成正式多区。Ficus等B许可场景输出K3/K5所有臂与match票据、主干叶缘误差/UNKNOWN，沿用英文标题固定色盘。全部native像素数据、visible/occluded/front/outside分母、来源UV、共享centroid/参数和未运行阶段。独立readonly replay、旧893Python/HEAD/index/status与source哈希前后验证，安全包与local commit，不push/merge。
'''
 (ROOT/'HYPOTHESIS_FREEZE_ZH.md').write_text(text)
 js(ROOT/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(ROOT/'CONFIG_FREEZE.json'),hypothesis_sha256=sha(ROOT/'HYPOTHESIS_FREEZE_ZH.md'),before_v02_scientific_results=True,code_files_at_freeze={p.name:sha(p) for p in CODE.glob('*.py')}))
 review('01_method_GO','GO：v01证据已实看；先测试联合可见depth背景承托假设，A通过后才共同3D样本分簇。这是不同于图cut/watershed的可证伪机制。共享簇身份仍需独立投影与视觉gate。此时尚无v02科学结果；不许根据reserved回调。',[ROOT/'HYPOTHESIS_FREEZE_ZH.md',ROOT/'CONFIG_FREEZE.json',ROOT/'INPUT_AUDIT.json'])
 state('METHOD_FROZEN',children=[])
if __name__=='__main__':main()
