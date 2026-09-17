"""Post-freeze, image-evidence-free rendering and persistent ink-budget calibration.

Both budgets are calibrated on the complete DEV path, never on selected frames.
Each calibration produces one fixed subset of whole object-space paths. Matching
length and matching area are separate controls, not a claim of simultaneous equality.
"""
import hashlib,json,subprocess,time
from pathlib import Path
import cv2,numpy as np,torch,imageio_ffmpeg
from src import common,render as gs_render,stroke_relations as draw
from run_raster_candidates import (ROOT,OUT,ARMS,git,sha,dump,paths_from,geom,
                                   provenance,scaled,label,stock_rgb)


def orbit(m,cams,g,keep):
    cfg=m['trajectory'];ref=cams[cfg['reference_train_index']]
    target=np.median(g['mu'][keep],axis=0);off=ref.center-target
    radius=float(np.linalg.norm(off));phi0=np.arctan2(off[1],off[0]);out=[]
    K=scaled(ref,cfg['resolution']).K
    for j in range(cfg['frames']):
        angle=2*np.pi*j/cfg['frames'];phi=phi0+angle
        el=np.deg2rad(cfg['elevation_deg']+cfg['elevation_swing_deg']*np.sin(2*angle))
        C=target+radius*np.array([np.cos(el)*np.cos(phi),np.cos(el)*np.sin(phi),np.sin(el)])
        forward=target-C;forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0.,0.,1.]);right/=np.linalg.norm(right);down=np.cross(forward,right)
        c2w=np.eye(4);c2w[:3,:3]=np.stack([right,down,forward],axis=1);c2w[:3,3]=C
        out.append(common.Camera(K,np.linalg.inv(c2w),cfg['resolution'],cfg['resolution'],f'dev_{j:03d}'))
    return out


def path_order(paths,seed):
    # Geometry hashes give identical A/N1 ordering when N1 produces no additions.
    keys=[hashlib.sha256(np.round(p,7).tobytes()+str(seed).encode()).hexdigest() for p in paths]
    return np.argsort(keys,kind='stable')


def prefix_mask(order,n):
    mask=np.zeros(len(order),bool);mask[order[:n]]=True;return mask


