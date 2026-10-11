import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from pathlib import Path
import sys,json,hashlib,time
T=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/fusion_redesign_v03');B=T.parent/'balanced_multiview_v02';O=T.parent/'spatial_rgb_gaussian_demo_v01'
OLD_CODE=Path('/home/u00134/3dgs_line/gaer_rade_depth_lift_v01/reproduction/radegs_balanced_multiview_v02')
sys.path.insert(0,str(OLD_CODE))
import core,demo
import numpy as np
import cv2
cv2.setNumThreads(2)
def sha(p):return demo.sha(p)
def js(p,a):demo.writejson(p,a)
def status(phase,**kw):
 p=T/'STATUS.json';a=json.loads(p.read_text());a.update(phase=phase,status='RUNNING',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw);js(p,a);print(phase,kw,flush=True)
