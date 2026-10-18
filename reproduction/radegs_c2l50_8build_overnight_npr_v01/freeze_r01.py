from env import *
CFG=dict(round='r01',mechanism='camera-upright constrained support layer and axial visible-cross-section bottleneck',seed=1729,near=.2,alpha=.5,stride=4,
 pose=dict(max_rms_degrees=5,maximum_eigen_ratio=.05,maximum_plane_tilt_degrees=20),
 plane=dict(hypotheses=768,pool_cap=8000,inlier_p=2.5,mask_p=3,peripheral_min=.15,counts_min=40,central_max=.35,central_separation_p=6,refit=3),
 section=dict(bins=32,min_points_per_view_bin=8,min_segment_bins=4,min_valid_fraction=.85,width_middle_ratio=.65,log_sse_improvement=.35,cut_view_disagreement_bins=3,boundary_unknown_bins=.5,profile_smoothing_sigma_bins=1,minimum_view_count=2),
 gate=dict(subject_complete=True,no_large_background=True,min_stable_regions=2,mutual_fraction=.75,min_visible_fraction=.2,min_visible_count=30,max_target_unknown=.35),
 views={s:dict(fit=[DEV[s],AUX[s]],reserved=RES[s]) for s in SCENES},pose_only_8_build=True,region_fit_images=2,original_C8_immutable=True,source_GS_immutable=True,max_unit_seconds=900,maximum_round_minutes=65,reserved_historically_seen=True,zero_parameter_tuning=True,controls=['v02 same-view A','v02 K3','v02 RGB-only K3','v01 RGB-only','fixed equal-height thirds, same 3-region budget'],downstream='C/D/NPR only on a later explicitly frozen round after actual gate, NOT_RUN in r01',stop_new_round_at_JST='2026-10-19T07:40:00+09:00',deadline_JST='2026-10-19T08:00:00+09:00')
