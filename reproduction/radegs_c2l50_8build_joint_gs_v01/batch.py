from common import *
from produce import export,load_model,render_view
import traceback
def main():
 results=[];failures=[];state('STATIC_THREE_SCENE_BATCH',status='RUNNING',worker_pid=os.getpid(),children=[])
 for s in SCENES:
  try:
   guard();model=export(s);loaded=load_model(s);rows=[]
   for v in registry()[s]['display_views']:
    rows.append(render_view(s,v,loaded));js(ROOT/'BATCH_PROGRESS.json',dict(completed_scenes=results,current_scene=s,completed_current_views=[r['view'] for r in rows],failures=failures))
   del loaded
   results.append(dict(scene=s,model=model,views=rows));js(ROOT/('ROLLBACK_AFTER_'+s+'.json'),rollback())
  except Exception:
   failures.append(dict(scene=s,traceback=traceback.format_exc()));js(ROOT/'BATCH_FAILURES.json',failures)
  js(ROOT/'BATCH_PROGRESS.json',dict(completed_scenes=results,failures=failures))
 js(ROOT/'COUNTS.json',dict(expected_scenes=3,completed_scenes=len(results),scenes=results,failures=failures));state('STATIC_COMPLETE',status='PARTIAL' if failures else 'STATIC_READY_FOR_REVIEW',completed_scenes=len(results),completed_cameras=sum(len(r['views']) for r in results),worker_pid=None,children=[]);assert not failures
if __name__=='__main__':main()
