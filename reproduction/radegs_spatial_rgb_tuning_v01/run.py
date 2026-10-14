import argparse,json,time,traceback,os,resource
import numpy as np
from scipy.ndimage import label,convolve
from common import *
from detector import *
from render_boards import save_png,board

def metrics(r):
    m=r['marked'];s=r['skeleton'];lab,n=label(m,np.ones((3,3),np.uint8));slab,sn=label(s,np.ones((3,3),np.uint8))
    deg=convolve(s.astype(np.int16),np.ones((3,3),np.int16),mode='constant')-s
    sizes=np.bincount(lab.ravel())[1:]
    return dict(marked_pixels=int(m.sum()),marked_fraction=float(m.mean()),skeleton_pixels=int(s.sum()),components_8=int(n),skeleton_components_8=int(sn),skeleton_endpoints_degree1=int(np.sum(s&(deg==1))),skeleton_junction_pixels_degree_ge3=int(np.sum(s&(deg>=3))),isolated_skeleton_pixels=int(np.sum(s&(deg==0))),component_size_median=float(np.median(sizes)) if len(sizes) else 0,mean_candidate_darkness=float(r['candidate_darkness'].mean()))

def title(p):
    return f"{p['id']} | T={p['threshold']:.2f} | detail={p['detail_lambda']:.2f}\nscales={SCALES[p['analysis']]}"

def process(entry,ps):
    started=time.time();scene=entry['scene'];view=entry['view'];root=T/'scenes'/scene/view
    root.mkdir(parents=True,exist_ok=True)
    assert sha(entry['path'])==entry['sha256']
    with np.load(entry['path']) as z:rgb=rgb_from_npz(z)
    save_png(root/'RGB.png',rgb)
    fields={};timings={}
    for kind in SCALES:
        start=time.time();f=analyze_rgb(rgb,kind);timings[kind]=time.time()-start
        fields[kind]={k:f[k] for k in ['detail','structural','union','normal','confidence','magnitude','profile_confidence','width_map','classmap']}
        np.savez_compressed(root/f'fields_{kind}.npz',**fields[kind])
        write(root/f'analysis_{kind}.json',dict(config={**boundary.DEFAULT,'scales':SCALES[kind]},seconds=timings[kind],profile_count=len(f['profiles']['xy']),profile_accepted=int(f['profiles']['valid'].sum())))
    f=fields['native'];np.testing.assert_array_equal(mix_fields(f,1),f['union'])
    old=B/'depth_guided_native_dtu_v01'/'scenes'/scene/'detector'/f'{view}.npz'
    equality=None
    if old.exists():
        with np.load(old) as z:
            np.testing.assert_array_equal(f['union'],z['union']);equality='bitexact DEFAULT union vs previous05 cache'
    results={};stats=[]
    for p in ps:
        r=candidate(mix_fields(fields[p['analysis']],p['detail_lambda']),p['threshold'])
        pr=root/'presets'/p['id'];pr.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(pr/'maps.npz',**r)
        write(pr/'recipe.json',dict(**p,analysis_config={**boundary.DEFAULT,'scales':SCALES[p['analysis']]},input_sha256=entry['sha256'],boundary_sha256=sha(C/'boundary.py'),candidate_rule='darkness > threshold; skeletonize(marked)',display='1 - darkness*marked; no second blur; no adaptive contrast'))
        save_png(pr/'candidate.png',1-r['candidate_darkness']);save_png(pr/'marked.png',1-r['marked'].astype(np.float32));save_png(pr/'skeleton.png',1-r['skeleton'].astype(np.float32))
        stat=dict(scene=scene,view=view,preset=p['id'],**metrics(r));stats.append(stat)
        write(pr/'metrics.json',stat);results[p['id']]=r
    original=boundary.ink(f['union']);detail=boundary.ink(f['detail']);structure=boundary.ink(f['structural'])
    save_png(root/'DEFAULT_soft.png',original);save_png(root/'DETAIL_only.png',detail);save_png(root/'STRUCTURAL_only.png',structure)
    base=results['A20'];foot=f'{scene}/{view} | {entry["split"]} | RGB-only; no depth, alpha or semantic masks'
    board(root/'DIAGNOSTICS.jpg',[
        ('Original rendered RGB',rgb),('DEFAULT soft ink\nNo candidate threshold applied',original),('DETAIL-only soft\nNot ground-truth noise',detail),('STRUCTURAL-only soft\nNot guaranteed complete structure',structure),('A20 binary candidates\nStrict darkness > 0.20',1-base['marked'].astype(float)),('A20 skeleton\nDerived from exact binary candidates',1-base['skeleton'].astype(float))],f'{scene} {view} | Branch diagnostics',foot)
    families={'THRESHOLD':['A10','A15','A20','A30','A40','A50'],'MIX':['A20','B75','B50','B25','B00','M50T30'],'SCALE':['A20','C1U20','C1L50','C2U20','C2L50','M75T30']}
    lookup={p['id']:p for p in ps}
    for name,ids in families.items():board(root/f'{name}.jpg',[(title(lookup[id]),1-results[id]['candidate_darkness']) for id in ids],f'{scene} {view} | {name} candidate series',foot)
    summary=dict(scene=scene,view=view,input=entry,statistics=stats,analyze_seconds=timings,total_seconds=time.time()-started,default_cache_equality=equality,complete_presets=len(ps),peak_rss_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    write(root/'COMPLETE.json',summary);return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['pilot','rest'],required=True);args=ap.parse_args()
    entries=json.loads((T/'REGISTRY.json').read_text())['views'];ps=json.loads((T/'PRESETS.json').read_text())['presets']
    pilot=lambda e:e['view'] in ['0000','train_r_80']
    entries=[e for e in entries if pilot(e)==(args.stage=='pilot')]
    status('RUNNING_'+args.stage.upper(),children=[os.getpid()])
    start=time.time()
    try:
        for e in entries:
            target=T/'scenes'/e['scene']/e['view']/'COMPLETE.json'
            if target.exists():raise RuntimeError('Refuse overwrite completed unit: '+str(target))
            d=process(e,ps);print(e['scene'],e['view'],d['total_seconds'],'seconds',flush=True)
            completed=list((T/'scenes').glob('*/*/COMPLETE.json'))
            status('RUNNING_'+args.stage.upper(),children=[os.getpid()],completed_views=len(completed),completed_units=sum(json.loads(p.read_text())['complete_presets'] for p in completed),last_event=f'{e["scene"]}/{e["view"]} completed')
        write(T/'logs'/f'{args.stage}_EXIT.json',dict(exit_code=0,seconds=time.time()-start,utc=utc(),pid=os.getpid()))
        status(args.stage.upper()+'_RENDERED',children=[],next_action='Visual inspection required')
    except BaseException:
        write(T/'logs'/f'{args.stage}_EXIT.json',dict(exit_code=1,traceback=traceback.format_exc(),utc=utc(),pid=os.getpid()))
        status('ENGINEERING_NOT_READY',children=[],last_event=traceback.format_exc());raise
if __name__=='__main__':main()
