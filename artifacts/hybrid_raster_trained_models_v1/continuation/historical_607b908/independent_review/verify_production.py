#!/usr/bin/env python3
"""Read-only independent actual-output verifier. Missing outputs remain failures."""
import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import traceback
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation,Slerp

from verify_experiment import (ROOT,ART,OUT,STAGE,SCENES,F,C,LOCK_SHA,PRIOR,
    canonical,sha,read,write,require,verify_seal,verify_camera_set,verify_inheritance,check_counts)
from scripts.verify_hybrid_raster_evidence_v2 import verify_native,verify_arrays
from src.hybrid_raster_io import validate_video

TART=ROOT/'artifacts'/STAGE/'transport'
TOUT=ROOT/'out'/STAGE/'transport'


def specs_for(manifest):
    result=[]
    for split,indices in [('F',F),('C',C)]:
        result += [dict(scene=manifest['scene'],split=split,key=f'{split}_{i:03d}',camera=manifest['cameras'][str(i)]) for i in indices]
    result += [dict(scene=manifest['scene'],split='arc0',key=f'arc0_{i:03d}',camera=cam) for i,cam in enumerate(manifest['arcs'][0]['frames'])]
    return result


def verify_cameras(scene):
    pre=read(TART/'PREDECLARED_CAMERAS.json');manifest=read(TART/scene/'CAMERAS.json')
    require(manifest['scene']==scene and manifest['F']==list(F) and manifest['C']==list(C),'camera manifest scene/splits differ')
    require(manifest['predeclared_sha256']==sha(TART/'PREDECLARED_CAMERAS.json'),'predeclared linkage differs')
    declared=pre['scenes'][scene];meta_record=declared['metadata']
    require(Path(meta_record['path']).name=='transforms_train.json','non-TRAIN metadata')
    require(sha(meta_record['path'])==meta_record['sha256'],'TRAIN metadata hash differs')
    meta=read(meta_record['path']);fov=meta['camera_angle_x']
    require(manifest['cameras']==declared['cameras'],'F/C changed from preGPU freeze')
    for i in F+C:
        frame=meta['frames'][i]
        require(Path(frame['file_path']).as_posix() in (f'train/r_{i}',f'./train/r_{i}'),'TRAIN frame order/index mismatch')
        expected=np.linalg.inv(np.asarray(frame['transform_matrix'],np.float64)@np.diag([1.,-1.,-1.,1.]))
        require(np.array_equal(expected,np.asarray(manifest['cameras'][str(i)]['w2c'])),'TRAIN camera transform differs')
    checkpoint=manifest['checkpoint'];require(checkpoint['path']==declared['checkpoint_destination'],'checkpoint destination changed')
    require(sha(checkpoint['path'])==checkpoint['sha256'],'frozen checkpoint hash differs')
    training_lock=manifest['training_checkpoint_lock'];require(sha(training_lock['path'])==training_lock['sha256'],'checkpoint lock changed')
    # PLY is explicitly the frozen vanilla checkpoint, never a mesh asset.
    from plyfile import PlyData
    vertex=PlyData.read(checkpoint['path'])['vertex'].data
    require({'x','y','z','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3','opacity','f_dc_0','f_dc_1','f_dc_2'}<=set(vertex.dtype.names),'checkpoint is not vanilla3DGS')
    points=np.column_stack([vertex[k] for k in ('x','y','z')]).astype(np.float64)
    require(np.isfinite(points).all(),'nonfinite checkpoint positions')
    box=np.array([np.quantile(points,.001,axis=0),np.quantile(points,.999,axis=0)])
    center=box.mean(0)
    require(np.array_equal(box,np.asarray(manifest['quantile_box'])) and np.array_equal(center,np.asarray(manifest['center'])),'checkpoint eligibility center differs')
    poses=np.array([np.linalg.inv(manifest['cameras'][str(i)]['w2c']) for i in (7,33)])
    loc=poses[:,:3,3]-center;r=np.linalg.norm(loc,axis=1);u=loc/r[:,None]
    ang=np.degrees(np.arccos(np.clip(u@u.T,-1,1)));theta=np.radians(ang[0,1]);ts=np.linspace(0,1,33)
    dirs=(np.sin((1-ts)*theta)[:,None]*u[0]+np.sin(ts*theta)[:,None]*u[1])/np.sin(theta)
    radius=(1-ts)*r[0]+ts*r[1];rot=Slerp([0,1],Rotation.from_matrix(poses[:,:3,:3]))(ts).as_matrix()
    arc=manifest['arcs'][0];require(arc['endpoints']==[7,33] and len(arc['frames'])==33,'arc endpoints/count differ')
    max_error=0.
    for i,t in enumerate(ts):
        pose=np.eye(4);pose[:3,:3]=rot[i];pose[:3,3]=center+dirs[i]*radius[i]
        expected=np.linalg.inv(pose);actual=np.asarray(arc['frames'][i]['w2c'])
        max_error=max(max_error,float(np.max(np.abs(expected-actual))))
        require(np.array_equal(expected,actual) and arc['frames'][i]['t']==float(t),'inherited exact arc differs')
    specs=specs_for(manifest);result=verify_camera_set(specs,fov)
    result.update(checkpoint=checkpoint,gaussians=len(points),arc_max_abs_error=max_error,camera_manifest_sha256=sha(TART/scene/'CAMERAS.json'))
    return manifest,specs,result


