"""Post-run same-camera selector diagnostics; frozen ROI center, no tuning."""
import sys,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/edge_control_lego_chair_v1/src'))
from runtime import ART,OUT,atomic_json,sha
from data import load_reference
from media import load_arrays,array_image,font

def main():
    data=json.loads((ART/'DATA_FREEZE.json').read_text());record=[]
    arms=['reference','B0','relative_cov','band2d_cov','random_cov']
    for scene,s in data['scenes'].items():
        targets={x['key']:x for x in json.loads((ART/f'{scene}_TARGET_FREEZE.json').read_text())['targets']}
        sheet=Image.new('RGB',(256*len(arms),4*310+50),'white');draw=ImageDraw.Draw(sheet);draw.text((8,8),f'{scene.upper()} | same count / operation | selector comparison',font=font(21),fill='black')
        zoomsheet=Image.new('RGB',(256*len(arms),4*310+50),'white');zd=ImageDraw.Draw(zoomsheet);zd.text((8,8),f'{scene.upper()} | frozen TRAIN-target ROI center, expanded context',font=font(21),fill='black')
        for row,entry in enumerate(s['roles']['dev']):
            gt,aa=load_reference(entry);images={'reference':gt}
            for arm in arms[1:]:images[arm]=load_arrays(scene,'dev',arm,entry['key'])['rgb']
            roi=targets[entry['key']]['roi'];cx=(roi[0]+roi[2])/2;cy=(roi[1]+roi[3])/2;r=96
            expanded=[max(0,int(cx-r)),max(0,int(cy-r)),min(512,int(cx+r)),min(512,int(cy+r))]
            for col,arm in enumerate(arms):
                im=array_image(images[arm]);y=50+row*310
                sheet.paste(im.resize((256,256),Image.Resampling.LANCZOS),(col*256,y+44));draw.text((col*256+4,y),f'{entry["key"]} / {arm}',font=font(13),fill='black');draw.text((col*256+4,y+21),'original TRAIN dev / fixed parameters',font=font(11),fill='black')
                crop=im.crop(tuple(expanded));crop.thumbnail((250,256),Image.Resampling.NEAREST)
                zoomsheet.paste(crop,(col*256+(256-crop.width)//2,y+44));zd.text((col*256+4,y),f'{entry["key"]} / {arm}',font=font(13),fill='black');zd.text((col*256+4,y+21),'native pixels / frozen target ROI center',font=font(11),fill='black')
            record.append({'scene':scene,'key':entry['key'],'camera_hash':entry['camera_hash'],'subplot_keys':arms,'selected_count':json.loads((ART/f'{scene}_SELECTION_FREEZE.json').read_text())['budget'],'primary_frozen_roi':roi,'context_display_roi':expanded,'context_scope':'post-run display only, same frozen TRAIN-target ROI center; no new optimization/evaluation target; all arms use actual native RGB','primary_operation':'bounded DC+covariance,336steps,positions/opacity/restSH frozen'})
        sheet.save(ART/'figures'/f'{scene}_fourview_selectors.jpg',quality=95);zoomsheet.save(ART/'figures'/f'{scene}_fourview_failure_context.jpg',quality=95)
    atomic_json(ART/'SELECTOR_FIGURE_MANIFEST.json',record)
    with (ART/'REPORT_ZH.md').open('a') as f:f.write('\n\n## 相同操作/数量的选核对比\n\n额外四视角图直接使用已有原生渲染：参考/B0/relative-cov/band2d-cov/random-cov；开发相机与参数固定。failure context 沿已冻结 TRAIN-target ROI 中心扩大显示范围，不选择新的优化目标或改变评价区域。\n\n- [Lego选核对比](figures/lego_fourview_selectors.jpg) / [固定ROI上下文放大](figures/lego_fourview_failure_context.jpg)。\n- [Chair选核对比](figures/chair_fourview_selectors.jpg) / [固定ROI上下文放大](figures/chair_fourview_failure_context.jpg)。\n')

if __name__=='__main__':main()
