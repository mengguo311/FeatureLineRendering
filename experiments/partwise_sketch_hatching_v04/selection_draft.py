"""A manual, camera-independent set of proxy faces, committed only once.

Rectangles contribute only frontmost ray hits. Union/difference acts on saved
triangle IDs, never on screen pixels or a fabricated hidden-surface completion.
"""
import runtime
import copy
import numpy as np
from screen_selection import visible_faces


class SelectionDraft:
    def __init__(self, mesh, mesh_sha256, source_region):
        if source_region not in mesh['regions']:
            raise ValueError('unknown source region')
        self.mesh=mesh
        self.mesh_sha256=mesh_sha256
        self.source_region=int(source_region)
        self.face_ids=np.empty(0,np.int32)
        self.steps=[]
        self._previous=[]

    def apply(self, camera, rectangle, operation='add'):
        if operation not in ('replace','add','subtract'):
            raise ValueError('selection operation must be replace, add or subtract')
        if len(self.steps)>=64:
            raise ValueError('save or clear this draft before adding more than 64 steps')
        hits, summary=visible_faces(self.mesh,camera,rectangle,self.source_region,allow_all=True)
        before=self.face_ids
        after=(hits if operation=='replace' else np.union1d(before,hits) if operation=='add'
               else np.setdiff1d(before,hits)).astype(np.int32)
        step=dict(operation=operation,camera=copy.deepcopy(camera),rectangle=summary['rectangle'],
                  visible_hit_faces=len(hits),before_faces=len(before),after_faces=len(after),
                  added_faces=len(np.setdiff1d(after,before)),removed_faces=len(np.setdiff1d(before,after)))
        self._previous.append(before.copy())
        self.steps.append(step)
        self.face_ids=after
        return step

    def undo(self):
        if not self.steps:raise ValueError('no selection step to undo')
        self.face_ids=self._previous.pop()
        self.steps.pop()

    def clear(self):
        self.face_ids=np.empty(0,np.int32)
        self.steps=[]
        self._previous=[]

    def summary(self):
        total=int((self.mesh['regions']==self.source_region).sum())
        return dict(source_region=self.source_region,face_count=len(self.face_ids),source_face_count=total,
                    step_count=len(self.steps),can_commit=0<len(self.face_ids)<total,
                    steps=copy.deepcopy(self.steps))

    def provenance(self):
        return dict(operation='manual_multiview_visible_selection',mesh_sha256=self.mesh_sha256,
                    steps=copy.deepcopy(self.steps),
                    rule='union/difference of frontmost 2x ray-hit whole proxy triangles; no hidden expansion',
                    provenance='manually authored multi-view rectangles; not automatic semantics or a complete-part guarantee')


def replay_recipe(mesh,mesh_sha256,recipe):
    if recipe.get('schema')!='manual_multiview_selection_v1':
        raise ValueError('unsupported selection recipe')
    if recipe.get('mesh_sha256')!=mesh_sha256:
        raise ValueError('selection recipe proxy checksum mismatch')
    if not isinstance(recipe.get('steps'),list) or not 1<=len(recipe['steps'])<=64:
        raise ValueError('selection recipe needs 1 to 64 steps')
    draft=SelectionDraft(mesh,mesh_sha256,recipe['source_region'])
    for step in recipe['steps']:
        draft.apply(step['camera'],step['rectangle'],step['operation'])
    if not draft.summary()['can_commit']:
        raise ValueError('selection must leave nonempty source and target regions')
    return draft
