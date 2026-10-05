import json,hashlib,subprocess,time
import numpy as np,torch
from runtime import *
from data import CFG,CHECKPOINT,selection,input_snapshot
from renderer_adapter import load_checkpoint
from evaluation import prepare,assess

def get_result(name):
    p=ART/'results'/f'{name}.json'
    return json.loads(p.read_text()) if p.exists() else None

def paired_profiles(base,method,role):
    a={x['id']:x for x in base['metrics']['per_view'] if x['role']==role};b={x['id']:x for x in method['metrics']['per_view'] if x['role']==role};before=[];after=[];counts=[]
    for k in a.keys()&b.keys():
        x,y=a[k],b[k];xx=[];yy=[]
        for p,q,r in zip(x['profiles'],y['profiles'],x['reference_profiles']):
            if p['width_px'] is not None and q['width_px'] is not None and r['width_px'] is not None:xx.append(abs(p['width_px']-r['width_px']));yy.append(abs(q['width_px']-r['width_px']))
        counts.append(len(xx))
        if xx:before.append(float(np.mean(xx)));after.append(float(np.mean(yy)))
    return {'before_px':float(np.mean(before)) if before else None,'after_px':float(np.mean(after)) if after else None,'common_profiles':sum(counts),'view_counts':counts,'aggregation':'macro means over paired common profiles; missing excluded with explicit counts'}

