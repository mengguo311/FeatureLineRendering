"""Counts come from verified per-scene flags, never wrapper status or mesh."""
def counts(rows):
 result={k:0 for k in ('train_completed','depth_export_completed','depth_review_passed')}
 for row in rows:
  train=row.get('train_completed') is True
  export=row.get('depth_export_completed') is True
  review=row.get('depth_review_passed') is True
  if (export and not train) or (review and not export):raise ValueError('inconsistent completion chain')
  for key in result:result[key]+=int(row.get(key) is True)
 return result

def disk_blocked(guard):
 return bool(guard and guard.get('status')=='LOW_DISK_STOP_REQUESTED')
