// Stage-local CPU perspective triangle rasterizer. No GPU or external geometry.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
struct V {double x,y,z;};
static V mix(V a,V b,double t){return {a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),a.z+t*(b.z-a.z)};}
static void triangle(V a,V b,V c,double fx,double fy,double cx,double cy,int w,int h,float* depth,int32_t* winner,int32_t id){
 double ax=a.x/a.z*fx+cx,ay=a.y/a.z*fy+cy,bx=b.x/b.z*fx+cx,by=b.y/b.z*fy+cy,ccx=c.x/c.z*fx+cx,ccy=c.y/c.z*fy+cy;
 double det=(bx-ax)*(ccy-ay)-(by-ay)*(ccx-ax);
 if(!std::isfinite(det)||std::abs(det)<1e-15)return;
 double lowx=std::max(0.,std::min({ax,bx,ccx})),highx=std::min(double(w-1),std::max({ax,bx,ccx}));
 double lowy=std::max(0.,std::min({ay,by,ccy})),highy=std::min(double(h-1),std::max({ay,by,ccy}));
 if(lowx>highx||lowy>highy)return;
 int x0=int(std::ceil(lowx)),x1=int(std::floor(highx)),y0=int(std::ceil(lowy)),y1=int(std::floor(highy));
 for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
  double u=((x-ax)*(ccy-ay)-(y-ay)*(ccx-ax))/det;
  double v=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/det;
  double t=1-u-v;
  if(u>=-1e-10&&v>=-1e-10&&t>=-1e-10){
   double invz=t/a.z+u/b.z+v/c.z;
   if(invz<=0)continue;
   float z=float(1/invz);int p=y*w+x;
   if(z<depth[p]){depth[p]=z;winner[p]=id;}
  }
 }
}
extern "C" void raster_mesh(const double* points,int64_t nv,const int32_t* faces,int64_t nf,int w,int h,double fx,double fy,double cx,double cy,double near,float* depth,int32_t* winner){
 for(int64_t i=0;i<int64_t(w)*h;i++){depth[i]=std::numeric_limits<float>::infinity();winner[i]=-1;}
 for(int64_t i=0;i<nf;i++){
  V input[3];bool valid=true;
  for(int j=0;j<3;j++){int32_t k=faces[3*i+j];if(k<0||k>=nv){valid=false;break;}input[j]={points[3*k],points[3*k+1],points[3*k+2]};}
  if(!valid)continue;
  // Sutherland-Hodgman clipping against the camera near plane.
  V output[5];int n=0;
  for(int j=0;j<3;j++){
   V a=input[j],b=input[(j+1)%3];bool ia=a.z>=near,ib=b.z>=near;
   if(ia)output[n++]=a;
   if(ia!=ib)output[n++]=mix(a,b,(near-a.z)/(b.z-a.z));
  }
  for(int j=1;j<n-1;j++)triangle(output[0],output[j],output[j+1],fx,fy,cx,cy,w,h,depth,winner,int32_t(i));
 }
}
