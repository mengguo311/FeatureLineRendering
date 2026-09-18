// Exact area mixture of four already-calibrated native contribution streams.
#include <algorithm>
#include <cmath>
#include <cstdint>
extern "C" void area_layers(int h,int w,const int64_t* offsets,const float* depth,
    const float* weight,int64_t* dest_offsets,float* zs,float* ws,float* ts) {
    int dh=h/2,dw=w/2;
    if(!zs) {
        dest_offsets[0]=0;
        for(int p=0;p<dh*dw;++p) {
            int x=2*(p%dw),y=2*(p/dw);int64_t count=0;
            for(int dy=0;dy<2;++dy)for(int dx=0;dx<2;++dx) {
                int a=(y+dy)*w+x+dx;count+=offsets[a+1]-offsets[a];
            }
            dest_offsets[p+1]=dest_offsets[p]+count;
        }
        return;
    }
    #pragma omp parallel for schedule(static)
    for(int p=0;p<dh*dw;++p) {
        int x=2*(p%dw),y=2*(p/dw);int64_t cursor[4],end[4];int j=0;
        for(int dy=0;dy<2;++dy)for(int dx=0;dx<2;++dx) {
            int a=(y+dy)*w+x+dx;cursor[j]=offsets[a];end[j++]=offsets[a+1];
        }
        double mass=0;
        for(auto k=dest_offsets[p];k<dest_offsets[p+1];++k) {
            int best=-1;
            for(int i=0;i<4;++i)if(cursor[i]<end[i]&&(best<0||depth[cursor[i]]<depth[cursor[best]]))best=i;
            auto source=cursor[best]++;zs[k]=depth[source];ws[k]=weight[source]*.25f;
            mass+=double(ws[k]);ts[k]=float(std::max(0.,1-mass));
        }
    }
}
extern "C" void area_quantiles(int n,const int64_t* offsets,const float* zs,const float* ws,float* out) {
    #pragma omp parallel for schedule(static)
    for(int p=0;p<n;++p) {
        auto a=offsets[p],b=offsets[p+1];double mass=0;
        for(auto i=a;i<b;++i)mass+=ws[i];
        double cumulative=0;int q=0;double quantiles[3]={.05,.5,.95};
        for(auto i=a;i<b&&q<3;++i) {
            cumulative+=ws[i];
            while(q<3&&cumulative>=mass*quantiles[q])out[p*3+q++]=zs[i];
        }
    }
}
