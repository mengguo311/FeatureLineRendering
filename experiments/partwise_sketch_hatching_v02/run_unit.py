"""Frozen complete-lamp integration, serial staged execution; no old producers."""
from common import *
import argparse
import copy
import shutil
import subprocess
import time
from PIL import Image, ImageDraw
from scipy import ndimage
from renderer import render
from edit_asset import apply_edit
from temporal_probe import evaluate_probe, summarize_probes

def image_array(x): return np.uint8(np.rint(np.clip(x,0,1)*255))
def save_image(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(image_array(x)).save(path)

def check_lock():
    lock=json.loads((OUT/'SOURCE_LOCK.json').read_text())
    for name,digest in lock['files'].items(): assert sha(name)==digest, name
    return lock

def save_render(folder,name,result,seconds):
    folder=OUT/folder;folder.mkdir(parents=True,exist_ok=True)
    save_image(folder/f'{name}.png',result['image'])
    np.savez_compressed(folder/f'{name}.npz',hatch=result['hatch'],depth=result['depth'],parts=result['parts'])
    write_json(folder/f'{name}.json',dict(seconds=seconds,camera=result['camera'],diagnostics=result['diagnostics']))

def timed_render(mesh,strokes,cfg,**camera):
    t=time.perf_counter();result=render(mesh,strokes,cfg,**camera)
    return result,time.perf_counter()-t

def contact(paths,labels,destination,columns=4,thumb=256):
    rows=(len(paths)+columns-1)//columns
    sheet=Image.new('RGB',(columns*thumb,rows*(thumb+24)),'white')
    draw=ImageDraw.Draw(sheet)
    for i,(p,label) in enumerate(zip(paths,labels)):
        x=(i%columns)*thumb;y=(i//columns)*(thumb+24)
        im=Image.open(p).convert('RGB').resize((thumb,thumb),Image.Resampling.LANCZOS)
        sheet.paste(im,(x,y+24));draw.text((x+4,y+5),label,fill='black')
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);sheet.save(destination)

def verify_assets():
    mesh,strokes,cfg=load_inputs()
    t=time.perf_counter();cold=walker.generate_strokes(mesh,cfg,'mixed');duration=time.perf_counter()-t
    edited,editcfg,record=apply_edit(mesh,strokes,cfg,1,angle=35)
    oldedit=load_strokes(OUT/'inputs/mixed_shade_edit35.npz')
    anchor=[]
    for s in strokes:
        points=core.anchor_points(mesh,s)
        anchor.append(dict(id=s['id'],part=s['part'],points=len(points),arc=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum()),
                           min_bary=float(s['bary'].min()),sum_residual=float(abs(s['bary'].sum(axis=1)-1).max()),
                           wrong_part=int(np.count_nonzero(mesh['parts'][s['faces']]!=s['part'])),
                           analytic_distance_max=float(core.analytic_distance(points,cfg['asset']['profiles_ry'][str(s['part'])]).max())))
    gates=dict(cold_digest_matches=core.stroke_digest(cold)==core.stroke_digest(strokes),
               target_edit_matches_history=core.stroke_digest(edited)==core.stroke_digest(oldedit),
               non_target_exact=record['non_target_exact'],legal_anchors=all(x['min_bary']>=-1e-9 and x['sum_residual']<1e-9 and x['wrong_part']==0 for x in anchor))
    write_json(OUT/'ASSET_VALIDATION.json',dict(gates=gates,baseline_digest=core.stroke_digest(strokes),edited_digest=core.stroke_digest(edited),
                                               cold_regeneration_seconds=duration,edit=record,strokes=anchor))
    core.save_strokes(OUT/'inputs/cold_regenerated.npz',cold)
    core.save_strokes(OUT/'inputs/angle_edited.npz',edited)
    print(json.dumps(native(gates)))
    return all(gates.values())

