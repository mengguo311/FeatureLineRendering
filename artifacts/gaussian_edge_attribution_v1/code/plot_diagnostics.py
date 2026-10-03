"""Two fixed descriptive figures from sealed real metrics; no fitting/selection."""
from pathlib import Path
import argparse,hashlib,json,os
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'artifacts/gaussian_edge_attribution_v1'
os.environ['MPLCONFIGDIR']=str(ROOT/'out/gaussian_edge_attribution_v1/matplotlib_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write_json(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.partial');tmp.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def valid_json(path,expected):
    if sha(path)!=expected:raise ValueError('Sealed input changed: '+str(path))
    return json.loads(path.read_text())
def load_scene(scene,cfg):
    base=ROOT/'out/gaussian_edge_attribution_v1'/scene;ap=base/'assets/ASSET_SEAL.json';aseal=json.loads(ap.read_text());asealhash=sha(ap)
    if aseal['context']['config_sha256']!=sha(ART/'code/config.json'):raise ValueError('Config differs from F asset')
    asp=base/'assets/scores.npz';selp=base/'assets/selection.npz'
    for p in (asp,selp):
        if sha(p)!=aseal['files'][p.name]:raise ValueError('Sealed scores/selection changed')
    expected=[f'F_{i:03d}' for i in cfg['fixed_frame_ids']]+[f'C_{i:03d}' for i in cfg['check_frame_ids']]+[f'arc0_{i:03d}' for i in range(33)]
    actual=sorted(p.parent.name for p in (base/'frames').glob('*/METRICS.json'))
    if sorted(expected)!=actual:raise ValueError(f'{scene}: expected exactly49 frame metrics, got{len(actual)}')
    allrows=[];sources=[]
    for key in expected:
        frame=base/'frames'/key;seal=json.loads((frame/'SEAL.json').read_text())
        if seal['context']['asset_seal_sha256']!=asealhash:raise ValueError('Frame uses different F asset')
        m=valid_json(frame/'METRICS.json',seal['files']['METRICS.json'])
        if m['key']!=key or m['scene']!=scene:raise ValueError('Frame namespace changed')
        allrows.append(m);sources.append(dict(key=key,metrics_sha256=seal['files']['METRICS.json'],frame_seal_sha256=sha(frame/'SEAL.json')))
    s=np.load(asp);selection=np.load(selp)
    scores={k:s[k] for k in ('original_ids','raw_denominator','enhanced_union','eligible','unknown','unreliable')}
    thresholds={str(p):(float(np.min(scores['enhanced_union'][selection[f'enhanced_union_{p:02d}']])) if len(selection[f'enhanced_union_{p:02d}']) else None) for p in cfg['tiers_percent']}
    return dict(scene=scene,allrows=allrows,C=[r for r in allrows if r['key'].startswith('C_')],scores=scores,thresholds=thresholds,sources=sources,score_sha256=aseal['files']['scores.npz'],asset_seal_sha256=asealhash)

