#!/usr/bin/env python3
"""Publish all complete path evidence, without frame/method selection."""
import sys,json,shutil,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image,ImageDraw
from src.temporal_depth2d import sha,atomic_json,actual_ink
ART=ROOT/'artifacts/temporal_depth2d_video_probe';RUN=ROOT/'out/temporal_depth2d_video_probe/run'
SCENES=['lego','chair','drums','ficus']


def main():
    state=json.loads((RUN/'STATE.json').read_text())
    if state['status']!='COMPLETE':raise RuntimeError('cannot curate incomplete run')
    manifest=json.loads((ART/'INPUTS.json').read_text());media=[];metrics=[];counts=[]
    for scene in SCENES:
        for arc in [0,1]:
            name=f'{scene}_arc{arc}';unit=RUN/name;dst=ART/'media'/name;dst.mkdir(parents=True,exist_ok=True)
            result=json.loads((unit/'RESULTS.json').read_text());metrics.append(result)
            for p in sorted(unit.glob('*.png')):shutil.copy2(p,dst/p.name)
            shutil.copy2(unit/'RESULTS.json',dst/'RESULTS.json');shutil.copy2(unit/'DECODE.json',dst/'DECODE.json');shutil.copy2(unit/'SEAL.json',dst/'SEAL.json')
            # Entire video decoded contact review, all 33 consecutive frames, not sampled.
            import cv2
            cap=cv2.VideoCapture(str(unit/'comparison_forward.mp4'));tiles=[];i=0
            while True:
                ok,f=cap.read()
                if not ok:break
                rgb=cv2.cvtColor(f,cv2.COLOR_BGR2RGB)
                tiles.append(Image.fromarray(rgb).resize((800,207),Image.Resampling.LANCZOS));i+=1
            cap.release()
            if i!=33:raise ValueError('comparison decode count')
            for start in range(0,33,11):
                canvas=Image.new('RGB',(800,207*len(tiles[start:start+11])),'white')
                for j,tile in enumerate(tiles[start:start+11]):canvas.paste(tile,(0,j*207))
                canvas.save(dst/f'video_decoded_{start:03d}_{min(32,start+10):03d}.png')
            # Readable all-frame baseline overview; all original poses, chronological rows.
            canvas=Image.new('RGB',(1200,228*11),'white');draw=ImageDraw.Draw(canvas)
            for i in range(33):
                col,row=i%3,i//3
                for k,method in enumerate(['GS','B_matched']):
                    with Image.open(unit/'frames'/f'{i:03d}_{method}.png') as im:canvas.paste(im.resize((200,200),Image.Resampling.LANCZOS),(col*400+k*200,row*228+28))
                draw.text((col*400+6,row*228+7),f'{name} | frame {i:03d}',fill='black')
            canvas.save(dst/'B_all33_overview.png')
            original=next(r for r in manifest['scenes'][scene]['files'] if r['split']=='original_video' and f'arc{arc}_complete' in r['path'])
            shutil.copyfile(original['path'],unit.parent/(name+'_original.mp4'))
            counts.append({'path':name,'B':33,'W':33 if 'W' in result['methods'] else 0,'CAND':33 if 'CAND' in result['methods'] else 0,'original_video_decoded':33,'status':result['status']})
            for p in sorted(unit.rglob('*')):
                if p.is_file():media.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    for split in ['F_construction','C_reserved']:
        dst=ART/'media'/split;dst.mkdir(parents=True,exist_ok=True)
        for p in (RUN/split).glob('*_ALL.png'):shutil.copy2(p,dst/p.name)
        shutil.copy2(RUN/split/'CENSUS.json',dst/'CENSUS.json')
    atomic_json(ART/'FRAME_COUNTS.json',{'paths':counts,'unique_camera_frames':264,'baseline_frames':264,'candidate_frames':33,'warp_ema_frames':33,'candidate_not_run_after_kill':231,'F':32,'C':32})
    atomic_json(ART/'MEDIA_MANIFEST.json',{'assets':media,'original_videos':[r for s in manifest['scenes'].values() for r in s['files'] if r['split']=='original_video']})
    atomic_json(ART/'RUN_STATE.json',state)
    kill=metrics[0];native={}
    for m in ['B','W','CAND']:
        native[m]=[]
        for i in range(33):
            with Image.open(RUN/'lego_arc0/frames'/f'{i:03d}_{m}_native.png') as im:ink=1-np.asarray(im)[:,:,0].astype(float)/255
            b=kill['readability']['B'][i]['actual_ink'];native[m].append(actual_ink(ink)/b)
    atomic_json(ART/'NATIVE_INK.json',native)
    cards=''
    for row in counts:
        name=row['path'];url=f'../../out/temporal_depth2d_video_probe/run/{name}/B_pingpong.mp4'
        cards+=f'<article><h2>{name} · 33 原始帧</h2><video controls preload="metadata" src="{url}"></video><p><a href="media/{name}/B_all33_overview.png">全部 33 帧</a> · <a href="../../out/temporal_depth2d_video_probe/run/{name}_original.mp4">封存原始比较视频</a></p></article>'
    page='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>二维线条时序实验</title><style>body{font:16px system-ui;margin:36px auto;max-width:1280px;padding:0 24px;color:#252323;background:#f7f6f2}h1{font-size:36px}video{width:100%;background:white}section{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:18px;background:white;border-radius:12px}h2{font-size:19px}a{color:#665034}p{line-height:1.6}.comparison{margin-bottom:28px;padding:24px;background:#fff;border-radius:12px}@media(max-width:700px){section{grid-template-columns:1fr}}</style><h1>二维线条时序实验</h1><p>冻结 GS 相机路径 · 4 场景 × 2 路径 × 33 帧。二维、视角相关；没有固定三维墨迹或真实照片泛化结论。</p><div class="comparison"><h2>Lego arc0：预注册 kill test 未通过</h2><p>墨量和静帧结构通过；候选运动差异未优于简单 warp+EMA。其余 231 帧没有运行候选。完整比较依次为 GS / 原生 depth2d / warp+EMA / 二维曲线。</p><video controls preload="metadata" src="../../out/temporal_depth2d_video_probe/run/lego_arc0/comparison_forward.mp4"></video><p><a href="../../out/temporal_depth2d_video_probe/run/lego_arc0/comparison_native.mp4">各法原生展示</a> · <a href="../../out/temporal_depth2d_video_probe/run/lego_arc0/CAND_pingpong.mp4">候选往返</a> · <a href="media/lego_arc0/worst_and_neighbors.png">最坏帧及邻帧</a> · <a href="REPORT.md">完整报告</a></p></div><h2>全部八条原始路径：depth2d 原生往返视频</h2><p>每条往返视频为 65 播放帧，包含全部 33 原始相机帧，随后按原路返回。</p><section>'''+cards+'</section></html>'
    (ART/'gallery.html').write_text(page)
    print('curated all 264 baseline frames + full kill comparison; no selected-success subset')

if __name__=='__main__':main()
