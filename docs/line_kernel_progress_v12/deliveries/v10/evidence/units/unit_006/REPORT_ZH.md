# unit006 保存结果分析

实际数值子进程rc=0、reason=null，03:18:30.975493—03:22:14.026160 JST；RUN_RESULT completed。新GROUP_BALANCED_SCORE接受17次，五组均NATURAL_SCOPE_EXHAUSTION/NO_CONNECTABLE_FRAGMENT，无本轮时间或容量停止、无SUPPORTED_CLOSED。旧NO_U控制为封存33步PHASE_DEADLINE的PARTIAL，未重新执行。返回码仅说明进程退出，不认证科学身份。四份初稿于03:23:19 JST保存，距请求约65秒。

本轮只把排序位置/方向项改为当前G与donor F各半；WHOLE拟合仍用全部原核行均权，[2,4,6]保持关闭。初始十份策略库完整冻结；五组旧评分选择复用核对。最早分歧第3步64111：-158889的旧/新分0.077206/0.208513，127285为0.096149/0.109068。小donor的平均位置/方向损伤得到更大权重，真实改选127285，却接入保存的平行冲突对[64111,127285]。这是软排序的取舍，不是身份正确证明。

第5步22130+-149202引入平行对[22130,149201]。第6、9、12步64111仍接受旧行240923/240924方向损伤，最大79.457、82.483、89.167度；这些不是当步新行。R2/R4解除有真实效力；R6允许15次U=0池化。本轮接受事件没有self-contact/gap_exceeded，不能据此声称已检验长gap/自接触的质量。没有视觉确证的第三臂或跨深度误吞；相应不确定性保留，不能写成没有风险。

279616原行最终assigned126493、UNKNOWN153123，较START新增UNKNOWN归属65、旧已分配行并入64；起点已分配成员丢失0、旧组拆分0。68个中间checkpoint文件哈希、17次精确成员并集、17次全库最低分和评分分项和均通过保存数据审计。45份访问库完整；17次Q均移动了LOCAL会固定的旧区段，最大位移范围0.03781—0.81968p，证明存在整条旧曲线调整。全行最终映射等于最后有效checkpoint，没有未保存的尾步。GEOMETRY_AUDIT七数组前后哈希一致且原行序一致；原核几何不动，辅助Q不作墨迹，不画连接桥、不做源表面遮挡。独立审计记录见[SAVED_OUTPUT_AUDIT.json](SAVED_OUTPUT_AUDIT.json)。

|组|接受|核数起→末|支持union起→末(p)|最长run起→末(p)|末gap(p)|域外代理(p)|
|---|---:|---|---|---|---:|---:|
|5558|8|275→326|72.1081→71.9937|54.7484→54.5277|0.86651|0.11658|
|22130|5|216→255|61.2031→61.9559|61.2031→61.9559|0|0.01130|
|64111|4|209→248|38.5914→40.1215|36.9348→40.1215|0|0.00795|
|156151|0|169→169|44.0430不变|不变|0|0|
|238627|0|368→368|122.8132不变|99.8236不变|0.33766|0|

17次中15次纯池化，只有第3步U=1.61914p、第12步U=0.001958p。U是各次最终Q上的差集，不等于相对起点域外延；重映射/内部填充不能算新观测。238627长弧全部继承。64111对旧NO_U末态域外代理8.35574p，本轮仅0.00795p，提示外延取舍；两轨迹和旧控制截断不同，不把该比较说成物理质量优劣。更大计数、颜色或较低loss均不构成准确率。

终态库：5558有7donor、42解释，其中branch5；22130有1donor、6解释，全无注册/端距；64111有34donor、204解释（无注册46、vertex31、端距127）；156151邻域0；238627有59donor、354解释（vertex33、无注册85、端距236）。它们是规则1/3/5及当前候选定义下的局部穷尽，没有8次上限的停止证据，不能视作整个场景或06:00窗口耗尽。

按保存contingency，M4→末态gain358/loss0/split0，其中START已继承gain293，本轮仅65；M3→末态gain8150/loss0/split0，其中8085继承。对unit014联合参考gain484/loss144/split15，loss144与split15在起点已存在。对旧NO_U终态少102 assigned、split1，是匹配起点的轨迹分歧，并非本轮删除旧成员。scan65没有已执行M5/v06对照，强背景为M4；不得捏造跨场景M5增益。