def summary(scene,cfg):
    rows=scene['C'];s=scene['scores'];out=dict(scene=scene['scene'],frames_actual=len(scene['allrows']),frames_requested=49,C_count=len(rows),C_keys=[r['key'] for r in rows],gaussians=len(s['original_ids']),eligible=int(s['eligible'].sum()),unknown=int(s['unknown'].sum()),unreliable=int(s['unreliable'].sum()),tiers={},continuous={},visible_reference_mean=float(np.mean([r['visible_reference'] for r in rows])),visible_reference_min=float(min(r['visible_reference'] for r in rows)),visible_reference_max=float(max(r['visible_reference'] for r in rows)))
    for p in cfg['tiers_percent']:
        tag=f'{p:02d}';arms={}
        for arm in ('selected','baseline','random','single','null'):
            rr=[r['fields'][f'{arm}_Q_{tag}'] for r in rows]
            worst=int(np.argmin([r['lift'] for r in rr]));arms[arm]={k:float(np.mean([r[k] for r in rr])) for k in ('lift','mass','concentration','soft_alignment')}
            arms[arm].update(worst_C=rows[worst]['key'],worst_lift=rr[worst]['lift'],area_foreground_gt0p1_mean=float(np.mean([r['area_foreground']['0.1'] for r in rr])))
        delta={a:[r['fields'][f'selected_Q_{tag}']['lift']-r['fields'][f'{a}_Q_{tag}']['lift'] for r in rows] for a in ('baseline','random','single','null')}
        out['tiers'][str(p)]=dict(arms=arms,selected_lift_difference={a:dict(mean=float(np.mean(v)),min=float(min(v)),max=float(max(v)),strictly_positive_views=int(np.sum(np.asarray(v)>0))) for a,v in delta.items()})
    for arm in ('baseline_P','two_sided_P','single_P','null_P'):
        if arm in rows[0]['fields']:out['continuous'][arm]={k:float(np.mean([r['fields'][arm][k] for r in rows])) for k in ('lift','mass','concentration','soft_alignment')}
    audit=[r['top4_audit'] for r in rows]
    out['C_cached_all_mass_fraction']=sum(r['cached_mass'] for r in audit)/sum(r['alpha_mass'] for r in audit)
    out['C_cached_selected10_mass_fraction']=sum(r['selected_top10_cached_mass'] for r in audit)/sum(r['selected_top10_full_mass'] for r in audit)
    return out

def figures(data,cfg,out):
    plt.rcParams.update({'font.family':'Noto Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white','figure.facecolor':'white'})
    tiers=cfg['tiers_percent'];armstyle={'selected':('#c23b22','-','Two-sided'),'baseline':('#225ea8','-','Contribution-only'),'random':('#5b8f55','--','Visibility-matched random'),'single':('#865ea8',':','Single F'),'null':('#777777','-.','Shifted-evidence null')}
    fig,axes=plt.subplots(2,4,figsize=(16,7.3),sharex=True,sharey='row',layout='constrained')
    for i,scene in enumerate(data):
        labels=[r['key'][2:] for r in scene['C']];x=np.arange(len(labels))
        for j,p in enumerate(tiers):
            ax=axes[i,j]
            for arm,(color,ls,label) in armstyle.items():
                ax.plot(x,[r['fields'][f'{arm}_Q_{p:02d}']['lift'] for r in scene['C']],color=color,linestyle=ls,marker='o',markersize=3,linewidth=1.5,label=label)
            ax.axhline(1,color='#444444',lw=.8);ax.grid(alpha=.2);ax.set_xticks(x,labels,rotation=45);ax.set_title(f"{scene['scene'].capitalize()} | top {p}% eligible")
            if j==0:ax.set_ylabel('Lift over full-alpha reference')
            if i==1:ax.set_xlabel('Unused C view (GS training view)')
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=5,frameon=False)
    fig.suptitle('Fixed Gaussian groups: all eight C views and all four predefined tiers\nFull original-transmittance projection; independent 2 px evidence tolerance',fontsize=14)
    for suffix in ('png','pdf'):fig.savefig(out/f'C_lift_all_tiers.{suffix}',dpi=150)
    plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(15.3,8.3),layout='constrained')
    tiercolors=['#253494','#2c7fb8','#41b6c4','#c23b22']
    for i,scene in enumerate(data):
        rows=scene['C'];labels=[r['key'][2:] for r in rows];x=np.arange(len(rows));ax=axes[i,0]
        for p,col in zip(tiers,tiercolors):ax.plot(x,[r['fields'][f'selected_Q_{p:02d}']['mass'] for r in rows],marker='o',markersize=3,color=col,label=f'Top {p}%')
        ax.set_yscale('log');ax.set_ylabel('Projected group mass (sum of raw alpha*T)');ax.set_xticks(x,labels,rotation=45);ax.set_title(scene['scene'].capitalize()+' | native mass');ax.legend(ncol=2,fontsize=8);ax.grid(alpha=.2)
        ax=axes[i,1]
        allcov=[r['top4_audit']['coverage'] for r in rows];groupcov=[r['top4_audit']['selected_top10_cached_mass']/r['top4_audit']['selected_top10_full_mass'] for r in rows];ref=[r['visible_reference'] for r in rows]
        ax.plot(x,allcov,'o-',color='#225ea8',label='Top4 / all alpha mass');ax.plot(x,groupcov,'s-',color='#c23b22',label='Top4 / full selected-10% mass');ax.plot(x,ref,'^--',color='#777777',label='Evidence tolerance / alpha mass');ax.set_ylim(0,1.03);ax.set_xticks(x,labels,rotation=45);ax.set_ylabel('Mass fraction');ax.set_title('Truncation and tolerance saturation');ax.legend(fontsize=8);ax.grid(alpha=.2)
        ax=axes[i,2];s=scene['scores'];eligible=s['eligible'];xx=np.log10(s['raw_denominator'][eligible]);yy=s['enhanced_union'][eligible]
        if len(xx):
            im=ax.hist2d(xx,yy,bins=(60,50),norm=LogNorm(),cmap='cividis');fig.colorbar(im[3],ax=ax,label='Eligible original-ID count',shrink=.8)
        else:ax.text(.5,.5,'No reliable eligible IDs',transform=ax.transAxes,ha='center')
        for p,col in zip(tiers,tiercolors):
            if scene['thresholds'][str(p)] is not None:ax.axhline(scene['thresholds'][str(p)],color=col,lw=.8,linestyle='--',alpha=.9)
        ax.set_xlabel('log10 cumulative F raw visibility mass');ax.set_ylabel('Two-sided union score');ax.set_title(f"F asset: {int(eligible.sum()):,} eligible IDs\nNever observed in top4: {s['unknown'].mean():.1%}")
        if i==1:
            axes[i,0].set_xlabel('Unused C view');axes[i,1].set_xlabel('Unused C view')
    fig.suptitle('Visibility, density and score diagnostics; frozen assets, no pixel-based C selection\nDashed score levels: predefined 1/3/10/30% tiers. High concentration is not geometric accuracy.',fontsize=13)
    for suffix in ('png','pdf'):fig.savefig(out/f'visibility_mass_score_diagnostics.{suffix}',dpi=150)
    plt.close(fig)