TEXT='''# r01 方法冻结：共同竖直方向与截面瓶颈，不再颜色聚类

## 实际失败诊断和本轮GO
已读v02方法、报告、A/B门与实际anchor/regions源码，核读建筑/头骨/Ficus全部四视图及K3/K5/RGB控制。建筑拟合到立面，不是地台；头骨桌面深度偏差仍混主体；Ficus颜色与空间簇无部件拓扑。GO只表示运行一个廉价可证伪假设，不是已经成功分块。同一执行上下文自评，无外部模型/agent。

八个原BUILD相机right轴提供新的独立姿态约束：取sum(r rT)最小特征向量，按平均screen-up定符号，要求right投影RMS<=5°且lambda0/lambda1<=.05。这是相机共同upright代理，不是测得重力、真法线。输入审计DTU RMS2.606°、Ficus约0；只看相机元数据，尚未生成新分割。相机有roll或轴退化则UNKNOWN，不能硬指定场景轴。没有source中心或最小cov轴作法线。

## A：原同数据支撑拟合，增加方向资格而不改原容差
两构建图还是0000/0024、Ficus train_r_80/train_r_7。复用v02原depth回投样本/外围与中央标记（source-only，不含ink）。保持768假设、2.5p平面inlier、3p分离和所有原支持门，新增法向与upright夹角<=20°，每次SVD精化后也复查。拒绝立面假装地台；未知带仍UNKNOWN。Ficus孤立alpha范围原样保留，不声称新增语义能力。p=z/sqrt(fx fy)，完整W2C与整数像素中心，不用camera-z分位硬裁切。
对照v02无方向拟合及同原source/C8/truejoint。建筑或头骨A若全图仍漏主体/显著背景误入，B/C/D不运行；只保存A和失败机制。真实同色支撑层、倾斜承托面和roll相机为解析负控，不能以残差低宣布主体成功。

## B：仅Ficus A合格范围内，提议宽-窄-宽大结构
不改K值：没有KMeans。用相同两视角原可见深度样本，在共同upright轴上取1%..99%高度范围，32个等距分析bin。每bin按垂直于upright的两个坐标5%..95%跨度合成截面宽度；这是可见表面范围，不是实心体积/物理截面，至少每视角8点，缺样不插值认证。每视角分别测量，再取共同有效bin的中位数。仅描述量作sigma1bin平滑，不平滑RGB/depth/线。
在每段至少4bin的条件下枚举两个changepoints，以log(width)三段常数SSE最小定位。必须中段宽度<=两外段各.65、相对一段SSE下降>=.35、有效bin>=85%，且各视角独立求得切点与共同切点相差<=3bin。否则B假设NO_GO，不硬输出3种语义。通过仅称下部宽块/中间窄块/上部展开块候选；是否可解释为盆/干/冠还需全图跨视角视觉否决。切界半bin及未观察高度UNKNOWN，不能吃掉盆底未见面、填叶间洞。所有合法开放叶片保留。
等预算基线固定高度三等分（同3标签、同mask和unknown band）；另v02 K3、RGB-only K3及v01 RGB-only强基线。高度先验可能把枝干机械切断或把同高度叶混进干，必须呈现。此方法故意更可解释，但不把轴向层等同部件语义。

## 门/相机/终止
DEV0000/0000/train80，AUX0024/0024/train7；reserved0012/0036和test14/test79。历史全曝光，不新blind；DTU仍原GS训练相机。reserved不进入轴、plane/profile、cut、阈值拟合。共享轴仅8BUILD相机姿态，不读其额外RGB作为本轮8次观测。原C8仍8BUILD资产，多数单source parent，重投影不伪造对应。
双向实际depth可见重投影，分开occluded/front-inconsistent/outside/unknown；至少30样本且20%可见、每大区1%主体、双方dominant>=.75，至少2身份稳定大区及完整盆/干/冠才有B GO。数值通过但主干/叶被切坏仍NO_GO。无GT不报accuracy。所有原5展示中本轮预冻4视图，注明实际数，不凑第五。
本轮只验证A/B框架，C8/no-line/shifted-line和source soft责任及NPR NOT_RUN；若A/B真正有局部通过，下一轮再独立冻结这些消融。不得在失败分区上画漂亮NPR。r01结束seal后退出交runner，不启动第二科学轮于本invocation。每unit900s，全轮目标<=65min，CPU2，12GiB cap，root1/HDD10GiB，07:40起只收尾，08:00截止。

## TDD与证据
真实RED后最小GREEN：同色立面/地台方向约束、相机roll退化拒绝、rigid/scale不变、plane精化不得越界；宽窄宽toy有切点、单调/同宽不强分、缺视角/缺binUNKNOWN、不同颜色ID不是匹配、遮挡非反票、原C8/source索引分离。每个slice单独RED/GREEN日志，新增与继承分开。
每scene4个native完整画面 source/C8/joint/v02/newA；Ficus profile、共同候选/固定三等分/原强baseline、depth投影配对。source旧prefix与RAW不动。源码/参数hash、只读replay、旧893Python/12受保护树核验，包安全成员；报告明确该机理能否改进上游。不用删核/降墨证明成功。
'''
def main():
 assert not (R/'CONFIG.json').exists();js(R/'CONFIG.json',CFG);(R/'METHOD_FREEZE_ZH.md').write_text(TEXT);js(R/'METHOD_FREEZE.json',dict(utc=now(),config_sha256=sha(R/'CONFIG.json'),method_sha256=sha(R/'METHOD_FREEZE_ZH.md'),before_new_scientific_results=True))
 review('01_MECHANISM_GO','GO运行r01：在原样本与冻结容差上增加独立相机upright约束，Ficus检验可见截面瓶颈；所有阈值/强基线/失败门已冻结。不是重复KMeans/旧阈值搜索。', [R/'METHOD_FREEZE_ZH.md',R/'CONFIG.json',R/'POSE_INPUT_AUDIT.json'])
 status('METHOD_FROZEN',children=[])
if __name__=='__main__':main()
