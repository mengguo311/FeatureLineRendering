def validate_partition(scene):
 roles=scene['roles'];allkeys=sum((roles[k] for k in ('construction','dev','reserved')),[])
 if len(set(allkeys))!=len(allkeys) or not set(allkeys)<=set(scene['cameras']):raise ValueError('role overlap/missing filename')
 return True
def camera_for(scene,key,action,sealed=False):
 validate_partition(scene)
 if action=='extract' and key not in scene['roles']['construction']:raise PermissionError('construction only')
 if action=='develop' and key not in scene['roles']['dev']:raise PermissionError('DEV only')
 if action=='eval' and (key not in scene['roles']['reserved'] or not sealed):raise PermissionError('reserved requires sealed geometry')
 return scene['cameras'][key]
