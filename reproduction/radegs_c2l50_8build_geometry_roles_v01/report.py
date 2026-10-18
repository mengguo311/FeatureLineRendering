from env import *
from collections import Counter
def run():
 audit=json.loads((ROOT/'INPUT_AUDIT.json').read_text());rows={};cal={};cases=json.loads((ROOT/'CASE_FREEZE.json').read_text())['cases'];allr=[]
 for s in SCENES:
  paths=list((ROOT/'scenes'/s/'stage1').glob('*/*/*/RESULT.json'));rs=[json.loads(p.read_text()) for p in paths];allr+=rs;g=json.loads((ROOT/'scenes'/s/'graph/COUNTS.json').read_text());ca=[json.loads(p.read_text()) for p in (ROOT/'scenes'/s/'stage1').glob('*/reference/CALIBRATION.json')];cal[s]=dict(cameras=len(ca),max_rgb_mae=max(x['rgb_mae'] for x in ca),max_alpha_mae=max(x['alpha_mae'] for x in ca),max_center_surface_p95=max(x['center_surface_p95'] for x in ca),allN_checked_pixels=sum(x['all_N_pixels'] for x in ca),allN_max_error=max(x['all_N_max_error'] for x in ca),max_query_renderer_abs=max(x['renderer_query_max_abs'] for x in ca))
  rows[s]=dict(**g,original_ink_count=audit[s]['ink_count'],frozen_cases=sum(x['scene']==s for x in cases),valid_selected_cases=sum(x['scene']==s and x['selection_valid'] for x in cases),cameras=VIEWS[s],measurements=len(rs),roles_by_arm={a:dict(Counter(x['role']['role'] for x in rs if x['arm']==a)) for a in ['line','shifted_12px','source_geometry_axis']},scientific='NO_GO_PHYSICAL_PRIMITIVE_UPGRADE',diagnostic='PARTIAL_SOURCE_ID_ATTRIBUTION',fullframe_case_figures=len(list((ROOT/'scenes'/s/'stage1').glob('*/*/figures/CASE.jpg'))))
 counts=dict(expected_scenes=3,completed_scenes=3,selected_cases=12,available_cases=11,unavailable_cases=['scan24 roof_marks: nearest original parent 13.5268px > frozen12px'],measurements=len(allr),query_rows_including_repeated_pixels=sum(x['query_count'] for x in allr),per_measurement_unique_pixels_sum=sum(x['unique_pixel_count'] for x in allr),primary_line_measurements=sum(x['arm']=='line' for x in allr),source_role_touched_ids=sum(x['queried_source_count'] for x in rows.values()),new_physical_primitives=0,new_ink_Gaussians=0,source_model_mutations=0,whole_scene_classifications=0,DEV_parameter_revisions=0,scenes=rows,calibration=cal)
 js(ROOT/'COUNTS.json',counts)
 table='\n'.join(f'| {s} | {x["valid_selected_cases"]}/4 | {x["measurements"]} | {x["queried_source_count"]} | 0 |' for s,x in rows.items())
 report=f'''# 原 C8 线辅助原 GS 局部几何角色：真实三场景 pilot

**结论：已有线能作为查询位置，追溯哪些原高斯参与两侧成像；这次实验尚不能把这些高斯可靠升级为跨视角几何 primitive，也没有证明比同区域源几何对照更可靠。** 建议保留为诊断接口，不用于大范围自动 NPR 几何修改。原 C2L50＋8BUILD 线及所有源模型均保持原样，没有恢复核心线筛选、没有去刺或重建新线。

## 实际范围与输入

只读原 `c2l50_multiview05_v01/arms/C` 和原source，joint文件只用于核验原prefix/ID及复用CPU renderer。未使用mainlines v02/multiview核心标签。scan24是建筑、scan65是头骨，均为官方修复路线30k RaDe输入；Ficus是vanilla 3DGS，封存深度来自CPU协方差平面读出，不能称原生RaDe。世界单位非米。三场景source/ink分别为596467/458490、317817/279616、284835/285956。

源full SH保留；DTU按原实现激活filter_3D补偿。实际raw +Inf opacity数量scan24=50、scan65=1254，sigmoid后为1，未删核。Ficus没有filter_3D。不能把nx/ny/nz或协方差最短轴认证成表面法线。

DEV为0000/0000/train_r_80，其余固定相机为DTU0012、0036及Ficus test_r_14、test_r_79。所有均历史曝光；DTU是源GS训练视角，非blind或GS-heldout。病例在DEV原图与原线图上按预定部位冻结，再按最多12px选择原parent近邻、截取已有有序child范围，未改动几何。选出的来源均单视角；换相机查询不是新增对应线观测。

| 场景 | 可用冻结病例 | 三臂×三视角测量 | 实际触达原GS ID | 合格跨视角连接 |
|---|---:|---:|---:|---:|
{table}

共12个冻结病例，scan24 roof_marks距最近合法parent为13.5268px，超过12px，明确UNAVAILABLE，未偷偷换成好例。其余11例共99个case/view/control测量，其中原线33个。每scene仍有至少两个结构假设和一个负例；这些是人工指定诊断位置，不是人工GT“正例”。

## 实际测量与对照

每条原interval取至多9个真实child中心，保留parent、child、来源view/UV链。用完整fx/fy/cx/cy/W2C投影，在2D垂线±2/4/6px及中心查询原source-only。2D垂线不是3D法线。使用全source有限EWA footprint包围框，再精确q<=9检验、近裁面0.2、前到后排序：`alpha_i=min(.999,opacity_eff*exp(-q/2)); w_i=alpha_i*prod(j<i)(1-alpha_j)`。所有参与ID和权重落盘，无KNN/topK；每相机12个像素与all-N精算一致，共108个校准像素；另外只读重放核对真实病例像素。大核远中心亦不会漏查。透明后的零权重ID仍有记录，但不算正责任。

两侧先去重像素，再按各自总责任归一，计算overlap与L1。**参与line-band、对两侧差异有责任、世界空间面片可辨识，是三个不同问题。** 一颗大核跨两侧不自动成为边缘；红蓝仅显示实际原核责任，紫色表示不确定，不是生成了新表面。

局部几何proxy来自封存深度的两侧回投小patch，要求alpha、CPU/native深度一致性、点数、平面残差与二维展开条件；做5轮稳健平面拟合。法向来自这些深度点，不来自原核最短轴。两侧平面只在原查询线邻近小范围预测中心射线深度，检查是否接合/分层，输出条件与残差；此处仍有有限外推假设，不是物理面证明。源中心责任10–90%深度跨度>8世界像素代理时保守记为ambiguous。

三个同预算控制：原线；沿2D垂线错位12px；移除原线方向/深度断言、使用同区域源投影协方差轴和封存深度的geometry-axis。最后一个仍使用病例区域中心/长度预算，**不是无条件全场景geometry-only方法**。所有参数一次冻结，无DEV修改、无根据额外视角调阈值。配对需要两视角本地角色可辨识、源ID重叠>=.15、左右配对差>=.05、法向<=20度、对称平面残差<=2p、中心距<=20p；不通过保留各自节点，绝不平均/移动source。

## 实际图像与可证伪结果

**建筑：局部责任定位有用，面片升级NO_GO。** 窗框parent7456真实落在窗框附近，红蓝责任能定位参与原核，但中心深度混合较宽。屋檐parent6349在0012得到两侧层候选：L1=1.981、中心预测深度差14.846p；错位后成为单片候选，说明此位置存在局部分隔信号。然而geometry-axis同样得到两侧候选（L1=1.982、差14.808p），且0000不确定、0036原线UNKNOWN，尚未证明线优于源几何。地面长线负例parent5927的两侧有真实源责任；有支撑不代表线是所需物体结构。

**头骨：定位到颅缝/眼眶，但本次角色普遍不确定。** parent4703颅缝、377眼眶的原生深度小patch可较平滑，红蓝核责任不同；但学习到的核中心分布并不等于薄表面。33个原线测量中本scene12个有11个ambiguous、1个UNKNOWN，没有跨视角认证面片。颅盖纹理与头骨外侧背景线也可有明显责任差，因此不能把L1高当折痕。0036继续保留原位置，未改选更容易的样本。

**Ficus：叶缘有候选，细枝/薄叶仍不可可靠重建。** parent7803在DEV叶缘得到两侧层候选，L1=1.980、差7.254p；geometry-axis也得到同类结果（1.977、6.096p），不是独有的line优势。test_r_14为UNKNOWN，test_r_79为ambiguous。主干parent3577没有强行拟合圆柱；花盆parent5470原线不满足源表面定位条件；顶部长刺parent4758在DEV无合格源责任，三视角均UNKNOWN。这是该固定区间的实测负例，不是所有长刺都可据此删除。

原线33次测量：两侧候选2、ambiguous20、UNKNOWN11；单片/细丝候选0。两侧候选分别仅见于一个相机，跨视角兼容连接0。错位和源几何对照也有候选，故本轮对“线辅助优于null”的科学判定为NO_GO，而不是把更少UNKNOWN/更多候选当成功。0连接部分来自保守门槛，不是证明世界中不存在相应面片。

## 关键限制与负结果的解释

本实现的`volumetric_or_ambiguous`主要由**原核中心深度跨度**触发。这是原GS分配/测量不可辨识性代理；倾斜或延展核也可能覆盖同一连续表面。不能把它翻译成“真实体积混杂”，也不能从本轮NO_GO推出该方向不可行。原生深度patch连续而中心责任宽，是已保存的核心反例。未实现协方差条件射线深度下的每核表面假设，也未做真实几何GT标注；无法给precision/accuracy。

CPU fullSH/EWA是原joint近似renderer，非官方CUDA。九相机最大RGB MAE约0.00333、alpha MAE0.00634；中心中位深度与封存surface depth的相对p95最差0.1011（scan65），仍在预冻工程容差内，不能理解为局部几何误差已小。局部patch另有更严格门槛。Ficus深度本身为后验CPU代理。DTU alpha几乎铺满全图，不是object segmentation，背景有alpha不证明属于主体。

初版深度图曾把无效z=0和未到T=.5的median=0画入坐标，Ficus被纵轴拉大；原图保留，新`profile_valid_only.png`明示缺测数量，仅改善解释图，不改原数组、角色或阈值。原线图是X-RAY，不与源遮挡后的可见贡献等同。显示用源颜色标记在完整源alpha/排序下渲染；原PLY/SH/opacity没有写回。

## 交付与NPR判断

三scene均导出原source_index软role证据NPZ、触达ID的CSV/点PLY、带view/case/side/原parent来源的局部PATCH_GRAPH与完整CSR责任。source角色数组覆盖全source索引只是为了映射，未查询核保持UNKNOWN；不是全场景分类。局部多重patch候选和冲突保留。共有14009个源ID被原线两侧查询触达，198个含对照的测量节点；**物理primitive数0、新ink数0、源参数修改0**。点PLY是诊断点标签，不是替代3DGS模型。

实际99臂测量数据、33套全幅原线case图及控制板/放大、三场景三视角汇总与有效深度剖面均可查看。28项本轮新测试（27项责任/角色/图，1项原尺寸排版）保留真实RED/GREEN；校准all-N、源prefix字段、责任重放、标签坐标和源/旧工作树hash另行核验。跨scene汇总初次因777×581与800×800不同尺寸触发assert，失败日志保留；仅留白补齐画布恢复，没有缩放/裁切原像素或改变数据。未做视频，因为本轮空间可辨识gate未通过，不扩大成全场景动画或自动编辑。

当前可用：开发者沿真实线快速定位/检查原GS ID、颜色责任、局部深度候选；人工诊断上色PARTIAL。当前不可用：依此直接把整片source认作真墙面/颅骨面/叶片圆柱，批量改形变或材质。下一步若另获授权，优先单独检验“中心深度代理 vs 每核条件射线深度”的歧义来源，保持本轮病例与null对照；本任务停止，不自动执行。
'''
 (ROOT/'REPORT_ZH.md').write_text(report)
 (ROOT/'ASSET_FORMAT_ZH.md').write_text('''# 资产格式与使用限制

`scenes/<scene>/graph/SOURCE_ROLE_SCORES.npz`：source_index为原PLY行号；scores为N×5未校准责任加权证据（不是概率后验/GT置信），role_index取argmax只供显示，queried标明是否有正责任；未查询全为UNKNOWN。角色顺序见CONFIG/代码。

`PATCH_GRAPH.json`每个node是case/view/arm/side的测量patch，具有原source路径、深度点、拟合法向proxy、原因及parent来源；node不是认证物理primitive。`PATCH_MEMBERSHIPS.npz`以offsets把node映射到所有正责任source_index/weight，无topK；控制臂不进入原线source标签。edges记录左右配对候选、完整拒绝原因，无合格连接时为空accepted。没有用ink作source。

`SOURCE_ROLE_DIAGNOSTIC.ply/csv`仅包含触达原核的原xyz、source_index与显示标签/颜色，是诊断点云，不含完整高斯属性，不能代替原source模型。原source完整fullSH/filter/opacity在SOURCE_MANIFEST指定只读文件，通过source_index可精确取回。源和线均没有移动或重训。

`stage1/<view>/<case>/<arm>/EVIDENCE.npz`：query_uv/along_index/side_offset为真实像素查询；original_child_id/world_line为原C8样本；csr_offsets/source_index/alpha_i/T/weight/source_center_z是每像素全源有限footprint责任；native_z/native_alpha是同相机原缓存（Ficus是CPU代理），query_median_center_z是EWA原核中心中位数，二者不能混同；left/right_points为过门槛封存深度回投；participant_ids及两侧mass为像素去重后的平均责任。

`RESULT.json`含角色、原因、offset稳定性、front_side、中心资格、各侧拟合条件。figure的红蓝是源责任显示；X-RAY线无源遮挡；局部放大为解释图。profile_valid_only排除无效/低alpha深度，仅绘图。原图/数组保留。

所有单位为原COLMAP/NeRF场景单位，不是米。p=z/sqrt(fx*fy)只是归一尺度代理，不是投影后真实像素长度。坐标使用完整W2C/intrinsics和原像素中心约定。
''')
 (ROOT/'RUN_COMMANDS.md').write_text(f'''# 实际执行入口

工作目录 `{CODE.parent.parent}`；Python `{sys.executable}`，均加`-B`，env.py固定2核/2线程、不使用GPU。旧输入只读。

按执行顺序：
```
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/audit.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/freeze.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/test_responsibility.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/test_roles.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/measure.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/plots.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/review02.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/measure.py --secondary
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/test_graph.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/support_graph.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/plots.py --secondary
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/supplement.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/test_runner.py
python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/verify.py --readonly --replay
```

前面是生产命令记录，不应对封存目录重复运行。supplement首次汇总排版失败日志保留，随后用`python -B reproduction/radegs_c2l50_8build_geometry_roles_v01/supplement.py --resume-overview-only`补齐未生成的overview，不重写已有剖面/scene图。父级复核只运行最后的verify --readonly --replay，不会改报告/数组/封存图。新tests四轮RED/GREEN分别留在tests，最后28项回归结果在TEST_RESULTS。数据/renderer使用绝对依赖，见SOURCE_MANIFEST，不需要安装/下载。复现实验到新根需复制本任务代码并显式修改env.ROOT为全新目录，同时复核输入hash；不得改旧环境或旧资产。
''')
 return counts
if __name__=='__main__':print(json.dumps(run(),indent=2))
