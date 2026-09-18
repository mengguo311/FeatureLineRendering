// Read-only replay of native stock buffers; no independently approximated splats.
// Rules audited against GRAPHDECO forward.cu @59f5f77 (research-only upstream).
#include <cmath>
#include <cstdint>
#include <algorithm>
#include <vector>
extern "C" void foundation_composite(int h,int w,const float* xy,const float* conic,
    const float* colors,const float* depths,const uint32_t* ids,const uint32_t* ranges,
    const uint8_t* selected,const uint8_t* outside,float background,float* result) {
    #pragma omp parallel for schedule(static)
    for(int p=0;p<h*w;p++) {
        int x=p%w,y=p/w,tile=(y/16)*((w+15)/16)+x/16;
        float T=1, C[3]={0,0,0}, sel=0, ext=0;
        std::vector<float> ws,zs;
        for(uint32_t j=ranges[2*tile];j<ranges[2*tile+1];j++) {
            uint32_t i=ids[j]; float dx=xy[2*i]-x,dy=xy[2*i+1]-y;
            const float* co=conic+4*i;
            float power=-.5f*(co[0]*dx*dx+co[2]*dy*dy)-co[1]*dx*dy;
            if(power>0) continue;
            float a=std::min(.99f,co[3]*std::exp(power));
            if(a<1.f/255.f) continue;
            float next=T*(1-a);
            if(next<.0001f) break; // stock excludes the triggering splat
            float mass=a*T;
            for(int c=0;c<3;c++) C[c]+=colors[3*i+c]*mass;
            sel+=selected[i]*mass; ext+=outside[i]*mass;
            ws.push_back(mass); zs.push_back(depths[i]); T=next;
        }
        float* o=result+9*p;
        for(int c=0;c<3;c++) o[c]=C[c]+T*background;
        o[3]=1-T; o[4]=sel; o[5]=ext;
        for(int q=0;q<3;q++) {
            float fraction=q==0?.05f:(q==1?.5f:.95f),sum=0;
            o[6+q]=NAN;
            for(size_t j=0;j<ws.size();j++) {
                sum+=ws[j];
                if(sum>=fraction*(1-T)) {o[6+q]=zs[j];break;}
            }
        }
    }
}
