from env import *
paths=[ROOT/'stageA'/s/DEV[s]/'SUBJECT_FULL.jpg' for s in SCENES]
rows={'scan24':dict(stage_A_DEV='NO_GO',reason='Actual fullframe: bright left roof facets and eaves are black holes in subject mask; near buildings largely included, scope not uniquely main building. High seed stability does not protect missing roof.',allow_next='frozen fullframe controls / failure transfer only; B/C/D NOT_RUN'), 'scan65':dict(stage_A_DEV='NO_GO',reason='Actual fullframe: table under left jaw leaks into subject, shaded bone/socket/teeth lose support. Cavity appearance not certified background.',allow_next='frozen fullframe controls / failure transfer only; B/C/D NOT_RUN'),'ficus':dict(stage_A_DEV='PROVISIONAL_GO',reason='Actual fullframe: pot, trunks and leaf canopy extent preserved; leaf-edge mixed pixels unknown, inter-leaf gaps mostly preserved; await independent AUX/reserved projections and weak-view visual review.',allow_next='Stage A AUX/reserved qualification only; no B yet')}
js(ROOT/'DEV_VISUAL_REVIEW.json',dict(qualitative_not_GT=True,reviewed_actual_images=[str(x) for x in paths],scenes=rows))
review('02_DEV_review_GO_A_only','已实际view_image检查三scene整图。建筑与头骨A视觉NO_GO，即使数值稳定，不进入B/C/D。Ficus整体代理有可读性，尚须AUX/reserved检验；仅GO剩余Stage A冻结规则和投影诊断，无下层结构分区许可。不得把高seed IoU当正确率。',paths+[ROOT/'DEV_VISUAL_REVIEW.json'])
# Read-only inherited joint models and complete frozen dependency manifest.
extra=[]
for s in SCENES:
 p=JOINT/'scenes'/s/'model'
 for n in ['merged_native.ply','RANGES.json','GROUP_MAPPING.npz','AUDIT.json','SEAL.json']:extra.append(p/n)
 ref=json.loads((p/'SEAL.json').read_text())['files'];assert sha(p/'merged_native.ply')==ref['merged_native.ply']
js(ROOT/'DEPENDENCY_MANIFEST.json',dict(files={str(p):sha(p) for p in extra}))
js(ROOT/'CODE_STAGE_A.json',dict(utc=now(),description='Executed core version, recorded after DEV; no earlier-code-hash claim',files={str(p.relative_to(CODE)):sha(p) for p in CODE.glob('*.py')}))
state('DEV_REVIEW_COMPLETE',children=[],stageB='NOT_RUN_PENDING_FICUS_A',scientific_status='PARTIAL_STAGE_A')
