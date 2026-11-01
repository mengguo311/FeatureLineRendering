"""39 saved real kernels /12 seedlets; singleton guards and synthetic pair probes only."""
from runtime_io import *
from port_paths import Leaf,Edge,PathOracle,endpoint_ports,greedy,joint
from scene_adapter import local_validator
import unittest,importlib.util,sys
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units')
class BoundedReal(unittest.TestCase):
 def test_pinned_port_core_on_saved_ficus_geometry(self):
  path=O/'unit_008/tests/FICUS_REAL_COMPONENT.npz';z=dict(np.load(path,allow_pickle=False));p=float(z['p']);ls={}
  for j,cid in enumerate(z['carrier_id']):
   part=lambda key,off:z[key][z[off][j]:z[off][j+1]]
   ls[int(cid)]=Leaf(int(cid),int(z['version'][j]),part('rows','row_offsets'),part('seedlets','seed_offsets'),part('knots','knot_offsets')/p,bool(z['valid'][j]),bool(z['baseline'][j]),part('supported_intervals','interval_offsets')/p)
  self.assertLessEqual(sum(len(v.reps) for v in ls.values()),128)
  pref=lambda pre:{k[len(pre):]:v for k,v in z.items() if k.startswith(pre)}
  d=dict(asset=pref('asset_'),representatives=pref('representatives_'),tangents=z['tangents'])
  spec=importlib.util.spec_from_file_location('pinned_port_unit002',O/'unit_002/source_snapshot/port_paths.py');old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
  new_or=PathOracle(ls,d['representatives']['x']/p,d['representatives']['t'],local_validator(d,p));old_or=old.PathOracle(ls,d['representatives']['x']/p,d['representatives']['t'],local_validator(d,p))
  ids=sorted(ls);es=[]
  for i,(a,b) in enumerate(zip(ids,ids[1:])):
   ports=endpoint_ports(ls[a],ls[b]);self.assertEqual(ports,old.endpoint_ports(ls[a],ls[b]));es.append(Edge(i,a,ports[0],b,ports[1],.5))
  for cid in ids:self.assertEqual(new_or([(cid,False)]),old_or([(cid,False)]))
  for fn in ['greedy','joint']:
   x,r=globals()[fn](es,new_or);y,rr=getattr(old,fn)(es,old_or);self.assertEqual(x,y);self.assertEqual(r['status'],rr['status']);self.assertEqual(r['benefit'],rr['benefit'])
  print('BOUNDED_REAL_PORT_REGRESSION',dict(carriers=len(ls),seedlets=sum(len(v.reps) for v in ls.values()),kernels=len(d['asset']['means']),synthetic_pair_probes=len(es),fits=0,actual_scene_endpoint_solve=False))
