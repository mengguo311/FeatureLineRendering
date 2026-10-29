from runtime import *
from PIL import Image,ImageDraw
import subprocess,html

def diagnostics(scene):
    root=OUT/scene;a=load_np(root/'ORIGINAL/gaussians.npz');s=load_np(BASE/'arms/C/scenes'/scene/'full/SHARED_CONTROL_AND_SAMPLING.npz')
    ld=load_np(root/'DIRECT/ledger.npz');lh=load_np(root/'HOUGH/ledger.npz');n=len(a['means'])
    labels={'PROTECTED_CORNER':1,'SHORT_OR_DEGENERATE':2,'CURVED_DIRECT_FITTER':3,'HOUGH_SUPPORTED':4,'AMBIGUOUS_DIRECT_FALLBACK':5}
    rows=[json.loads(line) for line in (root/'WINDOWS.jsonl').read_text().splitlines()]
    perwindow=np.zeros(len(rows),np.uint8);selected=[]
    cam=json.loads((OUT/'CAMERAS.json').read_text())[scene][0];E=np.asarray(cam['extrinsic'])
    for r in rows:
        if r.get('status')=='protected_corner_piece':label=1
        elif 'status' in r:label=2
        elif not r['near_straight']:label=3
        elif r['hough']['ambiguous']:label=5
        else:label=4
        perwindow[r['window_id']]=label
    status=perwindow[lh['window_id']]
    np.savez_compressed(root/'PROCESSING_LEDGER.npz',line_kernel_id=np.arange(n,dtype=np.int64),parent_id=a['primitive_id'],piece_id=a['internal_piece_id'],window_id=lh['window_id'],
        processed=lh['processed'],direct_modified=ld['modified'],hough_modified=lh['modified'],direct_retained=ld['retained'],hough_retained=lh['retained'],
        direct_reason=ld['reason'],hough_reason=lh['reason'],hough_proposal_status=status,ambiguous=status==5,hough_support=lh['hough_support'],hough_group_id=lh['hough_group_id'],
        confidence_known=np.zeros(n,bool),source_GS_known=np.zeros(n,bool))
    js(root/'PROCESSING_LEDGER_SCHEMA.json',dict(proposal_labels=labels,reasons='LEDGER_REASONS.json',physical_group_purity='UNKNOWN; no ground-truth identities',
         no_cross_parent_associations_added=True,all_samples_accounted_for=bool(lh['processed'].all()),proposal_status_counts={k:int((status==v).sum()) for k,v in labels.items()}))
    direct=load_np(root/'DIRECT/gaussians.npz');hough=load_np(root/'HOUGH/gaussians.npz');p=s['pixel']
    dd=np.linalg.norm(direct['means']-a['means'],axis=1)/p;dh=np.linalg.norm(hough['means']-a['means'],axis=1)/p;hd=np.linalg.norm(hough['means']-direct['means'],axis=1)/p
    np.savez_compressed(root/'GEOMETRY_DELTA.npz',line_kernel_id=np.arange(n,dtype=np.int64),direct_displacement_pixel=dd,hough_displacement_pixel=dh,hough_minus_direct_distance_pixel=hd)
    numerical=dict(hough_vs_direct_over_001_pixel=int((hd>.001).sum()),hough_vs_direct_over_005_pixel=int((hd>.05).sum()),
        direct_displacement_quantiles=np.quantile(dd,[0,.5,.9,.95,.99,1]).tolist(),hough_displacement_quantiles=np.quantile(dh,[0,.5,.9,.95,.99,1]).tolist(),
        hough_vs_direct_distance_quantiles=np.quantile(hd,[0,.5,.9,.95,.99,1]).tolist())
    js(root/'DELTA_METRICS.json',numerical)
    # Diagnostic crops are selected by original geometry and first rejected window ID,
    # never by visual improvement. They do not change fit scope or cameras.
    seen=set()
    for r in rows:
        if 'HOUGH' not in r or r['HOUGH']['accepted']:continue
        why=r['HOUGH']['reason']
        if why in seen:continue
        lo=int(np.searchsorted(a['internal_piece_id'],r['piece_start']));hi=int(np.searchsorted(a['internal_piece_id'],r['piece_stop']))
        center=a['means'][lo:hi].mean(0);q=E[:3,:3]@center+E[:3,3]
        if q[2]<=.2:continue
        u=cam['fx']*q[0]/q[2]+cam['cx'];v=cam['fy']*q[1]/q[2]+cam['cy']
        if not (0<=u<cam['width'] and 0<=v<cam['height']):continue
        left=int(np.clip(round(u)-64,0,cam['width']-128));top=int(np.clip(round(v)-64,0,cam['height']-128))
        selected.append(dict(window_id=r['window_id'],reason=why,crop=[left,top,left+128,top+128],view=cam['view']));seen.add(why)
        if len(selected)>=4:break
    if selected:
        board=Image.new('RGB',(3*256,len(selected)*286+54),'white');draw=ImageDraw.Draw(board)
        draw.text((8,8),f'{scene} | Rejected Hough fits: original support retained',fill='black')
        draw.text((8,28),'Diagnostic crops only; complete assets were fitted and rendered',fill='black')
        for row,r in enumerate(selected):
            for col,name in enumerate(('ORIGINAL','DIRECT','HOUGH')):
                im=Image.open(root/'figures'/f'{cam["view"]}_{name}.png').crop(tuple(r['crop'])).resize((256,256),Image.Resampling.NEAREST)
                x=col*256;y=54+row*286;draw.text((x+5,y),f'{name} | W{r["window_id"]} {r["reason"]}',fill='black');board.paste(im,(x,y+25))
        board.save(root/'figures/REJECTED_FITS_DIAGNOSTIC.png')
    js(root/'FAILURE_SELECTION.json',dict(rule='First visible rejected window per reason in original order; same original camera',selected=selected))
    prov=root/'provenance';prov.mkdir(exist_ok=True);inp=BASE/'arms/C/scenes'/scene/'full'
    files={}
    for f in ('parents.json','ASSOCIATIONS.json','OBSERVATION_TO_PARENT.npz','OBSERVATIONS.npz','SHARED_CONTROL_AND_SAMPLING.npz','LENGTH_AND_PARENT.npz'):
        target=prov/f;shutil.copyfile(inp/f,target);assert sha(target)==sha(inp/f);files[f]=sha(target)
    js(prov/'README.json',dict(role='Unmodified original provenance, not refined curve controls. Use each arm curves.npz for refined geometry.',files=files))
    return numerical

