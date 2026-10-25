#include <cmath>
#include <algorithm>
#include <vector>
#include <numeric>
extern "C" void source_ewa(int n,int h,int w,const double* uv,const double* z,const double* S,const double* plane,const double* op,const double* col,double fx,double fy,double* rgb,double* alpha,double* median,double* center,double* expected){
 std::vector<int> order(n);std::iota(order.begin(),order.end(),0);std::stable_sort(order.begin(),order.end(),[&](int a,int b){return z[a]<z[b];});
 std::vector<double> T(h*w,1.);std::vector<unsigned char> done(h*w,0);std::fill(rgb,rgb+3*h*w,0.);std::fill(median,median+h*w,0.);std::fill(center,center+h*w,0.);std::fill(expected,expected+h*w,0.);
 for(int i:order){
  if(!std::isfinite(z[i])||z[i]<=.2||op[i]<=0)continue;
  double a=S[4*i],b=S[4*i+1],c=S[4*i+3],det=a*c-b*b;if(!(det>1e-18)||!std::isfinite(det))continue;
  double mid=.5*(a+c),lambda=mid+std::sqrt(std::max(.1,mid*mid-det));double radius=std::ceil(3*std::sqrt(lambda));double u=uv[2*i],v=uv[2*i+1];if(!std::isfinite(u+v)||u+radius<0||v+radius<0||u-radius>w||v-radius>h)continue;
  int x0=std::max(0,int(std::floor((u-radius)/16))*16),x1=std::min(w-1,(int(std::floor((u+radius)/16))+1)*16-1);
  int y0=std::max(0,int(std::floor((v-radius)/16))*16),y1=std::min(h-1,(int(std::floor((v+radius)/16))+1)*16-1);
  for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
   int k=y*w+x;if(done[k])continue;double dx=x-u,dy=y-v,q=(c*dx*dx-2*b*dx*dy+a*dy*dy)/det;if(q<0)continue;
   double al=std::min(.99,op[i]*std::exp(-q/2));if(al<1./255)continue;double next=T[k]*(1-al);if(next<.0001){done[k]=1;continue;}
   double weight=T[k]*al,depth=z[i]-plane[2*i]*dx/fx-plane[2*i+1]*dy/fy;
   for(int j=0;j<3;j++)rgb[3*k+j]+=weight*col[3*i+j];
   if(std::isfinite(depth)&&depth>.2){expected[k]+=weight*depth;if(T[k]>.5){median[k]=depth;center[k]=z[i];}}
   T[k]=next;
  }
 }
 for(int k=0;k<h*w;k++){alpha[k]=1-T[k];if(alpha[k]>0)expected[k]/=alpha[k];for(int j=0;j<3;j++)rgb[3*k+j]+=T[k];}
}