def media(manifest,names):
    ffmpeg=INPUT/'deps/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';records=[];uids,labels,sel=selection()
    base=load_checkpoint(CHECKPOINT);views=prepare(manifest,base,('dev-path',))
    for name in names:
        path=CHECKPOINT if name=='R0_B0' else OUT/'checkpoints'/f'{name}.pth'
        if not path.exists():continue
        model=load_checkpoint(path);ev=assess(model,views,labels,name,[f['theta_deg'] for f in manifest['roles']['train']],True);result(name+'_devpath',ev)
        directory=OUT/'renders'/name/'dev-path';video=ART/'videos'/f'{name}_devpath.mp4'
        subprocess.run([str(ffmpeg),'-y','-loglevel','error','-framerate','12','-i',str(directory/'dev-path_%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
        # Decode every full frame; distinct SHA and count, no prefix-only validation.
        raw=subprocess.check_output([str(ffmpeg),'-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'])
        size=512*512*3;assert len(raw)%size==0;frames=len(raw)//size;digests=[hashlib.sha256(raw[i*size:(i+1)*size]).hexdigest() for i in range(frames)]
        assert frames==len(manifest['roles']['dev-path'])==36;assert len(set(digests))>30
        rawbytes=video.read_bytes();assert rawbytes.find(b'moov')<rawbytes.find(b'mdat')
        records.append({'name':name,'video_sha256':sha(video),'codec':'H264','pixel_format':'yuv420p','faststart_verified':True,'full_frames_decoded':frames,'unique_decoded_frame_sha256':len(set(digests)),'decoded_sha256':digests,'camera_manifest_sha256':sha(OUT/'data_manifest.json'),'scope':'exploratory development full path; not TEST; task A RGB only, no temporal superiority claim'})
    result('MEDIA',records);return records

def report(manifest):
    results={p.stem:json.loads(p.read_text()) for p in (ART/'results').glob('*.json')};base=results.get('R0');gates={};lines=['# v2 原生实验执行报告','', '本报告记录新实测；245e056 的公开指标重分析属于历史报告复核。单场景单种子诊断不构成正式 GO。旧高对比 TEST/path 已成为探索性开发资料，原一次封印评价仍保留；旧低对比/远背景 TEST 未读取。独立新 TEST 保持 **TEST_CLOSED**。','', '## R0：原 checkpoint 只读扫描','']
    if base:
        lines += [f"实际 checkpoint SHA256：`{base['checkpoint_sha256']}`。N={base['N']}，固定 C1={base['C1_count']}。有效颜色范围 [{base['color_min']:.6g}, {base['color_max']:.6g}]，候选超盒通道 {base['candidate_channels_outside_box']}。零步投影与对称扰动独立记录。贡献覆盖不是错误核召回；表面中心/厚度仅使用 z=0 oracle 作评价代理。",'', '| 角色 | band MSE（float） | W px | 可测率 | 全前景孔洞 | 外轮廓 MSE |','|---|---:|---:|---:|---:|---:|']
        for role,s in base['metrics']['summary'].items():lines.append(f"|{role}|{s.get('edge_mse_linear',0):.6g}|{s.get('W_abs_error_px',0):.6g}|{s.get('profile_measurement_fraction',0):.4f}|{s.get('full_foreground_holes',0):.6g}|{s.get('outer_contour_mse',0):.6g}|")
    lines += ['','## R1：固定权重颜色能力','', '原生 override_color 和颜色反向的 A/Aᵀ 使用固定排序、alpha 与提前终止；无 N×H×W 张量。每个 Gaussian 跨视角共享 RGB，非候选有效颜色保留 SH0 下限截断及 >1 值。逐像素区间下界仅为必要条件。视角等权，权重后的 MSE=2P/M，float32 原生算子采用 float64 求和及预先固定的 3e-7 MSE 数值余量。','', '| 单元 | 拟合角色/集合 | P 上界 | D 下界 | gap | MSE 上/下界 | 状态 |','|---|---|---:|---:|---:|---|---|']
    for name in ('F00','F01','F10','F11'):
        r=results.get(name)
        if not r:lines.append(f'|{name}|未执行|||||PENDING|');continue
        c=r['certificate'];lines.append(f"|{name}|{' + '.join(r['fit_roles'])} / {r['validation']['selected_count']}|{c['P']:.6g}|{c['D']:.6g}|{c['gap']:.6g}|{c['mse_upper']:.6g} / {c['mse_lower']:.6g}|{r['claim']}|")
    lines += ['', 'F10/F11 使用额外诊断监督，只是能力参照，不参加仅原 train 方法排名。全体 Gaussian 是容量支线。gap 大时只报告优化未充分；即使数值下界超过阈值，也只涉及该固定权重和盒约束，不推断 3DGS 基本极限。所有角色分别评分，增加诊断监督后重新计算实际内插/外推状态。band-only 的 outside 损伤完整保存，不作为合格修复。', '']
    for name in ('F00_outside','F01_outside','F10_outside','F11_outside'):
        if name in results:
            r=results[name];lines.append(f"条件 outside 对照 {name}：最终 {r['trace'][-1]}，fit 角色 {r['fit_roles']}；保持 band MSE 目标，非 L1 替代。")
    l1=results.get('C1_exact_convex')
    if l1:
        f=l1['final_objective'];old=sum(l1['v1_Adam_same_objective'].values());lines.append(f"相同 v1 凸目标（量化 train band L1 + outside MSE）：原 Adam 全视角目标={old:.8g}；Chambolle–Pock 可行目标={f['exact_v1_primal']:.8g}，对偶={f['dual_lower']:.8g}，gap={f['gap']:.8g}。有限预算尚有 gap 时不称已证明最优；band MSE 最优值不能代替 L1 证明。")
    lines += ['','## R2：7000 步 2×2 底座诊断','','四组全部实际重训练，4096 初始点、SH0、同一 24 张量化线性 PNG、同一增密与学习率日程。surface 仅给 z=0 表面中心，颜色恒为 127/255，无真 UID 标签；原生最近邻尺度随初始化制度改变。oracle 正则中心离面与法向厚度，tau=0.015 场景单位，未用中心深度代替表面监督。每 epoch 保存全部训练相机 RGB 目标与几何项。','', '| 分支 | 初始化 | oracle | 最终 N / 参数 | 秒 | dev-out band MSE | dev-out W |','|---|---|---|---:|---:|---:|---:|']
    for name in ('G00','G10','G01','G11'):
        r=results.get(name)
        if not r:lines.append(f'|{name}|PENDING||||||');continue
        s=r['metrics']['summary']['dev-out'];lines.append(f"|{name}|{r['init']['regime']}|{r['oracle_geometry']}|{r['final_N']} / {r['parameters']}|{r['duration_seconds']:.1f}|{s['edge_mse_linear']:.6g}|{s.get('W_abs_error_px',0):.6g}|")
    if all(k in results for k in ('G00','G10','G01','G11')):
        x={k:results[k]['metrics']['summary']['dev-out']['edge_mse_linear'] for k in ('G00','G10','G01','G11')};effects={'G01-G00':x['G01']-x['G00'],'G11-G10':x['G11']-x['G10'],'G10-G00':x['G10']-x['G00'],'G11-G01':x['G11']-x['G01'],'interaction':x['G11']-x['G10']-x['G01']+x['G00']};lines += ['', 'band MSE 因素效应/交互：`'+json.dumps(effects)+'`。最终 N 不同，需要数量匹配确认后才能作正式因果优势或效率排名。未追加 14000 步；不把新的学习率策略混为唯一迭代数改变。']
    lines += ['','## R3：原 B0 同权限对照','','各组相同 B0、固定 1379 UID、固定 ROI/标签/opacity/中心；O-color 与 O-cov 共用 band L1 + outside MSE + coverage。普通微调使用全图 0.8 L1+0.2 SSIM，加相同 coverage，并具有完全相同参数权限。协方差组实际检验 coverage→scale/rotation 梯度。可靠前景（coverage>0.99）不透明约束与外缘连续 AA coverage 分开处理；报告 band、非 band 和全前景孔洞。','', '| 分支 | 步数 | 优化秒 / 预处理秒 | dev-out band MSE | outside 损伤 | 全前景孔洞 | 配对 W（前→后/条数） |','|---|---:|---:|---:|---:|---:|---|']
    for name in ('O_color','O_color_ordinary','O_cov','O_cov_ordinary','O_color_ordinary_time','O_cov_ordinary_time'):
        r=results.get(name)
        if not r:continue
        s=r['metrics']['summary']['dev-out'];pair=paired_profiles(base,r,'dev-out');lines.append(f"|{name}|{r['steps']}|{r['optimizer_wall_seconds']:.3f} / {r['preprocessing_seconds']:.3f}|{s['edge_mse_linear']:.6g}|{s['outside_rgb_change_mse']:.6g}|{s['full_foreground_holes']:.6g}|{pair['before_px']} → {pair['after_px']} / {pair['common_profiles']}|")
        if name in ('O_color','O_cov'):
            bs=base['metrics']['summary'];ds=r['metrics']['summary'];gates[name]={'band_improvement':1-s['edge_mse_linear']/bs['dev-out']['edge_mse_linear'],'dev_in_mse_increase':ds['dev-in']['edge_mse_linear']-bs['dev-in']['edge_mse_linear'],'psnr_drop':bs['dev-out']['psnr_linear_db']-s['psnr_linear_db'],'hole_increase':s['full_foreground_holes']-bs['dev-out']['full_foreground_holes']}
            g=gates[name];g['pass']=g['band_improvement']>=.1 and g['dev_in_mse_increase']<=1e-5 and g['psnr_drop']<=.2 and g['hole_increase']<=.001
    lines += ['','## R4 / R5 / 正式阶段','','R4：条件未执行。当前仅完成自然任务首轮操作与有限预算优化；若归因仍不清楚，下一恢复阶段须使用已知 UID 的可恢复尺度探针（最多六组），优化器不能读取原参数/倍率。','', 'R5：条件未执行；保留原 epsilon=0.02，原候选不重算、不改证书阈值。尚无正式局部控制收益证据，因此不先投入空间筛选重写。三态 near/far/uncertain、支持包围盒与独立表面关系评价仍待控制门槛后实施；Gaussian 支持关系不是物理接触。','', '未开启 opacity/position、拆分、软边、m(x)、新 kernel、多场景三种子或独立新 TEST。现有工程 pilot 不能支持 H1–H5 方法优势。旧低对比 no-op 和远背景 C1 跨阈值拒绝仅引用历史证据，本轮没有打开这些 TEST。','', '## 封印、成本与限制','','量化 train 与浮点参考同时评分；全前景和外轮廓独立保存。W 同时给可测率/拒绝原因和共同有效剖面配对，缺失不当作零。新底座标签均 unknown，mask/foreign 分数不用于底座排名。原 C1 约 404.5 秒选择预处理来自历史测量，本轮复用固定集合；新控制预处理与优化墙钟分别记录，等步骤与等优化时间普通对照均保存。视频为实际 36 帧开发路径 H264/yuv420p/faststart，每帧完整解码验 SHA；未实测重投影时间稳定优势。','', 'dev 门槛：`'+json.dumps(gates,ensure_ascii=False)+'`。即便绝对门槛通过，仍需超过同权限普通微调并完成多个场景/种子，才可开启正式结论。独立 TEST_CLOSED 的工程原因是开发门槛/方法优势/正式数量匹配与多种子证据尚未完成，不能用新 TEST 帮助拟合。','']
    probes=[k for k in results if k.startswith('R4_')]
    if probes:
        lines += ['','### R4 实际条件触发结果','']
        lines += [f"{k}: before={sum(results[k]['before'].values()):.6g}, after={sum(results[k]['after'].values()):.6g}, improvement={results[k]['relative_improvement']:.3%}; known-UID solver does not read original scales/amplitude." for k in sorted(probes)]
        lines=[x.replace('R4：条件未执行。当前仅完成自然任务首轮操作与有限预算优化；若归因仍不清楚，下一恢复阶段须使用已知 UID 的可恢复尺度探针（最多六组），优化器不能读取原参数/倍率。','R4：自然局部操作未显示 10% 开发潜力，条件触发了六组可恢复尺度探针，结果见末表；短优化失败仍不等于无可行解。') for x in lines]
    (ART/'REPORT_ZH.md').write_text('\n'.join(lines))
    done=[k for k,v in results.items() if isinstance(v,dict) and v.get('status')=='COMPLETED'];expected=['R0','F00','F01','F10','F11','C1_exact_convex','G00','G10','G01','G11','O_color','O_color_ordinary','O_cov','O_cov_ordinary','O_color_ordinary_time','O_cov_ordinary_time']
    original=json.loads((OUT/'original_inputs_before.json').read_text());after=input_snapshot();unchanged=original==after;assert unchanged
    atomic_json(ART/'INPUT_INTEGRITY.json',{'before_manifest_sha256':sha(OUT/'original_inputs_before.json'),'after_content_identical':unchanged,'checked_file_count':len(original),'input_hashes':original,'closed_low_far_test':'not read or hashed; directory metadata only, excluded from input scan'})
    atomic_json(ART/'FINAL.json',{'state':'DIAGNOSTIC_PILOT_COMPLETED_TEST_CLOSED' if all(k in done for k in expected) else 'PARTIAL_RUNNING_OR_BLOCKED','completed_units':done,'remaining_units':[k for k in expected if k not in done],'R0':'COMPLETED' if 'R0' in done else 'PENDING','R1':'COMPLETED' if all(k in done for k in ['F00','F01','F10','F11','C1_exact_convex']) else 'PENDING','R2':'COMPLETED' if all(k in done for k in ['G00','G10','G01','G11']) else 'PENDING','R3':'COMPLETED' if all(k in done for k in ['O_color','O_cov','O_color_ordinary','O_cov_ordinary']) else 'PENDING','R4':'COMPLETED_SIX_PROBES' if len(probes)==6 else 'CONDITIONAL_NOT_RUN','R5':'CONDITIONAL_NOT_RUN','test_state':'TEST_CLOSED','formal_GO':False,'gates':gates,'inputs_unchanged':unchanged,'source_freeze_sha256':sha(ART/'SOURCE_FREEZE.json'),'checkpoint_source_sha256':sha(CHECKPOINT),'independent_verification_required':True})
    return done
