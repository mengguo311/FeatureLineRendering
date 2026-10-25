"""Cross two saved material layouts with two corresponding carrier embeddings.

First letter is layout source, second letter is embedding. No correspondence
between the two layout families is assumed; only each family is transported.
"""
import runtime
from embedding import migrate


def cross_layouts(original_paths, denoised_paths, original, denoised,
                  original_offset, denoised_offset):
    oc, ro = migrate(original_paths, original, denoised, original_offset)
    co, rc = migrate(denoised_paths, denoised, original, denoised_offset)
    paths = dict(OO={k:v.copy() for k,v in original_paths.items()}, OC=oc,
                 CO=co, CC={k:v.copy() for k,v in denoised_paths.items()})
    records = dict(OC=ro, CO=rc)
    for arm, rows in records.items():
        for row in rows:
            row['immediate_saved_layout_id'] = row.pop('immediate_H_parent_id')
            row['layout_source'] = arm[0]
            row['embedding'] = arm[1]
            row['scope'] = 'Same face/bary material coordinates; no cross-family stroke correspondence or Gaussian ownership.'
    original_ids = set(original_paths['stroke_id']) | set(denoised_paths['stroke_id'])
    if original_ids & (set(oc['stroke_id']) | set(co['stroke_id'])):
        raise ValueError('new identity overlaps either saved family')
    if set(oc['stroke_id']) & set(co['stroke_id']):
        raise ValueError('crossed identity namespaces overlap')
    return paths, records
