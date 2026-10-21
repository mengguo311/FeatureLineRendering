"""Serial real-model execution of the frozen unit002 candidate and controls."""
import runtime
from runtime import js, now, sha, output_guard
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import time
import numpy as np
from PIL import Image
from demo import load_asset, create, edit, save_frame
from geometry import resize_camera


def run(unit, phase):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    if phase=='prepare':
        from refine_proxy import build
        build(unit)
        old=Path(p['previous_unit'])/'assets/baseline'
        shutil.copytree(old,unit/'assets/original')
        meta=json.loads((unit/'assets/original/asset.json').read_text())
        meta.update(cameras=p['static_cameras'],orbit=p['orbit'],zoom=p['zoom'])
        meta['comparison_metadata_update']='cameras only; parent mesh and paths byte-exact'
        js(unit/'assets/original/asset.json',meta)
        create(unit,unit/'assets/baseline',p['scene'])
        edit(unit/'assets/baseline',unit/'assets/edited',2,dict(angle=95.))
        shutil.copy2(Path(p['previous_unit'])/'DEPENDENCIES.json',unit/'DEPENDENCIES.json')
    elif phase=='source':
        import model_adapter as adapter
        builddir=unit/'build';builddir.mkdir(exist_ok=True)
        command=['g++','-O2','-shared','-fPIC',str(Path(__file__).with_name('source_ewa.cpp')),
                 '-o',str(builddir/'libsource.so')]
        r=subprocess.run(command,capture_output=True,text=True,timeout=120)
        js(builddir/'COMPILE.json',dict(command=command,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        r.check_returncode();adapter.LIB_PATH=builddir/'libsource.so'
        t=time.monotonic();source=adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
        out=unit/'source_model';out.mkdir()
        js(out/'MODEL_IMPORT.json',dict(utc=now(),source_sha256=p['original']['sha256'],
              source_path=p['original']['original_ply'],audit=source['audit'],seconds=time.monotonic()-t))
        rows=[]
        for i,c in enumerate(p['static_cameras']):
            c=resize_camera(c,512);t=time.monotonic();a=adapter.render_source(source,c)
            np.savez_compressed(out/f'frame_{i:03d}.npz',**a)
            Image.fromarray(np.uint8(np.clip(a['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
            row=dict(camera=c,seconds=time.monotonic()-t);rows.append(row)
            print(json.dumps(row),flush=True)
        js(out/'SOURCE_RENDER.json',dict(utc=now(),original_model_sha256=p['original']['sha256'],frames=rows,
                 scope='actual original learned Gaussians, no hatch contribution; estimated depth is not GT'))
        shutil.copy2(out/'frame_000_rgb.png',unit/'proxy/source_train_r_32.png')
    else:
        asset={'original':'original','baseline':'baseline','edited':'edited','orbit':'edited','zoom':'edited'}[phase]
        mesh,strokes,meta=load_asset(unit/'assets'/asset)
        camera_key=phase if phase in ('orbit','zoom') else 'static_cameras'
        out=unit/'renders'/({'original':'static_original','baseline':'static_baseline',
                           'edited':'static_edited'}.get(phase,phase))
        out.mkdir(parents=True)
        records=[]
        for i,c in enumerate(p[camera_key]):
            records.append(save_frame(out,f'frame_{i:03d}',mesh,strokes,meta,resize_camera(c,512)))
        js(out/'RENDER_RECEIPT.json',dict(utc=now(),asset_sha256=sha(unit/'assets'/asset/'asset.json'),
                                        frames=records,frame_count=len(records),cold_loaded=True))
        if phase=='baseline':
            first=unit/'renders/first';first.mkdir()
            for path in out.glob('frame_000*'):shutil.copy2(path,first/path.name)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('phase',choices=['prepare','source','original','baseline','edited','orbit','zoom'])
    a=p.parse_args();run(a.unit,a.phase)
