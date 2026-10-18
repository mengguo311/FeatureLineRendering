from env import *
from collections import Counter

def main():
 counts=json.loads((ROOT/'evaluation/COUNTS.json').read_text());verification=json.loads((ROOT/'VERIFY_REPLAY.json').read_text());assert verification['ok'];cal=[json.loads(p.read_text()) for phase in ['dev','reserved'] for p in (ROOT/phase).glob('*/*/CALIBRATION.json')];attr=[json.loads(p.read_text()) for phase in ['dev','reserved'] for p in (ROOT/phase).glob('*/*/*/*/SOURCE_ATTRIBUTION_STATUS.json')]
 js(ROOT/'TEST_RESULTS.json',dict(current_tests=21,groups={'closure_visibility_identity':11,'endpoint_graph_image_transfer':6,'raster_hole_diagnostic':4},red_logs=['tests/01_RED.log','tests/02_RED.log','tests/03_RED.log'],green_logs=['tests/01_GREEN.log','tests/02_GREEN.log','tests/03_GREEN.log'],regression='tests/REGRESSION.log',actual_replay='VERIFY_REPLAY.json',source_allN_calibration=144,source_allN_ROI=sum(len(a['all_N_checks']) for a in attr),source_allN_replay=27,queries=sum(a['queried_pixels'] for a in attr),inherited_tests_not_added_to_total=True))
 js(ROOT/'RENDERER_AUDIT.json',dict(cameras=len(cal),full_SH=True,source_only=True,mean_depth_sort=True,finite_EWA_q_max=9,opacity_alpha_max=.999,early_T=1e-5,filter3D_effective_activation='readonly official implementation',native_RaDe_DTU=True,ficus_vanilla_cpu_proxy=True,official_CUDA_equivalence=False,max_errors={k:max(c[k] for c in cal) for k in ['rgb_mae','alpha_mae','center_surface_p95']},renderer_query_tolerance=5e-7,all_N_tolerance=2e-12))
 js(ROOT/'COUNTS.json',dict(pilots_completed=1,scenes_completed=3,cameras=12,DEV_cameras=3,AUX_cameras=3,reserved_cameras=6,valid_case_view_units=44,unavailable_case_view_units=4,case_view_arm_units=132,transfer_attempts=123,source_role_known=0,new_Gaussian_models=0,new_physical_primitives=0,videos=0,per_scene=counts))
 # Whole-frame native images, padded (not stretched) to one common grid.
 items=[]
 for s in SCENES:
  v=DEV[s];raw=npz(rawpath(s,v));ink=npz(ROOT/'dev'/s/v/'INK_REFERENCE.npz')['rgb'];im=np.asarray(Image.open(ROOT/'diagnostics'/s/v/'FULL_FRAME.jpg'))/255
  # Rebuild third tile from the actual endpoint graph overlay, no prior-results image substitutions.
  from diagnostics import graph_image
  graph=raw['rgb'].copy()
  for cp in sorted((ROOT/'dev'/s/v).iterdir()):
   ap=cp/'original'
   if (ap/'FRAGMENTS.json').exists():graph=graph_image(graph,json.loads((ap/'FRAGMENTS.json').read_text()),json.loads((ap/'LINK_LEDGER.json').read_text()),json.loads((ap/'PROVENANCE.json').read_text())['center_uv'])
  for label,a in [('Frozen source RGB',raw['rgb']),('Original C8 ink | XRAY',ink),('Visible endpoint graph | region UNKNOWN',graph)]:
   pad=np.ones((800,800,3));h,w=a.shape[:2];pad[:h,:w]=a;items.append((s+' | '+label,pad))
  ref=npz(ROOT/'dev'/s/v/'REFERENCE.npz');err=np.clip(abs(ref['rgb']-raw['rgb'])*10,0,1);alpha=np.repeat(ref['alpha'][:,:,None],3,axis=2)
  panel(ROOT/'audit'/f'{s}_CALIBRATION.jpg',[('Frozen reference RGB',raw['rgb']),('CPU full-SH source-only RGB',ref['rgb']),('Absolute RGB difference x10',err),('CPU source alpha; NOT object segmentation',alpha)],s+' | source-only renderer audit','CPU EWA approximation, not official CUDA equivalence',cols=2)
 panel(ROOT/'OVERVIEW.jpg',items,'C8 line-guided region closure | bounded pilot','Three scenes / original line assets unchanged / no qualified persistent source region',cols=3)
 # Actual per-edge scale audit: graph connectedness is not physical continuity.
 ea={}
 for s in SCENES:
  ps=json.loads((linepath(s)/'parents.json').read_text());L=np.concatenate([np.linalg.norm(np.diff(np.asarray(p['control']),axis=0),axis=1)/p['pixel'] for p in ps]);ea[s]=dict(edges=len(L),length_worldpixel_quantiles=np.quantile(L,[.5,.9,.99,1]).tolist(),edges_over_8p=int((L>8).sum()),physical_break_truth='unavailable; stored connected paths can include wrong long edges')
 js(ROOT/'EDGE_GEOMETRY_AUDIT.json',ea)
 obs=[]
 paths=[ROOT/'diagnostics/scan24/0000/window_frame/EXPLANATION.jpg',ROOT/'diagnostics/scan65/0036/socket_rim/EXPLANATION.jpg',ROOT/'diagnostics/ficus/test_r_14/thin_leaf_edge/EXPLANATION.jpg']+[ROOT/'diagnostics'/s/RESERVED[s][1 if s!='ficus' else 0]/'FULL_FRAME.jpg' for s in SCENES]
 for p in paths:obs.append(dict(path=str(p),sha256=sha(p),inspected_with='actual view_image tool'))
 js(ROOT/'VISUAL_EVIDENCE.json',dict(files=obs,observations={'scan24':'Window panes read clearly in ink; DEV thirteen raster white components vs two graph cycles. Some no-line contours split white frames/material, not whole window semantics. Reserved0036 anchor case moves behind side wall/roof: visibility not a negative identity vote.','scan65':'Socket/cap detail contains interrupted and overlapping marks. In0036 projected former socket anchor is at far profile; raster voids can sit on bright bone/negative space. No certified cavity region.','ficus':'Leaf outlines appear closed in xray but several enclosed spaces span different leaves/background. Long top spike preserved. Stem is legal open structure, not a closure failure.'},scientific_qualitative_status='NO_GO for persistent source region; useful visual/graph diagnostic, not disproving all screen-space region methods'))
 review('03_delivery_GO_scientific_NO_GO','GO：完成一个bounded pilot，三scene/12相机、44病例视角×3臂=132测量，未运行第二pilot。21本轮tests和只读来源/图/源及ink数组回放通过。原线0合格源区域；不进入source primitive/NPR正式修改。可交付全部图、图候选/拒绝、区域mask、source责任及全UNKNOWN映射。已实看window/eye/leaf全图弱视角。无线路径少量转移通过但不是语义GT；既不能说原线无用途，也不能说闭合已解决区域。允许小代码本地commit及安全打包，随后停止。',[ROOT/'VERIFY_REPLAY.json',ROOT/'evaluation/COUNTS.json',ROOT/'VISUAL_EVIDENCE.json',ROOT/'tests/REGRESSION.log'])
 state('DELIVERY_READY',completed_pilots=1,scientific_status='NO_GO',engineering_status='PASS',completed_scenes=3,children=[])
if __name__=='__main__':main()
