"""Post-freeze rendering: fixed object-space paths, common depth and brush.

DEV access here calibrates display budgets only. No image evidence, graph edits,
per-frame selection, or path reconstruction is performed.
"""
import json,time,subprocess,hashlib
import cv2,numpy as np,torch,imageio_ffmpeg
from src import common,render,stroke_relations as draw
from src.stroke_simplify import budget_prefix
from raster_candidate_outputs import orbit,path_order,image_metrics
from run_stroke_organization import ROOT,OUT,OLD,ARMS,git,sha,dump,scaled,label,stock_rgb


def paths_from(path):
    z=np.load(path);return [z['vertices'][a:b] for a,b in zip(z['offsets'][:-1],z['offsets'][1:])]


def densify_fixed(paths,step):
    output=[]
    for p in paths:
        pieces=[]
        for a,b in zip(p[:-1],p[1:]):
            n=max(1,min(64,int(np.ceil(np.linalg.norm(b-a)/step))))
            pieces.append(a+np.arange(n)[:,None]/n*(b-a))
        output.append(np.vstack(pieces+[p[-1:]]))
    return output


def trajectory(m,cams,g,keep):
    result=orbit(m,cams,g,keep);target=np.median(g['mu'][keep],axis=0)
    a=np.deg2rad(m['trajectory']['phase_offset_deg']);R=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1.]])
    rotated=[]
    for cam in result:
        c=np.linalg.inv(cam.w2c);c[:3,:3]=R@c[:3,:3];c[:3,3]=target+R@(c[:3,3]-target)
        rotated.append(common.Camera(cam.K,np.linalg.inv(c),cam.H,cam.W,cam.name))
    return rotated


def freeze_check():
    names=['out/stroke_organization/MANIFEST.json','src/stroke_graph.py','src/path_cover.py','src/stroke_simplify.py',
           'scripts/run_stroke_organization.py','scripts/stroke_organization_outputs.py']
    names += [f'out/stroke_organization/paths/{a}.json' for a in ARMS]
    for name in names:
        content=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+name])
        if hashlib.sha256(content).hexdigest()!=sha(ROOT/name):raise RuntimeError('must commit before DEV: '+name)
    for a in ARMS:
        meta=json.loads((OUT/f'paths/{a}.json').read_text())
        if sha(OUT/f'paths/{a}.npz')!=meta['path_sha256']:raise RuntimeError('path changed '+a)
    return dict(commit=git('rev-parse','HEAD'),files={name:sha(ROOT/name) for name in names})


def packed_projection(path,frames):
    vertices=[];roff=[0];poff=[0];foff=[0]
    for pp in frames:
        for runs in pp:
            for run in runs:vertices.append(run);roff.append(roff[-1]+len(run))
            poff.append(len(roff)-1)
        foff.append(len(poff)-1)
    np.savez_compressed(path,vertices=np.concatenate(vertices) if vertices else np.empty((0,2)),run_offsets=roff,path_offsets=poff,frame_offsets=foff)


def unpacked_projection(path):
    z=np.load(path);r=z['run_offsets'];p=z['path_offsets'];f=z['frame_offsets'];v=z['vertices'];frames=[]
    for fa,fb in zip(f[:-1],f[1:]):
        frames.append([[v[r[k]:r[k+1]] for k in range(p[i],p[i+1])] for i in range(fa,fb)])
    return frames


def metrics(pp,selected,image):
    result=image_metrics(pp,selected,image)
    lengths=[float(np.linalg.norm(np.diff(run,axis=0),axis=1).sum()) for i in np.flatnonzero(selected) for run in pp[i]]
    total=draw.path_lengths(pp)[selected];total=total[total>0]
    result.update(median_visible_fragment_px=float(np.median(lengths)) if lengths else 0.,
                  median_visible_path_px=float(np.median(total)) if len(total) else 0.,visible_paths=int(len(total)))
    return result


