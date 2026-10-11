"""C24 RGB covariance VJP algebra, checked against independent scalar autograd."""
import torch

def backward(a,b,c,dx,dy,opacity,u):
 det=a*c-b*b;coef=torch.sqrt(det/(det+1e-6)+1e-6);G=torch.exp(-.5*(c*dx*dx-2*b*dx*dy+a*dy*dy)/det)
 alpha=opacity*coef*G;gx=-.5*alpha*u*dx*dx;gy=-.5*alpha*u*dx*dy;gz=-.5*alpha*u*dy*dy;packed_grad=u*G
 combined=opacity*coef
 raw_opacity=combined/coef;dcoef=packed_grad*raw_opacity;dsqrt=dcoef*.5/coef;d0=dsqrt/(det+1e-6);d1=-dsqrt*det/((det+1e-6)*(det+1e-6))
 inv=1/(det*det)
 ga=inv*(-c*c*gx+2*b*c*gy+(det-a*c)*gz)+(d0+d1)*c
 gc=inv*(-a*a*gz+2*a*b*gy+(det-a*c)*gx)+(d0+d1)*a
 gb=inv*2*(b*c*gx-(det+2*b*b)*gy+a*b*gz)+(d0+d1)*(-2*b)
 return torch.stack([ga,gb,gc])
