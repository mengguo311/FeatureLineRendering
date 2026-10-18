from env import *
if __name__=='__main__':
 review('00_scope_and_three_rounds_GO','''GO执行恰好三轮有界pilot，科学输入只读原C8/source，继承11可用病例和一个UNAVAILABLE，不选新漂亮病例。先输入/CPU校准复核。旧报告的中心深度宽度不能证明无局部面片。
预冻三轮：1 exact满秩effective covariance沿像素ray的一维条件高斯mode/variance，保持原EWA alpha*T与center排序，和旧center宽度同门槛对照；2 DEV+额外固定BUILD的有限责任软sheet分区及跨视角资格；3原预留两个历史展示视角验证，若前两轮NO_GO则做条件顺序/源层归属/视角遮挡的固定证伪，不扩场景、不启第四轮。
新增BUILD仅按旧BUILD身份选择DTU0024、Ficus train_r_7，非按检出质量。原保留0012/0036和test_r_14/test_r_79直到第三轮才运行新计算。
全source有限EWA贡献复用已审计定义，另做all-N与重渲染。工程不通过先修同轮，不改科学阈值。单轮最长90分钟、全任务12GiB，两核、无GPU/下载/训练/改source。''',[OLD/'REPORT_ZH.md',OLD/'COUNTS.json',OLD/'SOURCE_MANIFEST.json',ROOT/'ROLLBACK_RECEIPT.json'])
 state('PREFLIGHT',status='RUNNING',children=[os.getpid()]);js(ROOT/'ROLLBACK_BEFORE.json',rollback());files=json.loads((OLD/'SOURCE_MANIFEST.json').read_text())['files'].copy()
 for p in [OLD/'CASE_FREEZE.json',OLD/'CONFIG.json',OLD/'COUNTS.json',OLD/'REPORT_ZH.md',OLD/'RESULTS_MANIFEST.json',OLD/'VERIFY_REPLAY.log']+list(GC.glob('*.py')):files[str(p)]=sha(p)
 for p,h in files.items():assert sha(p)==h,p
 for s in SCENES:
  assert AUX[s] in registry()[s]['build_views'] and AUX[s] not in RESERVED[s];p=rawpath(s,AUX[s]);assert p.exists();files[str(p)]=sha(p)
 for p in OLD.glob('scenes/*/stage1/*/*/*/EVIDENCE.npz'):files[str(p)]=sha(p);q=p.parent/'RESULT.json';files[str(q)]=sha(q)
 for p in OLD.glob('scenes/*/stage1/*/reference/*'):files[str(p)]=sha(p)
 for p in OLD.glob('scenes/*/stage0/REFERENCE.npz'):files[str(p)]=sha(p)
 js(ROOT/'SOURCE_MANIFEST.json',dict(files=files,scientific_input='original C8 arms/C and source; old measurements as immutable control, no core labels'))
 shutil.copyfile(OLD/'CONFIG.json',ROOT/'CONFIG.json');shutil.copyfile(OLD/'CASE_FREEZE.json',ROOT/'CASE_FREEZE.json')
 protocol=dict(exact_rounds=3,DEV=DEV,AUX=AUX,RESERVED=RESERVED,arms=['line','shifted_12px','source_geometry_axis','shuffled_sides'],conditional=dict(method='exact Gaussian restricted to perspective ray; camera-z t, r_z=1',finite_mahalanobis=9,near=.2,min_valid_responsibility=.8,width_gate_p=8,uncertainty_width='max(weighted mode q90-q10,2.563103*weighted median conditional sigma)',sort='frozen original mean-depth EWA order; no opacity/color change',max_native_error_p=4,max_native_error_relative=.02),partition=dict(min_unique_pixels=10,min_unique_sources=3,max_rms_p=1,min_spread=.005,min_two_sheet_relative_gain=.3,complexity_penalty='3*log(unique_pixel_N) per extra plane',max_shared_source_overlap=.85,conditional_sigma_p_max=4,finite_support_q=9,soft_assignment='source responsibility weighted posterior; no exclusive source labels',crossview_overlap=.15,crossview_normal_deg=20,crossview_symmetric_plane_p=2,crossview_center_distance_p=20,crossview_pairing_margin=.05),round3=dict(mode='reserved verification or predeclared falsification; no new parameter fitting',order_counterfactual='recompute alpha*T after conditional-mode ordering at existing ROI pixels only',visibility_tolerance_relative=.02,visibility_tolerance_p=4,minimum_comparable_fraction=.6),world_proxy='median original line camera-z / sqrt(fx*fy); not metres',max_round_seconds=5400,max_GiB=12,parameter_retuning_forbidden=True)
 js(ROOT/'PROTOCOL_FREEZE.json',protocol)
 (ROOT/'METHOD_FREEZE_ZH.md').write_text('''# 三轮预冻方案

原11有效case和scan24 unavailable原样继承。DEV：0000/0000/train_r_80；R2新增构建：0024/0024/train_r_7；R3保留：0012/0036、test_r_14/test_r_79。所有历史曝光，非blind。

R1：Σ使用官方effective covariance（含filter补偿），相机μ=Rμw+t、Σc=RΣwRᵀ，r=[(u-cx)/fx,(v-cy)/fy,1]。沿ray高斯：t*=rᵀΣc⁻¹μ/(rᵀΣc⁻¹r)，σ²=1/(rᵀΣc⁻¹r)，qmin=(t*r-μ)ᵀΣc⁻¹(t*r-μ)。这是高斯条件proxy，不是真表面，不是简单center z。qmin<=9且t>.2才具有限3sigma支持；不合格贡献保留为UNKNOWN质量。不重排原alpha*T，使R1只测深度proxy变量。模式quantile变窄但条件sigma很宽仍不认证。

R2：按同预算像素责任取条件3D点，保留sourceID多重软归属，原native/proxy深度作一致性检查。单片与按line两侧的双片作稳健残差/展开条件/复杂度比较；同核两侧高度重复不能认证双片。像素是有效样本单位，不能把一个像素多个核当独立采样涨置信。线引导限制只划分已有观测，不创建缺失面。去线源几何轴、错位线、固定随机打乱两侧标签均保留。没有两相机资格则REFUSED，不升级primitive。

R3：只用预冻保留视角。若R2无GO，不扩大ROI；比较原mean排序与条件模式重排的局部责任变化、源ID重叠、可见/遮挡/缺观测，判断失败是否可能来自proxy或视角。不能从缺对应就断言rolling silhouette，更不自动生成3D边界。若有合格代理只做独立源角色诊断色，不改原模型。第三轮后硬停止。

null预算：line/shift/geometry-axis均每case同样最多9沿线×7跨线offset；shuffled_sides使用完全相同原线像素和责任，只确定性打乱非中心两侧标记，是标签null而非新图像。相邻非线区域由移位臂提供。源责任核数和质量可因遮挡自然不同，另做匹配贡献质量报告，不能凭核数取胜。

科学GO需跨视角可辨识且相对null出现可解释增益、负例没有同等假面片。只有候选增加是PARTIAL，不能称物理面。工程校准保留旧RGB .02/alpha .02/depth p95 .15、query abs5e-7、allN2e-12，不放宽。
''')
 state('PREFLIGHT_READY',status='GO_ROUND1_TESTS',children=[])
