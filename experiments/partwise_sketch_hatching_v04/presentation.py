"""Bounded serial presentation exports from an immutable saved-asset snapshot."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,os,shutil,subprocess,time,zipfile
import numpy as np
from PIL import Image
from demo import load_asset,new_output,save_frame
from geometry import orbit_camera,project
from media import contact

KINDS={'image':1,'orbit':12,'zoom':6}
SIZE=512
FPS=6

def camera_values(values):
    if not isinstance(values,dict) or set(values)!= {'azimuth','elevation','distance'}:
        raise ValueError('camera requires azimuth, elevation and distance')
    result={}
    for key,lo,hi in [('azimuth',-360,360),('elevation',5,75),('distance',3.8,6)]:
        value=values[key]
        if type(value) not in (int,float) or not np.isfinite(value) or not lo<=value<=hi:
            raise ValueError('camera value outside demo range: '+key)
        result[key]=float(value)
    return result

def fit_distance(vertices,azimuth,elevation,margin=16):
    """Exact perspective bounds for the saved vertices, with origin-facing camera."""
    c=orbit_camera(azimuth,elevation,1.,SIZE)
    p=vertices@np.asarray(c['extrinsic'])[:3,:3].T
    return float(max(np.max(.21-p[:,2]),np.max(c['fx']*np.abs(p[:,0])/(c['cx']-margin)-p[:,2]),
                     np.max(c['fy']*np.abs(p[:,1])/(c['cy']-margin)-p[:,2]))+1e-6)

def trajectory(mesh,values,kind):
    if kind not in KINDS:raise ValueError('unknown presentation kind')
    values=camera_values(values);a,e,d=(values[k] for k in ('azimuth','elevation','distance'))
    if kind=='image':parameters=[values]
    elif kind=='orbit':
        angles=[((a+360*i/12+180)%360)-180 for i in range(12)]
        distance=max(d,*[fit_distance(mesh['vertices'],angle,e) for angle in angles])
        parameters=[dict(azimuth=angle,elevation=e,distance=distance) for angle in angles]
    else:
        near=max(d,fit_distance(mesh['vertices'],a,e));far=max(d*1.15,near)
        parameters=[dict(azimuth=a,elevation=e,distance=float(x)) for x in np.linspace(far,near,6)]
    return [orbit_camera(**p,size=SIZE) for p in parameters],dict(requested=values,actual=parameters,
        framing='image keeps exact current camera; motion fits all proxy vertices with 16px margin',
        adjusted=any(p['distance']!=d for p in parameters))

def ffmpeg_binary():
    explicit=os.environ.get('DEMO_FFMPEG')
    if explicit:
        if not Path(explicit).is_file():raise ValueError('DEMO_FFMPEG does not name a file')
        return explicit
    system=shutil.which('ffmpeg')
    if system:return system
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        from media import FFMPEG
        if FFMPEG.is_file():return str(FFMPEG)
    raise ValueError('Video export needs ffmpeg; set DEMO_FFMPEG. PNG export is still available.')

def video_files(folder,encoder):
    frames=sorted((folder/'frames').glob('frame_*_image.png'))
    receipts=[]
    for suffix,options in [('mkv',['-c:v','ffv1','-level','3','-pix_fmt','bgr0']),
                           ('mp4',['-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart'])]:
        target=folder/('animation.'+suffix)
        command=[encoder,'-nostdin','-v','error','-threads','1','-filter_threads','1','-framerate',str(FPS),
                 '-i',str(folder/'frames/frame_%03d_image.png'),*options,'-threads','1','-y',str(target)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=90)
        record=dict(encode_command=command,encode_returncode=result.returncode,encode_stderr=result.stderr)
        receipts.append(record);js(folder/'VIDEO_RECEIPTS.json',receipts)
        result.check_returncode()
        command=[encoder,'-nostdin','-v','error','-threads','1','-i',str(target),'-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
        result=subprocess.run(command,capture_output=True,timeout=90)
        record.update(decode_command=command,decode_returncode=result.returncode,decode_stderr=result.stderr.decode(errors='replace'))
        js(folder/'VIDEO_RECEIPTS.json',receipts);result.check_returncode()
        raw=np.frombuffer(result.stdout,np.uint8).reshape(-1,SIZE,SIZE,3)
        if len(raw)!=len(frames):raise ValueError('video frame count mismatch')
        exact=[bool(np.array_equal(a,np.asarray(Image.open(f).convert('RGB')))) for a,f in zip(raw,frames)]
        if suffix=='mkv' and not all(exact):raise ValueError('lossless video differs from rendered frames')
        record.update(file=target.name,sha256=sha(target),decoded_frames=len(raw),all_frames_exact=all(exact),
            claim='lossless RGB exact' if suffix=='mkv' else 'lossy viewing copy; full decode/count only')
        js(folder/'VIDEO_RECEIPTS.json',receipts)
    return receipts

def file_hashes(folder):
    return {str(p.relative_to(folder)):sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file()}

def export(asset,output,kind,values,selected_region=None,example_metadata=None):
    start=time.monotonic()
    mesh,_,meta=load_asset(asset)
    cameras,framing=trajectory(mesh,values,kind)
    encoder=ffmpeg_binary() if kind!='image' else None
    output=new_output(output)
    try:
        snapshot=output/'asset';snapshot.mkdir()
        for p in Path(asset).iterdir():
            if p.is_file():shutil.copy2(p,snapshot/p.name)
        meta['viewer_camera']=camera_values(values)
        if selected_region is not None:meta['selected_region']=int(selected_region)
        if example_metadata is not None:meta['demo_example']=example_metadata
        js(snapshot/'asset.json',meta)
        # Reload the snapshot; source edits cannot affect any subsequent frame.
        mesh,strokes,meta=load_asset(snapshot)
        assets=file_hashes(snapshot)
        js(output/'CAMERAS.json',dict(schema='presentation_cameras_v1',kind=kind,width=SIZE,height=SIZE,fps=FPS,
                                     cameras=cameras,framing=framing))
        folder=output/'frames';folder.mkdir();rows=[]
        for i,c in enumerate(cameras):
            if time.monotonic()-start>240:raise TimeoutError('presentation rendering exceeded 240 seconds')
            rows.append(save_frame(folder,f'frame_{i:03d}',mesh,strokes,meta,c))
        if kind!='image' and not all(r['bounds']['all_proxy_vertices_inside'] for r in rows):
            raise ValueError('motion export did not fit the complete saved proxy')
        contact(output/'contact_sheet.png',[(f'{kind} {i:02d}',Image.open(folder/f'frame_{i:03d}_image.png')) for i in range(len(rows))],
                cols=min(4,len(rows)),size=320,title=meta['scene'].title()+' | fixed saved paths | all exported frames')
        videos=video_files(output,encoder) if encoder else []
        if assets!=file_hashes(snapshot):raise ValueError('snapshot changed while exporting')
        receipt=dict(schema='partwise_presentation_v1',execution_state='completed',created_utc=now(),scene=meta['scene'],
            kind=kind,source_asset_sha256=sha(Path(asset)/'asset.json'),asset_files=assets,original_model=meta['original'],
            cameras_sha256=sha(output/'CAMERAS.json'),frame_count=len(rows),frames=rows,
            frame_png_sha256=[sha(folder/f'frame_{i:03d}_image.png') for i in range(len(rows))],
            all_proxy_vertices_inside=all(r['bounds']['all_proxy_vertices_inside'] for r in rows),
            videos=videos,seconds=time.monotonic()-start,paths_regenerated=False,display=meta.get('display'),
            scope='Saved model-derived proxy and authored regions; finite frames, not full temporal or independent geometry certification.')
        js(output/'PRESENTATION.json',receipt)
        (output/'README.txt').write_text('Saved presentation: asset/ + CAMERAS.json + actual frames/.\n'
            'animation.mp4 is a lossy viewing copy; animation.mkv is verified lossless.\n'
            'Replay after extraction using the demo package:\n'
            './run.sh replay --scene '+meta['scene']+' --bundle /absolute/path/to/extracted/presentation\n'
            'Exports preserve fixed 3D paths; view contours are computed per camera.\n'
            'Proxy defects and authored region provenance are unchanged.\n')
        js(output/'MANIFEST.json',dict(schema='presentation_files_v1',files=file_hashes(output)))
        archive=output/'presentation.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(output.rglob('*')):
                if p.is_file() and p!=archive:z.write(p,p.relative_to(output))
        return receipt
    except Exception as exc:
        js(output/'FAILURE.json',dict(execution_state='engineering_invalid',error_type=type(exc).__name__,error=str(exc),
                                     seconds=time.monotonic()-start,partial_outputs_retained=True))
        raise

def replay(bundle,output):
    bundle=Path(bundle).resolve();manifest=json.loads((bundle/'MANIFEST.json').read_text())
    for name,digest in manifest['files'].items():
        file=(bundle/name).resolve()
        if bundle not in file.parents or not file.is_file() or sha(file)!=digest:
            raise ValueError('presentation checksum mismatch: '+name)
    receipt=json.loads((bundle/'PRESENTATION.json').read_text())
    schedule=json.loads((bundle/'CAMERAS.json').read_text())
    if not 1<=len(schedule['cameras'])<=12 or len(schedule['cameras'])!=receipt['frame_count']:
        raise ValueError('invalid presentation frame count')
    if any(c['width']!=SIZE or c['height']!=SIZE for c in schedule['cameras']):raise ValueError('invalid presentation resolution')
    mesh,strokes,meta=load_asset(bundle/'asset');output=new_output(output);rows=[]
    for i,c in enumerate(schedule['cameras']):
        row=save_frame(output,f'frame_{i:03d}',mesh,strokes,meta,c)
        row['png_exact']=sha(output/f'frame_{i:03d}_image.png')==receipt['frame_png_sha256'][i]
        with np.load(bundle/f'frames/frame_{i:03d}_arrays.npz') as before,np.load(output/f'frame_{i:03d}_arrays.npz') as after:
            row['all_arrays_exact']=set(before.files)==set(after.files) and all(np.array_equal(before[k],after[k]) for k in before.files)
        rows.append(row)
    result=dict(scene=meta['scene'],frame_count=len(rows),all_png_exact=all(r['png_exact'] for r in rows),
        all_arrays_exact=all(r['all_arrays_exact'] for r in rows),frames=rows,cold_loaded=True)
    js(output/'REPLAY.json',result)
    if not result['all_png_exact'] or not result['all_arrays_exact']:raise ValueError('cold replay differs')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['export','replay'])
    p.add_argument('--asset',type=Path);p.add_argument('--bundle',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--kind',choices=KINDS,default='orbit')
    for key in ('azimuth','elevation','distance'):p.add_argument('--'+key,type=float)
    a=p.parse_args()
    if a.command=='replay':
        if not a.bundle:p.error('replay requires --bundle')
        result=replay(a.bundle,a.output)
    else:
        if not a.asset:p.error('export requires --asset')
        meta=json.loads((a.asset/'asset.json').read_text());values=dict(meta.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)))
        values.update({key:getattr(a,key) for key in ('azimuth','elevation','distance') if getattr(a,key) is not None})
        result=export(a.asset,a.output,a.kind,values,meta.get('selected_region'))
    print(json.dumps({k:result[k] for k in ('scene','frame_count')}),flush=True)

if __name__=='__main__':main()
