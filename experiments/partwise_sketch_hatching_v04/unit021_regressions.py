"""Focused inherited cross-layer contracts and unchanged legacy raster."""
import runtime
from runtime import js,sha,now
from unit021_run import U,PREV
import unittest,importlib.util
import numpy as np
import test_crosshatch
from demo import load_asset
from render import render
from geometry import orbit_camera
test_crosshatch.UNIT=U
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_crosshatch))
assert result.wasSuccessful()
spec=importlib.util.spec_from_file_location('legacy_render',U/'source_before/render.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
records=[]
for scene in ('chair','lego','drums','ficus'):
    asset=PREV/'portable_demo/assets'/scene;m,s,j=load_asset(asset);c=orbit_camera(29,28,5.2,192)
    before=old.render(m,s,j['styles'],c,display=j.get('display'))
    after=render(m,s,j['styles'],c,display=j.get('display'))
    for key in ('image','hatch','contour','depth','regions','proxy','region_rgb'):np.testing.assert_array_equal(before[key],after[key])
    for r in s:np.testing.assert_array_equal(before['layers'][r],after['layers'][r])
    records.append(dict(scene=scene,asset_sha256=sha(asset/'asset.json'),PNG_float_arrays_and_layers_exact=True,camera=c))
js(U/'metrics/REGRESSIONS.json',dict(utc=now(),cross_tests=result.testsRun,legacy_defaults=records,legacy_renderer_sha256=sha(U/'source_before/render.py'),output_root=str(U),no_historical_writes=True))
