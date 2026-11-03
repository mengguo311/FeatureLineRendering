# unit007 保存结果分析

组均权拟合真实改变几何和排名：38次接受（5558/22130/64111/238627分别8/5/4/21），16次纯池化，新增UNKNOWN183核。相较封存ROW_FIT17步自然停止，238627原死端被释放，但新增116核仍无起点域外支持，长弧主要继承/内部填充。第6步22130平行冲突、第15步64111自接触是明确保留的风险；同donor自接触端点Q的J=.067926低于无接触重叠Q的.076681，不是U奖励导致。全部接受的最大距离1.298543p/角71.753462度，未复现unit006的89度超限，这只是几何代理改善。最终因450秒增长预算PARTIAL，238627末库已有5个合格解释但其余未完，不能宣称自然耗尽或挑选截断库赢家。

实际子进程03:41:22.550260—03:51:01.796163 JST，rc=0/reason=null；RUN_RESULT为partial，原因PHASE_DEADLINE GROUP_BALANCED_FIT。readiness9.03秒、共同初始库20.29秒、增长451.90秒、交付97.13秒。2727次拟合/评估，850次均衡评分。父退出码与科学完成程度分开。四份初稿03:52:02 JST保存，距请求约61秒。

本轮仅改变拟合位置项：G/F各半；全部原行参加五轮IRLS、全部结点可动，排序仍GROUP_BALANCED_SCORE，规则2/4/6保持关闭。五份旧ROW_FIT初始库精确重放（科学记录及q/template/masks）通过，旧17步轨迹仅引用。后续Q和合法库改变，不能宣称相同几何的纯排序优势。

保存审计验证152个中间checkpoint文件哈希、38次逐行精确并集、38次完整库最低J、38次拟合行分区及每轮权重。38次均移动LOCAL会固定的旧区段，最大位移范围0.04997—0.93163p；不是只改颜色/接缝。最终映射等于第38次最后有效checkpoint，未完成第39次未提交。109完整访问库+1部分库，两拟合库均保存。详见[SAVED_OUTPUT_AUDIT.json](SAVED_OUTPUT_AUDIT.json)。

279616原行最终assigned126611、UNKNOWN153005；起点126428/153188。本轮新增UNKNOWN183核及既有assigned成员并入39核，起点丢失0、拆分0。GEOMETRY_AUDIT七字段前后哈希一致、行序一致；原核几何冻结，渲染只用原核，无辅助桥墨/源表面遮挡。辅助曲线再拟合不能去除原尖刺。

|组|接受|核数起→末|union起→末(p)|longest起→末(p)|末gap(p)|起点域外(p)|实质M4贡献数|
|---|---:|---|---|---|---:|---:|---:|
|5558|8|275→324|72.1081→71.5077|54.7484→54.3928|0.8507|0.0000|5|
|22130|5|216→255|61.2031→61.7572|61.2031→61.7572|0.0000|0.0000|5|
|64111|4|209→227|38.5914→42.8075|36.9348→38.3782|0.3489|4.9220|1|
|156151|0|169→169|44.0430→44.0430|44.0430→44.0430|0.0000|0.0000|2|
|238627|21|368→484|122.8132→122.9921|99.8236→122.9921|0.0000|0.0000|3|

16/38次U=0，1次自接触，0次超原gap界，0次闭合。U是每次拟合Q中的差集，不能直接累加成真实新增观测。64111虽然域外代理超过4p，却只一个实质M4贡献；不能拿209核旧短弧加18小核称三片段完整曲线。238627的三项实质贡献亦不能抵消域外0和继承长弧的事实。

最早排名/拟合分歧在第1步5558选择-76451，旧同状态选-76498；第3步64111改选-274461，旧同状态127285。第6步新增平行冲突；第15步自接触端点解释胜出（分项和有限，U奖励仍0），替代同donor无接触重叠解释。第25步以后238627逐渐吞入多对平行冲突。所有接受事件均未超过原R2距离/角阈值，比unit006的旧行89度损伤代理改善，但不同成员轨迹、颜色和低loss不能证明正确率。没有确证第三臂或深度误吞，亦不能据此声称不存在。

