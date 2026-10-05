# Gaussian Edge 真实缓存选择检查器

中文离线研究演示：Mic / Materials；每个场景仅包含已导出的 `F_001`、`C_007`、`arc0_016`。数据由独立导出流程提供，本应用从不改写 `data/`、`SOURCE_MAP.json` 或冻结评分。

## 启动

```sh
cd /Users/menakuniay/next_npr_results/gaussian_edge_demo_v1
npm start
# http://127.0.0.1:8765
# 健康检查 http://127.0.0.1:8765/health
```

Node 20+（实测 Node 26.7.0）。Three.js、OrbitControls 在 `node_modules/three/` 本地提供，不使用 CDN。完整交付包保留该依赖后运行不需要网络。若依赖丢失，联网执行 `npm ci`。服务器仅监听 loopback；8765 被占用时自动逐个尝试后续端口，使用终端打印的地址。不能双击 HTML 代替服务器。

二进制请求 `*.bin` 自动映射到存在的 `*.bin.gz`，设置 `Content-Encoding: gzip` 与 `application/octet-stream`，浏览器透明解压。JSON/JPEG 不转码。

## 使用

- 全局模式：选择基线/增强和 Union/Color/Geometry/Outline。读取原始 category-specific 分数，在 eligible 集合内排序，取 `ceil(eligible_count * percent / 100)`，相同分数按 original ID 升序，再与评分下限相交。
- 图像点击、连续画笔、矩形自动进入局部模式；始终映射到原生 800×800 坐标。画笔半径改变会重算当前 ROI。
- 局部模式：真实 TOP4 `alpha*T` 加权；贡献小于 cutoff 的样本不参与分母；证据小于 evidence cutoff 的样本分子为零但仍保留分母。`score = Σ w*e / Σ w`。按局部候选分数排名/密度再用 score cutoff；零证据不选中。这里不要求全局 eligible，unknown/unreliable 内核仍可被本帧真实贡献选中，检查器单独展示其状态。这不是全局多视图重评分。
- 换视图清空本帧 ROI；锁定时保留 ID（不重新评分）。换场景始终清空 ID，即使锁定，因为 ID 只在本场景有意义。全局冻结排名不随视图改变。
- 三维背景为全部原始高斯中心点，使用源 RGB；高亮为真实 xyz、物理尺度和 wxyz quaternion 构造的实例化低面数椭球，或中心点。显示倍率/不透明度仅用于可视化，不改数据。高亮默认统一青绿以便辨认；源 RGB/opacity 仍在几何数组中，opacity 可检查。
- `对齐图像相机` 使用导出的 native_K / w2c；OpenCV y-down/+z 转换为 Three y-up/-z。自由旋转/缩放只改变几何检查器，左侧固定缓存 RGB 不随之变化。
- 核绘制上限显式显示 total/drawn，支持全绘制。上限绝不裁剪选择或 JSON 导出。全部绘制可能变慢。
- 悬停图像显示最多四个真实 original ID、贡献、alpha、eligible/unknown；悬停绘制核显示 ID、位置、物理尺度、原始 quaternion 和 opacity。
- JSON 导出全部 original IDs、settings、scene/frame、原生 ROI 像素/路径、完整源文件路径、source commit、相机/证据 SHA、camera metadata、可视化上限和限制。

## 科学边界

这是 **cached selection inspector**，不是实时原生 3DGS renderer。椭球核可视化不模拟原生 alpha compositing。TOP4 为截断归因，未出现的贡献不补造，部分覆盖是 unknown 而不是非边缘。独立 RGB evidence 和 OLD A/B/C 均来自缓存源，旧 A/B/C 仅显示，不用于新冻结排名。源结果没有真实三维曲线。C 是 TRAIN 的 non-fitting-for-scoring 视图，**不是盲测**。仅提供六张真实缓存帧，不宣称支持任意原生渲染视图。

出处：`SOURCE_MAP.json`、`data/manifest.json`；源 commit `20f85a15c3d3c382b94b83e8b6aa501c72009e70`。外部数据验证见父流程的 `DATA_VERIFICATION.json`，不要把它当作本应用的 UI 人工验收。

## 测试与实际输出

```sh
npm test
node tests/browser-shell.mjs
node tests/browser-radius.mjs
node tests/browser-real.mjs
```

浏览器测试使用系统 Chrome `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` 与 Playwright，不需要下载 Chromium。unit fixture 明确为合成小数组，不出现在演示页面。核心实现采用先失败再通过的垂直增量测试；记录见 `TDD_LOG.md`。

实测：5 个 Node 测试通过；包括重复三个不同 ID 的权重聚合、unknown 可选、稳定排序/ceil、原生坐标、ROI、非对称 wxyz、ID 不重排、锁定/导出、gzip 服务和路径穿越拒绝。精确投影回归读取全部六个真实相机，已知 world point 的 Three 投影与 native_K/w2c 的像素误差 <1e-7。

`browser-real.mjs` 在六张真实帧上实际鼠标点击，比较权重选择，验证帧切换/锁定、scene-scoped ID、密度、贡献/证据 cutoff、真实 WebGL context、旋转缩放、点/椭球切换、完整下载和选中/绘制数量；无 console/page errors。输出 `screenshots/browser_results.json`。截图 `screenshots/{mic,materials}_{global,roi}.png`，额外真实交互截图 `materials_interaction.png`。

真实鼠标/滑块/场景切换录屏：`screenshots/demo_interaction.webm`（26.8 秒，1440×1080，VP8，已完整解码验证）。重新录制：

```sh
PLAYWRIGHT_BROWSERS_PATH=./node_modules/.cache/ms-playwright node tests/record-demo.mjs
```

当前本机 Playwright 下载的 ffmpeg 被 macOS 杀掉，已在项目内用已可运行的系统 ffmpeg 替换；该录屏依赖不是应用运行依赖。若重新部署，录屏可选。

## 已知限制

CPU 上 800×800 四槽叠加和排序是同步计算，大矩形/全核显示可能短暂延迟。浏览器内数据不是完整多视图可见性；不会重训练、重算科学分数或填补 TOP4 缺口。只提供图像像素和已绘制高亮核的 picking，背景未选中心点不提供独立 picking。默认 20,000 高亮绘制上限明确披露，选择/导出完整保留。
