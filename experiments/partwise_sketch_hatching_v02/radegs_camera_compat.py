"""Read-only local adapter for the verified RaDe-GS synthetic camera reader.

Only one AST dtype changes: signed np.byte -> np.uint8 at Image.fromarray.
Current Pillow rejects signed 3-channel arrays. The official checkout stays
byte-identical. This is not a full scene loader and creates no initial points.
"""
from common import *
import ast,math
from typing import NamedTuple
from PIL import Image

SOURCE=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/sources/RaDe-GS/scene/dataset_readers.py')
SOURCE_SHA='f8a0fd4df7945c8c52a274744bb2a02103ebf4930a6cbcabf0a3272b9eb7e4a0'


def get_reader():
    assert sha(SOURCE)==SOURCE_SHA,'official source changed'
    ns=dict(os=os,np=np,json=json,Image=Image,Path=Path,NamedTuple=NamedTuple,math=math)
    graphics=SOURCE.parents[1]/'utils/graphics_utils.py'
    nodes=[x for x in ast.parse(graphics.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ('focal2fov','fov2focal')]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(graphics),'exec'),ns)
    nodes=[x for x in ast.parse(SOURCE.read_text()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name in ('CameraInfo','readCamerasFromTransforms')]
    count=0
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child,ast.Attribute) and isinstance(child.value,ast.Name) and child.value.id=='np' and child.attr=='byte':
                child.attr='uint8';count+=1
    assert count==1,'expected exactly one signed RGB dtype conversion'
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(SOURCE)+' [local uint8 adapter]','exec'),ns)
    return ns['readCamerasFromTransforms']


def read_cameras(root,transforms='transforms_train.json',white_background=True):
    return get_reader()(str(Path(root).resolve()),transforms,white_background)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');p.add_argument('--transforms',default='transforms_train.json')
    a=p.parse_args();c=read_cameras(a.root,a.transforms)
    print(json.dumps(dict(loaded_frames=len(c),adapter='one signed-to-unsigned RGB dtype correction',training=False,oracle_loaded=False)))
