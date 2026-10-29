from pilotio import *
from PIL import Image

def verify_outputs():
    checked=0; samples=0
    for input_path in sorted((OUT/'synthetic').glob('seed_*/*/*/input.npz')):
        data=load_np(input_path)
        for method in CFG['methods']:
            folder=input_path.parent/method; geom=load_np(folder/'geometry.npz'); stats=json.loads((folder/'stats.json').read_text());fs=json.loads((folder/'fragments.json').read_text());links=json.loads((folder/'links.json').read_text())
            good=[f['id'] for f in fs if f['eligible']]; ineligible=~np.isin(data['fragment_id'],good)
            assert geom['xyz'].shape==data['xyz'].shape
            assert np.array_equal(geom['xyz'][data['protected']],data['xyz'][data['protected']])
            assert np.array_equal(geom['xyz'][ineligible],data['xyz'][ineligible])
            assert np.linalg.norm(geom['xyz']-data['xyz'],axis=1).max(initial=0)<=2+1e-9
            assert stats['refiner_calls']<=32 and stats['final_hypotheses']<=32
            assert all(not p['confirmed'] and not p['render_gap'] and p['visibility']=='UNKNOWN' for p in links)
            checked+=1;samples+=len(data['xyz'])
    real=OUT/'real_budgeted/scan24';data=load_np(real/'input.npz'); imstats={}
    for method in CFG['methods']:
        geom=load_np(real/method/'geometry.npz');fs=json.loads((real/method/'fragments.json').read_text());good=[f['id'] for f in fs if f['eligible']]
        assert np.array_equal(geom['xyz'][~np.isin(data['fragment_id'],good)],data['xyz'][~np.isin(data['fragment_id'],good)])
        assert np.array_equal(geom['xyz'][data['protected']],data['xyz'][data['protected']])
        for view in CFG['scan24_views']:
            folder=real/'figures'/view; old=np.asarray(Image.open(folder/'C8_original_JOINT.png')).astype(int); new=np.asarray(Image.open(folder/(method+'_JOINT.png'))).astype(int)
            imstats[method+'/'+view]=dict(changed_pixels=int(np.any(old!=new,axis=2).sum()),max_channel_difference_255=int(abs(old-new).max()),mean_channel_difference_255=float(abs(old-new).mean()),pixel_denominator=old.shape[0]*old.shape[1],meaning='render difference only; not edge F1 or 3D accuracy')
    js(OUT/'render_difference_metrics.json',imstats)
    verified={};lock=json.loads((ORCH/'INPUT_LOCK.json').read_text())
    for path,want in lock['files'].items():
        got=sha(path);verified[path]=dict(sha256=got,unchanged=got==want);assert got==want,path
    manifest=json.loads((OUT/'manifest.json').read_text());assert sha(OUT/'DECISION.json')==manifest['decision_sha256']
    js(OUT/'input_after_audit.json',verified)
    js(OUT/'verification.json',dict(synthetic_method_outputs_checked=checked,sample_instances_checked=samples,protected_and_ineligible_samples_exact=True,no_confirmed_or_rendered_gaps=True,shared_final_refiner_cap=32,locked_files_unchanged=len(verified),decision_unchanged=True,real_render_difference_file='render_difference_metrics.json'))
    return checked,imstats

