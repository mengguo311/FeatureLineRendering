#include <algorithm>
#include <cmath>
#include <cstdint>
extern "C" void contribution_weights(int h,int w,const float* xy,const float* conic,
    const uint32_t* ids,const uint32_t* ranges,double* weights) {
    // Serial fixed-order summation: deterministic across thread counts.
    for(int p=0;p<h*w;++p) {
        int x=p%w,y=p/w,tile=(y/16)*((w+15)/16)+x/16;float T=1;
        for(uint32_t j=ranges[2*tile];j<ranges[2*tile+1];++j) {
            auto i=ids[j];float dx=xy[2*i]-x,dy=xy[2*i+1]-y;const float* co=conic+4*i;
            float power=-.5f*(co[0]*dx*dx+co[2]*dy*dy)-co[1]*dx*dy;
            if(power>0)continue;float a=std::min(.99f,co[3]*std::exp(power));
            if(a<1.f/255.f)continue;float next=T*(1-a);if(next<.0001f)break;
            weights[i]+=double(a*T);T=next;
        }
    }
}
