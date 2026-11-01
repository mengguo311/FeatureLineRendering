"""Bounded ficus M4 regression against the immutable unit007 numerical core."""
from runtime_io import *
from port_paths import Leaf
import unittest,importlib.util,sys
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_008/tests')
PIN=U.parent.parent/'unit_007/source_snapshot'
def pinned(name):
 spec=importlib.util.spec_from_file_location('pinned_unit007_'+name,PIN/(name+'.py'));m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m
class RealSceneRegression(unittest.TestCase):
 def test_real_complete_component_same_fits_banks_selection_and_membership(self):
  import overlap_model,observation_model,pair_model,pair_delivery
  z=dict(np.load(U/'FICUS_REAL_COMPONENT.npz',allow_pickle=False));p=float(z['p']);leaves={}
  for j,cid in enumerate(z['carrier_id']):
   part=lambda key,off:z[key][z[off][j]:z[off][j+1]]
   leaves[int(cid)]=Leaf(int(cid),int(z['version'][j]),part('rows','row_offsets'),part('seedlets','seed_offsets'),part('knots','knot_offsets')/p,bool(z['valid'][j]),bool(z['baseline'][j]),part('supported_intervals','interval_offsets')/p)
  self.assertLessEqual(sum(len(x.reps) for x in leaves.values()),128)
  prefix=lambda x:{k[len(x):]:v for k,v in z.items() if k.startswith(x)}
  cand=prefix('candidate_');cand['metric_names']=z['metric_names'];d=dict(asset=prefix('asset_'),representatives=prefix('representatives_'),membership=prefix('membership_'),leaves=leaves,tangents=z['tangents'],p=p,next_version=50000,candidates=cand,aux={})
  d['pairs']=list(zip(cand['a'].tolist(),cand['b'].tolist()));d['overlaps']=overlap_model.successful_overlaps(d);ctx=dict(carriers=sorted(leaves))
  self.assertEqual(d['overlaps'],pinned('overlap_model').successful_overlaps(d))
  before=hashlib.sha256(b''.join(v.tobytes() for v in d['asset'].values())).hexdigest();models=[];oldmodels=[]
  old=pinned('pair_model');engine=pair_model.fit_engine(Path(__file__).parent/'pinned_v05_fit_core.py',d);oldengine=old.fit_engine(PIN/'pinned_v05_fit_core.py',d)
  for rid,(a,b) in enumerate(d['pairs']):
   expected=dict(zip(cand['metric_names'].tolist(),cand['metrics'][rid].tolist()));expected['cost']=float(cand['cost'][rid])
   model=pair_model.fit_pair(engine,d,a,b,rid,expected);control=old.fit_pair(oldengine,d,a,b,rid,expected)
   self.assertEqual(model,control);self.assertEqual(model['status'],'RECOVERED');models.append(model);oldmodels.append(control)
  hs,rec=overlap_model.build_bank(d,ctx);hh,rr=pinned('overlap_model').build_bank(d,ctx);self.assertEqual(hs,hh);self.assertEqual(rec,rr)
  extra,rec=observation_model.build_extra_bank(d,ctx,models);ee,rr=pinned('observation_model').build_extra_bank(d,ctx,oldmodels);self.assertEqual(extra,ee);self.assertEqual(rec,rr)
  bank=hs+extra
  for i,h in enumerate(bank):h['hid']=i
  for method in ['select_greedy','select_joint']:
   if method=='select_joint':sel,receipt=getattr(pair_model,method)(bank,5);ss,oldrec=getattr(old,method)(bank,5);self.assertEqual(receipt['status'],oldrec['status'])
   else:sel=getattr(pair_model,method)(bank);ss=getattr(old,method)(bank)
   self.assertEqual(sel,ss);chosen=[h for h in bank if h['hid'] in sel]
   m,g,l=pair_delivery.membership_for(d,chosen,bank);mm,gg,ll=pinned('pair_delivery').membership_for(d,chosen,bank)
   self.assertEqual(g,gg);self.assertEqual(l,ll)
   for k in m:np.testing.assert_array_equal(m[k],mm[k])
  self.assertEqual(engine.fit_count,len(models));self.assertEqual(before,hashlib.sha256(b''.join(v.tobytes() for v in d['asset'].values())).hexdigest())
  print('FICUS_BOUNDED_REGRESSION',dict(carriers=len(leaves),seedlets=sum(len(v.reps) for v in leaves.values()),kernels=len(d['asset']['means']),pairs=len(models),fits_per_implementation=engine.fit_count,hypotheses=len(bank),full_scene_run=False))
