"""Prepare blinded material; do not claim that independent review occurred."""
import json,secrets,shutil
from pathlib import Path
import numpy as np
from .foundation import freeze_json


def blind_package(directory,key_path,pairs,seed=None):
    directory=Path(directory);key_path=Path(key_path)
    if directory==key_path.parent or directory in key_path.parents:raise ValueError('identity key must be stored separately')
    directory.mkdir(parents=True,exist_ok=False)
    seed=int.from_bytes(secrets.token_bytes(16),'big') if seed is None else seed
    rng=np.random.default_rng(seed);key=[]
    # One identity flip per pair-group name; all fixed views remain consistent.
    flips={}
    for i,pair in enumerate(pairs):
        group=pair.get('group',pair['name'])
        if group not in flips:flips[group]=bool(rng.integers(0,2))
        order=[pair['left'],pair['right']]
        if flips[group]:order.reverse()
        mapping={}
        for label,path in zip(['A','B'],order):
            dest=directory/f'{i:03d}_{label}.png';shutil.copyfile(path,dest);mapping[label]=str(path)
        key.append(dict(index=i,name=pair['name'],group=group,identities=mapping))
    freeze_json(key_path,dict(seed=seed,pairs=key,independent_reviews_completed=0,author='implementing assistant; not independent'))
    (directory/'README.md').write_text('''# Blinded raw-glyph review package

Independent review is pending. The implementing assistant generated this package
and is not an independent evaluator. No human preference or annotation is claimed.
The identity key is stored separately and must not be given to reviewers.

For each numbered A/B comparison, review the white-background images first.
Record independently whether shape structure is clearer and irrelevant lines are
fewer; allow ties, neither, and unassessable. Then review fixed RGB references and
the preserved TRAIN target/challenge annotations. These prior coarse annotations
are internal candidates, not independently certified cross-view spans. Do not add
labels after viewing outputs to rescue a gate. An empty image is an actual empty
accepted output, not a missing rendering. Matching count/ink limitations are listed
in the accompanying review inventory. Native-count, fixed64 and fixed-ink-prefix
comparisons are distinct; insufficient output never gets padded with guessed ink.

G2 manual precision and G5 require genuinely independent annotation/review. Three
independent reviewers are required for G5; at least two must prefer both clearer
structure and fewer irrelevant lines under the registered rules. This package alone
does not certify those gates. The scientific output is a local observability
probe, not a curve, UDF, final stroke asset or a general geometry reconstruction.
''')
    return key
