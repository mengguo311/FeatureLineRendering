#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

extern "C" void adaptive_pairs(int h,int w,const int64_t* off,const double* z,const double* weight,
 const int64_t* histid,const double* histw,const int64_t* histrank,const double* mass,const double* depth,
 const double* scale,float* output) {
 const int dy[8]={-1,-1,-1,0,0,1,1,1},dx[8]={-1,0,1,-1,1,-1,0,1};
 #pragma omp parallel for schedule(static)
 for(int p=0;p<h*w;++p) for(int dir=0;dir<8;++dir) {
  int y=p/w+dy[dir],x=p%w+dx[dir];if(y<0||y>=h||x<0||x>=w)continue;int q=y*w+x;
  int64_t a=off[p],ae=off[p+1],b=off[q],be=off[q+1];if(a==ae||b==be)continue;
  double A=0,B=0;for(auto i=a;i<ae;++i)A+=weight[i];for(auto j=b;j<be;++j)B+=weight[j];
  if(A<=0||B<=0)continue;
  float* out=output+(int64_t(p)*8+dir)*9;double bc=0,layerbc[4][4]={};
  auto i=a,j=b;
  while(i<ae&&j<be){
   if(histid[i]<histid[j]){++i;continue;}if(histid[j]<histid[i]){++j;continue;}
   auto id=histid[i];double wa=0,wb=0,la[4]={},lb[4]={};
   while(i<ae&&histid[i]==id){wa+=histw[i];if(histrank[i]<4)la[histrank[i]]+=histw[i];++i;}
   while(j<be&&histid[j]==id){wb+=histw[j];if(histrank[j]<4)lb[histrank[j]]+=histw[j];++j;}
   bc+=std::sqrt(wa*wb/(A*B));
   for(int l=0;l<4;++l)for(int m=0;m<4;++m)if(mass[4*p+l]>0&&mass[4*q+m]>0)
    layerbc[l][m]+=std::sqrt(la[l]*lb[m]/(mass[4*p+l]*mass[4*q+m]));
  }
  double pairscale=std::max(scale[p],scale[q]);
  out[0]=std::min(1.,bc);
  i=a;j=b;double ca=0,cb=0,previous=std::min(z[i],z[j]),distance=0;
  while(i<ae||j<be){double at=i<ae?(j<be?std::min(z[i],z[j]):z[i]):z[j];
   distance+=std::abs(ca-cb)*(at-previous);
   while(i<ae&&z[i]==at){ca+=weight[i]/A;++i;}while(j<be&&z[j]==at){cb+=weight[j]/B;++j;}previous=at;
  }
  out[1]=distance;out[2]=std::abs(z[a]-z[b])/pairscale;
  out[3]=std::min(A,B);out[4]=std::min(mass[4*p]/A,mass[4*q]/B);
  for(int l=0;l<4;++l){int match=-1;double best=3*pairscale;
   for(int m=0;m<4;++m)if(mass[4*q+m]>0&&std::abs(depth[4*p+l]-depth[4*q+m])<=best&&(match<0||std::abs(depth[4*p+l]-depth[4*q+m])<best)){best=std::abs(depth[4*p+l]-depth[4*q+m]);match=m;}
   if(match>=0)out[5+l]=std::min(1.,layerbc[l][match]);
  }
 }
}

extern "C" void adaptive_matched_hessian(int h,int w,double sigma,const double* depth,
 const double* mass,const double* scale,const uint8_t* seed,float* output) {
 int radius=int(std::ceil(4*sigma));double s2=sigma*sigma;
 std::vector<double> kernel((2*radius+1)*(2*radius+1)*6);
 for(int y=-radius;y<=radius;++y)for(int x=-radius;x<=radius;++x){
  double g=std::exp(-.5*(x*x+y*y)/s2);int k=((y+radius)*(2*radius+1)+x+radius)*6;
  kernel[k]=g;kernel[k+1]=g*x/s2;kernel[k+2]=g*y/s2;
  kernel[k+3]=g*(x*x/s2-1)/s2;kernel[k+4]=g*x*y/(s2*s2);kernel[k+5]=g*(y*y/s2-1)/s2;
 }
 #pragma omp parallel for schedule(static)
 for(int p=0;p<h*w;++p)for(int l=0;l<4;++l){
  if(!seed[4*p+l])continue;double target=depth[4*p+l],S[6]={},N[6]={};
  for(int dy=-radius;dy<=radius;++dy){int y=p/w+dy;if(y<0||y>=h)continue;
   for(int dx=-radius;dx<=radius;++dx){int x=p%w+dx;if(x<0||x>=w)continue;int q=y*w+x;
    double best=3*std::max(scale[p],scale[q]);int match=-1;
    for(int m=0;m<4;++m){if(mass[4*q+m]<=0)break;double dist=std::abs(depth[4*q+m]-target);
     if(dist<=best&&(match<0||dist<best)){best=dist;match=m;}}
    if(match<0)continue;double v=depth[4*q+match]-target;
    auto k=((dy+radius)*(2*radius+1)+dx+radius)*6;
    for(int c=0;c<6;++c){S[c]+=kernel[k+c];N[c]+=kernel[k+c]*v;}
   }
  }
  if(S[0]<=0)continue;
  double f=N[0]/S[0],fx=(N[1]-f*S[1])/S[0],fy=(N[2]-f*S[2])/S[0];
  float* out=output+(int64_t(p)*4+l)*4;
  out[0]=s2*(N[3]-f*S[3]-2*fx*S[1])/S[0]/scale[p];
  out[1]=s2*(N[4]-f*S[4]-fx*S[2]-fy*S[1])/S[0]/scale[p];
  out[2]=s2*(N[5]-f*S[5]-2*fy*S[2])/S[0]/scale[p];out[3]=f+target;
 }
}

