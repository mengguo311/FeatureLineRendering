"""Focused inherited authoring and legacy catalog checks, current-unit outputs."""
import runtime
from runtime import js,sha
import unittest
from unit022_run import U,PREV,ASSET,protocol
import test_preserve_authoring as author_tests
from demo import load_asset
from geometry import orbit_camera
from render import render
import numpy as np

author_tests.U=U;author_tests.ASSET=ASSET;author_tests.protocol=protocol
suite=unittest.defaultTestLoader.loadTestsFromModule(author_tests)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
rows=[]
for directory in ('assets','examples'):
    for folder in sorted((PREV/'portable_demo'/directory).iterdir()):
        if not (folder/'asset.json').is_file():continue
        mesh,paths,meta=load_asset(folder)
        row=dict(asset=str(folder),scene=meta['scene'],load_valid=True)
        if directory=='assets':
            r=render(mesh,paths,meta['styles'],orbit_camera(33,27,4.9,192),display=meta.get('display'))
            assert np.isfinite(r['image']).all() and (r['image']<.99).any()
            row['smoke_nonblank_pixels']=int((r['image']<.99).sum())
        rows.append(row)
js(U/'metrics/REGRESSIONS.json',dict(authoring_tests=result.testsRun,all_passed=True,catalog=rows))
