# 执行与失败说明

- 首次预检 GPU0 有其他用户计算进程；没有占用、停止或修改它们。选择 CPU 全核复现算子，并先在四个历史 construction native 缓存上做 RGB、alpha、逐核可见质量、feature forward 和 adjoint 校准。CPU replica 与执行 CUDA native 分开命名。
- camera fixture 最初将所有 metadata 旋转视为 1e-6 内理想正交，真实 metadata 最大偏差 Lego 1.25e-6 / Chair 2.17e-6，测试失败。没有改相机或放宽实验质量阈值；改为验证实际 c2w 约定转换和 w2c 精确互逆，这是本任务要求的坐标契约。失败日志保留。
- mesh near-clip 初始 fixture 恰好投影成退化直线，失败后修复合成 fixture，保留 `mesh_GREEN_attempt1.log`。新旧 thin A tube 的顶点和面逐 bit 相等，基线不是另一个拟合图。
- native、fusion、camera/heldout、region、mesh/export 模块的首次缺失实现 RED 和后续 GREEN 均保留。媒体 helper 是新增后实际33帧合成验收，没有将它伪称为预实现 RED。
- 独立方法审阅指出了代码 hash 续跑、校准绑定、上游依赖和顶点来源归属问题；在新 construction 提取前修复并冻结。旧审阅 snapshot 和修复复查分别保留，未覆盖前一版意见。
- 首次 `nohup` 启动在后续 PID 检查时已不存在、日志为空，具体宿主终端生命周期原因未确定；当时没有有效 construction 提取产物。随后改用持续执行 session 启动同一独立 runner，逐单元 seal 与 resume 不依赖代理逐次调度。这个启动问题不作科学失败结论。
- 全部宽度选择和构建规则在保留视角开启前冻结。任何实际 producer 异常保留在 `logs/failures.jsonl`，运行状态与视觉质量分开判断。
- 主四臂完成后，原 capped widened 的 DEV 墨量匹配仍不足。另冻结 `PROTOCOL_MATCHED_INK_AUDIT.json`，追加只改旧图固定世界半径的 DEV 均值匹配诊断；不更改主协议、资产、阈值或 verdict。两场景达到0.003647%/0.005461%的均值误差；reserved 已有主实验曝光，且非逐图等墨量。独立检查44个主文件 hash 不变。
- 追加脚本首轮停在旧图资产 geometry hash 校验：主 thin/widened 的 hash 使用导出前 int64 faces，导出 NPZ/GLB 使用 int32。索引数值与顶点完全不变；独立核验导出后 GLB/OBJ/NPZ 一致，并精确重算 int64 回转 hash。保留原主记录及 FAILURE_ATTEMPT_01.json，未通过重写 seal 掩盖问题。main multi24/two_source hash 无此问题；追加资产统一为 float32/int32。
- 离线旋转器通过 JavaScript 语法和8个内嵌几何的静态检查；没有可用浏览器，因此未声称实际拖动交互验收。视频完整解码与全部帧条带检查是另一项独立证据。
- 最终独立审计 PASS 只表示来源、固定几何、投影媒体与保护契约有效；科学结论为 NO_GO_CONTOUR_OVERFILL / PARTIAL_SHAPE_RECOVERY。保留执行成功和视觉失败的区别。
- 交付检查发现 ignored RGB/alpha 缓存属于原 seal 依赖，新 checkout 不能直接跳过校验。新增非核心缓存恢复工具，只恢复缺失文件且要求字节 hash 精确匹配；Lego r_7 已真实重建验证，未修改核心方法、原缓存、seal 或 BUILD。主流水线和科学协议不变。
- 首次 Git 暂存因既有 sparse-checkout 未包含本 stage 的 out/.gitignore 而返回非零。随后对三个授权路径使用 `git add --sparse`，没有更改稀疏配置或触及旧树。此问题是交付操作问题，与实验有效性无关。