extern "C" void adaptive_hysteresis(int h,int w,double low,const float* response,const double* angle,
 const double* sigma,const double* depth,const double* scale,const float* bc,const uint8_t* anchors,
 uint8_t* center,uint8_t* band) {
 const int dy[8]={-1,-1,-1,0,0,1,1,1},dx[8]={-1,0,1,-1,1,-1,0,1};
 std::vector<int> queue;queue.reserve(h*w/4);
 for(int p=0;p<h*w;++p)if(anchors[p]){center[p]=1;queue.push_back(p);}
 for(size_t at=0;at<queue.size();++at){int p=queue[at];
  for(int dir=0;dir<8;++dir){int y=p/w+dy[dir],x=p%w+dx[dir];if(y<0||y>=h||x<0||x>=w)continue;int q=y*w+x;
   if(center[q]||response[q]<low||response[q]<=0||bc[8*p+dir]<.25)continue;
   if(std::abs(std::cos(angle[p]-angle[q]))<std::cos(M_PI/6))continue;
   double step=std::atan2(dy[dir],dx[dir]);
   if(std::abs(std::cos(step-angle[p]))<std::cos(M_PI/4)-1e-12||std::abs(std::cos(step-angle[q]))<std::cos(M_PI/4)-1e-12)continue;
   if(std::abs(depth[p]-depth[q])>3*std::max(scale[p],scale[q]))continue;
   center[q]=1;queue.push_back(q);
  }
 }
 for(int p:queue){int radius=int(std::ceil(sigma[p]));
  for(int y=std::max(0,p/w-radius);y<=std::min(h-1,p/w+radius);++y)
   for(int x=std::max(0,p%w-radius);x<=std::min(w-1,p%w+radius);++x){
    if((y-p/w)*(y-p/w)+(x-p%w)*(x-p%w)>radius*radius)continue;int q=y*w+x;
    if(response[q]<low||response[q]<=0)continue;
    if(std::abs(depth[p]-depth[q])>3*std::max(scale[p],scale[q]))continue;
    if(std::abs(std::cos(angle[p]-angle[q]))<std::cos(M_PI/6))continue;band[q]=1;
   }
 }
}

// Share only the layer lookup across scales. Each scale retains the original
// lexicographic accumulation order and double arithmetic exactly.
extern "C" void adaptive_matched_hessians(int h,int w,const double* depth,
 const double* mass,const double* scale,const uint8_t* seed,float* output) {
 const int radius=16,radii[3]={6,10,16};const double s2[3]={2.25,6.25,16.};
 std::vector<double> kernel(33*33*18);
 for(int y=-16;y<=16;++y)for(int x=-16;x<=16;++x)for(int s=0;s<3;++s){
  if(std::abs(y)>radii[s]||std::abs(x)>radii[s])continue;
  double g=std::exp(-.5*(x*x+y*y)/s2[s]);int k=((y+16)*33+x+16)*18+s*6;
  kernel[k]=g;kernel[k+1]=g*x/s2[s];kernel[k+2]=g*y/s2[s];
  kernel[k+3]=g*(x*x/s2[s]-1)/s2[s];kernel[k+4]=g*x*y/(s2[s]*s2[s]);kernel[k+5]=g*(y*y/s2[s]-1)/s2[s];
 }
 #pragma omp parallel for schedule(static)
 for(int p=0;p<h*w;++p)for(int l=0;l<4;++l){
  if(!seed[4*p+l])continue;double target=depth[4*p+l],S[3][6]={},N[3][6]={};
  for(int dy=-radius;dy<=radius;++dy){int y=p/w+dy;if(y<0||y>=h)continue;
   for(int dx=-radius;dx<=radius;++dx){int x=p%w+dx;if(x<0||x>=w)continue;int q=y*w+x;
    double best=3*std::max(scale[p],scale[q]);int match=-1;
    for(int m=0;m<4;++m){if(mass[4*q+m]<=0)break;double dist=std::abs(depth[4*q+m]-target);
     if(dist<=best&&(match<0||dist<best)){best=dist;match=m;}}
    if(match<0)continue;double v=depth[4*q+match]-target;
    for(int s=0;s<3;++s){if(std::abs(dy)>radii[s]||std::abs(dx)>radii[s])continue;
     auto k=((dy+radius)*33+dx+radius)*18+s*6;
     for(int c=0;c<6;++c){S[s][c]+=kernel[k+c];N[s][c]+=kernel[k+c]*v;}
    }
   }
  }
  for(int s=0;s<3;++s){if(S[s][0]<=0)continue;double f=N[s][0]/S[s][0],fx=(N[s][1]-f*S[s][1])/S[s][0],fy=(N[s][2]-f*S[s][2])/S[s][0];
   float* out=output+((int64_t(p)*4+l)*3+s)*4;
   out[0]=s2[s]*(N[s][3]-f*S[s][3]-2*fx*S[s][1])/S[s][0]/scale[p];
   out[1]=s2[s]*(N[s][4]-f*S[s][4]-fx*S[s][2]-fy*S[s][1])/S[s][0]/scale[p];
   out[2]=s2[s]*(N[s][5]-f*S[s][5]-2*fy*S[s][2])/S[s][0]/scale[p];out[3]=f+target;
  }
 }
}
