"""Bounded diagnostic prefix only; never finish the scientific training run."""
class ReplayComplete(Exception):pass
class ReplayLimit:
 def __init__(self,start,end):
  if end<=start:raise ValueError('invalid diagnostic interval')
  self.start,self.last,self.end=start,start,end
 def completed(self,iteration):
  if iteration!=self.last+1 or iteration>self.end:raise ValueError('nonsequential diagnostic iteration')
  self.last=iteration
  if iteration==self.end:raise ReplayComplete('bounded replay reached target without reproduced failure')
 def resume(self,iteration):
  if not self.start<=iteration<=self.end:raise ValueError("resume outside diagnostic bound")
  self.last=iteration
  if iteration==self.end:raise ReplayComplete("bounded replay already checkpointed at target")
