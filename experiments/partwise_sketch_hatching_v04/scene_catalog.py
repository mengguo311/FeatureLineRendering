"""Independent in-memory editing sessions for a portable catalog of real assets."""
import runtime
from pathlib import Path
import json,re
from runtime import sha
from demo import new_output

def read_catalog(catalog):
    catalog=Path(catalog).resolve();data=json.loads(catalog.read_text())
    if data.get('schema')!='partwise_scene_catalog_v1' or not data.get('scenes'):
        raise ValueError('invalid scene catalog')
    entries={};examples={}
    def entry(key,value,scene,default=False):
        if not re.fullmatch('[a-z][a-z0-9_]{0,31}',key):raise ValueError('invalid catalog ID')
        asset=(catalog.parent/value['asset']).resolve()
        if not (asset/'asset.json').is_file():raise ValueError(f'missing saved asset for {key}')
        meta=json.loads((asset/'asset.json').read_text())
        if meta['scene']!=scene:raise ValueError('catalog scene/asset mismatch')
        return dict(asset=asset,label=value.get('label',key.capitalize()),scene=scene,
            description=value.get('description','Original catalog default · authored regions on a model-derived proxy.'),
            original_sha256=meta['original']['sha256'],source_asset_sha256=sha(asset/'asset.json'))
    for key,value in data['scenes'].items():entries[key]=entry(key,value,key,True)
    for key,value in data.get('examples',{}).items():
        scene=value['scene']
        if key=='default' or scene not in entries:raise ValueError('invalid example scene or ID')
        examples[key]=entry(key,value,scene)
        if examples[key]['original_sha256']!=entries[scene]['original_sha256']:
            raise ValueError('example original model mismatch')
    return data,entries,examples

class SceneCatalog:
    def __init__(self,catalog,output,scene=None,example=None):
        from viewer import Editor
        self.Editor=Editor
        data,self.entries,self.examples=read_catalog(catalog)
        self.last_example={s:'default' for s in self.entries}
        self.editors={};self.output=new_output(output);self.import_count=0
        self.switch(scene or data.get('default_scene',next(iter(self.entries))),example)

    def switch(self,scene,example=None):
        if scene not in self.entries:raise ValueError('unknown scene')
        example=self.last_example[scene] if example is None else example
        if example!='default' and (example not in self.examples or self.examples[example]['scene']!=scene):
            raise ValueError('unknown example for this model')
        key=(scene,example);entry=self.entries[scene] if example=='default' else self.examples[example]
        if 'active' in self.__dict__ and self.editors.get(key) is not self.active:
            self.active.render_cache.clear()
        if key not in self.editors:
            prefix=scene if example=='default' else scene+'/'+example
            provenance=dict(id=example,scene=scene,label='Default' if example=='default' else entry['label'],
                description=entry['description'],source_asset_sha256=entry['source_asset_sha256'])
            self.editors[key]=self.Editor(entry['asset'],self.output/prefix,image_prefix=prefix+'/',example_metadata=provenance)
        self.active=self.editors[key];self.active_example=example;self.last_example[scene]=example
        return self.record

    def switch_example(self,example):return self.switch(self.active.record['scene'],example)

    def import_archive(self,payload,filename='saved-asset.zip'):
        """Open a validated upload without changing any existing session."""
        from asset_archive import unpack_archive
        from runtime import js
        import shutil
        if self.import_count>=16:raise ValueError('16 imported sessions open; download your assets and restart the viewer')
        index=self.import_count+1;key=f'import_{index:04d}'
        # Catalog authors may already use an import-like ID.
        while key in self.examples:index+=1;key=f'import_{index:04d}'
        destination=self.output/'imports'/key
        receipt=unpack_archive(payload,destination,{s:e['original_sha256'] for s,e in self.entries.items()})
        scene=receipt['scene'];prefix=scene+'/'+key
        label='Imported '+str(index)+' · '+Path(str(filename)).name[:64]
        provenance=dict(id=key,scene=scene,label=label,
            description='Imported saved asset. Final styles and camera restored; undo starts here. Download to keep later edits.',
            source_asset_sha256=sha(destination/'asset.json'),archive_sha256=receipt['archive_sha256'],
            imported_from=json.loads((destination/'asset.json').read_text()).get('demo_example'))
        try:
            editor=self.Editor(destination,self.output/prefix,image_prefix=prefix+'/',example_metadata=provenance,import_receipt=receipt)
            js(self.output/'imports'/(key+'.receipt.json'),receipt)
        except Exception:
            shutil.rmtree(destination)
            if (self.output/prefix).exists():shutil.rmtree(self.output/prefix)
            raise
        self.examples[key]=dict(asset=destination,label=label,scene=scene,description=provenance['description'],
            original_sha256=receipt['original_sha256'],source_asset_sha256=provenance['source_asset_sha256'])
        self.editors[(scene,key)]=editor;self.import_count+=1
        self.active.render_cache.clear()
        self.active=editor;self.active_example=key;self.last_example[scene]=key
        return self.record

    @property
    def record(self):
        return dict(self.active.record,available_scenes={s:e['label'] for s,e in self.entries.items()},
                    example=self.active_example,can_import=True,
                    available_examples={'default':'Default',**{k:e['label'] for k,e in self.examples.items() if e['scene']==self.active.record['scene']}},
                    scene_session_policy='Each model/example keeps its own edits, camera, selection and undo until this server stops. Download each saved asset to keep it.')

    @property
    def asset(self):return self.active.asset

    def check_scene(self,values):
        if values.get('scene')!=self.active.record['scene']:
            raise ValueError('scene changed; refresh before editing')
        if values.get('example','default')!=self.active_example:
            raise ValueError('example changed; refresh before editing')

    def __getattr__(self,name):
        # Only called after construction; handlers reuse the current Editor API.
        return getattr(self.active,name)
