def validate_records(rows):
 if [r['iteration'] for r in rows]!=list(range(1,30001)):raise ValueError('missing/duplicate/out-of-order iteration')
 for r in rows:
  geom=r['iteration']>=15000;update=r['iteration']<30000
  if (r['geometry_active']!=geom or r['optimizer_updated']!=update or r['wd']!=(100 if geom else 0) or r['wn']!=(.05 if geom else 0)):raise ValueError('C24 schedule violation')
 return {'records':len(rows),'optimizer_updates':sum(r['optimizer_updated'] for r in rows),'geometry_records':sum(r['geometry_active'] for r in rows)}
