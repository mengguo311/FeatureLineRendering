// Read the pinned CUDA sorted tile stream, without projection or sorting.
#include <algorithm>
#include <cmath>
#include <cstdint>

extern "C" void adaptive_mass_csr(int h,int w,int k,double tau,
    const float* xy,const float* conic,const float* depth,const float* rgb,
    const uint32_t* ids,const uint32_t* ranges,const float* native_T,
    int64_t* sizes,const int64_t* offsets,int64_t* outid,int64_t* positions,
    float* events,double* tail,int64_t* counts) {
    #pragma omp parallel for schedule(static)
    for(int p=0;p<h*w;++p) {
        int x=p%w,y=p/w,tile=(y/16)*((w+15)/16)+x/16;
        float T=1;int64_t n=0,stored=0;double mass=0;
        const double target=tau*(1.-double(native_T[p]));
        for(uint32_t j=ranges[2*tile];j<ranges[2*tile+1];++j) {
            auto i=ids[j];float dx=xy[2*i]-x,dy=xy[2*i+1]-y;
            const float* co=conic+4*i;
            float power=-.5f*(co[0]*dx*dx+co[2]*dy*dy)-co[1]*dx*dy;
            if(power>0)continue;
            float a=std::min(.99f,co[3]*std::exp(power));
            if(a<1.f/255.f)continue;
            float next=T*(1-a);
            if(next<.0001f)break;
            float weight=a*T;
            if(stored<k && mass<target) {
                if(events) {
                    auto q=offsets[p]+stored;outid[q]=i;positions[q]=j;
                    float* e=events+q*7;e[0]=depth[i];e[1]=a;e[2]=T;e[3]=weight;
                    for(int c=0;c<3;++c)e[4+c]=rgb[3*i+c];
                }
                ++stored;mass+=weight;
            } else if(tail) {
                for(int c=0;c<3;++c)tail[5*p+c]+=double(weight)*rgb[3*i+c];
                tail[5*p+3]+=weight;
            }
            ++n;T=next;
        }
        sizes[p]=stored;counts[p]=n;if(tail)tail[5*p+4]=T;
    }
}