def stills():
    mesh,strokes,cfg=load_inputs();ed=load_strokes(OUT/'inputs/angle_edited.npz')
    wc=copy.deepcopy(cfg);wc['widths_by_part']['1']=2.
    metrics=[];files=[];labels=[]
    for az in (30,120,210,300):
        b,secs=timed_render(mesh,strokes,cfg,azimuth=az);save_render('stills',f'base_{az:03}',b,secs)
        a,secs=timed_render(mesh,ed,cfg,azimuth=az);save_render('stills',f'angle_{az:03}',a,secs)
        w,secs=timed_render(mesh,strokes,wc,azimuth=az);save_render('stills',f'width_{az:03}',w,secs)
        old=core.render(mesh,strokes,cfg,azimuth=az)
        save_image(OUT/'stills'/f'old_{az:03}.png',old['image'])
        depth,parts=core.analytic_reference(cfg['asset'],b['camera'])
        np.savez_compressed(OUT/'stills'/f'reference_{az:03}.npz',depth=depth,parts=parts)
        save_image(OUT/'stills'/f'parts_{az:03}.png',core.label_image(parts)/255.)
        # Metrics consume the actual quantized output PNGs, not pre-save floats.
        base=image_array(b['image'])/255.;angle=image_array(a['image'])/255.;width=image_array(w['image'])/255.
        noedit=core.edit_metrics(base,base,parts,1,2)
        injected=angle.copy();yy,xx=np.where(parts==2);j=len(yy)//2
        cy,cx=int(yy[j]),int(xx[j]);injected[max(0,cy-4):cy+4,max(0,cx-4):cx+4]=0
        am=core.edit_metrics(base,angle,parts,1,2);wm=core.edit_metrics(base,width,parts,1,2)
        lm=core.edit_metrics(base,injected,parts,1,2)
        gates={name:m['inside_delta']>10 and m['far_other_parts_fraction']<=.02 and m['far_background_fraction']<=.02 for name,m in [('angle',am),('width',wm)]}
        gates['no_edit_control']=noedit['total_delta']==0 and not noedit['nonzero_edit']
        gates['leakage_control']=lm['far_other_parts_fraction']>am['far_other_parts_fraction']
        interior=ndimage.binary_erosion(parts>0,iterations=2)&np.isfinite(depth)&np.isfinite(b['depth'])
        dz=abs(depth[interior]-b['depth'][interior])
        metrics.append(dict(azimuth=az,angle=am,width=wm,no_edit=noedit,injected_leakage=lm,gates=gates,
                            independent_depth=dict(samples=len(dz),p95=float(np.percentile(dz,95)),max=float(dz.max())),
                            per_part_ink={str(p):float(b['hatch'][parts==p].sum()) for p in (1,2,3)}))
        for name,label in [('old','Inherited backend'),('base','New baseline'),('angle','Shade angle +35'),('width','Shade width 2 px')]:
            files.append(OUT/'stills'/f'{name}_{az:03}.png');labels.append(f'{label} | az {az}')
    write_json(OUT/'EDIT_METRICS.json',dict(views=metrics,all_gates=all(all(x['gates'].values()) for x in metrics)))
    contact(files,labels,OUT/'figures/full_lamp_comparison.png')
    # Native-resolution region crops disclose the thin stem and short base.
    im=Image.open(OUT/'stills/base_030.png').convert('RGB')
    ref=np.load(OUT/'stills/reference_030.npz')['parts']
    for p,name in [(1,'shade'),(2,'stem'),(3,'base')]:
        y,x=np.where(ref==p);box=(max(0,int(x.min())-8),max(0,int(y.min())-8),min(512,int(x.max())+9),min(512,int(y.max())+9))
        im.crop(box).save(OUT/'figures'/f'crop_{name}.png')
    print(json.dumps(dict(all_gates=all(all(x['gates'].values()) for x in metrics))))

