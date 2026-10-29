"""Read completed levels only; produce audits and honest PARTIAL delivery."""
from common import *
from core import union_intervals
import subprocess

def crop_panel(path,items,title):
    w,h=650,320;im=Image.new('RGB',(2*w,50+((len(items)+1)//2)*(h+30)),'white');d=ImageDraw.Draw(im);d.text((8,8),title,fill='black')
    for k,(label,file) in enumerate(items):
        pic=Image.open(file).convert('RGB');arr=np.asarray(pic);yy,xx=np.nonzero(arr.min(2)<253)
        if len(xx):pic=pic.crop((max(0,int(xx.min())-8),max(0,int(yy.min())-8),min(pic.width,int(xx.max())+9),min(pic.height,int(yy.max())+9)))
        scale=min(w/pic.width,h/pic.height);pic=pic.resize((max(1,int(pic.width*scale)),max(1,int(pic.height*scale))),Image.Resampling.NEAREST);x=k%2*w;y=50+k//2*(h+30);d.text((x+5,y+3),label,fill='black');im.paste(pic,(x+(w-pic.width)//2,y+28))
    im.save(path)

def main():
    out=OUT/'delivery';out.mkdir(exist_ok=False);guard();allitems=[];metrics=[];tables={}
    for lev in (0,1):
        folder=OUT/'scan24'/f'L{lev}';seal=json.loads((folder/'CHECKPOINT.json').read_text())['files']
        for f,h in seal.items():assert sha(folder/f)==h,('checkpoint hash',f)
        metrics.append(json.loads((folder/'METRICS.json').read_text()));tables[lev]=json.loads((folder/'GROUPS.json').read_text())['groups']
        for view in ('0012','0036'):allitems.append((f'scan24 L{lev} / {view} / all original kernels',folder/(view+'_FULL.png')))
        selected=json.loads((folder/'VISUAL_SELECTION.json').read_text())['groups'];items=[]
        for view in ('0012','0036'):
            for rank,g in enumerate(selected):items.append((f"L{lev} {view} ID {g['edge_id']} N={g['kernels']}",folder/f'{view}_CROSS_ISOLATED_{rank+1}.png'))
        crop_panel(out/f'L{lev}_CROSS_PARENT_CROPS.png',items,f'L{lev}: crops of native Gaussian renders; display magnification only')
    panel(out/'SCAN24_COMPLETE_LEVELS.png',allitems,'scan24: only L0 and L1 completed; L2 timed out; L3/L4 NOT_RUN')
    # Verify the entire L1 containment DAG preserves one exact predecessor curve.
    c0=dict(np.load(OUT/'scan24/L0/CARRIERS.npz'));c1=dict(np.load(OUT/'scan24/L1/CARRIERS.npz'));curves={}
    for k,cid in enumerate(c0['carrier_id']):curves[(int(cid),0)]=c0['knots'][c0['knot_offsets'][k]:c0['knot_offsets'][k+1]]
    events=json.loads((OUT/'scan24/L1/LINEAGE.json').read_text())
    for e in events:
        assert e['operation']=='containment';host=next(tuple(v) for v in e['inputs'] if v[0]==e['host']);curves[tuple(e['output'])]=curves[host]
    for k,cid in enumerate(c1['carrier_id']):assert np.array_equal(curves[(int(cid),int(c1['version'][k]))],c1['knots'][c1['knot_offsets'][k]:c1['knot_offsets'][k+1]])
    # Full original geometry is checked again from disk, separately from the producing process.
    src=dict(np.load(BASE/'scan24/full/gaussians.npz'));original_hashes={k:hashlib.sha256(v.tobytes()).hexdigest() for k,v in src.items() if k!='colors'}
    for lev in (0,1):
        cold=dict(np.load(OUT/'scan24'/f'L{lev}/DISPLAY_GAUSSIANS.npz'))
        for k,h in original_hashes.items():assert cold[k].dtype==src[k].dtype and cold[k].shape==src[k].shape and hashlib.sha256(cold[k].tobytes()).hexdigest()==h,k
    js(out/'INDEPENDENT_AUDIT.json',dict(complete_levels=[0,1],all_original_rows=458490,original_noncolor_arrays_bitexact=True,all_L1_pooling_curves_exact_predecessor_curves=True,L1_pooling_events=len(events),geometry_extension_demonstrated=False))
    # Requested source and old-output preservation checks, without opening source RGB models.
    sealed=json.loads((ORCH/'V03_SEALED_REFERENCE.json').read_text());bad=[]
    for name,h in sealed['files'].items():
        if sha(Path(sealed['root'])/name)!=h:bad.append(name)
    inherited=json.loads((ORCH/'READ_ONLY_BEFORE.json').read_text());work=CODE.parent.parent;old_bad=[]
    for name,h in inherited['files'].items():
        if sha(work/name)!=h:old_bad.append(name)
    protected=json.loads((ORCH/'PROTECTED_BEFORE.json').read_text());git_bad=[]
    for path,expected in protected.items():
        head=subprocess.check_output(['git','--no-optional-locks','-C',path,'rev-parse','HEAD'],text=True).strip();status=subprocess.check_output(['git','--no-optional-locks','-C',path,'status','--porcelain'],text=True)
        if head!=expected['head'] or status!=expected['status']:git_bad.append(path)
    js(out/'OLD_STATE_AUDIT.json',dict(v03_sealed_files=len(sealed['files']),v03_mismatches=bad,inherited_files=len(inherited['files']),inherited_mismatches=old_bad,protected_worktrees=len(protected),protected_git_mismatches=git_bad,source_RGB_models_opened=False));assert not bad and not old_bad and not git_bad
    # Real hard-case contexts and same-row lineage, only completed memberships.
    r=dict(np.load(OLD/'scan24/REPRESENTATIVES.npz'));initial=dict(np.load(OUT/'scan24/L0/MEMBERSHIP.npz'));final=dict(np.load(OUT/'scan24/L1/MEMBERSHIP.npz'));records=json.loads((OUT/'scan24/L1/CANDIDATES.json').read_text());render=helpers()['render'];cams=json.loads((OUT/'CAMERAS.json').read_text())['scan24'];nitems=[];cases=[]
    for label in ('accepted','parallel','branch','ambiguous','residual','tangent'):
        candidates=sorted((z for z in records if z['reason']==label),key=lambda z:(z['cost'],z['a'],z['b']))
        if not candidates:cases.append(dict(category=label,status='NO_CASE'));continue
        rec=candidates[0];owner=initial['carrier_id'];sources=np.unique(owner[[rec['a'],rec['b']]]);rows=np.flatnonzero(np.isin(owner,sources));cases.append(dict(category=label,record=rec,kernel_rows=rows.tolist(),context='original L0 carriers containing candidate seed IDs; not asserted physical truth'))
        for cam in cams:
            asset={k:src[k][rows] for k in ('means','covariance','opacity')};asset['colors']=colors(owner[rows]);f=out/f"CASE_{label}_{cam['view']}.png";save_image(f,render(asset,cam,(1,1,1),.0144)['rgb']);nitems.append((f"{label}: {cam['view']}; actual source kernels",f))
    js(out/'REAL_CASES.json',cases);crop_panel(out/'NEGATIVE_CASES_CROPS.png',nitems,'Real candidate contexts; smallest cost per recorded category')
    cross=[g for g in tables[1] if g['old_parent_count']>1];selected=sorted(cross,key=lambda g:(-g['kernels'],g['edge_id']))[:1];lineage_items=[]
    for g in selected:
        rows=np.flatnonzero(final['edge_id']==g['edge_id'])
        for lev,m in [(0,initial),(1,final)]:
            for cam in cams:
                asset={k:src[k][rows] for k in ('means','covariance','opacity')};asset['colors']=colors(m['edge_id'][rows]);f=out/f"LINEAGE_L{lev}_{cam['view']}.png";save_image(f,render(asset,cam,(1,1,1),.0144)['rgb']);lineage_items.append((f"same rows, final ID {g['edge_id']}, L{lev}, {cam['view']}",f))
    crop_panel(out/'POOLING_LINEAGE.png',lineage_items,'Same actual kernels; membership changes, no carrier extension')
    summary=dict(status='PARTIAL_POOLING_ONLY_NO_COMPLETED_GROWTH_LEVEL',complete_assets=['scan24 L0','scan24 L1'],incomplete={'scan24 L2':'TIMED_OUT_-15_NO_CHECKPOINT','scan24 L3':'NOT_RUN','scan24 L4':'NOT_RUN','ficus':'NOT_RUN_BUILDING_INCOMPLETE','scan65':'NOT_RUN_BUILDING_INCOMPLETE'},L0_child_exit=0,L1_child_exit=None,L1_exit_reason='UNKNOWN_SUPERVISOR_EXIT',original_driver_exit=143,recovery_L2_exit=-15,engineering_recoveries=1,parameters_tuned=False,growth_target='NOT_DEMONSTRATED',metrics=metrics,geometry_unchanged=True,physical_identity='PROVISIONAL',total_output_bytes=sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()))
    js(OUT/'SUMMARY.json',summary)
    lines=['# v04 单次渐进载体试验：PARTIAL','', '**已交付 scan24 的完整 L0 强基线与 L1 重叠池化；没有交付完成的几何增长层。** ficus、scan65 因 building 未完成五层而未运行。','', '| 层级 | 核数 | 已分配 | UNKNOWN | 主组 | 跨 parent 组 |','|---|---:|---:|---:|---:|---:|']
    for m in metrics:lines.append(f"| L{m['level']} | {m['kernels']} | {m['assigned']} | {m['UNKNOWN']} | {m['groups']} | {m['cross_parent_groups']} |")
    lines+=['','L1 新分配 10,448 个原 UNKNOWN 核，共接受 4,527 次包含式池化。独立冷读与完整合并 DAG 核验确认，每个 L1 载体逐点等于某个前驱宿主载体：这不是几何延伸。跨 parent 组数增加不能证明获得更长真实边；每组 parent 核数和去重支持长度见 GROUPS.json。','', 'L0 有 5,995 个旧组通过新载体验证；192 个旧组因转角或切向不合格保留原身份、冻结增长。所有原 UNKNOWN seedlet 重新进入候选资格，旧歧义不作为永久排除条件；无效源切向仍保留明确 UNKNOWN。','', 'L1 达到每层 30,000 次整组验证上限。记录 3,918 次平行拒绝、2 次分支拒绝、856 次歧义和 37,099 次 fit_cap；第二遍池化没有接受新合并。候选截断及近邻饱和均有统计，不能声称穷尽所有可合并支持。','', '原监督进程以 143 退出；L1 完整检查点存在，但子进程实际退出码丢失，严格记为 UNKNOWN。唯一一次工程恢复保留原源码、配置与检查点，批量化相同候选去重和投影评分，使用脱离交互连接的监督进程；未改科学参数。恢复后 L2 日志记录 14,602 次内存合并，但在池化结束、导出与封存前耗尽 scan24 的 600 秒计算预算，被监督进程终止，实际退出码 -15。它没有有效 MEMBERSHIP 或图像，不能把这些内存合并计作交付或成功。','', '原核总数、行序、位置、协方差、宽度、旋转、尺度、不透明度与所有非颜色字段通过冷载逐字节核验；图像只渲染真实原核。原 v03 封存文件、继承文件和旧工作树状态经独立只读检查。源 RGB 高斯未打开。','', '本次未证明五级渐进长边目标，也未证明真实直线与曲线的跨碎片延伸。所有身份仍是暂定几何假设；没有独立物理真值、间隙内部证据或留出泛化结论。三层增长及两份后续完整资产明确未完成，不自动开第二个科学单元。','', '[全量两层两视图](delivery/SCAN24_COMPLETE_LEVELS.png) · [L0 隔离放大](delivery/L0_CROSS_PARENT_CROPS.png) · [L1 隔离放大](delivery/L1_CROSS_PARENT_CROPS.png) · [相同核集合的池化前后](delivery/POOLING_LINEAGE.png) · [真实负例上下文](delivery/NEGATIVE_CASES_CROPS.png)','', '放大图仅裁剪并最近邻放大已保存的原生 Gaussian 图像；完整原生固定相机图像仍保留。颜色变化表示身份变化，不表示几何改变。支持长度使用原 seedlet 有限端点投影区间的并集；间隙不计作支持，不能使用旧 seedlet 长度总和冒充去重边长。']
    (OUT/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n')
    docs=CODE.parent.parent/'docs/line_kernel_edge_growth_v04';docs.mkdir(exist_ok=True);(docs/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n\n完整资产目录：'+str(OUT)+'\n')
    js(out/'FINALIZATION_EXIT.json',dict(utc=now(),complete=True,status=summary['status']));print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
