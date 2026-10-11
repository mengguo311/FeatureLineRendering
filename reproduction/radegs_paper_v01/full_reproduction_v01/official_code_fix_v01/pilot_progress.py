"""Counts are real records and verified seals, never wrapper counters."""
def progress(state,iteration,verified):
 status=state['status'];counts={'train_started':int(iteration>0),'train_completed':int('train' in verified),'export_completed':int('export' in verified),'mesh_completed':int('tsdf' in verified),'official_metrics':int('eval' in verified)}
 action='Observe durable runner; do not launch duplicate GPU work or expand scenes'
 if status=='ENGINEERING_NOT_READY':action='Review preserved stage failure; no automatic retry or new scene'
 elif 'eval' in verified:action='Review actual scan24 geometry, metric and visuals before any scene expansion'
 return {'status':status,'actual_counts':counts,'last_completed_iteration_record':iteration,'verified_stages':sorted(verified),'scientificdone':False,'full_suite_completed':False,'next_action':action}
