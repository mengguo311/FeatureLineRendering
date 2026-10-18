from env import *
from run_stage_a import overlay
r=json.loads((ROOT/'B_COUNTS.json').read_text());items=[];receipts=[]
for arm in ['rgb_depth','rgb_only']:
 row=next(x for x in r['matches'] if x['arm']==arm and x['level']==2 and x['to_view']=='test_r_14')
 for i,j in row['mutual_pairs']:
  for view,gid in [(row['from_view'],i),(row['to_view'],j)]:
   lab=npz(ROOT/'stageB/ficus'/view/(arm+'.npz'))['levels'][-1];mask=lab==gid;yy,xx=np.nonzero(mask);receipts.append(dict(arm=arm,view=view,region_id=gid,bbox_xyxy=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],area=int(mask.sum()),not_semantic_certification=True));items.append((arm+' | '+view+' | region '+str(gid),overlay(npz(rawpath('ficus',view))['rgb'],mask)))
js(ROOT/'MATCH_SCOPE_AUDIT.json',dict(post_frozen_diagnostic=True,records=receipts,note='RGB-only target region20 extends above pot into stems (y316..681). Passing mutual containment does not establish a pure pot part. Earlier concise pot wording refers to dominant area, not exclusive semantic membership.'))
panel(ROOT/'delivery/B_MATCH_SCOPE.jpg',items,'Ficus | The few passing region matches are not certified parts','Original frozen labels only. RGB-only target includes stem extension; no parameters changed.',2)
(ROOT/'B_SCOPE_CLARIFICATION_ZH.md').write_text('补充实际ID范围核查：主RGB-depth level2仅DEV27→test_r_14的23配对，以花盆面为主。RGB-only DEV24→目标20的范围延伸至y316，包含盆上枝干；不能把双向dominant fraction通过称为纯花盆语义分割。前述“花盆整体”是外观主面积的简述，不是排他语义认证。已有gate文件保留，本补充不改算法/阈值/数据。\n')
