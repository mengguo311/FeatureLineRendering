#include <cmath>
#include <algorithm>
#include <vector>
#include <numeric>
extern "C" void ewa(int n,int h,int w,const double* uv,const double* z,const double* cov,const double* opacity,const double* colors,const double* depth,const double* alpha,double focal,double* out){
 std::vector<int> order(n);std::iota(order.begin(),order.end(),0);std::stable_sort(order.begin(),order.end(),[&](int a,int b){return z[a]<z[b];});
 std::vector<double> trans(h*w,1.0);std::fill(out,out+h*w*3,0.0);
 for(int i:order){
  if(!std::isfinite(z[i])||z[i]<=1e-8)continue;
  double a=cov[i*4],b=cov[i*4+1],c=cov[i*4+3],det=a*c-b*b;
  if(!std::isfinite(det)||det<=1e-18)continue;
  double u=uv[2*i],v=uv[2*i+1],rx=3*std::sqrt(a),ry=3*std::sqrt(c);
  if(!std::isfinite(u)||!std::isfinite(v)||u+rx<0||v+ry<0||u-rx>w-1||v-ry>h-1)continue;
  int x0=(int)std::max(0.0,std::ceil(u-rx)),x1=(int)std::min(double(w-1),std::floor(u+rx));
  int y0=(int)std::max(0.0,std::ceil(v-ry)),y1=(int)std::min(double(h-1),std::floor(v+ry));
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
   int k=y*w+x;double dx=x-u,dy=y-v,q=(c*dx*dx-2*b*dx*dy+a*dy*dy)/det;
   if(q>9)continue;
   if(depth&&alpha&&std::isfinite(depth[k])&&depth[k]>0&&std::isfinite(alpha[k])&&alpha[k]>=.5){double tol=std::max(.005*depth[k],2*depth[k]/focal);if(z[i]>depth[k]+tol)continue;}
   double al=std::min(.999,std::max(0.0,opacity[i]*std::exp(-.5*q))),weight=trans[k]*al;
   for(int j=0;j<3;j++)out[3*k+j]+=weight*colors[3*i+j];trans[k]*=(1-al);
  }
 }
 for(int k=0;k<h*w;k++)for(int j=0;j<3;j++)out[k*3+j]+=trans[k];
}
