"""Independent in-memory editing sessions for a portable catalog of real assets."""
import runtime
from pathlib import Path
import json,re
from demo import new_output

class SceneCatalog:
    def __init__(self,catalog,output,scene=None):
        from viewer import Editor
        self.Editor=Editor
        catalog=Path(catalog).resolve()
        data=json.loads(catalog.read_text())
        if data.get('schema')!='partwise_scene_catalog_v1' or not data.get('scenes'):
            raise ValueError('invalid scene catalog')
        self.entries={}
        for key,entry in data['scenes'].items():
            if not re.fullmatch('[a-z][a-z0-9_]{0,31}',key):raise ValueError('invalid scene ID')
            asset=(catalog.parent/entry['asset']).resolve()
            if not (asset/'asset.json').is_file():raise ValueError(f'missing saved asset for {key}')
            meta=json.loads((asset/'asset.json').read_text())
            if meta['scene']!=key:raise ValueError('catalog scene/asset mismatch')
            self.entries[key]=dict(asset=asset,label=entry.get('label',key.capitalize()))
        self.editors={};self.output=new_output(output)
        self.switch(scene or data.get('default_scene',next(iter(self.entries))))

    def switch(self,scene):
        if scene not in self.entries:raise ValueError('unknown scene')
        if scene not in self.editors:
            self.editors[scene]=self.Editor(self.entries[scene]['asset'],self.output/scene,image_prefix=scene+'/')
        self.active=self.editors[scene]
        return self.record

    @property
    def record(self):
        return dict(self.active.record,available_scenes={s:e['label'] for s,e in self.entries.items()},
                    scene_session_policy='Each scene keeps its own edits, camera and selection until this server stops. Export each committed asset to keep it.')

    @property
    def asset(self):return self.active.asset

    def check_scene(self,values):
        if values.get('scene')!=self.active.record['scene']:
            raise ValueError('scene changed; refresh before editing')

    def __getattr__(self,name):
        # Only called after construction; handlers reuse the current Editor API.
        return getattr(self.active,name)