def main():
    check_budget(15)
    status=json.loads((OUT/'STATUS.json').read_text());scenes=status['scenes'];summary={};parts=[]
    report=['# 完整专用线高斯资产：局部 Hough 与分段三次曲线试验','',
      '已对完成场景保留全部线核并生成真实几何改动、完整 NPZ/PLY/曲线文件及纯线渲染。没有读取源 GS，没有 RGB 合成，没有新增缺口连接。',
      '', '全图视觉变化有限，Hough 与同拟合器的直接基线非常接近，**没有证据证明 Hough 明显更优**。修改数量不是视觉改善或物理准确性的证明。',
      '', '|场景|状态|线核总数|DIRECT 修改|HOUGH 修改|HOUGH 三次段|最大位移/p|', '|---|---|---:|---:|---:|---:|---:|']
    for scene,st in scenes.items():
        if st!='COMPLETE':summary[scene]=dict(status=st);report.append(f'|{scene}|{st}|—|—|—|—|—|');continue
        numerical=diagnostics(scene);root=OUT/scene
        metrics={name:json.loads((root/name/'METRICS.json').read_text()) for name in ('ORIGINAL','DIRECT','HOUGH')}
        d=metrics['DIRECT'];h=metrics['HOUGH'];renders=json.loads((root/'RENDER_METRICS.json').read_text())
        summary[scene]=dict(status='COMPLETE',metrics=metrics,numerical=numerical,render_metrics=renders,
            artifacts={name:{f:str(root/name/f) for f in ('gaussians.npz','gaussians.ply','curves.npz','ledger.npz','RELOAD_VERIFY.json')} for name in metrics},
            figures=[str(root/'figures'/f'{v}_COMPARISON.png') for v in CFG['views'][scene]],missing_items=[])
        report.append(f'|{scene}|COMPLETE|{h["kernel_count"]}|{d["modified_kernels"]}|{h["modified_kernels"]}|{h["cubic_segments"]}|{h["maximum_displacement_pixel"]:.6f}|')
        sections=[f'## {scene}',f'全量核账本：[PROCESSING_LEDGER.npz]({scene}/PROCESSING_LEDGER.npz)。实际 Hough 点×方向票数 {h["point_direction_votes"]}，有效局部组 {h["hough_valid_groups"]}，支持核 {h["hough_support_kernels"]}。',
          f'DIRECT 实际拟合调用 {d["actual_fitter_calls"]}；HOUGH 新轴拟合调用 {h["actual_fitter_calls"]}，另有 {h["reused_direct_windows"]} 个窗直接复用共同拟合结果；每次均为3轮IRLS。每个窗完整记录于 [WINDOWS.jsonl]({scene}/WINDOWS.jsonl)。',
          f'Hough 与直接拟合位置差超过 0.001p 的核：{numerical["hough_vs_direct_over_001_pixel"]}；超过 0.05p：{numerical["hough_vs_direct_over_005_pixel"]}。']
        rr=[metrics[name]['roughness']['rms_adjacent_angle_deg'] for name in metrics]
        sections.append(f'相邻核方向 RMS 角度 ORIGINAL/DIRECT/HOUGH：{rr[0]:.8f}/{rr[1]:.8f}/{rr[2]:.8f} 度；仅为平滑度诊断，不能据此判断形状正确性。')
        sections.append('|输出|NPZ|PLY|显式曲线|\n|---|---|---|---|')
        for name in metrics:sections.append(f'|{name}|[下载]({scene}/{name}/gaussians.npz)|[下载]({scene}/{name}/gaussians.ply)|[下载]({scene}/{name}/curves.npz)|')
        for v in CFG['views'][scene]:sections.append(f'![{scene} {v}: ORIGINAL / DIRECT / HOUGH]({scene}/figures/{v}_COMPARISON.png)')
        if (root/'figures/REJECTED_FITS_DIAGNOSTIC.png').exists():sections.append(f'![Rejected fits retained unchanged]({scene}/figures/REJECTED_FITS_DIAGNOSTIC.png)')
        parts.extend(sections+[''])
    report+=['','## 冻结方法与验证','',
      '8片短窗，局部9+9方向Hough，偏移格0.5p/0.25p；同一固定端点与切向的双手柄三次拟合器、3轮Huber IRLS。位移≤0.75p、核切向旋转≤15°、长度比0.95–1.05；35°角点及邻片保护。曲窗保形门槛与33个离散支持管检查见 config.json。p来自原资产pixel字段，不能解释为校准的不确定性。',
      '所有原始parent、piece和样本ID保留；不合并不同parent；未知物理组纯度、置信度及源GS关联均明确UNKNOWN。平滑窗之间使用共同端切向；与拒绝后恢复的原折线相接处只保证原端点连续，未宣称全局C1。',
      '四个小型检查先RED（未实现功能），实现后GREEN；真实保存文件在独立进程重载，逐字段验证计数、颜色、opacity、尺度、ID不变，保留核原样，协方差特征值不变，显式曲线重建核位置及原始支持端点一致。',
      '相机固定：scan24/scan65 0012、0036；ficus test_r_1、test_r_79。白背景、原分辨率、相同CPU EWA渲染参数。显示的是完整专用线资产，没有源表面遮挡；不使用全模型图像或输入RGB作拟合目标。',
      '源输入及成熟渲染代码在执行前后哈希检查；INPUT_LOCK中的三个源GS模型明确排除且未读取。原始控制、观察及关联文件另存provenance，仅用于追溯，不冒充新的三次曲线控制。',
      '', '## 限制与执行记录','',
      '多数未通过角度/保形门槛的窗完整保留；原有杂线和缺口也保留。没有通过删除、加粗或提高不透明度制造视觉改善。支持管只在所有原采样点及33个固定位置检查，并非连续几何证明。此试验不是一般曲线Hough、H4、缺口验证或held-out泛化试验。',
      'ficus 和 scan65 几何外层退出143，包装器未取得子进程退出码；子进程都写出了完整几何完成回执，其中scan65在包装器中断后继续完成。两个原始异常未抹除，不算科学失败，也不记作干净子进程退出。随后独立重载/渲染进程退出0并验证全部保存资产，无第二次科学拟合。详见 logs/ficus_geometry_outer_exit.json、logs/scan65_geometry_outer_exit.json。',
      '未完成场景及缺失项以 RESULT.json 为准；本次不追加参数搜索。','']+parts
    (OUT/'REPORT_ZH.md').write_text('\n\n'.join(report))
    snapshot=OUT/'code_snapshot';snapshot.mkdir(exist_ok=True);sources={}
    for p in sorted(CODE.iterdir()):
        if p.is_file() and p.suffix in ('.py','.json','.md'):
            shutil.copyfile(p,snapshot/p.name);sources[p.name]=sha(p);assert sha(snapshot/p.name)==sources[p.name]
    js(OUT/'SOURCE_HASHES.json',sources)
    commit=subprocess.check_output(['git','-C',str(CODE),'rev-parse','HEAD']).decode().strip()
    elapsed=time.time()-datetime.datetime.fromisoformat(START).timestamp()
    result=dict(status='COMPLETE' if all(v=='COMPLETE' for v in scenes.values()) else 'PARTIAL',scenes=summary,
        source_commit=commit,elapsed_seconds_including_implementation=elapsed,deadline_utc=CFG['deadline_utc'],
        no_source_GS_read=True,all_original_kernels_retained=True,hough_advantage='NOT_ESTABLISHED',
        new_gap_confirmation=False,physical_accuracy='UNKNOWN',administrative_outer_143_preserved=True,
        scientific_fit_attempts_per_scene=1,missing_items=[s for s,v in scenes.items() if v!='COMPLETE'],
        source_hashes='SOURCE_HASHES.json',input_hashes_before='INPUT_HASHES_before.json',input_hashes_after='INPUT_HASHES_after.json',
        tests_red='logs/correctness_red.json',tests_green='logs/correctness_green.json',report='REPORT_ZH.md')
    js(OUT/'RESULT.json',result)
    cards=[]
    for scene,r in summary.items():
        if r['status']!='COMPLETE':continue
        links=' '.join(f'<a href="{scene}/HOUGH/{f}">{f}</a>' for f in ('gaussians.npz','gaussians.ply','curves.npz'))
        cards.append(f'<h2>{scene}</h2><p>{links}</p>'+''.join(f'<img style="width:100%" src="{scene}/figures/{v}_COMPARISON.png">' for v in CFG['views'][scene]))
    (OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Complete line assets</title><body style="font:16px sans-serif;max-width:1800px;margin:24px auto"><h1>完整专用线资产：ORIGINAL / DIRECT / HOUGH</h1><p>真实几何改动；全量核保留。Hough 优势未得到证明。无源 GS 或 RGB 合成。</p><a href="REPORT_ZH.md">中文报告</a>'+''.join(cards)+'</body>')
    files={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name not in ('MANIFEST.json','STATUS.json') and '/logs/' not in str(p)}
    js(OUT/'MANIFEST.json',dict(files=files,output_bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())))
    assert sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())<8*2**30
    state('PILOT_FINISHED',scenes=scenes,result=str(OUT/'RESULT.json'),no_further_scientific_runs=True,elapsed_seconds=elapsed)
    print('FINAL_RESULT',json.dumps({s:r['status'] for s,r in summary.items()}),flush=True)
if __name__=='__main__':main()
