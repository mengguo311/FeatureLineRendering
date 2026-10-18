from env import *
from run_stage_a import overlay,grey
from hierarchy import CFG as BCFG
import csv

def run():
 b=json.loads((ROOT/'B_COUNTS.json').read_text());stageA=json.loads((ROOT/'STAGE_A_GATE.json').read_text())['scenes'];paths=[ROOT/'stageB/ficus'/v/'COMPARISON_FULL.jpg' for v in [DEV['ficus'],AUX['ficus'],*RESERVED['ficus']]]
 cases=[]
 for arm in ['rgb_depth','rgb_only','depth_only']:
  m=[x for x in b['matches'] if x['arm']==arm and x['level']==2]
  cases.append(dict(arm=arm,coarse_mutual_by_target={x['to_view']:x['mutual_pairs'] for x in m},not_GT=True))
 gate=dict(stageB_ficus='NO_GO',reason='Main RGB-depth: DEV/AUX mutual major-region links 0 at all three frozen levels; AUX has16 major regions>12 budget. Main coarse test_r_14 one pot-related pair; test_r_79 zero. RGB-only coarse has one pot pair per target, showing source appearance grouping baseline stronger here. No consistent pot/trunk/canopy framework.',source_assignments='NOT_RUN',stageC='NOT_RUN',stageD='NOT_RUN',cases=cases)
 js(ROOT/'STAGE_B_GATE.json',gate)
 review('06_B_review_NO_GO_STOP','已实际检查Ficus DEV和test_r_14全图。主层级把花盆按视角/深度分为不同片，树干与叶簇组合不稳定；DEV/AUX 0双向区域配对，预冻上限也失败。RGB-only有更稳定的花盆整体，不能称深度版增加结构信息。NO_GO升级；C/D NOT_RUN。仅允许冻结结果的汇总、失败解释图、readonly复算/封存，不再优化或试下一方向。',paths+[ROOT/'B_COUNTS.json'])
 out=ROOT/'delivery';out.mkdir(exist_ok=True);overview=[];countrows=[];cal=[]
 for s in SCENES:
  native_items=[]
  for v in [DEV[s],AUX[s],*RESERVED[s]]:
   p=ROOT/'stageA'/s/v;raw=npz(rawpath(s,v));a=npz(p/'SUBJECT.npz');ref=npz(p/'REFERENCE.npz');native_items.extend([(v+' | frozen source RGB',raw['rgb']),(v+' | proposal + UNKNOWN',overlay(raw['rgb'],a['candidate'],a['unknown'])),(v+' | TRUE joint unchanged C8 + source',ref['joint_rgb'])]);r=json.loads((p/'RESULT.json').read_text());countrows.append(r)
   c=json.loads((p/'CALIBRATION.json').read_text());c.update(scene=s,view=v,joint_vs_RGB_times_ink_max=float(abs(ref['joint_rgb']-ref['source_rgb']*ref['line_rgb']).max()),grouped_fullSH=True);cal.append(c)
  panel(out/(s+'_FOUR_VIEWS.jpg'),native_items,s+' | All four frozen cameras / Stage A','Green: candidate, orange: uncertainty. Full scene unchanged. DTU views are source-GS train / historically seen.',3)
  v='0036' if s!='ficus' else 'test_r_14';raw=npz(rawpath(s,v));a=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');ref=npz(ROOT/'stageA'/s/v/'REFERENCE.npz')
  for title,im in [('Original source RGB',raw['rgb']),('Whole-subject proposal + UNKNOWN',overlay(raw['rgb'],a['candidate'],a['unknown'])),('Original C8 xray (NOT mask input)',ref['line_rgb'])]:
   pad=np.ones((800,800,3));h,w=im.shape[:2];pad[:h,:w]=im;overview.append((s+' / '+v+' | '+title,pad))
 panel(out/'OVERVIEW.jpg',overview,'Outside-in pilot | Whole subject first; do not force the next level','scan24/scan65: A NO_GO. Ficus: A proxy GO, B NO_GO. C/D NOT_RUN. Original C8 and source remain intact.',3)
 # Explanatory crops AFTER failure; never used in segmentation/matching/threshold selection.
 crops=[('scan24','0000',[0,70,220,315],'Bright roof is lost to background appearance'),('scan24','0036',[0,260,260,581],'White floor incorrectly enters subject'),('scan65','0000',[0,280,420,581],'Shaded bone loss and tabletop leakage'),('scan65','0036',[0,180,380,581],'Brown table mistaken for subject'),('ficus','test_r_14',[250,70,620,420],'Leaf gaps mostly retained; mixed edges UNKNOWN')]
 for i,(s,v,box,title) in enumerate(crops):
  raw=npz(rawpath(s,v));a=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');x0,y0,x1,y1=box;sl=(slice(y0,y1),slice(x0,x1));panel(out/('FAILURE_DETAIL_'+str(i)+'.jpg'),[('Original pixels',raw['rgb'][sl]),('Proposal / UNKNOWN',overlay(raw['rgb'],a['candidate'],a['unknown'])[sl]),('Binary proposal',grey(a['candidate'])[sl])],title,'Explanatory crop after frozen evaluation; full frames supplied; NOT a selection ROI.',3)
 js(ROOT/'EXPLANATORY_CROPS.json',dict(posthoc_explanation_only=True,never_used_for_algorithm=True,cases=crops))
 js(ROOT/'RENDERER_AUDIT.json',dict(rows=cal,all_N_queries=sum(x['all_N_queries'] for x in cal),new_cuda=False,source_depth_and_center_depth_not_identical=True))
 stats=dict(completed_pilots=1,expected_pilots=1,scenes=3,stageA_units=len(countrows),stageA_cut_solves=len(countrows)*3*3,stageB_scenes=1,stageB_view_arm_units=len(b['rows']),stageB_level_maps=len(b['rows'])*3,stageB_transfer_pair_level_units=len(b['matches']),A_transfer_arm_pairs=len(json.loads((ROOT/'TRANSFER_COUNTS.json').read_text())['rows']),new_Gaussian_models=0,new_physical_primitives=0,source_region_assignments=0,views=countrows,stageA={s:x['stageA'] for s,x in stageA.items()},stageB=dict(scan24='NOT_RUN',scan65='NOT_RUN',ficus='NO_GO'),stageC='NOT_RUN',stageD='NOT_RUN',qualitative_outcome='PARTIAL_SCREEN_SPACE_SCOPE_ONLY')
 js(ROOT/'COUNTS.json',stats);js(ROOT/'SCIENTIFIC_STOP.json',dict(utc=now(),one_pilot_finished=True,no_further_optimization=True,C='NOT_RUN',D='NOT_RUN'))
 state('SCIENTIFIC_PILOT_COMPLETE_VERIFY_PENDING',children=[],completed_pilots=1,scientific_status='PARTIAL',stage_B=stats['stageB'],stage_C='NOT_RUN',stage_D='NOT_RUN')
if __name__=='__main__':run()