末库5558/22130/64111/156151分别完整无连接；64111的216解释有50无注册、139端距、26vertex、1原叶非单调。238627末库37donor已记录199解释，已有5个合格，但仍有四个未完donor，selected=null；不从其中挑最低者晋级。无接受次数上限，21步238627仍因预算截断，不能说研究窗口耗尽。

按保存contingency：M4→最终gain476/loss0/split0，起点已继承gain293；M3 gain8268中8085继承。unit014联合参考loss144/split15全部起点已有，本轮未新增；相对旧ROW_FIT最终gain138/loss20/split2属于匹配起点的不同增长轨迹，并非删除本轮旧成员。scan65没有已执行M5/v06对照，强背景为M4；不虚构跨场景参考。

实际看图：完整对象仍是同一头盔/面部原核线网。5558隔离短直线旁有近邻平行细线；22130处背景交叠。238627双视图长弧可见，但起点与终态外轮廓接近，主要变化是原弧内密度；第38步新增为极小点划。64111视图很小，不足认证实质新增曲线。所有负例文件保留；本分析未逐张视觉验收全部负例。visual_evidence_missing=true表示身份证据不足，并非没有保存PNG。

实际查看图：

- [GROUP_BALANCED_FIT_FINAL/0012_FULL.png](scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0012_FULL.png)
- [238627/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/238627/GROUP_BALANCED_FIT_0036_ISOLATED_CROP.png)
- [238627/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/238627/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [0015/0036_ISOLATED_CROP.png](scenes/scan65/worst_events/GROUP_BALANCED_FIT/0015/0036_ISOLATED_CROP.png)
- [0038/0036_ADDED_CROP.png](scenes/scan65/worst_events/GROUP_BALANCED_FIT/0038/0036_ADDED_CROP.png)
- [GROUP_BALANCED_FIT_FINAL/0036_FULL.png](scenes/scan65/stages/GROUP_BALANCED_FIT_FINAL/0036_FULL.png)
- [238627/START_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/238627/START_0036_ISOLATED_CROP.png)
- [238627/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/238627/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [238627/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/238627/GROUP_BALANCED_FIT_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [64111/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [64111/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [5558/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/5558/GROUP_BALANCED_FIT_0012_ISOLATED_CROP.png)
- [5558/GROUP_BALANCED_FIT_0012_QUERY_CONTEXT_CROP.png](scenes/scan65/diagnostics/5558/GROUP_BALANCED_FIT_0012_QUERY_CONTEXT_CROP.png)
- [22130/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/22130/GROUP_BALANCED_FIT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [0026/0012_FULL_OBJECT_CONTEXT.png](scenes/scan65/worst_events/GROUP_BALANCED_FIT/0026/0012_FULL_OBJECT_CONTEXT.png)

下一步（NOT_RUN，须另冻review）：另行冻结“GROUP_BALANCED_FIT终态续接＋固定起点支持坐标对照”，不再调拟合权重或恢复2/4/6。输入unit007 GROUP_BALANCED_FIT_FINAL，MEMBERSHIP SHA256=030f7025d5ce151dfde5ffd4e5d3aa6bbda055d5fc1586865480aa52dc63ccf1，next_version21707；保持五组队列及完整279616背景，优先完成238627尚未评完的37-donor整库，必须重查全库而非仅四个未完donor。完整ROW_FIT影子对照保留。诊断新增固定unit007 START q坐标下的同一原行协方差支持，与动态Q上的U/union/run及旧域运动并列；固定坐标对照只用于解释池化/重映射，不加入评分或接受门。第15步-274465的重叠/端点两解释作为固定反例：并列同核、分项J、接触与域外代理，不以解除接触等于闭合。新review冻结精确预算及独立证据；保持2p候选、五轮整组拟合、GROUP_BALANCED_SCORE、规则1/3/5、容量和闭合认证。若续接再到时仍PARTIAL；若真实穷尽，转预先绑定的新种子/场景而非重复阈值扫描。

本分析仅读取保存数据、查看PNG并写元数据，未重跑/拟合/渲染/改源码配置。无物理身份、held-out、时间稳定或新颖性认证。
