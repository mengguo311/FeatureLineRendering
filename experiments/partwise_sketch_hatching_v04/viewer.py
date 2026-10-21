"""Local, serial CPU editor. No external services or browser libraries."""
import runtime
from runtime import js,now,output_guard
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
import argparse
import io
import json
import time
import zipfile
import numpy as np
from PIL import Image
from urllib.parse import urlsplit
from demo import load_asset,edit,new_output,save_frame
from geometry import orbit_camera,ray_surface
from region_tools import select_faces,selection_summary,author_face_selection
from screen_selection import visible_faces,pick_region
from selection_draft import SelectionDraft

class Editor:
    def __init__(self,asset,output):
        self.asset=Path(asset);self.output=new_output(output);self.revision=0
        self.pending=None;self.preview_count=0;self.history=[];self.draft=None
        meta=json.loads((self.asset/'asset.json').read_text())
        self.selected_region=meta.get('selected_region',2)
        self.record=self.draw(meta.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)))

    def draw(self,values):
        t=time.monotonic();mesh,strokes,meta=load_asset(self.asset)
        camera=orbit_camera(values['azimuth'],values['elevation'],values['distance'])
        folder=self.output/f'view_{self.revision:04d}';folder.mkdir()
        save_frame(folder,'frame_000',mesh,strokes,meta,camera)
        record=dict(scene=meta['scene'],regions=meta['regions'],styles=meta['styles'],revision=self.revision,seconds=time.monotonic()-t,
                    images={k:f'/image/view_{self.revision:04d}/frame_000_{k}.png' for k in ('image','region_rgb','proxy')},
                    asset=str(self.asset),camera={k:values[k] for k in ('azimuth','elevation','distance')},
                    mesh_bounds=np.concatenate([mesh['vertices'].min(0),mesh['vertices'].max(0)]).tolist(),
                    manual_regions=len(meta.get('region_history',[])),can_undo=bool(self.history),
                    selected_region=self.selected_region,draft=None)
        js(self.output/'CURRENT.json',record)
        return record

    def apply(self,values):
        if self.draft is not None and self.draft.steps:
            raise ValueError('save or clear the selection draft before changing style')
        region=int(values['region'])
        if str(region) not in self.record['regions']:raise ValueError('unknown style region')
        for k,(lo,hi) in dict(azimuth=(-360,360),elevation=(5,75),distance=(3.8,6)).items():
            values[k]=float(values[k])
            if not lo<=values[k]<=hi:raise ValueError('camera value outside demo range')
        style={k:float(values[k]) for k in ('angle','spacing','length','width')}
        from hatching import validate_style
        validate_style(style)
        destination=self.output/f'asset_{self.revision+1:04d}'
        edit(self.asset,destination,region,style)
        self.history.append((self.asset,self.record['camera']))
        self.revision+=1;self.pending=None;self.draft=None;self.selected_region=region
        meta=json.loads((destination/'asset.json').read_text())
        meta['viewer_camera']={k:values[k] for k in ('azimuth','elevation','distance')}
        meta['selected_region']=region
        js(destination/'asset.json',meta)
        self.asset=destination;self.record=self.draw(values)
        return self.record

    def navigate(self,values):
        """Camera-only navigation never regenerates or copies a stroke asset."""
        self.check_revision(values)
        camera={}
        for k,(lo,hi) in dict(azimuth=(-360,360),elevation=(5,75),distance=(3.8,6)).items():
            camera[k]=float(values[k])
            if not lo<=camera[k]<=hi:raise ValueError('camera value outside demo range')
        self.revision+=1;self.pending=None
        self.record=self.draw(camera)
        if self.draft is not None:self.publish_draft()
        return self.record

    def check_revision(self,values):
        if int(values['revision'])!=self.revision:raise ValueError('view changed; preview again')

    def selection_overlay(self,mesh,ids):
        camera=orbit_camera(**self.record['camera'])
        _,face,_,_=ray_surface(mesh,camera,2)
        selected=np.isin(face,ids).reshape(512,2,512,2).mean((1,3))
        proxy=np.asarray(Image.open(self.output/f'view_{self.revision:04d}/frame_000_proxy.png').convert('RGB'),float)/255
        overlay=proxy*(1-.75*selected[:,:,None])+np.array([.85,.16,.55])*(.75*selected[:,:,None])
        self.preview_count+=1;filename=f'selection_preview_{self.preview_count:04d}.png'
        Image.fromarray(np.uint8(overlay*255+.5)).save(self.output/filename)
        return dict(visible_pixels=float(selected.sum()),image='/image/'+filename)

    def publish_draft(self):
        summary=self.draft.summary()
        overlay=self.selection_overlay(self.draft.mesh,self.draft.face_ids)
        token=f'{self.revision}:{self.preview_count}' if summary['can_commit'] else None
        self.pending=(dict(revision=self.revision,source_region=self.draft.source_region,
                           face_ids=self.draft.face_ids.copy(),selection=self.draft.provenance(),token=token)
                      if token else None)
        self.record['draft']=dict(**summary,**overlay,token=token)
        js(self.output/'DRAFT.json',dict(mesh_sha256=self.draft.mesh_sha256,
            face_ids=self.draft.face_ids.tolist(),**self.record['draft']))
        js(self.output/'CURRENT.json',self.record)
        return self.record['draft']

    def draft_action(self,values):
        self.check_revision(values)
        action=values['action']
        if action=='clear':
            self.draft=None;self.pending=None;self.record['draft']=None
            js(self.output/'DRAFT.json',dict(cleared=True,revision=self.revision))
            js(self.output/'CURRENT.json',self.record)
        elif action=='undo':
            if self.draft is None:raise ValueError('no selection step to undo')
            self.draft.undo();self.publish_draft()
        else:raise ValueError('draft action must be clear or undo')
        return self.record

    def preview_selection(self,values):
        self.check_revision(values)
        mesh,_,meta=load_asset(self.asset);source=int(values['source_region'])
        camera=orbit_camera(**self.record['camera'])
        mode=values.get('mode','box')
        if mode=='visible':
            if self.draft is not None and self.draft.source_region!=source:
                raise ValueError('clear the current draft before changing source region')
            draft=self.draft if self.draft is not None else SelectionDraft(mesh,meta['mesh_sha256'],source)
            draft.apply(camera,values['rectangle'],values.get('operation','replace'))
            self.draft=draft
            return self.publish_draft()
        elif mode=='box':
            if self.draft is not None and self.draft.steps:raise ValueError('clear the visible selection draft before using a world box')
            ids=select_faces(mesh,values['bounds'],source)
            summary=selection_summary(mesh,values['bounds'],source)
            provenance=dict(operation='manual_box_split',bounds=summary['bounds'],rule=summary['rule'])
        else:raise ValueError('unknown selection mode')
        overlay=self.selection_overlay(mesh,ids)
        self.pending=dict(revision=self.revision,source_region=source,face_ids=ids,selection=provenance,
                          token=f'{self.revision}:{self.preview_count}')
        return dict(**summary,**overlay,token=self.pending['token'])

    def pick(self,values):
        if int(values['revision'])!=self.revision:raise ValueError('view changed; pick again')
        mesh,_,_=load_asset(self.asset)
        hit=pick_region(mesh,orbit_camera(**self.record['camera']),values['point'])
        self.selected_region=hit['region'];self.record['selected_region']=hit['region']
        js(self.output/'CURRENT.json',self.record)
        return hit

    def author(self,values):
        if self.pending is None or values.get('token')!=self.pending['token'] or self.pending['revision']!=self.revision:
            raise ValueError('selection preview expired; preview the box again')
        pending=self.pending;destination=self.output/f'asset_{self.revision+1:04d}'
        result=author_face_selection(self.asset,destination,pending['face_ids'],pending['source_region'],values['name'],pending['selection'])
        self.history.append((self.asset,self.record['camera']))
        self.revision+=1;self.pending=None;self.draft=None;self.selected_region=result['new_region']
        meta=json.loads((destination/'asset.json').read_text());meta['viewer_camera']=self.record['camera']
        meta['selected_region']=result['new_region']
        js(destination/'asset.json',meta)
        self.asset=destination;self.record=self.draw(self.record['camera'])
        return self.record

    def undo(self):
        if self.draft is not None and self.draft.steps:raise ValueError('save or clear the selection draft before undoing an asset edit')
        if not self.history:raise ValueError('no earlier edit in this session')
        self.asset,camera=self.history.pop();self.revision+=1;self.pending=None;self.draft=None
        self.selected_region=json.loads((self.asset/'asset.json').read_text()).get('selected_region',2)
        self.record=self.draw(camera)
        return self.record

