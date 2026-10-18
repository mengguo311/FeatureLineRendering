from env import *
from collections import Counter
rd=ROOT/'round1';rows=[json.loads(p.read_text()) for p in (rd/'scenes').glob('*/*/*/*/RESULT.json')];assert len(rows)==44
text='''# 第一轮：条件射线深度

科学结论：PARTIAL（深度表示纠偏），线的独有划分增益 NO_GO；不认证物理primitive。
实际运行3场景DEV、11个有效病例、4臂共44测量。scan24 roof_marks继续UNAVAILABLE，不补选。全部保持原source alpha*T和原center排序；仅替换深度proxy，条件方差也纳入宽度。

原线11例从旧1两侧候选/8混杂/2未知，变成1两侧候选/1单片/5混杂/4未知。候选并非简单净增：Ficus thin_leaf_edge旧两侧候选因有限责任/与原深度一致性不足退UNKNOWN；scan24屋檐从混杂变两侧候选，scan65 cap_marks变单片。几何轴null也得到同一屋檐两侧候选和cap_marks单片；移位线得到2单片。这不支持“线独有信息已恢复几何边界”。

实际view_image检查：scan24/0000/roof_wall_eave/figures/CASE.jpg，scan65/0000/cap_seam/figures/CASE.jpg，ficus/train_r_80/thin_leaf_edge/figures/CASE.jpg（相对于round1/scenes）。建筑屋檐责任集中在檐口附近，但局部着色不代表整面；头骨颅盖接缝宽度仍约12p；Ficus薄叶条件中位与旧读出不总一致，顶部原长刺完整保留为负例。所有全画面与原C8Xray保留。

局限：qmin有限椭球条件与EWA投影足迹并非等价，缺失责任质量留UNKNOWN。沿ray条件mode是3D高斯密度proxy，不是RaDe surface，也不等于高斯条件期望或真实遮挡面。保持center排序隔离变量，但排序误差留给第三轮独立诊断。无逐物理面GT、不报准确率。

下一轮GO仅为预冻DEV+AUX少量同病例责任软图。条件点和源ID均保留，不把核中心当面片。双片必须胜过单片复杂度、通过两侧连接及有限深度资格，并有第二相机的可配对资格；失败导出REFUSED图，不扩全场景。
'''
(rd/'ROUND1_REPORT_ZH.md').write_text(text)
js(rd/'VISUAL_REVIEW.json',dict(inspected=[str(rd/'scenes'/s/v/ca/'figures/CASE.jpg') for s,v,ca in [('scan24','0000','roof_wall_eave'),('scan65','0000','cap_seam'),('ficus','train_r_80','thin_leaf_edge')]],verdict='PARTIAL_PROXY_CORRECTION_NO_GO_LINE_SPECIFIC_PRIMITIVE'))
review('02_round2_GO','''R1实际44测量与3scene全图已检查：屋檐/颅盖标记的proxy纠偏与null同增，叶边退UNKNOWN。GO只执行预冻第二轮局部责任图证伪，不升级全场景。
明确实现定义：每source/pixel条件mode作为候选点；完整CSR中非有限/3sigma外/条件sigma>4p及未满足R1像素资格的责任留UNKNOWN；不归一化消失质量以伪装完整。每个唯一像素只算一次独立样本，多核是混合假设。平面按source责任加权稳健拟合，不能用核中心替代；single vs line-side two-sheet按冻残差/复杂度与同核重叠门比较。仅与线的原几何/原深度一致的中心可升级；source浮层/假刺不因平面好拟合获准。图为sourceID—pixel/side二部图，无KNN/topK。配对仅DEV/AUX固定相机，世界接近平面不够还需实际source责任重叠与不歧义配对。归属软、多重，全部未查询source保持UNKNOWN。
即使R2全REFUSED，R3仍按预冻排序/可见性证伪执行；不得更改阈值让其成功。''',[rd/'ROUND1_REPORT_ZH.md',rd/'VISUAL_REVIEW.json',ROOT/'PROTOCOL_FREEZE.json'])
