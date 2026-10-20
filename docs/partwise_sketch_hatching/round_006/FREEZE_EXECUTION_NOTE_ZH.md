# 冻结提交工程记录

首次`git add`被sparse-checkout拒绝，随后的commit没有创建。该shell未启用fail-fast，继续运行了只使用旧primitive的开发RED测试（TESTS_RED.json）。因此“先commit再RED”的执行顺序未实现；原日志和退出码完整保留。此时尚未编写候选、运行新18例接受集或打开接受结果，参数和测试没有按RED结果修改。

修正仅为使用`git add --sparse`明确添加本轮文件并提交，再将同一RED测试重放为TESTS_RED_COMMITTED.json。候选、接受协议和输入SHA锁仍须在任何科学接受评测前提交。本记录不把工程修正算作新的科学实验，也不覆盖第一次执行证据。