def encode_and_validate(name,frames):
    destination=OUT/'videos'/f'{name}.mkv';destination.parent.mkdir(exist_ok=True)
    cmd=[FFMPEG,'-v','error','-y','-threads','1','-filter_threads','1','-framerate','12','-i',str(OUT/'frames'/name/'%04d.png'),'-c:v','ffv1','-level','3','-threads','1','-pix_fmt','bgr0',str(destination)]
    run=subprocess.run(cmd,capture_output=True)
    (OUT/'runtime'/f'{name}_encode.log').write_bytes(run.stderr)
    decode_cmd=[FFMPEG,'-v','error','-threads','1','-i',str(destination),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
    dec=subprocess.run(decode_cmd,capture_output=True)
    (OUT/'runtime'/f'{name}_decode.log').write_bytes(dec.stderr)
    data=np.frombuffer(dec.stdout,np.uint8);expected=frames*512*512*3
    exact=[];digests=[]
    if len(data)==expected:
        for i,frame in enumerate(data.reshape(frames,512,512,3)):
            src=np.array(Image.open(OUT/'frames'/name/f'{i:04d}.png').convert('RGB'))
            exact.append(bool(np.array_equal(frame,src)));digests.append(hashlib.sha256(frame.tobytes()).hexdigest())
    result=dict(encode_command=cmd,encode_returncode=run.returncode,decode_command=decode_cmd,decode_returncode=dec.returncode,
                decoded_bytes=len(data),expected_frames=frames,decoded_frames=len(exact),all_rgb_exact=len(exact)==frames and all(exact),distinct_frames=len(set(digests)),frame_sha256=digests)
    write_json(OUT/f'VIDEO_{name}.json',result)
    return result

def sequence(name):
    mesh,strokes,cfg=load_inputs();edited=load_strokes(OUT/'inputs/angle_edited.npz')
    count={'orbit':36,'zoom':24,'edit':24}[name]
    folder=OUT/'frames'/name;folder.mkdir(parents=True,exist_ok=True)
    records=[];cache={}
    for i in range(count):
        az=10*i if name=='orbit' else 30
        distance=float(4.8-.8*np.cos(2*np.pi*i/23)) if name=='zoom' else 4.5
        use_edit=name=='edit' and i>=12
        key=(az,distance,use_edit)
        if key not in cache:
            result,seconds=timed_render(mesh,edited if use_edit else strokes,cfg,azimuth=az,distance=distance)
            cache[key]=(image_array(result['image']),seconds,result['diagnostics'])
            reused=False
        else: reused=True
        pixels,seconds,diag=cache[key];Image.fromarray(pixels).save(folder/f'{i:04d}.png')
        records.append(dict(frame=i,azimuth=az,elevation=20,distance=distance,shade_edit=use_edit,render_seconds=0. if reused else seconds,reused_identical_scene=reused,diagnostics=diag))
        write_json(OUT/f'PARTIAL_{name}.json',dict(completed_frames=i+1,records=records))
        if i%6==0: print(f'{name} {i+1}/{count}',flush=True);check_resources()
    write_json(OUT/f'TRAJECTORY_{name}.json',records)
    contact([folder/f'{i:04d}.png' for i in range(count)],[f'{name} frame {i:02}' for i in range(count)],OUT/'figures'/f'{name}_all_frames.png',columns=6,thumb=192)
    contact([folder/f'{i:04d}.png' for i in (0,count//2,count-1)],[f'{name} frame {i:02}' for i in (0,count//2,count-1)],OUT/'figures'/f'{name}_first_middle_last.png',columns=3,thumb=512)
    print(json.dumps(native(encode_and_validate(name,count))))

def probes():
    mesh,strokes,cfg=load_inputs();protocol=json.loads((OUT/'PROTOCOL.json').read_text())
    chosen=[s for s in strokes if s['id'] in protocol['metrics']['probe_ids']]
    rows=[];faults=[];folder=OUT/'probes';folder.mkdir(exist_ok=True)
    for fi,cam in enumerate(protocol['metrics']['probe_cameras']):
        lowcam=core.camera(cam['azimuth'],cam['elevation'],cam['distance'],512,600)
        depth,parts=core.analytic_reference(cfg['asset'],lowcam)
        np.savez_compressed(folder/f'reference_{fi:02}.npz',depth=depth,parts=parts)
        for s in chosen:
            result,seconds=timed_render(mesh,[s],cfg,**cam,structure=False)
            path=core.anchor_points(mesh,s);name=s['id'].replace(':','_')
            # Quantized isolated actual output is retained and is the metric input.
            pixels=image_array(result['hatch']);Image.fromarray(pixels).save(folder/f'{fi:02}_{name}.png')
            row=evaluate_probe(pixels,path,s['part'],lowcam,depth,parts,s['id'],fi);row['render_seconds']=seconds
            rows.append(row)
            shifted=np.zeros_like(pixels);shifted[:,3:]=pixels[:,:-3]
            drift=evaluate_probe(shifted,path,s['part'],lowcam,depth,parts,s['id'],fi)
            dropout=evaluate_probe(np.zeros_like(pixels),path,s['part'],lowcam,depth,parts,s['id'],fi)
            faults.append(dict(stroke_id=s['id'],frame=fi,part=s['part'],baseline=row['summary'],drift=drift['summary'],dropout=dropout['summary']))
        write_json(OUT/'PROBE_PARTIAL.json',dict(completed_views=fi+1,rows=rows))
        print(f'probe views {fi+1}/12',flush=True);check_resources()
    summary=summarize_probes(rows)
    drift_responses=[];drop_responses=[]
    for f in faults:
        n=f['baseline']['class_counts']['visible']
        if n:
            drop_responses.append(f['dropout']['missing_visible']==n)
            a=f['baseline']['support_distance_px']['mean'];b=f['drift']['support_distance_px']['mean']
            if a is not None and b is not None: drift_responses.append(b-a)
    controls=dict(dropout_all_eligible_missing=bool(drop_responses) and all(drop_responses),
                  drift_max_mean_support_increase_px=max(drift_responses) if drift_responses else None,
                  drift_sensitive=bool(drift_responses) and max(drift_responses)>.5)
    write_json(OUT/'TEMPORAL_PROBES.json',dict(summary=summary,controls=controls,rows=rows,faults=faults))
    # Show every isolated ID at first/middle/last view, including blank hidden cases.
    paths=[];labels=[]
    for s in chosen:
        for fi in (0,6,11):
            source=folder/f'{fi:02}_{s["id"].replace(":","_")}.png'
            white=folder/f'display_{fi:02}_{s["id"].replace(":","_")}.png'
            Image.fromarray(255-np.array(Image.open(source))).save(white)
            paths.append(white);labels.append(f'{s["id"]} az {fi*30}')
    contact(paths,labels,OUT/'figures/probes_first_middle_last.png',columns=3,thumb=192)
    print(json.dumps(native(dict(status=summary['status'],per_part=summary['per_part'],controls=controls))))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['assets','stills','orbit','zoom','edit','probes']);args=ap.parse_args()
    check_lock();check_resources()
    if args.stage=='assets': ok=verify_assets();sys.exit(0 if ok else 1)
    elif args.stage=='stills': stills()
    elif args.stage=='probes': probes()
    else: sequence(args.stage)

if __name__=='__main__': main()
