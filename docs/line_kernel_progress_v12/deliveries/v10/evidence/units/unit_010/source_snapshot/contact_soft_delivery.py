"""Preserve old raw-fit replay separately from the two finite score libraries."""
from group_fit_delivery import *
import group_fit_delivery as inherited
from cohort_support import freeze_references as inherited_freeze,save_diagnostics

def save_library(out,lib):
 clean={k:v for k,v in lib.items() if k!='baseline_fit_library'}
 inherited.save_library(out,clean)

def freeze_references(c,d,stage,binding,guard):
 inherited_freeze(c,d,stage,binding,guard)
 d['_fixed_references']={'UNIT010_START':d['_fixed_references']['UNIT009_START']}
 d['_reference_binding']={'UNIT010_START':d['_reference_binding']['UNIT009_START']}
