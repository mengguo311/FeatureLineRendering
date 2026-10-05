# 工程记录

S0 protocol commit 6747a548e44d5e53c602804886559ce7bad18780，实际测试日志commit 7f6d2a3523f4b3e5f91a157b4784bb572716a559，SSH fetch读回文件逐byte核验在logs/S0_REMOTE_READBACK.json。S0不重写，全部科学源代码/配置不在生产后更改。

初次nohup经工具启动，在调用会话结束时其进程被回收，停在Lego F079开始处；没有读C/arc，也没有改写已封存F。随后改由独立tmux会话 representative-three-production 启动相同plain pipeline，从已校验封条恢复。此次恢复使用相同source/hash/normalization与deadline，没有改变任何科学方法或已完成证据。最终退出码与全部阶段封条在新out。

所有历史文件、checkpoint与native build只读引用，没有对hardlink chmod或inplace写入。A是此前不存在的新三场景同历史算法新计算，完整原F统计单独保存，未冒称复制历史结果。新out不入Git；新stage显式add --sparse，测试与读回日志显式force add（仓库全局忽略log）。

全部F封存后、C前，原CPU审计在Chair的float64 B_score绝对误差6.795e-6触发原5e-6界限；原audit.py/断言不改。额外stored-float32独立算术验证保持相同界限，三scene误差约1e-14，证明封存生产算术一致。详见AUDIT_ARITHMETIC_NOTE.md和POST_S0_VERIFICATION_BINDING.json，S0/F seal不变；补充代码及诊断先提交再打开C。此项原失败在最终报告与machine JSON并列披露。
