"""Audit all rendered/reused frames and make lossless, fully decoded APNG media."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from linked_asset import npz
from motion import load_trajectory,transition_counts
from run_motion import verify_unit

def resolve(root,sequence,index):
    p=root/sequence/f'{index:03d}'
    if (p/'REUSE.json').exists():
        reuse=json.loads((p/'REUSE.json').read_text());p=root/reuse['source']
        assert sha(p/'RENDER_RECEIPT.json')==reuse['receipt_sha256']
    return p

def label_panel(paths,labels):
    images=[Image.open(p).convert('RGB') for p in paths]
    w,h=images[0].size;out=Image.new('RGB',(w*len(images),h+28),'white');d=ImageDraw.Draw(out)
    for i,(im,label) in enumerate(zip(images,labels)):
        out.paste(im,(i*w,28));d.text((i*w+5,6),label,fill='black')
    return out

def sheet(images,labels,cols,thumb=192):
    h=thumb+24;out=Image.new('RGB',(cols*thumb,((len(images)+cols-1)//cols)*h),'white');draw=ImageDraw.Draw(out)
    for i,(im,label) in enumerate(zip(images,labels)):
        x=(i%cols)*thumb;y=(i//cols)*h;im=im.copy();im.thumbnail((thumb,thumb));out.paste(im,(x,y+24));draw.text((x+3,y+4),label,fill='black')
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);a=p.parse_args();u=a.unit.resolve();verify_unit(u)
    plan=load_trajectory(u/'delivery/TRAJECTORY.json');samples=json.loads((u/'delivery/SAMPLES.json').read_text())
    out=runtime.configure_output(u/'media');root=u/'renders';all_stats={};all_frames=[];media={};unique={};events=[]
    for sequence in ('orbit','zoom'):
        rows=plan[sequence];panels=[];hybrids=[];observed=[];receipts=[];frame_records=[]
        directory=out/(sequence+'_frames');directory.mkdir()
        for row in rows:
            i=row['index'];path=resolve(root,sequence,i);receipt=json.loads((path/'RENDER_RECEIPT.json').read_text())
            assert receipt['camera']==row['camera']
            if str(path) not in unique:
                for name,h in receipt['files'].items():assert sha(path/name)==h
                frames=npz(path/'FRAME.npz');obs=npz(path/'OBSERVATIONS.npz')
                assert np.isfinite(frames['hybrid']).all()
                assert np.max(np.abs(frames['paper']-(1-.05*frames['source_alpha'][:,:,None])))<1e-6
                png_checks=0
                for key in ('source','paper','support','hybrid','proxy','combined_ink','seat_ink','seat_linked_ink','other_ink','contour'):
                    with Image.open(path/(key+'.png')) as im:
                        im.load();actual=np.asarray(im.convert('RGB'))
                    v=frames[key] if key in ('source','paper','support','hybrid','proxy') else 1-frames[key]
                    if v.ndim==2:v=np.repeat(v[:,:,None],3,axis=2)
                    expected=np.uint8(np.clip(v,0,1)*255+.5);np.testing.assert_array_equal(actual,expected);png_checks+=1
                assert obs['own_pre'].shape==(12,384,384)
                for j,key in enumerate(samples['selected_paths']):
                    expected=obs['own_pre'][j]*frames['support'] if key.startswith('4:') else obs['own_pre'][j]
                    np.testing.assert_array_equal(obs['own_post'][j],expected)
                unique[str(path)]=dict(png_checks=png_checks,receipt_sha256=sha(path/'RENDER_RECEIPT.json'))
            obs=npz(path/'OBSERVATIONS.npz');observed.append({k:obs[k] for k in ('uv','status','pre','post')});receipts.append(receipt)
            panel=label_panel([path/'hybrid.png',path/'proxy.png'],[f'{sequence} {i:03d} | linked whole Chair',f'Conventional proxy | az {row["azimuth"]:g}, d {row["distance"]:g}'])
            panel.save(directory/f'{i:03d}.png');panels.append(panel);hybrids.append(Image.open(path/'hybrid.png').convert('RGB'))
            record=dict(sequence=sequence,index=i,time_seconds=row['time_seconds'],camera=row['camera'],exposure=row['exposure'],
                actual_result=str(path.relative_to(u)),reuse=path!=root/sequence/f'{i:03d}',receipt_sha256=sha(path/'RENDER_RECEIPT.json'),
                panel_sha256=sha(directory/f'{i:03d}.png'))
            frame_records.append(record);all_frames.append(record)
        durations=[round((i+1)*1000/12)-round(i*1000/12) for i in range(len(panels))]
        movie=out/(sequence+'.png')
        panels[0].save(movie,format='PNG',save_all=True,append_images=panels[1:],duration=durations,loop=1,disposal=0,blend=0)
        decoded=[]
        with Image.open(movie) as animation:
            assert animation.n_frames==len(panels),(animation.n_frames,len(panels))
            for i,panel in enumerate(panels):
                animation.seek(i);decoded_image=animation.convert('RGB');decoded_image.load()
                np.testing.assert_array_equal(np.asarray(decoded_image),np.asarray(panel))
                decoded.append(dict(index=i,duration_ms=animation.info.get('duration'),pixel_sha256=hashlib.sha256(decoded_image.tobytes()).hexdigest()))
        media[sequence]=dict(file=str(movie.relative_to(u)),sha256=sha(movie),frames=len(panels),nominal_fps=12,
            actual_durations_ms=durations,all_frames_decoded_equal_PNG=True,decoded=decoded,scope='Lossless APNG; 83/84ms quantization of12fps, no interpolation')
        sheet(hybrids,[f'{sequence} {r["index"]:03d} | {r["azimuth"]:g}/{r["distance"]:g}' for r in rows],8 if sequence=='orbit' else 5,192 if sequence=='orbit' else 256).save(out/(sequence+'_CONTACT.png'))
        stats=dict(frames=len(rows),anchors_per_frame=len(samples['anchors']),status_counts={},transitions_pre={},transitions_post={},
            visible_samples_without_pre=0,visible_samples_without_post=0,all_proxy_vertices_inside=all(r['bounds']['all_proxy_vertices_inside'] for r in receipts),
            frame_metrics=[dict(index=i,**r['metrics'],bounds=r['bounds']) for i,r in enumerate(receipts)])
        for obs in observed:
            for name,count in zip(*np.unique(obs['status'],return_counts=True)):stats['status_counts'][str(name)]=stats['status_counts'].get(str(name),0)+int(count)
            stats['visible_samples_without_pre']+=int(((obs['status']=='visible')&(obs['pre']<=1/255)).sum())
            stats['visible_samples_without_post']+=int(((obs['status']=='visible')&(obs['post']<=1/255)).sum())
        for i,(before,after) in enumerate(zip(observed,observed[1:])):
            for layer in ('pre','post'):
                counts=transition_counts(before['status'],after['status'],before[layer],after[layer])
                for key,value in counts.items():stats['transitions_'+layer][key]=stats['transitions_'+layer].get(key,0)+value
                joint=(before['status']=='visible')&(after['status']=='visible')
                lost=joint&(before[layer]>1/255)&(after[layer]<=1/255)
                gained=joint&(before[layer]<=1/255)&(after[layer]>1/255)
                for j in np.flatnonzero(lost|gained):events.append(dict(sequence=sequence,frame_before=i,frame_after=i+1,layer=layer,
                    kind='dropout' if lost[j] else 'reappearance',sample_index=int(j),anchor=samples['anchors'][j],
                    intensity_before=float(before[layer][j]),intensity_after=float(after[layer][j])))
        all_stats[sequence]=stats
        js(out/(sequence+'_FRAME_INDEX.json'),frame_records)
    rows=[]
    for sequence,index in [('orbit',0),('orbit',30),('orbit',60),('zoom',10)]:
        path=resolve(root,sequence,index)
        rows.append(label_panel([path/(n+'.png') for n in ('source','paper','combined_ink','hybrid','proxy')],
            [f'{sequence} {index:03d} | Original GS','Global paper','Combined ink','Actual linked hybrid','Conventional proxy']))
    canvas=Image.new('RGB',(rows[0].width,sum(x.height for x in rows)),'white');y=0
    for row in rows:canvas.paste(row,(0,y));y+=row.height
    canvas.save(out/'WHOLE_LAYERS.png')
    # Every event is retained; first few distinct adjacent pairs are displayed, not fitted.
    pairs=[]
    for event in events:
        key=(event['sequence'],event['frame_before'])
        if key not in pairs:pairs.append(key)
    for n,(sequence,i) in enumerate(pairs[:8]):
        paths=[resolve(root,sequence,k)/'hybrid.png' for k in (i,i+1)]
        label_panel(paths,[f'{sequence} {i:03d} | before event',f'{sequence} {i+1:03d} | after event']).save(out/f'EVENT_{n:02d}.png')
    js(u/'TEMPORAL.json',dict(scope='Descriptive sampled own-ink observations, proxy visibility not physical GT; all exclusions retained',sequences=all_stats,events=events))
    js(u/'FRAME_INDEX.json',all_frames);js(u/'MEDIA_AUDIT.json',dict(media=media,unique_actual_cameras=len(unique),png_array_checks=sum(x['png_checks'] for x in unique.values()),unique_payloads=unique,remote_validation='not performed'))
    verify_unit(u)
    print(json.dumps(dict(unique_actual_cameras=len(unique),media_frames=len(all_frames),events=len(events),
        summary={k:{n:v for n,v in s.items() if n!='frame_metrics'} for k,s in all_stats.items()})),flush=True)
if __name__=='__main__':main()