def png_check(path,size):
    with Image.open(path) as im:
        require(im.format=='PNG' and im.mode=='RGB' and im.size==tuple(size),'PNG size/mode differs: '+str(path))
        im.load()  # Complete decode, not just headers.


def verify_calibration(scene,manifest,lock):
    path=TOUT/'calibration'/scene/'CALIBRATION.json';report=read(path)
    require(report['status']=='PASS','calibration not qualified')
    require(report['context']['checkpoint_sha256']==manifest['checkpoint']['sha256'],'calibration checkpoint differs')
    require(report['context']['native_build']==lock['config']['native_build'],'calibration source/binary differs')
    require(report['context']['camera_manifest_sha256']==sha(TART/scene/'CAMERAS.json'),'calibration cameras differ')
    require([r['index'] for r in report['frames']]==list(F),'calibration must cover every exact F')
    for row in report['frames']:
        require(row['camera']==manifest['cameras'][str(row['index'])] and row['camera_hash']==canonical(row['camera']),'calibration camera identity differs')
        require(row['calibration']['status']=='PASS','invalid calibration frame')
        require(sha(row['unpatched_path'])==row['unpatched_sha256'],'unpatched calibration buffer hash differs')
        errors=row['calibration']['errors'];require(set(errors)=={'rgb','alpha','depth','normal','median_depth'},'calibration field set differs')
        with np.load(row['path'],allow_pickle=False) as patched,np.load(row['unpatched_path'],allow_pickle=False) as unpatched:
            for name,error in errors.items():
                a=patched[name].astype(np.float64);b=unpatched[name].astype(np.float64)
                require(a.shape==b.shape and np.isfinite(a).all() and np.isfinite(b).all(),'invalid calibration array')
                delta=np.abs(a-b);actual={'max_abs':float(delta.max(initial=0)),'mean_abs':float(delta.mean()),'max_rel':float((delta/np.maximum(np.abs(b),1e-8)).max(initial=0))}
                require(all(error[k]==v for k,v in actual.items()),'saved calibration metric differs from buffers')
                absolute=actual['max_abs'];relative=actual['max_rel']
                tolerance=absolute<=3e-6 or (name in ('depth','median_depth') and absolute<=1e-5 and relative<=3e-6)
                require(tolerance and error['passed'] is True,'calibration error exceeds inherited tolerance')
        require(sha(row['path'])==row['sha256'],'calibrated native buffer hash differs')
    return report


