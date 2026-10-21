"""Locked source/inputs, whole-lamp sequences and media for base length unit010."""
from common import *
import argparse,shutil,subprocess,time
from datetime import datetime,timezone
from PIL import Image
from asset_cli import load_asset
from renderer import render
from run_unit002 import contact
from validate_unit004 import audit_video
U=OUT.parent/'unit_010';VIEWS=[30,120,210,300]
def cp(src,dst):
    assert not dst.exists(),dst
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
def resources():
    total=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
    root=shutil.disk_usage(WORK).free;hdd=shutil.disk_usage(U).free
    assert root>=2**30 and hdd>=10*2**30 and total<20*2**30
    return dict(task_output_bytes=total,root_free_bytes=root,hdd_free_bytes=hdd,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)
def freeze():
    files=list(sorted((WORK/'experiments/partwise_sketch_hatching_v02').glob('*.py')))
    files += [LEGACY/n for n in ('core.py','core_walk_v2.py')]
    files += [U/'PROTOCOL.json']+sorted((U/'inputs').glob('*'))
    for p in files:
        if p.is_relative_to(WORK):cp(p,U/'source_snapshot'/p.relative_to(WORK))
    write_json(U/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in files},git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),numpy_version=np.__version__))
    write_json(U/'RESOURCES_LOCK.json',resources())
def lock():
    for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
    resources()
def cold_request():
    for name in ('recipe.json','mesh.npz','retained.npz','config.json'):cp(U/'outputs/edited'/name,U/'cold_request'/name)
    write_json(U/'COLD_REQUEST.json',dict(files={p.name:sha(p) for p in (U/'cold_request').glob('*')},target_path_cache_present=False,scope='Regenerate only selected150 base paths from seed recipe+mesh+retained284, fresh process'))
def save(prefix,result,seconds):
    assert not prefix.with_suffix('.png').exists(),prefix
    prefix.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.uint8(np.rint(result['image']*255))).save(prefix.with_suffix('.png'))
    np.savez_compressed(prefix.with_suffix('.npz'),**{k:result[k] for k in ('image','hatch','contours','rings','depth','parts')})
    write_json(prefix.with_suffix('.json'),dict(camera=result['camera'],diagnostics=result['diagnostics'],render_seconds=seconds))
def draw(mesh,strokes,cfg,az,distance=4.5,selected_ids=None):
    start=time.perf_counter();r=render(mesh,strokes,cfg,azimuth=az,elevation=20,distance=distance,selected_ids=selected_ids)
    return r,time.perf_counter()-start
def layers():
    for version in ('baseline','edited'):
        _,_,mesh,paths,cfg=load_asset(U/'outputs'/version/'asset.json')
        for az in VIEWS:
            for layer in (0,1):
                ids=[s['id'] for s in paths if s['part']==3 and s['layer']==layer]
                r,seconds=draw(mesh,paths,cfg,az,selected_ids=ids)
                stem=('baseline_' if version=='baseline' else '')+f'{az:03}_layer{layer}'
                save(U/'layers'/stem,r,seconds)
                print(version,az,layer,flush=True)
def dev():
    for version in ('baseline','edited'):
        _,_,mesh,paths,cfg=load_asset(U/'outputs'/version/'asset.json')
        r,seconds=draw(mesh,paths,cfg,0);save(U/'dev'/version,r,seconds)
    contact([U/'dev'/f'{v}.png' for v in ('baseline','edited')],['Before length 0.18 | DEV az0','After length 0.12 | DEV az0'],U/'figures/dev_comparison.png',columns=2,thumb=512)
def sequence(name,start,stop):
    _,_,mesh,paths,cfg=load_asset(U/'outputs/edited/asset.json')
    for i in range(start,stop):
        az=15*i if name=='orbit' else 30
        distance=4.5 if name=='orbit' else float(4.8-.8*np.cos(2*np.pi*i/15))
        r,seconds=draw(mesh,paths,cfg,az,distance);save(U/'frames'/name/f'{i:04}',r,seconds)
        print(name,i,seconds,flush=True)
        resources()
