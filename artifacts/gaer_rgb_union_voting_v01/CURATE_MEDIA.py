"""Presentation-only postproduction: readable headers and unit-gain raw vote feature.

Frozen assignment, ranking, native subsets and evaluation are never changed.
The original sealed production panels remain preserved. Added maps use exactly
the same per-original-row log-frequency feature, full native T, display gain 1.
"""
import sys,json,time,textwrap
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_rgb_union_voting_v01'))
from runtime import *
import numpy as np
import torch
from PIL import Image,ImageDraw,ImageFont
from binding import backend,scene_io,ops
from media import save,heat,support_overlay,winner_images
import curate

def readable_sheet(p,panels,cols=4,tile=800,title=''):
    rows=(len(panels)+cols-1)//cols;header=72;top=62
    im=Image.new('RGB',(cols*tile,rows*(tile+header)+top),'white');draw=ImageDraw.Draw(im)
    size=18 if tile>=640 else 12
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)
    titlefont=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    draw.text((12,14),title,font=titlefont,fill='black')
    for j,(label,a) in enumerate(panels):
        x=(j%cols)*tile;y=(j//cols)*(tile+header)+top
        parts=[]
        for part in label.split('|'):
            parts.extend(textwrap.wrap(part,width=max(20,int(tile/(size*.58))-2)))
        draw.text((x+8,y+8),'\n'.join(parts[:3]),font=font,fill='black',spacing=3)
        a=a if isinstance(a,Image.Image) else curate.Image.fromarray(np.round(np.clip(a,0,1)*255).astype(np.uint8))
        if a.size!=(tile,tile):a=a.resize((tile,tile),Image.Resampling.LANCZOS)
        im.paste(a,(x,y+header))
    save(p,im)

def main():
    start=time.perf_counter();curate.sheet=readable_sheet;curate.curate()
    frozen=json.loads((ART/'PRODUCTION_FREEZE.json').read_text());m=backend();records=[]
    for scene in ('lego','chair'):
        rec=frozen['scenes'][scene];guard(scene+'_post_display_load');model=scene_io.load_model(rec)
        votes=np.load(ART/'downloads'/(scene+'_votes_all_original.npz'));F=votes['raw_frequency'];feature=np.log1p(F)/np.log1p(F.max())
        colors=torch.as_tensor(np.repeat(feature[:,None],3,1).astype(np.float32),device='cuda')
        allpanels=[];zoompanels=[]
        views=[v for v in rec['vote_views'] if v['key'] in frozen['protocol']['visualization_views']]+rec['evaluation_views']
        for v in views:
            key=v['key'];kind='display' if v['role'] in ('dev','fixed') else 'eval';d=ART/'media'/scene/kind/key
            src=np.load(ART/'downloads'/scene/key/'source_fields.npz');rgb=src['RGB'];ink=src['ink'];s=scene_io.make_settings(m,v['camera'])
            guard(scene+'_post_vote_feature_'+key);t=time.perf_counter()
            with torch.no_grad():
                out,_=m.GaussianRasterizer(s._replace(bg=torch.zeros(3,device='cuda'),sh_degree=0))(**ops.feature_model(model,colors))
                original,_=m.GaussianRasterizer(s)(**model)
            if not np.array_equal(original.cpu().numpy().transpose(1,2,0),rgb):raise AssertionError('original model changed in presentation')
            mass=out[0].cpu().numpy();path=d/'raw_vote_frequency_fullT.npz';npz(path,log_frequency_feature_fullT=mass)
            save(d/'raw_vote_frequency_gain1.png',heat(mass))
            save(d/'raw_vote_frequency_gain1_overlay.png',support_overlay(rgb,mass,1.))
            chosen=np.load(OUT/'display_maps'/scene/kind/key/'top500_fullT.npz')['contribution']
            readable_sheet(d/'readable_main_evidence.jpg',[
                (scene+' '+key+' original native fullSH3',Image.open(d/'RGB.png').copy()),
                ('Exact old RGB spatial union ink | marked darkness > 0.2',Image.open(d/'spatial_union_ink.png').copy()),
                ('FIXED TOP500 original SH3 selected-only | n=500; same eight-view IDs',Image.open(d/'top500_selected_only.png').copy()),
                ('TOP500 actual full-model T contribution | magenta overlay gain=6; supports internal + outline pixels',Image.open(d/'top500_fullT_overlay.png').copy()),
                ('All original nuclei raw pixel-frequency feature | full-model T * log1p(F)/log1p(maxF), UNIT gain=1',Image.open(d/'raw_vote_frequency_gain1.png').copy()),
                ('Mandatory largest-center-alphaT TOP500 | original SH3 selected-only; same masks',Image.open(d/'center_top500_selected_only.png').copy())],
                cols=3,tile=800,title=scene+' '+key+' | eight frozen source views, same fixed candidate sets | '+kind)
            records.append(dict(scene=scene,key=key,kind=kind,seconds=time.perf_counter()-t,RGB_post_bitwise=True,
                feature_sha256=array_sha(mass),display_gain=1.,interpretation='postproduction unit-range display, no refitting of F or IDs'))
            if kind=='display':
                for name in ('RGB','raw_vote_frequency_gain1','raw_vote_frequency_gain1_overlay','top500_fullT_overlay'):
                    allpanels.append((key+' '+name+'|raw votes over 8 source views; fixed TOP500',Image.open(d/(name+'.png')).copy()))
                a=np.load(ART/'downloads'/scene/key/'assignment.npz');line=src['line_binary'];standalone,receiver=winner_images(rgb,a['winner_map'],line)
                roi=[240,260,560,580] if scene=='lego' else [240,330,560,650]
                for label,img in [('original RGB',rgb),('old spatial ink',np.repeat((1-ink)[...,None],3,2)),('all marked receiver-ID overlay',receiver),
                    ('TOP500 fullT original support',support_overlay(rgb,chosen,6))]:
                    tile=Image.fromarray(np.round(np.clip(img[roi[1]:roi[3],roi[0]:roi[2]],0,1)*255).astype(np.uint8)).resize((640,640),Image.Resampling.NEAREST)
                    zoompanels.append((key+' '+label+'|frozen old native ROI, exact nearest 2x',tile))
                readable_sheet(ART/'media'/scene/'receivers'/key/'native_ROI_nearest2x.png',zoompanels[-4:],cols=4,tile=640,
                    title=scene+' '+key+' original native 320x320 ROI, nearest 2x')
        readable_sheet(ART/'media'/scene/'fourview_frequency_and_support.jpg',allpanels,cols=4,tile=800,
            title=scene+' raw eight-view frequency feature at UNIT gain=1 and fixed TOP500 fullT support')
        readable_sheet(ART/'media'/scene/'fourview_internal_ROI_nearest2x.png',zoompanels,cols=4,tile=640,
            title=scene+' same frozen native ROIs; every marked valid pixel receives an original Gaussian')
        del model,colors;torch.cuda.empty_cache()
    # Additional evidence is outside frozen production sources; exact source
    # hashes and presentation changes are disclosed without rewriting the seal.
    sourcepath=ART/'SOURCE_MAP.json';sources=json.loads(sourcepath.read_text())
    sources['postproduction_presentation']={relative(Path(__file__)):sha(__file__)}
    sources['citations'][0].update(title='Feature Line Rendering from Rasterization States in 3D Gaussian Splatting',
        authors=['Weiren Hao','Tomohiko Mukai'],author_page='https://mukai-lab.org/publications/sa2026poster-3dgs/',retrieved='2026-10-06')
    atomic_json(sourcepath,sources)
    atomic_json(ART/'results/POST_PRESENTATION.json',dict(seconds=time.perf_counter()-start,records=records,
        changes=['readable curated sheet headers','unit-gain raw frequency feature in addition to original sealed gain8 panels',
            'nearest-neighbor ROI zooms in addition to original sealed resampled previews'],ranking_or_assignment_changed=False))
    manifest=[]
    for path in sorted((ART/'media').rglob('*'))+sorted((ART/'downloads').rglob('*')):
        if path.is_file():
            item=dict(path=relative(path),bytes=path.stat().st_size,sha256=sha(path))
            if path.suffix in ('.png','.jpg'):
                with Image.open(path) as im:item.update(width=im.width,height=im.height)
            manifest.append(item)
    atomic_json(ART/'MEDIA_MANIFEST.json',dict(files=manifest,count=len(manifest),total_bytes=sum(x['bytes'] for x in manifest)))
    print('POST_PRESENTATION_COMPLETE',round(time.perf_counter()-start,3),flush=True)

def relative(p):return str(p.relative_to(ROOT))
if __name__=='__main__':main()
