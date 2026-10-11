"""Diagnostic chain-rule decomposition; NEVER a training loss replacement.

Partial terms intentionally hold the opposite factor constant to measure its
individual VJP. Their GRADIENTS add to the unchanged full Eq24 gradient; their
VALUES must not be added to form a loss. No production file imports this module.
"""
from paper_losses import median_depth_normal,normal_consistency

def eq24_diagnostic_parts(alpha,mixed_normal,depth,fx,fy):
    nd=median_depth_normal(depth,fx,fy)
    return {'full':normal_consistency(alpha,mixed_normal,nd),
            'alpha':alpha.mean(),
            'normal':-(mixed_normal*nd.detach()).sum(0).mean(),
            'depth':-(mixed_normal.detach()*nd).sum(0).mean()}
