"""Presentation only. Never changes recipes/maps; shortlisted on BUILD pilots."""
import json,numpy as np
from PIL import Image,ImageDraw
from common import *
from render_boards import board,font
CHOICES={'scan24':['C2U20','A40','C1L50'],'scan65':['A40','C1L50','C2U20'],'ficus':['C1U20','A30','M75T30']}
ROIS={'scan24':dict(roof=(50,15,335,180),windows=(285,110,510,350)),
      'scan65':dict(eyes_nose_teeth=(165,280,460,540),head_outline=(20,10,350,180)),
      'ficus':dict(leaves_stems=(280,140,580,420),branches_pot=(340,405,470,695))}
def main():
    plan=T/'PROVISIONAL_CHOICES_BUILD.json'
    if not plan.exists():write(plan,dict(utc=utc(),source='actual first BUILD/reference pilot images; before remaining/EVAL visual review',provisional_not_user_selection=True,choices=CHOICES,rois=ROIS,roi_use='explanatory crops only; never detector inputs or masks'))
    for scene,ids in CHOICES.items():
        views=['train_r_80'] if scene=='ficus' else ['0000','0012','0024','0036','0048']
        for v in views:
            p=T/'scenes'/scene/v
            if not (p/'COMPLETE.json').exists():continue
            def candidate(id):return p/'presets'/id/'candidate.png'
            cells=[('Original RGB',p/'RGB.png'),('A20 | original candidates',candidate('A20'))]+[(id+' | provisional option',candidate(id)) for id in ids]+[('B00 | OVER-SUPPRESSION control',candidate('B00'))]
            board(T/'selection'/f'{scene}_{v}_CHOICES.jpg',cells,f'{scene} {v} | User selection: compare complete frames','Options are provisional | B00 is a negative control | No 3D rebuild has been run')
            # Same binary black for all candidates: no amplitude/brightness advantage.
            board(T/'selection'/f'{scene}_{v}_BINARY.jpg',[(id+' | binary candidates',p/'presets'/id/'marked.png') for id in ['A20']+ids+['B50','B00']],f'{scene} {v} | Binary candidate audit','Every marked pixel is black | Compare topology, not soft-line darkness',binary=True)
        ref='train_r_80' if scene=='ficus' else '0000';p=T/'scenes'/scene/ref
        context=Image.open(p/'RGB.png').convert('RGB');draw=ImageDraw.Draw(context)
        for name,box in ROIS[scene].items():draw.rectangle(box,outline='#e44b25',width=3);draw.text((box[0],box[1]),name,font=font(15),fill='#e44b25')
        context.save(T/'selection'/f'{scene}_ROI_CONTEXT.png')
        for name,box in ROIS[scene].items():
            def crop(path):
                im=Image.open(path).crop(box);return im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
            items=[('RGB | secondary crop',crop(p/'RGB.png'))]+[(id+' | exact same crop',crop(p/'presets'/id/'candidate.png')) for id in ['A20']+ids+['B00']]
            board(T/'selection'/f'{scene}_ROI_{name}.jpg',items,f'{scene} {ref} | Detail check: {name}',f'Secondary explanatory crop {box}; 2x nearest display | Full-frame images also delivered',full_frame=False)
        if scene!='ficus' and all((T/'scenes'/scene/v/'COMPLETE.json').exists() for v in views):
            for id in ids:
                board(T/'selection'/f'{scene}_{id}_ALL5.jpg',[(f'{v} | {id}'+(' | seen holdout' if v in ['0012','0036'] else ' | BUILD'),T/'scenes'/scene/v/'presets'/id/'candidate.png') for v in views]+[('0000 | A20 reference',T/'scenes'/scene/'0000'/'presets'/'A20'/'candidate.png')],f'{scene} | {id} | Same preset across all five cameras','No per-view tuning | Historical seen/sourceGS train cameras; not blind evaluation')
    print('Selection boards updated')
if __name__=='__main__':main()
