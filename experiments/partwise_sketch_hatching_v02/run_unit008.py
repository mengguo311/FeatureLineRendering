"""Bounded unit008 source lock, media and provenance utility; no renderer changes."""
from common import *
import argparse,shutil,subprocess,time
from datetime import datetime,timezone
from PIL import Image
from run_unit002 import contact
U=OUT.parent/'unit_008';VIEWS=(30,120,210,300)

def copy(src,dst):
    assert not dst.exists(),dst
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)

def resources():
    count=sum(p.stat().st_size for p in U.parent.rglob('*') if p.is_file())
    root=shutil.disk_usage(WORK).free;hdd=shutil.disk_usage(U).free
    assert root>=2**30 and hdd>=10*2**30 and count<20*2**30
    return dict(task_output_bytes=count,root_free_bytes=root,hdd_free_bytes=hdd,cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False)

def freeze():
    names=['common.py','renderer.py','asset_cli.py','direction_cli.py','test_direction_unit008.py','run_unit008.py','receipt_unit008.py','validate_unit008.py','validate_unit005.py','validate_unit004.py','validate_unit003.py','run_unit002.py']
    files=[WORK/'experiments/partwise_sketch_hatching_v02'/n for n in names]
    files += [LEGACY/n for n in ('core.py','core_walk_v2.py')]
    files += [U/'PROTOCOL.json']+sorted((U/'inputs').glob('*'))
    for p in files:
        if p.is_relative_to(WORK):copy(p,U/'source_snapshot'/p.relative_to(WORK))
    write_json(U/'SOURCE_LOCK.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in files},git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),numpy_version=np.__version__))
    write_json(U/'RESOURCES_LOCK.json',resources())

def lock():
    for p,h in json.loads((U/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(p)==h,p
    resources()

def cold_request():
    folder=U/'cold_request'
    for name in ('recipe.json','mesh.npz','retained.npz','config.json'):copy(U/'outputs/edited'/name,folder/name)
    write_json(U/'COLD_REQUEST.json',dict(files={p.name:sha(p) for p in folder.glob('*')},target_cache_present=False,scope='Fresh target regeneration from recipe plus retained198 non-target asset. Not whole-object procedural regeneration.'))

def media():
    paths=[];labels=[]
    for az in VIEWS:
        for name,title in (('baseline','Before: 0 deg'),('edited','After: +15 deg')):
            paths.append(U/'outputs'/name/'renders'/f'{az:03}.png');labels.append(f'{title} | az {az}')
    contact(paths,labels,U/'figures/full_lamp_comparison.png',columns=2,thumb=512)
    cfg=json.loads((U/'outputs/edited/config.json').read_text());crops=[];titles=[];allcrops=[];alltitles=[]
    for az in VIEWS:
        _,parts=core.analytic_reference(cfg['asset'],core.camera(az,20,4.5,512,600))
        for part,pname in ((1,'shade'),(2,'stem'),(3,'base')):
            y,x=np.where(parts==part);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
            for name in ('baseline','edited'):
                dest=U/'figures'/f'{name}_{az:03}_{pname}.png'
                with Image.open(U/'outputs'/name/'renders'/f'{az:03}.png') as im:im.crop(box).save(dest)
                allcrops.append(dest);alltitles.append(f'{name} {pname} | az {az}')
                if part==1:crops.append(dest);titles.append(f'{name} shade | az {az}')
    contact(crops,titles,U/'figures/shade_comparison.png',columns=2,thumb=384)
    contact(allcrops,alltitles,U/'figures/all_parts_comparison.png',columns=6,thumb=256)
    frames=U/'frames/edit';frames.mkdir(parents=True)
    for i in range(24):copy(U/'outputs'/('baseline' if i<12 else 'edited')/'renders/030.png',frames/f'{i:04}.png')
    files=sorted(frames.glob('*.png'))
    contact(files,[f'Edit frame {i:02}' for i in range(24)],U/'figures/edit_all_frames.png',columns=6,thumb=256)
    contact([files[i] for i in (0,12,23)],['First: 0 deg','Middle: +15 deg','Last: +15 deg'],U/'figures/edit_first_middle_last.png',columns=3,thumb=512)
    video=U/'videos/edit.mkv';video.parent.mkdir(parents=True)
    command=[FFMPEG,'-v','error','-threads','1','-filter_threads','1','-framerate','12','-i',str(frames/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(video)]
    result=subprocess.run(command,capture_output=True,timeout=90)
    (U/'runtime/media_encode.log').write_bytes(result.stderr)
    write_json(U/'VIDEO_ENCODING.json',dict(command=command,returncode=result.returncode));result.check_returncode()
    from validate_unit004 import audit_video
    write_json(U/'VIDEO_VALIDATION.json',audit_video(U,FFMPEG,'edit',files))

def history():
    rows=[]
    for n in (3,4,5,6,7):
        old=U.parent/f'unit_{n:03}';seal=json.loads((old/'SEAL.json').read_text());manifest=old/'SHA256_MANIFEST.json'
        assert sha(manifest)==seal['manifest_sha256']
        data=json.loads(manifest.read_text())
        for item in data['files']:
            path=Path(data['roots'][item['root']])/item['path'];assert sha(path)==item['sha256'],path
        rows.append(dict(unit=str(old),files=len(data['files']),manifest_sha256=sha(manifest),valid=True))
    write_json(U/'HISTORICAL_SEAL_AUDIT.json',dict(valid=True,checks=rows))
    write_json(U/'RESOURCES_FINAL.json',resources())

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['freeze','cold_request','media','history']);args=ap.parse_args()
    if args.stage!='freeze':lock()
    globals()[args.stage]();print(json.dumps(dict(stage=args.stage,done=True)))
