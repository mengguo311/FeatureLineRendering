"""Scene-neutral real-model preparation, source rendering and diagnostics."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json,time,zipfile,subprocess,sys
import numpy as np
from PIL import Image
from geometry import resize_camera,ray_surface,depth_valid,region_ids
from demo import create,edit,load_asset,save_frame

def run(unit,phase):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    if phase=='prepare':
        create(unit,unit/'assets/baseline',p['scene'])
        edit(unit/'assets/baseline',unit/'assets/edited',2,dict(angle=95.))
        mesh,paths,meta=load_asset(unit/'assets/baseline')
        out=unit/'renders/first';out.mkdir(parents=True)
        save_frame(out,'frame_000',mesh,paths,meta,resize_camera(meta['cameras'][0],512))
    elif phase=='source':
        import model_adapter as adapter
        adapter.LIB_PATH=unit/'build/libsource.so'
        t=time.monotonic();a=adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
        out=unit/'source_model';out.mkdir()
        js(out/'MODEL_IMPORT.json',dict(source=p['original'],audit=a['audit'],seconds=time.monotonic()-t))
        rows=[]
        for i,c in enumerate(p['static_cameras']):
            c=resize_camera(c,512);t=time.monotonic();r=adapter.render_source(a,c)
            np.savez_compressed(out/f'frame_{i:03d}.npz',**r)
            Image.fromarray(np.uint8(np.clip(r['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
            rows.append(dict(camera=c,seconds=time.monotonic()-t));print(c['view'],flush=True)
        js(out/'SOURCE_RENDER.json',dict(frames=rows,source_model_sha256=p['original']['sha256'],
          scope='actual frozen original Gaussians; no hatch or prior ink; not independent geometry truth'))
    elif phase=='diagnostics':
        mesh,paths,meta=load_asset(unit/'assets/baseline')
        np.testing.assert_array_equal(mesh['regions'],region_ids(mesh['tri'].mean(1),p['region_rule']['cuts']))
        rows=[]
        for i,c in enumerate(p['static_cameras']):
            c=resize_camera(c,512);z,_,labels,_=ray_surface(mesh,c,1)
            with np.load(unit/f'source_model/frame_{i:03d}.npz') as f:
                source={k:f[k] for k in f.files}
            valid=depth_valid(source['median_camera_z'],source['alpha'],source['center_depth_proxy'])
            hit=np.isfinite(z);common=hit&valid;src=source['alpha']>=.5
            error=np.abs(z[common]-source['median_camera_z'][common])
            with np.load(unit/f'renders/static_baseline/frame_{i:03d}_arrays.npz') as f:
                coverage={str(r):dict(visible_pixels=int((f['regions']==r).sum()),
                  hatch_pixels=int(((f['regions']==r)&(f['hatch']>.1)).sum()),ink=float(f[f'layer_{r}'].sum())) for r in (1,2,3)}
            rows.append(dict(view=c['view'],source_alpha_proxy_iou=float((hit&src).sum()/max(1,(hit|src).sum())),
              qualified_source_pixels=int(valid.sum()),common_depth_pixels=int(common.sum()),
              qualified_source_missing_proxy=int((valid&~hit).sum()),
              mean_depth_residual=float(error.mean()) if len(error) else None,
              p95_depth_residual=float(np.quantile(error,.95)) if len(error) else None,region_coverage=coverage))
        js(unit/'metrics/SOURCE_DIAGNOSTICS.json',dict(views=rows,region_rule_verified=True,
          scope='same-model depth estimate, same integer pixel rays; not independent truth; no accuracy improvement claim'))
        print(json.dumps(rows),flush=True)
    elif phase=='export':
        out=unit/'exported_reload';out.mkdir()
        with zipfile.ZipFile(unit/'metrics/viewer_export.zip') as z:
            assert all(Path(name).name==name for name in z.namelist())
            z.extractall(out/'asset')
        camera=json.loads((unit/'viewer_smoke/CURRENT.json').read_text())['camera']
        command=[sys.executable,str(Path(__file__).with_name('demo.py')),'render','--scene',p['scene'],
          '--asset',str(out/'asset'),'--output',str(out/'preview')]
        for k,v in camera.items():command+=['--'+k,str(v)]
        result=subprocess.run(command,timeout=120);result.check_returncode()
        from validate_replays import compare
        rows=[compare(unit/f'viewer_smoke/view_0006/frame_000_{s}',out/f'preview/frame_000_{s}') for s in ['image.png','arrays.npz']]
        js(unit/'metrics/EXPORT_REPLAY.json',dict(status='PASS',command=command,returncode=result.returncode,
           exact_files=rows,server_already_stopped=True,cold_CLI_process=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('phase',choices=['prepare','source','diagnostics','export']);a=p.parse_args();run(a.unit,a.phase)
