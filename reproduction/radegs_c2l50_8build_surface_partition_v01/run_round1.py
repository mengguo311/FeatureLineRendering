from env import *
from evidence import acquire,ARMS
from visuals import round1_figures
from collections import Counter
if __name__=='__main__':
 review('01_round1_GO','''R1 GO：满秩条件射线解析8个新fixture GREEN，包含倾斜薄椭球非center深度、两层不混、远中心大核、无效协方差、mode有限差分、camera-z与range区别、旋转尺度。真实RED日志保留。
冻结阈值不变，先只跑DEV。保持所有原source alpha*T及center排序，条件支持不足/方差宽标未知。候选增加若null同增，仅PARTIAL不能称面片恢复。工程校准失败单独INVALID，不计科学轮完成；禁止自动读取reserved作调参。''',[ROOT/'PROTOCOL_FREEZE.json',ROOT/'round1/tests/RED.log',ROOT/'round1/tests/GREEN.log',CODE/'conditional.py'])
 rd=ROOT/'round1';js(rd/'CODE_CONFIG_FREEZE.json',dict(code={p.name:sha(p) for p in CODE.glob('*.py')},protocol=sha(ROOT/'PROTOCOL_FREEZE.json')));results=[];failed=[]
 for s in SCENES:
  try:state('ROUND1',round=1,scene=s,status='RUNNING',children=[os.getpid()]);results+=acquire(s,[DEV[s]],rd/'scenes');round1_figures(s,[DEV[s]],rd/'scenes')
  except Exception as e:js(rd/f'INVALID_{s}.json',dict(error=repr(e)));failed.append(s)
 counts=dict(round=1,measurements=len(results),scenes={s:{arm:dict(Counter(r['conditional_role']['role'] for r in results if r['scene']==s and r['arm']==arm)) for arm in ARMS} for s in SCENES},original_line_old=dict(Counter(r['old_role']['role'] for r in results if r['arm']=='line')),original_line_conditional=dict(Counter(r['conditional_role']['role'] for r in results if r['arm']=='line')),failed_scenes=failed,physical_primitives=0)
 js(rd/'COUNTS.json',counts);state('ROUND1_MEASURED',round=1,status='INVALID' if failed else 'READY_FOR_REVIEW',children=[],round_counts=counts);print(json.dumps(counts,indent=2))
 if failed:raise SystemExit(1)
