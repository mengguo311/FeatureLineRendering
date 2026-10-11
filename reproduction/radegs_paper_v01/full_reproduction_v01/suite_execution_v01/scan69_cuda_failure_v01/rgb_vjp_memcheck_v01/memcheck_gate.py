import re

def validate(returncode,log,result):
    counts=re.findall(r'ERROR SUMMARY:\s*(\d+) errors',log)
    if returncode!=0 or counts!=['0']:
        raise ValueError('memcheck did not terminate with exactly one zero-error summary')
    if result.get('status')!='NO_NONFINITE_FOUND_THROUGH1000' or result.get('last_completed')!=1000:
        raise ValueError('fresh 0..1000 finite replay not completed')
    return True
