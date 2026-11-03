# v10 unit_001：R2 放开后的真实效果与局限

实际子进程 rc=0、reason=null；2026-11-03 00:55:59.621372–01:03:06.806811 JST，保存运行耗时426.157秒。STRICT_TRANSPORT接受0次，R2_OFF_TRANSPORT接受5次。两臂均从同一scan24终态出发，完整458490行；当前六组以外保留强背景。旧scan24使用RADIAL分叉，本轮两臂共同使用TRANSPORT，不能作跨代单变量归因。

R2确实被解除：事件1的新行63866切向80.6835°仍获有限J；事件2距离1.52436p、角78.0419°均越过旧门。本轮没有使用q95或无穷评分偷偷恢复R2。规则4/6尚开启，其解除效果未执行。

|事件|组 / donor|新行|关系|J|unique支持p|最大距离p / 角度°|
|---|---|---:|---|---:|---:|---|
|1|132977 / -63867|10|overlap|0.054839|0.170|0.985 / 80.684|
|2|210790 / -241653|8|overlap|0.003197|0.594|1.524 / 78.042|
|3|132977 / -6505|6|overlap|-0.054857|1.352|0.965 / 83.494|
|4|132977 / -419418|9|endpoint|-0.097348|2.953|0.979 / 84.704|
|5|132977 / -232977|11|endpoint|-0.094056|3.316|0.896 / 84.996|

5次逐步冷载检查均满足新组=上次旧组∪事件added_rows，所有旧assigned保留，全部checkpoint文件哈希匹配。新增44行全来自UNKNOWN，没有吞并既有assigned donor组；不能称为本轮大规模旧身份重分割。STRICT所有成员字段与START相同，最终R2映射与第5次checkpoint相同。原核means/covariance/opacity/colors/primitive_id/internal_piece_id/arc_t的前后哈希一致，行序458490不变；辅助模型版本/成员元数据改变属于预期。

完整保存库中5个选择均为最低有限J，可连接解释数依次1/1/3/3/20；对应访问1/5/7/13/19。STRICT有6个访问，R2有30个访问，132977确实在接受后重复重查并连续4次提交。WHOLE全部结点参与全成员拟合；旧曲线fit-only最大位移依次0.7291/1.0019/0.3245/0.4315/0.3334p，不能说只改标签或冻结旧前缀，也不能说每个旧结点均发生同样位移。

最终六组均是完整库下NO_CONNECTABLE_FRAGMENT；0个SUPPORTED_CLOSED。无时间/容量/拟合截断、无接受次数上限触发。2306次拟合、4612次策略评估；阶段约11.93秒readiness、44.04秒共同库、4.01秒STRICT、231.96秒R2、134.22秒交付。该完成仅指六组和固定候选/剩余守卫范围，非整个研究耗尽。

|组|起点→最终核数|support union p|最长run p|最大gap p|域外支持代理p|
|---|---|---|---|---|---:|
|132977|529→565|147.615→155.847|55.614→54.183|0.495→0.664|9.078|
|210790|200→208|42.304→42.927|26.283→26.911|0.389→0.397|0|
|其余四组|不变|不变|不变|不变|0|

132977总gap从1.359增到2.585p，union增量不是连续长度增量。210790主要内部填充；132977事件1unique仅0.170p，重映射后union反而略降。每步unique不能直接相加当终态域外支持。132977既有9项实质M4贡献、210790既有4项均未增加；新增donor分别仅10/8/6/9/11行。曲线201906和202023零增长，因此未证明新增实质直线与完整曲线的双重恢复。

相对START与v09 WHOLE：assigned259985→260029，UNKNOWN198505→198461，新增44、损失0、旧组split0；原已归属组的成员归属不变。相对M5的271新增中227已在起点，不能都计本轮；M4的13680新增中13636继承。相对v06 greedy/joint最终新增11172、损失1231、旧组split81；起点已是11128/1231/81，这1231损失及81拆分是继承差异，本轮没有新增。以上参照保存CROSS contingency和METRICS，标签ID变化数不被当作物理身份改变。

