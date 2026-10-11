"""Minimal headless/durable C24 train patch; applies only to new official source."""
def patch(s):
 if 'official_runtime' in s:raise ValueError('already patched')
 def replace(a,b):
  nonlocal s
  if s.count(a)!=1:raise ValueError('unexpected C24 anchor '+a[:70])
  s=s.replace(a,b,1)
 replace('from scene.cameras import Camera','from scene.cameras import Camera\nfrom official_runtime import OfficialRuntime, finite_tree\nfrom masked_division import distortion_quotient, expected_depth_quotient')
 replace('checkpoint, debug_from):','checkpoint, debug_from, runtime_config):')
 replace('    first_iter = 0','    runtime = OfficialRuntime(runtime_config)\n    first_iter = 0')
 replace('    viewpoint_stack = None','    first_iter, viewpoint_stack = runtime.restore(gaussians, opt, trainCameras)')
 start=s.index('        if network_gui.conn == None:');end=s.index('        iter_start.record()',start)
 s=s[:start]+'        # Headless run: no network GUI socket/remote camera control.\n        runtime.guard(gaussians, "before_render")\n\n'+s[end:]
 replace('        rendered_image: torch.Tensor','        finite_tree(render_pkg, "render_outputs")\n        rendered_image: torch.Tensor')
 replace('torch.where(rendered_mask>0,depth_distortion/(rendered_mask * rendered_mask).detach(),0)','distortion_quotient(depth_distortion, rendered_mask)')
 replace('            rendered_depth = rendered_depth / rendered_mask\n            rendered_depth = torch.nan_to_num(rendered_depth, 0, 0)','            rendered_depth = expected_depth_quotient(rendered_depth, rendered_mask)')
 replace('        loss.backward()','        finite_tree(loss, "total_loss")\n        loss.backward()\n        runtime.guard(gaussians, "after_backward", gradients=True)')
 anchor='                torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")'
 replace(anchor,anchor+'\n\n            runtime.completed_step(iteration, gaussians, viewpoint_stack, {"photo": rgb_loss, "distortion": distortion_loss, "normal": depth_normal_loss, "total": loss}, rendered_mask)\n    runtime.finished(gaussians)')
 return s