def media():
    figs=U/'figures';figs.mkdir(exist_ok=True)
    paths=[];titles=[];bases=[];base_titles=[];parts_all=[];parts_titles=[];crops=[]
    for az in VIEWS:
        cfg=json.loads((U/'outputs/edited/config.json').read_text());camera=json.loads((U/'outputs/edited/renders'/f'{az:03}.json').read_text())['camera']
        _,labels=core.analytic_reference(cfg['asset'],camera)
        for version,title in [('baseline','Before length 0.18'),('edited','After length 0.12')]:
            src=U/'outputs'/version/'renders'/f'{az:03}.png';paths.append(src);titles.append(f'{title} | az{az}')
        for part,pname in [(1,'shade'),(2,'stem'),(3,'base')]:
            y,x=np.where(labels==part);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
            for version,title in [('baseline','Before length 0.18'),('edited','After length 0.12')]:
                src=U/'outputs'/version/'renders'/f'{az:03}.png';dst=figs/f'{version}_{az:03}_{pname}.png';big=figs/f'{version}_{az:03}_{pname}_enlarged.png'
                with Image.open(src) as im:
                    crop=im.crop(box);crop.save(dst);scale=384/max(crop.size);crop.resize(tuple(max(1,round(v*scale)) for v in crop.size),Image.Resampling.NEAREST).save(big)
                parts_all.append(big);parts_titles.append(f'{title} | {pname} az{az}')
                if part==3:bases.append(big);base_titles.append(f'{title} | base az{az}')
                crops.append(dict(source=str(src),sha256=sha(src),box_xyxy=box,part=part,crop=str(dst),enlarged=str(big),interpolation='nearest'))
    contact(paths,titles,figs/'full_lamp_comparison.png',columns=2,thumb=512)
    contact(bases,base_titles,figs/'base_comparison.png',columns=2,thumb=384)
    contact(parts_all,parts_titles,figs/'all_parts_comparison.png',columns=6,thumb=384)
    for i in range(24):cp(U/'outputs'/('baseline' if i<12 else 'edited')/'renders/030.png',U/'frames/edit'/f'{i:04}.png')
    audits={};encoding={}
    for name,n in [('orbit',24),('zoom',16),('edit',24)]:
        sources=[U/'frames'/name/f'{i:04}.png' for i in range(n)];labels=[f'{name.title()} {i:02}' for i in range(n)]
        contact(sources,labels,figs/f'{name}_all_frames.png',columns=6 if n==24 else 4,thumb=256)
        pick=(0,n//2,n-1);contact([sources[i] for i in pick],[labels[i] for i in pick],figs/f'{name}_first_middle_last.png',columns=3,thumb=512)
        trajectory=[dict(frame=i,azimuth=15*i if name=='orbit' else 30,elevation=20,distance=float(4.8-.8*np.cos(2*np.pi*i/15)) if name=='zoom' else 4.5,asset_sha256=sha(U/'outputs'/('baseline' if name=='edit' and i<12 else 'edited')/'asset.json')) for i in range(n)]
        write_json(U/f'TRAJECTORY_{name}.json',trajectory)
        video=U/'videos'/f'{name}.mkv';video.parent.mkdir(exist_ok=True);assert not video.exists()
        cmd=[FFMPEG,'-v','error','-threads','1','-filter_threads','1','-framerate','12','-i',str(U/'frames'/name/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(video)]
        r=subprocess.run(cmd,capture_output=True,timeout=90);(U/'runtime'/f'encode_{name}.log').write_bytes(r.stderr)
        encoding[name]=dict(command=cmd,returncode=r.returncode,frames=n,fps=12,resolution=[512,512]);write_json(U/'VIDEO_ENCODING.json',encoding);r.check_returncode()
        audits[name]=audit_video(U,FFMPEG,name,sources);write_json(U/'VIDEO_VALIDATION.json',audits)
    write_json(U/'MEDIA_PROVENANCE.json',dict(crops=crops,decoded_frames=sum(r['decoded_frames'] for r in audits.values()),all_rgb_exact=all(r['all_rgb_exact'] for r in audits.values()),scope='All frames decoded; contacts are visual review, not independent temporal correspondence'))
def history():
    rows=[]
    # Previous009 seal recursively includes historical failures; verify its actual files.
    old=U.parent/'unit_009';seal=json.loads((old/'SEAL.json').read_text());mf=old/'SHA256_MANIFEST.json'
    assert sha(mf)==seal['manifest_sha256'];data=json.loads(mf.read_text())
    for item in data['files']:
        p=Path(data['roots'][item['root']])/item['path'];assert sha(p)==item['sha256'],p
    rows.append(dict(unit=str(old),files=len(data['files']),manifest_sha256=sha(mf),valid=True))
    write_json(U/'HISTORICAL_SEAL_AUDIT.json',dict(valid=True,checks=rows,scope='Previous009 exact seal audit; earlier failures copied unchanged, no new historical science claim'))
    write_json(U/'RESOURCES_FINAL.json',resources())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','cold_request','dev','layers','orbit','zoom','media','history']);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
    if a.stage!='freeze':lock()
    if a.stage in ('orbit','zoom'):sequence(a.stage,a.start,a.stop if a.stop is not None else (24 if a.stage=='orbit' else 16))
    else:globals()[a.stage]()
    print(json.dumps(dict(stage=a.stage,done=True)))
if __name__=='__main__':main()
