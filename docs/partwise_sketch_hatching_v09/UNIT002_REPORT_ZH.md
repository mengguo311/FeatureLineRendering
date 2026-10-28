# Unit002：条件H1真实相机对照

执行完成，科学结论PARTIAL。Chair同粗标签、共享投影方向场、固定纸底/座面S/结构层下，比较确定性逐视角二维积分B0与原U持久三维排线B1。全部27科学相机实际重算原GS，其中25帧为196/36至241/24连续弧段；另有BUILD和241/60静态负视角。

- 自然强度的union墨量归一化双向误差：B0 **0.592088**，B1 **0.349214**。
- 各方法自身中心线至目标实际墨的加权距离：**0.370497 / 0.007939 px**；这不是逐ID物理对应精度。
- BUILD匹配后不再逐帧匹配，DEV墨量与覆盖不等。B0早期更密，弱后侧出现少画；B1也有非零自身缺墨。只支持本生成系统与有限轨迹的条件性时序优势，不支持纯锚定因果效应、自动分割、整物体赢家或Gaussian特有优势。
- 243张PNG与数组一致，两条25帧APNG全帧解码核对；012及文档BUILD命令冷重载/重新生成/渲染逐数组一致。25577个原接受事件独立重建fullSH RGB和座面S。上背及结构仍proxy-only。

完整报告及原始输出位于HDD：

- [报告](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/REPORT_ZH.md)
- [自然影片](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/media/natural_orbit.png)
- [完整关键帧](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/media/KEYFRAMES.png)
- [复现命令](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/REPRODUCE.md)
- [协议](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/PROTOCOL.json)
- [时序原始指标](/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_002/TEMPORAL.json)

初始BUILD二维种子漏掉边界相交片段，已在DEV前通过针对性RED/GREEN修复；初始图、代码和协议原样保留。两次命令路径拼写错误、004缺最终回执/UNKNOWN与011实际rc2均保留，恢复不改写历史。unit001的H2 U/S/D/sham静态PARTIAL及旧开放框、孔洞、高后侧零增量、143/UNKNOWN和时序跌落均不被本结果覆盖。

NEXT=continue：新一轮只读审查后，检验unit001冻结U/S/D/sham在相机变化下的留白选择性、必要覆盖和自身墨稳定性，使用精确同相机底层缓存并实际重光栅化；不做参数扫描或仅重播影片。父级独立核验待完成。
