from contact_soft_delivery import *
from contact_soft_delivery import freeze_references as previous_freeze

def freeze_references(c,d,stage,binding,guard):
 previous_freeze(c,d,stage,binding,guard)
 d['_fixed_references']={'UNIT011_START':d['_fixed_references']['UNIT010_START']}
 d['_reference_binding']={'UNIT011_START':d['_reference_binding']['UNIT010_START']}
