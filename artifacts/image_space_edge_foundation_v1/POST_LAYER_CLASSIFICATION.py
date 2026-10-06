"""Separate auxiliary alpha provenance; never changes frozen RGB ink/evidence.

RGB-only fits cannot identify an object's exterior. These *auxiliary* maps use
native alpha coverage to distinguish exterior, supported interior color fit and
detail/unknown. Interior means screen coverage, not geometry or material truth.
"""
import json,sys
from pathlib import Path
import cv2,numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/image_space_edge_foundation_v1/src'))
from runtime import ART,OUT,sha,atomic_json
from campaign import npz
from boundary import alpha_outline
from presentation import save_image,panel_sheet

def run():
    records=[]
    for scene in ['lego','chair']:
        for key in ['r_000','r_008','r_018','r_030']:
            f=np.load(OUT/'fixed_fields'/scene/key/'fields.npz');z=np.load(OUT/'raw'/scene/'fixed'/key/'native.npz');a=z['alpha']
            exterior=cv2.dilate(alpha_outline(a).astype(np.uint8),np.ones((7,7),np.uint8)).astype(bool)
            interior=cv2.erode((a>.995).astype(np.uint8),np.ones((23,23),np.uint8)).astype(bool)
            classes=np.zeros(a.shape,np.uint8);classes[f['detail']>=.075]=2
            fitted=f['structural']>=.075
            classes[fitted&interior]=1;classes[fitted&~interior&~exterior]=4;classes[exterior]=3
            palette=np.array([[1,1,1],[.15,.65,.25],[.95,.55,.15],[.15,.35,.95],[.65,.35,.75]],np.float32)
            p=ART/'media'/scene/'fixed'/key
            npz(p/'alpha_aux_classes.npz',classes=classes,alpha_exterior=exterior,alpha_supported_interior=interior)
            save_image(p/'alpha_aux_classes.png',palette[classes])
            row=dict(scene=scene,key=key,counts={str(k):int((classes==k).sum()) for k in range(5)},
                     native_alpha_sha256=sha(OUT/'raw'/scene/'fixed'/key/'native.npz'),
                     frozen_RGB_fields_sha256=sha(OUT/'fixed_fields'/scene/key/'fields.npz'))
            records.append(row)
    atomic_json(ART/'ALPHA_LAYER_PROVENANCE.json',dict(source_sha256=sha(__file__),records=records,
      labels={'0':'no visible RGB ridge / background','1':'alpha-supported interior clear color fit','2':'detail/unknown, including legitimate pattern',
              '3':'native alpha silhouette band, including alpha hole contours','4':'qualified RGB fit near ambiguous alpha coverage'},
      RGB_only_label='qualified two-side color transition; exterior/interior status unknown without alpha',
      postproduction_diagnostic_only=True,RGB_ink_unchanged=True,physical_geometry_or_material_truth=False))
if __name__=='__main__':run()
