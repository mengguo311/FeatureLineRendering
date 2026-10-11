"""Separate negative eval-cull review from earlier TSDF-empty review; fail closed."""
import hashlib,json
from pathlib import Path
def validate_review(review,parent_scene):
 if review.get('decision')!='CONTINUE_SAME_FROZEN_METHOD_TO_NEXT_EXPLICIT_SCENE' or review.get('direct_failure_explained') is not True or review.get('failure_stage')!='eval':raise ValueError('unexplained or wrong-stage continuation review')
 p=Path(review['confirmed_negative_result']);data=p.read_bytes()
 if hashlib.sha256(data).hexdigest()!=review['result_sha256']:raise ValueError('result status hash mismatch')
 result=json.loads(data)
 if result.get('scene')!=parent_scene or result.get('status')!='NEGATIVE_GEOMETRY_EMPTY_AFTER_AUTHOR_MASK_CONFIRMED' or result.get('GPU_original_cull_verified') is not True or result.get('official_metric') is not None or set(result.get('verified_stages',[]))!={'smoke','train','export','tsdf'}:raise ValueError('negative author-cull proof incomplete')
 return result