def render_all(m):
    frozen=freeze_check();start=time.perf_counter();folder=OUT/'render';folder.mkdir(exist_ok=True)
    if (OUT/'render.json').exists():raise FileExistsError('render already completed')
    paths={a:paths_from(OUT/f'paths/{a}.npz') for a in ARMS}
    unit=float(np.load(OUT/'graph/graph.npz')['unit']);dense={a:densify_fixed(p,.5*unit) for a,p in paths.items()}
    cams,_=common.load_cameras('lego');g=common.load_gaussians('lego');keep=render.defloat_mask(g['mu'],g['opacity'])
    cameras=trajectory(m,cams,g,keep)
    official,official_info=stock_rgb(dict(gs=m['inputs']['gs'],renderer=m['renderer']))
    projections={a:[] for a in ARMS};rgbs=[]
    for j,cam in enumerate(cameras):
        rgb=(official(cam)[:,:,::-1]*255).astype('uint8');rgbs.append(rgb)
        depth=render.render_gbuffer(g,keep,cam)['depth']
        for a in ARMS:projections[a].append(draw.project_paths(dense[a],cam,depth) if dense[a] else [])
        if j%10==0:print('project frozen paths',j,'/120',round(time.perf_counter()-start,1),'seconds',flush=True)
    for a in ARMS:packed_projection(folder/f'projection_{a}.npz',projections[a])
    np.savez_compressed(folder/'official_frames.npz',rgb=np.array(rgbs))
    native_areas={};mean_lengths={}
    for a in ARMS:
        selected=np.ones(len(paths[a]),bool)
        native_areas[a]=np.array([(1-draw.draw_paths(pp,selected,(400,400))[:,:,0]/255.).sum() for pp in projections[a]])
        mean_lengths[a]=np.mean([draw.path_lengths(pp) for pp in projections[a]],axis=0)
    target_area=float(native_areas['A'].mean()*m['ink_matching']['target_A_native_fraction'])
    target_length=float(mean_lengths['A'].sum()*m['ink_matching']['target_A_native_fraction'])
    selection={mode:{} for mode in ['native','length_matched','area_matched']};calibration={}
    for a in ARMS:
        order=path_order(paths[a],m['seed']);selection['native'][a]=np.ones(len(paths[a]),bool)
        def choose_length(ids):return mean_lengths[a][ids].sum()
        def choose_area(ids):
            sel=np.zeros(len(paths[a]),bool);sel[ids]=True
            return np.mean([(1-draw.draw_paths(pp,sel,(400,400))[:,:,0]/255.).sum() for pp in projections[a]])
        record={}
        for mode,target,fn in [('length_matched',target_length,choose_length),('area_matched',target_area,choose_area)]:
            n,value,info=budget_prefix(order,fn,target);sel=np.zeros(len(paths[a]),bool);sel[order[:n]]=True;selection[mode][a]=sel
            error=abs(value-target)/max(target,1e-12);record[mode]=dict(**info,selected_paths=int(n),value=float(value),target=target,relative_error=float(error),matched=bool(error<=m['ink_matching']['tolerance']))
        calibration[a]=record;print('calibrated',a,record,flush=True)
    dump(folder/'calibration.json',dict(target_length_px=target_length,target_area_px=target_area,arms=calibration,
        selected_ids={mode:{a:np.flatnonzero(v).tolist() for a,v in arms.items()} for mode,arms in selection.items()},
        note='separate fixed whole-path subsets; full-DEV aggregate costs only; under-capacity arms explicitly unmatched'))
    fixed=[0,30,60,90];all_metrics={};videos={}
    for mode,selections in selection.items():
        video=folder/f'official_A_C_{mode}.mp4'
        writer=imageio_ffmpeg.write_frames(str(video),(1200,426),fps=m['trajectory']['fps'],codec='libx264',quality=8,macro_block_size=1);writer.send(None)
        main_fixed=[];all_fixed=[];contacts=[];all_metrics[mode]={a:[] for a in ARMS}
        for j in range(120):
            ims={a:draw.draw_paths(projections[a][j],selections[a],(400,400)) for a in ARMS}
            main=np.hstack([label(rgbs[j],f'Official RGB | {j:03d}'),label(ims['A'],f'A current | {mode}'),label(ims['C'],f'C organized | {mode}')])
            writer.send(np.ascontiguousarray(main[:,:,::-1]))
            for a in ARMS:all_metrics[mode][a].append(dict(frame=j,**metrics(projections[a][j],selections[a],ims[a])))
            if j in fixed:
                main_fixed.append(main);all_fixed.append(np.hstack([label(ims[a],f'{a} | {j:03d}') for a in ARMS]));cv2.imwrite(str(folder/f'main_{mode}_{j:03d}.png'),main)
            strip=np.hstack([label(cv2.resize(ims[a],(150,150),interpolation=cv2.INTER_AREA),f'{j:03d} {a}') for a in ARMS]);contacts.append(strip)
            if (j+1)%10==0:
                cv2.imwrite(str(folder/f'all_contact_{mode}_{j//10:02d}.png'),np.vstack(contacts));contacts=[]
        writer.close();cv2.imwrite(str(folder/f'fixed_{mode}.png'),np.vstack(main_fixed));cv2.imwrite(str(folder/f'all_fixed_{mode}.png'),np.vstack(all_fixed))
        cap=cv2.VideoCapture(str(video));decoded=[];count=0
        while True:
            ok,im=cap.read()
            if not ok:break
            decoded.append(cv2.resize(im,(600,213),interpolation=cv2.INTER_AREA));count+=1
            if count%20==0:
                cv2.imwrite(str(folder/f'video_contact_{mode}_{count//20-1:02d}.png'),np.vstack([np.hstack(decoded[i:i+2]) for i in range(0,20,2)]));decoded=[]
        cap.release()
        if count!=120:raise RuntimeError('incomplete video')
        videos[mode]=dict(path=str(video.relative_to(ROOT)),frames=count,sha256=sha(video),bytes=video.stat().st_size)
        print('rendered',mode,'all 120 frames',round(time.perf_counter()-start,1),'seconds',flush=True)
    # Same TRAIN camera for premarked before/after, with the DEV display selections
    # already fixed. The method never uses these boxes or calibration results.
    cam=scaled(cams[53],400);st=np.load(OLD/'step1/state_053.npz');dep=torch.from_numpy(st['depth'])
    pp={a:draw.project_paths(dense[a],cam,dep) if dense[a] else [] for a in ARMS}
    rgb=cv2.imread(str(OLD/'step1/channels_053.png'))[26:426,:400]
    raw=[]
    for a in ARMS:
        uncut=[]
        for p in paths[a]:
            uv,z=common.project(p,cam);uncut.append([uv] if np.all(z>0) else [])
        raw.append(label(draw.draw_paths(uncut,np.ones(len(uncut),bool),(400,400)),a+' raw / no visibility'))
    cv2.imwrite(str(folder/'raw_organized_train053.png'),np.vstack([np.hstack(raw[:3]),np.hstack(raw[3:])]))
    for mode,sels in selection.items():
        images={'RGB':rgb,**{a:draw.draw_paths(pp[a],sels[a],(400,400)) for a in ARMS}}
        cv2.imwrite(str(folder/f'final_train053_{mode}.png'),np.hstack([label(images[a],a+' '+mode) for a in ['RGB']+ARMS]))
        rows=[]
        for region in m['regions']:
            x0,y0,x1,y1=region['box'];row=[]
            for name in ['RGB','A','B','C','C-no-global','C-no-corner']:
                crop=images[name][y0:y1,x0:x1];canv=np.full((180,320,3),255,np.uint8)
                ratio=min(320/crop.shape[1],180/crop.shape[0]);cr=cv2.resize(crop,None,fx=ratio,fy=ratio,interpolation=cv2.INTER_NEAREST);canv[:cr.shape[0],:cr.shape[1]]=cr
                row.append(label(canv,region['id']+' '+name))
            rows.append(np.hstack(row))
        cv2.imwrite(str(folder/f'regions_{mode}.png'),np.vstack(rows))
    means={mode:{a:{key:float(np.mean([r[key] for r in rows])) for key in rows[0] if key!='frame'} for a,rows in arms.items()} for mode,arms in all_metrics.items()}
    dump(OUT/'render.json',dict(freeze=frozen,official_rgb=official_info,means=means,per_frame=all_metrics,calibration=calibration,videos=videos,
        fixed_frames=fixed,seconds=time.perf_counter()-start,common_visibility_sample_step_world=.5*unit,
        runtime='fixed world-space paths, common GS disc depth, no RGB evidence or framewise grouping'))
