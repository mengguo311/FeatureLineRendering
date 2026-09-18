// Exact inherited query; avoid OpenMP barriers for tiny local calls.
#include <algorithm>
#include <cmath>
#include <cstdint>
extern "C" void multiscene_layer_query(int n,int pixels,const int64_t* offsets,
    const float* zs,const float* ts,const int64_t* pixel,const double* depth,
    double delta,double* front,uint8_t* support) {
    #pragma omp parallel for schedule(static) if(n>=2048)
    for(int i=0;i<n;++i) {
        support[i]=0;front[i]=1;
        if(pixel[i]<0||pixel[i]>=pixels||!std::isfinite(depth[i]))continue;
        auto begin=offsets[pixel[i]],end=offsets[pixel[i]+1];
        if(begin==end)continue;
        const float* f=std::lower_bound(zs+begin,zs+end,depth[i]-2*delta);
        if(f>zs+begin)front[i]=ts[f-zs-1];
        double mass=1-ts[end-1];
        auto lo=begin,hi=end-1;
        while(lo<end-1&&(1-ts[lo])<.05*mass)++lo;
        while(hi>lo&&(1-ts[hi-1])>=.95*mass)--hi;
        const float* at=std::lower_bound(zs+lo,zs+hi+1,depth[i]);
        if(at<zs+hi+1&&std::abs(*at-depth[i])<=2*delta)support[i]=1;
        if(at>zs+lo&&std::abs(*(at-1)-depth[i])<=2*delta)support[i]=1;
    }
}