def review(summaries,path):
    lines=['# 量化结果的独立解读','', '本文件只汇总两个已封存场景的真实指标，不改变配置、分数、ID、阈值或展示档位。文中 top% 均以各场景 F 合格 Gaussian 集合为分母，非模型全量比例。所有 C 相机都曾用于原 Gaussian 模型训练；这里的“未使用”只表示没有参与此次 F 归因拟合，不是盲测或几何真值评估。','', '| 场景 | 实际/请求姿态 | C 容差区 alpha 质量均值 | top10% two-sided lift | baseline lift | random lift | single-F lift | null lift |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        a=s['tiers']['10']['arms'];lines.append(f"| {s['scene']} | {s['frames_actual']}/{s['frames_requested']} | {s['visible_reference_mean']:.2%} | {a['selected']['lift']:.5f} | {a['baseline']['lift']:.5f} | {a['random']['lift']:.5f} | {a['single']['lift']:.5f} | {a['null']['lift']:.5f} |")
    lines+=['','以上 lift 为八 C 的逐视图比率算术均值。分子是属性/组贡献落在独立证据两像素膨胀区的质量比例，分母是完整 alpha 落在同一区域的比例。因此 concentration≈0.99 不是“99% 精度”：当容差区已覆盖大部分对象质量时，随机组也可有很高 concentration，lift 上限接近 1/可见参考比例。soft alignment、面积、质量、最差视图和随机/null 对照必须共同看。','']
    lines += ['固定移位 null 在两个场景的 top10% 平均 lift 也高于 1。这说明可见性、对象支持区域和图像结构本身即可产生部分富集；仅凭 lift>1 不能确认特定几何边缘身份。主选择优于随机或 null 仍需与 baseline 的增益、所有档位以及未观测比例一起解释。', '']
    for s in summaries:
        name=s['scene'];t=s['tiers']['10'];a=t['arms'];delta=t['selected_lift_difference'];cb=s['continuous']['baseline_P'];ce=s['continuous']['two_sided_P']
        lines += [f"## {name}",'',f"固定 top10% two-sided 在 {delta['random']['strictly_positive_views']}/8 个 C 上超过可见性匹配随机组；相对随机的 lift 差均值 {delta['random']['mean']:+.5f}。相对 contribution-only baseline 的差均值只有 {delta['baseline']['mean']:+.5f}，逐视图范围 [{delta['baseline']['min']:+.5f}, {delta['baseline']['max']:+.5f}]，胜出 {delta['baseline']['strictly_positive_views']}/8；不能将随机对照优势直接写成两侧方法相对 baseline 的全面改进。",'',f"连续分数主投影（不合格 ID 按冻结规则置零弃权，原始估计仍保留）的 mean lift：baseline {cb['lift']:.5f}，two-sided {ce['lift']:.5f}，差 {ce['lift']-cb['lift']:+.5f}。弃权零值不是负标签。连续分数结果与离散 top10% 组是不同问题；不得只选有利档位。全部 1/3/10/30% 与每个 C 都在 `C_lift_all_tiers.png` 中列出。",'',f"top10% two-sided 最低 lift 视图为 {a['selected']['worst_C']}（{a['selected']['worst_lift']:.5f}）；C 平均投影质量 {a['selected']['mass']:.2f}，前景中 Q>0.1 的平均面积比例 {a['selected']['area_foreground_gt0p1_mean']:.2%}。整 Gaussian 组的宽支持区是归因足迹，不以线细度或低入选数量判成败。",'',f"C 中 top4 对完整 alpha 的质量覆盖 {s['C_cached_all_mass_fraction']:.2%}；对固定 top10% 组选中质量的覆盖 {s['C_cached_selected10_mass_fraction']:.2%}。主图使用完整模型原始透射率投影，可避免这部分投影遗漏，但分数仍由 top4 截断 F 贡献估计，完整归因不因此成立。",'']
    lines += ['两个场景使用同一参数与 Mic F 归一化。Materials 是受限 SH0 配方下的平滑/反射场景压力例，不能据此声称恢复了完整视角依赖反射或真实几何边界。当前量化支持的是冻结 Gaussian 群对独立渲染证据的富集程度；未证明曲线位置、表面法向、几何边缘身份或时间稳定性的优越性。','', '图中的质量匹配不改变固定 ID：统一标量缩放会改变亮度/质量，但不改变 concentration 或 lift。本审阅不把缩放后的浓度相同当作额外独立证据。两张图均由全部既定 C 和完整 F 资产计算，没有选择“最佳视图”、调整 tolerance 或额外扫参。']
    path.write_text('\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ART/'research/diagnostic_figures');args=ap.parse_args();out=args.output.resolve()
    if ROOT not in out.parents:raise ValueError('Output outside authorized workspace')
    cfg=json.loads((ART/'code/config.json').read_text());data=[load_scene(scene,cfg) for scene in ('mic','materials')];out.mkdir(parents=True,exist_ok=True)
    sums=[summary(s,cfg) for s in data];figures(data,cfg,out);review(sums,ART/'research/METRIC_REVIEW_ZH.md')
    write_json(out/'DIAGNOSTIC_DATA.json',dict(summary=sums,C_metrics={s['scene']:s['C'] for s in data}))
    inputs={s['scene']:dict(asset_seal_sha256=s['asset_seal_sha256'],scores_sha256=s['score_sha256'],frames=s['sources']) for s in data}
    files=[*out.glob('*.png'),*out.glob('*.pdf'),out/'DIAGNOSTIC_DATA.json',ART/'research/METRIC_REVIEW_ZH.md']
    write_json(out/'FIGURE_MANIFEST.json',dict(script_sha256=sha(__file__),config_sha256=sha(ART/'code/config.json'),inputs=inputs,artifacts=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in files],scope='Descriptive only; fixed 2 scenes x49 frames validated; figures use8 C per scene and sealed F scores; no fits/selections/parameter changes.'))
    print(json.dumps(sums,indent=2),flush=True)
if __name__=='__main__':main()