def main():
    guard();status('FINALIZING');checked,imstats=verify_outputs()
    metrics=json.loads((OUT/'synthetic_metrics.json').read_text()); real=json.loads((OUT/'real_budgeted/scan24/metrics.json').read_text()); audit=json.loads((OUT/'input_audit.json').read_text()); ablations=json.loads((OUT/'ablation_metrics.json').read_text())
    summary={};bycase={}
    for method in CFG['methods']:
        rows=[r for r in metrics if r['method']==method];positive=[r for r in rows if r['positive_pairs']>0]
        summary[method]=dict(runs=len(rows),positive_pair_denominator=sum(r['positive_pairs'] for r in rows),true_candidate_pairs=sum(r['true_candidate_pairs'] for r in rows),false_candidate_pairs=sum(r['false_candidate_pairs'] for r in rows),mean_candidate_recall_at_precision95=float(np.mean([r['candidate_recall_at_precision95'] for r in positive])),positive_case_runs=len(positive),wrong_hypothesis_groups=sum(r['wrong_hypothesis_groups'] for r in rows),wrong_depth_candidate_pairs=sum(r['wrong_depth_candidate_pairs'] for r in rows),junction_samples_retained=sum(r['junction_samples_retained'] for r in rows),junction_sample_denominator=sum(r['junction_denominator'] for r in rows),seconds=sum(r['seconds'] for r in rows),confirmed_connections=0)
        bycase[method]={}
        for case in CFG['synthetic_cases']:
            rr=[r for r in rows if r['case']==case];vals=[r['candidate_recall_at_precision95'] for r in rr if r['candidate_recall_at_precision95'] is not None]
            bycase[method][case]=dict(runs=len(rr),mean_candidate_recall_at_precision95=float(np.mean(vals)) if vals else None,false_candidate_pairs=sum(r['false_candidate_pairs'] for r in rr),wrong_groups=sum(r['wrong_hypothesis_groups'] for r in rr),mean_assigned_sample_fraction=float(np.mean([r['assigned_samples']/r['input_samples'] for r in rr])))
    # The primary descriptive PR must include negative-only layouts as well.
    # Per-positive-case PR envelopes above are secondary; averaging them alone
    # excludes the collinear-distinct negatives from the precision denominator.
    pooled={}
    for method in CFG['methods']:
        candidates=[];positive_count=0
        for input_path in sorted((OUT/'synthetic').glob('seed_*/*/*/input.npz')):
            ev=json.loads((input_path.parent/'EVALUATION_ONLY.json').read_text()); pos={tuple(p) for p in ev['positive_pairs']};positive_count+=len(pos)
            links=json.loads((input_path.parent/method/'links.json').read_text())
            candidates.extend((p['score'],int(tuple(p['pair']) in pos)) for p in links)
        rows=[dict(threshold=None,predictions=0,tp=0,fp=0,fn=positive_count,precision=None,recall=0.)]
        for threshold in sorted({score for score,label in candidates},reverse=True):
            selected=[label for score,label in candidates if score>=threshold];tp=sum(selected);fp=len(selected)-tp
            rows.append(dict(threshold=threshold,predictions=len(selected),tp=tp,fp=fp,fn=positive_count-tp,precision=tp/len(selected),recall=tp/positive_count))
        pooled[method]=dict(positive_pair_denominator=positive_count,candidate_pairs=len(candidates),raw_PR=rows,recall_at_precision95=max([r['recall'] for r in rows if r['precision'] is not None and r['precision']>=.95],default=0.))
        assert rows[-1]['tp']==summary[method]['true_candidate_pairs']
        assert rows[-1]['fp']==summary[method]['false_candidate_pairs']
        assert positive_count==summary[method]['positive_pair_denominator']
        summary[method]['pooled_all_case_candidate_recall_at_precision95']=pooled[method]['recall_at_precision95']
    js(OUT/'pooled_all_case_raw_PR.json',pooled)
    strongest=max(['B1','B2'],key=lambda m:summary[m]['pooled_all_case_candidate_recall_at_precision95']);gain=summary['H1']['pooled_all_case_candidate_recall_at_precision95']-summary[strongest]['pooled_all_case_candidate_recall_at_precision95']
    conclusion='NO_GAIN' if gain<=0 else 'CANDIDATE_ONLY_GAIN_UNCONFIRMED'
    js(OUT/'summary_metrics.json',dict(methods=summary,by_case=bycase,strongest_non_Hough=strongest,candidate_recall_gain_H1=gain,primary_descriptive_metric='pooled all-case PR including negative-only layouts; exploratory curve envelope, not a deployed threshold',secondary_metric='mean_candidate_recall_at_precision95 averages positive-case PR envelopes only, not overall precision',unit='descriptive paired backend runs; only eight layouts, not 160 independent scenes',full_PR='pooled_all_case_raw_PR.json and synthetic/seed_*/condition/case/method/raw_PR.json',confirmed_connection_main_hypothesis='NOT_EVALUATED'))
    failures=[json.loads(p.read_text()) for p in (OUT/'logs').glob('*.json') if json.loads(p.read_text()).get('returncode',0)!=0]
    not_run=CFG['not_run']+['scan65 real Hough/refinement/render slice (M0 audited only)','ficus real Hough/refinement/render slice (M0 audited only)','real independent 3D connection labels and accuracy','visible-ink edge F1 gate','calibrated confidence weighting (neutral confidence ablation only)']
    result=dict(status='PARTIAL',scientific_conclusion=conclusion,main_hypothesis='UNDETERMINED / NOT_EVALUATED',completed=['M0 all three exact C8 assets','scan24 real fixed ROI, five methods x five paired seeds','scan24 six assets x three original-GS-occluded joint cameras','eight synthetic layouts x four conditions x five seeds x five methods','24 single-factor diagnostic ablations','real RED/GREEN and immutable-input recheck'],synthetic_runs=len(metrics),real_paired_runs=len(real),strongest_non_Hough=strongest,candidate_recall_gain_H1=gain,confirmed_links=0,unsupported_rendered_gaps=0,not_run=not_run,excluded_engineering_run='real/scan24: final refiner attempt budget bug; retained with raw RED and original code snapshot, never used as scientific result',valid_real_results='real_budgeted/scan24',raw_failures=[dict(log=f['log'],returncode=f['returncode']) for f in failures],claim='fixed-fused-input postprocessing',scope='Independent sparse weighted Hough adaptation, not author code reproduction',stop_after_this_pilot=True,utc=now())
    js(OUT/'RESULT.json',result)
    lines=['# C8 线高斯 Hough 有界 pilot：实际运行报告','',f'结论：**PARTIAL；{conclusion}；主连接假设 UNDETERMINED**。真实 scan24 的预算一致 H0/H1 没有通过资格检查的最终组，最终图像保持原 C8。没有填补任何缺乏证据的缺口。','',
    '## 范围和证据','使用精确 C2L50+05 8BUILD arm C，未使用被拒绝的 core 子集。此次是 fixed-fused-input postprocessing；原融合输入包含8个BUILD，历史inspection视角已曝光，不是新留出泛化。原场景 full-SH3、filter、上游检线/升维和旧线资产不变。样本ID和线Gaussian行号独立命名，source-GS关联缺失均为UNKNOWN。','',
    '| 场景 | 线Gaussian | 控制点 | parent | means最大再生误差 | 最大重投影误差px | h |','|---|---:|---:|---:|---:|---:|---:|']
    for scene,a in audit.items():lines.append(f"| {scene} | {a['line_gaussians']} | {a['controls']} | {a['parents']} | {a['means_max_abs_error']:.3g} | {a['reprojection_pixel']['q'][-1]:.3g} | {a['h']:.6g} |")
    lines+=['','完整诊断见 input_audit.json、audit/*/line_samples.npz。h由有序同parent同piece的非零相邻线样本间距估计；精确重复和可用source-view直方图另存。切向来自优化control导数及投影Jacobian；无定位误差校准，未把Gaussian形状协方差当成测量噪声。','',
    '## 真实 scan24','固定BUILD 0000 ROI=[280,140,515,340]，由原source图预先选定。按parent顺序保留完整路径，输入8192样本、140 parents；419样本/13 fragments通过最终公共直线资格。保留所有不合格及未分配样本；原端点和重复交叉支持样本受保护。最大允许移动2h，原采样数、opacity及横向/切向Gaussian宽度不变。','',
    '| 方法/seed0 | 最终假设 | 有限区间 | 归属样本 | 几何变化样本 | 最终拟合次数 | 合法连接候选 |','|---|---:|---:|---:|---:|---:|---:|']
    for r in real[:5]:lines.append(f"| {r['method']} | {r['final_hypotheses']} | {r['intervals']} | {r['assigned_samples']} | {r['changed_samples']} | {r['refiner_calls']} | {r['candidate_links']} |")
    lines+=['','B0/B1的局部几何变化属于共享鲁棒拟合的效果，不能归因Hough。Hough稀疏粗层为覆盖量化漂移使用了很宽的位置格；在此ROI及32次公共最终拟合预算下，优先峰未产生完整合格fragment。此限制说明本次实现/离散/输入资格组合没有显示增益，不证明所有Hough方法均不可行。未继续改格宽、ROI、资格或预算来追求通过。','',
    '最终可见图来自已审查的成熟CPU EWA联合source+ink深度排序，保留完整source SH/filter；它是既有CPU近似，不宣称官方CUDA RaDe等价。0000/0012/0036全部输出。彩色groups、raw峰和候选图明确为X-RAY诊断，不能代替最终遮挡渲染。图像差值只是实际渲染变化，不是edge F1或三维正确率。','',
    '- [真实全帧对照](real_budgeted/scan24/figures/0000/COMPARISON_FULL.jpg)','- [固定ROI对照](real_budgeted/scan24/figures/0000/COMPARISON_ROI.png)','- [真实失败：被拒绝的raw峰支持](real_budgeted/scan24/figures/0000/NEGATIVE_RAW_PEAKS_FULL.jpg)','- [侧视0012](real_budgeted/scan24/figures/0012/COMPARISON_FULL.jpg)','- [侧视0036](real_budgeted/scan24/figures/0036/COMPARISON_FULL.jpg)','',
    '## 配对合成后端比较','8类布局、4种单因素条件、5个种子、5法，共800个实际方法运行。每个配对输入保存在input.npz并记录相同hash；曲线身份、连接标签和真值坐标只传给评价器。使用随机斜向旋转避免轴对齐偏好。该直接样本基准未运行冻结上游重建，也没有真实二维内部证据；不是重建画质实验。','',
    '| 方法 | 有正例运行数 | 正连接对分母 | 正候选 | 错候选 | 全案例候选R@P≥.95 | 错误假设组 | 后端秒 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for method,s in summary.items():lines.append(f"| {method} | {s['positive_case_runs']} | {s['positive_pair_denominator']} | {s['true_candidate_pairs']} | {s['false_candidate_pairs']} | {s['pooled_all_case_candidate_recall_at_precision95']:.4f} | {s['wrong_hypothesis_groups']} | {s['seconds']:.2f} |")
    lines += ['',f'包含共线独立结构等纯负例布局的全案例PR中，相对最强非Hough对照 {strongest}，H1候选R@P≥.95差值为 {gain*100:.2f} 个百分点。这是探索性PR曲线包络，不是已选择部署阈值，也不能冒充confirmed连接召回。pooled_all_case_raw_PR.json保存全案例原始TP/FP/FN和完整阈值曲线。每个输入另存完整raw PR；空预测precision=null，无正例recall=null。八种布局才是有限的结构单位，重复种子不是额外独立场景。','',
    '早期汇总中的逐正例案例平均R@P≥.95（H1=0.7333，B1=0.7417）仅保留为次要描述：它不把纯负例布局计入precision分母，不能用作主精度门槛。最终主汇总已纳入这些负例，未改动方法、参数、输出或候选score。错误假设组数量包含重复假设，不能解释为独立已接受错误连接；实际confirmed连接始终为0。','',
    '每方法共享相同有限支持拆分、端点合法性、5轮Huber正交IRLS和最多32次最终拟合尝试；B1枚举所有合法端点邻接，B2为2048次非破坏性RANSAC。提议内部计算量不完全相等，实际点-方向/点-候选评估数、候选数、预处理和耗时均记录，不能把更多计算当纯算法收益。Hough单样本粗层票重≤1（浮点误差量级例外），fine层同样归一化，密度与切向开关独立。置信度缺校准而固定1，no-confidence消融必然退化，未验证置信度加权假设。','',
    '## 正确性、失败与限制','真实第一轮把32限制用于成功输出数量，却允许更多最终拟合尝试：B2=52、H0=469、H1=435。此轮保存在real/scan24和code_snapshots/uncapped_engineering_run，排除科学比较。实际数据回归测试记录三个RED失败；修复公共尝试上限后GREEN，再完整重跑真实三视角及配对种子。另保存首次缺core的RED和M0路径拼接错误。没有删除失败记录。','',
    '交付检查另发现B0错误应用跨假设直线NMS，跳过独立共线片段。真实RED证明两独立片段仅输出一条；修复为B0绕过去重后GREEN，按原始保存输入重算160个B0合成输出。旧输出和修复前源码保存在engineering_history/B0_independence；真实scan24五个B0种子重放的geometry/membership逐元素相等。B1/B2/H0/H1参数、输出和score均未变。','',
    '合成日志已到SYNTHETIC_DONE（800主运行、24消融），但命令包装层被观察到返回143，子进程退出码未落盘，明确UNKNOWN。保留M1_transport_observed.json；不把它改写成exit 0，也不据此假称科学失败。下述逐文件检查确认的是持久化结果完整性，不能补造进程退出状态。','',
    f'最终产物检查验证{checked}个合成方法输出：原样保留所有不合格/受保护样本、无丢样本、移动≤2h、最终拟合≤32、所有候选confirmed=false且render_gap=false。95个锁定输入文件与父级DECISION前后不变，详细证据见verification.json、input_after_audit.json和logs/。','',
    '主门槛仍冻结为precision≥.95时recall增加≥10pp、错误合并不增加、覆盖不降低、正确内部碎片减少≥20%、固定视角F1下降≤1pp。没有完成M2确认及独立真实标签，故主门槛均不能宣称通过。geometry-only连线始终UNKNOWN/inferred，不把遮挡未知充当支持。','',
    '## 明确未运行']
    lines += ['- '+item for item in not_run]
    lines += ['', '## 实现来源与停止','参考Dalitz等IPOL 2017的三维线参数化与投票思路，固定作者代码commit为3f2910f6534775e57fa449a8d555be3b5a031aee。本代码为独立NumPy稀疏、加权、有限支持适配，不是作者实现的精确复现；未复制其逐次删除内点行为。原文：https://www.ipol.im/pub/art/2017/208/ 。','本轮至此停止；不追加科学调参、不执行H4、不修改旧source，不启动其他模型或训练。']
    (OUT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    snapshot=OUT/'code_snapshot';snapshot.mkdir(exist_ok=True)
    for p in CODE.iterdir():
        if p.is_file():shutil.copyfile(p,snapshot/p.name)
    js(OUT/'code_snapshot_manifest.json',{p.name:sha(p) for p in snapshot.iterdir() if p.is_file()})
    receipts=[json.loads(p.read_text()) for p in sorted((OUT/'logs').glob('*.json'))]
    js(OUT/'runtime.json',dict(started_utc=CFG['started_utc'],finished_utc=now(),wall_seconds=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(CFG['started_utc'])).total_seconds(),strict_serial=True,cpu_affinity=sorted(os.sched_getaffinity(0)),commands=receipts,finalizer_command_receipt='The current logs/finalize*.json receipt is written by run_logged after this process exits'))
    status('COMPLETE_PARTIAL',scientific_conclusion=conclusion,not_run=not_run)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
