"""Focused coverage/hidden-contour regression; whole-lamp visuals are primary."""
import argparse
import sys
import unittest
from common import core, np
from renderer import render

MODE = "visible_centerline"

def scene(occluder_part=None):
    camera = core.camera(0, 0, 4.5, 96, 96)
    vertices, faces, parts = [], [], []
    def rectangle(x0, y0, x1, y1, z, part):
        i = len(vertices)
        vertices.extend(core.backproject(np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]]), np.full(4,z), camera))
        faces.extend([[i,i+1,i+2],[i,i+2,i+3]])
        parts.extend([part,part])
    rectangle(8,8,88,88,4.,1)
    if occluder_part:
        rectangle(48,0,80,50,3.5,occluder_part)
    mesh = core.finalize_mesh(vertices,faces,parts)
    cfg = {'asset':{'profiles_ry':{}}, 'renderer':{'resolution':[96,96], 'focal_px':96,
           'supersample':4, 'visibility_tolerance_world':.006, 'contour_width_px':.8,
           'contour_visibility':MODE}}
    return render(mesh,[],cfg,azimuth=0,elevation=0,distance=4.5,structure=False)

class ContourContracts(unittest.TestCase):
    def test_silhouette_keeps_symmetric_coverage(self):
        out=scene()
        self.assertGreater(float(out['contours'][8,20:40].mean()), .8,
                           'visible .8px contour must retain its background-side samples')
        self.assertEqual(float(out['contours'][:7,20:40].sum()),0.)

    def test_different_part_hides_rear_contour(self):
        out=scene(2)
        self.assertEqual(float(out['contours'][7:10,54:75].sum()),0.)
        self.assertGreater(float(out['contours'][8,20:40].sum()),8.)

    def test_same_part_hides_rear_contour(self):
        out=scene(1)
        self.assertEqual(float(out['contours'][7:10,54:75].sum()),0.)
        self.assertGreater(float(out['contours'][8,20:40].sum()),8.)

if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False)
    p.add_argument('--mode',choices=['surface_fragments','visible_centerline'],default=MODE)
    args,rest=p.parse_known_args();MODE=args.mode
    unittest.main(argv=[sys.argv[0],*rest],verbosity=2)