def verify_frame(spec,manifest,lock,calibration):
    scene=spec['scene'];key=spec['key'];folder=TOUT/'frames'/scene/key;rawfolder=TOUT/'raw'/scene/key
    sealed=verify_seal(folder);context=sealed['context'];rawsealed=verify_seal(rawfolder,context)
    expected=dict(scene=scene,key=key,camera=spec['camera'],camera_hash=canonical(spec['camera']),
        checkpoint_sha256=manifest['checkpoint']['sha256'],camera_manifest_sha256=sha(TART/scene/'CAMERAS.json'),
        renderer_source_sha256=lock['config']['sources']['src/hybrid_raster_native.py'],
        calibration_sha256=sha(TOUT/'calibration'/scene/'CALIBRATION.json'),
        render_recipe={'SH':0,'topk':4,'background':'white','kernel_size':0},
        scientific_parameter_hash=lock['parameter_hash'],inherited_lock_sha256=LOCK_SHA,
        source_hashes=lock['config']['sources'],adapter_source_hashes={name:sha(TART/name) for name in ('adapters.py','run_transport.py')})
    require(context==expected and read(folder/'camera.json')==expected,'frame source/parameter/camera context differs')
    require(set(rawsealed['files'])=={'native.npz','camera.json','checkpoint_qualification.json'},'raw field inventory differs')
    require(read(rawfolder/'camera.json')==expected,'raw camera metadata differs')
    require(rawsealed['files']['native.npz']==sealed['files']['native.npz'],'raw/frame native bytes differ')
    qualification=read(rawfolder/'checkpoint_qualification.json')
    require(qualification['sha256']==manifest['checkpoint']['sha256'],'checkpoint qualification differs')
    require(qualification['filter_3D_applied'] is False and qualification['proxy_axis_normals_computed'] is False,'unsupported filter/normal semantics')
    native=verify_native(folder/'native.npz',(800,800),qualification['gaussians'],full_native=True)
    with np.load(folder/'native.npz',allow_pickle=False) as z:raw={k:z[k] for k in ('alpha','topk_w','normal_len','moment2','depth','rgb')}
    with np.load(folder/'responses.npz',allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
    with np.load(folder/'provenance.npz',allow_pickle=False) as z:provenance={k:z[k] for k in z.files}
    diagnostics=read(folder/'diagnostics.json')
    require(diagnostics['parameter_hash']==lock['parameter_hash'] and diagnostics['camera_hash']==expected['camera_hash'],'diagnostic configuration differs')
    require(diagnostics['native_sha256']==sealed['files']['native.npz'],'diagnostic native identity differs')
    response=verify_arrays(arrays,provenance,diagnostics,(800,800),native_raw=raw)
    import cv2
    foreground=cv2.dilate((raw['alpha']>=.08).astype(np.uint8),np.ones((3,3),np.uint8))>0
    require(np.array_equal(foreground,provenance['foreground']),'common foreground differs from native alpha')
    with np.load(folder/'typed.npz',allow_pickle=False) as z:
        for name in z.files:require(np.isfinite(z[name]).all(),'nonfinite typed field '+name)
        for name in ('q_s','q','u','ell','E_V','delta_A','delta_D','delta_N','delta_C','delta_G','E_A','E_D','E_N','E_C','E_G','L','S_L','E_T','visibility_raw','topk_mass','normal_coherence','depth_variance'):
            require(z[name].shape==(800,800),'typed field shape differs '+name)
        require(z['normalized_topk_w'].shape==(800,800,4) and z['visible_color'].shape==(800,800,3),'typed vector shape differs')
        original=z['S_L']
    require(np.array_equal(original,arrays['author_absolute']),'AUTHOR raw equation value altered')
    require(np.allclose(arrays['author_gain'],np.clip(original/lock['normalization']['author_scale'],0,1),rtol=0,atol=2e-7),'AUTHOR frozen display gain differs')
    required={'native.npz','typed.npz','responses.npz','provenance.npz','camera.json','diagnostics.json','rgb.png','line_panel.png','overlay_panel.png','matched_panel.png','response_panel.png'}
    required|={f'{arm}_{kind}.png' for arm in ('A','B','C','A_matched','B_matched','C_matched','author_absolute','author_gain') for kind in ('ink','overlay')}
    require(set(sealed['files'])==required,'full frame inventory differs')
    for name in required:
        if name.endswith('.png'):
            size=(4000,2496) if name=='response_panel.png' else ((4000,832) if name.endswith('_panel.png') else (800,800))
            png_check(folder/name,size)
    rgb=np.uint8(np.round(np.clip(raw['rgb'],0,1)*255))
    with Image.open(folder/'rgb.png') as im:require(np.array_equal(np.asarray(im),rgb),'RGB PNG differs from shared native RGB')
    for arm in ('A','B','C','A_matched','B_matched','C_matched','author_absolute','author_gain'):
        gray=np.rint(255*(1-arrays[arm])).astype(np.uint8)
        ink=np.repeat(gray[...,None],3,axis=2)
        overlay=np.rint(rgb.astype(np.float32)*(1-arrays[arm][...,None])).astype(np.uint8)
        for kind,expected_pixels in [('ink',ink),('overlay',overlay)]:
            with Image.open(folder/f'{arm}_{kind}.png') as im:require(np.array_equal(np.asarray(im),expected_pixels),'saved arm PNG differs '+arm+'/'+kind)
    return dict(passed=True,seal_sha256=sealed['seal_sha256'],raw_seal_sha256=rawsealed['seal_sha256'],files=sealed['files'],native=native,responses=response)


def mp4_atoms(path):
    result=[]
    with Path(path).open('rb') as stream:
        end=Path(path).stat().st_size
        while stream.tell()<end:
            offset=stream.tell();header=stream.read(8);require(len(header)==8,'truncated MP4 atom')
            length,kind=struct.unpack('>I4s',header)
            if length==1:length=struct.unpack('>Q',stream.read(8))[0]
            elif length==0:length=end-offset
            require(length>=8 and offset+length<=end,'invalid MP4 atom extent')
            result.append(kind.decode('ascii'));stream.seek(offset+length)
    return result


def verify_media(scene,frames,lock):
    folder=TOUT/'media'/scene;sealed=verify_seal(folder);manifest=read(folder/'MANIFEST.json')
    expected_context={'scene':scene,'camera_manifest_sha256':sha(TART/scene/'CAMERAS.json'),'frames_manifest_sha256':sha(TART/scene/'FRAMES.json'),'parameter_hash':lock['parameter_hash']}
    require(sealed['context']==expected_context,'media source-frame context differs')
    require(manifest==read(TART/scene/'MEDIA.json'),'media manifest copies differ')
    expected={name for kind in ('comparison','overlay','matched') for name in (kind,kind+'_telegram1600')}
    require(set(manifest['videos'])==expected,'native+Telegram six videos required')
    videos={}
    for name,row in manifest['videos'].items():
        path=folder/f'arc0_{name}.mp4';size=(1600,368) if name.endswith('_telegram1600') else (4000,832)
        decoded=validate_video(path,expected_frames=33,expected_size=size,require_distinct=True)
        for field in ('frames','distinct_frames','size','frame_sha256','sha256'):require(decoded[field]==row[field],'video decode differs '+name+'/'+field)
        require(row['fps']==12,'video fps differs')
        if name.endswith('_telegram1600'):
            atoms=mp4_atoms(path);require(atoms.index('moov')<atoms.index('mdat'),'Telegram faststart absent')
            import imageio_ffmpeg
            cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(path),'-f','null','-']
            probe=subprocess.run(cmd,capture_output=True,text=True)
            require(probe.returncode==0 and 'h264' in probe.stderr and 'yuv420p' in probe.stderr,'Telegram full codec decode failed')
        videos[name]=decoded
    contacts={f'{split}_{arm}_contact.png' for split in ('F','C','arc0') for arm in ('rgb','A','B','C','author_gain')}
    require(set(manifest['contacts'])==contacts,'contact sheet inventory differs')
    for name in contacts:
        arc=name.startswith('arc0_');png_check(folder/name,(2400,9152) if arc else (3200,1664))
        require(manifest['contacts'][name]['sha256']==sealed['files'][name],'contact digest differs')
    representatives={f'arc0_{i:03d}_{kind}.png' for i in (0,16,32) for kind in ('line','overlay','matched')}
    require(set(manifest['first_mid_last'])==representatives,'representative inventory differs')
    for name in representatives:
        parts=name.split('_');key='_'.join(parts[:2]);kind=parts[2].split('.')[0]
        png_check(folder/name,(4000,832));require(sealed['files'][name]==frames[key]['files'][kind+'_panel.png'],'representative differs from complete output')
    require(set(sealed['files'])==contacts|representatives|{'MANIFEST.json'}|{f'arc0_{n}.mp4' for n in expected},'media seal inventory differs')
    return dict(passed=True,seal_sha256=sealed['seal_sha256'],videos=videos,contacts=len(contacts),first_mid_last=len(representatives))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scenes',nargs='+',choices=SCENES,default=SCENES)
    parser.add_argument('--output',type=Path,default=ART/'PRODUCTION.json');args=parser.parse_args()
    require(ART in args.output.resolve().parents,'output outside independent directory')
    start=time.monotonic();report=dict(passed=False,scientific_GO=False,human_review='PENDING',scenes={},errors=[],expected_total=196,verified_total=0)
    try:report['inheritance']=verify_inheritance();lock=read(PRIOR/'out/hybrid_raster_evidence_v2/LOCK.json')
    except Exception as exc:report['errors'].append(dict(where='inheritance',error=repr(exc)));lock=None
    for scene in args.scenes:
        rows={};report['scenes'][scene]={'frames':rows}
        try:
            require(lock is not None,'inheritance failed');manifest,specs,cameras=verify_cameras(scene)
            report['scenes'][scene]['cameras']=cameras;calibration=verify_calibration(scene,manifest,lock)
            report['scenes'][scene]['calibration']={'frames':len(calibration['frames']),'status':'PASS'}
            for spec in specs:
                rows[spec['key']]=verify_frame(spec,manifest,lock,calibration);print('VERIFIED',scene,spec['key'],flush=True)
            report['scenes'][scene]['media']=verify_media(scene,rows,lock)
        except Exception as exc:report['errors'].append(dict(where=scene,error=repr(exc),traceback=traceback.format_exc()))
        report['verified_total']=sum(len(s['frames']) for s in report['scenes'].values());write(args.output,report)
    if not report['errors'] and set(args.scenes)==set(SCENES):
        check_counts({s:len(v['frames']) for s,v in report['scenes'].items()});report['passed']=True
    report['status']='PASS' if report['passed'] else 'INCOMPLETE_OR_INVALID';report['elapsed_seconds']=time.monotonic()-start
    report['scope']='All raw+typed numeric fields decoded, equations/provenance/scalar diagnostics checked, all PNG/media decoded. TRAIN metadata and explicitly frozen Gaussian checkpoint only; no source image pixels.'
    write(args.output,report);print(json.dumps({k:report[k] for k in ('passed','status','verified_total','errors')}));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