class Handler(BaseHTTPRequestHandler):
    editor=None
    def send(self,data,kind='application/json',status=200):
        if isinstance(data,dict):data=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/':self.send(Path(__file__).with_name('viewer.html').read_bytes(),'text/html; charset=utf-8')
        elif path=='/state':self.send(self.editor.record)
        elif path=='/export':
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
                for p in sorted(self.editor.asset.iterdir()):
                    if p.name=='asset.json':
                        meta=json.loads(p.read_text());meta['viewer_camera']=self.editor.record['camera']
                        meta['selected_region']=self.editor.record['selected_region']
                        z.writestr('asset.json',json.dumps(meta,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
                    elif p.is_file():z.write(p,p.name)
            self.send(buf.getvalue(),'application/zip')
        elif path.startswith('/image/'):
            target=(self.editor.output/path[len('/image/'):]).resolve()
            if self.editor.output not in target.parents or target.suffix!='.png' or not target.is_file():
                self.send({'error':'not found'},status=404)
            else:self.send(target.read_bytes(),'image/png')
        else:self.send({'error':'not found'},status=404)
    def do_POST(self):
        path=urlsplit(self.path).path
        if path not in ('/render','/selection','/author','/undo','/pick','/view','/draft'):return self.send({'error':'not found'},status=404)
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=4096:raise ValueError('invalid request length')
            values=json.loads(self.rfile.read(length))
            result=(self.editor.apply(values) if path=='/render' else self.editor.preview_selection(values) if path=='/selection'
                    else self.editor.navigate(values) if path=='/view' else self.editor.draft_action(values) if path=='/draft'
                    else self.editor.author(values) if path=='/author' else self.editor.pick(values) if path=='/pick' else self.editor.undo())
            self.send(result)
        except (ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)},status=422)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--asset',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--port',type=int,default=8765);a=p.parse_args()
    Handler.editor=Editor(a.asset,a.output)
    server=HTTPServer(('127.0.0.1',a.port),Handler)
    js(a.output/'SERVER.json',dict(port=server.server_address[1],host='127.0.0.1',utc=now()))
    print(f'Open http://127.0.0.1:{server.server_address[1]}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