def image_metrics(projected,selected,image):
    lengths=draw.path_lengths(projected);fragments=[];count=np.zeros(image.shape[:2],np.uint16)
    for i in np.flatnonzero(selected):
        for p in projected[i]:
            fragments.append(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
            lo=np.maximum(np.floor(p.min(0)).astype(int)-2,0);hi=np.minimum(np.ceil(p.max(0)).astype(int)+3,np.array(image.shape[1::-1]))
            if np.any(hi<=lo):continue
            mask=np.zeros((hi[1]-lo[1],hi[0]-lo[0]),np.uint8)
            cv2.polylines(mask,[np.round((p-lo)*16).astype(np.int32)],False,1,1,cv2.LINE_8,4)
            count[lo[1]:hi[1],lo[0]:hi[0]]+=mask
    return dict(visible_length_px=float(lengths[selected].sum()),ink_area_px=float((1-image[:,:,0]/255.).sum()),
        overlap_rate=float((count>1).sum()/max((count>0).sum(),1)),fragments=len(fragments),
        short_fragment_fraction_lt12px=float(np.mean(np.asarray(fragments)<12)) if fragments else 0.)


def render_outputs(m,scene,cams,photos,dest,cheap):
    if cheap:raise RuntimeError('no cheap DEV rendering')
    frozen=dest/'step4.json';rel=str(frozen.relative_to(ROOT))
    committed=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+rel])
    if hashlib.sha256(committed).hexdigest()!=sha(frozen):raise RuntimeError('final paths/parameters must be committed before DEV')
    if git('status','--porcelain','--','src','scripts',str(OUT/'MANIFEST.json')):raise RuntimeError('commit renderer and parameters before DEV')
    t=time.perf_counter();meta=json.loads(frozen.read_text());folder=dest/'render';folder.mkdir(exist_ok=True)
    if meta['provenance']['manifest_sha256']!=sha(OUT/'MANIFEST.json'):raise RuntimeError('manifest changed after fit')
    paths={};dense={};orders={}
    for arm in ARMS:
        p=dest/f'step4/paths_{arm}.npz'
        if sha(p)!=meta['arms'][arm]['path_sha256']:raise RuntimeError('path mutation')
        paths[arm]=paths_from(np.load(p));dense[arm]=draw.densify(paths[arm]) if paths[arm] else []
        orders[arm]=path_order(paths[arm],m['seed'])
    g,keep=geom(scene);trajectory=orbit(m,cams,g,keep)
    official,info=stock_rgb(dict(gs=m['inputs'][scene]['gs'],renderer=m['renderer']))
    dump(folder/'dev_cameras.json',dict(K=trajectory[0].K.tolist(),w2c=[c.w2c.tolist() for c in trajectory],
        freeze_commit=git('rev-parse','HEAD'),source='predeclared analytic nonpolar orbit'))
    projections={a:[] for a in ARMS};costs={a:[] for a in ARMS};rgbs=[];native_areas={a:[] for a in ARMS}
    for j,cam in enumerate(trajectory):
        gb=gs_render.render_gbuffer(g,keep,cam);rgbs.append((official(cam)[:,:,::-1]*255).astype('uint8'))
        for arm in ARMS:
            pp=draw.project_paths(dense[arm],cam,gb['depth']) if dense[arm] else []
            projections[arm].append(pp);costs[arm].append(draw.path_lengths(pp))
            im=draw.draw_paths(pp,np.ones(len(pp),bool),(cam.H,cam.W));native_areas[arm].append(float((1-im[:,:,0]/255.).sum()))
        if j%20==0:print('DEV projection',j,round(time.perf_counter()-t,1),flush=True)
        del gb;torch.cuda.empty_cache()
    mean_cost={a:np.mean(costs[a],axis=0) for a in ARMS}
    target_length=min(float(mean_cost[a].sum()) for a in ARMS);target_area=min(float(np.mean(native_areas[a])) for a in ARMS)
    selections={'native':{},'length_matched':{},'area_matched':{}};calibration={}
    for arm in ARMS:
        order=orders[arm];selections['native'][arm]=np.ones(len(order),bool)
        cumulative=np.r_[0,np.cumsum(mean_cost[arm][order])];n=int(np.argmin(abs(cumulative-target_length)))
        selections['length_matched'][arm]=prefix_mask(order,n)
        memo={0:0.,len(order):float(np.mean(native_areas[arm]))}
        def area_at(n):
            if n not in memo:
                select=prefix_mask(order,n)
                memo[n]=float(np.mean([(1-draw.draw_paths(pp,select,(400,400))[:,:,0]/255.).sum() for pp in projections[arm]]))
            return memo[n]
        lo,hi=0,len(order)
        while hi-lo>1:
            mid=(lo+hi)//2
            if area_at(mid)<target_area:lo=mid
            else:hi=mid
        best=min([lo,hi],key=lambda n:abs(area_at(n)-target_area));selections['area_matched'][arm]=prefix_mask(order,best)
        calibration[arm]=dict(length_selected_paths=n,area_selected_paths=best,area_evaluations=len(memo),
            length_relative_error=float(abs(cumulative[n]-target_length)/max(target_length,1e-12)),
            area_relative_error=float(abs(area_at(best)-target_area)/max(target_area,1e-12)))
        print('ink calibration',arm,calibration[arm],flush=True)
    dump(folder/'display_calibration.json',dict(target_length_px=target_length,target_area_px=target_area,arms=calibration,
        selected_ids={mode:{a:np.flatnonzero(v).tolist() for a,v in sels.items()} for mode,sels in selections.items()},
        note='DEV-derived display budgets only; each subset fixed for every frame; no evidence reads or geometric changes'))
    fixed=[0,30,60,90];metrics={};videos={};best_null=max(['N1','N2'],key=lambda a:json.loads((dest/'step3.json').read_text())['arms'][a]['accepted'])
    for mode,select in selections.items():
        video=folder/f'rgb_A_D_{mode}.mp4';writer=imageio_ffmpeg.write_frames(str(video),(1200,426),fps=m['trajectory']['fps'],codec='libx264',quality=8,macro_block_size=1);writer.send(None)
        main_fixed=[];arm_fixed=[];thumbs=[];metrics[mode]={a:[] for a in ARMS}
        for j in range(len(trajectory)):
            images={a:draw.draw_paths(projections[a][j],select[a],(400,400)) for a in ARMS}
            main=np.hstack([label(rgbs[j],f'Official RGB | {j:03d}'),label(images['A'],f'A | {mode}'),label(images['D'],f'D | {mode}')]);writer.send(np.ascontiguousarray(main[:,:,::-1]))
            for a in ARMS:metrics[mode][a].append(dict(frame=j,**image_metrics(projections[a][j],select[a],images[a])))
            if j in fixed:
                main_fixed.append(main);arm_fixed.append(np.hstack([label(images[a],f'{a} | frame {j:03d}') for a in ['A','B','C','D',best_null]]))
                cv2.imwrite(str(folder/f'{mode}_{j:03d}.png'),main)
            thumbs.append(cv2.resize(main,(600,213),interpolation=cv2.INTER_AREA))
        writer.close();cv2.imwrite(str(folder/f'fixed_{mode}.png'),np.vstack(main_fixed));cv2.imwrite(str(folder/f'arms_{mode}.png'),np.vstack(arm_fixed))
        for start in range(0,len(thumbs),20):
            page=thumbs[start:start+20];cv2.imwrite(str(folder/f'contact_{mode}_{start//20:02d}.png'),np.vstack([np.hstack(page[k:k+2]) for k in range(0,len(page),2)]))
        cap=cv2.VideoCapture(str(video));count=0
        while True:
            ok,_=cap.read()
            if not ok:break
            count+=1
        cap.release()
        if count!=len(trajectory):raise RuntimeError('incomplete video')
        videos[mode]=dict(path=str(video.relative_to(ROOT)),sha256=sha(video),bytes=video.stat().st_size,decoded_frames=count)
        print('rendered full video',mode,'frames',count,'seconds',round(time.perf_counter()-t,1),flush=True)
    # Held-out camera metadata only. No held-out photos/evidence enter this rendering.
    valpanels=[]
    for v in m['dev_validation_indices']:
        cam=scaled(cams[v],400);gb=gs_render.render_gbuffer(g,keep,cam);rgb=(official(cam)[:,:,::-1]*255).astype('uint8');tiles=[label(rgb,f'Official held-out camera {v}')]
        for a in ['A','D']:
            pp=draw.project_paths(dense[a],cam,gb['depth']) if dense[a] else []
            tiles.append(label(draw.draw_paths(pp,np.ones(len(pp),bool),(400,400)),a+' native'))
        valpanels.append(np.hstack(tiles))
    cv2.imwrite(str(folder/'heldout_camera_panel.png'),np.vstack(valpanels))
    means={mode:{a:{k:float(np.mean([x[k] for x in rows])) for k in rows[0] if k!='frame'} for a,rows in arms.items()} for mode,arms in metrics.items()}
    dump(dest/'render.json',dict(provenance=provenance(),freeze_commit=git('rev-parse','HEAD'),step4_sha256=sha(frozen),
        means=means,per_frame=metrics,calibration=calibration,videos=videos,official_rgb=info,seconds=time.perf_counter()-t,
        runtime='fixed 3D paths + GS depth visibility only',best_null=best_null,frames=len(trajectory),fixed_frames=fixed))
