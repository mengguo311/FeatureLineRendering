// Independent fixture oracle invokes upstream FORWARD::render unchanged.
#include <cuda_runtime.h>
#include <cstdint>
#include "cuda_rasterizer/forward.h"
extern "C" int stock_oracle(int h,int w,int n,int count,const float* xy,const float* co,
 const float* color,const uint32_t* ids,const uint32_t* ranges,float* rgb,float* trans) {
 const void* inputs[]={xy,co,color,ids,ranges};
 size_t sizes[]={size_t(n)*8,size_t(n)*16,size_t(n)*12,size_t(count)*4,size_t((w+15)/16)*((h+15)/16)*8,size_t(h)*w*12,size_t(h)*w*4,size_t(h)*w*4,12};
 void* d[9]={};cudaError_t e=cudaSuccess;float bg[3]={1,1,1};
 for(int i=0;i<9;i++){e=cudaMalloc(&d[i],sizes[i]);if(e)goto end;if(i<5){e=cudaMemcpy(d[i],inputs[i],sizes[i],cudaMemcpyHostToDevice);if(e)goto end;}}
 e=cudaMemcpy(d[8],bg,12,cudaMemcpyHostToDevice);if(e)goto end;
 FORWARD::render(dim3((w+15)/16,(h+15)/16),dim3(16,16),(uint2*)d[4],(uint32_t*)d[3],w,h,(float2*)d[0],(float*)d[2],(float4*)d[1],(float*)d[6],(uint32_t*)d[7],(float*)d[8],(float*)d[5]);
 e=cudaGetLastError();if(e)goto end;
 e=cudaMemcpy(rgb,d[5],sizes[5],cudaMemcpyDeviceToHost);if(e)goto end;
 e=cudaMemcpy(trans,d[6],sizes[6],cudaMemcpyDeviceToHost);
 end:for(int i=0;i<9;i++)if(d[i])cudaFree(d[i]);return int(e);
}
