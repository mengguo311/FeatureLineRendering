#include <cmath>
#include <vector>
#include <algorithm>
#include <numeric>
extern "C" void ewa(int n,int h,int w,const double* uv,const double* z,const double* cov,const double* opacity,const double* colors,const double* bg,double* rgb,double* alpha,double* median,double* expected){
 std::vector<int> order(n);std::iota(order.begin(),order.end(),0);std::stable_sort(order.begin(),order.end(),[&](int a,int b){return z[a]<z[b];});
 std::vector<double> trans(h*w,1);std::fill(rgb,rgb+h*w*3,0);std::fill(median,median+h*w,0);std::fill(expected,expected+h*w,0);
 for(int i:order){
  if(!std::isfinite(z[i])||z[i]<=.2||opacity[i]<=0)continue;
  double a=cov[4*i],b=cov[4*i+1],c=cov[4*i+3],det=a*c-b*b;
  if(!(det>1e-18)||!std::isfinite(det))continue;
  double u=uv[2*i],v=uv[2*i+1],rx=3*std::sqrt(a),ry=3*std::sqrt(c);
  if(!std::isfinite(u)||!std::isfinite(v)||u+rx<0||v+ry<0||u-rx>w-1||v-ry>h-1)continue;
  int x0=(int)std::max(0.,std::ceil(u-rx)),x1=(int)std::min(double(w-1),std::floor(u+rx));
  int y0=(int)std::max(0.,std::ceil(v-ry)),y1=(int)std::min(double(h-1),std::floor(v+ry));
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
   int k=y*w+x;if(trans[k]<1e-5)continue;
   double dx=x-u,dy=y-v,q=(c*dx*dx-2*b*dx*dy+a*dy*dy)/det;if(q>9)continue;
   double al=std::min(.999,std::max(0.,opacity[i]*std::exp(-q/2))),weight=trans[k]*al;
   for(int j=0;j<3;j++)rgb[3*k+j]+=weight*colors[3*i+j];expected[k]+=weight*z[i];
   if(trans[k]>.5 && trans[k]*(1-al)<=.5)median[k]=z[i];trans[k]*=(1-al);
  }
 }
 for(int k=0;k<h*w;k++){alpha[k]=1-trans[k];if(alpha[k]>0)expected[k]/=alpha[k];for(int j=0;j<3;j++)rgb[3*k+j]+=trans[k]*bg[j];}
}
