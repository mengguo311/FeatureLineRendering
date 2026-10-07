"""RaDe-GS v2 text variant: Eq.23/Eq.24, never the C24 normalized losses.

Image mean and C24 central-difference/zero-border convention are explicit
engineering defaults; the paper does not fully specify these reductions.
"""
import torch
import torch.nn.functional as F


def distortion_reference(depths, weights):
    weights = weights.detach()
    return (weights[:, None]*weights[None, :]*(depths[:, None]-depths[None, :]).square()).sum()


def normal_consistency(alpha, blended_normal, depth_normal):
    # sum_i w_i(1 - n_i dot n_depth) = alpha - blended_normal dot n_depth.
    # Neither alpha nor the blended normal is normalized or detached.
    return (alpha.squeeze(0) - (blended_normal*depth_normal).sum(dim=0)).mean()


def geometry_active(iteration):
    if not 1 <= iteration <= 30000:
        raise ValueError('pilot iteration outside 1..30000')
    return iteration > 15000


def median_depth_normal(depth, focal_x, focal_y):
    _, height, width = depth.shape
    y, x = torch.meshgrid(torch.arange(height, device=depth.device, dtype=depth.dtype),
                          torch.arange(width, device=depth.device, dtype=depth.dtype), indexing='ij')
    rays = torch.stack(((x+.5-width/2)/focal_x, (y+.5-height/2)/focal_y, torch.ones_like(x)),dim=0)
    points = (depth*rays).permute(1,2,0)
    dx = points[2:,1:-1] - points[:-2,1:-1]
    dy = points[1:-1,2:] - points[1:-1,:-2]
    normal = F.normalize(torch.cross(dx,dy,dim=-1),p=2,dim=-1).permute(2,0,1)
    return F.pad(normal,(1,1,1,1),value=0)


def geometry_losses(render_pkg, camera):
    import math
    focal_x = camera.image_width / (2*math.tan(camera.FoVx/2))
    focal_y = camera.image_height / (2*math.tan(camera.FoVy/2))
    normal = median_depth_normal(render_pkg['middepth'], focal_x, focal_y)
    return (render_pkg['depth_distortion'].mean(),
            normal_consistency(render_pkg['mask'], render_pkg['normal'], normal))