已看0012/0036两幅全景、132977起点/中间/最终及新增行、210790最坏事件两视图、查询竞争和完整对象裁剪、201906曲线以及84842/362883负例背景。全景建筑线框和既有尖刺依然存在；132977孤立图表现为折线，起点与末态视觉差异很小，新增图只有很小的点/短划。完整背景有密集邻线和交叉，QUERY_CONTEXT也保留异色邻线，不能用同色证明同一物理边。210790只是几十像素竖短段；201906小弧为继承结果。当前不能确认或排除新增平行/第三臂/深度层误吞，未把“不确定”写成无错误或已证实错误。

最早可量化损伤不是失核，而是事件3开始原已归属132977行230338/230339超过75°，事件4/5进一步涉及27506x原成员；最终最大84.996°。保留这些坏例，按授权不恢复R2。最大新变化组565核、最大六种子组990核未变；没有本轮巨组失控证据，但不构成安全认证。零自接触/最大gap<1.5p仅表明当前规则6仍在过滤。

R2终态残余瓶颈：201906有10个parallel拒绝和1个no_unique_support；132977有9个parallel、8个branch、1个原叶非单调；200509有69个vertex和3个parallel；53254有194个vertex；202023有1个parallel。拒绝数按解释计，重复访问不能当独立样本。下一步解除规则4有具体曲线候选依据；规则3/5保留，不作“必须先完美”门槛。

仅渲染原核，无辅助曲线/连接桥墨，无源表面遮挡。颜色、计数、低loss、支持代理和测试都不是物理、held-out、时间稳定性或准确率认证。

下一步（尚未执行，需另行冻结）：另行review/freeze：从本单元R2_OFF_TRANSPORT_FINAL同一完整458490行/260029 assigned/198461 UNKNOWN、next_version33931出发，六种子匹配比较R2_OFF=[2]与R2_R4_OFF=[2,4]；只解除parallel硬返回，保留冲突诊断、WHOLE五轮拟合、J、整曲线2p完整候选及规则1/3/5/6。优先保存201906的10条和132977的9条终态parallel拒绝及全部替代解释，报告首个新吞并/最大误差/最大组；不以身份完美为继续条件，不恢复R2。随后另冻[2,4,6]，不在本分析执行。

实际已查看的单位相对PNG：
- [scenes/scan24/stages/R2_OFF_TRANSPORT_FINAL/0012_FULL.png](scenes/scan24/stages/R2_OFF_TRANSPORT_FINAL/0012_FULL.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0005/0012_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0005/0012_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0005/0012_FULL_OBJECT_CONTEXT.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0005/0012_FULL_OBJECT_CONTEXT.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0001/0036_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0001/0036_ISOLATED_CROP.png)
- [scenes/scan24/stages/R2_OFF_TRANSPORT_FINAL/0036_FULL.png](scenes/scan24/stages/R2_OFF_TRANSPORT_FINAL/0036_FULL.png)
- [scenes/scan24/diagnostics/132977/START_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/132977/START_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0012_ADDED_MEMBERS_CROP.png](scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0012_ADDED_MEMBERS_CROP.png)
- [scenes/scan24/diagnostics/210790/R2_OFF_TRANSPORT_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/210790/R2_OFF_TRANSPORT_0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/210790/R2_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/210790/R2_OFF_TRANSPORT_0036_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/201906/R2_OFF_TRANSPORT_0036_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/R2_OFF_TRANSPORT_0036_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/negative_84842_362883/R2_OFF_TRANSPORT_0012_FULL_OBJECT_CONTEXT_CROP.png](scenes/scan24/diagnostics/negative_84842_362883/R2_OFF_TRANSPORT_0012_FULL_OBJECT_CONTEXT_CROP.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0012_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0012_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0036_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0036_ISOLATED_CROP.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0012_FULL_OBJECT_CONTEXT.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0002/0012_FULL_OBJECT_CONTEXT.png)
- [scenes/scan24/worst_events/R2_OFF_TRANSPORT/0003/0012_ISOLATED_CROP.png](scenes/scan24/worst_events/R2_OFF_TRANSPORT/0003/0012_ISOLATED_CROP.png)
- [scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0012_QUERY_CONTEXT_CROP.png](scenes/scan24/diagnostics/132977/R2_OFF_TRANSPORT_0012_QUERY_CONTEXT_CROP.png)
- [scenes/scan24/diagnostics/201906/R2_OFF_TRANSPORT_0012_ISOLATED_CROP.png](scenes/scan24/diagnostics/201906/R2_OFF_TRANSPORT_0012_ISOLATED_CROP.png)
