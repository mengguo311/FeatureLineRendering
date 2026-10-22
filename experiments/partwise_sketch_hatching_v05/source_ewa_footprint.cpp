// Opt-in all-pixel original-kernel footprint accumulation. Acceptance arithmetic unchanged.
#include <cmath>
#include <algorithm>
#include <vector>
#include <numeric>
#include <cstdint>
struct Event {int64_t sample,source,local;double alpha,T,weight,depth,z;};
static std::vector<Event> events;
static int64_t overflow=0;
static const int32_t* footprint_category=nullptr;
static const double* footprint_depth=nullptr;
static const unsigned char* footprint_valid=nullptr;
static double* footprint_stats=nullptr;
extern "C" void footprint_config(const int32_t* category,const double* depth,const unsigned char* valid,double* stats){
 footprint_category=category;footprint_depth=depth;footprint_valid=valid;footprint_stats=stats;
}
extern "C" int64_t link_event_count(){return events.size();}
extern "C" int64_t link_overflow_count(){return overflow;}
extern "C" void link_copy_events(int64_t* ids,double* values){
 for(size_t k=0;k<events.size();k++){
  const auto &e=events[k];ids[3*k]=e.sample;ids[3*k+1]=e.source;ids[3*k+2]=e.local;
  values[5*k]=e.alpha;values[5*k+1]=e.T;values[5*k+2]=e.weight;values[5*k+3]=e.depth;values[5*k+4]=e.z;
 }
}
extern "C" void source_ewa_link(int n,int h,int w,const double* uv,const double* z,const double* S,const double* plane,const double* op,const double* col,double fx,double fy,double* rgb,double* alpha,double* median,double* center,double* expected,const int64_t* source_ids,const int32_t* sample_map,const double* strength,double* contribution,int64_t max_events){
 events.clear();overflow=0;if(footprint_stats)std::fill(footprint_stats,footprint_stats+5*n,0.);std::fill(contribution,contribution+h*w,0.);
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
   if(sample_map && sample_map[k]>=0){
    if(int64_t(events.size())<max_events)events.push_back({sample_map[k],source_ids[i],i,al,T[k],weight,depth,z[i]});else overflow++;
   }
   if(footprint_stats){
    int category=footprint_category[k];
    footprint_stats[5*i]+=weight;
    footprint_stats[5*i+1+category]+=weight;
    if(category==0 && footprint_valid[k] && std::isfinite(depth) && std::abs(depth-footprint_depth[k])<=.06)footprint_stats[5*i+4]+=weight;
   }
   if(strength)contribution[k]+=weight*strength[i];
   for(int j=0;j<3;j++)rgb[3*k+j]+=weight*col[3*i+j];
   if(std::isfinite(depth)&&depth>.2){expected[k]+=weight*depth;if(T[k]>.5){median[k]=depth;center[k]=z[i];}}
   T[k]=next;
  }
 }
 for(int k=0;k<h*w;k++){alpha[k]=1-T[k];if(alpha[k]>0)expected[k]/=alpha[k];for(int j=0;j<3;j++)rgb[3*k+j]+=T[k];}
}
