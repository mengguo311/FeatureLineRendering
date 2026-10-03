#!/usr/bin/env python3
"""Synthetic CPU-only exercise of the actual patched upstream Blender reader."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FIXTURE=REPO/'out/hybrid_raster_trained_models_v1/training/synthetic_loader_fixture'
p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');args=p.parse_args()
if args.prepare:
    from PIL import Image
    (FIXTURE/'train').mkdir(parents=True,exist_ok=True)
    Image.new('RGBA',(4,4),(100,80,40,128)).save(FIXTURE/'train/r_0.png')
    Image.new('RGBA',(4,4),(40,80,100,255)).save(FIXTURE/'train/r_1.png')
    metadata={'camera_angle_x':.69,'frames':[{'file_path':'./train/r_0','transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,4],[0,0,0,1]]},{'file_path':'./train/r_1','transform_matrix':[[1,0,0,1],[0,1,0,0],[0,0,1,4],[0,0,0,1]]}]}
    (FIXTURE/'transforms_train.json').write_text(json.dumps(metadata))
    # These are synthetic sentinels, never source dataset metadata.
    (FIXTURE/'transforms_test.json').write_text('MUST NOT BE READ')
    (FIXTURE/'transforms_val.json').write_text('MUST NOT BE READ')
else:
    sys.path[:0]=[str(REPO/'out/hybrid_raster_trained_models_v1/vendor/vanilla'),'/home/u00134/3dgs_line/tier1/out/multiscene_foundation/vendor/training_site','/home/u00134/3dgs_line/tier1/out/vrss/vendor/official_site']
    import numpy as np
    from scene.dataset_readers import readNerfSyntheticInfo
    np.random.seed(1729)
    scene=readNerfSyntheticInfo(str(FIXTURE),True,False)
    assert len(scene.train_cameras)==2 and scene.test_cameras==[]
    assert len(scene.point_cloud.points)==100000
    assert scene.train_cameras[0].image.size==(4,4)
    print(json.dumps({'passed':True,'train_cameras':2,'test_cameras':0,'initial_points':100000,'GPU_initialized':False,'scope':'synthetic actual upstream reader CPU, not production'}))