实际看图：两幅全景保留头盔/面部完整碎边与原尖刺。5558隔离为短直线，查询背景旁有近邻细线；64111起点与终态0036均为很短浅弧，0012是近竖短痕，新增核图只有细小点划。完整对象裁剪显示交叠背景，无法据此区分平行层/深度。22130完整背景位于多条边交叠处。未展示双视图可认证的新增实质直/曲身份，visual_evidence_missing=true表示证据分辨率不足，非PNG缺失。未逐张审查所有六类负例或所有中间图，不能宣称全面视觉验收。

已实际查看的原核图（原生小图不以放大制造证据）：

- [GROUP_BALANCED_SCORE_FINAL/0012_FULL.png](scenes/scan65/stages/GROUP_BALANCED_SCORE_FINAL/0012_FULL.png)
- [5558/GROUP_BALANCED_SCORE_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/5558/GROUP_BALANCED_SCORE_0012_ISOLATED_CROP.png)
- [64111/GROUP_BALANCED_SCORE_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/GROUP_BALANCED_SCORE_0036_ISOLATED_CROP.png)
- [64111/GROUP_BALANCED_SCORE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/64111/GROUP_BALANCED_SCORE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [0003/0036_ADDED_CROP.png](scenes/scan65/worst_events/GROUP_BALANCED_SCORE/0003/0036_ADDED_CROP.png)
- [GROUP_BALANCED_SCORE_FINAL/0036_FULL.png](scenes/scan65/stages/GROUP_BALANCED_SCORE_FINAL/0036_FULL.png)
- [64111/START_0036_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/START_0036_ISOLATED_CROP.png)
- [64111/GROUP_BALANCED_SCORE_0012_ISOLATED_CROP.png](scenes/scan65/diagnostics/64111/GROUP_BALANCED_SCORE_0012_ISOLATED_CROP.png)
- [22130/GROUP_BALANCED_SCORE_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan65/diagnostics/22130/GROUP_BALANCED_SCORE_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [0009/0036_ISOLATED_CROP.png](scenes/scan65/worst_events/GROUP_BALANCED_SCORE/0009/0036_ISOLATED_CROP.png)
- [5558/GROUP_BALANCED_SCORE_0012_QUERY_CONTEXT_CROP.png](scenes/scan65/diagnostics/5558/GROUP_BALANCED_SCORE_0012_QUERY_CONTEXT_CROP.png)

下一步（当前NOT_RUN，须另冻决定）：下一单元另行review并冻结“相同GROUP_BALANCED_SCORE排序，行均权拟合 versus 组均权拟合”。从本单元封存START、同五组开始；控制复用本轮17步完整轨迹，仅重放共同初始库。新拟合仍保留全部G/F成员、整条Q可动、五轮Huber IRLS(delta=.5p)，仅将位置项改为.5*mean_G(Huber)+.5*mean_F(Huber)，即基础行权1/(2nG)、1/(2nF)；其余平滑.05、模板.001、LSQR1e-8/2000、GROUP_BALANCED_SCORE、2p完整候选、规则1/3/5、[2,4,6]关闭及容量/闭合定义不变。比较最早64111/127285、22130/149201平行吸收及旧行240923/240924损伤，保留坏例，不新增方向/平行拒绝。以新机制检验排序均衡而拟合仍按行加权是否限制效果，不能预言改善。复用封存控制，不重跑全部旧science。后续范围扩展另选预先可辨新种子，不把五组耗尽当窗口耗尽。

所有现有坏例、旧控制PARTIAL和来源保持封存；本次仅读取保存结果并写分析元数据，无重拟合/渲染/源码配置变更。无物理真值、held-out、时间稳定或新颖性认证。

恢复核对：四份文件在首次分析开始约65秒已落盘；本次ANALYSIS_RECOVERY重新核对schema、实际COMPUTE_EXIT及原核图，保留rc=0/reason=null。模型阶段恢复与科学进程状态分开记录，未启动数值重跑。
