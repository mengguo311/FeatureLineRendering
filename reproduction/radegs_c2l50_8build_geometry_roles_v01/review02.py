from env import *
if __name__=='__main__':
 evidence=[ROOT/'scenes'/s/'stage1'/DEV[s]/case/'figures/CASE.jpg' for s,case in [('scan24','window_frame'),('scan65','socket_rim'),('ficus','thin_leaf_edge'),('ficus','top_spike')]]
 review('02_secondary_and_graph_GO_primitive_NO_GO', '''实际检查了三场景全幅证据图及Ficus长刺负例。GO：冻结v00不调阈值，对原来预定的两个额外相机进行同一测量、校准与控制比较，并保存源ID支撑图。
NO_GO：当前不能把这些责任分布升级为物理面片/圆柱，也不能自动全场景分类。建筑和头骨多处原高斯中心深度责任跨度较宽；这只表示当前中心深度代理难以辨识，绝非已证明物体有体积混杂。原生深度小patch可能很连续，二者的差异须并列报告。
Ficus叶缘得到两侧候选，但源几何方向对照亦得相同类型，尚无line-signal优于null的证据。顶部长刺在DEV缺有效源支撑，不可自动推广成全视角物理结论。
下一步变量：只有相机；输入、case、offset、参数、控制均不变。支撑图采用已冻结的源ID加权重叠/法向门槛；新增明确定义的保守图资格为：两视角本地角色可辨识、patch各自valid、源ID重叠>=.15、左右配对margin>=.05、法向夹角<=20度、两patch对称点到平面中心残差<=2个世界像素代理，且中心距离<=20个代理。配对失败仍保留原节点，绝不合并几何或移动GS。
图是测量关系，不是真曲面。局部展示上色不改变保存的source SH/opacity/geometry。若跨视角失败，交付负结果与完整节点，不强迫图连通。
绘图审计发现第一版profile包含无效z=0/无贡献median=0，造成Ficus纵轴被背景拉大；保留原图，在新文件额外给valid-only剖面并标注缺测数量，不改测量/分类/阈值。
资源目标<10GiB，两线程；无新模型、GPU、训练、外网。''',evidence)
 js(ROOT/'GRAPH_CONFIG.json',dict(min_weighted_ID_overlap=.15,min_pairing_margin=.05,max_normal_deg=20,max_symmetric_plane_pixels=2,max_center_distance_pixels=20,min_views=2,scope='local source-ID support graph only; no physical reconstruction',role_score_semantics='uncalibrated heuristic; unqueried source remains UNKNOWN'))
 state('SECONDARY_APPROVED',status='GO_MEASUREMENT_ONLY',children=[])
