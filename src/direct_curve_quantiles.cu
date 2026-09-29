// Native-buffer replay on the same CUDA arithmetic backend as stock forward.cu.
// No final_T, n_contrib, stock RGB, scene identity, or fitted assets are inputs.
#include <cuda_runtime.h>
#include <cstdint>
#include <algorithm>

__device__ float splat_alpha(float2 xy,float4 co,float2 pixel) {
    float2 d={xy.x-pixel.x,xy.y-pixel.y};
    float power=-0.5f*(co.x*d.x*d.x+co.z*d.y*d.y)-co.y*d.x*d.y;
    if(power>0.0f) return 0.0f;
    return min(0.99f,co.w*exp(power));
}
__global__ void replay(int h,int w,const float2* xy,const float4* co,
    const float* colors,const float* depths,const uint32_t* ids,const uint2* ranges,
    const uint8_t* selected,const uint8_t* outside,float bg,float* result) {
    int x=blockIdx.x*16+threadIdx.x,y=blockIdx.y*16+threadIdx.y;
    if(x>=w||y>=h)return;
    uint2 range=ranges[blockIdx.y*((w+15)/16)+blockIdx.x];
    float2 pixel={float(x),float(y)};
    float T=1.0f,C[3]={0,0,0},sel=0,ext=0,front=NAN;
    uint32_t end=range.y;
    for(uint32_t j=range.x;j<range.y;j++) {
        uint32_t i=ids[j];float a=splat_alpha(xy[i],co[i],pixel);
        if(a<1.0f/255.0f)continue;
        float next=T*(1-a);
        if(next<0.0001f){end=j;break;}
        if(isnan(front))front=depths[i];
        // Preserve stock multiplication order (color * alpha) * T.
        for(int c=0;c<3;c++)C[c]+=colors[3*i+c]*a*T;
        float mass=a*T;sel+=selected[i]*mass;ext+=outside[i]*mass;T=next;
    }
    float* o=result+10*(y*w+x);
    for(int c=0;c<3;c++)o[c]=C[c]+T*bg;
    o[3]=1-T;o[4]=sel;o[5]=ext;o[9]=front;
    for(int q=0;q<3;q++)o[6+q]=NAN;
    // Replay accepted contributions, with thresholds from our own total mass.
    float sum=0;float total=1-T;T=1.0f;
    for(uint32_t j=range.x;j<end;j++) {
        uint32_t i=ids[j];float a=splat_alpha(xy[i],co[i],pixel);
        if(a<1.0f/255.0f)continue;
        float mass=a*T;
        // Keep the preregistered separately rounded mass accumulation.
        sum=__fadd_rn(sum,mass);
        for(int q=0;q<3;q++) {
            float fraction=q==0?.1f:(q==1?.5f:.9f);
            if(isnan(o[6+q])&&sum>=fraction*total)o[6+q]=depths[i];
        }
        T=T*(1-a);
    }
}
// Host ABI takes only native buffers and returns CUDA error codes, fail closed.
extern "C" int direct_curve_quantiles_cuda(int h,int w,const float* xy,const float* co,
    const float* colors,const float* depths,const uint32_t* ids,const uint32_t* ranges,
    const uint8_t* selected,const uint8_t* outside,float bg,float* result) {
    size_t tiles=((w+15)/16)*((h+15)/16),count=0,n=0;
    for(size_t t=0;t<tiles;t++)count=std::max(count,size_t(ranges[2*t+1]));
    for(size_t j=0;j<count;j++)n=std::max(n,size_t(ids[j])+1);
    const void* inputs[]={xy,co,colors,depths,ids,ranges,selected,outside};
    size_t sizes[]={n*8,n*16,n*12,n*4,count*4,tiles*8,n,n,size_t(h)*w*40};
    void* device[9]={};cudaError_t status=cudaSuccess;
    for(int i=0;i<9;i++) {
        status=cudaMalloc(&device[i],std::max(size_t(1),sizes[i]));if(status!=cudaSuccess)goto cleanup;
        if(i<8&&sizes[i]){status=cudaMemcpy(device[i],inputs[i],sizes[i],cudaMemcpyHostToDevice);if(status!=cudaSuccess)goto cleanup;}
    }
    replay<<<dim3((w+15)/16,(h+15)/16),dim3(16,16)>>>(h,w,(float2*)device[0],(float4*)device[1],
        (float*)device[2],(float*)device[3],(uint32_t*)device[4],(uint2*)device[5],
        (uint8_t*)device[6],(uint8_t*)device[7],bg,(float*)device[8]);
    status=cudaGetLastError();if(status!=cudaSuccess)goto cleanup;
    status=cudaMemcpy(result,device[8],sizes[8],cudaMemcpyDeviceToHost);
cleanup:
    for(int i=0;i<9;i++)if(device[i])cudaFree(device[i]);
    return int(status);
}
