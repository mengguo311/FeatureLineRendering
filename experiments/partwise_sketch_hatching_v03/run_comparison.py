"""One frozen display comparison; actual backend invocation for each arm/frame."""
from runtime import *
import argparse
import time
from PIL import Image
from experiments.partwise_sketch_hatching_v02 import renderer

def check_lock():
    lock=json.loads((ROOT/'SOURCE_LOCK.json').read_text())
    for path,h in lock['files'].items():
        assert sha(path)==h, f'frozen source/input changed: {path}'
    return lock

def save_render(folder,result,frame,arm,seconds):
    folder=output_path(folder/'image.png').parent
    image=np.uint8(np.rint(result['image']*255))
    Image.fromarray(image).save(folder/'image.png')
    np.savez_compressed(folder/'layers.npz',**{k:result[k] for k in ('image','hatch','contours','rings','parts','depth')})
    write_json(folder/'render.json',dict(frame=frame,arm=arm,seconds=seconds,camera=result['camera'],diagnostics=result['diagnostics'],image_sha256=sha(folder/'image.png')))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('sequence',choices=['static','orbit','zoom','isolated']); args=ap.parse_args()
    check_lock(); resources()
    protocol=json.loads((ROOT/'PROTOCOL.json').read_text())
    mesh,strokes,cfg=load_asset()
    assert cfg['renderer']['resolution']==[512,512]
    sequence=args.sequence
    target=ROOT/('isolated' if sequence=='isolated' else f'renders/{sequence}')
    if target.exists(): raise FileExistsError(target)
    target.mkdir(parents=True)
    frames=[f for f in protocol['frames'] if f['sequence']==('static' if sequence=='isolated' else sequence)]
    records=[]
    for frame in frames:
        if sequence=='isolated':
            for part in (1,2,3):
                ids=[s['id'] for s in strokes if s['part']==part]
                start=time.perf_counter()
                result=renderer.render(mesh,strokes,cfg,frame['azimuth'],frame['elevation'],frame['distance'],structure=False,selected_ids=ids)
                seconds=time.perf_counter()-start
                folder=target/frame['id']/f'part_{part}'
                save_render(folder,result,frame,dict(id=f'part_{part}',purpose='score-only isolated hatch',structure=False),seconds)
                records.append(dict(frame=frame['id'],part=part,seconds=seconds))
        else:
            for arm in protocol['arms']:
                start=time.perf_counter()
                result=renderer.render(mesh,strokes,cfg,frame['azimuth'],frame['elevation'],frame['distance'],structure=arm['structure'])
                seconds=time.perf_counter()-start
                save_render(target/frame['id']/arm['id'],result,frame,arm,seconds)
                records.append(dict(frame=frame['id'],arm=arm['id'],seconds=seconds))
        write_json(target/'PROGRESS.json',dict(completed=records,resources=resources()))
        print(json.dumps(dict(sequence=sequence,frame_done=frame['id'])),flush=True)
    write_json(target/'COMPLETE.json',dict(records=records,protocol_sha256=sha(ROOT/'PROTOCOL.json'),resources=resources()))
    status=json.loads((ROOT/'STATUS.json').read_text())
    artifacts=status['artifacts']; artifacts[sequence]=str(target/'COMPLETE.json')
    update_status(f'RENDERED_{sequence.upper()}',artifacts=artifacts)

if __name__=='__main__': main()
