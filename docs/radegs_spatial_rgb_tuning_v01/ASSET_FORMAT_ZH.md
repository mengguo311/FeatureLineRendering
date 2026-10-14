# 检线资产格式

scenes/<scene>/<view>/input_rgb_float32.npz：rgb，H×W×3 float32，原渲染值逐元素保留（可略大于1）。无深度/alpha，出处与SHA见PORTABLE_RGB_MANIFEST。RGB.png仅屏幕展示。

fields_native/medium/coarse.npz：detail、structural、union、normal、confidence、magnitude、profile_confidence、width_map、classmap。field只按三套尺度计算一次，所有预设引用它们。未保存庞大profile采样数组，可用原RGB精确重算。

presets/<ID>/maps.npz：soft为max(structural,lambda*detail)；darkness为1-boundary.ink(soft,gain=1,sigma=.5)的第一通道；marked bool=darkness>T（严格大于）；skeleton bool=skimage.skeletonize(marked)；candidate_darkness=darkness*marked。浮点地图float32，均为原生H×W。

candidate.png是1-candidate_darkness的8bit显示；marked.png/skeleton.png为黑色有效像素、白底。没有二次模糊，没有按图调亮度。recipe.json包含完整分析参数、阈值、分支系数、输入hash。不得拿candidate.png重新阈值代替float32地图用于精确复现。

后续05若获用户选择，需显式读取该recipe的soft/darkness/marked，然后使用既定骨架过程；不能只改变展示gain便声称用了该预设。本轮不修改05，不导出3D Gaussian或直接曲线。
