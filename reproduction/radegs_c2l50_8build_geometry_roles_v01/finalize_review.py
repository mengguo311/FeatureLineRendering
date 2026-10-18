from env import *
if __name__=='__main__':
 proof=json.loads((ROOT/'VERIFY_REPLAY.log').read_text());assert proof['status']=='PASS';tests=json.loads((ROOT/'TEST_RESULTS.json').read_text());assert tests['passed']==28
 seen=[('scan24','0000','window_frame','CASE.jpg'),('scan24','0012','roof_wall_eave','CASE.jpg'),('scan65','0000','socket_rim','CASE.jpg'),('scan65','0036','cap_seam','CASE.jpg'),('scan65','0000','outside_skull_line','CASE.jpg'),('ficus','train_r_80','thin_leaf_edge','CASE.jpg'),('ficus','train_r_80','top_spike','CASE.jpg'),('ficus','train_r_80','stem','ZOOM.jpg'),('ficus','test_r_14','thin_leaf_edge','CASE.jpg'),('ficus','train_r_80','thin_leaf_edge','CONTROLS.jpg')]
 paths=[ROOT/'scenes'/s/'stage1'/v/c/'figures'/f for s,v,c,f in seen]+[ROOT/'summary/OVERVIEW.jpg',ROOT/'summary/scan24_MULTIVIEW.jpg',ROOT/'summary/ficus_SUPPORT_GRAPH.png',ROOT/'scenes/ficus/stage1/train_r_80/thin_leaf_edge/profile_valid_only.png']
 js(ROOT/'VISUAL_INSPECTION.json',dict(actual_view_image_paths={str(p):sha(p) for p in paths},observations=['建筑窗框附近能定位局部红蓝源责任；外侧地面假线也有宽源支撑。','头骨颅缝/眼眶附近显示局部责任，但外侧背景线也影响宽核，不能把参与当边界。','Ficus主干样本跨几根近邻茎，未强迫拟合圆柱；叶缘两侧候选未跨视角稳定，几何对照也有候选。','Ficus顶部长刺DEV无有效source责任；弱视角leaf定位未稳定，保留UNKNOWN。','全幅、控制板、局部放大与有效深度补图均实际查看；没有声称全场景几何已恢复。'],assessment='same executing agent qualitative audit, not independent human/GT review'))
 review('03_delivery_GO_geometry_upgrade_NO_GO','''GO：封存真实测量/诊断，打包与本地commit；NO_GO：物理primitive升级、全场景NPR几何修改及自动后续。
实际查看了三scene完整case和负例、scan65 0036、Ficus test_r_14及多视图汇总。11有效冻结病例×3相机×3臂=99测量；2原线局部两侧候选均没有跨视角合格连接，并且同区域源几何对照同样有候选。没有证明line优于null。
28新tests通过；54来源hash、旧main893Python及依赖worktree保护通过；三DEV病例责任与source渲染bitexact replay，all-N查询一致。汇总排版尺寸assert及测试汇总器单数test/tests解析失败日志保留，修复仅工程展示/报告解析，未改fixture容差和科学规则。
边界：中心深度跨度是分配歧义，不是物理体积认证；原深度patch可能平滑而源核分配宽。本轮产出源索引标签和支撑图，0物理primitive、0新ink、0source修改。Point PLY仅诊断，不替代fullSH模型。''',[ROOT/'COUNTS.json',ROOT/'TEST_RESULTS.json',ROOT/'VERIFY_REPLAY.log',ROOT/'VISUAL_INSPECTION.json',ROOT/'REPORT_ZH.md'])
 js(ROOT/'SOURCE_AFTER.json',dict(verified_unchanged=True,count=proof['source_files'],files=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())['files'],verification_log_sha256=sha(ROOT/'VERIFY_REPLAY.log')))
 js(ROOT/'ROLLBACK_AFTER.json',proof['rollback']);state('READY_TO_SEAL',status='GO_DELIVERY_SCIENTIFIC_NO_GO',children=[],completed_scenes=3,physical_primitives=0)
