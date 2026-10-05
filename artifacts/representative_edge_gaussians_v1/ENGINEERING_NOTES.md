# 实际工程记录

S0实际RED→GREEN日志已提交；G0共13项CPU测试通过。K32全16F原始数值校准通过，但Mic F_079射线p10=.894206未达.90，所以按冻结规则隔离容量-only构建K64，一次编译成功（65.99秒）。K64全16F校准及操作门槛通过，不运行K128。所有选择预算/λ/证据阈值保持S0原值。

最终SOURCE_MAP首次校验发现自身仍在写入的`out/.../LEDGER.log`被记录为空文件散列；这是ledger工程问题，不是科学数据错误。实际RED记录在logs/LEDGER_RED.json。修复只把这个live日志从稳定文件ledger排除，重新建立并逐文件校验；科学数组、ID、相机、归一化、配置和图像均未改动。自引用FINAL/SOURCE_MAP与live AGENT/events/status同样明示排除，FINAL/report/source_map通过独立delivery verification记录散列。

plain runner新增pipeline.py，在现有全F封条有效时跳过selection.py，防止续跑重写全F封条；当前check-only实际验证全部阶段，F封条SHA256保持原字节。阶段脚本单独使用时，已有全F封条后不得重跑selection.py。外层timeout90分钟，新任务续跑不改变任何科学配方。

所有native launch均执行GPU guard，未停止外来任务；未安装依赖、扩展sparse checkout、修改旧文件或重新训练。初始90分钟内实际完成全部98姿态和全33视频。输出1.5GiB量级，两个filesystem守门持续保留root>=2GiB/commonGit>=1GiB。
