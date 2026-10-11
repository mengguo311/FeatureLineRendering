// Execute only under the authorized common-lock GPU0 shared supervisor.
#include <cuda_runtime.h>
#include <iostream>
#include <fstream>
#include <cmath>
#include "paper_geometry_precision.cuh"
__global__ void probe(const float* input,float* output){
 glm::mat3 a;for(int r=0;r<3;r++)for(int c=0;c<3;c++)a[c][r]=input[r*3+c];
 glm::vec3 values(0.f);glm::mat3 vectors(0.f);
 unsigned n=paper_find_eigenvalues(a,values,vectors);output[0]=float(n);
 for(int j=0;j<3;j++)output[1+j]=values[j];
 auto rec=vectors*glm::mat3(values.x,0,0,0,values.y,0,0,0,values.z)*glm::transpose(vectors);
 float err=0,scale=0;for(int c=0;c<3;c++)for(int r=0;r<3;r++){err=fmaxf(err,fabsf(rec[c][r]-a[c][r]));scale=fmaxf(scale,fabsf(a[c][r]));}
 output[4]=err/scale;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;float input[9],out[5];std::ifstream f(argv[1]);for(float&x:input)f>>x;if(!f)return 3;
 float *x,*y;cudaMalloc(&x,sizeof(input));cudaMalloc(&y,sizeof(out));cudaMemcpy(x,input,sizeof(input),cudaMemcpyHostToDevice);
 probe<<<1,1>>>(x,y);auto e=cudaDeviceSynchronize();if(e!=cudaSuccess){std::cerr<<cudaGetErrorString(e);return 4;}
 cudaMemcpy(out,y,sizeof(out),cudaMemcpyDeviceToHost);cudaFree(x);cudaFree(y);
 std::cout.precision(17);std::cout<<"count "<<out[0]<<" eigenvalues "<<out[1]<<" "<<out[2]<<" "<<out[3]<<" relative_reconstruction "<<out[4]<<"\n";
 return (out[0]==3 && out[1]>1e-8&&out[2]>1e-8&&out[3]>1e-8&&std::isfinite(out[4])&&out[4]<1e-5)?0:1;
}
