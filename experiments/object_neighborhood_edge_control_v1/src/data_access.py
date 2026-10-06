"""Controller view API. TEST and surface/depth arrays belong only to evaluator."""
import json
import numpy as np
from PIL import Image
from runtime import OUT, EXP

def config():return json.loads((EXP/'configs/pilot.json').read_text())
def frames(group):
    if group not in ('train','val'):raise PermissionError('controller cannot read heldout cameras')
    return json.loads((EXP/'data/manifests/cameras.json').read_text())['splits'][group]
def training_view(scene,frame,group='train'):
    if group not in ('train','val') or not frame['id'].startswith(group+'_'):
        raise PermissionError('controller cannot read TEST or path targets')
    with np.load(OUT/'data'/scene/group/frame['id']/'A_target.npz') as r:
        view={k:r[k].copy() for k in ('rgb','instance','coverage')}
    if group=='train':
        view['rgb']=np.asarray(Image.open(OUT/'data'/scene/'native_train'/(frame['id']+'.png')),dtype=np.float32)/255
    return view
